"""Read native boundary topology, ownership, defect sets and geometric centres."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,closed_boundary_topology
from audit_diagnostic import ascii_list
from audit_frame_interface_v2 import cell_flags
from run_case import ascii_faces
case=Path('work/bionic-airflow-20261012/baseline-profile-mesh-031');mesh=case/'constant/polyMesh'
manifest=json.loads((case/'case-manifest.json').read_text());receipt=json.loads((case/'run-mesh.json').read_text())
assert receipt['case_manifest_sha256']==sha(case/'case-manifest.json')
assert all(sha(case/n)==h for n,h in receipt['output_sha256'].items())
centres_receipt=json.loads((case/'write-centres-receipt.json').read_text());assert centres_receipt['native_exit_code']==0
assert sha(case/'0/C')==centres_receipt['outputs']['0/C']
x=re.search(r'internalField\s+nonuniform\s+List<vector>\s*(\d+)\s*\((.*?)\)\s*;', (case/'0/C').read_text(),re.S);assert x
centres=np.fromstring(x[2].translate(str.maketrans('()','  ')),sep=' ').reshape(-1,3);assert len(centres)==int(x[1])==718456 and np.isfinite(centres).all()
owner=ascii_list((mesh/'owner').read_text()).astype(np.int64);neighbour=ascii_list((mesh/'neighbour').read_text()).astype(np.int64)
x=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);assert x
zone=np.fromstring(x[2],sep=' ',dtype=np.int64);assert len(zone)==int(x[1])
rotating=cell_flags(owner,neighbour,zone)
interface=np.flatnonzero(rotating[owner[:len(neighbour)]]^rotating[neighbour]);adjacent=np.union1d(owner[interface],neighbour[interface])
patches={};labels={}
for x in re.finditer(r'(\w+)\s*\{([^{}]*)\}',(mesh/'boundary').read_text()):
 count=re.search(r'nFaces\s+(\d+)',x[2]);start=re.search(r'startFace\s+(\d+)',x[2])
 if count and start:
  n,begin=int(count[1]),int(start[1]);patches[x[1]]=dict(faces=n,start=begin);labels.update({i:x[1] for i in range(begin,begin+n)})
text=(mesh/'faces').read_text();topology=closed_boundary_topology((f,labels[i]) for i,f in enumerate(ascii_faces(text)) if i in labels)
patch_cells={name:np.unique(owner[p['start']:p['start']+p['faces']]) for name,p in patches.items()}
results={}
for name,kind in (('concaveCells','cell'),('wrongOrientedFaces','face'),('lowQualityTetFaces','face')):
 p=mesh/'sets'/name;ids=ascii_list(p.read_text()).astype(np.int64);assert len(np.unique(ids))==len(ids)
 cells=ids if kind=='cell' else np.unique(np.r_[owner[ids],neighbour[ids[ids<len(neighbour)]]])
 results[name]=dict(kind=kind,count=len(ids),sha256=sha(p),adjacent_cells=len(cells),cells_touching_interface=len(np.intersect1d(cells,adjacent)),touching_patches={n:len(np.intersect1d(cells,v)) for n,v in patch_cells.items()},cell_centre_bounds_m=[centres[cells].min(axis=0).tolist(),centres[cells].max(axis=0).tolist()])
 if kind=='face':results[name]['face_labels']=ids.tolist();results[name]['cell_labels']=cells.tolist()
record=dict(source_sha256=sha(Path(__file__)),native_centres_sha256=sha(case/'0/C'),all_original_payloads_read_and_hashed=True,mesh_cells=len(centres),native_boundary_topology=topology,source_boundary_topology=manifest['surface']['boundary_topology'],patches=patches,rotor_owners_outside_zone=int(np.count_nonzero(~rotating[owner[patches['rotor']['start']:patches['rotor']['start']+patches['rotor']['faces']]])),port_owners_inside_zone={n:int(np.count_nonzero(rotating[patch_cells[n]])) for n in ('inlet','outlet')},defects=results,performance_ranking_authorized=False)
with Path(__file__).with_name('localization-031.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(record,indent=2))
