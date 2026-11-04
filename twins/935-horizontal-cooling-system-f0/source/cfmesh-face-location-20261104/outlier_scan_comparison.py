#!/usr/bin/env python3
"""Compare three sampled input and wall locations with the aligned scan."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('outliers',type=Path); p.add_argument('scan',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
if a.output.exists(): raise SystemExit('output exists')
if sha(a.outliers)!='8436da55838c6e3963dfd397c4e8edf9f0d310fe38af138b25d89d33ab7cc59f' or sha(a.scan)!='452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247': raise SystemExit('unexpected input hash')
with np.load(a.outliers) as f:
    source=f['points']; wall=f['nearest']; stored=f['distances']
with np.load(a.scan) as f:
    scan=trimesh.Trimesh(vertices=f['vertices'],faces=f['faces'],process=False)
if source.shape!=(3,3) or wall.shape!=(3,3) or not np.allclose(np.linalg.norm(source-wall,axis=1),stored,rtol=1e-10,atol=1e-10): raise ValueError('inconsistent points')
_,sd,_=trimesh.proximity.closest_point(scan,source); _,wd,_=trimesh.proximity.closest_point(scan,wall)
if not np.isfinite(sd).all() or not np.isfinite(wd).all(): raise ValueError('nonfinite distances')
result={'status':'point_distances_not_surface_identity_or_causal_proof','unit':'uncalibrated_source_unit','outliers_sha256':sha(a.outliers),'aligned_scan_sha256':sha(a.scan),'points':[{'input_to_wall':float(g),'input_to_scan':float(s),'wall_to_scan':float(w)} for g,s,w in zip(stored,sd,wd)],'physical_registration_verified':False,'physical_scale_verified':False}
a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
