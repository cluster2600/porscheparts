"""The faster verifier retains exact primitives and a concrete rejection witness."""
import importlib.util
from pathlib import Path
import sys
import unittest

try:
 import shapely
 from shapely.geometry import Polygon,box
except ImportError:shapely=None
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
if shapely is not None:
 import exact_band_union_v2 as proof


@unittest.skipUnless(shapely is not None and hasattr(shapely,'constrained_delaunay_triangles'),'Constrained-triangulation runtime required')
class BandUnionV2(unittest.TestCase):
 def test_same_primitives_and_decisions_as_original_on_hole_and_plate(self):
  free=Polygon(box(0,1,4,5).exterior.coords,[box(1,2,3,4).exterior.coords])
  for material in [free,box(0,1,4,5),box(-.01,1,4,5)]:
   old=proof._BASE.prove_band_covered(material,free,.2);new=proof.prove_band_covered(material,free,.2)
   self.assertEqual(new['passed'],old['passed'])
   self.assertEqual(new['primitives_sha256'],old['primitives_sha256'])
   self.assertEqual(new['material_triangulation'],old['material_triangulation'])
  self.assertFalse(proof.prove_band_covered(box(0,-.01,2,1),box(0,0,2,1),.2)['passed'])
 def test_first_failed_triangle_retains_exact_uncovered_cell(self):
  result=proof.prove_band_covered(box(-1,1,2,3),box(0,1,2,3),.2)
  self.assertFalse(result['passed']);self.assertTrue(result['stopped_at_first_uncovered_triangle'])
  self.assertTrue(result['triangles'][-1]['receipt']['uncovered_cells'])
  self.assertGreater(int(result['triangles'][-1]['receipt']['exact_remaining_area_mm2']['numerator']),0)
