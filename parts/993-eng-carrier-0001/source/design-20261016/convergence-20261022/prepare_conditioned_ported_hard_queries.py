"""Probe the most ill-conditioned real triangles with an independent CPU oracle."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--broad-oracle',type=Path,required=True);p.add_argument('--variant-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--regression-bundle',type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();import numpy as np;import igl
    if importlib.metadata.version('libigl')!='2.6.3':raise ValueError('Pinned independent oracle version required')
    broad=a.broad_oracle/'carrier-queries.npz';report_path=a.broad_oracle/'assessment.json';r=json.loads(report_path.read_text());source=a.variant_directory/'candidate.npz'
    if r['bundle_sha256']!=sha(broad)or r['source_surface_sha256']!=sha(source)or r['fixed_absolute_error_limit_mm']!=.0001:raise ValueError('Broad oracle identity differs')
    z=np.load(broad,allow_pickle=False);v=z['vertices'];f=z['triangles'];native=np.load(source,allow_pickle=False)
    if not np.array_equal(v,native['vertices'].astype(np.float32))or not np.array_equal(f,native['triangles']):raise ValueError('Complete model transport differs')
    def aspect(vertices):
        t=vertices[f];area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1);longest=np.linalg.norm(np.stack([t[:,1]-t[:,0],t[:,2]-t[:,1],t[:,0]-t[:,2]],1),axis=2).max(1)
        if np.any(area<=0):raise ValueError('Collapsed input triangle')
        return longest**2/area
    vd=v.astype(np.float64);native_aspect=aspect(native['vertices']);transport_aspect=aspect(vd);selected=np.unique(np.concatenate([np.argsort(native_aspect,kind='stable')[-128:],np.argsort(transport_aspect,kind='stable')[-128:]]));tri=vd[f[selected]];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None];weights=np.asarray([[1/3,1/3,1/3],[.8,.1,.1],[.1,.8,.1],[.1,.1,.8]]);points=[]
    for weight in weights:
        centre=(tri*weight[None,:,None]).sum(1)
        for offset in [0.,-.00005,.00005,-.0001,.0001,-.001,.001,-.01,.01]:points.append(centre+offset*normal)
    probes=np.vstack(points).astype(np.float32);hard_count=len(probes);groups={'worst_triangle_barycentric_normal_sweeps':[0,hard_count]};regression_sha=None
    if a.regression_bundle is not None:
        previous=np.load(a.regression_bundle,allow_pickle=False)['probes']
        if previous.shape!=(36,3)or previous.dtype!=np.float32:raise ValueError('Frozen 36-position regression corpus required')
        probes=np.vstack([probes,previous]);groups['previous_failure_positions_retargeted_to_current_geometry']=[hard_count,len(probes)];regression_sha=sha(a.regression_bundle)
    if not np.isfinite(probes).all():raise ValueError('Finite hard queries required')
    tree=igl.AABB();ff=f.astype(np.int64);tree.init(vd,ff);squared,_,_=tree.squared_distance(vd,ff,probes.astype(np.float64));expected=np.sqrt(np.maximum(0,np.asarray(squared).reshape(-1)))
    if not np.isfinite(expected).all():raise ValueError('Finite independent distances required')
    bundle=a.output/'carrier-queries.npz';np.savez_compressed(bundle,vertices=v,triangles=f,probes=probes,expected_distances_mm=expected);np.save(a.output/'selected-face-indices.npy',selected);report=dict(status='conditioned_carrier_hard_queries_prepared',source_surface_sha256=sha(source),source_broad_oracle_sha256=sha(broad),source_broad_report_sha256=sha(report_path),vertices=len(v),triangles=len(f),queries=len(probes),selected_triangles=len(selected),selected_face_indices_sha256=sha(a.output/'selected-face-indices.npy'),selection='Union of highest 128 native and float32-promoted aspect ratios; stable deterministic sorting',barycentric_locations=weights.tolist(),normal_offsets_mm=[0.,-.00005,.00005,-.0001,.0001,-.001,.001,-.01,.01],query_groups=groups,regression_bundle_sha256=regression_sha,oracle='libigl 2.6.3 double-precision AABB distances on exact float32-promoted input arrays',oracle_uses_Warp=False,fixed_absolute_error_limit_mm=.0001,source_sha256=sha(Path(__file__)),bundle_sha256=sha(bundle),elapsed_seconds=time.monotonic()-start,geometry_only=True,manufacturing_authorized=False);(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
