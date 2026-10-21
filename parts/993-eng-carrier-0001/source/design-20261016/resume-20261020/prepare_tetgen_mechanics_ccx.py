"""Prepare nominal six-bore C3D4 mechanical inputs on the audited volume.

No solver is launched. Reuses the retained equivalent force/moment distributor
exactly; node-selection tolerance is explicit and is not a fitment tolerance.
"""
import argparse
import ast
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def ccx_field(value):
    for digits in range(17,0,-1):
        token=format(float(value),f'.{digits}g')
        if len(token)<=20:return token
    raise ValueError('No bounded-width numeric representation')


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    root=Path(__file__).resolve().parents[5];source=Path(__file__).resolve().parent
    config_path=root/'parts/993-eng-carrier-0001/source/design-20261016/bounded-webs.json'
    helper=root/'parts/993-eng-carrier-0001/source/bionic-20261011/simulate.py'
    config=json.loads(config_path.read_text());geometry=config['geometry'];material=config['material']
    record=root/'docs/reports/carrier-resume-20261020/evidence/tetgen-refined-outward-boundary-001/assessment.json'
    proof=json.loads(record.read_text())
    if sha(a.mesh)!=proof['output_sha256']['volume.npz']:raise ValueError('Refined outward volume identity differs')
    with np.load(a.mesh,allow_pickle=False)as data:v=data['vertices'].copy();cells=data['tetrahedra'].copy();faces=data['boundary'].copy()
    t=v[faces];tol=.0001;groups={};details={}
    for i,(x,y)in enumerate(geometry['central_bolt_centres_xy_mm']):
        distance=np.hypot(t[:,:,0]-x,t[:,:,1]-y)-geometry['central_bore_radius_mm']
        selected=np.all(abs(distance)<=tol,axis=1);name=f'bolt{i}';groups[name]=np.unique(faces[selected])
        details[name]=dict(triangles=int(selected.sum()),nodes=len(groups[name]),radial_deviation_max_mm=float(abs(distance[selected]).max()),bounds_mm=[v[groups[name]].min(axis=0).tolist(),v[groups[name]].max(axis=0).tolist()])
    for i,x in enumerate(geometry['end_centres_x_mm']):
        distance=np.hypot(t[:,:,0]-x,t[:,:,2])-geometry['end_bore_radius_mm']
        selected=np.all(abs(distance)<=tol,axis=1);name=f'end{i}';groups[name]=np.unique(faces[selected])
        details[name]=dict(triangles=int(selected.sum()),nodes=len(groups[name]),radial_deviation_max_mm=float(abs(distance[selected]).max()),bounds_mm=[v[groups[name]].min(axis=0).tolist(),v[groups[name]].max(axis=0).tolist()])
    if min(map(len,groups.values()))<12:raise ValueError('Missing nominal bore group')
    if len(np.unique(np.concatenate(list(groups.values()))))!=sum(map(len,groups.values())):raise ValueError('Overlapping bore groups')
    original=helper.read_text();node=next(n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)and n.name=='distribute');function=ast.get_source_segment(original,node);namespace={'np':np};exec(compile(function,str(helper),'exec'),namespace);distribute=namespace['distribute']
    (a.output/'distribute-source.py').write_text(function+'\n')
    np.savez_compressed(a.output/'groups.npz',**groups)
    transport=v.copy();maximum_error=F(0)
    with (a.output/'mesh.inp').open('w')as stream:
        stream.write('** Exact audited volume coordinates; positive C3D4 connectivity\n*NODE,NSET=ALLN\n')
        for i,row in enumerate(v,1):
            tokens=[ccx_field(x)for x in row];transport[i-1]=list(map(float,tokens));cost=sum(abs(F(float(x))-F(float(y)))for x,y in zip(row,transport[i-1])if x!=y);maximum_error=max(maximum_error,cost)
            stream.write(str(i)+','+','.join(tokens)+'\n')
        stream.write('*ELEMENT,TYPE=C3D4,ELSET=BODY\n')
        for i,row in enumerate(cells,1):stream.write(str(i)+','+','.join(str(int(x)+1)for x in row)+'\n')
    fixed=np.concatenate([groups['end0'],groups['end1']])+1;loads={}
    for case in ['gravity','combined']:
        request=config['load_cases'][case];force=distribute(v,[groups[f'bolt{i}']for i in range(4)],request['force_N'],request['moment_Nmm'])
        lines=['** Nominal geometry, assumed loads, dense elastic material study','*INCLUDE,INPUT=mesh.inp','*MATERIAL,NAME=REFERENCE','*ELASTIC',f"{material['E_MPa']},{material['nu']}",'*SOLID SECTION,ELSET=BODY,MATERIAL=REFERENCE','*NSET,NSET=FIXED']
        lines += [','.join(map(str,fixed[j:j+16]))for j in range(0,len(fixed),16)]
        lines += ['*STEP','*STATIC,SOLVER=SPOOLES','*BOUNDARY','FIXED,1,3','*CLOAD']
        for i in np.flatnonzero(np.any(force!=0,axis=1)):
            lines += [f'{i+1},{j+1},{ccx_field(x)}'for j,x in enumerate(force[i])if x!=0]
        lines += ['*NODE PRINT,NSET=ALLN','U','*NODE PRINT,NSET=FIXED','RF','*EL PRINT,ELSET=BODY','S','*END STEP']
        deck=a.output/(case+'.inp');deck.write_text('\n'.join(lines)+'\n')
        np.savez_compressed(a.output/(case+'-loads.npz'),force=force)
        loads[case]=dict(force_N=force.sum(axis=0).tolist(),moment_Nmm=np.cross(v,force).sum(axis=0).tolist(),requested=request,deck_sha256=sha(deck))
    np.savez_compressed(a.output/'transport.npz',vertices=transport,tetrahedra=cells,boundary=faces)
    report=dict(numeric_field_width_limit=20,complete_coordinate_transport_L1_bound_mm=str(maximum_error),complete_coordinate_transport_L1_bound_mm_float=float(maximum_error),source_derivation=dict(parent_source_sha256='9c741913e44bdb180539eda1b5cbe049d5af231c0b590fca3cea8388ed2a0987',changes=['Select SPOOLES after affine-control comparison','Serialize every numeric value within 20 characters; quantify complete coordinate transport displacement']),status='nominal_C3D4_mechanical_inputs_prepared_not_solved',nodes=len(v),C3D4_elements=len(cells),bore_groups=details,node_selection_tolerance_mm=tol,selection_tolerance_is_dimensional_acceptance=False,support_model='All translations fixed on both nominal end-bore groups',load_distribution='Unchanged retained weighted minimum-norm six-component distributor; no contact or bolt preload',loads=loads,material=material,solver_requested='CalculiX SPOOLES',source_sha256={str(p):sha(p)for p in [a.mesh,config_path,helper,record,Path(__file__)]},output_sha256={p.name:sha(p)for p in a.output.iterdir()if p.is_file()},mechanical_mesh_admitted=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],nodes=len(v),cells=len(cells),bore_group_nodes={k:d['nodes']for k,d in details.items()})))

if __name__=='__main__':main()
