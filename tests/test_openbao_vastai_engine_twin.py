"""Profil engine-twin-v1 : donnees synthetiques, ni reseau ni secret."""
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
HEX = "c" * 20


def load(relative, name):
    loader = SourceFileLoader(name, str(ROOT / relative))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class EngineTwinTests(unittest.TestCase):
    def setUp(self):
        self.w = load("deploy/openbao/openbao-vastai", "engine_twin_wrapper_test")
        self.g = load("deploy/vast/engine-twin/deadline_guard.py", "engine_twin_guard_test")
        self.temp = tempfile.TemporaryDirectory(prefix="engine-twin-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.guard = ROOT / "deploy/vast/engine-twin/deadline_guard.py"
        self.manifests = {role: self.make(role) for role in ("llm", "compute")}

    def make(self, role):
        proof = {"image_ref": self.w.ENGINE_TWIN_IMAGES[role], "platform": "linux/amd64",
                 "anonymous_registry_verified": True, "image_download_bytes": 20_000_000_000}
        if role == "llm":
            proof.update(model=self.w.RESEARCH_MODEL, model_revision=self.w.RESEARCH_REVISION,
                         public_weights_verified=True, model_download_bytes=32_000_000_000)
        proof_path = self.root / f"{role}-qualification.json"
        proof_path.write_text(json.dumps(proof))
        now = int(time.time())
        other = "compute" if role == "llm" else "llm"
        job = f"engine-twin-{role}-fixture"
        return {"schema_version": "1.0.0", "profile": "engine-twin-v1", "role": role, "job_id": job,
                "attempt_label": f"3dprinting993-engine-twin-{role}-{HEX}",
                "sibling_label": f"3dprinting993-engine-twin-{other}-{HEX}",
                "image_ref": self.w.ENGINE_TWIN_IMAGES[role],
                "model": self.w.RESEARCH_MODEL, "model_revision": self.w.RESEARCH_REVISION,
                "created_epoch": now - 1, "deadline_epoch": now + 21599, "budget_usd": 30,
                "download_budget_gb": 60, "upload_budget_gb": 10,
                "qualification_path": str(proof_path),
                "qualification_sha256": hashlib.sha256(proof_path.read_bytes()).hexdigest(),
                "guard_path": str(self.guard), "guard_sha256": hashlib.sha256(self.guard.read_bytes()).hexdigest(),
                "guard_ready_path": str(self.root / f"{job}.guard-ready.json")}

    def save(self, manifest):
        path = self.root / f"{manifest['job_id']}.json"
        path.write_text(json.dumps(manifest))
        return path

    def offer(self, role, **changes):
        gpus, gpu_ram, cores, ram, disk = self.w.ENGINE_TWIN_HARDWARE[role]
        base = {"id": 123, "gpu_name": gpus[0], "gpu_ram": gpu_ram, "gpu_frac": 1, "num_gpus": 1,
                "cpu_cores_effective": cores, "cpu_ram": ram, "disk_space": disk, "dph_total": 2.0,
                "reliability": 0.995, "verified": True, "rentable": True, "rented": False,
                "inet_up_cost": 0.001, "inet_down_cost": 0.001}
        return {**base, **changes}

    def test_guard_fingerprint_is_pinned_and_guard_accepts_both_roles(self):
        self.assertEqual(hashlib.sha256(self.guard.read_bytes()).hexdigest(), self.w.ENGINE_TWIN_GUARD_SHA256)
        for role, manifest in self.manifests.items():
            with self.subTest(role=role):
                loaded, digest = self.w.engine_twin_load_manifest(self.save(manifest))
                self.assertEqual(loaded, manifest)
                self.g.validate_manifest(manifest)
                self.assertEqual(self.g.IMAGES[role], self.w.ENGINE_TWIN_IMAGES[role])
        self.assertEqual(self.g.MAX_DPH, self.w.ENGINE_TWIN_MAX_DPH)
        self.assertEqual(self.g.MAX_SECONDS, self.w.ENGINE_TWIN_MAX_SECONDS)
        self.assertEqual(self.g.MAX_BUDGET_USD, self.w.ENGINE_TWIN_MAX_BUDGET_USD)

    def test_two_roles_stay_under_the_session_ceiling(self):
        self.assertLessEqual(2 * self.w.ENGINE_TWIN_MAX_BUDGET_USD, 60.0)
        self.assertLessEqual(self.w.ENGINE_TWIN_MAX_DPH * self.w.ENGINE_TWIN_MAX_SECONDS / 3600 + 1,
                             self.w.ENGINE_TWIN_MAX_BUDGET_USD)

    def test_manifest_rejects_out_of_contract_values(self):
        base = self.manifests["llm"]
        cases = (("image_ref", self.w.SIMREADY_IMAGE), ("role", "compute"), ("model_revision", "main"),
                 ("sibling_label", f"3dprinting993-engine-twin-compute-{'d' * 20}"),
                 ("attempt_label", f"3dprinting993-engine-twin-llm-{'d' * 20}"),
                 ("guard_sha256", "0" * 64), ("qualification_sha256", "0" * 64),
                 ("budget_usd", 30.01), ("budget_usd", True), ("download_budget_gb", 80.01),
                 ("upload_budget_gb", 20.01), ("deadline_epoch", base["created_epoch"] + 21601),
                 ("job_id", "engine-twin-compute-fixture"), ("extra", 1))
        for key, value in cases:
            with self.subTest(key=key):
                with self.assertRaises(self.w.SafeError):
                    self.w.engine_twin_load_manifest(self.save({**base, key: value}))

    def test_offer_limits_per_role(self):
        self.assertTrue(self.w.engine_twin_offer_eligible(self.offer("llm"), "llm"))
        self.assertTrue(self.w.engine_twin_offer_eligible(self.offer("compute"), "compute"))
        self.assertFalse(self.w.engine_twin_offer_eligible(self.offer("llm"), "compute"))
        for field, value in (("dph_total", 2.61), ("gpu_ram", 79999), ("num_gpus", 2), ("reliability", 0.98),
                             ("inet_down_cost", 0.02), ("rented", True), ("verified", False)):
            with self.subTest(field=field):
                self.assertFalse(self.w.engine_twin_offer_eligible(self.offer("llm", **{field: value}), "llm"))
        with self.assertRaises(self.w.SafeError):
            self.w.engine_twin_offer_eligible(self.offer("llm"), "shell")

    def test_offer_query_is_bounded(self):
        with mock.patch.object(self.w, "vast_request", return_value={"offers": [self.offer("compute"), self.offer("compute", id=9, dph_total=3)]}) as call:
            self.assertEqual([o["id"] for o in self.w.get_engine_twin_offers("synthetic", "compute", 123)], [123])
        query = call.call_args.kwargs["payload"]
        self.assertEqual(query["dph_total"], {"lte": 2.60})
        self.assertEqual(query["cpu_cores_effective"], {"gte": 64})
        self.assertEqual(query["allocated_storage"], 500)

    def test_singleton_tolerates_only_the_exact_sibling(self):
        m = self.manifests["compute"]
        sibling = {"id": 1, "label": m["sibling_label"]}
        own = {"id": 2, "label": m["attempt_label"]}
        cases = (
            ([], None, True), ([sibling], None, True), ([{"id": 3, "label": "other"}], None, False),
            ([sibling, {"id": 4, "label": m["sibling_label"]}], None, False),
            ([sibling, own], 2, True), ([own], 2, True), ([sibling, own, {"id": 5, "label": "x"}], 2, False),
        )
        for inventory, instance_id, ok in cases:
            with self.subTest(inventory=inventory, instance_id=instance_id):
                with mock.patch.object(self.w, "strict_instance_inventory", return_value=inventory):
                    if ok:
                        self.w.engine_twin_singleton("synthetic", instance_id, m)
                    else:
                        with self.assertRaises(self.w.SafeError):
                            self.w.engine_twin_singleton("synthetic", instance_id, m)

    def test_onstart_commands(self):
        llm = {**self.manifests["llm"], "deadline_epoch": 2_000_021_600}
        compute = {**self.manifests["compute"], "deadline_epoch": 2_000_021_600}
        with mock.patch.object(self.w.time, "time", return_value=2_000_000_000):
            serve = self.w.engine_twin_onstart(llm)
            idle = self.w.engine_twin_onstart(compute)
        self.assertIn("--kill-after=30 20340", serve)
        self.assertIn(self.w.RESEARCH_REVISION, serve)
        self.assertIn("--host 127.0.0.1", serve)
        self.assertIn("unset HF_TOKEN HUGGING_FACE_HUB_TOKEN", serve)
        self.assertIn("sleep 20340", idle)
        for forbidden in ("vllm", "8000", "curl ", "pip "):
            self.assertNotIn(forbidden, idle)
        with mock.patch.object(self.w.time, "time", return_value=2_000_021_000):
            with self.assertRaises(self.w.SafeError):
                self.w.engine_twin_onstart(llm)

    def test_budget_cost_caps(self):
        m = self.manifests["llm"]
        self.assertLessEqual(self.w.engine_twin_budget_cost(m, 2.6, 0.01, 0.01), 30)
        for price, up, down in ((2.61, 0, 0), (2.0, 0.02, 0), (None, 0, 0)):
            with self.assertRaises(self.w.SafeError):
                self.w.engine_twin_budget_cost(m, price, up, down)

    def test_guard_hides_only_exact_sibling(self):
        m = self.manifests["llm"]
        self.g.validate_manifest(m)
        inventory = [{"id": 1, "label": m["sibling_label"]}, {"id": 2, "label": "unrelated"},
                     {"id": 3, "label": m["attempt_label"]}]
        with mock.patch.object(self.g, "initial_wrapper_call", return_value=inventory):
            self.assertEqual([i["id"] for i in self.g.wrapper_call("instances")], [2, 3])
        with mock.patch.object(self.g, "initial_wrapper_call", return_value=inventory[:1] * 2):
            with self.assertRaises(self.g.engine.GuardError):
                self.g.wrapper_call("instances")
        instance = {"dph_total": 2.6, "inet_up_cost_usd_per_gb": 0.01, "inet_down_cost_usd_per_gb": 0.01}
        self.assertTrue(self.g.cost_valid(instance, m))
        self.assertFalse(self.g.cost_valid({**instance, "dph_total": 2.61}, m))

    def test_cli_rejects_bad_arguments_before_login(self):
        with mock.patch.object(self.w, "login", side_effect=AssertionError("login must not run")):
            for operation in (["engine-twin-offers"], ["engine-twin-offers", "gpu"], ["engine-twin-offers", "llm", "x"],
                              ["launch-engine-twin", "1"], ["launch-engine-twin", "0", "/tmp/x.json"]):
                with self.subTest(operation=operation):
                    with self.assertRaises(self.w.SafeError):
                        self.w.run(operation)


if __name__ == "__main__":
    unittest.main()
