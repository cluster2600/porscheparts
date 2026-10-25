"""Build a bounded real-carrier Warp bundle and independent double libigl oracle."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import time


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--surface',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic()
    import numpy as np
    import igl
    raw=gzip.decompress(a.surface.read_bytes())
    if hashlib.sha256(raw).hexdigest()!='396161993b35f708fdd1e527f875aff60daf8c79031dc9a39c42891a9c1ae1a0':raise ValueError('Retained R2 surface identity differs')
    with io.StringIO(raw.decode())as stream:nv,nf=map(int,stream.readline().split());native=np.loadtxt(stream,max_rows=nv);faces=np.loadtxt(stream,dtype=np.int32)
    if native.shape!=(nv,3)or faces.shape!=(nf,3):raise ValueError('Complete surface roster required')
    v=native.astype(np.float32);rng=np.random.default_rng(99327422);t=v[faces[rng.choice(nf,16384,replace=False)]].astype(np.float64);centre=t.mean(1);normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None];random=rng.uniform(v.min(0)-[5,5,5],v.max(0)+[5,5,5],size=(32768,3));offset=centre[:8192]+normal[:8192]*.025;tools=[]
    for x,y in [(-50,-20),(-50,20),(50,-20),(50,20)]:
        theta=rng.uniform(0,2*np.pi,2048);radius=12.5*np.sqrt(rng.uniform(0,1,2048));tools.append(np.column_stack([x+radius*np.cos(theta),y+radius*np.sin(theta),rng.uniform(4,40,2048)]))
    probes=np.vstack([random,centre,offset,*tools]).astype(np.float32)
    if len(probes)!=65536 or not np.isfinite(probes).all():raise ValueError('Bounded finite query roster differs')
    vd=v.astype(np.float64);tree=igl.AABB();tree.init(vd,faces.astype(np.int64));squared,_,_=tree.squared_distance(vd,faces.astype(np.int64),probes.astype(np.float64));expected=np.sqrt(np.maximum(0,np.asarray(squared).reshape(-1)))
    if not np.isfinite(expected).all():raise ValueError('Finite independent oracle required')
    np.savez_compressed(a.output/'carrier-queries.npz',vertices=v,triangles=faces,probes=probes,expected_distances_mm=expected)
    report=dict(status='real_carrier_oracle_prepared',source_surface_sha256=hashlib.sha256(raw).hexdigest(),source_gzip_sha256=sha(a.surface),vertices=nv,triangles=nf,queries=len(probes),query_groups={'random_bounding_box':[0,32768],'surface_centroids':[32768,49152],'normal_offsets':[49152,57344],'nominal_tool_columns':[57344,65536]},seed=99327422,oracle='libigl 2.6.3 double-precision AABB distances on exact float32-promoted input arrays',oracle_uses_Warp=False,fixed_absolute_error_limit_mm=.0001,geometry_only=True,manufacturing_authorized=False,geometry_adopted=False,whole_surface_float32_transport_l1_observed_mm=float(abs(native-v.astype(np.float64)).sum(1).max()),source_sha256=sha(Path(__file__)),bundle_sha256=sha(a.output/'carrier-queries.npz'),elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
