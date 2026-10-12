"""Verify collar topology, native rejection labels and polygon frame balance."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh,metrics
from audit_diagnostic import ascii_list
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'reconstructed-interface-038';case=root/'protected-axial-056'
for c in (parent,case):
 r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==0 and all(sha(c/n)==h for n,h in r['output_sha256'].items())
 assert sha(c/'manifest.json')==r['manifest_sha256'] and sha(c/'execution.json')==r['execution_sha256']
p,oldfaces,oldinterface,oldinternal=read_mesh(parent);q,faces,interface,internal=read_mesh(case)
mesh=case/'constant/polyMesh';owner=ascii_list((mesh/'owner').read_text()).astype(int);neighbour=ascii_list((mesh/'neighbour').read_text()).astype(int)
parents=ascii_list((case/'0/polyMesh/cellMap').read_text()).astype(int);selection=json.loads((case/'selection.json').read_text())
assert len(parents)==30720 and parents.min()==0 and parents.max()==20479
expected=np.ones(20480,int);expected[selection['selected_cells']]=2
assert np.array_equal(np.bincount(parents,minlength=20480),expected)
assert len(q)==47360 and len(faces)==108544 and len(interface)==5120
# Native writePrecision 16 may round original 17-digit coordinates; report it explicitly.
point_error=float(np.abs(q[:len(p)]-p).max());assert point_error<1e-17
key=lambda face:tuple(sorted(map(int,face)))
assert {key(faces[i]) for i in interface}=={key(oldfaces[i]) for i in oldinterface}
protected=set(selection['protected_cells']);assert set(parents[np.r_[owner[interface],neighbour[interface]]])==protected
centres=np.empty((len(faces),3));areas=centres.copy();warp=np.empty(len(faces))
for width in sorted(set(map(len,faces))):
 ids=np.array([i for i,f in enumerate(faces) if len(f)==width]);verts=np.array([faces[i] for i in ids]);c,s,d=geometry(q[verts]);centres[ids]=c;areas[ids]=s;warp[ids]=d
omega=10471.975511966;flux=np.einsum('ij,ij->i',np.cross([0,0,omega],centres),areas)
count=len(parents);net=np.bincount(owner,weights=flux,minlength=count)-np.bincount(neighbour,weights=flux[:internal],minlength=count)
volume=np.einsum('ij,ij->i',centres,areas)/3;vol=np.bincount(owner,weights=volume,minlength=count)-np.bincount(neighbour,weights=volume[:internal],minlength=count)
match=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);assert match
zone=np.fromstring(match[2],sep=' ',dtype=int);assert len(zone)==int(match[1])
labels={name:ascii_list((mesh/'sets'/name).read_text()).astype(int) for name in ('concaveCells','underdeterminedCells')}
assert len(labels['concaveCells'])==10240 and len(labels['underdeterminedCells'])==5888
cell_faces=[[] for _ in parents]
for i,o in enumerate(owner):cell_faces[o].append(i)
for i,n in enumerate(neighbour):cell_faces[n].append(i)
predicted=[];scores=[]
for cell,ids in enumerate(cell_faces):
 ids=np.array(ids);c=centres[ids];n=areas[ids]/np.linalg.norm(areas[ids],axis=1)[:,None];n*=np.where(owner[ids]==cell,1,-1)[:,None]
 delta=c[None,:,:]-c[:,None,:];length=np.linalg.norm(delta,axis=2);dots=np.einsum('ijk,ik->ij',delta,n)/np.maximum(length,1e-300);np.fill_diagonal(dots,-1)
 score=float(dots.max());scores.append(score)
 if score> -1e-6:predicted.append(cell)
assert set(predicted)==set(labels['concaveCells'])
classes={name:dict(cells=len(ids),protected_parent_cells=int(np.isin(parents[ids],selection['protected_cells']).sum()),selected_parent_cells=int(np.isin(parents[ids],selection['selected_cells']).sum())) for name,ids in labels.items()}
result=dict(reader_sha256=sha(Path(__file__)),all_payloads_verified=True,parent_cells=20480,cells=count,rotating_cells=len(zone),faces=len(faces),native_parent_map_verified=True,protected_parent_count=len(protected),selected_parent_count=len(selection['selected_cells']),original_point_serialization_max_component_change_m=point_error,interface_topology_unchanged=True,interface=metrics(q,[faces[i] for i in interface],omega),max_face_warp_m=float(warp.max()),max_rotating_cell_geometric_frame_flux_m3_s=float(abs(net[zone]).max()),minimum_oriented_cell_volume_m3=float(vol.min()),boundary_volume_m3=float(volume[internal:].sum()),native_concavity_labels_reproduced=True,concavity_score_range=[min(np.array(scores)[labels['concaveCells']]),max(np.array(scores)[labels['concaveCells']])],rejected_classes=classes,mesh_admitted=False,solver_launched=False,performance_ranking_authorized=False)
with (w/'readback.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
