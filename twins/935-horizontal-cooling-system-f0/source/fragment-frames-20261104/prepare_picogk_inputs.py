#!/usr/bin/env python3
"""Prepare binary STL copies of a private normalized scan and open fragments."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import trimesh


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('scan',type=Path); p.add_argument('shaft',type=Path); p.add_argument('support',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
root=Path(__file__).resolve().parents[4]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('use fresh private work output')
expected=('fafb45129e8d5b09bb7971f2f2a5c6cdcd4c645c4a4f2a9fe10fd039f809c085','73045fcb66e638e542c884fac619fd8cf6b49ff480f9d9b2331b7d5df3314bae','f55a6ec4d3c2fbf2feb60b596a360f2836b3d73ac244afd352e742b8b3caac1c')
if tuple(sha(x) for x in (a.scan,a.shaft,a.support))!=expected: raise ValueError('input hash mismatch')
with np.load(a.scan) as d: scan=trimesh.Trimesh(vertices=d['vertices'],faces=d['faces'],process=False)
meshes=[scan,trimesh.load_mesh(a.shaft,process=False),trimesh.load_mesh(a.support,process=False)]
if [len(m.faces) for m in meshes]!=[2484656,2112,94]: raise ValueError('unexpected triangle count')
a.output.mkdir(mode=0o700,parents=True); rows=[]
for mesh,name in zip(meshes,('drive.stl','shaft.stl','support.stl')):
    path=a.output/name; mesh.export(path,file_type='stl'); reread=trimesh.load_mesh(path,process=False)
    if len(mesh.faces)!=len(reread.faces) or not np.array_equal(mesh.triangles.astype(np.float32),reread.triangles.astype(np.float32)): raise ValueError('triangle float32 reread failed')
    rows.append({'file':name,'triangles':len(mesh.faces),'sha256':sha(path)})
(a.output/'receipt.json').write_text(json.dumps({'status':'binary_stl_float32_triangle_readback','source_sha256':expected,'outputs':rows,'scale_verified':False,'manufacturing_authorized':False},indent=2)+'\n')
print(json.dumps(rows))
