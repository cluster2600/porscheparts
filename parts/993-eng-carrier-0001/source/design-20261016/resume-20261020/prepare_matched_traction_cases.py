"""Matched P1/P2 cases with consistently integrated, constant bore tractions.

The same continuous boundary patches and resultant loads are used at both
orders. This is a separate fixture model from the retained dead-node studies.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--geometry',type=Path,required=True);p.add_argument('--mapping-proof',type=Path,required=True);p.add_argument('--study',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    proof=json.loads(a.mapping_proof.read_text());record=json.loads((a.geometry/'assessment.json').read_text());config=json.loads(a.study.read_text());g=config['geometry'];material=config['material']
    if proof['status']!='complete_C3D10_mapping_and_geometry_budget_passed'or sha(a.geometry/'quadratic.npz')not in proof['source_sha256'].values():raise ValueError('Whole quadratic mapping proof required')
    source=Path(__file__).with_name('prepare_tetgen_mechanics_ccx.py');spec=importlib.util.spec_from_file_location('_matched_numeric_codec',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with np.load(a.geometry/'linear.npz',allow_pickle=False)as data:v=data['vertices'].copy();cells=data['tetrahedra'].copy();faces=data['boundary'].copy()
    with np.load(a.geometry/'quadratic.npz',allow_pickle=False)as data:v2=data['vertices'].copy();cells2=data['tetrahedra'].copy();faces2=data['boundary'].copy()
    if not np.array_equal(v2[:len(v)],v)or not np.array_equal(cells2[:,:4],cells)or not np.array_equal(faces2[:,:3],faces):raise ValueError('Matched corner geometry and boundary rosters required')
    t=v[faces];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);norm=np.linalg.norm(cross,axis=1);area=norm/2;normal=cross/norm[:,None];centres=t.mean(axis=1);groups={};details={};tol=.06
    def selected(radial,distance,axis,length):
        rnorm=np.linalg.norm(radial,axis=1);alignment=np.sum(normal*radial/np.where(rnorm>0,rnorm,1.)[:,None],axis=1)
        return np.all(abs(distance)<=tol,axis=1)&(alignment<=-.9)&np.all(abs(t[:,:,axis])<=length+tol,axis=1)
    for i,(x,y)in enumerate(g['central_bolt_centres_xy_mm']):
        radial=np.column_stack([centres[:,0]-x,centres[:,1]-y,np.zeros(len(t))]);distance=np.hypot(t[:,:,0]-x,t[:,:,1]-y)-g['central_bore_radius_mm'];groups[f'bolt{i}']=np.flatnonzero(selected(radial,distance,2,4.))
    for i,x in enumerate(g['end_centres_x_mm']):
        radial=np.column_stack([centres[:,0]-x,np.zeros(len(t)),centres[:,2]]);distance=np.hypot(t[:,:,0]-x,t[:,:,2])-g['end_bore_radius_mm'];groups[f'end{i}']=np.flatnonzero(selected(radial,distance,1,23.))
    for name,indices in groups.items():
        if len(indices)<4:raise ValueError('Missing complete nominal bore patch: '+name)
        details[name]=dict(faces=len(indices),area_mm2=float(area[indices].sum()),area_centroid_mm=np.average(centres[indices],axis=0,weights=area[indices]).tolist())
    def B(r):
        x,y,z=r;skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])
        return np.column_stack([np.eye(3),-skew])
    operators=[B(np.array(details[f'bolt{i}']['area_centroid_mm']))for i in range(4)];H=sum(details[f'bolt{i}']['area_mm2']*(operators[i].T@operators[i])for i in range(4))
    if not np.linalg.eigvalsh(H).min()>0:raise ValueError('Positive six-component traction system required')
    field={}
    for case in ['gravity','combined']:
        request=config['load_cases'][case];wrench=np.array([*request['force_N'],*request['moment_Nmm']],dtype=float);q=np.linalg.solve(H,wrench);field[case]=[operator@q for operator in operators]
    reports={}
    for order,points,connectivity,skin in [('P1',v,cells,faces),('P2',v2,cells2,faces2)]:
        out=a.output/order;out.mkdir();shutil.copyfile(a.geometry/f'mesh-{order}.inp',out/'mesh.inp');np.savez_compressed(out/'transport.npz',vertices=points,tetrahedra=connectivity,boundary=skin)
        nodes={name:np.unique(skin[indices])for name,indices in groups.items()};fixed=np.concatenate([nodes['end0'],nodes['end1']]);np.savez_compressed(out/'groups.npz',**nodes);loads={}
        for case in ['gravity','combined']:
            force=np.zeros_like(points)
            for i in range(4):
                indices=groups[f'bolt{i}'];slots=faces[indices]if order=='P1'else faces2[indices,3:];load=area[indices,None]*field[case][i][None,:]/3
                for slot in range(3):np.add.at(force,slots[:,slot],load)
            lines=['** Matched continuous constant-bore-traction fixture; assumed nominal geometry/loads','*INCLUDE,INPUT=mesh.inp','*MATERIAL,NAME=REFERENCE','*ELASTIC',f"{material['E_MPa']},{material['nu']}",'*SOLID SECTION,ELSET=BODY,MATERIAL=REFERENCE','*NSET,NSET=FIXED']
            lines += [','.join(str(int(x)+1)for x in fixed[j:j+16])for j in range(0,len(fixed),16)]
            lines += ['*STEP','*STATIC,SOLVER=SPOOLES','*BOUNDARY','FIXED,1,3','*CLOAD'];encoded=np.zeros_like(force)
            for index in np.flatnonzero(np.any(force!=0,axis=1)):
                for axis,value in enumerate(force[index]):
                    if value:
                        token=module.ccx_field(value);lines.append(f'{index+1},{axis+1},{token}');encoded[index,axis]=float(token)
            lines += ['*NODE PRINT,NSET=ALLN','U','*NODE PRINT,NSET=FIXED','RF','*EL PRINT,ELSET=BODY','S','*END STEP'];deck=out/(case+'.inp');deck.write_text('\n'.join(lines)+'\n');np.savez_compressed(out/(case+'-loads.npz'),force=encoded)
            target=np.array([*config['load_cases'][case]['force_N'],*config['load_cases'][case]['moment_Nmm']],dtype=float);actual=np.r_[encoded.sum(axis=0),np.cross(points,encoded).sum(axis=0)];scale=max(1.,float(abs(target[:3]).max()));moment_scale=max(1.,float(abs(target[3:]).max()),300*scale)
            if abs(actual[:3]-target[:3]).max()>1e-8*scale or abs(actual[3:]-target[3:]).max()>1e-8*moment_scale:raise ValueError('Encoded consistent load wrench refused')
            loads[case]=dict(requested=config['load_cases'][case],actual_force_N=actual[:3].tolist(),actual_moment_Nmm=actual[3:].tolist(),wrench_residual=(actual-target).tolist(),per_bore_constant_traction_N_per_mm2=[r.tolist()for r in field[case]],nonzero_force_nodes=int(np.any(encoded!=0,axis=1).sum()),deck_sha256=sha(deck))
        result=dict(status='matched_consistent_traction_inputs_prepared_not_solved',order=order,nodes=len(points),elements=len(connectivity),material=material,fixture='Both nominal end-bore patches fixed; consistently integrated constant vector traction on each of four central bore patches',load_model_changed_from_dead_node_study=True,constant_traction_shape_integrals='P1: area/3 on corner nodes. P2: zero on corners, area/3 on the three edge midpoint nodes.',traction_selection='Minimum surface-L2 norm over four constant vector tractions, subject to six resultant components',radial_selection_band_mm=tol,inward_normal_alignment_minimum=.9,traction_system_condition=float(np.linalg.cond(H)),bore_patches=details,bore_group_nodes={name:len(value)for name,value in nodes.items()},loads=loads,source_sha256={str(p):sha(p)for p in [a.study,a.mapping_proof,a.geometry/'assessment.json',Path(__file__)]},output_sha256={p.name:sha(p)for p in out.iterdir()if p.is_file()},stress_convergence_demonstrated=False,geometry_adopted=False)
        (out/'assessment.json').write_text(json.dumps(result,indent=2)+'\n');reports[order]=dict(nodes=len(points),elements=len(connectivity),load_node_counts={k:r['nonzero_force_nodes']for k,r in loads.items()})
    (a.output/'assessment.json').write_text(json.dumps(dict(status='matched_P1_P2_consistent_traction_cases_prepared',orders=reports),indent=2)+'\n');print(json.dumps(reports))

if __name__=='__main__':main()
