#!/usr/bin/env python3
"""Check every actual USD float32 point against independent native field coordinates."""
import argparse,hashlib,json,math
from pathlib import Path


def verify(asset,reference,output):
 from pxr import Usd,UsdGeom
 stage=Usd.Stage.Open(str(asset));r=json.load(open(reference));root=stage.GetDefaultPrim()
 if not root or UsdGeom.GetStageMetersPerUnit(stage)!=1 or UsdGeom.GetStageUpAxis(stage)!='Z':raise ValueError('Physical field units/axes mismatch')
 meta=root.GetCustomData()
 if meta['sourceFieldSHA256']!=r['source_field_sha256'] or meta['deformationScale']!=1:raise ValueError('Source field/physical scale identity failed')
 meshes=[UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)]
 if len(meshes)!=1:raise ValueError('One native boundary expected')
 points=meshes[0].GetPointsAttr().Get();expected=r['native_released_points_m']
 if len(points)!=len(expected):raise ValueError('All native boundary points required')
 error=max(math.dist(tuple(p),x)*1000 for p,x in zip(points,expected))
 limit=2e-5
 if error>limit:raise ValueError('Actual USD float32 coordinates exceed the representation precision bound')
 result={'status':'passed_actual_USD_float32_coordinate_check','all_boundary_coordinates_checked':len(points),'maximum_actual_USD_storage_error_mm':error,'representation_precision_bound_mm':limit,'native_reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'field_bundle_sha256':r['field_bundle_sha256'],'source_field_sha256':r['source_field_sha256'],'asset_sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'meters_per_unit':1,'up_axis':'Z','deformation_scale':1,'precision_bound_is_not_manufacturing_acceptance_limit':True,'physical_validation_established':False}
 output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('asset',type=Path);p.add_argument('native_reference',type=Path);p.add_argument('output',type=Path);a=p.parse_args();verify(a.asset,a.native_reference,a.output)
