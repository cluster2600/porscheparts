"""Independent native-connectivity proof for the extracted coarse sector."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh
from audit_diagnostic import ascii_list
from run_case import ascii_faces
root=Path('work/bionic-airflow-20261012');parent=root/'projected-interface-035';case=root/'directed-sector-042';p,f,_,old_internal=read_mesh(parent);mesh=case/'input/base-polyMesh'
r=json.loads((case/'report.json').read_text());assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
q=ascii_list((mesh/'points').read_text(),True);faces=list(ascii_faces((mesh/'faces').read_text()));owner=ascii_list((mesh/'owner').read_text()).astype(int);nei=ascii_list((mesh/'neighbour').read_text()).astype(int)
lookup={tuple(v):i for i,v in enumerate(p)};ids=[lookup[tuple(v)] for v in q];oldfaces={tuple(sorted(face)):i for i,face in enumerate(f)};mapped=[oldfaces[tuple(sorted(ids[v] for v in face))] for face in faces]
sourceowner=ascii_list((parent/'constant/polyMesh/owner').read_text()).astype(int);sourcenei=ascii_list((parent/'constant/polyMesh/neighbour').read_text()).astype(int)
sets=[set() for _ in range(int(sourceowner.max())+1)]
for i,face in enumerate(f):
 sets[sourceowner[i]].update(face)
 if i<len(sourcenei):sets[sourcenei[i]].update(face)
cellmap={tuple(sorted(v)):i for i,v in enumerate(sets)};newsets=[set() for _ in range(int(owner.max())+1)]
for i,face in enumerate(faces):
 newsets[owner[i]].update(ids[v] for v in face)
 if i<len(nei):newsets[nei[i]].update(ids[v] for v in face)
mapped_cells=[cellmap[tuple(sorted(v))] for v in newsets];assert len(set(mapped_cells))==160
result=dict(source_sha256=sha(Path(__file__)),parent_receipt_sha256=sha(parent/'report.json'),sector_receipt_sha256=sha(case/'report.json'),points_exact_native_subset=len(ids),base_faces_exact_native_subset=len(mapped),base_cells_exact_native_subset=len(mapped_cells),source_cell_labels=mapped_cells,boundary_faces_from_original_walls=sum(i>=old_internal for i in mapped[len(nei):]),boundary_faces_new_synthetic_angular_cuts=sum(i<old_internal for i in mapped[len(nei):]),scope='Exact subset geometry and connectivity; cut faces become synthetic stationary walls, so this is not the full annulus or turbo.')
with Path(__file__).with_name('extraction-proof.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='source_cell_labels'}))
