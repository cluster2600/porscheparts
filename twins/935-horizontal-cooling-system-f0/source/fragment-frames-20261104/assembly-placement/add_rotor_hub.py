#!/usr/bin/env python3
"""Add the scan-fitted open hub surfaces beneath the animated rotor prim."""
import argparse,hashlib,json,shutil,struct
from pathlib import Path
import numpy as np
from pxr import Gf,Usd,UsdGeom,Vt


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('hub',type=Path);p.add_argument('output',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[5]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()):raise SystemExit('fresh private output required')
names=['assembly-inspection.usdc','assembly-with-open-drive-fragments.usda','assembly-with-fragments-and-witnesses.usda','935-fragments-witnesses-rotation.usda']; hashes=['22fa354baa2d69d22e21b4677625023259cd529e22708b25aeba0affe87f10ce','89744d984fae2dd30a43dd1e09294a1e8182d456bd7558667136291094df2107','89cebdf8065c2ea2d647ffbd2cd29e15e487b0b94351c5e61cb62b71559c8a11','dfc56a4f4d832e6616b2211c864d7ac62a79db224ce51472940739f704fb1234']
if [sha(a.scene/n) for n in names]!=hashes or sha(a.hub)!='4223cbf3d31ae9b37d9fe03ee8a7f2d0be8ec786e9e7101bc005915717f5fee1':raise ValueError('input hash mismatch')
with a.hub.open('rb') as f:f.seek(80); n=struct.unpack('<I',f.read(4))[0]
if n!=906 or a.hub.stat().st_size!=84+n*50:raise ValueError('invalid hub STL')
dtype=np.dtype([('n','<f4',(3,)),('v','<f4',(3,3)),('a','<u2')]);raw=np.memmap(a.hub,mode='r',dtype=dtype,offset=84,shape=(n,))['v'];points=(np.asarray(raw,dtype=np.float64).reshape(-1,3)*.001).astype(np.float32)
a.output.mkdir(mode=0o700,parents=True)
for name in names:shutil.copyfile(a.scene/name,a.output/name)
path=a.output/'935-animated-with-hub-witness.usda';stage=Usd.Stage.CreateNew(str(path));stage.GetRootLayer().subLayerPaths=['./'+names[-1]];UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z);stage.SetStartTimeCode(0);stage.SetEndTimeCode(240);stage.SetTimeCodesPerSecond(60);stage.SetFramesPerSecond(60)
world=stage.GetPrimAtPath('/World');rotor=stage.GetPrimAtPath('/World/rotor_candidate')
if not world or not rotor or len(UsdGeom.Xformable(rotor).GetOrderedXformOps())!=1:raise ValueError('animated rotor missing')
stage.SetDefaultPrim(world);mesh=UsdGeom.Mesh.Define(stage,'/World/rotor_candidate/hub_open_witness');mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points));mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(n,3,np.int32)));mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.arange(3*n,dtype=np.int32)));mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none);mesh.CreateDisplayColorAttr([Gf.Vec3f(1.,.72,.08)]);mesh.GetPrim().SetCustomData({'classification':'open_fitted_hub_surface_not_complete_part','source_stl_sha256':sha(a.hub),'scale_verified':False,'interface_verified':False,'manufacturing_authorized':False});stage.GetRootLayer().Save();del stage
check=Usd.Stage.Open(str(path));mesh=UsdGeom.Mesh(check.GetPrimAtPath('/World/rotor_candidate/hub_open_witness'));rotor=check.GetPrimAtPath('/World/rotor_candidate')
if not mesh or not np.array_equal(np.asarray(mesh.GetPointsAttr().Get()),points) or not np.array_equal(np.asarray(mesh.GetFaceVertexIndicesAttr().Get()),np.arange(3*n)) or not np.array_equal(np.asarray(mesh.GetFaceVertexCountsAttr().Get()),np.full(n,3)):raise ValueError('hub readback mismatch')
for time in (0,60,120,180,240):
 cache=UsdGeom.XformCache(Usd.TimeCode(time));
 if cache.GetLocalToWorldTransform(mesh.GetPrim())!=cache.GetLocalToWorldTransform(rotor):raise ValueError('hub does not follow rotor transform')
if len(UsdGeom.Xformable(rotor).GetOrderedXformOps()[0].GetTimeSamples())!=241:raise ValueError('rotor samples lost')
result={'status':'animated_open_hub_witness_not_functional_hub','source_hub_sha256':sha(a.hub),'source_animation_sha256':hashes[-1],'output_sha256':sha(path),'hub_triangles':n,'all_hub_points_and_indices_reread_exact':True,'parent_transform_checked_at_five_times':True,'scale_verified':False,'hub_fit_verified':False,'rotor_drive_joint_defined':False,'manufacturing_authorized':False}
(a.output/'hub-layer-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
