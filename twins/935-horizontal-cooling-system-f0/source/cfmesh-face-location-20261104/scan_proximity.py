#!/usr/bin/env python3
"""Compare incident wall-point scan distances with nearby sampled controls."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576),b''): h.update(block)
    return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('centres',type=Path); p.add_argument('scan',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
if a.output.exists(): raise SystemExit('output exists')
if sha(a.centres) != 'fd93d57463e616e3b1940ecf9ff8d7931c0db17fcdd95e01a258e245a0ad7954' or sha(a.scan) != '452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247':
    raise SystemExit('unexpected centre or aligned-scan input')
with np.load(a.centres) as d:
    targets=d['incident'].astype(float)*1000.; pool=d['sampled_wall'].astype(float)*1000.
with np.load(a.scan) as d:
    scan=trimesh.Trimesh(vertices=d['vertices'],faces=d['faces'],process=False)
if targets.shape!=(257,3) or len(pool)<257 or len(scan.vertices)!=624492 or not np.isfinite(targets).all(): raise ValueError('unexpected inputs')
tree=cKDTree(pool); distances,indices=tree.query(targets,k=64); used=set(); chosen=[]; spacing=[]
for ds,ix in zip(distances,indices):
    for d,j in zip(ds,ix):
        if d>1e-9 and int(j) not in used:
            used.add(int(j)); chosen.append(pool[j]); spacing.append(float(d)); break
    else: raise ValueError('could not find distinct nearby controls')
controls=np.asarray(chosen); _, td, _=trimesh.proximity.closest_point(scan,targets); _, cd, _=trimesh.proximity.closest_point(scan,controls)
def summary(d):
    return {'count':len(d),'median':float(np.median(d)),'p95':float(np.percentile(d,95)), 'max':float(np.max(d)), 'at_most_0p5':int(np.count_nonzero(d<=.5)), 'over_1':int(np.count_nonzero(d>1))}
result={'status':'point_sample_screen_not_provenance_or_whole_surface_bound', 'centres_sha256':sha(a.centres),'aligned_scan_sha256':sha(a.scan),'unit':'uncalibrated_source_unit', 'case_to_source_factor':1000, 'targets':summary(td),'controls':summary(cd),'control_to_target_median':float(np.median(spacing)),'control_to_target_max':float(np.max(spacing)),'scan_registration_verified':False,'scale_verified':False}
a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
