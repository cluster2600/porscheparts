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
        self.assertIn("UNEXPECTED_LISTENER", idle)
        for forbidden in ("vllm", "--port", "curl ", "pip "):
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

    def test_guard_waits_for_state_less_listing_but_not_terminal_states(self):
        self.assertTrue(self.g.startup_pending({"status": None, "provider_states": None}))
        self.assertTrue(self.g.startup_pending({"status": None, "provider_states": {
            "actual_status": None, "cur_state": None, "next_state": None, "intended_status": None}}))
        self.assertTrue(self.g.startup_pending({"status": "loading", "provider_states": {
            "actual_status": "loading", "cur_state": None, "next_state": None, "intended_status": None}}))
        for states in ({"actual_status": "exited", "cur_state": None, "next_state": None, "intended_status": None},
                       {"actual_status": None, "cur_state": None, "next_state": None, "intended_status": "stopped"}):
            with self.subTest(states=states):
                self.assertFalse(self.g.startup_pending({"status": states["actual_status"], "provider_states": states}))
        self.assertIs(self.g.engine.startup_pending, self.g.startup_pending)

    def test_published_ports_are_role_specific(self):
        self.assertEqual(self.w.ENGINE_TWIN_ALLOWED_PUBLISHED_PORTS["llm"], {"22/tcp"})
        offer = self.offer("compute", gpu_frac=0.5)
        m = self.manifests["compute"]
        raw = {"id": 7, "label": m["attempt_label"], "image_uuid": m["image_ref"], "actual_status": "running",
               "gpu_name": offer["gpu_name"], "num_gpus": 1, "gpu_frac": 0.5, "gpu_ram": 97887,
               "cpu_cores_effective": 128, "cpu_ram": 1031835, "disk_space": 500, "dph_total": 2.0,
               "inet_up_cost": 0.001, "inet_down_cost": 0.001, "verification": "verified",
               "ports": {p: [{"HostPort": "1"}] for p in ("22/tcp", "8000/tcp", "8001/tcp", "8100/tcp", "8200/tcp")}}
        self.w.engine_twin_contract(raw, 7, m, offer)
        self.assertTrue(self.w.engine_twin_metadata_pending(raw, offer, m))
        for extra in ("9000/tcp", "8000/udp"):
            with self.subTest(extra=extra):
                bad = {**raw, "ports": {**raw["ports"], extra: [{"HostPort": "2"}]}}
                with self.assertRaises(self.w.SafeError):
                    self.w.engine_twin_contract(bad, 7, m, offer)
                self.assertFalse(self.w.engine_twin_metadata_pending(bad, offer, m))
        llm = {**self.manifests["llm"]}
        llm_raw = {**raw, "label": llm["attempt_label"], "image_uuid": llm["image_ref"]}
        with self.assertRaises(self.w.SafeError):
            self.w.engine_twin_contract(llm_raw, 7, llm, offer)

    def test_guard_api_port_allowed_for_compute_only(self):
        instance = {"dph_total": 2.0, "inet_up_cost_usd_per_gb": 0.001, "inet_down_cost_usd_per_gb": 0.001, "api_port": "33000"}
        self.g.validate_manifest(self.manifests["llm"])
        self.assertFalse(self.g.cost_valid(instance, self.manifests["llm"]))
        self.g.validate_manifest(self.manifests["compute"])
        self.assertTrue(self.g.cost_valid(instance, self.manifests["compute"]))

    def flashnext_manifest(self):
        spec = self.w.ENGINE_TWIN_FLASHNEXT
        proof = {"image_ref": spec["image"], "platform": "linux/amd64", "anonymous_registry_verified": True,
                 "model": spec["model"], "model_revision": spec["revision"], "gated_read_access_verified": True,
                 "image_download_bytes": 8_634_500_849, "model_download_bytes": 236_000_000_000}
        proof_path = self.root / "llm-flashnext-qualification.json"
        proof_path.write_text(json.dumps(proof))
        m = {**self.manifests["llm"], "image_ref": spec["image"], "model": spec["model"],
             "model_revision": spec["revision"], "variant": "qwen38-flash-next", "download_budget_gb": 248,
             "qualification_path": str(proof_path),
             "qualification_sha256": hashlib.sha256(proof_path.read_bytes()).hexdigest()}
        return m

    def test_flashnext_variant_manifest_guard_and_limits(self):
        m = self.flashnext_manifest()
        loaded, _ = self.w.engine_twin_load_manifest(self.save(m))
        self.assertEqual(loaded["variant"], "qwen38-flash-next")
        self.g.validate_manifest(m)
        self.assertEqual(self.g.FLASHNEXT["image"], self.w.ENGINE_TWIN_FLASHNEXT["image"])
        self.assertEqual(self.g.FLASHNEXT["max_dph"], self.w.ENGINE_TWIN_FLASHNEXT["max_dph"])
        self.assertEqual(self.g.FLASHNEXT["download_cap_gb"], self.w.ENGINE_TWIN_FLASHNEXT["download_cap_gb"])
        spec = self.w.ENGINE_TWIN_FLASHNEXT
        self.assertLessEqual(spec["max_dph"] * 6 + spec["download_cap_gb"] * 0.01 + 20 * 0.01 + 1, 30)
        for key, value in (("variant", "other"), ("image_ref", self.w.RESEARCH_IMAGE), ("download_budget_gb", 251),
                           ("model_revision", self.w.RESEARCH_REVISION)):
            with self.subTest(key=key):
                with self.assertRaises(self.w.SafeError):
                    self.w.engine_twin_load_manifest(self.save({**m, key: value}))
        public = json.loads(Path(m["qualification_path"]).read_text())
        public.pop("gated_read_access_verified")
        Path(m["qualification_path"]).write_text(json.dumps({**public, "public_weights_verified": True}))
        with self.assertRaises(self.w.SafeError):
            self.w.engine_twin_load_manifest(self.save({**m, "qualification_sha256": hashlib.sha256(Path(m["qualification_path"]).read_bytes()).hexdigest()}))
        with self.assertRaises(self.w.SafeError):
            self.w.engine_twin_spec("compute", "qwen38-flash-next")
        with self.assertRaises(self.g.engine.GuardError):
            self.g.validate_manifest({**self.manifests["compute"], "variant": "qwen38-flash-next"})

    def test_flashnext_offers_contract_ports_and_idle_onstart(self):
        m = self.flashnext_manifest()
        offer = self.offer("llm", gpu_name="RTX PRO 6000 WS", num_gpus=2, gpu_ram=97887, cpu_cores_effective=48,
                           cpu_ram=256000, disk_space=400, dph_total=3.9)
        self.assertTrue(self.w.engine_twin_offer_eligible(offer, "llm", "qwen38-flash-next"))
        self.assertFalse(self.w.engine_twin_offer_eligible(offer, "llm"))
        self.assertFalse(self.w.engine_twin_offer_eligible({**offer, "num_gpus": 1}, "llm", "qwen38-flash-next"))
        self.assertFalse(self.w.engine_twin_offer_eligible({**offer, "dph_total": 4.21}, "llm", "qwen38-flash-next"))
        self.assertEqual(self.w.engine_twin_role_token("llm+qwen38-flash-next"), ("llm", "qwen38-flash-next"))
        for token in ("compute+qwen38-flash-next", "llm+x", "gpu"):
            with self.assertRaises(self.w.SafeError):
                self.w.engine_twin_role_token(token)
        with mock.patch.object(self.w, "vast_request", return_value={"offers": [offer]}) as call:
            self.assertEqual(len(self.w.get_engine_twin_offers("synthetic", "llm", 123, "qwen38-flash-next")), 1)
        self.assertEqual(call.call_args.kwargs["payload"]["num_gpus"], {"eq": 2})
        self.assertEqual(call.call_args.kwargs["payload"]["dph_total"], {"lte": 4.20})
        raw = {"id": 7, "label": m["attempt_label"], "image_uuid": m["image_ref"], "actual_status": "running",
               "gpu_name": offer["gpu_name"], "num_gpus": 2, "gpu_frac": 1, "gpu_ram": 97887,
               "cpu_cores_effective": 48, "cpu_ram": 256000, "disk_space": 400, "dph_total": 3.9,
               "inet_up_cost": 0.001, "inet_down_cost": 0.001, "verification": "verified",
               "ports": {p: [{"HostPort": "1"}] for p in ("22/tcp", "8000/tcp")}}
        self.w.engine_twin_contract(raw, 7, m, offer)
        with self.assertRaises(self.w.SafeError):
            self.w.engine_twin_contract({**raw, "ports": {**raw["ports"], "8001/tcp": [{"HostPort": "2"}]}}, 7, m, offer)
        with mock.patch.object(self.w.time, "time", return_value=m["created_epoch"]):
            idle = self.w.engine_twin_onstart(m)
        self.assertIn("UNEXPECTED_LISTENER", idle)
        for forbidden in ("vllm", "HF_TOKEN=", "start.sh", "--port"):
            self.assertNotIn(forbidden, idle)
        self.g.validate_manifest(m)
        instance = {"dph_total": 3.9, "inet_up_cost_usd_per_gb": 0.001, "inet_down_cost_usd_per_gb": 0.001, "api_port": "4000"}
        self.assertTrue(self.g.cost_valid(instance, m))
        self.assertFalse(self.g.cost_valid({**instance, "dph_total": 4.3}, m))

    def test_lookup_waits_only_for_identity_less_records(self):
        for raw in (None, {}, [], {"id": None, "label": "", "image_uuid": None, "ports": None}):
            with self.subTest(raw=raw):
                self.assertTrue(self.w.engine_twin_lookup_not_yet_visible(raw))
        for raw in ({"id": 5}, {"label": "other"}, {"image_uuid": "x"}):
            with self.subTest(raw=raw):
                self.assertFalse(self.w.engine_twin_lookup_not_yet_visible(raw))

    def test_cli_rejects_bad_arguments_before_login(self):
        with mock.patch.object(self.w, "login", side_effect=AssertionError("login must not run")):
            for operation in (["engine-twin-offers"], ["engine-twin-offers", "gpu"], ["engine-twin-offers", "llm", "x"],
                              ["launch-engine-twin", "1"], ["launch-engine-twin", "0", "/tmp/x.json"]):
                with self.subTest(operation=operation):
                    with self.assertRaises(self.w.SafeError):
                        self.w.run(operation)


if __name__ == "__main__":
    unittest.main()
