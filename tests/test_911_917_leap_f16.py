import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/vehicle-911-917/source"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("leap_f16", SOURCE / "run_leap_f16.py")
f16 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f16)
spec = importlib.util.spec_from_file_location("prepare_linux_leap_root", SOURCE / "prepare_linux_leap_root.py")
prep = importlib.util.module_from_spec(spec); spec.loader.exec_module(prep)


class LeapF16Tests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((f16.STUDY / "study.json").read_text())

    def test_declared_scope(self):
        f16.validate_config(self.config)
        self.assertEqual(len(f16.PARTS), 10)

    def test_rejects_promoted_gates(self):
        for key in f16.GATES:
            c = copy.deepcopy(self.config); c[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                f16.validate_config(c)

    def test_rejects_units_and_resolution(self):
        for key, value in (("units", "inch"), ("voxel_size_mm", 2.5)):
            c = copy.deepcopy(self.config); c[key] = value
            with self.assertRaises(ValueError): f16.validate_config(c)

    def test_rejects_unresolved_or_nonfinite_dimensions(self):
        for value in (0, 5, -1, True, float("nan"), float("inf")):
            c = copy.deepcopy(self.config); c["duct_wall_mm"] = value
            with self.subTest(value=value), self.assertRaises(ValueError): f16.validate_config(c)

    def test_rejects_missing_or_degenerate_routes(self):
        for mode in ("missing", "repeated", "far"):
            c = copy.deepcopy(self.config)
            if mode == "missing": c["ducts"].pop()
            if mode == "repeated": c["ducts"][0]["control_points_mm"][1] = c["ducts"][0]["control_points_mm"][0]
            if mode == "far": c["ducts"][0]["control_points_mm"][0][0] = 10000
            with self.subTest(mode=mode), self.assertRaises(ValueError): f16.validate_config(c)

    def test_native_receipt_when_available(self):
        directory = os.environ.get("PICOGK_F16_RESULT")
        if not directory: self.skipTest("Set PICOGK_F16_RESULT for an installed native result")
        r = f16.verify_output(Path(directory))
        self.assertEqual(len(r["checks"]), 45)
        self.assertGreater(r["solid_fraction_in_zone"], 0)
        self.assertLess(r["solid_fraction_in_zone"], 1)


def git(directory, *args):
    subprocess.run(["git", "-C", str(directory), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


class LinuxLeapRootTests(unittest.TestCase):
    """prepare_linux_leap_root.py decides provenance, so its refusals are tested on fakes."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp)
        self.home, self.nuget, self.dotnet = self.tmp / "picogk", self.tmp / "nuget", self.tmp / "dotnet"
        revisions = {}
        for repo in prep.REVISIONS:
            name = repo.split("/")[1]; checkout = self.home / name
            source = checkout / ("ShapeKernel" if "ShapeKernel" in name else "LatticeLibrary")
            source.mkdir(parents=True)
            (source / "Fake.cs").write_text("// fake source\n")
            (checkout / "LICENSE").write_text("Apache License\nVersion 2.0, January 2004\n")
            git(checkout, "init", "-q"); git(checkout, "add", "."); git(checkout, "commit", "-qm", "fake")
            revisions[repo] = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                                             check=True, capture_output=True, text=True).stdout.strip()
        self.revisions = revisions
        for path in (self.nuget / f"picogk/{prep.PICOGK_NUGET}/lib/net9.0/PicoGK.dll",
                     self.nuget / f"skiasharp/{prep.SKIASHARP_NUGET}/lib/net8.0/SkiaSharp.dll",
                     self.home / "PicoGK/assets/ViewerEnvironment.zip", self.home / "native/picogk.26.2.so"):
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(path.name.encode())
        (self.home / "native/RUNTIME_COMMIT").write_text("0" * 40 + "\n")
        self.dotnet.mkdir(); (self.dotnet / "dotnet").write_text("#!/bin/sh\necho 9.0.0-test\n")
        (self.dotnet / "dotnet").chmod(0o755)

    def prepare(self, root=None):
        with mock.patch.dict(prep.REVISIONS, self.revisions):
            return prep.prepare(self.home, self.nuget, self.dotnet, root or self.tmp / "root")

    def test_receipt_is_accepted_by_the_runner_and_detects_tampering(self):
        receipt = self.prepare()
        root = self.tmp / "root"
        self.assertEqual({p["verified_by"] for p in receipt["libraries"]}, {"git rev-parse HEAD on a clean checkout"})
        self.assertFalse(any(k.startswith("sdk/") for k in receipt["sha256"]))
        with mock.patch.dict(f16.REVISIONS, self.revisions):
            self.assertIn(root / "runtime/picogk.26.2.so", f16.installed_files(root))
            (root / "runtime/picogk.26.2.so").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "differs from installation receipt"):
                f16.installed_files(root)

    def test_refuses_existing_root(self):
        (self.tmp / "root").mkdir()
        with self.assertRaisesRegex(ValueError, "new LEAP root"): self.prepare()

    def test_refuses_unreviewed_revision(self):
        with self.assertRaisesRegex(ValueError, "reviewed clean revision"):
            prep.prepare(self.home, self.nuget, self.dotnet, self.tmp / "root")
        self.assertFalse((self.tmp / "root").exists())

    def test_refuses_dirty_checkout(self):
        (self.home / "LEAP71_ShapeKernel/ShapeKernel/Extra.cs").write_text("// untracked\n")
        with self.assertRaisesRegex(ValueError, "reviewed clean revision"): self.prepare()

    def test_refuses_other_licence(self):
        checkout = self.home / "LEAP71_LatticeLibrary"
        (checkout / "LICENSE").write_text("MIT License\n"); git(checkout, "commit", "-qam", "licence")
        self.revisions["leap71/LEAP71_LatticeLibrary"] = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        with self.assertRaisesRegex(ValueError, "Unexpected licence"): self.prepare()


class NativeExitTests(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.out)

    def write(self, log="  30s    0.0+ Done.\n", report=True):
        if log is not None: (self.out / "native.log").write_text(log)
        if report: (self.out / "report.json").write_text("{}\n")

    def test_accepts_only_segfault_after_closed_log_and_report(self):
        self.write(); f16.check_native_exit(-11, ["dotnet"], self.out)

    def test_rejects_other_exits_and_early_segfaults(self):
        cases = {"other_signal": (-6, {}), "error_code": (1, {}), "log_open": (-11, {"log": "Writing VDB\n"}),
                 "no_log": (-11, {"log": None}), "no_report": (-11, {"report": False})}
        for name, (code, files) in cases.items():
            for p in self.out.iterdir(): p.unlink()
            self.write(**files)
            with self.subTest(name), self.assertRaises(subprocess.CalledProcessError):
                f16.check_native_exit(code, ["dotnet"], self.out)


class LinuxReceiptTests(unittest.TestCase):
    """The Linux receipt is a separate record; it must stay bounded and match the committed inputs."""

    def setUp(self):
        self.receipt = json.loads((ROOT / "twins/vehicle-911-917/leap-f16-linux-receipt-20261015.json").read_text())

    def test_receipt_claims_stay_bounded(self):
        r = self.receipt
        self.assertEqual((r["phase"], r["status"], r["manufacturing_authorized"]),
                         ("F16", "geometry_study_not_qualified_vehicle", False))
        self.assertEqual({p["id"] for p in r["components"]}, f16.PARTS)
        self.assertEqual(r["checks"], 45); self.assertFalse(r["field_exchange"]["physical_solver_executed"])
        comparison = r["comparison_with_mac_published_metrics"]; mac = comparison["mac"]
        self.assertFalse(comparison["byte_equality_vs_mac_checked"])
        self.assertTrue(comparison["metrics_match"])
        self.assertEqual((r["solid_fraction_in_zone"], r["lattice_cells_before_clipping"], r["intersections"]),
                         (mac["solid_fraction_in_zone"], mac["lattice_cells_before_clipping"], mac["intersections"]))
        self.assertEqual((r["field_exchange"]["scalar_active_values"], r["field_exchange"]["vector_active_values"]),
                         (mac["scalar_active_values"], mac["vector_active_values"]))
        self.assertIn("qualified heat exchanger", r["not_established"])

    def test_receipt_inputs_match_committed_sources(self):
        for path, digest in self.receipt["run"]["repository_inputs_sha256"].items():
            with self.subTest(path=path):
                self.assertEqual(f16.sha256(ROOT / path), digest, "re-run F16 on Linux and refresh the receipt")

    def test_receipt_matches_native_run_when_available(self):
        directory = os.environ.get("PICOGK_F16_RESULT")
        if not directory or f16.sha256(Path(directory) / "report.json") != self.receipt["report_sha256"]:
            self.skipTest("Set PICOGK_F16_RESULT to the Linux run named in the receipt")
        r = f16.verify_output(Path(directory))
        self.assertEqual([{k: p[k] for k in self.receipt["components"][0]} for p in r["components"]],
                         self.receipt["components"])
        self.assertEqual(f16.sha256(Path(directory) / "raw-mesh-inspection.json"),
                         self.receipt["raw_mesh_inspection"]["sha256"])


if __name__ == "__main__": unittest.main()
