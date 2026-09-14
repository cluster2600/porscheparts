import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "twins/m64-cylinder-head/jobs/steps-234-20260912.json"
SOURCE = ROOT / "twins/m64-cylinder-head/source/prepare_jobs_234.py"
SPEC = importlib.util.spec_from_file_location("prepare_jobs_234", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PreparationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.plan = json.loads(PLAN.read_text())

    def run_plan(self, plan=None):
        path = self.base / "plan.json"
        path.write_text(json.dumps(self.plan if plan is None else plan))
        return MODULE.prepare(ROOT, path, self.base / "packet")

    def test_real_packet_pins_and_keeps_physics_blocked(self):
        before = {v["path"]: (ROOT / v["path"]).read_bytes()
                  for v in self.plan["evidence"].values()}
        report = self.run_plan()
        self.assertTrue(report["packet_prepared"])
        self.assertFalse(report["ready_for_remote_execution"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["solver_executed"])
        self.assertIsNone(report["selected_variant"])
        self.assertEqual(len(report["missing_interfaces"]), 8)
        self.assertEqual(report["native_failed_checks"], 5)
        self.assertTrue(report["coupon_cap_persists"])
        for path, raw in before.items():
            self.assertEqual((ROOT / path).read_bytes(), raw)
        for key, raw in ((k, before[v["path"]]) for k, v in self.plan["evidence"].items()):
            self.assertEqual((self.base / "packet" / (key + ".json")).read_bytes(), raw)

    def test_hash_mismatch_refused_before_output(self):
        self.plan["evidence"]["interfaces"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash_mismatch"):
            self.run_plan()
        self.assertFalse((self.base / "packet").exists())

    def test_no_release_or_rental_switch(self):
        for key in ("rental_enabled", "manufacturing_authorized"):
            with self.subTest(key=key):
                plan = copy.deepcopy(self.plan)
                plan[key] = True
                with self.assertRaisesRegex(ValueError, "preparation_only"):
                    self.run_plan(plan)

    def test_no_unreviewed_job_admission(self):
        self.plan["jobs"][0]["ready_for_execution"] = True
        with self.assertRaisesRegex(ValueError, "unreviewed_job"):
            self.run_plan()

    def test_contour_change_refused(self):
        self.plan["preserve_master_contour"] = False
        with self.assertRaisesRegex(ValueError, "preparation_only"):
            self.run_plan()

    def test_duplicate_job_refused(self):
        self.plan["jobs"][-1] = self.plan["jobs"][0]
        with self.assertRaisesRegex(ValueError, "unexpected_jobs"):
            self.run_plan()

    def test_pilot_budget_refused(self):
        self.plan["jobs"][0]["rental_budget_usd"] = 5
        with self.assertRaisesRegex(ValueError, "invalid_job_budget"):
            self.run_plan()

    def test_aggregate_budget_refused(self):
        self.plan["budget"]["campaign_reserve"] = 7
        with self.assertRaisesRegex(ValueError, "budget_plan"):
            self.run_plan()

    def test_negative_or_nonfinite_reserve_refused(self):
        for value in (-1, float("nan"), float("inf"), True):
            with self.subTest(value=value):
                plan = copy.deepcopy(self.plan)
                plan["budget"]["campaign_reserve"] = value
                with self.assertRaisesRegex(ValueError, "budget_plan"):
                    self.run_plan(plan)

    def test_reserved_output_name_refused(self):
        self.plan["evidence"]["plan"] = self.plan["evidence"]["interfaces"]
        with self.assertRaisesRegex(ValueError, "unexpected_evidence_names"):
            self.run_plan()

    def test_path_traversal_and_absolute_input_refused(self):
        for path in ("../AGENTS.md", str(ROOT / "AGENTS.md")):
            with self.subTest(path=path):
                plan = copy.deepcopy(self.plan)
                plan["evidence"]["interfaces"]["path"] = path
                with self.assertRaisesRegex(ValueError, "invalid_evidence"):
                    self.run_plan(plan)

    def test_symlink_parent_refused(self):
        (self.base / "link").symlink_to(ROOT, target_is_directory=True)
        self.plan["evidence"]["interfaces"]["path"] = "link/twins/m64-cylinder-head/interface-contract.json"
        path = self.base / "plan.json"
        path.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ValueError, "symlink_input"):
            MODULE.prepare(self.base, path, self.base / "packet")

    def test_existing_output_preserved(self):
        self.run_plan()
        before = (self.base / "packet" / "preparation.json").read_bytes()
        with self.assertRaises(FileExistsError):
            MODULE.prepare(ROOT, self.base / "plan.json", self.base / "packet")
        self.assertEqual((self.base / "packet" / "preparation.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
