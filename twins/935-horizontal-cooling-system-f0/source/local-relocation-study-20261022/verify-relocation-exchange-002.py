"""Check every exchanged relocated coordinate/triangle without changing the proposal."""
import json
import struct
from pathlib import Path

import numpy as np
import trimesh
from prepare_conforming_surface import load_surface
from run_reconstruction import ROOT, sha
from stl_moments import DTYPE

phase=ROOT/'work/935-local-relocation-20261022';out=phase/'candidate-001';proof=json.loads((out/'proposal.json').read_text())
for name,expected in proof['output_sha256'].items():assert sha(out/name)==expected
surface=trimesh.load_mesh(out/'candidate.off',process=False)
with np.load(out/'candidate.npz') as z:vertices,faces=z['vertices'],z['faces']
assert np.array_equal(np.asarray(surface.vertices),vertices.astype(float)) and np.array_equal(np.asarray(surface.faces),faces)
source=ROOT/'work/935-surface-facet-repair-20261022/accepted-005/candidate.npz';assert sha(source)==proof['input_sha256']
with np.load(source) as z:reference,reference_faces=z['vertices'],z['faces']
assert np.array_equal(faces,reference_faces) and len(np.unique(vertices,axis=0))==len(vertices)
changed=np.flatnonzero(np.any(vertices!=reference,axis=1));assert set(map(int,changed))=={m['vertex'] for m in proof['moves']}
t=vertices[faces].astype(float);normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);area=np.linalg.norm(normal,axis=1);assert np.all(area>0)
records=np.zeros(len(faces),dtype=DTYPE);records['vertices']=vertices[faces];records['normal']=normal/area[:,None]
assert sha(out/'candidate.stl')=='0c5686e33a3df6f3586bc2e6bbb0c5b3b59cfa92a0756a162159ad0ec9c83d8d'
with (phase/'exchange-STL-replay-002.stl').open('xb') as stream:stream.write(b'935 tangential analysis proposal; scale unverified'.ljust(80,b'\0'));stream.write(struct.pack('<I',len(records)));stream.write(records.tobytes())
bundle=phase/'exchange-002';bundle.mkdir(mode=0o700)
assert np.array_equal(faces,faces.astype(np.int32).astype(np.int64))
np.savez_compressed(bundle/'candidate.npz',vertices=vertices.astype(np.float32),faces=faces.astype(np.int32))
load_surface(bundle/'candidate.npz',sha(bundle/'candidate.npz'),out/'candidate.stl',sha(out/'candidate.stl'))
bounds=json.loads((phase/'bounds-001/assessment.json').read_text());assert bounds['complete_surface_bound_established'] and bounds['inputs_sha256']['/home/lolman/935-local-relocation-20261022/candidate-001/candidate.off']==sha(out/'candidate.off')
assert sha(phase/'exchange-STL-replay-002.stl')==sha(out/'candidate.stl')
result={'normalized_bundle_sha256':sha(bundle/'candidate.npz'),'complete_bounds_sha256':sha(phase/'bounds-001/assessment.json'),'initial_int64_bundle_refused':True,'status':'complete_OFF_NPZ_STL_coordinate_triangle_readback_passed','source_sha256':sha(__file__),'proposal_sha256':sha(out/'proposal.json'),'original_input_sha256':sha(source),'all_face_indices_unchanged':True,'all_original_vertex_ids_retained':True,'changed_vertices':len(changed),'unique_vertices':len(vertices),'triangles':len(faces),'topological_connectivity_identical_to_certified_input':True,'output_sha256':{name:sha(out/name) for name in ['candidate.off','candidate.npz','candidate.stl']},'Trimesh_version':trimesh.__version__,'complete_surface_bound_established':True,'CFD_accepted':False,'manufacturing_authorized':False}
with (phase/'exchange-002.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result),flush=True)
