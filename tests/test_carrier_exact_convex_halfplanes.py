from dataclasses import FrozenInstanceError
from fractions import Fraction as Q
import importlib.util
import json
import math
from pathlib import Path
import unittest

try:
    import shapely
    SHAPELY_CDT = hasattr(shapely, 'constrained_delaunay_triangles')
except ImportError:
    SHAPELY_CDT = False

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016'
spec = importlib.util.spec_from_file_location('carrier_compiled_convex', SOURCE/'exact_convex_halfplanes.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def points(values):
    return [tuple(Q(c) for c in p) for p in values]


class ExactHalfplanes(unittest.TestCase):
    def test_closed_edges_and_vertices_for_both_orientations(self):
        polygon = points([(0, 0), (4, 0), (4, 3), (0, 3)])
        for vertices in (polygon, polygon[::-1]):
            compiled = audit.CompiledConvex(vertices)
            for p in [*polygon, (Q(2), Q(0)), (Q(4), Q(3, 2)), (Q(2), Q(1))]:
                self.assertTrue(compiled.contains(p))
            self.assertFalse(compiled.contains((Q(4)+Q(1, 10**60), Q(1))))
            self.assertTrue(all(isinstance(c, int) for line in compiled.halfplanes for c in line))

    def test_non_dyadic_coordinates_and_tiny_positive_sliver(self):
        a, b, c, d = Q(-7, 3), Q(11, 7), Q(2, 5), Q(19, 11)
        compiled = audit.CompiledConvex([(a, c), (b, c), (b, d), (a, d)])
        self.assertTrue(compiled.contains(((a+b)/2, (c+d)/2)))
        self.assertTrue(compiled.contains((a, c)))
        self.assertFalse(compiled.contains((a-Q(1, 10**70), c)))
        width = Q(1, 10**40)
        thin = audit.CompiledConvex([(Q(0), Q(0)), (width, Q(0)), (width, Q(1)), (Q(0), Q(1))])
        self.assertTrue(thin.contains_triangle([(Q(0), Q(0)), (width, Q(0)), (Q(0), Q(1))]))
        self.assertFalse(thin.contains((width+Q(1, 10**80), Q(1, 2))))

    def test_whole_triangle_is_decided_by_all_vertices(self):
        compiled = audit.CompiledConvex(points([(0, 0), (2, 0), (2, 2), (0, 2)]))
        self.assertTrue(compiled.contains_triangle(points([(0, 0), (2, 0), (0, 2)])))
        self.assertFalse(compiled.contains_triangle(points([(0, 0), (3, 0), (0, 2)])))

    def test_nonconvex_noncyclic_repeated_and_zero_area_primitives_are_refused(self):
        for polygon in [points([(0, 0), (3, 0), (1, 1), (3, 3), (0, 3)]),
                        points([(0, 0), (3, 3), (0, 3), (3, 0)]),
                        points([(0, 0), (2, 0), (1, 0)]),
                        points([(0, 0), (2, 0), (2, 2), (0, 0)])]:
            with self.assertRaises(ValueError):
                audit.CompiledConvex(polygon)

    def test_only_exact_two_dimensional_fraction_inputs_are_accepted(self):
        good = points([(0, 0), (2, 0), (0, 2)])
        for polygon in [[(0, 0), (2, 0), (0, 2)], [(Q(0), Q(0), Q(0)), *good[1:]]]:
            with self.assertRaises(ValueError):
                audit.CompiledConvex(polygon)
        compiled = audit.CompiledConvex(good)
        for point in [(0., 0.), (Q(0), Q(0), Q(0)), (Q(0),)]:
            with self.assertRaises(ValueError):
                compiled.contains(point)
        with self.assertRaises(ValueError):
            compiled.contains_triangle([good[0], good[0], good[1]])

    def test_compiled_coefficients_are_immutable(self):
        compiled = audit.CompiledConvex(points([(0, 0), (2, 0), (0, 2)]))
        with self.assertRaises(FrozenInstanceError):
            compiled.halfplanes = ((0, 0, 1),)

    @unittest.skipUnless(SHAPELY_CDT, 'Optional Shapely constrained-triangulation runtime required')
    def test_all_768_fixture_candidate_pairs_match_the_frozen_generic_predicate(self):
        import shapely
        from shapely.geometry import box
        band_path = SOURCE.parent/'process-skins-20261016/exact_band_union_v2.py'
        spec = importlib.util.spec_from_file_location('fixture_frozen_band', band_path)
        band = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(band)
        data = json.loads((SOURCE/'band-union-evidence/left-grid.json').read_text())
        shapes = {k:shapely.from_wkb(bytes.fromhex(v)) for k, v in data['geometry_wkb_hex'].items()}
        triangles, _ = band._BASE._triangulation(shapes['result'])
        primitives, _ = band._BASE._primitives(shapes['free'], data['penetration_mm'])
        compiled = [audit.CompiledConvex(p) for p in primitives]
        boxes = [box(math.nextafter(float(min(p[0] for p in ps)), -math.inf),
                     math.nextafter(float(min(p[1] for p in ps)), -math.inf),
                     math.nextafter(float(max(p[0] for p in ps)), math.inf),
                     math.nextafter(float(max(p[1] for p in ps)), math.inf)) for ps in primitives]
        tree, pairs = shapely.STRtree(boxes), 0
        for triangle in triangles:
            extent = box(min(float(p[0]) for p in triangle), min(float(p[1]) for p in triangle),
                         max(float(p[0]) for p in triangle), max(float(p[1]) for p in triangle))
            for index in sorted(int(i) for i in tree.query(extent)):
                old = all(band._BASE._EXACT.inside([primitives[index]+[primitives[index][0]]], p) for p in triangle)
                self.assertEqual(compiled[index].contains_triangle(triangle), old)
                pairs += 1
        self.assertEqual((len(triangles), len(primitives), pairs), (102, 95, 768))


if __name__ == '__main__':
    unittest.main()
