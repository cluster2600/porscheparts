"""The stricter admission binds certified planar intervals to actual material."""
from pathlib import Path
import copy
import importlib.util
import sys
import unittest
from unittest.mock import patch
import json
import tempfile
if importlib.util.find_spec('pyslm') is None:raise unittest.SkipTest('Optional coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support,'_triangulate_exact_projected_domain'):raise unittest.SkipTest('Coverage runtime required')
import shapely
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
from continuous_prism_interfaces import repair
from grid_intervals import contacts
from admissions_v2 import continuous_admission

class ContinuousAdmissions(unittest.TestCase):
 def example(self):
  free=shapely.box(0,0,10,1);native=shapely.union_all([shapely.box(0,0,1,.3),shapely.box(8,.7,9,1.1)])
  interfaces=dict(upper=[[[0,1],[10,1]]],lower=[[[0,0],[10,0]]])
  material,receipt=repair(native,free,interfaces,.2)
  return receipt,contacts(material,free,interfaces)
 def test_bound_continuous_interval_is_admitted(self):
  receipt,actual=self.example();r=continuous_admission(receipt,actual,.2)
  self.assertTrue(r['exact_final_component_boundaries_identical'])
 def test_changed_final_material_cannot_borrow_interval_proof(self):
  receipt,actual=self.example();actual=copy.deepcopy(actual)
  component=next(r for r in actual if r['kind']=='generated_material_component')
  component['component_geometry_wkb_hex']=shapely.box(0,0,10,.8).wkb_hex
  with self.assertRaisesRegex(ValueError,'component identity'):continuous_admission(receipt,actual,.2)
 def test_false_proof_and_missing_normalization_are_refused(self):
  receipt,actual=self.example();bad=copy.deepcopy(receipt);bad['intervals'][0]['exact_free_domain_coverage']['passed']=False
  with self.assertRaisesRegex(ValueError,'proof differs'):continuous_admission(bad,actual,.2)
  bad=copy.deepcopy(receipt);bad['intervals'][0]['exact_intended_hole_normalization']['all_removed_holes_certified']=False
  with self.assertRaisesRegex(ValueError,'normalization'):continuous_admission(bad,actual,.2)
 def test_native_interval_cannot_borrow_legacy_zero_area_without_exact_band_proof(self):
  free=shapely.box(0,0,10,1);interfaces=dict(upper=[[[0,1],[10,1]]],lower=[[[0,0],[10,0]]])
  material,receipt=repair(free,free,interfaces,.2);actual=contacts(material,free,interfaces)
  self.assertFalse(receipt['intervals'][0]['continuous_interface_selected'])
  self.assertTrue(continuous_admission(receipt,actual,.2)['passed'])
  for removed in [None,False]:
   bad=copy.deepcopy(receipt)
   if removed is None:bad['intervals'][0]['exact_intended_band_union_confinement']=None
   else:del bad['intervals'][0]['exact_intended_band_union_confinement']
   with self.assertRaisesRegex(ValueError,'Every v2 interval'):continuous_admission(bad,actual,.2)
 def test_v2_seal_refuses_region_without_explicit_continuous_strategy(self):
  from admissions_v2 import seal
  for flag in [None,False]:
   with self.subTest(flag=flag),tempfile.TemporaryDirectory() as directory:
    directory=Path(directory);admission={}
    for key in ['envelopes','regions','skins','grids','contacts','collisions']:
     path=directory/f'admission-{key}.json';path.write_text(json.dumps(dict(passed=True,status='passed')))
     admission[key]=dict(status='passed',receipt=path.name,receipt_sha256='unused_stub')
    skin={} if flag is None else dict(continuous_fragmented_interfaces=flag)
    checkpoint=dict(supports=[dict(index=0,peripheral_skin=skin)],parameters={})
    with patch('admissions_v2.historical_seal',return_value=(admission,True)):
     result,passed=seal(directory,checkpoint,None)
    self.assertFalse(passed)
    self.assertEqual(result['contacts']['status'],'rejected')
 def test_intended_band_is_recomputed_when_rounded_overlay_omits_source_edge(self):
  from continuous_prism_interfaces import repair as prism_repair
  fixture=SOURCE.parent/'process-scanpath-audit-20261016/band-union-evidence/left-grid.json'
  data=json.loads(fixture.read_text());free=shapely.from_wkb(bytes.fromhex(data['geometry_wkb_hex']['free']))
  interfaces=dict(upper=[],lower=[])
  material,receipt=prism_repair(shapely.Polygon(),free,interfaces,.2)
  row=receipt['intervals'][0]
  self.assertFalse(row['exact_own_band_confinement']['passed'])
  self.assertTrue(row['exact_intended_band_union_confinement']['passed'])
  actual=contacts(material,free,interfaces)
  self.assertTrue(continuous_admission(receipt,actual,.2)['passed'])
  bad=copy.deepcopy(receipt);bad['intervals'][0]['exact_intended_band_union_confinement']['passed']=False
  with self.assertRaisesRegex(ValueError,'union proof differs'):continuous_admission(bad,actual,.2)
  # This proves only the planar band predicate. With no attested interfaces,
  # this fixture cannot pass the separate material-connection/anchor gate.
