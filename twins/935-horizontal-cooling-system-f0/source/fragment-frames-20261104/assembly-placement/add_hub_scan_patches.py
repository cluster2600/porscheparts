#!/usr/bin/env python3
"""Add selected input-scan triangles as rotor-following inspection geometry."""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from pxr import Gf,Usd,UsdGeom,Vt


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('hub_report',type=Path);p.add_argument('observed',type=Path);p.add_argument('aligned',type=Path);p.add_argument('output',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[5]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()):raise SystemExit('fresh private output required')
names=['assembly-inspection.usdc','assembly-with-open-drive-fragments.usda','assembly-with-fragments-and-witnesses.usda','935-fragments-witnesses-rotation.usda','935-animated-with-hub-witness.usda'];hashes=['22fa354baa2d69d22e21b4677625023259cd529e22708b25aeba0affe87f10ce','89744d984fae2dd30a43dd1e09294a1e8182d456bd7558667136291094df2107','89cebdf8065c2ea2d647ffbd2cd29e15e487b0b94351c5e61cb62b71559c8a11','dfc56a4f4d832e6616b2211c864d7ac62a79db224ce51472940739f704fb1234','10bd3c940e107ef1c03d15f0b81ca0caf676924576bb266eb07125181277dbeb']; expected=['41ebfafdb38124e4b878baf6da3822893265ba3f25c3f2ea85b0b2daca383a37','4acc04ebdc81c16017c78d2bb6fac2167c40bf15d619d1ec0a5f63ff02cd0e2a','452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247']
if [sha(a.scene/n) for n in names]!=hashes or [sha(x) for x in (a.hub_report,a.observed,a.aligned)]!=expected:raise ValueError('input hash mismatch')
r=json.loads(a.hub_report.read_text());m=np.asarray(r['transform_seed_to_rotor_candidate_frame'],float)
if r['schema']!='935-observed-hub-surfaces-v1' or r['scale_verified'] or m.shape!=(4,4) or not np.allclose(m[3],[0,0,0,1]):raise ValueError('unexpected hub evidence')
with np.load(a.observed) as d:original_v=d['vertices'];original_f=d['faces']
with np.load(a.aligned) as d:aligned_v=d['vertices'];aligned_f=d['faces']
if not np.array_equal(original_f,aligned_f) or original_v.shape!=aligned_v.shape or not np.isfinite(m).all():raise ValueError('frame transport mismatch')
err=float(np.max(np.abs(original_v@m[:3,:3].T+m[:3,3]-aligned_v)))
if err>1e-9:raise ValueError('coordinate transport failed')
patches=[]
for i,patch in enumerate(r['patches']):
 ids=np.asarray(patch['selected_face_indices'],np.int64)
 if patch['id']!=f'hub-patch-{i:02}' or len(ids)==0 or len(np.unique(ids))!=len(ids) or ids.min()<0 or ids.max()>=len(aligned_f):raise ValueError('invalid selected faces')
 patches.append((ids,(aligned_v[aligned_f[ids]].reshape(-1,3)*.001).astype(np.float32)))
if [len(ids) for ids,_ in patches]!=[2888,2963]:raise ValueError('unexpected selected counts')
a.output.mkdir(mode=0o700,parents=True)
for name in names:shutil.copyfile(a.scene/name,a.output/name)
path=a.output/'935-animated-hub-scan-patches.usda';stage=Usd.Stage.CreateNew(str(path));stage.GetRootLayer().subLayerPaths=['./'+names[-1]];UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z);stage.SetStartTimeCode(0);stage.SetEndTimeCode(240);stage.SetTimeCodesPerSecond(60);stage.SetFramesPerSecond(60);world=stage.GetPrimAtPath('/World');rotor=stage.GetPrimAtPath('/World/rotor_candidate')
if not world or not rotor or not stage.GetPrimAtPath('/World/rotor_candidate/hub_open_witness'):raise ValueError('prior scene missing')
stage.SetDefaultPrim(world)
for i,(ids,points) in enumerate(patches):
 mesh=UsdGeom.Mesh.Define(stage,f'/World/rotor_candidate/hub_scan_patch_{i:02}');mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points));mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(ids),3,np.int32)));mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.arange(len(points),dtype=np.int32)));mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none);mesh.CreateDisplayColorAttr([Gf.Vec3f(.1,.85,.9) if i==0 else Gf.Vec3f(.9,.15,.75)]);mesh.GetPrim().SetCustomData({'classification':'selected_input_scan_mesh_triangles_not_metrology_certificate','aligned_scan_sha256':expected[2],'source_units_calibrated':False,'manufacturing_authorized':False})
stage.GetRootLayer().Save();del stage
check=Usd.Stage.Open(str(path));rotor=check.GetPrimAtPath('/World/rotor_candidate')
for i,(ids,points) in enumerate(patches):
 mesh=UsdGeom.Mesh(check.GetPrimAtPath(f'/World/rotor_candidate/hub_scan_patch_{i:02}'))
 if not mesh or not np.array_equal(np.asarray(mesh.GetPointsAttr().Get()),points) or not np.array_equal(np.asarray(mesh.GetFaceVertexCountsAttr().Get()),np.full(len(ids),3)) or not np.array_equal(np.asarray(mesh.GetFaceVertexIndicesAttr().Get()),np.arange(len(points))):raise ValueError('USD patch readback mismatch')
 for frame in (0,60,120,180,240):
  cache=UsdGeom.XformCache(Usd.TimeCode(frame))
  if cache.GetLocalToWorldTransform(mesh.GetPrim())!=cache.GetLocalToWorldTransform(rotor):raise ValueError('scan patch does not follow rotor')
result={'status':'selected_same_scan_triangles_for_inspection_not_measured_surface_certificate','source_report_sha256':expected[0],'scan_sha256':expected[2],'frame_max_coordinate_error_source_units':err,'patch_triangle_counts':[len(ids) for ids,_ in patches],'output_sha256':sha(path),'all_points_and_topology_reread_exact':True,'parent_transform_checked_at_five_times':True,'scale_verified':False,'physical_registration_verified':False,'manufacturing_authorized':False}
(a.output/'hub-scan-patch-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
