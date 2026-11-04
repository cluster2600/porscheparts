#!/usr/bin/env python3
"""Sample input triangle centres against OpenFOAM triangulated rotor wall."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('rotor',type=Path); p.add_argument('wall',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
if a.output.exists(): raise SystemExit('output exists')
if sha(a.rotor)!='7d273b6072449c1e9140a995847fc4704990944fbb888d74a6a10a5a3db79091' or sha(a.wall)!='60f8564a87add660078b8609b09d6bfe6b8e439f146afe02ad6de91457b37f35': raise SystemExit('unexpected input hash')
source=trimesh.load_mesh(a.rotor,process=False); wall=trimesh.load_mesh(a.wall,process=False)
if len(source.faces)!=878612 or len(wall.faces)!=699084: raise ValueError('unexpected triangle count')
ids=np.linspace(0,len(source.faces)-1,4096,dtype=int); points=source.vertices[source.faces[ids]].mean(axis=1)*.001
values=[]
for start in range(0,len(points),32):
    _,d,_=trimesh.proximity.closest_point(wall,points[start:start+32]); values.extend(d*1000.)
d=np.asarray(values)
if not np.isfinite(d).all(): raise ValueError('invalid distances')
result={'status':'sampled_point_distance_to_openfoam_triangulation_not_surface_bound','unit':'uncalibrated_source_unit','rotor_sha256':sha(a.rotor),'wall_sha256':sha(a.wall),'point_count':len(points),'median':float(np.median(d)),'p95':float(np.percentile(d,95)),'max':float(d.max()),'over_0p05':int(np.count_nonzero(d>.05)),'over_0p5':int(np.count_nonzero(d>.5)),'physical_scale_verified':False,'cfd_admitted':False}
a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
