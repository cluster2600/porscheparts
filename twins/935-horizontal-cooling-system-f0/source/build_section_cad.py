#!/usr/bin/env python3
"""FreeCAD native BRep lofts from private fitted profiles; this is a partial rotor."""
import hashlib
import json
from pathlib import Path
import os
import sys

sys.path.append('/opt/freecad/usr/lib')
import FreeCAD as App
import Part

if len(sys.argv) != 5:
    raise ValueError('Usage: sections.json sha256 assumed_mm_per_source_unit NEW_PRIVATE_OUTPUT')
source, expected, scale, output = Path(sys.argv[1]).resolve(), sys.argv[2], float(sys.argv[3]), Path(sys.argv[4]).resolve()
if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise ValueError('Section hash mismatch')
if not 0 < scale < float('inf') or output.exists():
    raise ValueError('Finite positive scale and new output required')
for parent in output.parents:
    if (parent / '.git').exists() and output.relative_to(parent).parts[0] != 'work':
        raise ValueError('Scan derivatives must stay in ignored work/')
os.umask(0o077)
data = json.loads(source.read_text())
if data['schema'] != '935-observed-section-loft-v1' or not data['blades']:
    raise ValueError('No observed section lofts')
output.mkdir(parents=True, mode=0o700)
doc = App.newDocument('935PartialObservedBladeRegions')
solids = []
for i, blade in enumerate(data['regions']):
    sections = []
    for j, row in enumerate(blade['profiles']):
        # Exact samples of the fitted periodic spline. A second spline interpolation
        # overshot one thin contour and produced an invalid BRep in the real scan.
        points = [App.Vector(*[x * scale for x in point]) for point in row]
        section = doc.addObject('Part::Feature', f'Blade{i}Section{j}')
        section.Shape = Part.makePolygon(points + [points[0]])
        sections.append(section)
    loft = doc.addObject('Part::Loft', f'Blade{i}ObservedRegion')
    loft.Sections = sections; loft.Solid = True; loft.Ruled = True; loft.Closed = False
    loft.Label = f'{blade["id"]} - cropped observed region; root/tip absent'
    loft.addProperty('App::PropertyString', 'SectionInputSHA256').SectionInputSHA256 = expected
    loft.addProperty('App::PropertyFloat', 'AssumedMmPerSourceUnit').AssumedMmPerSourceUnit = scale
    solids.append(loft)
doc.recompute()
if any(not s.Shape.isValid() or len(s.Shape.Solids) != 1 or s.Shape.Volume <= 0 for s in solids):
    raise ValueError('Invalid BRep blade loft; output retained for diagnosis')
doc.saveAs(str(output / 'observed-blade-regions.FCStd'))
Part.export(solids, str(output / 'observed-blade-regions.step'))
expected_volume = sum(s.Shape.Volume for s in solids)
step = Part.read(str(output / 'observed-blade-regions.step'))
if not step.isValid() or abs(step.Volume - expected_volume) > expected_volume * 1e-6:
    raise ValueError('STEP reread does not preserve volume')
App.closeDocument(doc.Name)
reopened = App.openDocument(str(output / 'observed-blade-regions.FCStd'))
if len([o for o in reopened.Objects if o.TypeId == 'Part::Loft']) != len(solids):
    raise ValueError('Editable lofts lost on native CAD reread')
if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise ValueError('Section input changed during CAD reconstruction')
receipt = {'status': 'partial_observed_blade_regions_native_editable_lofts', 'sections_sha256': expected,
           'section_representation': 'sampled_periodic_spline_polygon_ruled_BRep',
           'FreeCAD_version': App.Version()[:3], 'assumed_mm_per_source_unit': scale,
           'conditional_volume_mm3': expected_volume, 'STEP_reread_volume_preserved': True,
           'scale_verified': False, 'root_tip_hub_reconstructed': False, 'manufacturing_authorized': False,
           'artifacts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}}
(output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
App.closeDocument(reopened.Name)
print('Private editable BRep lofts saved and reread; incomplete rotor')
