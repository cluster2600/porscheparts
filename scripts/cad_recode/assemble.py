#!/usr/bin/env python3
"""Compose converted USD assets for inspection, never invent engine joints."""
import argparse
import os
from pathlib import Path
from pxr import Gf, Usd, UsdGeom

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('scan_usd', type=Path); p.add_argument('cad_usd', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--scan-display-scale', type=float, required=True)
p.add_argument('--cad-display-scale', type=float, required=True)
a = p.parse_args()
import math
if not all(math.isfinite(s) and s > 0 for s in [a.scan_display_scale, a.cad_display_scale]):
    raise ValueError('positive explicit display scales required')
if a.output.exists(): raise FileExistsError(a.output)
for path in (a.scan_usd, a.cad_usd):
    source = Usd.Stage.Open(str(path.resolve()))
    if not source or not source.GetDefaultPrim(): raise ValueError('input needs a default prim')
    if not any(prim.IsA(UsdGeom.Gprim) for prim in
               Usd.PrimRange.Stage(source, Usd.TraverseInstanceProxies())):
        raise ValueError('input contains no renderable geometry')
a.output.parent.mkdir(parents=True, exist_ok=True)
stage = Usd.Stage.CreateNew(str(a.output))
root = UsdGeom.Xform.Define(stage, '/Comparison')
stage.SetDefaultPrim(root.GetPrim())
UsdGeom.SetStageMetersPerUnit(stage, 1.0)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
stage.GetRootLayer().customLayerData = {
    'identity': '935-Wolfe-reference', 'unitsStatus': 'display_only_physical_scale_unknown',
    'physicsValidated': False, 'manufacturingAuthorized': False}
for name, path, scale in [('RawScan', a.scan_usd, a.scan_display_scale), ('Candidate', a.cad_usd, a.cad_display_scale)]:
    xform = UsdGeom.Xform.Define(stage, '/Comparison/' + name)
    xform.GetPrim().GetReferences().AddReference(Path(os.path.relpath(path.resolve(), a.output.parent.resolve())).as_posix())
    xform.AddScaleOp().Set(Gf.Vec3d(scale))
    xform.GetPrim().SetCustomDataByKey('displayScaleOnly', True)
stage.GetRootLayer().Save()
