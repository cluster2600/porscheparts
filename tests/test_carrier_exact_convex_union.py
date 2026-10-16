from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import unittest

try:
    import shapely
except ImportError:
    shapely = None

if shapely is not None:
    path = (Path(__file__).resolve().parents[1]/
            'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/exact_convex_union.py')
    spec = importlib.util.spec_from_file_location('carrier_exact_convex_union', path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)


def points(values):
    return [tuple(Q(c) for c in point) for point in values]


@unittest.skipIf(shapely is None, 'Optional geometry runtime required')
class ExactConvexUnion(unittest.TestCase):
    def setUp(self):
        self.triangle = points([(0, 0), (4, 0), (0, 4)])
        self.left = points([(0, 0), (2, 0), (2, 4), (0, 4)])
        self.right = points([(2, 0), (4, 0), (4, 4), (2, 4)])

    def test_collective_coverage_and_both_orientations_preserve_exact_area(self):
        for triangle in [self.triangle, self.triangle[::-1]]:
            for parts in [[self.left, self.right], [self.right[::-1], self.left[::-1]]]:
                receipt = audit.union_certificate(triangle, parts)
                self.assertTrue(receipt['passed'])
                self.assertEqual(receipt['exact_removed_area_mm2'], Q(8))
                self.assertEqual(receipt['exact_remaining_area_mm2'], 0)

    def test_empty_union_partial_coverage_and_exact_positive_sliver_are_refused(self):
        for parts in [[], [self.left], [points([(0, 0), (4, 0), (0, Q(4)-Q(1, 10**30))])]]:
            receipt = audit.union_certificate(self.triangle, parts)
            self.assertFalse(receipt['passed'])
            self.assertGreater(receipt['exact_remaining_area_mm2'], 0)
            self.assertTrue(receipt['uncovered_cells'])

    def test_overlaps_duplicates_and_point_contact_do_not_invent_coverage(self):
        self.assertTrue(audit.union_certificate(self.triangle, [self.left, self.left, self.right])['passed'])
        touching = points([(4, 0), (5, 0), (5, 1)])
        self.assertFalse(audit.union_certificate(self.triangle, [touching])['passed'])

    def test_float_nonconvex_repeated_and_zero_area_inputs_are_refused(self):
        for bad in [[(0., 0.), (4., 0.), (0., 4.)], points([(0, 0), (1, 0), (2, 0)]),
                    points([(0, 0, 0), (4, 0, 0), (0, 4, 0)]),
                    points([(0, 0), (4, 0), (1, 1), (4, 4), (0, 4)]), self.left+[self.left[0]]]:
            with self.assertRaises(ValueError):
                audit.union_certificate(self.triangle, [bad])

    @unittest.skipUnless(shapely is not None and hasattr(shapely, 'constrained_delaunay_triangles'),
                         'Optional Shapely constrained-triangulation runtime required')
    def test_same_actual_left_material_is_covered_with_successive_subtraction(self):
        spec = importlib.util.spec_from_file_location('isolated_actual_band_subtraction',
                                                      path.with_name('exact_band_union.py'))
        band = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(band)
        # This private test dispatch changes no source or admitted receipt.
        band._PARTITION._union_certificate = lambda triangle, boundaries: audit.union_certificate(
            triangle, [rings[0][:-1] for rings in boundaries])
        data = json.loads((path.parent/'band-union-evidence/left-grid.json').read_text())
        geometries = {k: shapely.from_wkb(bytes.fromhex(v)) for k, v in data['geometry_wkb_hex'].items()}
        receipt = band.prove_band_covered(geometries['result'], geometries['free'], data['penetration_mm'])
        self.assertTrue(receipt['passed'])
        self.assertEqual(receipt['material_triangulation']['triangles'], 102)
        self.assertEqual(receipt['intended_convex_primitives'], 95)
