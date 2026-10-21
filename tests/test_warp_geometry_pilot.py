"""Oracle and fail-closed contract checks; native Warp is optional locally."""

import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    import numpy as np
except ImportError:
    np = None


PILOT_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "warp-geometry" / "pilot.py"
SPEC = importlib.util.spec_from_file_location("warp_geometry_pilot", PILOT_PATH)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


class CommandContractTests(unittest.TestCase):
    def test_help_does_not_require_warp(self):
        result = subprocess.run([sys.executable, "-S", str(PILOT_PATH), "--help"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cuda:0", result.stdout)

    def test_cuda_is_default_and_ranges_are_bounded(self):
        self.assertEqual(pilot.parser().parse_args(["--output", "report.json"]).device, "cuda:0")
        for option, value in [("--samples", "63"), ("--samples", "1000001"),
                              ("--samples", "nan"), ("--repeats", "0"),
                              ("--repeats", "21"), ("--device", "cuda:1")]:
            with self.subTest(option=option, value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    pilot.parser().parse_args(["--output", "report.json", option, value])

    def test_existing_report_is_preserved_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            output.write_text("preserve me", encoding="utf-8")
            with mock.patch.object(pilot, "run_pilot") as run, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    pilot.main(["--output", str(output)])
            run.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")

    def test_dangling_output_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            output.symlink_to(Path(directory) / "missing.json")
            with mock.patch.object(pilot, "run_pilot") as run, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    pilot.main(["--output", str(output)])
            run.assert_not_called()

    def test_device_failure_has_nonzero_exit_and_failed_report(self):
        import json

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            with mock.patch.object(pilot, "run_pilot", side_effect=RuntimeError("CUDA unavailable")), \
                    contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pilot.main(["--output", str(output)]), 1)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "error")
            self.assertFalse(report["gpu_validated"])
            self.assertFalse(report["manufacturing_authorized"])

    def test_report_is_recoverable_from_marked_stdout(self):
        import json

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            stdout = io.StringIO()
            with mock.patch.object(pilot, "run_pilot", return_value={"status": "passed"}), \
                    contextlib.redirect_stdout(stdout):
                self.assertEqual(pilot.main(["--output", str(output)]), 0)
            payload = stdout.getvalue().split(pilot.REPORT_BEGIN + "\n", 1)[1].split(pilot.REPORT_END, 1)[0]
            self.assertEqual(json.loads(payload), json.loads(output.read_text(encoding="utf-8")))


@unittest.skipIf(np is None, "NumPy is not installed")
class AnalyticOracleTests(unittest.TestCase):
    def test_known_inside_surface_edges_and_outside_distances(self):
        probes = [[0, 0, 0], [0.5, 0, 0], [1, 0, 0], [1, 1, 0], [1, 1, 1],
                  [2, 0, 0], [2, 2, 0], [2, 2, 2], [-2, -2, -2]]
        expected = [1, 0.5, 0, 0, 0, 1, 2**0.5, 3**0.5, 3**0.5]
        np.testing.assert_allclose(pilot.box_surface_oracle(probes, [0, 0, 0], [1, 1, 1]), expected)

    def test_translation_is_independent_of_origin(self):
        points = np.array([[0, 0, 0], [2, 2, 2]], dtype=np.float64)
        shift = np.array([3.0, -7.0, 2.5])
        np.testing.assert_allclose(pilot.box_surface_oracle(points + shift, shift, [1, 1, 1]),
                                   pilot.box_surface_oracle(points, [0, 0, 0], [1, 1, 1]))

    def test_invalid_oracle_inputs_are_rejected(self):
        for points, half in [([[float("nan"), 0, 0]], [1, 1, 1]), ([[0, 0, 0]], [1, 0, 1]),
                             ([[0, 0]], [1, 1, 1])]:
            with self.subTest(points=points, half=half), self.assertRaises(ValueError):
                pilot.box_surface_oracle(points, [0, 0, 0], half)

    def test_box_is_closed_with_consistent_edges(self):
        vertices, triangles = pilot.box_mesh([0, 0, 0], [10, 15, 5])
        self.assertEqual(vertices.shape, (8, 3))
        edges = [(int(a), int(b)) for triangle in triangles
                 for a, b in zip(triangle, np.roll(triangle, -1))]
        self.assertEqual(len(set(edges)), 36)
        self.assertTrue(all((b, a) in edges for a, b in edges))
        for triangle in triangles:
            a, b, c = vertices[triangle]
            self.assertGreater(float(np.dot(np.cross(b - a, c - a), (a + b + c) / 3)), 0.0)

    def test_fixtures_are_deterministic_and_cover_the_contract(self):
        cases = pilot.make_cases(64)
        repeated = pilot.make_cases(64)
        self.assertEqual(len(cases), 3)
        for case, other in zip(cases, repeated):
            self.assertEqual(case["probes"].shape, (64, 3))
            self.assertEqual(pilot.fixture_hash(case), pilot.fixture_hash(other))
        surface = cases[0]
        np.testing.assert_array_equal(pilot.box_surface_oracle(surface["probes"], surface["center"],
                                                              surface["half_extent"]), np.zeros(64))
        mixed = cases[1]
        distances = pilot.box_surface_oracle(mixed["probes"], mixed["center"], mixed["half_extent"])
        self.assertEqual(distances[0], 5.0)
        self.assertEqual(distances[3], 0.0)
        self.assertEqual(distances[6], 1.0)
        translated = cases[2]
        shifted = pilot.box_surface_oracle(translated["probes"], translated["center"], translated["half_extent"])
        self.assertFalse(np.array_equal(distances, shifted))

    def test_modified_distance_fails_the_independent_assessor(self):
        expected = np.array([0.0, 1.0, 5.0])
        actual = expected.copy()
        self.assertTrue(pilot.assess_distances(actual, expected, [1, 1, 1])["passed"])
        actual[1] += pilot.TOLERANCE_MM * 2
        self.assertFalse(pilot.assess_distances(actual, expected, [1, 1, 1])["passed"])

    def test_missing_nonfinite_or_negative_results_fail(self):
        for actual, hits in [([0, 1], [1, 0]), ([0, float("nan")], [1, 1]),
                             ([0, float("inf")], [1, 1]), ([0, -1], [1, 1])]:
            with self.subTest(actual=actual, hits=hits):
                self.assertFalse(pilot.assess_distances(actual, [0, 1], hits)["passed"])

    def test_cuda_request_refuses_a_cpu_fallback_before_loading_kernel(self):
        fake_warp = SimpleNamespace(init=mock.Mock(), config=SimpleNamespace(),
                                    get_device=mock.Mock(return_value=SimpleNamespace(is_cuda=False)))
        with mock.patch.dict(sys.modules, {"warp": fake_warp}), mock.patch.object(pilot, "load_kernel") as kernel:
            with self.assertRaisesRegex(RuntimeError, "did not select a CUDA device"):
                pilot.run_pilot(64, 1, "cuda:0")
        fake_warp.get_device.assert_called_once_with("cuda:0")
        kernel.assert_not_called()


@unittest.skipUnless(np is not None and importlib.util.find_spec("warp") is not None,
                     "Native Warp is not installed")
class NativeWarpSmokeTests(unittest.TestCase):
    def test_cpu_dispatch_matches_oracle_and_never_claims_gpu_validation(self):
        report = pilot.run_pilot(64, 1, "cpu")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["device"]["type"], "cpu")
        self.assertTrue(report["cpu_smoke_only"])
        self.assertFalse(report["gpu_validated"])
        self.assertFalse(report["application_validated"])
        self.assertEqual(len(report["cases"]), 3)


if __name__ == "__main__":
    unittest.main()
