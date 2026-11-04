#!/usr/bin/env python3
"""Place same-scan inspection fragments into the existing hypothetical assembly."""
import argparse, hashlib, json, struct
from pathlib import Path
import numpy as np
import trimesh


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()


def triangles(p):
 with p.open('rb') as f: f.seek(80); count=struct.unpack('<I',f.read(4))[0]
 if p.stat().st_size!=84+50*count: raise ValueError('invalid binary STL')
 return np.memmap(p,mode='r',dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attr','<u2')]),offset=84,shape=(count,))['vertices']

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('case',type=Path);p.add_argument('input_drive',type=Path);p.add_argument('placed_drive',type=Path);p.add_argument('shaft',type=Path);p.add_argument('support',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[5]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('fresh private output required')
expected=('ec58a866ae562c2a77664c727f3205177a0911f67263d4623a9294d2730cc5c9','6d7b5c6a35935013659d45af33c63bb2f69f8c82c53092155ba7ac3c07463f72','fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35','1f607a95bc107d2e18ea4a5806170652e534e9125561aa7eec730ccb01ee1f4c','637f7fcce78441cd4ef8fa1d33e6c23ba1a3a1a3864276cfcafaba7097cbc38c')
if tuple(sha(x) for x in (a.case,a.input_drive,a.placed_drive,a.shaft,a.support))!=expected: raise ValueError('input hash mismatch')
d=json.loads(a.case.read_text()); rows=[r for r in d['imports'] if r['id']=='drive_observed']
if len(rows)!=1 or rows[0]['sha256']!=expected[1] or d['scale_verified']: raise ValueError('unexpected case')
m=np.array(rows[0]['source_to_assembly_mm'],float)
if m.shape!=(4,4) or not np.allclose(m[3],[0,0,0,1],atol=1e-10) or not np.allclose(m[:3,:3].T@m[:3,:3],np.eye(3),atol=1e-9) or np.linalg.det(m[:3,:3])<0: raise ValueError('invalid placement')
src,dst=triangles(a.input_drive),triangles(a.placed_drive)
if src.shape!=dst.shape: raise ValueError('drive triangle count changed')
maxerr=0.
for i in range(0,len(src),100000):
 error=np.abs(src[i:i+100000].astype(float)@m[:3,:3].T+m[:3,3]-dst[i:i+100000]); maxerr=max(maxerr,float(error.max()))
if maxerr>.0002: raise ValueError('case transform does not reproduce retained drive')
a.output.mkdir(mode=0o700,parents=True); outputs=[]
for file,name in ((a.shaft,'shaft-assembly.stl'),(a.support,'support-assembly.stl')):
 mesh=trimesh.load_mesh(file,process=False); original=mesh.triangles.copy(); mesh.apply_transform(m); out=a.output/name; mesh.export(out,file_type='stl'); check=triangles(out)
 delta=np.max(np.abs((original.astype(float)@m[:3,:3].T+m[:3,3])-check.astype(float)))
 if delta>.0002 or len(original)!=len(check): raise ValueError('fragment placement error')
 outputs.append({'file':name,'sha256':sha(out),'triangles':len(check),'max_coordinate_error_source_units':float(delta)})
result={'status':'case_hypothesis_same_scan_fragments_not_fit_validation','case_sha256':expected[0],'drive_placement_max_coordinate_error_source_units':maxerr,'outputs':outputs,'scale_verified':False,'physical_registration_verified':False,'mating_interface_verified':False,'manufacturing_authorized':False}
(a.output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
