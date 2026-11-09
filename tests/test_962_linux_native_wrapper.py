"""Exercise the Linux wrapper's process and shared-lock boundaries without PicoGK."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "head_linux_native", ROOT / "twins/962-cylinder-head-f0/source/linux_runtime/run_native.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@unittest.skipIf(os.name != "posix", "POSIX process groups required")
class LinuxNativeWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root / "picogk.so"
        self.native.write_bytes(b"\x7fELF\x02\x01" + b"\0" * 12 + (62).to_bytes(2, "little"))
        self.assembly = self.root / "fixture.py"
        self.assembly.write_text("import pathlib,sys\npathlib.Path(sys.argv[1]).mkdir()\n")
        for target, value in (("LOCK", self.root / "picogk-catalog.lock"),
                              ("platform.system", lambda: "Linux"),
                              ("platform.machine", lambda: "x86_64")):
            obj = runner
            parts = target.split(".")
            for name in parts[:-1]:
                obj = getattr(obj, name)
            mock = patch.object(obj, parts[-1], value)
            mock.start()
            self.addCleanup(mock.stop)

    def run_fixture(self, seconds=2):
        return runner.run(Path(sys.executable), self.assembly, self.native, self.root / "run", seconds)

    def test_success_retains_runtime_hashes_and_releases_lock(self):
        result = self.run_fixture()
        self.assertEqual(result["status"], "executed")
        self.assertTrue(result["process_group_absent"])
        self.assertFalse(runner.LOCK.exists())
        self.assertEqual(result["runtime_sha256"][str(self.native.resolve())], runner.sha(self.native))
        self.assertEqual(json.loads((self.root / "run/run.json").read_text()), result)
        self.assertFalse(result["manufacturing_authorized"])

    def test_failure_keeps_log_and_nonzero_exit(self):
        self.assembly.write_text("import sys\nprint('fixture failure')\nsys.exit(7)\n")
        result = self.run_fixture()
        self.assertEqual((result["status"], result["exit_code"]), ("failed", 7))
        self.assertIn("fixture failure", (self.root / "run/native.log").read_text())
        self.assertFalse(runner.LOCK.exists())

    def test_timeout_kills_process_group_and_preserves_failure(self):
        self.assembly.write_text("import time\ntime.sleep(30)\n")
        result = self.run_fixture(0.1)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["timed_out"])
        self.assertTrue(result["process_group_absent"])
        self.assertLess(result["exit_code"], 0)
        self.assertFalse(runner.LOCK.exists())

    def test_successful_parent_cannot_hide_leftover_child(self):
        self.assembly.write_text(
            "import subprocess,sys\nsubprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])\n")
        result = self.run_fixture()
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["descendants_terminated"])
        self.assertEqual(result["status"], "failed")

    def test_old_shared_lock_is_not_stolen(self):
        runner.LOCK.write_text("other owner")
        os.utime(runner.LOCK, (time.time() - 7200,) * 2)
        result = self.run_fixture(0.05)
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["exit_code"])
        self.assertEqual(runner.LOCK.read_text(), "other owner")
        self.assertFalse((self.root / "run/native").exists())

    def test_foreign_architecture_fails_before_output(self):
        self.native.write_bytes(self.native.read_bytes()[:18] + (183).to_bytes(2, "little"))
        with self.assertRaisesRegex(ValueError, "host-matching"):
            self.run_fixture()
        self.assertFalse((self.root / "run").exists())

    def test_limits_and_existing_output_fail_closed(self):
        for seconds in (0, -1, 601, float("nan"), float("inf")):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.run_fixture(seconds)
        out = self.root / "run"
        out.mkdir()
        (out / "retained").write_text("keep")
        with self.assertRaises(FileExistsError):
            self.run_fixture()
        self.assertEqual((out / "retained").read_text(), "keep")

    def test_qualification_binds_sources_without_promoting_engineering(self):
        record = json.loads((ROOT / "twins/962-cylinder-head-f0/source/linux_runtime/qualification-20261107.json").read_text())
        for name, digest in record["source_sha256"].items():
            self.assertEqual(runner.sha(ROOT / name), digest, name)
        phases = json.loads((ROOT / "twins/962-cylinder-head-f0/workflow-contract.json").read_text())["phases"]
        self.assertEqual(record["engineering_phase_states"], {p["id"]: "blocked" for p in phases})
        self.assertTrue(record["passed"])
        self.assertFalse(record["manufacturing_authorized"])
        self.assertFalse(record["native_report"]["head_geometry_executed"])


if __name__ == "__main__":
    unittest.main()
