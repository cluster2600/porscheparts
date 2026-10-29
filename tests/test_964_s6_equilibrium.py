"""Force/moment postprocessing and admission, independent of a vehicle claim."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("NumPy is required for the equilibrium audit")

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "twins/964-chassis/monocoque/s6-equilibrium-20261029"
SPEC = importlib.util.spec_from_file_location("s6_equilibrium", STUDY / "audit.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class EquilibriumTests(unittest.TestCase):
    def test_zero_force_can_hide_a_nonzero_moment(self):
        result = AUDIT.resultants([[0, -1, 0], [0, 1, 0]], [[0, 0, -10], [0, 0, 10]], [0, 0, 0])
        self.assertEqual(result["force_N"], [0, 0, 0])
        self.assertEqual(result["moment_Nmm"], [20, 0, 0])
        screen = AUDIT.balance(result, 20, 20)
        self.assertTrue(screen["force"]["numerical_screen_passed"])
        self.assertFalse(screen["moment"]["numerical_screen_passed"])

    def test_origin_translation_obeys_vector_identity(self):
        points = [[1, 2, 3], [-2, 1, 4]]
        forces = [[4, -2, 1], [3, 2, -4]]
        offset = np.array([200, -400, 75])
        a = AUDIT.resultants(points, forces, [0, 0, 0])
        b = AUDIT.resultants(points, forces, offset)
        np.testing.assert_allclose(b["moment_Nmm"], np.array(a["moment_Nmm"]) - np.cross(offset, a["force_N"]))

    def test_printing_interval_bounds_products_and_detects_large_error(self):
        p = np.array([[0., 2., 3.]])
        f = np.array([[5., 7., 11.]])
        dp, df = np.full((1, 3), .1), np.full((1, 3), .01)
        baseline = AUDIT.resultants(p, f, [0, 0, 0], dp, df)
        for sign in (-1, 1):
            changed = AUDIT.resultants(p + sign*dp, f - sign*df, [0, 0, 0])
            self.assertTrue((abs(np.array(changed["moment_Nmm"]) - baseline["moment_Nmm"]) <=
                             np.array(baseline["moment_printing_bound_Nmm"]) + 1e-12).all())
        result = {"force_N": [0, 0, .001], "moment_Nmm": [.002, 0, 0],
                  "force_printing_bound_N": [.002]*3, "moment_printing_bound_Nmm": [.003]*3}
        screen = AUDIT.balance(result, 1, 1)["force"]
        self.assertTrue(screen["printing_interval_contains_zero"])
        self.assertFalse(screen["numerical_screen_passed"])
        result["force_N"][2] = .1
        self.assertFalse(AUDIT.balance(result, 1, 1)["force"]["numerical_screen_passed"])
        with self.assertRaises(ValueError):
            AUDIT.balance(result, 0, 1)

    def test_decimal_precision_is_not_a_material_tolerance(self):
        self.assertEqual(AUDIT.printed_number(" 1.23450E+03"), (1234.5, .005))
        self.assertEqual(AUDIT.printed_number("-1.23450D-02"), (-.012345, 5e-8))
        with self.assertRaises(ValueError):
            AUDIT.printed_number("nan")
        with self.assertRaises(ValueError):
            AUDIT.resultants([[0, 0, 0]], [[0, 0, float("nan")]], [0, 0, 0])

    def test_only_requested_output_changes(self):
        old = "*NODE FILE, OUTPUT=2D\nU\n*EL FILE, OUTPUT=2D\nS\n"
        prefix = "*NODE\n1,0,0,0\n*STEP\n*STATIC\n*CLOAD\n1,3,-1\n"
        suffix = "*NODE PRINT,NSET=NALL\nU,RF\n*END STEP\n"
        changed = AUDIT.expanded_deck(prefix + old + suffix)
        self.assertTrue(changed.startswith(prefix))
        self.assertTrue(changed.endswith(suffix))
        self.assertIn("*NODE FILE, OUTPUT=3D\nU, RF\n", changed)
        for bad in (prefix, old + old):
            with self.assertRaises(ValueError):
                AUDIT.expanded_deck(bad)

    def test_unknown_source_is_rejected_before_output_or_solver(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "run-1").mkdir()
            (root / "run-1/shell.inp").write_text("unadmitted bytes")
            output = root / "new-output"
            argv = ["audit.py", "--torsion-source", str(root), "--bending-source", str(root),
                    "--output", str(output)]
            with mock.patch("sys.argv", argv), mock.patch.object(AUDIT, "solve") as solve:
                with self.assertRaisesRegex(ValueError, "Unadmitted"):
                    AUDIT.main()
                solve.assert_not_called()
            self.assertFalse(output.exists())
            output.mkdir()
            marker = output / "preserve.txt"
            marker.write_text("retained")
            with mock.patch("sys.argv", argv), mock.patch.object(AUDIT, "solve") as solve:
                with self.assertRaises(FileExistsError):
                    AUDIT.main()
                solve.assert_not_called()
            self.assertEqual(marker.read_text(), "retained")

    def test_frd_exact_id_coverage_and_single_step_required(self):
        def row(node, v):
            return f" -1{node:10d}" + "".join(f"{x:12.5E}" for x in v) + "\n"
        good = "    2C\n" + row(7, [1, 2, 3]) + " -3\n -4 FORC\n" + row(7, [4, 5, 6]) + " -3\n"
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "test.frd"
            p.write_text(good)
            xyz, force, _, _ = AUDIT.read_frd(p)
            np.testing.assert_equal(xyz, [[1, 2, 3]])
            np.testing.assert_equal(force, [[4, 5, 6]])
            for bad in (good.replace(row(7, [4, 5, 6]), row(8, [4, 5, 6])),
                        good + " -4 FORC\n" + row(7, [4, 5, 6])):
                p.write_text(bad)
                with self.assertRaises(ValueError):
                    AUDIT.read_frd(p)

    def test_deck_loads_sum_and_dat_rejects_missing_or_duplicate_nodes(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "test.inp"
            p.write_text("*NODE\n7,1,2,3\n*CLOAD\n7,3,-4\n7,3,-5\n*BOUNDARY\nFIX,1,6\n")
            ids, _, forces, bc = AUDIT.read_deck(p)
            np.testing.assert_equal(forces, [[0, 0, -9]])
            self.assertEqual(bc, [["FIX", "1", "6"]])
            dat = Path(temp) / "test.dat"
            good = "displacements for set NALL\n7 0 0 1\nforces for set NALL\n7 0 0 -9\n"
            dat.write_text(good)
            u, rf = AUDIT.read_dat_vectors(dat, ids)
            np.testing.assert_equal(u, [[0, 0, 1]])
            np.testing.assert_equal(rf, [[0, 0, -9]])
            for bad in (good.replace("7 0 0 -9", "8 0 0 -9"), good + "7 0 0 -9\n"):
                dat.write_text(bad)
                with self.assertRaises(ValueError):
                    AUDIT.read_dat_vectors(dat, ids)

    def test_published_run_is_bound_and_not_a_vehicle_release(self):
        audit = json.loads((STUDY / "audit.json").read_text())
        upstream = json.loads((STUDY / "admissibility.json").read_text())
        self.assertEqual(AUDIT.sha(STUDY / "admissibility.json"), audit["admissibility_sha256"])
        self.assertEqual(AUDIT.sha(STUDY / "audit.py"), upstream["script_sha256"])
        self.assertFalse(upstream["vehicle_interface_admissible"])
        self.assertFalse(upstream["geometry_parameter_sweep_admissible"])
        self.assertFalse(upstream["strength_or_manufacturing_admissible"])
        for key in ("physical_validation", "mesh_converged", "manufacturing_authorized"):
            self.assertFalse(audit[key])
        self.assertIsNone(audit["strength_pass"])
        self.assertTrue(audit["numerical_screens_passed"])
        for case, row in audit["cases"].items():
            self.assertTrue(row["dat_byte_identical_to_retained"])
            self.assertGreater(row["expanded_nodes"], row["original_nodes"])
            receipt_path = AUDIT.REPLAY / ("bending/result-after-2.json" if case == "bending" else "result-after-2.json")
            old = json.loads(receipt_path.read_text())["runs"][0]
            hashes = old.get("file_hashes", old.get("files_sha256"))
            self.assertEqual(row["files_sha256"]["shell.dat"], hashes["shell.dat"])
            for screen in row["balance"].values():
                self.assertTrue(screen["numerical_screen_passed"])
                # These actual runs also pass before allowing any printing interval.
                self.assertLessEqual(screen["relative_residual_before_printing_bound"], 1e-4)
            self.assertIsNone(row["energy_correlation_passed"])
        witness = json.loads((STUDY / "witness.json").read_text())
        self.assertEqual(AUDIT.sha(STUDY / "cantilever_witness.py"), witness["script_sha256"])
        self.assertEqual(AUDIT.sha(STUDY / "audit.py"), witness["audit_script_sha256"])
        self.assertTrue(witness["dat_identical"])
        self.assertTrue(witness["known_missing_2d_moment_demonstrated"])
        self.assertFalse(witness["physical_validation"])


if __name__ == "__main__":
    unittest.main()
