"""Read-only localization of the native failed cell set; no acceptance changes."""
from pathlib import Path
import hashlib, json, re
import numpy as np

case=Path(__file__).parent
mesh=case/'constant/polyMesh'
paths=['owner','neighbour','cellLevel','sets/concaveCells','boundary']
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
hashes={name:sha(mesh/name) for name in paths}
def labels(name):
    raw=(mesh/name).read_text()
    if not re.search(r'\bformat\s+ascii\s*;',raw): raise ValueError('ASCII required')
    raw=re.sub(r'/\*.*?\*/|//[^\n]*','',raw,flags=re.S)
    m=re.search(r'\}\s*(\d+)\s*\((.*?)\)\s*$',raw,re.S)
    if not m: raise ValueError('Invalid label list')
    a=np.fromstring(m[2],dtype=np.int64,sep=' ')
    if len(a)!=int(m[1]): raise ValueError('Count mismatch')
    return a
owner=labels('owner'); neighbour=labels('neighbour'); levels=labels('cellLevel'); flagged=labels('sets/concaveCells')
if len(np.unique(flagged))!=len(flagged): raise ValueError('Duplicate native IDs')
is_boundary=np.isin(flagged,owner[len(neighbour):])
transition=levels[owner[:len(neighbour)]]!=levels[neighbour]
transition_ids=np.unique(np.concatenate((owner[:len(neighbour)][transition],neighbour[transition])))
is_transition=np.isin(flagged,transition_ids)
patch_counts={}
boundary=(mesh/'boundary').read_text()
for name in ('inlet','outlet','rotor','stator'):
    b=re.search(r'\b'+name+r'\s*\{([^{}]+)\}',boundary,re.S)[1]
    start=int(re.search(r'startFace\s+(\d+)',b)[1]); count=int(re.search(r'nFaces\s+(\d+)',b)[1])
    patch_counts[name]=int(np.isin(flagged,owner[start:start+count]).sum())
result={'status':'diagnostic_only','mesh_gate_changed':False,'native_concave_cells':len(flagged),
    'native_cell_set_sha256':hashes['sets/concaveCells'],'input_sha256':hashes,'script_sha256':sha(Path(__file__)),
    'boundary_adjacent':int(is_boundary.sum()),'refinement_transition_adjacent':int(is_transition.sum()),
    'both_boundary_and_transition':int((is_boundary&is_transition).sum()),
    'neither_boundary_nor_transition':int((~is_boundary&~is_transition).sum()),
    'boundary_patch_adjacent_counts':patch_counts,
    'refinement_level_counts':{str(int(v)):int((levels[flagged]==v).sum()) for v in np.unique(levels[flagged])},
    'limitations':['Adjacency localization of the native set, not a new convexity calculation.',
                   'Boundary and transition categories may overlap. No geometric repair or solver run.']}
for name,value in hashes.items():
    if sha(mesh/name)!=value: raise ValueError('Input changed')
with (case/'concave-cell-localization.json').open('x') as f: json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
