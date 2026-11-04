#!/usr/bin/env python3
"""Add a provisional rigid rotor revolution to the extended 935 scene."""
import argparse,hashlib,json,math,shutil
from pathlib import Path
import numpy as np
from pxr import Gf,Usd,UsdGeom


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('scene',type=Path);p.add_argument('sweep',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[5]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('fresh private output required')
files=[a.scene/'assembly-inspection.usdc',a.scene/'assembly-with-open-drive-fragments.usda',a.scene/'assembly-with-fragments-and-witnesses.usda',a.sweep]
expected=['22fa354baa2d69d22e21b4677625023259cd529e22708b25aeba0affe87f10ce','89744d984fae2dd30a43dd1e09294a1e8182d456bd7558667136291094df2107','89cebdf8065c2ea2d647ffbd2cd29e15e487b0b94351c5e61cb62b71559c8a11','656c15ff50002192f9df19d2ba2c2888e9666f2471ffd6b5bc5c9f85aab60146']
if [sha(f) for f in files]!=expected: raise ValueError('input hash mismatch')
sweep=json.loads(a.sweep.read_text())
if sweep['schema']!='935-rigid-rotor-sweep-v1' or sweep['samples_per_revolution']!=240 or sweep['axis']!={'origin_native_units':[0,0,0],'direction':[0,0,1]} or any(sweep[k] is not False for k in ('scale_verified','axis_verified_on_historical_935','rotor_drive_mount_defined','solid_containment_checked','thermal_or_elastic_changes_checked','manufacturing_authorized')): raise ValueError('unexpected sweep evidence')
for name in ('drive_observed','provisional_shroud'):
 if len(sweep['phases'][name])!=240 or sweep['summary'][name]['sampled_collision_count']!=0 or not sweep['summary'][name]['rigid_surface_sweep_separated']: raise ValueError('sweep did not pass its limited surface check')
 if any(row['phase_index']!=i or abs(row['angle_deg']-i*1.5)>1e-10 for i,row in enumerate(sweep['phases'][name])): raise ValueError('sweep phase mismatch')
a.output.mkdir(mode=0o700,parents=True)
for f in files[:3]: shutil.copyfile(f,a.output/f.name)
path=a.output/'935-fragments-witnesses-rotation.usda';stage=Usd.Stage.CreateNew(str(path));stage.GetRootLayer().subLayerPaths=['./'+files[2].name];UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z);stage.SetStartTimeCode(0);stage.SetEndTimeCode(240);stage.SetTimeCodesPerSecond(60);stage.SetFramesPerSecond(60)
world=stage.GetPrimAtPath('/World');rotor=stage.GetPrimAtPath('/World/rotor_candidate')
if not world or not rotor or not rotor.IsA(UsdGeom.Mesh): raise ValueError('base scene missing rotor')
stage.SetDefaultPrim(world); over=stage.OverridePrim('/World/rotor_candidate'); xform=UsdGeom.Xformable(over)
if xform.GetOrderedXformOps(): raise ValueError('unexpected existing rotor transform')
op=xform.AddRotateZOp();op.Set(0.)
for i in range(241):op.Set(i*1.5,Usd.TimeCode(i))
stage.GetRootLayer().Save();del stage
check=Usd.Stage.Open(str(path));rotor=check.GetPrimAtPath('/World/rotor_candidate');ops=UsdGeom.Xformable(rotor).GetOrderedXformOps()
if len(ops)!=1 or len(ops[0].GetTimeSamples())!=241 or not check.GetPrimAtPath('/World/inspection_drive_fragments/shaft_open') or len(check.GetPrimAtPath('/World/inspection_flange_witnesses').GetChildren())!=8: raise ValueError('scene readback failed')
pt=np.array(UsdGeom.Mesh(rotor).GetPointsAttr().Get()[0],float); maxerr=0.
for i in range(241):
 angle=math.radians(1.5*i); expected_pt=np.array([math.cos(angle)*pt[0]-math.sin(angle)*pt[1],math.sin(angle)*pt[0]+math.cos(angle)*pt[1],pt[2]])
 xf=UsdGeom.XformCache(Usd.TimeCode(i)).GetLocalToWorldTransform(rotor); actual=np.array(xf.Transform(Gf.Vec3d(*pt)));maxerr=max(maxerr,float(np.linalg.norm(actual-expected_pt)))
 if abs(float(ops[0].Get(Usd.TimeCode(i)))-1.5*i)>1e-10: raise ValueError('angle mismatch')
for name in ('/World/inspection_drive_fragments','/World/inspection_flange_witnesses'):
 xf=UsdGeom.Xformable(check.GetPrimAtPath(name))
 if xf.TransformMightBeTimeVarying(): raise ValueError('stationary inspection geometry has animation')
if maxerr>1e-8: raise ValueError('rotation fixture mismatch')
result={'status':'conditional_rigid_rotation_preview_not_physical_twin','source_layer_sha256':expected[2],'sweep_sha256':expected[3],'output_sha256':sha(path),'time_samples':241,'frame_rate_preview_only':60,'max_fixture_error_m':maxerr,'operating_speed_defined':False,'scale_verified':False,'axis_verified':False,'gear_ratio_verified':False,'rotor_drive_joint_defined':False,'manufacturing_authorized':False}
(a.output/'animation-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
