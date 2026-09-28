"""FEA512 policy and billing boundaries: synthetic fixtures, no network/secrets."""
from contextlib import ExitStack, nullcontext, redirect_stdout, redirect_stderr
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
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


class FEA512Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fea512-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        # The repository wrapper is pinned by historical F46 evidence. Test
        # only the versioned delta on a disposable copy; never edit the source.
        source = ROOT / "deploy/openbao/openbao-vastai"
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         "42fe39ebcf7fc81e8f6c4a85e38fa9da03fd4637bb93a37b3a422c315e8a5aa4")
        variant = self.root / "deploy/openbao/openbao-vastai"
        variant.parent.mkdir(parents=True)
        shutil.copyfile(source, variant)
        subprocess.run(["git", "apply", str(ROOT / "deploy/vast/m64-fea512/wrapper-fea512.patch")],
                       cwd=self.root, check=True, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(hashlib.sha256(variant.read_bytes()).hexdigest(),
                         "18b2a205c16f2d4d3bcce25baefe47cd921750223ab614834bb9eeb4111bb328")
        self.w = load(variant, "fea512_wrapper_test")
        self.g = load("deploy/vast/m64-fea512/deadline_guard.py", "fea512_guard_test")
        self.path = self.root / "job.json"
        self.guard = ROOT / "deploy/vast/m64-fea512/deadline_guard.py"
        image = "ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:" + "a" * 64
        proof = {"image_ref": image, "platform": "linux/amd64", "runtime_smoke_verified": True,
                 "anonymous_exact_digest_pull_verified": True, "manufacturing_validated": False,
                 "engine_validated": False}
        proof_path = self.root / "qualification.json"
        proof_path.write_text(json.dumps(proof))
        now = int(time.time())
        self.manifest = {"schema_version": "1.0.0", "profile": self.w.FEA512_PROFILE,
                         "job_id": "m64-fea512-fixture", "attempt_label": self.w.FEA512_LABEL + "-" + "b" * 20,
                         "image_ref": image, "created_epoch": now - 1, "deadline_epoch": now + 3599,
                         "budget_usd": 5, "image_download_gb": 20, "max_input_gb": 2, "max_output_gb": 2,
                         "qualification_path": str(proof_path),
                         "qualification_sha256": hashlib.sha256(proof_path.read_bytes()).hexdigest(),
                         "guard_ready_path": str(self.root / "m64-fea512-fixture.guard-ready.json"),
                         "guard_path": str(self.guard), "guard_sha256": self.w.FEA512_GUARD_SHA256,
                         "background_instance": dict(self.w.FEA512_BACKGROUND)}
        self.offer = {"id": 50924858, "gpu_name": "RTX 3090", "gpu_frac": 1, "num_gpus": 1,
                      "cpu_cores_effective": 104, "cpu_ram": 1523000, "disk_space": 500,
                      "dph_total": 0.986, "reliability": 0.999, "verified": True,
                      "rentable": True, "rented": False, "inet_up_cost": 0.01, "inet_down_cost": 0.01}
        self.raw = {**self.offer, "id": 999, "label": self.manifest["attempt_label"],
                    "actual_status": "running", "image_uuid": image, "verification": "verified"}
        self.background = dict(self.w.FEA512_BACKGROUND)
        self.background_raw = {"id": self.background["id"], "label": self.background["label"],
                               "image_uuid": self.background["image"]}
        self.save()
        # Every test must explicitly mock a provider operation it expects.
        self.network = mock.patch.object(self.w, "vast_request", side_effect=AssertionError("no live provider calls"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def save(self):
        self.path.write_text(json.dumps(self.manifest))

    def test_manifest_guard_pin_and_old_engine_unchanged(self):
        parsed, digest = self.w.picogk_load_manifest(self.path)
        self.assertEqual(parsed, self.manifest)
        self.assertEqual(digest, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(hashlib.sha256(self.guard.read_bytes()).hexdigest(), self.w.FEA512_GUARD_SHA256)
        old = ROOT / "deploy/vast/picogk/deadline_guard.py"
        self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(), self.g.ENGINE_SHA256)
        self.g.validate_manifest(self.manifest)

    def test_manifest_rejects_policy_escape_before_authentication(self):
        original = dict(self.manifest)
        for key, value in (("budget_usd", 5.01), ("budget_usd", True),
                           ("deadline_epoch", original["created_epoch"] + 10801),
                           ("max_input_gb", 2.01), ("image_download_gb", 0),
                           ("guard_sha256", "0" * 64), ("guard_path", "relative"),
                           ("background_instance", {**self.background, "id": 52810564}),
                           ("background_instance", {**self.background, "image": "other"}),
                           ("attempt_label", "3dprinting993-picogk-m64-" + "b" * 20),
                           ("image_ref", "ubuntu:latest"), ("profile", "unknown")):
            with self.subTest(key=key, value=value):
                self.manifest = {**original, key: value}
                self.save()
                with mock.patch.object(self.w, "login") as login:
                    with self.assertRaises(self.w.SafeError):
                        self.w.run(["launch-picogk-m64", "50924858", str(self.path)])
                    login.assert_not_called()

    def test_offer_query_exact_refresh_and_old_profile_isolation(self):
        self.assertTrue(self.w.picogk_offer_eligible(self.offer, self.manifest))
        self.assertFalse(self.w.picogk_offer_eligible(self.offer))
        for key, value in (("cpu_ram", 511999), ("disk_space", 499), ("dph_total", 1.001),
                           ("gpu_frac", .5), ("num_gpus", 2), ("cpu_cores_effective", 31),
                           ("inet_up_cost", .0101), ("reliability", .98), ("rented", True)):
            with self.subTest(key=key):
                self.assertFalse(self.w.picogk_offer_eligible({**self.offer, key: value}, self.manifest))
        with mock.patch.object(self.w, "vast_request", return_value={"offers": [self.offer]}) as request:
            self.assertEqual(self.w.get_picogk_offers("synthetic", 50924858, self.manifest), [self.offer])
            query = request.call_args.kwargs["payload"]
        self.assertEqual(query["allocated_storage"], 500)
        self.assertEqual(query["cpu_ram"], {"gte": 512000})
        self.assertEqual(query["dph_total"], {"lte": 1.0})
        self.assertNotIn("id", query)
        self.assertEqual(self.w.picogk_policy()["budget"], 4)
        self.assertEqual(self.w.picogk_policy()["disk"], 100)

    def test_read_only_offer_cli_has_fixed_policy(self):
        with mock.patch.object(self.w, "login", return_value="synthetic"), \
             mock.patch.object(self.w, "read_vast_key", return_value="synthetic"), \
             mock.patch.object(self.w, "revoke_token"), \
             mock.patch.object(self.w, "get_picogk_offers", return_value=[]) as offers, \
             redirect_stdout(io.StringIO()):
            self.w.run(["fea512-offers", "50924858"])
        offers.assert_called_once_with("synthetic", 50924858, {"profile": self.w.FEA512_PROFILE})

    def test_budget_and_contract_recheck_real_allocations(self):
        manifest = {**self.manifest, "deadline_epoch": self.manifest["created_epoch"] + 10800}
        self.assertAlmostEqual(self.w.picogk_budget_cost(manifest, .986, .01, .01), 4.198)
        with self.assertRaises(self.w.SafeError):
            self.w.picogk_budget_cost({**manifest, "budget_usd": 4.19}, .986, .01, .01)
        self.w.picogk_contract(self.raw, 999, self.manifest, self.offer)
        for key, value in (("cpu_ram", 511999), ("disk_space", 499), ("dph_total", .987), ("image_uuid", "other")):
            with self.subTest(key=key), redirect_stderr(io.StringIO()), self.assertRaises(self.w.SafeError):
                self.w.picogk_contract({**self.raw, key: value}, 999, self.manifest, self.offer)

    def test_singleton_permits_only_exact_background_and_owned_attempt(self):
        with mock.patch.object(self.w, "strict_instance_inventory", return_value=[self.background_raw]):
            self.w.picogk_singleton("synthetic", None, self.manifest)
            with self.assertRaises(self.w.SafeError):
                self.w.picogk_singleton("synthetic", None, {"profile": self.w.PICOGK_PROFILE})
        with mock.patch.object(self.w, "strict_instance_inventory", return_value=[self.background_raw, self.raw]):
            self.w.picogk_singleton("synthetic", 999, self.manifest)
        for inventory in ([], [{**self.background_raw, "image_uuid": "other"}],
                          [self.background_raw, {**self.raw, "id": 1000}]):
            with self.subTest(inventory=inventory), mock.patch.object(self.w, "strict_instance_inventory", return_value=inventory):
                with self.assertRaises(self.w.SafeError):
                    self.w.picogk_singleton("synthetic", None, self.manifest)

    def test_guard_never_hides_changed_unknown_or_duplicate_background(self):
        own = self.w.picogk_safe_instance(self.raw)
        with mock.patch.object(self.g, "initial_wrapper_call", return_value=[self.background, own]):
            self.assertEqual(self.g.wrapper_call("instances"), [own])
        for other in ({**self.background, "image": "other"}, {**self.background, "id": 1000},
                      {**self.background, "label": "other"}):
            with mock.patch.object(self.g, "initial_wrapper_call", return_value=[other, own]):
                self.assertEqual(self.g.wrapper_call("instances"), [other, own])
        duplicate = [self.background, self.background, own]
        with mock.patch.object(self.g, "initial_wrapper_call", return_value=duplicate):
            self.assertEqual(self.g.wrapper_call("instances"), duplicate)
        with mock.patch.object(self.g, "initial_wrapper_call") as call:
            with self.assertRaises(self.g.engine.GuardError):
                self.g.wrapper_call("destroy", str(self.background["id"]), "--confirm")
            call.assert_not_called()

    def test_guard_refuses_to_arm_without_exact_background(self):
        for inventory in ([], [{**self.background, "image": "other"}], [self.background, self.background]):
            self.g._initial_inventory = True
            with mock.patch.object(self.g, "initial_wrapper_call", return_value=inventory):
                with self.assertRaises(self.g.engine.GuardError):
                    self.g.wrapper_call("instances")

    def test_guard_price_resources_signal_and_missing_metadata(self):
        own = self.w.picogk_safe_instance(self.raw)
        self.assertTrue(self.g.cost_valid(own, self.manifest))
        for key, value in (("cpu_ram_mb", 511999), ("disk_space_gb", 499), ("dph_total", 1.01),
                           ("gpu_fraction", .5), ("inet_down_cost_usd_per_gb", .011)):
            self.assertFalse(self.g.cost_valid({**own, key: value}, self.manifest))
            self.assertFalse(self.g.only_cost_metadata_missing({**own, key: value}, None))
        self.assertTrue(self.g.only_cost_metadata_missing({**own, "cpu_ram_mb": None}, None))
        self.assertFalse(self.g.cost_valid(own, self.manifest, .985))
        self.g.request_cleanup(None, None)
        self.assertFalse(self.g.cost_valid(own, self.manifest))

    def test_armed_guard_pid_is_bound_to_exact_helper_and_manifest(self):
        manifest = {**self.manifest, "_manifest_path": str(self.path)}
        ready = {"armed": True, "pid": os.getpid(), "manifest_sha256": "a" * 64,
                 "wrapper_sha256": hashlib.sha256(Path(self.w.__file__).read_bytes()).hexdigest(),
                 "deadline_epoch": manifest["deadline_epoch"], "label": manifest["attempt_label"],
                 "image_ref": manifest["image_ref"]}
        Path(manifest["guard_ready_path"]).write_text(json.dumps(ready))
        output = "python3 " + str(self.guard) + " " + str(self.path)
        with mock.patch.object(self.w.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")):
            self.w.picogk_verify_armed_guard(manifest, "a" * 64)
        with mock.patch.object(self.w.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "python3 other job", "")):
            with self.assertRaises(self.w.SafeError):
                self.w.picogk_verify_armed_guard(manifest, "a" * 64)

    def test_paid_launch_failure_has_500gb_and_only_owned_cleanup(self):
        with ExitStack() as stack:
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(redirect_stderr(io.StringIO()))
            stack.enter_context(mock.patch.object(self.w, "simready_launch_lock", return_value=nullcontext()))
            stack.enter_context(mock.patch.object(self.w, "strict_instance_inventory", return_value=[self.background_raw]))
            stack.enter_context(mock.patch.object(self.w, "picogk_account_balance", return_value={"conservative_available_usd": 19}))
            stack.enter_context(mock.patch.object(self.w, "ensure_local_ssh_registered"))
            stack.enter_context(mock.patch.object(self.w, "get_picogk_offers", return_value=[self.offer]))
            armed = stack.enter_context(mock.patch.object(self.w, "picogk_verify_armed_guard"))
            paid = stack.enter_context(mock.patch.object(self.w, "vast_request", return_value={"new_contract": 999}))
            stack.enter_context(mock.patch.object(self.w, "picogk_ssh_ready", side_effect=self.w.SafeError("synthetic failure")))
            destroy = stack.enter_context(mock.patch.object(self.w, "destroy_instance_verified"))
            with self.assertRaises(self.w.SafeError):
                self.w.launch_picogk_m64("synthetic", 50924858, self.manifest, "a" * 64)
        armed.assert_called_once()
        self.assertEqual(paid.call_args.kwargs["payload"]["disk"], 500)
        destroy.assert_called_once_with("synthetic", 999, expected_label=self.manifest["attempt_label"],
                                       expected_image=self.manifest["image_ref"])
        with self.assertRaises(self.w.SafeError):
            self.w.picogk_consume_attempt(self.manifest, "a" * 64, 50924858)

    def test_deadline_with_background_destroys_only_new_instance(self):
        self.manifest["deadline_epoch"] = int(time.time()) + 600
        self.save()
        fake_wrapper = self.root / "wrapper"
        fake_wrapper.write_text("# fixture, never executed\n")
        own = self.w.picogk_safe_instance(self.raw)
        proof = {"instance_id": 999, "destroyed": True, "verified_absent": True}
        with mock.patch.object(self.g.engine, "WRAPPER", fake_wrapper), \
             mock.patch.object(self.g, "initial_wrapper_call", side_effect=[[self.background], [self.background, own]]), \
             mock.patch.object(self.g.time, "monotonic", side_effect=[0, 0, 0, 400, 400]), \
             mock.patch.object(self.g.engine, "cleanup_until_absent", return_value=proof) as destroy, \
             redirect_stdout(io.StringIO()):
            result = self.g.initial_guard(self.path)
        self.assertTrue(result["verified_absent"])
        destroy.assert_called_once_with(999, self.manifest)


if __name__ == "__main__":
    unittest.main()
