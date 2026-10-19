import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    import shapely
    from shapely.geometry import Polygon
except ImportError:
    shapely = None

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/process-skins-20261016/combinatorial_interfaces.py'
SPEC = importlib.util.spec_from_file_location('carrier_combinatorial_interfaces', SOURCE)
if shapely is not None and hasattr(shapely, 'constrained_delaunay_triangles'):
    MODULE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MODULE)


@unittest.skipUnless(shapely is not None and hasattr(shapely, 'constrained_delaunay_triangles'),
                     'Constrained-triangulation runtime required')
class CombinatorialInterfacesTests(unittest.TestCase):
    def test_box_plate_and_continuous_upper_strip(self):
        domain = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        result, proof = MODULE.construct(domain, dict(upper=[[[0, 10], [10, 10]]], lower=[[[0, 0], [10, 0]]]), .2)
        self.assertEqual(result.bounds, (0, 0, 10, 10.2))
        self.assertTrue(proof['exact_positive_triangle_boundary_chain_equal'])
        self.assertEqual(proof['polygon_overlay_operations'], 0)
        self.assertTrue(MODULE._BAND.prove_band_covered(result, domain, .2)['passed'])

    def test_hole_preserves_gap_and_subdivides_collinear_boundaries(self):
        domain = Polygon([(0, 10), (10, 10), (10, 30), (0, 30)], holes=[[(3, 17), (3, 23), (7, 23), (7, 17)]])
        result, proof = MODULE.construct(domain, dict(upper=[[[0, 30], [10, 30]], [[3, 17], [7, 17]]],
            lower=[[[0, 10], [10, 10]], [[3, 23], [7, 23]]]), .2)
        self.assertEqual(len(result.interiors), 1)
        self.assertEqual(Polygon(result.interiors[0]).bounds, (3, 17.2, 7, 22.8))
        self.assertEqual(proof['included_strips'], 4)
        self.assertTrue(MODULE._BAND.prove_band_covered(result, domain, .2)['passed'])

    def test_partial_attestation_is_not_rounded_into_whole_edge(self):
        domain = Polygon([(0, 10), (10, 10), (10, 20), (0, 20)])
        result, proof = MODULE.construct(domain, dict(upper=[[[2, 20], [8, 20]]], lower=[]), .2)
        self.assertTrue(result.equals_exact(domain, 0, normalize=True))
        self.assertEqual(proof['included_strips'], 0)
        self.assertEqual(proof['partially_attested_edges_not_extended'], 1)

    def test_one_ulp_source_gap_never_attests_edge(self):
        import math
        domain = Polygon([(0, 10), (10, 10), (10, 20), (0, 20)])
        result, proof = MODULE.construct(domain, dict(upper=[[[0, math.nextafter(20., 30.)], [10, math.nextafter(20., 30.)]]], lower=[]), .2)
        self.assertEqual(proof['included_strips'], 0)
        self.assertTrue(result.equals_exact(domain, 0, normalize=True))

    def test_lower_strip_needing_plate_intersection_refuses(self):
        domain = Polygon([(0, .1), (10, .1), (10, 1), (0, 1)])
        with self.assertRaisesRegex(ValueError, 'plate intersection'):
            MODULE.construct(domain, dict(upper=[], lower=[[[0, .1], [10, .1]]]), .2)

    def test_contradictory_roles_refuse(self):
        domain = Polygon([(0, 10), (10, 10), (10, 20), (0, 20)])
        with self.assertRaisesRegex(ValueError, 'contradictory'):
            MODULE.construct(domain, dict(upper=[[[0, 20], [10, 20]]], lower=[[[0, 20], [10, 20]]]), .2)

    def test_exact_nonadjacent_crossing_refuses(self):
        with self.assertRaisesRegex(ValueError, 'cross or meet'):
            MODULE._exact_boundary_check(Polygon([(0, 0), (10, 10), (0, 10), (10, 0)]))

    def test_exact_adjacent_overlap_refuses(self):
        with self.assertRaisesRegex(ValueError, 'overlap'):
            MODULE._exact_boundary_check(Polygon([(0, 0), (10, 0), (5, 0), (5, 10), (0, 10)]))

    def test_positive_triangle_duplicate_refuses_boundary_multiplicity(self):
        q = MODULE.Q
        tri = [(q(0), q(0)), (q(1), q(0)), (q(0), q(1))]
        with self.assertRaisesRegex(ValueError, 'multiplicity'):
            MODULE._assemble([tri, tri])

    def test_flat_snapshot_import_keeps_the_pinned_math_dependencies(self):
        audit = SOURCE.parent.parent/'process-scanpath-audit-20261016'
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            shutil.copy2(SOURCE, target/SOURCE.name)
            for name in ['exact_band_union.py', 'exact_intended_holes.py', 'exact_polygon_coverage.py', 'exact_contacts.py']:
                shutil.copy2(audit/name, target/name)
            code = ('import sys;sys.path.insert(0,sys.argv[1]);import combinatorial_interfaces as c;'
                    'from shapely.geometry import box;'
                    'r,p=c.construct(box(0,0,10,10),dict(upper=[[[0,10],[10,10]]],lower=[[[0,0],[10,0]]]),.2);'
                    'assert p["exact_positive_triangle_boundary_chain_equal"]')
            subprocess.run([sys.executable, '-I', '-B', '-c', code, str(target)], cwd='/', check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)


if __name__ == '__main__':
    unittest.main()
