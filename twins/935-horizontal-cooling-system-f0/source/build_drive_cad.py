#!/usr/bin/env python3
"""Editable open loft of a scanned periodic shaft patch; omit crop caps."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
sys.path.append('/opt/freecad/usr/lib')
import FreeCAD as App
import Part

if len(sys.argv) != 5:
    raise ValueError('Expected shaft profile JSON, SHA256, assumed scale and new destination')
source, expected, scale, output = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]), Path(sys.argv[4]).resolve()
if not math.isfinite(scale) or scale <= 0 or output.exists():
    raise ValueError('Finite positive assumed scale and new destination required')
if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise ValueError('Shaft profile hash mismatch')
for parent in output.parents:
    if (parent/'.git').exists() and output.relative_to(parent).parts[0] != 'work':
        raise ValueError('Scan derivatives must stay in ignored work/')
data = json.loads(source.read_text()); profiles = data.get('profiles', [])
if (data['schema'] != '935-observed-drive-shaft-v1' or len(profiles) < 3
        or len({len(p) for p in profiles}) != 1 or len(profiles[0]) < 16
        or any(len(v) != 3 or not all(math.isfinite(x) for x in v) for p in profiles for v in p)):
    raise ValueError('Finite compatible acquired shaft profiles required')
os.umask(0o077); output.mkdir(parents=True, mode=0o700)
doc = App.newDocument('935PartialAcquiredDriveShaft'); sections = []
for i, profile in enumerate(profiles):
    points = [App.Vector(*[v*scale for v in point]) for point in profile]
    section = doc.addObject('Part::Feature', f'ObservedSection{i}')
    section.Shape = Part.makePolygon(points+[points[0]]); sections.append(section)
loft = doc.addObject('Part::Loft','AcquiredPeriodicShaftPatch')
loft.Sections = sections; loft.Solid = False; loft.Ruled = True; loft.Closed = False
loft.Label = 'Acquired periodic shaft patch; open ends, uncalibrated'
loft.addProperty('App::PropertyString','ProfileInputSHA256').ProfileInputSHA256 = expected
loft.addProperty('App::PropertyString','SurfaceStatus').SurfaceStatus = data['profile_label']
loft.addProperty('App::PropertyInteger','ObservedPeriodicity').ObservedPeriodicity = data['observed_periodicity']
doc.recompute()
if not loft.Shape.isValid() or len(loft.Shape.Solids) or loft.Shape.isClosed() or loft.Shape.Area <= 0:
    raise ValueError('Invalid open shaft surface')
area = loft.Shape.Area; face_count = len(loft.Shape.Faces)
doc.saveAs(str(output/'observed-drive-shaft.FCStd')); Part.export([loft],str(output/'observed-drive-shaft.step'))
step = Part.read(str(output/'observed-drive-shaft.step'))
if not step.isValid() or len(step.Solids) or step.isClosed() or len(step.Faces) != face_count or abs(step.Area/area-1) > 1e-6:
    raise ValueError('STEP open surface reread failed')
App.closeDocument(doc.Name); reopened = App.openDocument(str(output/'observed-drive-shaft.FCStd'))
lofts = [o for o in reopened.Objects if o.TypeId == 'Part::Loft']
if len(lofts) != 1 or not lofts[0].Shape.isValid() or len(lofts[0].Shape.Solids) or lofts[0].Shape.isClosed():
    raise ValueError('Editable native open loft reread failed')
App.closeDocument(reopened.Name)
if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise ValueError('Shaft input changed during export')
receipt = {'status':'partial_acquired_periodic_shaft_open_loft','sections_sha256':expected,
           'cad_program_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'FreeCAD_version':App.Version()[:3],'assumed_mm_per_source_unit':scale,'surface_count':face_count,
           'observed_periodicity':data['observed_periodicity'],'solids':0,'crop_caps_added':False,
           'STEP_area_preserved':True,'reopened_editable_loft_valid':True,'scale_verified':False,
           'functional_interface_verified':False,'manufacturing_authorized':False,
           'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}}
(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Private open shaft candidate saved and reread; manufacturing interface unresolved')
