"""Protect the future native fixture's exact reference and independent oracle."""
import importlib.util
from pathlib import Path
import struct
import unittest

PATH = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/check_finest_endpoint_fixtures.py"
SPEC = importlib.util.spec_from_file_location("finest_endpoint_fixture", PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class EndpointFixtureOracle(unittest.TestCase):
    def test_declared_closed_fixed_neighbor_fixture_and_oracle_reject_wrong_geometry(self):
        source = M.fixture(); expected = M.fixture(split=False)
        self.assertEqual((len(source[0]), len(source[1])), (10, 16))
        self.assertEqual(M.qualities(*source)["below_necessary_bound"], 2)
        self.assertEqual(M.closed_volume(*source), 152**3)
        self.assertEqual(M.closed_volume(*expected), 152**3)
        self.assertEqual([i for i, p in enumerate(source[0]) if abs(p[0]) != 76], [8, 9])
        neighbors = lambda i: {v for row in source[1] if i in row for v in row if v != i}
        self.assertEqual(neighbors(8) & neighbors(9), {5, 7})
        origins = b"".join(struct.pack("<Q", i) for i in range(9))
        report = M.assess_arrays(source, expected, expected, origins)
        self.assertEqual(report["after"]["below_necessary_bound"], 0)
        native = dict(full_surface_before=report["before"], full_surface_after=report["after"],
                      accepted_collapses=1, candidate_written=True, full_quality_objective=True,
                      fixed_source_coordinates_exact=True, exterior_oriented_faces_exact=True,
                      retained_coordinates_are_exact_source_points=True, closed_valid_triangle_mesh=True,
                      collapse_count_bookkeeping=True, geometry_budget_mm=0.0625, soft_stop_requested=False)
        M.require_native_flags(native, report, True)
        with self.assertRaises(ValueError):
            M.require_native_flags(dict(native, accepted_collapses=True), report, True)
        altered = list(expected[0]); altered[8] = (1/1024, 0, 76)
        with self.assertRaises(ValueError):
            M.assess_arrays(source, (altered, expected[1]), expected, origins)
        wrong_winding = list(expected[1]); wrong_winding[2] = tuple(reversed(wrong_winding[2]))
        with self.assertRaises(ValueError):
            M.assess_arrays(source, (expected[0], wrong_winding), expected, origins)
        with self.assertRaises(ValueError):
            M.assess_arrays(source, expected, expected, origins[:-8]+struct.pack("<Q", 9))
        rotated = M.fixture(rotated=True)
        self.assertTrue(all(abs(p[0]) == 76 for p in rotated[0]))
        self.assertEqual(M.closed_volume(*rotated), 152**3)
        self.assertEqual(M.qualities(*rotated)["below_necessary_bound"], 2)


if __name__ == "__main__":
    unittest.main()
