"""Budget-guard tests: fake clock and installed-wrapper responses only."""
from contextlib import ExitStack, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_guard():
    spec = importlib.util.spec_from_file_location("m64_guard_test", ROOT / "deploy/vast/simready/m64-deadline-guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DeadlineGuardTests(unittest.TestCase):
    def setUp(self):
        self.g = load_guard()
        self.temp = tempfile.TemporaryDirectory(prefix="m64-guard-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.manifest_path = self.root / "manifest.json"
        self.state = self.root / "private-guard"
        self.wrapper = self.root / "synthetic-wrapper"
        self.wrapper.write_text("#!/bin/false\n# never executed by these tests\n")
        self.wrapper.chmod(0o700)
        self.wall = 1000.0
        self.mono = 50.0
        self.sleeps = []
        self.calls = []
        self.active = True
        self.hook = None
        self.response_hook = None
        self.manifest = {
            "profile": "m64-omni-static-v1", "job_id": "m64-guard-fixture", "instance_id": 123456,
            "label": "3dprinting993-simready-local-ai-" + "a" * 20,
            "image": "ghcr.io/cluster2600/3dprinting993-simready-m64-runtime@sha256:" + "b" * 64,
            "created_epoch": 1000, "deadline_epoch": 1061, "max_dph": 2.5, "budget_usd": 5,
        }
        self.save()
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(self.g, "WRAPPER", self.wrapper))
        stack.enter_context(mock.patch.object(self.g.time, "time", side_effect=lambda: self.wall))
        stack.enter_context(mock.patch.object(self.g.time, "monotonic", side_effect=lambda: self.mono))
        stack.enter_context(mock.patch.object(self.g.time, "sleep", side_effect=self.sleep))
        stack.enter_context(mock.patch.object(self.g, "wrapper_call", side_effect=self.call))

    def save(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.manifest_path.chmod(0o600)

    def manifest_sha(self):
        return hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()

    def identity(self):
        return {"id": 123456, "label": "3dprinting993-simready-local-ai-" + "a" * 20, "image": "ghcr.io/cluster2600/3dprinting993-simready-m64-runtime@sha256:" + "b" * 64, "status": "running"}

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.wall += seconds
        self.mono += seconds
        if self.hook:
            self.hook()

    def call(self, arguments, timeout):
        self.calls.append((arguments, timeout))
        if self.response_hook:
            value = self.response_hook(arguments, timeout)
            if value is not None:
                return value
        if arguments[0] == "show":
            if not self.active:
                raise self.g.GuardError("wrapper_operation_failed")
            return self.identity()
        if arguments[0] == "instances":
            return [self.identity()] if self.active else []
        if arguments[0] == "m64-collect":
            return {"operation": "collect", "job_id": "m64-guard-fixture", "instance_id": 123456, "manifest_sha256": self.manifest_sha(), "retrieval_complete": True}
        if arguments[0] == "destroy":
            self.active = False
            return {"instance_id": 123456, "destroyed": True, "verified_absent": True}
        self.fail("No other command may be invoked")

    def execute(self):
        with redirect_stdout(io.StringIO()) as output:
            code = self.g.run_guard(self.manifest_path, self.state)
        self.final = json.loads(output.getvalue())
        return code

    def marker(self, *, receipt_hash=None):
        receipt = self.root / "collection-receipt.json"
        receipt.write_text(json.dumps({"operation": "collect", "job_id": self.manifest["job_id"], "instance_id": 123456, "manifest_sha256": receipt_hash or self.manifest_sha(), "files": {"results/proof.json": {"size": 1, "sha256": "0" * 64}}}))
        receipt.chmod(0o600)
        marker = {name: self.manifest[name] for name in ("job_id", "instance_id", "label", "image")}
        marker.update(manifest_sha256=self.manifest_sha(), collection_receipt=str(receipt))
        (self.state / "stop.json").write_text(json.dumps(marker))
        (self.state / "stop.json").chmod(0o600)

    def test_deadline_collect_then_exact_destroy_then_inventory(self):
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.sleeps, [30, 30, 1])
        self.assertEqual([args[0] for args, _ in self.calls][-4:], ["m64-collect", "show", "destroy", "instances"])
        collection = next(item for item in self.calls if item[0][0] == "m64-collect")
        self.assertEqual(collection, (["m64-collect", "123456", str(self.manifest_path), str(self.state / "deadline-collection")], 300))
        self.assertIn((["destroy", "123456", "--confirm"], 90), self.calls)
        self.assertTrue(self.final["absence_verified"])
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.state / "final.json").stat().st_mode), 0o600)

    def test_collection_timeout_still_destroys_and_reports_failure(self):
        def fail_collect(arguments, _):
            if arguments[0] == "m64-collect":
                raise self.g.GuardError("wrapper_timeout")
        self.response_hook = fail_collect
        self.assertEqual(self.execute(), 1)
        self.assertFalse(self.active)
        self.assertEqual(self.final["collection_error"], "wrapper_timeout")
        self.assertTrue(self.final["absence_verified"])

    def test_wrong_instance_id_label_or_image_never_destroyed(self):
        for field, value in (("id", 999), ("label", "other"), ("image", "other@digest")):
            with self.subTest(field=field):
                self.state = self.root / ("bad-" + field)
                self.calls = []
                self.response_hook = lambda arguments, _, field=field, value=value: dict(self.identity(), **{field: value}) if arguments[0] == "show" else None
                self.assertEqual(self.execute(), 1)
                self.assertFalse(any(args[0] == "destroy" for args, _ in self.calls))
                self.assertEqual(self.final["error"], "exact_instance_identity_mismatch")

    def test_rechecks_identity_after_collect_before_destroy(self):
        collected = False
        def change_after_collect(arguments, _):
            nonlocal collected
            if arguments[0] == "m64-collect":
                collected = True
            elif arguments[0] == "show" and collected:
                return dict(self.identity(), label="reassigned")
        self.response_hook = change_after_collect
        self.assertEqual(self.execute(), 1)
        self.assertFalse(any(args[0] == "destroy" for args, _ in self.calls))

    def test_destroy_failure_alerts_without_claiming_absence(self):
        self.response_hook = lambda arguments, _: {"instance_id": 123456, "destroyed": False, "verified_absent": False} if arguments[0] == "destroy" else None
        self.assertEqual(self.execute(), 1)
        self.assertFalse(self.final["absence_verified"])
        self.assertEqual(self.final["error"], "destruction_not_attested")

    def test_claimed_destroy_requires_independent_absence(self):
        self.response_hook = lambda arguments, _: {"instance_id": 123456, "destroyed": True, "verified_absent": True} if arguments[0] == "destroy" else None
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.final["error"], "absence_not_verified")

    def test_manual_stop_requires_receipt_and_remote_absence(self):
        def stop():
            self.marker()
            self.active = False
        self.hook = stop
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.sleeps, [30])
        self.assertEqual(self.final["status"], "manual_collection_and_absence_verified")
        self.assertFalse(any(args[0] in {"destroy", "m64-collect"} for args, _ in self.calls))

    def test_valid_marker_with_still_live_instance_cannot_disarm_guard(self):
        self.hook = lambda: self.marker()
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.sleeps, [30, 30, 1])
        self.assertEqual(self.final["status"], "deadline_destroyed_verified_absent")

    def test_touch_marker_is_ignored(self):
        self.hook = lambda: (self.state / "stop.json").touch()
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.final["status"], "deadline_destroyed_verified_absent")

    def test_clock_rollback_does_not_extend_monotonic_deadline(self):
        def roll_back():
            if len(self.sleeps) == 1:
                self.wall -= 3600
        self.hook = roll_back
        self.assertEqual(self.execute(), 0)
        self.assertEqual(sum(self.sleeps), 61)

    def test_manifest_change_cannot_retarget_or_extend_guard(self):
        def modify():
            self.manifest["instance_id"] = 999
            self.manifest["deadline_epoch"] += 7200
            self.save()
        self.hook = modify
        self.assertEqual(self.execute(), 1)
        self.assertEqual(sum(self.sleeps), 61)
        self.assertEqual(self.final["collection_error"], "collection_manifest_changed")
        self.assertTrue(self.final["absence_verified"])
        self.assertIn((["destroy", "123456", "--confirm"], 90), self.calls)

    def test_transient_read_failures_do_not_abandon_deadline(self):
        def temporary_failure(arguments, _):
            if self.wall < 1030 and arguments[0] in {"show", "instances"}:
                raise self.g.GuardError("wrapper_timeout")
        self.response_hook = temporary_failure
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.final["last_read_error"], "transient_inventory_read_failed")
        self.assertTrue(self.final["absence_verified"])

    def test_wrapper_change_is_not_silently_executed(self):
        self.hook = lambda: self.wrapper.write_text("changed installed wrapper")
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.final["error"], "installed_wrapper_changed")
        self.assertFalse(any(args[0] == "destroy" for args, _ in self.calls))

    def test_nonfinite_budget_and_lifetime_over_two_hours_rejected_before_calls(self):
        for key, value in (("budget_usd", float("nan")), ("max_dph", True), ("max_dph", 2.51), ("budget_usd", 20.01), ("deadline_epoch", 8201)):
            original = self.manifest[key]
            self.manifest[key] = value
            self.save()
            with self.subTest(key=key), self.assertRaises(self.g.GuardError):
                self.execute()
            self.assertEqual(self.calls, [])
            self.manifest[key] = original

    def test_symlink_manifest_rejected_before_wrapper_calls(self):
        link = self.root / "link.json"
        link.symlink_to(self.manifest_path)
        self.manifest_path = link
        with self.assertRaises(self.g.GuardError):
            self.execute()
        self.assertEqual(self.calls, [])

    def test_scope_rejects_launch_phase_and_direct_ssh(self):
        real = load_guard()
        with mock.patch.object(real.subprocess, "Popen") as popen:
            for arguments in (["launch", "123"], ["m64-phase", "123", "/m", "render"], ["ssh", "root@host"], ["destroy", "123", "--force"]):
                with self.subTest(arguments=arguments), self.assertRaises(real.GuardError):
                    real.wrapper_call(arguments, 30)
            popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
