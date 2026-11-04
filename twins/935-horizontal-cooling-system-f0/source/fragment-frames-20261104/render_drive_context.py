#!/usr/bin/env python3
"""Review the placed open CAD fragments against the same normalized scan."""
import argparse, hashlib, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('scan',type=Path); p.add_argument('shaft',type=Path); p.add_argument('support',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
root=Path(__file__).resolve().parents[4]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('use fresh private work output')
expected=('fafb45129e8d5b09bb7971f2f2a5c6cdcd4c645c4a4f2a9fe10fd039f809c085','73045fcb66e638e542c884fac619fd8cf6b49ff480f9d9b2331b7d5df3314bae','f55a6ec4d3c2fbf2feb60b596a360f2836b3d73ac244afd352e742b8b3caac1c')
if tuple(sha(x) for x in (a.scan,a.shaft,a.support))!=expected: raise ValueError('input hash mismatch')
with np.load(a.scan) as data: points=data['vertices'].copy()
if points.shape!=(1256836,3) or not np.isfinite(points).all(): raise ValueError('invalid scan')
meshes=[trimesh.load_mesh(f,process=False) for f in (a.shaft,a.support)]
if [len(m.faces) for m in meshes]!=[2112,94]: raise ValueError('unexpected tessellation')
centres=[m.triangles.mean(axis=1) for m in meshes]; tree=cKDTree(points); stats={}
for name,x in zip(('shaft','support'),centres):
 d=tree.query(x,workers=1)[0]; stats[name]={'points':len(x),'median_nearest_scan_vertex':float(np.median(d)),'p95_nearest_scan_vertex':float(np.percentile(d,95)),'max_nearest_scan_vertex':float(d.max())}
a.output.mkdir(mode=0o700,parents=True)
fig,axes=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
for ax,(x,y,label) in zip(axes,[(0,1,'XY'),(0,2,'XZ'),(1,2,'YZ')]):
 ax.scatter(points[::25,x],points[::25,y],s=.15,c='#9aa4a9',alpha=.25,rasterized=True,label='Drive scan (1 vertex in 25)')
 for c,col,name in zip(centres,['#dd6b20','#286caa'],['Shaft open patch','Support open patches']): ax.scatter(c[:,x],c[:,y],s=3,alpha=.8,c=col,label=name)
 ax.set_aspect('equal',adjustable='box'); ax.set_title(label); ax.set_xlabel('uncalibrated source units'); ax.set_ylabel('uncalibrated source units'); ax.grid(alpha=.2)
axes[0].legend(fontsize=7); fig.suptitle('935 observed drive: CAD fragments in same scan-derived frame\nScale, registration and mechanical fit unverified')
fig.savefig(a.output/'drive-fragments-scan-overlay.png',dpi=180); plt.close(fig)
report={'status':'same_scan_visual_and_nearest_vertex_screen_only','scan_sha256':expected[0],'shaft_stl_sha256':expected[1],'support_stl_sha256':expected[2],'nearest_vertex_distance_upper_bound':stats,'source_units_calibrated':False,'physical_fit_verified':False,'support_crop_is_material_boundary':False,'manufacturing_authorized':False,'image_sha256':sha(a.output/'drive-fragments-scan-overlay.png')}
(a.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report))
