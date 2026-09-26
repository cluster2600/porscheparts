#!/usr/bin/env python3
"""Check ONLY the synthetic 20x40x60 mm aluminum block, never a real part."""
import argparse
import json
import math
from pathlib import Path
from pxr import Usd, UsdGeom, UsdPhysics

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('asset', type=Path)
p.add_argument('report', type=Path)
a = p.parse_args()
stage = Usd.Stage.Open(str(a.asset))
if not stage or not stage.GetDefaultPrim():
    raise ValueError('fixture needs a valid USD stage and default prim')
meters = UsdGeom.GetStageMetersPerUnit(stage)
kg = UsdPhysics.GetStageKilogramsPerUnit(stage)
bounds = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_]).ComputeWorldBound(stage.GetDefaultPrim()).ComputeAlignedBox()
size = [float(v) * meters for v in bounds.GetSize()]
values = {}
labels = []
for prim in stage.Traverse():
    for attr in prim.GetAttributes():
        if attr.HasAuthoredValueOpinion():
            if attr.GetName().startswith('physics:'):
                values.setdefault(attr.GetName(), []).append(attr.Get())
            elif attr.GetName() == 'semantics:labels:material':
                labels.extend(str(v).lower() for v in attr.Get())
checks = {'dimensions_m': all(math.isclose(v, ref, rel_tol=1e-5, abs_tol=1e-8)
                              for v, ref in zip(size, [0.02, 0.04, 0.06]))}
observed = {'dimensions_m': size, 'volume_m3': math.prod(size), 'material_labels': labels}
for name, scale, expected in [('mass', kg, 0.1296), ('density', kg / meters**3, 2700),
                              ('gravityMagnitude', meters, 9.81)]:
    actual = [float(v) * scale for v in values.get('physics:' + name, [])]
    observed[name] = actual
    checks[name] = len(actual) == 1 and math.isclose(actual[0], expected, rel_tol=1e-5)
checks['aluminum_material'] = bool({'aluminum', 'aluminium'} & set(labels)) and 'plastic' not in labels
checks['one_rigid_body'] = values.get('physics:rigidBodyEnabled') == [True]
checks['collision_enabled'] = values.get('physics:collisionEnabled') == [True]
report = {'passed': all(checks.values()), 'fixture_only': True, 'asset': str(a.asset),
          'checks': checks, 'observed': observed, 'head_physics_validated': False}
a.report.parent.mkdir(parents=True, exist_ok=True)
a.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['passed'] else 1)
