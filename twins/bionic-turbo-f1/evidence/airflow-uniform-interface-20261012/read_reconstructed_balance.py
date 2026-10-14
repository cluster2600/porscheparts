"""Read native meshes and fields; distinguish interface tangency from cell balance."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from audit_frame_interface import face_geometry
from uniform_interface_projection import read_mesh,metrics


def cell_balance(points,faces,owner,neighbour,omega,rotating=None):
    count=int(max(owner.max(),neighbour.max(initial=-1)))+1;balance=np.zeros(count);worst_warp=0.
    for i,face in enumerate(faces):
        p=points[list(face)];c,s=face_geometry(p);q=float(np.dot(np.cross([0,0,omega],c),s));balance[owner[i]]+=q
        if i<len(neighbour):balance[neighbour[i]]-=q
        worst_warp=max(worst_warp,float(np.max(np.abs((p-p[0])@(s/np.linalg.norm(s))))))
    selected=np.arange(count) if rotating is None else np.asarray(rotating,dtype=int)
    return dict(max_abs_selected_cell_geometric_frame_flux_m3_s=float(np.abs(balance[selected]).max()),worst_selected_cell=int(selected[np.abs(balance[selected]).argmax()]),cells=count,max_abs_cell_geometric_frame_flux_m3_s=float(np.abs(balance).max()),worst_cell=int(np.abs(balance).argmax()),max_face_plane_distance_m=worst_warp)


# A planar cube has zero net flux for rigid rotation, independently of translation.
cube=np.array([[x,y,z] for z in (0,1) for y in (0,1) for x in (0,1)],float)+[3,4,5]
faces=[[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]]
assert cell_balance(cube,faces,np.zeros(6,dtype=int),np.array([],dtype=int),2)['max_abs_cell_geometric_frame_flux_m3_s']<1e-12
root=Path('work/bionic-airflow-20261012');results=[]
for name in ('reconstructed-interface-038',):
    case=root/name;receipt=json.loads((case/'report.json').read_text());assert receipt['native_exit_code']==0
    assert receipt['manifest_sha256']==sha(case/'manifest.json')
    assert all(sha(case/n)==h for n,h in receipt['output_sha256'].items())
    p,faces,selected,internal=read_mesh(case);mesh=case/'constant/polyMesh'
    owner=ascii_list((mesh/'owner').read_text()).astype(int);neighbour=ascii_list((mesh/'neighbour').read_text()).astype(int)
    match=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);assert match
    zone=np.fromstring(match[2],sep=' ',dtype=int);assert len(zone)==int(match[1])
    r=cell_balance(p,faces,owner,neighbour,10471.975511966,zone)
    r['selected_cells_are_rotating']=True
    r.update(case=name,receipt_sha256=sha(case/'report.json'),interface=metrics(p,[faces[i] for i in selected],10471.975511966),all_native_payloads_verified=True)
    if name.endswith('036'):
        fields={}
        for field,components in (('p',1),('T',1),('U',3)):
            path=case/'2e-05'/field;text=path.read_text();m=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S);assert m and int(m[2])==r['cells']
            a=np.fromstring(m[3].translate(str.maketrans('()','  ')),sep=' ');assert a.size==r['cells']*components and np.isfinite(a).all();a=a.reshape(-1,components)
            fields[field]=dict(sha256=sha(path),cells=len(a),minimum=a.min(axis=0).tolist(),maximum=a.max(axis=0).tolist(),max_magnitude=float(np.linalg.norm(a,axis=1).max()))
        r['native_final_fields']=fields
    results.append(r)
report=dict(source_sha256=sha(Path(__file__)),polygon_source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/audit_frame_interface.py')),results=results,interpretation='Geometric diagnostic only, not physical mass flow. Correlation of warped interior faces and rest drift does not alone prove a unique cause.',performance_ranking_authorized=False)
with Path(__file__).with_name('reconstructed-balance.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
