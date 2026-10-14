import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

try:
    import numpy as np
except ImportError:
    np = None

SOURCE = Path(__file__).resolve().parents[1] / "twins/964-chassis/monocoque/source"
if np is not None:
    spec = importlib.util.spec_from_file_location("strength_audit", SOURCE / "strength_audit.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)


@unittest.skipIf(np is None, "numpy not installed")
class StrengthAuditTests(unittest.TestCase):
    def test_receipt_is_complete_source_bound_and_not_a_strength_approval(self):
        r = json.loads((SOURCE.parent / "derived/strength-audit-20261012.json").read_text())
        self.assertEqual(len(r["runs"]), 6)
        self.assertEqual(len(r["checks"]), 16)
        self.assertTrue(all(r["checks"].values()))
        self.assertTrue(r["numerical_checks_passed"])
        self.assertFalse(r["product_strength_validated"])
        self.assertFalse(r["model"]["vehicle_mass_applied_as_load"])
        self.assertEqual(r["runtime"]["threads"], 1)
        for name, digest in r["source_sha256"].items():
            self.assertEqual(hashlib.sha256((SOURCE.parent / name).read_bytes()).hexdigest(), digest, name)
        for row in r["runs"].values():
            self.assertEqual(row["stress"]["integration_points"], 2 * r["model"]["triangles"])
            self.assertIsNone(row["stress"]["strength_pass"])
            self.assertIsNone(row["stress"]["reserve_factor"])
            self.assertIn("shell.dat", row["files_sha256"])

    def fixture(self):
        return (" displacements (vx,vy,vz) for set NALL and time 1\n\n 1 0 0 -1\n\n"
                " forces (fx,fy,fz) for set NALL and time 1\n\n 1 0 0 0\n\n"
                " stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set E0 and time 1\n\n"
                " 1 1 10 0 0 0 0 0 _shell_0000000001\n\n"
                " global coordinates (elem, integ.pnt.,x,y,z) for set E0 and time 1\n\n 1 1 0 0 0.288675\n")

    def read(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shell.dat"
            path.write_text(text)
            return audit.read_dat(path)

    def test_parser_requires_all_fields_and_matching_ids(self):
        result = self.read(self.fixture())
        self.assertEqual(result["stress"][(1, 1)][0], 10)
        for bad in (self.fixture().split(" global coordinates")[0],
                    self.fixture().replace("1 1 0 0 0.288675", "2 1 0 0 0.288675"),
                    self.fixture().replace("1 1 10", "1 1 nan"),
                    self.fixture().replace("1 0 0 -1", "1 0 0 -1\n 1 0 0 -1")):
            with self.assertRaises(ValueError):
                self.read(bad)

    def test_signed_principals_and_no_strength_claim(self):
        r = audit.stress_summary([[10, 0, 0, 0, 0, 0], [-20, 0, 0, 0, 0, 0]], [[0, 0, 1], [0, 0, -1]])
        self.assertEqual(r["max_principal_MPa"], 10)
        self.assertEqual(r["min_principal_MPa"], -20)
        self.assertEqual(r["von_mises_max_MPa"], 20)
        self.assertIsNone(r["strength_pass"])
        self.assertIsNone(r["reserve_factor"])
        self.assertEqual(audit.relative_error(np.array([-2., 4.]), -2 * np.array([1., -2.])), 0)
        self.assertGreater(audit.relative_error(np.array([-2., 4.1]), np.array([-2., 4.])), audit.TOLERANCE)

    def test_retained_run_never_overwrites_and_keeps_failed_log(self):
        p = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        tri = np.array([[0, 1, 2]])
        sec = [(np.ones(1, bool), 1, 70000, .3)]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            with patch.object(audit.tr.subprocess, "run") as solver:
                solver.return_value.stdout = "Job finished"
                solver.return_value.stderr = "failure"
                solver.return_value.returncode = 1
                with self.assertRaises(SystemExit):
                    audit.tr.run(p, tri, sec, [(np.array([0]), 1, 6)], [], output_dir=run)
            self.assertIn("failure", (run / "solver.log").read_text())
            deck = (run / "shell.inp").read_text()
            self.assertIn("*EL PRINT, ELSET=E0, GLOBAL=YES\nS, COORD", deck)
            self.assertIn("*NODE PRINT, NSET=NALL\nU, RF", deck)
            with self.assertRaises(FileExistsError):
                audit.tr.run(p, tri, sec, [], [], output_dir=run)

    @unittest.skipUnless(shutil.which("ccx"), "ccx not on PATH")
    def test_cantilever_integration_stress_retains_bending(self):
        # Compare away from the clamp and tip; S3 is an approximate plate model.
        nx, ny = 80, 8
        p = np.array([[100 * i / nx, 10 * j / ny, 0] for i in range(nx + 1) for j in range(ny + 1)])
        tri = []
        for i in range(nx):
            for j in range(ny):
                a = i * (ny + 1) + j
                b = a + ny + 1
                tri.extend(((a, b, b + 1), (a, b + 1, a + 1)))
        tri = np.array(tri)
        tip, root = np.where(p[:, 0] == 100)[0], np.where(p[:, 0] == 0)[0]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "plate"
            _, vm2d = audit.tr.run(p, tri, [(np.ones(len(tri), bool), 1., 70000., .3)],
                                  [(root, 1, 6)], [(tip, 3, np.full(len(tip), -1 / len(tip)))], output_dir=run)
            d = audit.read_dat(run / "shell.dat")
            keys = sorted(d["stress"])
            stress = np.array([d["stress"][k] for k in keys])
            coord = np.array([d["coord"][k] for k in keys])
            mid = (coord[:, 0] > 30) & (coord[:, 0] < 70)
            expected = (100 - coord[mid, 0]) * coord[mid, 2] / (10 / 12)
            self.assertLess(audit.relative_error(stress[mid, 0], expected), .15)
            self.assertGreater(stress[mid, 0].max(), 1)
            self.assertLess(stress[mid, 0].min(), -1)
            # OUTPUT=2D retains transverse shear; compare only the interior,
            # not the local clamp stresses or a fictitious zero stress field.
            mid_nodes = (p[:, 0] > 30) & (p[:, 0] < 70)
            self.assertLess(vm2d[mid_nodes].max(), .1 * np.abs(stress[mid, 0]).max())


if __name__ == "__main__":
    unittest.main()
