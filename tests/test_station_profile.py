"""No credentials, network calls or rental: fixed-contract and failure-path checks."""
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


policy = load(ROOT / "deploy/openbao/station_profile.py", "station_policy_test")
guard = load(ROOT / "deploy/vast/station/deadline_guard.py", "station_guard_test")
prepare = load(ROOT / "deploy/vast/station/prepare.py", "station_prepare_test")


class StationProfileTests(unittest.TestCase):
    def setUp(self):
        self.wrapper = load(ROOT / "deploy/openbao/openbao-vastai", "station_wrapper_test")
        self.w = vars(self.wrapper)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.now = int(time.time())
        self.proof = {"image_ref": "ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:" + "a"*64,
                      "model": policy.MODEL, "model_revision": policy.REVISION, "platform": "linux/amd64",
                      "anonymous_registry_verified": True, "gated_read_access_verified": True,
                      "image_download_bytes": 20*10**9, "model_download_bytes": 184*10**9,
                      "published_ports": ["22/tcp", "47998/udp"]}
        path = self.directory / "qualification.json"
        policy.write_json(path, self.proof)
        self.pins = {"qualification_path": str(path), "qualification_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "guard_path": str(ROOT / "deploy/vast/station/deadline_guard.py"),
                     "guard_sha256": hashlib.sha256((ROOT / "deploy/vast/station/deadline_guard.py").read_bytes()).hexdigest(),
                     "session_directory": str(self.directory)}
        policy.write_json(self.directory / "session.json", {"profile": policy.PROFILE,
                          "created_epoch": self.now, "deadline_epoch": self.now + 21600, "budget_usd": 50.0})
        job = "station-" + "b"*20
        self.manifest = {"schema_version": "1.0.0", "profile": policy.PROFILE, "role": "llm", "variant": policy.PROFILE,
                         "job_id": job, "attempt_label": "3dprinting993-picogk-station-" + "b"*20, "sibling_label": "",
                         "image_ref": self.proof["image_ref"], "model": policy.MODEL, "model_revision": policy.REVISION,
                         "created_epoch": self.now, "deadline_epoch": self.now + 21600, "budget_usd": 50.0,
                         "download_budget_gb": 500, "upload_budget_gb": 100,
                         **{k: v for k, v in self.pins.items() if k != "session_directory"},
                         "guard_ready_path": str(self.directory / (job + ".guard-ready.json")),
                         "guard_service_name": "com.3dprinting993." + job}
        self.path = self.directory / (job + ".json")
        policy.write_json(self.path, self.manifest)

    def test_manifest_and_qualification_are_pinned(self):
        result = policy.prepare(self.w, ["launch-station", "48926609", str(self.path)], self.pins)
        self.assertEqual(result["manifest"]["image_ref"], self.proof["image_ref"])
        self.manifest["image_ref"] = self.proof["image_ref"].replace("a"*64, "c"*64)
        policy.write_json(self.path, self.manifest, replace=True)
        with self.assertRaises(self.wrapper.SafeError):
            policy.prepare(self.w, ["launch-station", "48926609", str(self.path)], self.pins)
        self.proof["image_ref"] = self.manifest["image_ref"]
        policy.write_json(Path(self.pins["qualification_path"]), self.proof, replace=True)
        with self.assertRaises(self.wrapper.SafeError):
            policy.prepare(self.w, ["station-offers"], self.pins)

    def test_fixed_model_namespace_ports_and_download_reserve(self):
        self.assertTrue(policy.qualification_valid(self.proof))
        for key, value in (("model_revision", "main"), ("gated_read_access_verified", 1),
                           ("published_ports", ["22/tcp", "8000/tcp", "47998/udp"]),
                           ("image_download_bytes", 100*10**9),
                           ("image_ref", "ghcr.io/cluster2600/3dprinting993-picogk-station@sha256:" + "a"*64),
                           ("image_ref", "elsewhere/image@sha256:" + "a"*64)):
            with self.subTest(key=key):
                self.assertFalse(policy.qualification_valid({**self.proof, key: value}))

    def test_deadline_budget_and_session_cannot_be_extended(self):
        for key, value in (("deadline_epoch", self.now+21601), ("budget_usd", 50.01),
                           ("download_budget_gb", 501), ("sibling_label", "another-rental")):
            with self.subTest(key=key):
                policy.write_json(self.path, {**self.manifest, key: value}, replace=True)
                with self.assertRaises(self.wrapper.SafeError):
                    policy.prepare(self.w, ["launch-station", "48926609", str(self.path)], self.pins)

    def test_cost_includes_storage_in_offer_tariff_and_all_reserves(self):
        expected = 6 * 6.585185185185185 + 500 * .0026666666666666666 + 100 * .004 + 2
        self.assertAlmostEqual(policy.budget_cost(self.w, self.manifest, 6.585185185185185, .004, .0026666666666666666), expected)
        for values in ((10, .01, .01), (6, float("nan"), .002), (6, .02, 0)):
            with self.assertRaises(self.wrapper.SafeError):
                policy.budget_cost(self.w, self.manifest, *values)

    def test_failed_attempt_reservations_are_never_refunded(self):
        policy.write_json(self.directory / "station-first.paid-attempt.json", {"cost_ceiling_usd": 35.0})
        policy.write_json(self.directory / "station-second.paid-attempt.json", {"cost_ceiling_usd": 10.0})
        self.assertEqual(policy.reserved_cost(self.w, self.directory), 45)
        policy.write_json(self.directory / "station-third.paid-attempt.json", {"paid_outcome": "unknown"})
        with self.assertRaises(self.wrapper.SafeError):
            policy.reserved_cost(self.w, self.directory)

    def test_station_reuses_hardware_filter_with_four_gpus_and_no_vm_requirement(self):
        policy.install_policy(self.w, {"proof": self.proof})
        offer = {"id": 48926609, "gpu_name": "RTX PRO 6000 S", "num_gpus": 4, "gpu_frac": .5,
                 "gpu_ram": 97887, "cpu_cores_effective": 64, "cpu_ram": 773829, "disk_space": 1000,
                 "dph_total": 6.585185185185185, "inet_up_cost": .004, "inet_down_cost": .002666666666,
                 "reliability": .995, "verified": True, "rentable": True, "rented": False}
        self.assertTrue(self.wrapper.engine_twin_offer_eligible(offer, "llm", policy.PROFILE))
        for key, value in (("num_gpus", 2), ("cpu_ram", 511999), ("cpu_cores_effective", 63),
                           ("disk_space", 999), ("gpu_name", "RTX 5090")):
            self.assertFalse(self.wrapper.engine_twin_offer_eligible({**offer, key: value}, "llm", policy.PROFILE))

    def test_network_caps_count_all_bytes_and_reject_counter_rollbacks(self):
        previous = {"eth0": {"rx_bytes": 100, "tx_bytes": 200}}
        self.assertTrue(guard.within_transfer_limit(previous, None, 20*10**9))
        self.assertFalse(guard.within_transfer_limit({"eth0": {"rx_bytes": 99, "tx_bytes": 200}}, previous, 0))
        self.assertFalse(guard.within_transfer_limit({"eth1": previous["eth0"]}, previous, 0))
        self.assertFalse(guard.within_transfer_limit({"eth0": {"rx_bytes": 460*10**9, "tx_bytes": 200}}, None, 20*10**9))
        self.assertFalse(guard.within_transfer_limit({"eth0": {"rx_bytes": 100, "tx_bytes": 100*10**9}}, None, 0))

    def test_surgical_wrapper_candidate_preserves_legacy_and_scoped_auth(self):
        source = (ROOT / "deploy/openbao/openbao-vastai").read_text()
        rendered = prepare.render(source, self.pins)
        namespace = {"__name__": "wrapper_render_test", "__file__": str(ROOT / "deploy/openbao/openbao-vastai")}
        exec(compile(rendered, "candidate", "exec"), namespace)
        self.assertEqual(namespace["_station_prepare"](["instances"]), (None, None))
        module, bundle = namespace["_station_prepare"](["station-offers"])
        self.assertEqual(bundle["proof"]["image_ref"], self.proof["image_ref"])
        self.assertIn("run", module)
        self.assertEqual(rendered.count("token = login()"), source.count("token = login()"))
        with self.assertRaises(ValueError):
            prepare.render(rendered, self.pins)

    def test_station_onstart_is_idle_and_never_loads_weights(self):
        policy.install_policy(self.w, {"proof": self.proof})
        command = self.wrapper.engine_twin_onstart(self.manifest)
        self.assertIn(" sleep ", command)
        self.assertIn("unset HF_TOKEN", command)
        self.assertNotIn("api_server", command)
        self.assertNotIn("snapshot_download", command)

    def test_guard_destruction_binds_id_and_manifest_in_wrapper(self):
        instance = {"id": 7, "label": self.manifest["attempt_label"], "image": self.manifest["image_ref"]}
        proof = {"instance_id": 7, "destroyed": True, "verified_absent": True}
        with mock.patch.object(guard, "call", side_effect=[instance, proof]) as call:
            self.assertEqual(guard.destroy_exact(7, self.manifest, self.path), proof)
            self.assertEqual(call.call_args_list, [mock.call("show", "7"),
                             mock.call("destroy-station", "7", str(self.path))])
        for changed in ({**instance, "label": "someone-else"}, {**instance, "image": "other-image"}):
            with mock.patch.object(guard, "call", return_value=changed) as call:
                with self.assertRaises(guard.engine.GuardError):
                    guard.destroy_exact(7, self.manifest, self.path)
                call.assert_called_once_with("show", "7")

    def test_cleanup_is_idempotent_and_preserves_prior_failed_receipt(self):
        bundle = policy.prepare(self.w, ["destroy-station", "7", str(self.path)], self.pins)
        created = {"instance_id": 7, "manifest_sha256": bundle["digest"],
                   "label": self.manifest["attempt_label"], "image_ref": self.manifest["image_ref"]}
        policy.write_json(self.path.with_suffix(".provider-created.json"), created)
        policy.write_json(self.path.with_suffix(".cleanup.json"), {"verified_absent": False})
        proof = {"instance_id": 7, "verified_absent": True, "destroyed": True}
        self.w["engine_twin_reconcile"] = mock.Mock(return_value=proof)
        self.w["print_json"] = mock.Mock()
        for _ in range(2):
            self.assertEqual(policy.run(self.w, "synthetic", ["destroy-station", "7", str(self.path)], bundle), 0)
        self.w["engine_twin_reconcile"].assert_called_with("synthetic", bundle["manifest"], bundle["digest"], expected_instance_id=7)
        self.assertEqual(json.loads(self.path.with_suffix(".cleanup.json").read_text()), {"verified_absent": False})
        with self.assertRaises(self.wrapper.SafeError):
            policy.run(self.w, "synthetic", ["destroy-station", "8", str(self.path)], bundle)

    def test_stale_remaining_budget_cannot_survive_another_paid_attempt(self):
        policy.write_json(self.directory / "station-earlier.paid-attempt.json", {"cost_ceiling_usd": 5.0})
        bundle = policy.prepare(self.w, ["launch-station", "48926609", str(self.path)], self.pins)
        self.w["get_engine_twin_offers"] = mock.Mock(return_value=[{"dph_total": 6.585185185185185,
            "inet_up_cost": .004, "inet_down_cost": .0026666666666666666}])
        self.w["launch_engine_twin"] = lambda api, offer_id, manifest, sha: self.w["picogk_consume_attempt"](manifest, sha, offer_id)
        with self.assertRaises(self.wrapper.SafeError):
            policy.run(self.w, "synthetic", ["launch-station", "48926609", str(self.path)], bundle)
        self.assertFalse(self.path.with_suffix(".paid-attempt.json").exists())


if __name__ == "__main__":
    unittest.main()
