"""PicoGK scoped rental tests: synthetic fixtures, no network or secrets."""
from contextlib import ExitStack, nullcontext, redirect_stdout, redirect_stderr
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    loader = SourceFileLoader(name, str(ROOT / relative))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class PicoGKTests(unittest.TestCase):
    def setUp(self):
        self.w = load("deploy/openbao/openbao-vastai", "picogk_wrapper_test")
        self.g = load("deploy/vast/picogk/deadline_guard.py", "picogk_guard_test")
        self.temp = tempfile.TemporaryDirectory(prefix="picogk-wrapper-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "job.json"
        self.proof_path = self.root / "qualification.json"
        image = "ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:" + "a" * 64
        proof = {"image_ref": image, "platform": "linux/amd64", "runtime_smoke_verified": True,
                 "anonymous_exact_digest_pull_verified": True,
                 "manufacturing_validated": False, "engine_validated": False}
        proof_data = json.dumps(proof).encode()
        self.proof_path.write_bytes(proof_data)
        now = int(time.time())
        self.manifest = {"schema_version": "1.0.0", "profile": "picogk-m64-v1",
                         "job_id": "picogk-m64-fixture", "attempt_label": self.w.PICOGK_LABEL + "-" + "b" * 20,
                         "image_ref": image, "created_epoch": now - 1, "deadline_epoch": now + 3600,
                         "budget_usd": 4, "image_download_gb": 3, "max_input_gb": 1, "max_output_gb": 1,
                         "qualification_path": str(self.proof_path),
                         "qualification_sha256": hashlib.sha256(proof_data).hexdigest(),
                         "guard_ready_path": str(self.root / "picogk-m64-fixture.guard-ready.json")}
        self.offer = {"id": 123, "gpu_name": "RTX 4090", "gpu_frac": 1, "num_gpus": 1,
                      "cpu_cores_effective": 64, "cpu_ram": 128000, "disk_space": 100,
                      "dph_total": 0.5, "reliability": 0.999, "verified": True,
                      "rentable": True, "rented": False, "inet_up_cost": 0.001, "inet_down_cost": 0.001}
        self.raw = {**self.offer, "id": 999, "label": self.manifest["attempt_label"],
                    "actual_status": "running", "image_uuid": image, "verification": "verified"}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.manifest))

    def test_manifest_and_expired_cleanup(self):
        manifest, sha = self.w.picogk_load_manifest(self.path)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(sha, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.manifest.update(created_epoch=int(time.time()) - 3600, deadline_epoch=int(time.time()) - 1)
        self.save()
        with self.assertRaises(self.w.SafeError):
            self.w.picogk_load_manifest(self.path)
        self.w.picogk_load_manifest(self.path, require_active=False)

    def test_manifest_rejects_escape_budget_clock_and_proof(self):
        for key, value in (("image_ref", "ubuntu:latest"), ("profile", "anything"),
                           ("budget_usd", 4.01), ("budget_usd", True), ("max_input_gb", 3),
                           ("deadline_epoch", self.manifest["created_epoch"] + 10801),
                           ("qualification_sha256", "c" * 64), ("guard_ready_path", "/tmp/other.json")):
            with self.subTest(key=key, value=value):
                old = self.manifest[key]
                self.manifest[key] = value
                self.save()
                with self.assertRaises(self.w.SafeError):
                    self.w.picogk_load_manifest(self.path)
                self.manifest[key] = old
        self.save()

    def test_qualification_cannot_claim_engine_release(self):
        proof = json.loads(self.proof_path.read_bytes())
        proof["engine_validated"] = True
        data = json.dumps(proof).encode()
        self.proof_path.write_bytes(data)
        self.manifest["qualification_sha256"] = hashlib.sha256(data).hexdigest()
        self.save()
        with self.assertRaises(self.w.SafeError):
            self.w.picogk_load_manifest(self.path)

    def test_offer_limits_and_budget(self):
        self.assertTrue(self.w.picogk_offer_eligible(self.offer))
        for key, value in (("id", True), ("num_gpus", 2), ("gpu_frac", 0.5), ("cpu_ram", 63999),
                           ("cpu_cores_effective", 31), ("dph_total", 0.81), ("rented", True),
                           ("inet_up_cost", None), ("inet_down_cost", 0.02), ("reliability", 0.98)):
            with self.subTest(key=key):
                self.assertFalse(self.w.picogk_offer_eligible({**self.offer, key: value}))
        self.assertLess(self.w.picogk_budget_cost(self.manifest, 0.5, 0.001, 0.001), 4)
        with self.assertRaises(self.w.SafeError):
            self.w.picogk_budget_cost({**self.manifest, "budget_usd": 1.01}, 0.5, 0.001, 0.001)

    def test_account_billing_redacts_identity_and_recharge(self):
        with mock.patch.object(self.w, "vast_request", return_value={"balance": -0.1, "credit": 19.1,
                "email": "fixture@example.invalid", "ssh_key": "not-for-output", "sid": "not-for-output"}) as call:
            result = self.w.picogk_account_balance("synthetic")
        call.assert_called_once_with("synthetic", "/api/v0/users/current/")
        self.assertEqual(result["conservative_available_usd"], 19.0)
        self.assertEqual(set(result), {"balance_usd", "credit_usd", "conservative_available_usd", "automatic_recharge_requested"})
        self.assertFalse(result["automatic_recharge_requested"])
        with mock.patch.object(self.w, "vast_request", return_value={"balance": "unknown"}):
            with self.assertRaises(self.w.SafeError):
                self.w.picogk_account_balance("synthetic")

    def test_actual_contract_revalidates_price_and_identity(self):
        self.w.picogk_contract(self.raw, 999, self.manifest, self.offer)
        for key, value in (("image_uuid", "foreign"), ("label", "foreign"), ("id", 998),
                           ("dph_total", 0.6), ("inet_down_cost", None), ("verification", "unverified")):
            with self.subTest(key=key), self.assertRaises(self.w.SafeError):
                self.w.picogk_contract({**self.raw, key: value}, 999, self.manifest, self.offer)

    def test_guard_must_be_alive_pinned_and_already_armed(self):
        _, sha = self.w.picogk_load_manifest(self.path)
        with self.assertRaises(self.w.SafeError):
            self.w.picogk_verify_armed_guard(self.manifest, sha)
        ready = {"armed": True, "pid": os.getpid(), "manifest_sha256": sha,
                 "wrapper_sha256": hashlib.sha256(Path(self.w.__file__).read_bytes()).hexdigest(),
                 "deadline_epoch": self.manifest["deadline_epoch"], "label": self.manifest["attempt_label"],
                 "image_ref": self.manifest["image_ref"]}
        path = Path(self.manifest["guard_ready_path"])
        path.write_text(json.dumps(ready))
        self.w.picogk_verify_armed_guard(self.manifest, sha)
        ready["manifest_sha256"] = "0" * 64
        path.write_text(json.dumps(ready))
        with self.assertRaises(self.w.SafeError):
            self.w.picogk_verify_armed_guard(self.manifest, sha)

    def test_launch_failure_destroys_only_returned_owned_instance(self):
        with ExitStack() as stack:
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(redirect_stderr(io.StringIO()))
            stack.enter_context(mock.patch.object(self.w, "simready_launch_lock", return_value=nullcontext()))
            stack.enter_context(mock.patch.object(self.w, "picogk_singleton"))
            stack.enter_context(mock.patch.object(self.w, "picogk_account_balance", return_value={"conservative_available_usd": 19}))
            stack.enter_context(mock.patch.object(self.w, "ensure_local_ssh_registered"))
            stack.enter_context(mock.patch.object(self.w, "get_picogk_offers", return_value=[self.offer]))
            armed = stack.enter_context(mock.patch.object(self.w, "picogk_verify_armed_guard"))
            paid = stack.enter_context(mock.patch.object(self.w, "vast_request", return_value={"new_contract": 999}))
            stack.enter_context(mock.patch.object(self.w, "picogk_ssh_ready", side_effect=self.w.SafeError("fixture failed")))
            destroy = stack.enter_context(mock.patch.object(self.w, "destroy_instance_verified"))
            with self.assertRaises(self.w.SafeError):
                self.w.launch_picogk_m64("synthetic", 123, self.manifest, "d" * 64)
        armed.assert_called_once()
        self.assertEqual(paid.call_args.kwargs["payload"]["image"], self.manifest["image_ref"])
        self.assertEqual(paid.call_args.kwargs["payload"]["env"], {})
        destroy.assert_called_once_with("synthetic", 999, expected_label=self.manifest["attempt_label"],
                                       expected_image=self.manifest["image_ref"])

    def test_external_guard_exact_ownership_and_cost(self):
        self.g.validate_manifest(self.manifest)
        safe = self.w.safe_instance(self.raw)
        self.assertEqual(self.g.exact_match([safe], self.manifest, 999), safe)
        self.assertTrue(self.g.cost_valid(safe, self.manifest))
        self.assertFalse(self.g.cost_valid({**safe, "dph_total": 0.9}, self.manifest))
        self.assertFalse(self.g.cost_valid(safe, self.manifest, 0.4))
        for inventory in ([safe, safe], [{**safe, "image": "other"}], [{**safe, "label": "other"}]):
            with self.assertRaises(self.g.GuardError):
                self.g.exact_match(inventory, self.manifest, 999)

    def test_external_destroy_requires_fresh_exact_match(self):
        safe = self.w.safe_instance(self.raw)
        proof = {"instance_id": 999, "destroyed": True, "verified_absent": True}
        with mock.patch.object(self.g, "wrapper_call", side_effect=[safe, proof]) as call:
            self.assertEqual(self.g.destroy_exact(999, self.manifest), proof)
        self.assertEqual(call.call_args_list, [mock.call("show", "999"), mock.call("destroy", "999", "--confirm")])
        with mock.patch.object(self.g, "wrapper_call", return_value={**safe, "image": "other"}) as call:
            with self.assertRaises(self.g.GuardError):
                self.g.destroy_exact(999, self.manifest)
            self.assertEqual(call.call_count, 1)

    def test_runtime_probe_requires_no_python_and_checks_witness(self):
        self.assertNotIn("python", self.w.picogk_remote_ready_command())
        witness = {"status": "PASS", "architecture": "X64", "scope": "software_geometry_witness_only",
                   "triangles": 100, "stl_roundtrip_triangles": 100, "relative_volume_error": 0.03,
                   "manufacturing_validated": False, "engine_validated": False}
        self.assertTrue(self.w.picogk_smoke_valid(json.dumps(witness)))
        for key, value in (("triangles", 0), ("stl_roundtrip_triangles", 99), ("relative_volume_error", 0.11),
                           ("architecture", "Arm64"), ("engine_validated", True)):
            self.assertFalse(self.w.picogk_smoke_valid(json.dumps({**witness, key: value})))
        self.assertFalse(self.w.picogk_smoke_valid("not json"))

    def test_attempt_journal_is_durable_and_cannot_replay(self):
        path = self.w.picogk_consume_attempt(self.manifest, "a" * 64, 123)
        self.assertTrue(path.is_file())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(self.w.SafeError):
            self.w.picogk_consume_attempt(self.manifest, "a" * 64, 123)

    def test_cleanup_survives_inventory_error_and_lost_delete_ack(self):
        safe = self.w.safe_instance(self.raw)
        # First inventory fails; later DELETE times out after it has succeeded.
        responses = [self.g.GuardError("transient"), [safe], [], [], [], [], []]
        with mock.patch.object(self.g, "wrapper_call", side_effect=responses), \
             mock.patch.object(self.g, "destroy_exact", side_effect=self.g.GuardError("ack lost")) as destroy, \
             mock.patch.object(self.g.time, "sleep"), redirect_stdout(io.StringIO()):
            proof = self.g.cleanup_until_absent(999, self.manifest)
        self.assertTrue(proof["verified_absent"])
        self.assertTrue(proof["delete_acknowledgement_may_have_been_lost"])
        destroy.assert_called_once_with(999, self.manifest)

    def test_guard_arms_before_launch_then_destroys_at_monotonic_deadline(self):
        self.manifest["deadline_epoch"] = int(time.time()) + 600
        self.save()
        fake_wrapper = self.root / "approved-wrapper"
        fake_wrapper.write_text("# synthetic, never executed\n")
        safe = self.w.safe_instance(self.raw)
        proof = {"instance_id": 999, "destroyed": True, "verified_absent": True}
        with mock.patch.object(self.g, "WRAPPER", fake_wrapper), \
             mock.patch.object(self.g, "wrapper_call", side_effect=[[], [safe]]), \
             mock.patch.object(self.g.time, "monotonic", side_effect=[0, 0, 400]), \
             mock.patch.object(self.g, "cleanup_until_absent", return_value=proof) as destroy, \
             redirect_stdout(io.StringIO()):
            result = self.g.guard(self.path)
        self.assertTrue(json.loads(Path(self.manifest["guard_ready_path"]).read_bytes())["armed"])
        self.assertTrue(result["verified_absent"])
        destroy.assert_called_once_with(999, self.manifest)

    def test_guard_after_observation_cleans_up_when_inventory_read_fails(self):
        fake_wrapper = self.root / "approved-wrapper"
        fake_wrapper.write_text("# synthetic, never executed\n")
        safe = self.w.safe_instance(self.raw)
        proof = {"instance_id": 999, "destroyed": True, "verified_absent": True}
        with mock.patch.object(self.g, "WRAPPER", fake_wrapper), \
             mock.patch.object(self.g, "wrapper_call", side_effect=[[], [safe], self.g.GuardError("transient")]), \
             mock.patch.object(self.g.time, "monotonic", return_value=0), \
             mock.patch.object(self.g.time, "sleep"), \
             mock.patch.object(self.g, "cleanup_until_absent", return_value=proof) as destroy, \
             redirect_stdout(io.StringIO()):
            result = self.g.guard(self.path)
        self.assertEqual(result["reason"], "inventory_read_failed")
        destroy.assert_called_once_with(999, self.manifest)

    def test_guard_observed_absence_routes_through_resilient_cleanup(self):
        fake_wrapper = self.root / "approved-wrapper"
        fake_wrapper.write_text("# synthetic, never executed\n")
        safe = self.w.safe_instance(self.raw)
        proof = {"instance_id": 999, "destroyed": True, "verified_absent": True}
        with mock.patch.object(self.g, "WRAPPER", fake_wrapper), \
             mock.patch.object(self.g, "wrapper_call", side_effect=[[], [safe], []]), \
             mock.patch.object(self.g.time, "monotonic", return_value=0), \
             mock.patch.object(self.g.time, "sleep"), \
             mock.patch.object(self.g, "cleanup_until_absent", return_value=proof) as cleanup, \
             redirect_stdout(io.StringIO()):
            result = self.g.guard(self.path)
        self.assertTrue(result["verified_absent"])
        cleanup.assert_called_once_with(999, self.manifest)

    def test_unknown_startup_absence_retries_transient_failure(self):
        fake_wrapper = self.root / "approved-wrapper"
        fake_wrapper.write_text("# synthetic, never executed\n")
        responses = [[], [], self.g.GuardError("temporary"), [], [], [], [], [], []]
        with mock.patch.object(self.g, "WRAPPER", fake_wrapper), \
             mock.patch.object(self.g, "wrapper_call", side_effect=responses) as call, \
             mock.patch.object(self.g.time, "monotonic", side_effect=[0, 0, 1300, 1300]), \
             mock.patch.object(self.g.time, "sleep"), redirect_stdout(io.StringIO()):
            result = self.g.guard(self.path)
        self.assertEqual(result["reason"], "no_instance_observed")
        self.assertTrue(result["verified_absent"])
        self.assertEqual(call.call_count, 9)

    def test_cleanup_absence_counter_resets_after_inventory_error(self):
        responses = [[], [], self.g.GuardError("temporary"), [], [], [], [], []]
        with mock.patch.object(self.g, "wrapper_call", side_effect=responses) as call, \
             mock.patch.object(self.g.time, "sleep"), redirect_stdout(io.StringIO()):
            result = self.g.cleanup_until_absent(999, self.manifest)
        self.assertTrue(result["verified_absent"])
        self.assertEqual(call.call_count, 8)


if __name__ == "__main__":
    unittest.main()
