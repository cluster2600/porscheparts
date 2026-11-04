#!/usr/bin/env python3
"""Add open drive fragments to the existing hypothetical 935 USD scene."""
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
 if count!=n or p.stat().st_size!=84+50*n: raise ValueError('invalid STL')
 dt=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attr','<u2')])
 return np.memmap(p,mode='r',dtype=dt,offset=84,shape=(n,))['vertices']

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('base',type=Path);p.add_argument('shaft',type=Path);p.add_argument('support',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[5]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()): raise SystemExit('fresh private work output required')
expected=('22fa354baa2d69d22e21b4677625023259cd529e22708b25aeba0affe87f10ce','aab59ff0dd10644138dd6a9ec970c7b1abb94f20f72fee0e6234500200759a91','89b86f3d353603b57ab71eaf8306d8681a2cec6110a734a5ba17eae4da274e98')
if tuple(sha(x) for x in (a.base,a.shaft,a.support))!=expected: raise ValueError('input hash mismatch')
a.output.mkdir(mode=0o700,parents=True); base=a.output/'assembly-inspection.usdc'; shutil.copyfile(a.base,base)
if sha(base)!=expected[0]: raise ValueError('base copy changed')
base_stage=Usd.Stage.Open(str(base))
if not base_stage or UsdGeom.GetStageMetersPerUnit(base_stage)!=1 or UsdGeom.GetStageUpAxis(base_stage)!=UsdGeom.Tokens.z: raise ValueError('base scene metadata invalid')
del base_stage
path=a.output/'assembly-with-open-drive-fragments.usda'; stage=Usd.Stage.CreateNew(str(path)); stage.GetRootLayer().subLayerPaths=['./assembly-inspection.usdc']
UsdGeom.SetStageMetersPerUnit(stage,1); UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
world=stage.GetPrimAtPath('/World')
if not world: raise ValueError('base world missing')
stage.SetDefaultPrim(world)
group=UsdGeom.Xform.Define(stage,'/World/inspection_drive_fragments'); group.GetPrim().SetCustomData({'classification':'open_scan_derived_witnesses_not_mating_parts','physical_fit_verified':False,'manufacturing_authorized':False})
for name,source,n,color in [('shaft_open',a.shaft,2112,(1.,.35,.05)),('support_open',a.support,94,(.1,.5,1.))]:
 points=(vertices(source,n).reshape(-1,3).astype(np.float64)*.001).astype(np.float32)
 mesh=UsdGeom.Mesh.Define(stage,'/World/inspection_drive_fragments/'+name); mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points)); mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(n,3,dtype=np.int32))); mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.arange(n*3,dtype=np.int32))); mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none);mesh.CreateDisplayColorAttr([Gf.Vec3f(*color)]);mesh.GetPrim().SetCustomData({'source_sha256':sha(source),'scale_verified':False,'mating_interface_verified':False})
stage.GetRootLayer().Save(); del stage
reopened=Usd.Stage.Open(str(path));
if not reopened or not reopened.GetPrimAtPath('/World/drive_observed'): raise ValueError('base drive absent')
for name,source,n in [('shaft_open',a.shaft,2112),('support_open',a.support,94)]:
 mesh=UsdGeom.Mesh(reopened.GetPrimAtPath('/World/inspection_drive_fragments/'+name)); expected_points=(vertices(source,n).reshape(-1,3).astype(np.float64)*.001).astype(np.float32)
 if not mesh or not np.array_equal(np.asarray(mesh.GetPointsAttr().Get()),expected_points): raise ValueError('USD fragment readback mismatch')
result={'status':'conditional_935_scene_with_open_fragments_not_validated_assembly','base_sha256':expected[0],'shaft_sha256':expected[1],'support_sha256':expected[2],'layer_sha256':sha(path),'all_fragment_points_reread_exact':True,'base_relative_path':'assembly-inspection.usdc','unit_assumption_m_per_source_unit':.001,'scale_verified':False,'physical_registration_verified':False,'mating_interface_verified':False,'manufacturing_authorized':False}
(a.output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
