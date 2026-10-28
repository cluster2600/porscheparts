"""Nested eight-way T4 refinement using the already certified shared T10 nodes.

The continuous traction vectors and parent patch roster remain fixed. Child
shape integrals are recomputed; P2's equivalent nodal forces are not reused.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

CHILDREN=((0,4,6,7),(4,1,5,8),(6,5,2,9),(7,8,9,3),
          (4,6,7,9),(4,6,5,9),(4,5,8,9),(4,7,8,9))
FACE_CHILDREN=((0,3,5),(3,1,4),(5,4,2),(3,4,5))


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def subdivide(cells,np):
    return np.stack([cells[:,indices]for indices in CHILDREN],axis=1).reshape(-1,4)


def subdivide_faces(faces,np):
    return np.stack([faces[:,indices]for indices in FACE_CHILDREN],axis=1).reshape(-1,3)


def select_patches(v,faces,config,np):
    g=config['geometry'];t=v[faces[:,:3]];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);area=np.linalg.norm(cross,axis=1)/2;normal=cross/(2*area[:,None]);centre=t.mean(axis=1);groups={};tol=.06
    def choose(radial,distance,axis,length):
        norm=np.linalg.norm(radial,axis=1);alignment=np.sum(normal*radial/np.where(norm>0,norm,1.)[:,None],axis=1)
        return np.flatnonzero(np.all(abs(distance)<=tol,axis=1)&(alignment<=-.9)&np.all(abs(t[:,:,axis])<=length+tol,axis=1))
    for i,(x,y)in enumerate(g['central_bolt_centres_xy_mm']):
        radial=np.column_stack([centre[:,0]-x,centre[:,1]-y,np.zeros(len(t))]);distance=np.hypot(t[:,:,0]-x,t[:,:,1]-y)-g['central_bore_radius_mm'];groups[f'bolt{i}']=choose(radial,distance,2,4.)
    for i,x in enumerate(g['end_centres_x_mm']):
        radial=np.column_stack([centre[:,0]-x,np.zeros(len(t)),centre[:,2]]);distance=np.hypot(t[:,:,0]-x,t[:,:,2])-g['end_bore_radius_mm'];groups[f'end{i}']=choose(radial,distance,1,23.)
    return groups,area


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--geometry',type=Path,required=True);p.add_argument('--mapping-proof',type=Path,required=True);p.add_argument('--preparation',type=Path,required=True);p.add_argument('--study',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic()
    import numpy as np
    old=Path(__file__).parents[1]/'resume-20261020';spec=importlib.util.spec_from_file_location('_retained_codec',old/'prepare_tetgen_mechanics_ccx.py');codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
    proof=json.loads(a.mapping_proof.read_text());prepared=json.loads((a.preparation/'assessment.json').read_text());config=json.loads(a.study.read_text())
    if proof['status']!='complete_C3D10_mapping_and_geometry_budget_passed'or sha(a.geometry/'quadratic.npz')not in proof['source_sha256'].values():raise ValueError('Matching whole mapping proof required')
    with np.load(a.geometry/'quadratic.npz',allow_pickle=False)as d:v=d['vertices'].copy();parent=d['tetrahedra'].copy();skin=d['boundary'].copy()
    groups,parent_area=select_patches(v,skin,config,np)
    for name,indices in groups.items():
        prior=prepared['bore_patches'][name]
        if len(indices)!=prior['faces']or abs(float(parent_area[indices].sum())-prior['area_mm2'])>1e-10:raise ValueError('Retained continuous patch roster differs: '+name)
    cells=subdivide(parent,np);faces=subdivide_faces(skin,np)
    for begin in range(0,len(cells),65536):
        part=cells[begin:begin+65536];t=v[part];det=np.sum((t[:,1]-t[:,0])*np.cross(t[:,2]-t[:,0],t[:,3]-t[:,0]),axis=1);negative=det<0
        if np.any(det==0)or not np.isfinite(det).all():raise ValueError('Degenerate child')
        part[negative,1],part[negative,2]=part[negative,2].copy(),part[negative,1].copy()
    nodes={name:np.unique(subdivide_faces(skin[indices],np))for name,indices in groups.items()};fixed=np.unique(np.r_[nodes['end0'],nodes['end1']]);material=config['material'];loads={}
    with(a.output/'mesh.inp').open('w')as stream:
        stream.write('*NODE,NSET=ALLN\n')
        for i,row in enumerate(v):
            tokens=[codec.ccx_field(x)for x in row]
            if not np.array_equal(np.array(list(map(float,tokens))),row):raise ValueError('Node encoding is no longer idempotent')
            stream.write(str(i+1)+','+','.join(tokens)+'\n')
        stream.write('*ELEMENT,TYPE=C3D4,ELSET=BODY\n')
        for i,cell in enumerate(cells,1):stream.write(str(i)+','+','.join(str(int(j)+1)for j in cell)+'\n')
    np.savez_compressed(a.output/'transport.npz',vertices=v,tetrahedra=cells,boundary=faces);np.savez_compressed(a.output/'groups.npz',**nodes)
    for case,prior in prepared['loads'].items():
        force=np.zeros_like(v)
        for i in range(4):
            child=subdivide_faces(skin[groups[f'bolt{i}']],np);t=v[child];area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2;traction=np.array(prior['per_bore_constant_traction_N_per_mm2'][i]);f=area[:,None]*traction/3
            for slot in range(3):np.add.at(force,child[:,slot],f)
        lines=['** Nested h refinement; same continuous bore traction and fixed patch','*INCLUDE,INPUT=mesh.inp','*MATERIAL,NAME=REFERENCE','*ELASTIC',f"{material['E_MPa']},{material['nu']}",'*SOLID SECTION,ELSET=BODY,MATERIAL=REFERENCE','*NSET,NSET=FIXED']
        lines += [','.join(str(int(i)+1)for i in fixed[j:j+16])for j in range(0,len(fixed),16)];lines += ['*STEP','*STATIC,SOLVER=SPOOLES','*BOUNDARY','FIXED,1,3','*CLOAD'];encoded=np.zeros_like(force)
        for index in np.flatnonzero(np.any(force!=0,axis=1)):
            for axis,value in enumerate(force[index]):
                if value:token=codec.ccx_field(value);encoded[index,axis]=float(token);lines.append(f'{index+1},{axis+1},{token}')
        lines += ['*NODE PRINT,NSET=ALLN','U','*NODE PRINT,NSET=FIXED','RF','*EL PRINT,ELSET=BODY','S','*END STEP'];deck=a.output/(case+'.inp');deck.write_text('\n'.join(lines)+'\n');np.savez_compressed(a.output/(case+'-loads.npz'),force=encoded)
        actual=np.r_[encoded.sum(0),np.cross(v,encoded).sum(0)];target=np.array(prior['actual_force_N']+prior['actual_moment_Nmm'])
        if abs(actual[:3]-target[:3]).max()>4e-5 or abs(actual[3:]-target[3:]).max()>.012:raise ValueError('Original resultant tolerance refused')
        loads[case]=dict(requested=prior['requested'],actual_force_N=actual[:3].tolist(),actual_moment_Nmm=actual[3:].tolist(),deck_sha256=sha(deck),per_bore_constant_traction_N_per_mm2=prior['per_bore_constant_traction_N_per_mm2'])
    report=dict(status='nested_T4_inputs_prepared_exact_volume_audit_pending',nodes=len(v),elements=len(cells),parent_elements=len(parent),boundary_faces=len(faces),material=material,loads=loads,retained_parent_patch_rosters=True,load_model_changed=False,continuous_tractions_unchanged=True,all_parent_nodes_and_midsides_unchanged=True,whole_surface_distance_upper_mm=proof['composed_reference_to_quadratic_surface_bound_mm'],geometry_adopted=False,stress_convergence_demonstrated=False,output_sha256={p.name:sha(p)for p in a.output.iterdir()if p.is_file()},source_sha256={str(p):sha(p)for p in [a.geometry/'quadratic.npz',a.mapping_proof,a.preparation/'assessment.json',a.study,Path(__file__)]},elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','nodes','elements','boundary_faces','elapsed_seconds']}))

if __name__=='__main__':main()
