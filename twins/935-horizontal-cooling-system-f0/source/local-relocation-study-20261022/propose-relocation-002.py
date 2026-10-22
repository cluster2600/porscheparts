"""Try one smaller tangential pass on the seven remaining analysis facets."""
import json
import signal
import struct
import sys

import numpy as np
from run_reconstruction import ROOT, sha
from prepare_conforming_surface import load_surface
from stl_moments import DTYPE

signal.alarm(180)
sys.path.insert(0,str(ROOT/'twins/935-horizontal-cooling-system-f0/source/local-relocation-study-20261022'))
import surface_relocation as local

phase=ROOT/'work/935-local-relocation-20261022';source=phase/'exchange-002/candidate.npz';stl=phase/'candidate-001/candidate.stl'
assert sha(source)=='32f09379a8c33e458781be5a87e3180f4c7af37391e871edd9f05970969d9e07'
assert sha(stl)=='0c5686e33a3df6f3586bc2e6bbb0c5b3b59cfa92a0756a162159ad0ec9c83d8d'
assert json.loads((phase/'bounds-001/assessment.json').read_text())['complete_surface_bound_established']
vertices,faces=load_surface(source,sha(source),stl,sha(stl));vertices=vertices.astype(float);points=vertices.copy()
q,_=local.qualities(points[faces]);assert int((q<.05).sum())==7
eligible=np.unique(faces[q<.05]);moves=[]
for vertex in eligible:
    vertex=int(vertex);incident=np.flatnonzero(np.any(faces==vertex,axis=1));patch=faces[incident]
    if local.qualities(points[patch])[0].min()>=.05:continue
    point=local.proposal(points,patch,vertex,.005)
    if point is not None:
        moves.append({'vertex':vertex,'before':points[vertex].tolist(),'after':point.tolist()});points[vertex]=point
new_q,normals=local.qualities(points[faces]);fixed=np.ones(len(points),dtype=bool);fixed[eligible]=False
assert np.array_equal(points[fixed],vertices[fixed]) and np.isfinite(new_q).all() and np.all(new_q>=np.minimum(q,.05)-1e-10)
volume=float(np.einsum('ij,ij->i',points[faces[:,0]],np.cross(points[faces[:,1]],points[faces[:,2]])).sum()/6);assert volume>0
out=phase/'candidate-002';out.mkdir(mode=0o700);v32=points.astype(np.float32)
assert np.array_equal(points,v32.astype(float)) and faces.dtype==np.int32
np.savez_compressed(out/'candidate.npz',vertices=v32,faces=faces)
with (out/'candidate.off').open('x') as stream:
    stream.write('OFF\n%d %d 0\n'%(len(points),len(faces)));np.savetxt(stream,points,fmt='%.17g');np.savetxt(stream,np.column_stack([np.full(len(faces),3),faces]),fmt='%d')
records=np.zeros(len(faces),dtype=DTYPE);records['vertices']=v32[faces];records['normal']=normals/np.linalg.norm(normals,axis=1)[:,None]
with (out/'candidate.stl').open('xb') as stream:stream.write(b'935 bounded local relocation pass 002'.ljust(80,b'\0'));stream.write(struct.pack('<I',len(records)));stream.write(records.tobytes())
load_surface(out/'candidate.npz',sha(out/'candidate.npz'),out/'candidate.stl',sha(out/'candidate.stl'))
record={'status':'smaller_tangential_pass_pending_complete_independent_certificates','source_sha256':sha(__file__),'helper_sha256':sha(local.__file__),'input_npz_sha256':sha(source),'input_STL_sha256':sha(stl),'parent_bounds_sha256':sha(phase/'bounds-001/assessment.json'),'poor_facets_before':7,'poor_facets_after':int((new_q<.05).sum()),'minimum_quality_after':float(new_q.min()),'triangles':len(faces),'vertices':len(points),'eligible_vertices':len(eligible),'moved_vertices':len(moves),'per_move_radius_native_units':.005,'maximum_additional_displacement_native_units':float(np.linalg.norm(points-vertices,axis=1).max()),'volume_native_units_cubed':volume,'complete_STL_NPZ_coordinate_triangle_readback':True,'all_faces_and_fixed_vertices_unchanged':True,'moves':moves,'output_sha256':{name:sha(out/name) for name in ['candidate.npz','candidate.off','candidate.stl']},'complete_surface_bound_established':False,'CFD_accepted':False,'manufacturing_authorized':False}
with (out/'proposal.json').open('x') as stream:json.dump(record,stream,indent=2)
print(json.dumps({k:v for k,v in record.items() if k!='moves'}),flush=True)
