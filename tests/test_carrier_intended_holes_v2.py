import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

try:
    import shapely
    from shapely.geometry import Polygon, box
    HAS_RUNTIME = hasattr(shapely, 'from_wkb')
except ImportError:
    HAS_RUNTIME = False

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016'
if HAS_RUNTIME:
    spec = importlib.util.spec_from_file_location('carrier_hull_hole_v2', SOURCE/'exact_intended_holes_v2.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)


@unittest.skipUnless(HAS_RUNTIME, 'Optional Shapely WKB runtime required')
class IntendedHoleHulls(unittest.TestCase):
    def setUp(self):
        self.outer = box(0, 0, 6, 6)
        self.bowtie = [(1, 1), (3, 3), (1, 3), (3, 1)]
        self.invalid = Polygon(self.outer.exterior.coords, [self.bowtie])

    def test_covered_invalid_bowtie_is_removed_only_after_full_hull_proofs(self):
        self.assertFalse(self.invalid.is_valid)
        result, receipt = audit.normalize_holes(self.invalid, [self.outer], self.outer)
        self.assertTrue(result.is_valid)
        self.assertEqual(receipt['removed_holes'], [0])
        row = receipt['holes'][0]
        self.assertFalse(row['ring_polygon_valid'])
        self.assertTrue(row['allowed_coverage']['passed'])
        self.assertTrue(row['intended_union_coverage']['passed'])
        self.assertTrue(row['hull_certificate']['all_ring_segments_covered'])
        self.assertEqual(list(result.exterior.coords), list(self.invalid.exterior.coords))
        self.assertEqual(receipt['allowed_geometry_sha256'], hashlib.sha256(self.outer.wkb).hexdigest())
        self.assertEqual(receipt['intended_primitive_geometry_sha256'], [hashlib.sha256(self.outer.wkb).hexdigest()])
        self.assertTrue(receipt['exterior_and_retained_holes_unchanged'])

    def test_genuine_convex_and_nonconvex_holes_are_retained_when_not_intended(self):
        for hole in [list(box(1, 1, 3, 3).exterior.coords),
                     [(1, 1), (3, 1), (3, 2), (2, 2), (2, 3), (1, 3)]]:
            original = Polygon(self.outer.exterior.coords, [hole])
            result, receipt = audit.normalize_holes(original, [original], self.outer)
            self.assertEqual(result.wkb, original.wkb)
            self.assertEqual(receipt['removed_holes'], [])
            self.assertFalse(receipt['holes'][0]['intended_union_coverage']['passed'])

    def test_partial_primitive_coverage_cannot_repair_an_invalid_ring(self):
        with self.assertRaisesRegex(ValueError, 'valid Polygon') as caught:
            audit.normalize_holes(self.invalid, [box(0, 0, 2, 6)], self.outer)
        receipt = caught.exception.receipt
        self.assertEqual(receipt['status'], 'refused')
        self.assertEqual(receipt['removed_holes'], [])
        self.assertFalse(receipt['holes'][0]['intended_union_coverage']['passed'])

    def test_allowed_domain_that_does_not_cover_the_entire_hull_refuses_removal(self):
        with self.assertRaises(ValueError) as caught:
            audit.normalize_holes(self.invalid, [self.outer], box(0, 0, 2, 6))
        self.assertFalse(caught.exception.receipt['holes'][0]['allowed_coverage']['passed'])
        self.assertEqual(caught.exception.receipt['removed_holes'], [])

    def test_exterior_and_unproved_retained_ring_coordinates_are_unchanged(self):
        first, second = box(1, 1, 2, 2), box(4, 4, 5, 5)
        original = Polygon(self.outer.exterior.coords, [first.exterior.coords, second.exterior.coords])
        result, receipt = audit.normalize_holes(original, [original, first], self.outer)
        self.assertEqual(receipt['removed_holes'], [0])
        self.assertEqual(receipt['retained_holes'], [1])
        self.assertEqual(list(result.exterior.coords), list(original.exterior.coords))
        self.assertEqual(list(result.interiors[0].coords), list(original.interiors[1].coords))
        self.assertEqual(receipt['new_vertices'], 0)
        self.assertEqual(receipt['intended_primitive_geometry_sha256'],
                         [hashlib.sha256(p.wkb).hexdigest() for p in [original, first]])
        self.assertTrue(receipt['exterior_and_retained_holes_unchanged'])

    def test_invalid_exterior_and_invalid_intended_primitives_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'exterior'):
            audit.normalize_holes(Polygon(self.bowtie), [self.outer], self.outer)
        with self.assertRaisesRegex(ValueError, 'valid nonempty'):
            audit.normalize_holes(self.invalid, [self.invalid], self.outer)

    def test_a_hull_producer_cannot_add_vertices_not_from_the_source_ring(self):
        forged = Polygon([(0, 0), (6, 0), (0, 6)])
        with mock.patch.object(audit, 'MultiPoint', return_value=type('Hull', (), {'convex_hull':forged})()):
            with self.assertRaises(ValueError) as caught:
                audit.normalize_holes(self.invalid, [self.outer], self.outer)
        self.assertEqual(caught.exception.receipt['holes'][0]['status'], 'retained_no_hull_certificate')

    def test_real_source008_bowtie_capture_is_normalized_without_new_vertices(self):
        fixture = SOURCE/'hull-hole-evidence/source008-inputs.json'
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(),
                         'fe4d0304925280aaa5755bdc8c956942e277b9759a5472b601b6065b186d5e59')
        data = json.loads(fixture.read_text())
        self.assertEqual(data['capture_sha256'], '31256e58ddda18578c8b0828b06fee1007903b0a03f5e092a50af55bf1c31184')
        shapes = {name:shapely.from_wkb(bytes.fromhex(value)) for name, value in data['geometry_wkb_hex'].items()}
        original = shapes['result'].wkb
        primitives = [shapes['free'], *[shapely.from_wkb(bytes.fromhex(value)) for value in data['raw_addition_wkb_hex']]]
        result, receipt = audit.normalize_holes(shapes['result'], primitives, shapes['allowed'])
        self.assertEqual(receipt['removed_holes'], [0, 1])
        self.assertFalse(receipt['input_polygon_valid'])
        self.assertTrue(receipt['final_polygon_valid'])
        self.assertEqual(list(result.exterior.coords), list(shapes['result'].exterior.coords))
        self.assertEqual(shapes['result'].wkb, original)
        for row in receipt['holes']:
            self.assertTrue(row['hull_certificate']['hull_vertices_from_original_ring'])
            self.assertTrue(row['hull_certificate']['all_ring_segments_covered'])
            self.assertTrue(row['allowed_coverage']['passed'])
            self.assertTrue(row['intended_union_coverage']['passed'])


if __name__ == '__main__':
    unittest.main()
