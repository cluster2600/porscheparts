"""Verify actual exported coordinates, full topology and independent original-surface bounds."""
import hashlib
import json
import resource
import struct
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from prepare_conforming_surface import load_surface
from stl_moments import DTYPE

p=Path('/home/lolman/935-surface-facet-repair-20261022')
case=p/sys.argv[1];assert case.parent==p and case.name in ['limit-010-002','limit-020-003','limit-020-005']
out=case/'quantized';out.mkdir(mode=0o700)
sha=lambda f:hashlib.file_digest(Path(f).open('rb'),'sha256').hexdigest()
original=Path('/home/lolman/935-native-gpu-20261022/geometry-certification/original.off')
reference=Path('/home/lolman/935-analysis-patches-20261022/surface-001/candidate-quantized.off')
checker=original.parent/'tiled-envelope-linux'
assert sha(original)=='e374fc2f850645efb6db4854a4355f541a9617833b827a6cff52d24929757587' and sha(reference)=='addba09e1ee2d7814f19a3262ac0910f0bc5b9d58dd43ada3254444845392e5a' and sha(checker)=='a64afa7238ab1b28064412142701473a94ba869089d20cfedfcbe3994ff56430'
proof=json.loads((case/'execution.json').read_text());assert sha(case/'candidate.off')==proof['output_OFF_sha256'] and proof['input_unchanged']
def off(path):
    assert path.stat().st_size<256*1024**2
    with path.open() as s:
        assert s.readline().strip()=='OFF'
        nv,nf,_=map(int,s.readline().split());assert 4<=nv<=2_000_000 and 4<=nf<=4_000_000
        v=np.loadtxt(s,max_rows=nv,ndmin=2);f=np.loadtxt(s,dtype=np.int64,ndmin=2)
    assert v.shape==(nv,3) and f.shape==(nf,4) and np.all(f[:,0]==3) and np.isfinite(v).all() and f[:,1:].min()>=0 and f[:,1:].max()<nv
    return v,f[:,1:]
v,f=off(case/'candidate.off');rv,rf=off(reference);v32=v.astype(np.float32);f32=f.astype(np.int32)
assert np.isfinite(v32).all() and len(np.unique(v32,axis=0))==len(v32)
all_points_from_reference=len(np.unique(np.vstack([rv,v]),axis=0))==len(rv)
quantized_shift=float(np.linalg.norm(v-v32.astype(float),axis=1).max())
np.savez_compressed(out/'candidate.npz',vertices=v32,faces=f32)
with (out/'candidate-quantized.off').open('x') as s:
    s.write(f'OFF\n{len(v32)} {len(f32)} 0\n');np.savetxt(s,v32,fmt='%.17g');np.savetxt(s,np.column_stack([np.full(len(f32),3),f32]),fmt='%d')
tri=v32[f32].astype(float);normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);twice_area=np.linalg.norm(normal,axis=1);assert np.all(twice_area>0)
records=np.zeros(len(f32),dtype=DTYPE);records['vertices']=v32[f32];records['normal']=normal/twice_area[:,None]
with (out/'candidate.stl').open('xb') as s:s.write(b'935 bounded local facet repair study'.ljust(80,b'\0'));s.write(struct.pack('<I',len(records)));s.write(records.tobytes())
load_surface(out/'candidate.npz',sha(out/'candidate.npz'),out/'candidate.stl',sha(out/'candidate.stl'))
edges=f32[:,[[0,1],[1,2],[2,0]]].reshape(-1,2);canonical=np.sort(edges,axis=1);unique,inverse,counts=np.unique(canonical,axis=0,return_inverse=True,return_counts=True);orient=np.bincount(inverse,weights=np.where(edges[:,0]<edges[:,1],1.,-1.));assert np.all(counts==2) and np.all(orient==0)
graph=coo_matrix((np.ones(len(unique),dtype=np.int8),(unique[:,0],unique[:,1])),shape=(len(v32),len(v32))).tocsr();nc=connected_components(graph,directed=False,return_labels=False);chi=len(v32)-len(unique)+len(f32);assert nc==1 and chi==-10
lengths=np.linalg.norm(tri[:,[1,2,0]]-tri,axis=2);q=2*np.sqrt(3)*twice_area/(lengths**2).sum(axis=1)
report={'source_sha256':sha(__file__),'candidate_execution_sha256':sha(case/'execution.json'),'input_OFF_sha256':sha(case/'candidate.off'),'reference_OFF_sha256':sha(reference),'original_PicoGK_OFF_sha256':sha(original),'checker_sha256':sha(checker),'vertices':len(v32),'triangles':len(f32),'candidate_vertices_are_reference_subset':all_points_from_reference,'maximum_float32_shift_native_units':quantized_shift,'complete_STL_bundle_coordinate_and_triangle_readback':True,'Euler_characteristic':chi,'connected_components':int(nc),'every_edge_has_two_oppositely_oriented_incident_faces':True,'poor_triangles_below_0_05':int((q<.05).sum()),'minimum_triangle_quality':float(q.min()),'minimum_edge_native_units':float(lengths.min()),'volume_native_units_cubed':float(np.einsum('ij,ij->i',tri[:,0],np.cross(tri[:,1],tri[:,2])).sum()/6),'output_sha256':{name:sha(out/name) for name in ['candidate.npz','candidate.stl','candidate-quantized.off']},'steps':[],'complete_surface_bound_established':False,'scale_verified':False,'CFD_accepted':False,'manufacturing_authorized':False}
assert np.isfinite(report['volume_native_units_cubed']) and report['volume_native_units_cubed']>0
report['helper_sha256']={name:sha(Path(sys.modules[name].__file__)) for name in ['prepare_conforming_surface','stl_moments']}
report['NumPy_version']=np.__version__
def save():(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
def run(name,args,seconds):
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))
    started=time.monotonic()
    with (out/(name+'.stdout')).open('x') as stdout,(out/(name+'.stderr')).open('x') as stderr:
        result=subprocess.run(['timeout','--signal=TERM','--kill-after=10s',str(seconds)+'s',str(checker),*map(str,args)],stdout=stdout,stderr=stderr,timeout=seconds+20,preexec_fn=limits)
    report['steps'].append({'name':name,'command':[str(checker),*map(str,args)],'exit':result.returncode,'elapsed_s':time.monotonic()-started,'timeout_s':seconds,'memory_limit_GiB':4});save();assert result.returncode==0
run('checker-controls',['--self-test'],30)
for name,input_path in [('original-bound',original),('reference-bound',reference)]:
    run(name,[input_path,out/'candidate-quantized.off'],900)
    certificate=json.loads((out/(name+'.stdout')).read_text());assert certificate['source_to_candidate_contained'] and certificate['candidate_to_source_contained'] and certificate['complete_containment_pass'] and certificate['topology_and_self_intersection_checks_pass'] and certificate['envelope_bound_native_units']==.0225 and certificate['reserved_numeric_margin_native_units']==.0025
    report[name]=certificate;save()
assert sha(checker)==report['checker_sha256'] and sha(case/'candidate.off')==report['input_OFF_sha256'] and sha(original)==report['original_PicoGK_OFF_sha256'] and sha(reference)==report['reference_OFF_sha256']
report.update(status='quantized_candidate_full_topology_readback_and_both_independent_bounds_passed',complete_surface_bound_established=True);save();print(json.dumps(report),flush=True)
