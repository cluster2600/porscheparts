"""Read every C3D4 result and check equilibrium of an actual owned native CCX run."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--execution',type=Path,required=True);p.add_argument('--preparation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qualification',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    receipt=json.loads((a.execution/'actual-terminal.json').read_text());plan=json.loads((a.execution/'plan.json').read_text());prepared=json.loads((a.preparation/'assessment.json').read_text())
    if receipt['actual_returncode']or not receipt['inputs_unchanged']or not receipt['process_reaped']or not receipt['solver_finished_marker']or receipt['solver_error_marker']:raise ValueError('Actual solver completion receipt refused')
    qualified=json.loads(a.qualification.read_text())
    if qualified['status']!='native_CalculiX_2_21_analytic_controls_passed'or receipt['native_binary_sha256']!=qualified['native_binary_sha256']:raise ValueError('Qualified native runtime identity differs')
    with np.load(a.preparation/'transport.npz',allow_pickle=False)as data:v=data['vertices'].copy();cells=data['tetrahedra'].copy()
    with np.load(a.preparation/'groups.npz',allow_pickle=False)as data:fixed=np.concatenate([data['end0'],data['end1']])
    files=[a.execution/'case'/n for n in ['job.inp','mesh.inp','job.dat']]
    for f in files:
        if sha(f)!=receipt['output_sha256'][f.name]:raise ValueError('Completed solver output identity differs')
    if sha(files[1])!=prepared['output_sha256']['mesh.inp']:raise ValueError('Mesh deck differs from preparation')
    if sha(files[0])not in [item['deck_sha256']for item in prepared['loads'].values()]:raise ValueError('Prepared load identity differs')
    force=np.zeros_like(v);active=False
    for line in files[0].read_text().splitlines():
        if line.startswith('*'):active=line.upper().startswith('*CLOAD');continue
        if active:
            i,j,x=line.split(',');force[int(i)-1,int(j)-1]+=float(x)
    displacements=np.empty((len(v),3));stress=np.empty((len(cells),6));reactions=np.empty((len(fixed),3));reaction_ids=np.empty(len(fixed),dtype=np.int64);counts=dict(displacements=0,stresses=0,forces=0);current=None
    with files[2].open()as stream:
        for line in stream:
            line=line.strip()
            for key in counts:
                if line.startswith(key+' ('):
                    if counts[key]:raise ValueError('Multiple result states; this assessor requires one linear step')
                    current=key
            fields=line.split();n=8 if current=='stresses' else 4
            if not current or len(fields)!=n or not fields[0].isdigit():continue
            i=counts[current];index=int(fields[0])-1;values=list(map(float,fields[2:]if current=='stresses'else fields[1:]))
            if current=='displacements':
                if index!=i or i>=len(v):raise ValueError('Displacement node roster differs')
                displacements[i]=values
            elif current=='stresses':
                if index!=i or i>=len(cells)or int(fields[1])!=1:raise ValueError('C3D4 integration-point roster differs')
                stress[i]=values
            else:
                if i>=len(fixed):raise ValueError('Reaction roster overflow')
                reaction_ids[i]=index;reactions[i]=values
            counts[current]+=1
    if counts!=dict(displacements=len(v),stresses=len(cells),forces=len(fixed)):raise ValueError('Incomplete whole result rosters')
    if not np.array_equal(np.sort(reaction_ids),np.sort(fixed)):raise ValueError('Reaction support node roster differs')
    if not all(np.isfinite(x).all()for x in [displacements,stress,reactions]):raise ValueError('Nonfinite results')
    residual_force=reactions.sum(axis=0)+force.sum(axis=0);residual_moment=np.cross(v[reaction_ids],reactions).sum(axis=0)+np.cross(v,force).sum(axis=0)
    scale=max(1.,float(abs(force).sum()),float(abs(reactions).sum()));force_limit=1e-4*scale;moment_limit=1e-4*scale*300
    sx,sy,sz,xy,xz,yz=stress.T;vm=np.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy*xy+xz*xz+yz*yz));peak=int(vm.argmax());u=np.linalg.norm(displacements,axis=1);work=float((force*displacements).sum())
    equilibrium=bool(abs(residual_force).max()<force_limit and abs(residual_moment).max()<moment_limit and work>0)
    np.savez_compressed(a.output/'results.npz',displacement=displacements,stress=stress,VM=vm,reaction_node_indices=reaction_ids,reactions=reactions,force=force)
    report=dict(status='complete_linear_C3D4_results_and_equilibrium_passed'if equilibrium else'linear_equilibrium_refused',nodes=len(v),C3D4_elements=len(cells),result_rows=counts,displacement_max_mm=float(u.max()),integration_point_VM_max_MPa=float(vm[peak]),peak_element_one_based=peak+1,peak_centroid_mm=v[cells[peak]].mean(axis=0).tolist(),force_N=force.sum(axis=0).tolist(),moment_Nmm=np.cross(v,force).sum(axis=0).tolist(),reaction_force_N=reactions.sum(axis=0).tolist(),force_residual_N=residual_force.tolist(),moment_residual_Nmm=residual_moment.tolist(),force_residual_limit_N=force_limit,moment_residual_limit_Nmm=moment_limit,external_work_Nmm=work,linear_strain_energy_Nmm=work/2,solver_seconds=receipt['elapsed_seconds'],material_allowable_MPa=None,stress_convergence_demonstrated=False,strength_qualified=False,mechanical_scope='Provisional C3D4 linear-elastic dense reference, nominal six-bore fixture and assumed load; no preload/contact model',source_sha256={str(p):sha(p)for p in [*files,a.execution/'actual-terminal.json',a.execution/'plan.json',a.preparation/'transport.npz',a.preparation/'assessment.json',a.qualification,Path(__file__)]},output_sha256=sha(a.output/'results.npz'))
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','displacement_max_mm','integration_point_VM_max_MPa','force_residual_N','moment_residual_Nmm']}));return 0 if equilibrium else 2

if __name__=='__main__':raise SystemExit(main())
