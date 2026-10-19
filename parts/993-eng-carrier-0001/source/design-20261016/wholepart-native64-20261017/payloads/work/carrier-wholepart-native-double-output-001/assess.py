"""Assess future fixed CCX outputs and dimensional changes; never run a solver."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FIELDS=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/analyze_plastic900.py'
GRADIENTS=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/audit_finite_work.py'
EDGES=ROOT/'parts/993-eng-carrier-0001/source/revalidation-20261016/audit_energy.py'
FIELDS_SHA='ea583d521738c1b775655fc0485c20c9d6db4e4e16310273899e5c1e1d4a8e85'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
GRADIENTS_SHA='e13397c0fd15d48d29b859bff371b2f135a73d34ee94ba104f74c869149b821c'
EDGES_SHA='eca4f9adc81e3511553a713d3f52d7ad604fac7fe36fc4e40eddfe9d9fbea4e8'


def private(path):
    spec=importlib.util.spec_from_file_location('_fixed_wholepart_inputs',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def circle(points,axis):
    keep=[i for i in range(3)if i!=axis];xy=np.asarray(points,dtype=float)[:,keep]
    origin=xy.mean(axis=0);q=xy-origin
    matrix=np.column_stack((2*q,np.ones(len(q))));rhs=np.einsum('ij,ij->i',q,q)
    coeff,_,rank,_=np.linalg.lstsq(matrix,rhs,rcond=None)
    if rank!=3:raise ValueError('A projected bore group does not define a circle')
    center=origin+coeff[:2];radii=np.linalg.norm(xy-center,axis=1);radius=np.sqrt(coeff[2]+np.dot(coeff[:2],coeff[:2]))
    c=np.asarray(points,dtype=float).mean(axis=0);c[keep]=center
    return dict(projected_center_mm=c.tolist(),projected_diameter_mm=float(2*radius),
        radial_residual_max_mm=float(np.max(np.abs(radii-radius))),fixed_projection_axis=axis,
        scope='Least-squares projected circle of the identical original nodes; not a newly fitted 3D cylinder or physical bore tolerance.')


def metrics(nodes,cells,groups,displacement,analytic_strain=None):
    tags=sorted(nodes);index={tag:i for i,tag in enumerate(tags)};xyz=np.array([nodes[i]for i in tags]);u=np.array([displacement[i]for i in tags]);moved=xyz+u
    before={};after={}
    for name,ids in groups.items():
        rows=[index[i]for i in ids];axis=2 if name.startswith('bolt')else 1
        before[name]=circle(xyz[rows],axis);after[name]=circle(moved[rows],axis)
    bores={n:dict(original=before[n],deformed=after[n],diameter_change_mm=after[n]['projected_diameter_mm']-before[n]['projected_diameter_mm'],
        center_shift_mm=(np.array(after[n]['projected_center_mm'])-before[n]['projected_center_mm']).tolist())for n in groups}
    distances={}
    for a,b in [('bolt0','bolt1'),('bolt2','bolt3'),('end0','end1')]:
        original=float(np.linalg.norm(np.array(before[a]['projected_center_mm'])-before[b]['projected_center_mm']))
        changed=float(np.linalg.norm(np.array(after[a]['projected_center_mm'])-after[b]['projected_center_mm']))
        distances[a+'__'+b]=dict(original_mm=original,deformed_mm=changed,change_mm=changed-original)
    if sha(GRADIENTS)!=GRADIENTS_SHA or sha(EDGES)!=EDGES_SHA:raise ValueError('The original C3D10 integration helpers differ')
    ns={'np':np};edge_nodes=[n for n in ast.parse(EDGES.read_text()).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='EDGE_PAIRS'for t in n.targets)]
    gradient_nodes=[n for n in ast.parse(GRADIENTS.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='gradients']
    if len(edge_nodes)!=1 or len(gradient_nodes)!=1:raise ValueError('The original C3D10 integration helpers are not unique')
    exec(compile(ast.Module(body=edge_nodes+gradient_nodes,type_ignores=[]),str(GRADIENTS),'exec'),ns)
    connectivity=np.array([[index[i]for i in row]for row in cells.values()]);derivative,weights=ns['gradients'](xyz[connectivity])
    deformation=np.eye(3)+np.einsum('eni,eqnj->eqij',u[connectivity],derivative);jacobian=np.linalg.det(deformation)
    if not np.isfinite(jacobian).all()or np.any(jacobian<=0):raise ValueError('A C3D10 Gauss deformation Jacobian is nonpositive/nonfinite')
    v0,v1=float(4*weights.sum()),float(np.sum(jacobian*weights[:,None]))
    strain_error=None if analytic_strain is None else float(np.max(np.abs(.5*(deformation+np.swapaxes(deformation,-1,-2))-np.eye(3)*(1+analytic_strain))))
    return dict(analytic_strain_max_error=strain_error,bore_projected_metrics=bores,center_distances=distances,displacement_max_mm=float(np.linalg.norm(u,axis=1).max()),
        reference_volume_mm3=v0,deformed_volume_4Gauss_mm3=v1,minimum_Gauss_detF=float(jacobian.min()),reference_mass_kg=v0*4.42e-6,
        material_mass_kg=v0*4.42e-6,mass_conserved_by_Lagrangian_definition=True,
        mass_note='Same material and cells. Deformed volume is diagnostic; keeping rho0 constant on that new volume would incorrectly change material mass.')


def assess(folder,output,solver_receipt,solver_sha):
    folder=Path(folder);output=Path(output)
    if output.exists()or output.is_symlink():raise FileExistsError('A fresh assessment is required')
    if sha(solver_receipt)!=solver_sha:raise ValueError('Actual solver receipt changed')
    execution=json.loads(Path(solver_receipt).read_text())
    if (execution.get('status')!='solver_executed_no_numeric_admission'or execution.get('actual_container_exit_code')!=0 or
        not execution.get('container_removed')or not execution.get('input_hashes_unchanged')or execution['actual_container_after_start']['OOMKilled']):
        raise ValueError('Actual clean RC0 solver execution is required')
    if sha(folder/'wholepart-release.dat')!=execution['outputs']['wholepart-release.dat']['sha256']:raise ValueError('Actual native DAT identity differs')
    if sha(FIELDS)!=FIELDS_SHA:raise ValueError('The unchanged existing DAT parser differs')
    prepare=private(HERE/'prepare.py');meta=json.loads((folder/'preparation.json').read_text())
    if meta['preparer_sha256']!=sha(HERE/'prepare.py')or any(sha(folder/n)!=h for n,h in meta['output_files_sha256'].items()):raise ValueError('Prepared wholepart inputs changed')
    nodes,cells=prepare.model(folder/'mesh.inp');groups=meta['original_bore_node_groups'];tags=set(nodes)
    tree=ast.parse(FIELDS.read_text());functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='fields']
    if len(functions)!=1:raise ValueError('Existing fields parser not unique')
    ns=dict(np=np,Path=Path);exec(compile(ast.Module(body=functions,type_ignores=[]),str(FIELDS),'exec'),ns)
    reports={};passed=True;analytic_passed=True;clamped_u=None
    path=folder/'wholepart-release.dat'
    if sha(path)!='51962537dbaf9cf567909932cd874b08839738a1e33fc65d2d7ebb3934813eae':raise ValueError('Native DAT mechanical fields differ from the unchanged original four-state result')
    data=ns['fields'](path)
    reader_path=HERE/'read_double_frd.py'
    if sha(reader_path)!='7d8fd8ec6f8431e95f105b74224de9ed210e9c81f1a7d684d45548d5243b29c4':raise ValueError('Reviewed native double reader differs')
    reader=private(reader_path)
    native=reader.read(folder/'wholepart-release.frd',nodes,cells,meta['expected_total_frame_times'])
    data['displacements']={t:np.asarray(rows,dtype=float)for t,rows in native.items()}
    all_times=sorted(data['displacements'])
    if all_times!=meta['expected_total_frame_times']or any(all_times!=sorted(data[k])for k in ('forces','stresses','internal energy density')):raise ValueError('The four exact full-part frame times differ or are incomplete')
    for name,expected_frames in [('zero',1),('uniform',1),('incompatible-release',2)]:
        times=[1.]if name=='zero'else[2.]if name=='uniform'else[3.,4.]
        frames=[]
        for time in times:
            rows=data['displacements'][time];ids=[int(row[0])for row in rows]
            if len(ids)!=len(tags)or set(ids)!=tags or np.any(rows[:,0]!=ids):raise ValueError('A full original nodal displacement is missing/repeated/noninteger')
            u={int(r[0]):r[1:]for r in rows}
            e=0. if name=='zero'else prepare.ALPHA*((prepare.T0-prepare.AMPLITUDE/prepare.ALPHA)-prepare.T0)if name=='uniform'else None
            report=metrics(nodes,cells,groups,u,analytic_strain=e)
            expected_GP=np.column_stack((np.repeat(list(cells),4),np.tile(np.arange(1,5),len(cells))))
            if any(not np.array_equal(data[k][time][:,:2],expected_GP)for k in ('stresses','internal energy density')):raise ValueError('A full original element/Gauss field is missing, repeated or reordered')
            force=data['forces'][time];fids=[int(row[0])for row in force]
            if len(fids)!=len(tags)or set(fids)!=tags or np.any(force[:,0]!=fids):raise ValueError('A full nodal force row is missing/repeated/noninteger')
            f=force[:,1:];x=np.array([nodes[int(row[0])]for row in force]);report.update(time=float(time),net_force_N=np.sum(f,axis=0).tolist(),net_moment_Nmm=np.sum(np.cross(x,f),axis=0).tolist(),
                maximum_abs_stress_component_MPa=float(np.max(np.abs(data['stresses'][time][:,2:]))))
            force_bound=max(1e-3,1e-4*float(np.linalg.norm(f,axis=1).sum()))
            moment_bound=max(1e-2,1e-4*float(np.linalg.norm(np.cross(x,f),axis=1).sum()))
            equilibrium=bool(np.linalg.norm(np.sum(f,axis=0))<=force_bound and np.linalg.norm(np.sum(np.cross(x,f),axis=0))<=moment_bound)
            report.update(force_residual_bound_N=force_bound,moment_residual_bound_Nmm=moment_bound,equilibrium_pass=equilibrium)
            passed=passed and equilibrium
            if name in ('zero','uniform'):
                a=np.array(nodes[meta['gauge_DOF'][0][0]]);e=0. if name=='zero'else prepare.ALPHA*((prepare.T0-prepare.AMPLITUDE/prepare.ALPHA)-prepare.T0)
                error=max(float(np.max(np.abs(u[i]-e*(np.array(nodes[i])-a))))for i in tags)
                report.update(analytic_displacement_max_error_mm=error,analytic_strain=e,
                    analytic_pass=error<=1e-6 and report['analytic_strain_max_error']<=1e-7 and report['maximum_abs_stress_component_MPa']<=1e-3)
                passed=passed and report['analytic_pass'];analytic_passed=analytic_passed and report['analytic_pass']
                if not report['analytic_pass']:raise ValueError('Analytic control failed before interpreting the quadratic case')
            if time==3.:clamped_u=u
            if time==4.:
                report['release_increment_displacement_max_mm']=max(float(np.linalg.norm(u[i]-clamped_u[i]))for i in tags)
                previous=frames[0]['bore_projected_metrics']
                report['release_bore_diameter_changes_mm']={n:report['bore_projected_metrics'][n]['deformed']['projected_diameter_mm']-previous[n]['deformed']['projected_diameter_mm']for n in groups}
            frames.append(report)
        reports[name]=dict(frames=frames,DAT_sha256=sha(path))
    result=dict(status='wholepart_sensitivity_numeric_controls_passed_no_physical_prediction'if passed else'numeric_controls_refused',analytical_controls_passed=analytic_passed,numeric_controls_passed=passed,cases=reports,
        global_admission=False,physical_print_prediction=False,real_support_release_claimed=False,solver_returncode_checked=True,actual_solver_receipt_sha256=solver_sha,
        scope='Four wholepart equivalent-eigenstrain sensitivity states; authentic RC0 and cleaned owned container checked. Fictitious fixture; not a calibrated print prediction.',
        assessor_sha256=sha(__file__),native_displacements_FRD_sha256=sha(folder/'wholepart-release.frd'),native_double_reader_sha256=sha(reader_path),displacement_scope='Native binary64 DISP only; original coordinates/IDs/C3D10 topology matched; unchanged DAT used for force/stress/ENER',original_DAT_byte_identical=True,existing_DAT_parser_sha256=FIELDS_SHA,preparation_sha256=sha(folder/'preparation.json'))
    with output.open('x')as s:json.dump(result,s,indent=2,allow_nan=False);s.write('\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('output',type=Path);p.add_argument('--solver-receipt',type=Path,required=True);p.add_argument('--solver-receipt-sha256',required=True);a=p.parse_args();r=assess(a.folder,a.output,a.solver_receipt,a.solver_receipt_sha256)
    raise SystemExit(0 if r['numeric_controls_passed']else 1)
