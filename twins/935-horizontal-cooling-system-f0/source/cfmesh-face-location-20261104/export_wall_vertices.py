import argparse
import re
import numpy as np
from pathlib import Path
from distance_screen import body
parser=argparse.ArgumentParser(description='Export private rotor-patch vertices from an ASCII OpenFOAM mesh')
parser.add_argument('poly_mesh',type=Path)
parser.add_argument('output',type=Path)
args=parser.parse_args()
p=args.poly_mesh
m=re.findall(r'rotor\s*\{[^{}]*?nFaces\s+(\d+)\s*;[^{}]*?startFace\s+(\d+)\s*;', (p/'boundary').read_text(),re.S); assert len(m)==1
count,start=map(int,m[0]); vertices=set(); found=0
for i,line in enumerate(body(p/'faces')):
 if start<=i<start+count:
  f=re.fullmatch(r'(\d+)\(([^()]*)\)',line); assert f
  x=[int(v) for v in f.group(2).split()]; assert len(x)==int(f.group(1)); vertices.update(x); found+=1
assert found==count and len(vertices)==349542
xyz=[]
for i,line in enumerate(body(p/'points')):
 if i in vertices: xyz.append([float(v) for v in line[1:-1].split()])
assert len(xyz)==len(vertices)
out=args.output
if out.exists(): raise SystemExit('output exists')
np.savez_compressed(out,vertices=np.asarray(xyz)); print('rotor_vertices',len(xyz))
