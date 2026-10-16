import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import unittest

try:
    import shapely
    from shapely.geometry import Polygon, MultiPolygon, box
except ImportError:
    shapely = None
SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0, str(SOURCE))
AVAILABLE = shapely is not None and hasattr(shapely, 'constrained_delaunay_triangles')
if AVAILABLE:
    import continuous_combinatorial_interfaces as repair
    import exact_band_union_v2 as old
    import exact_band_union_v3 as new


@unittest.skipUnless(AVAILABLE, 'Constrained-triangulation runtime required')
class CombinatorialRepairTests(unittest.TestCase):
    def test_all_domain_retained_from_an_empty_native(self):
        free = box(0, 10, 10, 20)
        interfaces = dict(upper=[[[0, 20], [10, 20]]], lower=[[[0, 10], [10, 10]]])
        result, receipt = repair.repair(Polygon(), free, interfaces, .2)
        self.assertEqual(receipt['strategy'], 'continuous_domain_with_nonoverlapping_attested_edge_strips')
        self.assertEqual(receipt['polygon_overlay_operations_for_material'], 0)
        row = receipt['intervals'][0]
        self.assertTrue(row['exact_free_domain_coverage']['passed'])
        self.assertTrue(row['exact_intended_band_union_confinement']['passed'])
        self.assertEqual(row['generated_material_geometry_wkb_hex'], result.wkb_hex)
        self.assertEqual(row['attested_source_interfaces'], interfaces)

    def test_separate_intervals_remain_separate_without_union_overlay(self):
        free = MultiPolygon([box(0, 10, 10, 20), box(0, 30, 10, 40)])
        interfaces = dict(upper=[[[0, 20], [10, 20]], [[0, 40], [10, 40]]],
            lower=[[[0, 10], [10, 10]], [[0, 30], [10, 30]]])
        result, receipt = repair.repair(free, free, interfaces, .2)
        self.assertEqual(len(result.geoms), 2)
        self.assertEqual(len(receipt['intervals']), 2)

    def test_contact_strips_joining_distinct_intervals_refuse(self):
        free = MultiPolygon([box(0, 10, 10, 11), box(0, 11.1, 10, 12)])
        interfaces = dict(upper=[[[0, 11], [10, 11]], [[0, 12], [10, 12]]],
            lower=[[[0, 10], [10, 10]], [[0, 11.1], [10, 11.1]]])
        with self.assertRaisesRegex(ValueError, 'joins distinct'):
            repair.repair(free, free, interfaces, .2)

    def test_integer_halfplanes_preserve_all_primitive_choices_and_witnesses(self):
        free = Polygon(box(0, 1, 4, 5).exterior.coords, [box(1, 2, 3, 4).exterior.coords])
        for material in [free, box(0, 1, 4, 5), box(-.01, 1, 4, 5)]:
            a, b = old.prove_band_covered(material, free, .2), new.prove_band_covered(material, free, .2)
            self.assertEqual(a['passed'], b['passed'])
            self.assertEqual(a['triangles'], b['triangles'])
            self.assertEqual(a['primitives_sha256'], b['primitives_sha256'])
            self.assertEqual(a['material_triangulation'], b['material_triangulation'])

    def test_captured_carrier_intervals_reproduce_their_geometry_and_exact_gates(self):
        fixture = json.loads((SOURCE/'combinatorial-evidence/fixtures.json').read_text())
        for case in fixture['cases']:
            if case['name'] not in ['left', 'right']:
                continue
            with self.subTest(name=case['name']):
                domain = shapely.from_wkb(case['source_domain_geometry_wkb_hex'])
                self.assertEqual(hashlib.sha256(domain.wkb).hexdigest(), case['source_domain_geometry_sha256'])
                result, receipt = repair.repair(domain, domain, case['attested_source_interfaces'], fixture['penetration_mm'])
                self.assertEqual(hashlib.sha256(result.wkb).hexdigest(), case['generated_material_geometry_sha256'])
                row = receipt['intervals'][0]
                self.assertTrue(row['exact_free_domain_coverage']['passed'])
                self.assertTrue(row['exact_intended_band_union_confinement']['passed'])
                self.assertEqual(row['combinatorial_construction']['included_strips'], case['included_strips'])
                self.assertEqual(row['combinatorial_construction']['explicitly_excluded_strips'], case['excluded_strips'])


if __name__ == '__main__':
    unittest.main()
