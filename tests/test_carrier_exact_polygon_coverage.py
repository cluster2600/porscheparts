import importlib.util
import hashlib
import json
import math
from pathlib import Path
import unittest

try:
    from shapely.geometry import Polygon, MultiPolygon
except ImportError:
    Polygon = None

MODULE = None
if Polygon is not None:
    path = (Path(__file__).resolve().parents[1] /
            'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/exact_polygon_coverage.py')
    spec = importlib.util.spec_from_file_location('exact_polygon_coverage', path)
    MODULE = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(MODULE)


@unittest.skipIf(Polygon is None, 'Optional Shapely runtime is absent')
class ExactPolygonCoverageTests(unittest.TestCase):
    def setUp(self):
        self.square = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])

    def test_identical_polygon_and_extra_collinear_boundary_vertex_pass(self):
        target = Polygon([(0, 0), (2, 0), (4, 0), (4, 4), (0, 4)])
        receipt = MODULE.prove_polygon_covered(self.square, target)
        self.assertTrue(receipt['passed'])
        self.assertEqual(receipt['boundary_intervals_checked'], 5)
        self.assertEqual(len(receipt['source_geometry_sha256']), 64)

    def test_boundary_crossing_is_refused_even_when_source_vertices_are_inside(self):
        target = Polygon([(0, 0), (4, 0), (4, 4), (3, 4), (3, 2), (2, 2), (2, 4), (0, 4)])
        receipt = MODULE.prove_polygon_covered(self.square, target)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any(w['kind'] == 'source_boundary_interval_outside_target' for w in receipt['witnesses']))

    def test_strictly_internal_hole_cannot_pass_on_boundary_coverage_alone(self):
        target = Polygon(self.square.exterior.coords, holes=[[(1, 1), (3, 1), (3, 3), (1, 3)]])
        receipt = MODULE.prove_polygon_covered(self.square, target)
        self.assertTrue(receipt['entire_source_boundary_covered'])
        self.assertFalse(receipt['passed'])
        self.assertEqual(receipt['witnesses'][0]['kind'], 'target_hole_inside_source')

    def test_one_ulp_wide_hole_remains_a_real_refusal(self):
        x = math.nextafter(1., 2.)
        target = Polygon(self.square.exterior.coords, holes=[[(1, 1), (x, 1), (x, 2), (1, 2)]])
        self.assertFalse(MODULE.prove_polygon_covered(self.square, target)['passed'])

    def test_target_hole_inside_source_hole_is_allowed(self):
        source = Polygon(self.square.exterior.coords, holes=[[(1, 1), (3, 1), (3, 3), (1, 3)]])
        target = Polygon(self.square.exterior.coords, holes=[[(1.5, 1.5), (2.5, 1.5), (2.5, 2.5), (1.5, 2.5)]])
        self.assertTrue(MODULE.prove_polygon_covered(source, target)['passed'])
        self.assertFalse(MODULE.prove_polygon_covered(target, source)['passed'])

    def test_multipolygon_is_refused_instead_of_using_an_incomplete_hole_proof(self):
        target = MultiPolygon([Polygon([(x, y), (x+1, y), (x+1, y+1), (x, y+1)])
                               for x, y in [(0, 1), (1, 0), (2, 1), (1, 2)]])
        source = Polygon([(1, 1), (2, 1), (2, 2), (1, 2)])
        self.assertTrue(target.is_valid)
        with self.assertRaises(ValueError):
            MODULE.prove_polygon_covered(source, target)

    def test_material_island_splitting_a_hole_requires_both_complements(self):
        outer = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
                        holes=[[(2, 2), (8, 2), (8, 8), (2, 8)]])
        island = Polygon([(2, 5), (5, 4), (8, 5), (5, 6)])
        target = MultiPolygon([outer, island])
        source = Polygon([(2, 2), (8, 2), (8, 5), (5, 4), (2, 5)])
        self.assertTrue(target.is_valid)
        with self.assertRaises(ValueError):
            MODULE.prove_polygon_covered(source, target)

    def test_source_multipolygon_is_also_outside_the_single_interval_contract(self):
        source = MultiPolygon([Polygon([(x, 1), (x+1, 1), (x+1, 2), (x, 2)]) for x in [0.5, 2.5]])
        with self.assertRaises(ValueError):
            MODULE.prove_polygon_covered(source, self.square)

    def test_invalid_or_empty_input_cannot_supply_a_pass(self):
        for bad in [Polygon(), Polygon([(0, 0), (2, 2), (0, 2), (2, 0)])]:
            with self.assertRaises(ValueError):
                MODULE.prove_polygon_covered(bad, self.square)

    def test_real_chart35_overlay_loss_and_corrected_candidate_are_reproducible(self):
        import shapely
        directory = path.parent/'polygon-coverage-evidence'
        fixture = json.loads((directory/'chart35-inputs.json').read_text())
        saved = json.loads((directory/'chart35-assessment.json').read_text())
        self.assertEqual(hashlib.sha256((directory/'chart35-inputs.json').read_bytes()).hexdigest(),
                         saved['fixture_sha256'])
        geometries = {key: shapely.from_wkb(fixture[key]) for key in
                      ['source_domain_wkb_hex', 'original_union_wkb_hex', 'allowed_wkb_hex', 'candidate_wkb_hex']}
        pairs = [('source_domain_wkb_hex', 'original_union_wkb_hex'),
                 ('source_domain_wkb_hex', 'candidate_wkb_hex'),
                 ('candidate_wkb_hex', 'allowed_wkb_hex'),
                 ('source_domain_wkb_hex', 'allowed_wkb_hex')]
        for saved_case, (first, last) in zip(saved['cases'], pairs):
            actual = MODULE.prove_polygon_covered(geometries[first], geometries[last])
            self.assertEqual(actual, saved_case['receipt'])


if __name__ == '__main__':
    unittest.main()
