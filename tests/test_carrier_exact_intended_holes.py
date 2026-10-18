import importlib.util
import hashlib
import json
from pathlib import Path
import unittest

try:
    from shapely.geometry import Polygon, box
except ImportError:
    Polygon = None

MODULE = None
if Polygon is not None:
    path = (Path(__file__).resolve().parents[1] /
            'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/exact_intended_holes.py')
    spec = importlib.util.spec_from_file_location('exact_intended_holes', path)
    MODULE = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(MODULE)


@unittest.skipIf(Polygon is None, 'Optional Shapely runtime is absent')
class ExactIntendedHoleTests(unittest.TestCase):
    def setUp(self):
        self.outer = box(0, 0, 4, 4)
        self.hole = box(1, 1, 2, 2)
        self.result = Polygon(self.outer.exterior.coords, [self.hole.exterior.coords])

    def test_fully_covered_hole_is_removed_without_new_vertices_or_overlay(self):
        candidate, receipt = MODULE.normalize_holes(self.result, [self.outer], self.outer)
        self.assertEqual(len(candidate.interiors), 0)
        self.assertEqual(list(candidate.exterior.coords), list(self.result.exterior.coords))
        self.assertEqual(receipt['removed_hole_indices'], [0])
        self.assertEqual(receipt['new_vertices_introduced'], 0)
        self.assertEqual(receipt['polygon_overlay_operations'], 0)
        self.assertTrue(receipt['all_removed_holes_certified'])

    def test_genuine_hole_missing_from_intended_union_is_retained(self):
        candidate, receipt = MODULE.normalize_holes(self.result, [self.result], self.outer)
        self.assertEqual(candidate.wkb, self.result.wkb)
        self.assertEqual(receipt['removed_hole_indices'], [])
        self.assertFalse(receipt['holes'][0]['intended_union_coverage']['passed'])

    def test_partial_hole_coverage_cannot_be_promoted_to_full_coverage(self):
        candidate, receipt = MODULE.normalize_holes(self.result, [box(0, 0, 1.5, 4)], self.outer)
        self.assertEqual(candidate.wkb, self.result.wkb)
        self.assertFalse(receipt['holes'][0]['intended_union_coverage']['passed'])
        cells = receipt['holes'][0]['intended_union_coverage']['cells']
        self.assertTrue(any(cell['covering_primitive_ids'] for cell in cells))
        self.assertTrue(any(not cell['covering_primitive_ids'] for cell in cells))

    def test_collective_union_coverage_is_proved_across_a_real_cell_partition(self):
        candidate, receipt = MODULE.normalize_holes(self.result,
            [box(0, 0, 1.5, 4), box(1.5, 0, 4, 4)], self.outer)
        self.assertEqual(len(candidate.interiors), 0)
        proof = receipt['holes'][0]['intended_union_coverage']
        self.assertTrue(proof['exact_area_conserved'])
        self.assertEqual(len(proof['cells']), 2)

    def test_allowed_domain_too_small_retains_even_an_intended_hole(self):
        candidate, receipt = MODULE.normalize_holes(self.result, [self.outer], box(0, 0, 1.5, 4))
        self.assertEqual(candidate.wkb, self.result.wkb)
        self.assertFalse(receipt['holes'][0]['allowed_coverage']['passed'])

    def test_nonconvex_hole_is_retained_with_explicit_absent_certificate(self):
        ring = [(1, 1), (2, 1), (2, 1.5), (1.5, 1.5), (1.5, 2), (1, 2)]
        result = Polygon(self.outer.exterior.coords, [ring])
        candidate, receipt = MODULE.normalize_holes(result, [self.outer], self.outer)
        self.assertEqual(candidate.wkb, result.wkb)
        self.assertEqual(receipt['holes'][0]['status'], 'retained_no_convex_certificate')
        self.assertIsNone(receipt['holes'][0]['intended_union_coverage'])

    def test_empty_primitive_list_and_invalid_polygons_are_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.normalize_holes(self.result, [], self.outer)
        with self.assertRaises(ValueError):
            MODULE.normalize_holes(Polygon(), [self.outer], self.outer)

    def test_result_without_holes_is_byte_identical(self):
        candidate, receipt = MODULE.normalize_holes(self.outer, [self.outer], self.outer)
        self.assertEqual(candidate.wkb, self.outer.wkb)
        self.assertEqual(receipt['holes'], [])

    def test_real_skin576_holes_and_post_normalization_inclusions(self):
        import shapely
        directory = path.parent/'intended-hole-evidence'
        fixture = directory/'skin576-inputs.json'
        data = json.loads(fixture.read_text())
        saved = json.loads((directory/'skin576-assessment.json').read_text())
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(), saved['fixture_sha256'])
        domain = shapely.from_wkb(data['domain_wkb_hex'])
        result = shapely.from_wkb(data['result_wkb_hex'])
        allowed = shapely.from_wkb(data['allowed_wkb_hex'])
        primitives = [domain, *[shapely.from_wkb(item['geometry_wkb_hex']) for item in data['strips']]]
        candidate, receipt = MODULE.normalize_holes(result, primitives, allowed)
        self.assertEqual(receipt, saved['normalization'])
        self.assertEqual(receipt['removed_hole_indices'], [0, 1, 2, 3])
        self.assertEqual(candidate.wkb_hex, saved['candidate_wkb_hex'])
        self.assertEqual(MODULE._COVERAGE.prove_polygon_covered(domain, result), saved['original_coverage'])
        self.assertEqual(MODULE._COVERAGE.prove_polygon_covered(domain, candidate), saved['final_D_coverage'])
        self.assertEqual(MODULE._COVERAGE.prove_polygon_covered(candidate, allowed), saved['final_allowed_confinement'])
        self.assertFalse(saved['original_coverage']['passed'])
        self.assertTrue(saved['final_D_coverage']['passed'])
        self.assertTrue(saved['final_allowed_confinement']['passed'])


if __name__ == '__main__':
    unittest.main()
