#!/usr/bin/env python3
"""Render sampled rotor wall and selected wall-face vertex means privately."""
import argparse
import re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from distance_screen import body

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('poly_mesh',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
if a.output.exists(): raise SystemExit('output already exists')
mesh=a.poly_mesh
matches=re.findall(r'rotor\s*\{[^{}]*?nFaces\s+(\d+)\s*;[^{}]*?startFace\s+(\d+)\s*;', (mesh/'boundary').read_text(), re.S)
if len(matches)!=1: raise ValueError('expected one rotor patch')
count,start=map(int,matches[0]); ids=list(map(int,body(mesh/'sets'/'nonOrthoFaces')))
if len(ids)!=len(set(ids)) or any(i<0 or i>=start for i in ids): raise ValueError('invalid face set')
wanted=set(ids); own={}; nei={}; rotor=[]
for i,s in enumerate(body(mesh/'owner')):
 if i in wanted: own[i]=int(s)
 if start<=i<start+count: rotor.append(int(s))
for i,s in enumerate(body(mesh/'neighbour')):
 if i in wanted: nei[i]=int(s)
if len(own)!=len(ids) or len(nei)!=len(ids) or len(rotor)!=count: raise ValueError('incomplete connectivity')
cells=set(own.values())|set(nei.values()); selected={start+i for i,c in enumerate(rotor) if c in cells}
sample={start+i for i in range(0,count,20)}; faces={}
for i,line in enumerate(body(mesh/'faces')):
 if i not in selected and i not in sample: continue
 m=re.fullmatch(r'(\d+)\(([^()]*)\)',line)
 if not m: raise ValueError('invalid face')
 vs=[int(v) for v in m.group(2).split()]
 if len(vs)!=int(m.group(1)) or len(vs)<3: raise ValueError('invalid vertex count')
 faces[i]=vs
if len(faces)!=len(selected|sample): raise ValueError('missing faces')
points=np.array([[float(v) for v in line[1:-1].split()] for line in body(mesh/'points')])
if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all(): raise ValueError('invalid points')
def centres(indices): return np.array([points[faces[i]].mean(axis=0) for i in sorted(indices)])
background=centres(sample); marked=centres(selected)
fig, axes=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
for ax,(x,y,label) in zip(axes,[(0,1,'XY'),(0,2,'XZ'),(1,2,'YZ')]):
 ax.scatter(background[:,x],background[:,y],s=0.15,c='#8e999e',alpha=.3,rasterized=True,label='Rotor wall (1 face in 20)')
 ax.scatter(marked[:,x],marked[:,y],s=10,c='#cb3b28',alpha=.9,label=f'Incident wall faces ({len(selected)})')
 ax.set_aspect('equal',adjustable='box'); ax.set_title(label); ax.set_xlabel('case coordinate'); ax.set_ylabel('case coordinate'); ax.grid(alpha=.2)
axes[0].legend(loc='upper right',fontsize=7,markerscale=1.5)
fig.suptitle('935 provisional cfMesh: wall faces incident to non-orthogonal cells\nExploratory mesh; scale and scan registration unverified',fontsize=12)
fig.savefig(a.output,dpi=180); plt.close(fig)
print(f'background_faces={len(sample)} incident_faces={len(selected)} output={a.output}')
