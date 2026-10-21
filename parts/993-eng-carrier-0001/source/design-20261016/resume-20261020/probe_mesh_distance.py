"""Diagnostic point distances only; this worker never admits a surface."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--first',type=Path,required=True);p.add_argument('--second',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    import igl
    def read(path):
        with path.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
        if v.shape!=(nv,3)or f.shape!=(nf,3):raise ValueError('Whole rosters differ')
        return v,f
    target_v,target_f=read(a.first);v,f=read(a.second);tree=igl.AABB();tree.init(target_v,target_f);rows=[]
    for kind,points in [('vertex',v),('face_centroid',v[f].mean(axis=1))]:
        squared,ids,closest=tree.squared_distance(target_v,target_f,points);index=int(np.argmax(squared));rows.append(dict(kind=kind,source_index=index,observed_distance_mm=float(np.sqrt(squared[index])),approximate_point_xyz_mm=points[index].tolist(),closest_target_triangle=int(ids[index]),approximate_closest_point_xyz_mm=closest[index].tolist(),tested_points=len(points)))
    report=dict(status='finite_point_distance_diagnostic_only',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.first,a.second,Path(__file__)]},probes=rows,complete_surface_distance_certified=False,exact_lower_bound_certified=False,geometry_adopted=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
