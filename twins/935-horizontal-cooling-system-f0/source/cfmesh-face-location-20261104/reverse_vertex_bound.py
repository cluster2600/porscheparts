#!/usr/bin/env python3
"""Upper-bound sampled rotor-input point distance to the cfMesh wall."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('rotor',type=Path); p.add_argument('wall_vertices',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
if a.output.exists(): raise SystemExit('output exists')
if sha(a.rotor)!='7d273b6072449c1e9140a995847fc4704990944fbb888d74a6a10a5a3db79091' or sha(a.wall_vertices)!='0d7b4fa7d7456670cd22970c3f772be7f8d852c40e55fb6680233dbba22bfef7': raise SystemExit('unexpected input hash')
rotor=trimesh.load_mesh(a.rotor,process=False)
with np.load(a.wall_vertices) as d: wall=d['vertices']*1000.
if len(rotor.faces)!=878612 or wall.shape!=(349542,3) or not np.isfinite(wall).all(): raise ValueError('unexpected inputs')
indices=np.linspace(0,len(rotor.faces)-1,4096,dtype=int)
points=rotor.vertices[rotor.faces[indices]].mean(axis=1)
d=cKDTree(wall).query(points,workers=1)[0]
if not np.isfinite(d).all(): raise ValueError('nonfinite distance')
result={'status':'input_sample_nearest_wall_vertex_upper_bound_only','unit':'uncalibrated_source_unit','input_sha256':sha(a.rotor),'wall_vertices_sha256':sha(a.wall_vertices),'case_to_source_factor':1000,'point_count':len(points),'wall_vertex_count':len(wall),'median':float(np.median(d)),'p95':float(np.percentile(d,95)),'max':float(d.max()),'over_0p5':int(np.count_nonzero(d>.5)),'over_1':int(np.count_nonzero(d>1)),'physical_scale_verified':False,'cfd_admitted':False}
a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
