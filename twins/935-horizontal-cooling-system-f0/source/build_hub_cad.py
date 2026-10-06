#!/usr/bin/env python3
"""Analytic open BRep hub patches; never cap an unobserved solid."""
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.append('/opt/freecad/usr/lib')
import FreeCAD as App
import Part

if len(sys.argv) != 5:
    raise ValueError('Expected hub surface JSON, SHA256, assumed scale and new destination')
source, expected, scale, destination = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]), Path(sys.argv[4])
if not 0 < scale < float('inf') or destination.exists():
    raise ValueError('Finite positive assumed scale and new private destination required')
if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise ValueError('Hub surface hash mismatch')
for parent in destination.resolve().parents:
    if (parent / '.git').exists() and destination.resolve().relative_to(parent).parts[0] != 'work':
        raise ValueError('Scan derivatives must stay in ignored work/')
os.umask(0o077); destination.mkdir(parents=True, mode=0o700)
data = json.loads(source.read_text())
if data['schema'] != '935-observed-hub-surfaces-v1' or not data['patches']:
    raise ValueError('Observed hub surface candidates required')
matrix = App.Matrix(); transform = data['transform_seed_to_rotor_candidate_frame']
for i in range(4):
    for j in range(4): setattr(matrix, f'A{i+1}{j+1}', transform[i][j] * (scale if j == 3 and i < 3 else 1))
doc = App.newDocument('935ObservedHubSurfaceCandidates'); objects = []
for patch in data['patches']:
    model = patch['models'][patch['preferred_model']]; lo, hi = model['axial_span_source_units']; slope = model['radius_slope']
    axis = App.Vector(*model['axis_in_seed_frame']); origin = App.Vector(*model['origin_in_seed_frame_source_units'])
    start = (origin + axis * lo) * scale
    r1 = (model['radius_at_zero_source_units'] + slope * lo) * scale
    r2 = (model['radius_at_zero_source_units'] + slope * hi) * scale
    if min(r1, r2, hi - lo) <= 0:
        raise ValueError('Nonpositive bounded analytic patch')
    solid = (Part.makeCylinder(r1, (hi-lo)*scale, start, axis) if model['type'] == 'cylinder'
             else Part.makeCone(r1, r2, (hi-lo)*scale, start, axis))
    lateral = [f.copy() for f in solid.Faces if type(f.Surface).__name__ != 'Plane']
    if len(lateral) != 1: raise ValueError('One analytic lateral face required; crop caps excluded')
    shape = lateral[0]; shape.transformShape(matrix)
    obj = doc.addObject('Part::Feature', patch['id'].replace('-', '_')); obj.Shape = shape
    obj.addProperty('App::PropertyString', 'SurfaceStatus').SurfaceStatus = patch['surface_label']
    obj.addProperty('App::PropertyString', 'InputSHA256').InputSHA256 = expected
    obj.Label = patch['id'] + ' - ' + model['type'] + '; open candidate, uncalibrated'
    if not shape.isValid() or len(shape.Solids) or len(shape.Faces) != 1: raise ValueError('Invalid open analytic surface')
    objects.append(obj)
doc.recompute(); doc.saveAs(str(destination/'observed-hub-surfaces.FCStd')); Part.export(objects, str(destination/'observed-hub-surfaces.step'))
area = sum(o.Shape.Area for o in objects); reread = Part.read(str(destination/'observed-hub-surfaces.step'))
if not reread.isValid() or len(reread.Solids) or len(reread.Faces) != len(objects) or abs(reread.Area / area - 1) > 1e-6: raise ValueError('STEP surface reread failed')
App.closeDocument(doc.Name); reopened = App.openDocument(str(destination/'observed-hub-surfaces.FCStd'))
if len(reopened.Objects) != len(objects) or any(not o.Shape.isValid() or len(o.Shape.Solids) or len(o.Shape.Faces) != 1 for o in reopened.Objects):
    raise ValueError('Native CAD surface reread failed')
App.closeDocument(reopened.Name)
if hashlib.sha256(source.read_bytes()).hexdigest() != expected: raise ValueError('Hub input changed')
receipt = {'status': 'analytic_open_hub_surface_candidates', 'sections_sha256': expected, 'FreeCAD_version': App.Version()[:3],
           'cad_program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'surface_count': len(objects), 'assumed_mm_per_source_unit': scale, 'solids': 0, 'STEP_area_preserved': True,
           'reopened_native_shapes_valid': True,
           'scale_verified': False, 'complete_hub_reconstructed': False, 'manufacturing_authorized': False,
           'artifacts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}}
(destination/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print('Open analytic hub candidate surfaces saved; no complete or qualified hub')
