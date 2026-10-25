"""Reuse audited STL moments and frozen density cards; retain conditional scale."""
from pathlib import Path
from stl_moments import moments
from run_reconstruction import ROOT, save, sha
import json
p=ROOT/'work/935-snap-resume-20261025';mesh=p/'field-root-repair-002/rotor-0p6/rotor_candidate.stl'
proof=json.loads((p/'field-root-audit-002/native-intersection-assessment.json').read_text())
assert proof['candidate_sha256']==sha(mesh) and proof['full_surface_self_intersections_passed']
r=moments(mesh);source=ROOT/'twins/935-horizontal-cooling-system-f0/vast-omniverse-screen/materials.json';cards=json.loads(source.read_text());v=r['conditional_volume_mm3'];old=430665.5705673645
mats=[dict(id=m['id'],density_g_cm3=m['density_g_cm3'],conditional_mass_kg=v*m['density_g_cm3']*1e-6) for m in cards['materials']]
r.update(geometry_sha256=sha(mesh),source_sha256=sha(ROOT/'twins/935-horizontal-cooling-system-f0/source/stl_moments.py'),material_cards_sha256=sha(source),mass_cases=mats,volume_added_source_units_cubed=v-old,volume_relative_change=v/old-1,scale_verified=False,source_unit_assumed_mm=True,physical_validation=False,manufacturing_authorized=False,topology_reference_sha256=sha(p/'field-root-audit-002/native-intersection-assessment.json'))
assert abs(v-431013.60111809644)<1e-6
assert not (p/'field-root-audit-002/moments-reproduction.json').exists();save(p/'field-root-audit-002/moments-reproduction.json',r)
assert r==json.loads((p/'field-root-audit-002/moments.json').read_text())
print('Moments reproduced with unchanged geometry and material cards',flush=True)
