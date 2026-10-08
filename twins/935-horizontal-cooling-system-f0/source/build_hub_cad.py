#!/usr/bin/env python3
"""Analytic open hub patches and support inspection planes; no solid closure."""
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.append('/opt/freecad/usr/lib')
import FreeCAD as App
import Part

if len(sys.argv) != 5:
    raise ValueError('Expected analytic surface JSON, SHA256, assumed scale and new destination')
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
support = data['schema'] in ('935-observed-support-plane-v1', '935-observed-support-surfaces-v1')
if not (support or data['schema'] == '935-observed-hub-surfaces-v1') or not data['patches']:
    raise ValueError('Observed analytic surface candidates required')
basename = 'observed-support-candidates' if support else 'observed-hub-surfaces'
matrix = App.Matrix(); transform = data['transform_patch_to_candidate_frame'] if support else data['transform_seed_to_rotor_candidate_frame']
for i in range(4):
    for j in range(4): setattr(matrix, f'A{i+1}{j+1}', transform[i][j] * (scale if j == 3 and i < 3 else 1))
doc = App.newDocument('935ObservedSupportCandidates' if support else '935ObservedHubSurfaceCandidates'); objects = []; checked_arcs = 0
for patch in data['patches']:
    model = patch['models'][patch['preferred_model']]
    if support and model['type'] == 'plane':
        if model['type'] != 'plane' or model['crop_is_part_boundary'] is not False:
            raise ValueError('Artificial inspection plane crop required')
        corners = [App.Vector(*p)*scale for p in model['inspection_crop_corners_source_units']]
        shape = Part.Face(Part.makePolygon(corners + [corners[0]]))
    else:
        lo, hi = model['axial_span_source_units']; slope = model['radius_slope']
        axis = App.Vector(*model['axis_in_seed_frame']); origin = App.Vector(*model['origin_in_seed_frame_source_units'])
        start = (origin + axis * lo) * scale
        r1 = (model['radius_at_zero_source_units'] + slope * lo) * scale
        r2 = (model['radius_at_zero_source_units'] + slope * hi) * scale
        if min(r1, r2, hi - lo) <= 0:
            raise ValueError('Nonpositive bounded analytic patch')
        extent = model.get('angular_extent_deg', 360.)
        if not 0 < extent <= 360: raise ValueError('Invalid bounded angular extent')
        partial = extent < 360.
        primitive_start = App.Vector(0,0,0) if partial else start
        primitive_axis = App.Vector(0,0,1) if partial else axis
        solid = (Part.makeCylinder(r1, (hi-lo)*scale, primitive_start, primitive_axis, extent) if model['type'] == 'cylinder'
                 else Part.makeCone(r1, r2, (hi-lo)*scale, primitive_start, primitive_axis, extent))
        lateral = [f.copy() for f in solid.Faces if type(f.Surface).__name__ != 'Plane']
        if len(lateral) != 1: raise ValueError('One analytic lateral face required; crop caps excluded')
        shape = lateral[0]
        if partial:
            radial = App.Vector(*model['radial_start_direction']); transverse = axis.cross(radial)
            if abs(radial.Length-1) > 1e-8 or abs(axis.dot(radial)) > 1e-8: raise ValueError('Invalid arc frame')
            placement = App.Matrix()
            for i in range(3):
                for j, vector in enumerate((radial, transverse, axis)):
                    setattr(placement, f'A{i+1}{j+1}', (vector.x,vector.y,vector.z)[i])
                setattr(placement, f'A{i+1}4', (start.x,start.y,start.z)[i])
            shape.transformShape(placement)
            # Check the actual BRep against analytic interior points in the source frame.
            import math
            midpoint_radius = (r1+r2)/2
            for fraction in (.25,.5,.75):
                angle = math.radians(extent*fraction)
                expected_point = start + axis*((hi-lo)*scale/2) + midpoint_radius*(radial*math.cos(angle)+transverse*math.sin(angle))
                if Part.Vertex(expected_point).distToShape(shape)[0] > 1e-7*max(1,r1,r2):
                    raise ValueError('Bounded BRep arc disagrees with the source frame')
            expected_area = midpoint_radius*math.radians(extent)*math.hypot((hi-lo)*scale,r2-r1)
            if abs(shape.Area/expected_area-1) > 1e-6: raise ValueError('Bounded arc area mismatch')
            checked_arcs += 1
    shape.transformShape(matrix)
    obj = doc.addObject('Part::Feature', patch['id'].replace('-', '_')); obj.Shape = shape
    obj.addProperty('App::PropertyString', 'SurfaceStatus').SurfaceStatus = patch['surface_label']
    obj.addProperty('App::PropertyString', 'InputSHA256').InputSHA256 = expected
    obj.Label = patch['id'] + ' - ' + model['type'] + '; open candidate, uncalibrated'
    if not shape.isValid() or len(shape.Solids) or len(shape.Faces) != 1: raise ValueError('Invalid open analytic surface')
    objects.append(obj)
doc.recompute(); doc.saveAs(str(destination/(basename+'.FCStd'))); Part.export(objects, str(destination/(basename+'.step')))
area = sum(o.Shape.Area for o in objects); reread = Part.read(str(destination/(basename+'.step')))
if not reread.isValid() or len(reread.Solids) or len(reread.Faces) != len(objects) or abs(reread.Area / area - 1) > 1e-6: raise ValueError('STEP surface reread failed')
App.closeDocument(doc.Name); reopened = App.openDocument(str(destination/(basename+'.FCStd')))
if len(reopened.Objects) != len(objects) or any(not o.Shape.isValid() or len(o.Shape.Solids) or len(o.Shape.Faces) != 1 for o in reopened.Objects):
    raise ValueError('Native CAD surface reread failed')
App.closeDocument(reopened.Name)
if hashlib.sha256(source.read_bytes()).hexdigest() != expected: raise ValueError('Hub input changed')
receipt = {'status': 'open_support_surface_candidates_not_complete_part' if support else 'analytic_open_hub_surface_candidates', 'sections_sha256': expected, 'FreeCAD_version': App.Version()[:3],
           'cad_program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'surface_count': len(objects), 'assumed_mm_per_source_unit': scale, 'solids': 0, 'STEP_area_preserved': True,
           'reopened_native_shapes_valid': True,
           'scale_verified': False, 'complete_hub_reconstructed': False, 'manufacturing_authorized': False,
           'artifacts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}}
if support:
    receipt.update(complete_support_reconstructed=False, inspection_crop_is_material_surface=False,
                   bounded_arcs_checked_against_source_frame=checked_arcs)
(destination/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print('Open analytic candidates saved; complete component and functional qualification remain open')
