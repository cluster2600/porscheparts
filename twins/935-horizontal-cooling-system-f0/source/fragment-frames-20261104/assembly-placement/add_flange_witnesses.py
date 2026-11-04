#!/usr/bin/env python3
"""Layer eight PicoGK opening witnesses onto the partial 935 inspection scene."""
import argparse,hashlib,json,shutil,struct
from pathlib import Path
import numpy as np
from pxr import Gf,Usd,UsdGeom,Vt


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()


def vertices(p,n):
 with p.open('rb') as f: f.seek(80); count=struct.unpack('<I',f.read(4))[0]
 if count!=n or p.stat().st_size!=84+50*n: raise ValueError('invalid binary STL')
 return np.memmap(p,mode='r',dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attr','<u2')]),offset=84,shape=(n,))['vertices']

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('scene_dir',type=Path);p.add_argument('witness_dir',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[5]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('fresh private work output required')
base=a.scene_dir/'assembly-inspection.usdc'; layer=a.scene_dir/'assembly-with-open-drive-fragments.usda'; receipt=a.witness_dir/'receipt.json'
if (sha(base),sha(layer),sha(receipt))!=('22fa354baa2d69d22e21b4677625023259cd529e22708b25aeba0affe87f10ce','89744d984fae2dd30a43dd1e09294a1e8182d456bd7558667136291094df2107','f6304f013e73a86d1604b3ae7ded76fde09e85830be3f606cb6da068ad65fdd7'): raise ValueError('input hash mismatch')
d=json.loads(receipt.read_text()); rows=d['openings']
if len(rows)!=8 or d['drive_stl_sha256']!='fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35' or any(d[k] for k in ('source_unit_to_mm_verified','mating_face_verified','through_holes_verified','interface_verified','manufacturing_authorized','physical_validation')): raise ValueError('unexpected witness status')
for row in rows:
 if Path(row['file']).name!=row['file'] or sha(a.witness_dir/row['file'])!=row['sha256']: raise ValueError('witness hash mismatch')
a.output.mkdir(mode=0o700,parents=True)
for f in (base,layer): shutil.copyfile(f,a.output/f.name)
path=a.output/'assembly-with-fragments-and-witnesses.usda'; stage=Usd.Stage.CreateNew(str(path)); stage.GetRootLayer().subLayerPaths=['./'+layer.name]; UsdGeom.SetStageMetersPerUnit(stage,1); UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z); world=stage.GetPrimAtPath('/World')
if not world or not stage.GetPrimAtPath('/World/inspection_drive_fragments/shaft_open') or not stage.GetPrimAtPath('/World/inspection_drive_fragments/support_open'): raise ValueError('prior fragment layer missing')
stage.SetDefaultPrim(world); group=UsdGeom.Xform.Define(stage,'/World/inspection_flange_witnesses'); group.GetPrim().SetCustomData({'classification':'opening_location_witnesses_not_mounting_material','physical_fit_verified':False,'manufacturing_authorized':False})
for i,row in enumerate(rows):
 points=(vertices(a.witness_dir/row['file'],row['triangles']).reshape(-1,3).astype(np.float64)*.001).astype(np.float32)
 mesh=UsdGeom.Mesh.Define(stage,f'/World/inspection_flange_witnesses/opening_{i:02}');mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points));mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(row['triangles'],3,np.int32)));mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.arange(len(points),dtype=np.int32)));mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none);mesh.CreateDisplayColorAttr([Gf.Vec3f(.95,.12,.62)]);mesh.GetPrim().SetCustomData({'source_sha256':row['sha256'],'mating_interface_verified':False})
stage.GetRootLayer().Save();del stage
check=Usd.Stage.Open(str(path))
if not check or UsdGeom.GetStageMetersPerUnit(check)!=1 or UsdGeom.GetStageUpAxis(check)!=UsdGeom.Tokens.z or not check.GetPrimAtPath('/World/inspection_drive_fragments/shaft_open'): raise ValueError('composed scene incomplete')
for i,row in enumerate(rows):
 mesh=UsdGeom.Mesh(check.GetPrimAtPath(f'/World/inspection_flange_witnesses/opening_{i:02}')); expected=(vertices(a.witness_dir/row['file'],row['triangles']).reshape(-1,3).astype(np.float64)*.001).astype(np.float32)
 if not mesh or not np.array_equal(np.asarray(mesh.GetPointsAttr().Get()),expected) or not np.array_equal(np.asarray(mesh.GetFaceVertexIndicesAttr().Get()),np.arange(len(expected))) or not np.array_equal(np.asarray(mesh.GetFaceVertexCountsAttr().Get()),np.full(row['triangles'],3)): raise ValueError('witness topology or points differ')
result={'status':'conditional_inspection_scene_not_validated_assembly','source_layer_sha256':sha(layer),'witness_receipt_sha256':sha(receipt),'new_layer_sha256':sha(path),'witness_count':8,'witness_triangles':sum(r['triangles'] for r in rows),'all_points_reread_exact':True,'scale_verified':False,'interface_verified':False,'manufacturing_authorized':False}
(a.output/'witness-layer-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
