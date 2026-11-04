"""Budget and ownership regression for the bounded native review session."""
import contextlib
import hashlib
import io
import json
from unittest import mock
import importlib.util
from pathlib import Path
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deploy/vast/monocoque-review/deadline_guard.py"
SPEC = importlib.util.spec_from_file_location("review_guard", SOURCE)
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class ReviewGuardTests(unittest.TestCase):
    def setUp(self):
        now = int(time.time())
        self.manifest = {
            "profile": "964-omniverse-review-v1", "job_id": "964-omniverse-test",
            "attempt_label": "3dprinting993-simready-local-ai-" + "a" * 20,
            "image_ref": GUARD.IMAGE, "created_epoch": now, "deadline_epoch": now + 5400,
            "budget_usd": 5, "download_budget_gb": 40, "upload_budget_gb": 15,
            "guard_path": str(SOURCE), "guard_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "guard_ready_path": "/unused/964-omniverse-test.guard-ready.json",
        }
        GUARD.policy.interrupted = False
        GUARD.validate_manifest(self.manifest)
        self.instance = {
            "id": 123, "label": self.manifest["attempt_label"], "image": GUARD.IMAGE,
            "status": "running", "dph_total": 1.538888888888889,
            "inet_down_cost_usd_per_gb": 0.00390625, "inet_up_cost_usd_per_gb": 0.00390625,
        }

    def test_proposed_cost_including_reserve_is_admissible(self):
        self.assertTrue(GUARD.policy.cost_valid(self.instance, self.manifest))

    def test_approval_boundaries_are_not_expandable(self):
        for key, value in (("budget_usd", 5.01), ("budget_usd", float("nan")),
                           ("deadline_epoch", self.manifest["created_epoch"] + 5401),
                           ("image_ref", GUARD.IMAGE + "x"), ("download_budget_gb", 41),
                           ("upload_budget_gb", 16), ("sibling_label", "unrelated"),
                           ("guard_sha256", "0" * 64), ("attempt_label", "other")):
            with self.subTest(key=key), self.assertRaises(GUARD.policy.engine.GuardError):
                GUARD.validate_manifest({**self.manifest, key: value})

    def test_tariffs_and_total_cost_are_checked(self):
        for overrides in ({"dph_total": 2.51}, {"dph_total": 2.5,
                "inet_down_cost_usd_per_gb": .01, "inet_up_cost_usd_per_gb": .01},
                {"inet_up_cost_usd_per_gb": .02}):
            self.assertFalse(GUARD.policy.cost_valid({**self.instance, **overrides}, self.manifest))
        self.assertFalse(GUARD.policy.cost_valid(self.instance, self.manifest, first_price=1.0))

    def test_changed_identity_cannot_be_destroyed_as_owned(self):
        for overrides in ({"image": "other"}, {"id": 124}, {"label": "other"}):
            with self.assertRaises(GUARD.policy.engine.GuardError):
                GUARD.policy.engine.exact_match([{**self.instance, **overrides}], self.manifest, 123)

    def test_diagnostics_keep_inventory_and_cost_policy_unchanged(self):
        other = {"id": 456, "label": "another-task", "private_field": "must-not-be-logged"}
        inventory = [self.instance, other]
        output = io.StringIO()
        with mock.patch.object(GUARD.policy, "wrapper_call", return_value=inventory), contextlib.redirect_stdout(output):
            self.assertIs(GUARD.observed_wrapper_call("instances"), inventory)
        report = json.loads(output.getvalue())
        self.assertEqual(report["event"], "nonexclusive_inventory")
        self.assertEqual(report["instance_ids"], [123, 456])
        self.assertNotIn("must-not-be-logged", output.getvalue())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertFalse(GUARD.observed_cost_valid(self.instance, self.manifest, first_price=1.0))
        report = json.loads(output.getvalue())
        self.assertEqual(report["event"], "cost_contract_rejected")
        self.assertEqual(report["first_price"], 1.0)
        self.assertEqual(report["observed"]["id"], 123)

    def test_interrupt_forces_cleanup_even_during_missing_metadata(self):
        GUARD.policy.interrupted = True
        self.assertFalse(GUARD.policy.cost_valid(self.instance, self.manifest))
        self.assertFalse(GUARD.policy.only_cost_metadata_missing({"dph_total": None}, None))
        self.assertFalse(GUARD.policy.startup_pending({"status": None}))


if __name__ == "__main__":
    unittest.main()
