#!/usr/bin/env python3
"""Sample cfMesh wall-face vertex means against the rotor input triangles."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576),b''): h.update(block)
    return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('centres',type=Path); p.add_argument('rotor',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
if a.output.exists(): raise SystemExit('output exists')
if sha(a.centres)!='fd93d57463e616e3b1940ecf9ff8d7931c0db17fcdd95e01a258e245a0ad7954' or sha(a.rotor)!='7d273b6072449c1e9140a995847fc4704990944fbb888d74a6a10a5a3db79091': raise SystemExit('unexpected input hash')
with np.load(a.centres) as d:
    flagged=d['incident']*1000.; wall=d['sampled_wall']*1000.
if flagged.shape!=(257,3) or wall.shape!=(17078,3): raise ValueError('unexpected point counts')
mesh=trimesh.load_mesh(a.rotor,process=False)
if len(mesh.faces)!=878612: raise ValueError('unexpected rotor triangle count')
sample=wall[np.linspace(0,len(wall)-1,2048,dtype=int)]
def distances(points):
    values=[]
    for start in range(0,len(points),32):
        _, d, _=trimesh.proximity.closest_point(mesh, points[start:start+32]); values.extend(d)
    d=np.asarray(values)
    if not np.isfinite(d).all(): raise ValueError('invalid distances')
    return {'count':len(d),'median':float(np.median(d)), 'p95':float(np.percentile(d,95)), 'max':float(d.max()),'over_0p5':int(np.count_nonzero(d>.5)), 'over_1':int(np.count_nonzero(d>1))}
result={'status':'sampled_points_only_not_bidirectional_surface_bound','unit':'uncalibrated_source_unit','centres_sha256':sha(a.centres),'rotor_sha256':sha(a.rotor),'case_to_source_factor':1000,'flagged':distances(flagged),'wall_sample':distances(sample),'physical_scale_verified':False,'cfd_admitted':False}
a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
