"""Read every C3D10 integration point, equilibrium and independent stress energy."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


EDGES=[(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)]


def stress_energy(v,cells,stress,E,nu,np):
    if not E>0 or not -1<nu<.5:raise ValueError('Positive isotropic elasticity required')
    low=(5-np.sqrt(5.))/20;high=1-3*low;bary=np.full((4,4),low);np.fill_diagonal(bary,high);grad=np.array([[-1,-1,-1],[1,0,0],[0,1,0],[0,0,1]])
    derivatives=[]
    for row in bary:
        derivatives.append(np.vstack([(4*row-1)[:,None]*grad,np.stack([4*(row[i]*grad[j]+row[j]*grad[i])for i,j in EDGES])]))
    total=0.;volume=0.
    for start in range(0,len(cells),16384):
        stop=min(start+16384,len(cells));points=v[cells[start:stop]];state=stress[start:stop];diag=state[:,:,:3];shear=state[:,:,3:];pairs=diag[:,:,0]*diag[:,:,1]+diag[:,:,1]*diag[:,:,2]+diag[:,:,2]*diag[:,:,0]
        density=(np.sum(diag*diag,axis=2)-2*nu*pairs+2*(1+nu)*np.sum(shear*shear,axis=2))/(2*E)
        for ip,derivative in enumerate(derivatives):
            jac=np.einsum('nki,kj->nij',points-points[:,0,None,:],derivative);det=np.linalg.det(jac)
            if not np.all(np.isfinite(det)&(det>0)):raise ValueError('Nonpositive quadratic integration Jacobian')
            total+=float(np.dot(det/24,density[:,ip]));volume+=float(det.sum()/24)
    return total,volume


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
    if sha(files[0])not in [item['deck_sha256']for item in prepared['loads'].values()]:raise ValueError('Completed load deck differs from prepared cases')
    force=np.zeros_like(v);active=False
    for line in files[0].read_text().splitlines():
        if line.startswith('*'):active=line.upper().startswith('*CLOAD');continue
        if active:
            i,j,x=line.split(',');force[int(i)-1,int(j)-1]+=float(x)
    displacements=np.empty((len(v),3));stress=np.empty((len(cells),4,6));reactions=np.empty((len(fixed),3));reaction_ids=np.empty(len(fixed),dtype=np.int64);counts=dict(displacements=0,stresses=0,forces=0);current=None
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
                if index!=i//4 or i>=4*len(cells)or int(fields[1])!=i%4+1:raise ValueError('C3D10 integration-point roster differs')
                stress[i//4,i%4]=values
            else:
                if i>=len(fixed):raise ValueError('Reaction roster overflow')
                reaction_ids[i]=index;reactions[i]=values
            counts[current]+=1
    if counts!=dict(displacements=len(v),stresses=4*len(cells),forces=len(fixed)):raise ValueError('Incomplete whole result rosters')
    if not np.array_equal(np.sort(reaction_ids),np.sort(fixed)):raise ValueError('Reaction support node roster differs')
    if not all(np.isfinite(x).all()for x in [displacements,stress,reactions]):raise ValueError('Nonfinite results')
    residual_force=reactions.sum(axis=0)+force.sum(axis=0);residual_moment=np.cross(v[reaction_ids],reactions).sum(axis=0)+np.cross(v,force).sum(axis=0)
    scale=max(1.,float(abs(force).sum()),float(abs(reactions).sum()));force_limit=1e-4*scale;moment_limit=1e-4*scale*300
    sx,sy,sz,xy,xz,yz=stress.reshape(-1,6).T;vm=np.sqrt(((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)/2+3*(xy*xy+xz*xz+yz*yz));peak=int(vm.argmax());peak_cell,peak_ip=divmod(peak,4);u=np.linalg.norm(displacements,axis=1);work=float((force*displacements).sum())
    equilibrium=bool(abs(residual_force).max()<force_limit and abs(residual_moment).max()<moment_limit and work>0)
    # Four-point order verified against CalculiX 2.21 gauss.f gauss3d5.
    low=(5-np.sqrt(5.))/20;high=1-3*low;bary=np.full((4,4),low);np.fill_diagonal(bary,high)
    shapes=np.column_stack([bary*(2*bary-1),np.stack([4*bary[:,i]*bary[:,j]for i,j in EDGES],axis=1)])
    peak_position=shapes[peak_ip]@v[cells[peak_cell]]
    internal,volume=stress_energy(v,cells,stress,prepared['material']['E_MPa'],prepared['material']['nu'],np)
    energy_residual=abs(internal-work/2)/(work/2)if work>0 else float('inf')
    energy_pass=bool(np.isfinite(energy_residual)and energy_residual<=1e-4)
    equilibrium=equilibrium and energy_pass
    np.savez_compressed(a.output/'results.npz',displacement=displacements,stress=stress,VM=vm,reaction_node_indices=reaction_ids,reactions=reactions,force=force)
    report=dict(status='complete_linear_C3D10_results_equilibrium_and_energy_passed'if equilibrium else'quadratic_equilibrium_or_energy_refused',nodes=len(v),C3D10_elements=len(cells),result_rows=counts,displacement_max_mm=float(u.max()),integration_point_VM_max_MPa=float(vm[peak]),peak_element_one_based=peak_cell+1,peak_integration_point_one_based=peak_ip+1,peak_integration_point_position_mm=peak_position.tolist(),force_N=force.sum(axis=0).tolist(),moment_Nmm=np.cross(v,force).sum(axis=0).tolist(),reaction_force_N=reactions.sum(axis=0).tolist(),force_residual_N=residual_force.tolist(),moment_residual_Nmm=residual_moment.tolist(),force_residual_limit_N=force_limit,moment_residual_limit_Nmm=moment_limit,external_work_Nmm=work,linear_strain_energy_Nmm=work/2,independent_stress_compliance_energy_Nmm=internal,relative_energy_residual=energy_residual,fixed_energy_relative_limit=1e-4,integrated_volume_mm3=volume,solver_seconds=receipt['elapsed_seconds'],material_allowable_MPa=None,stress_convergence_demonstrated=False,strength_qualified=False,mechanical_scope='Provisional C3D10 linear-elastic dense reference; consistent constant bore tractions and assumed loads; no preload/contact model',source_sha256={str(p):sha(p)for p in [*files,a.execution/'actual-terminal.json',a.execution/'plan.json',a.preparation/'transport.npz',a.preparation/'assessment.json',a.qualification,Path(__file__)]},output_sha256=sha(a.output/'results.npz'))
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','displacement_max_mm','integration_point_VM_max_MPa','force_residual_N','moment_residual_Nmm']}));return 0 if equilibrium else 2

if __name__=='__main__':raise SystemExit(main())
