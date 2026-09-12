"""Research rental contracts using synthetic data: no network or secrets."""
from contextlib import ExitStack, nullcontext, redirect_stdout, redirect_stderr
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
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


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.w = load("deploy/openbao/openbao-vastai", "research_wrapper_test")
        self.g = load("deploy/vast/research/deadline_guard.py", "research_guard_test")
        self.temp = tempfile.TemporaryDirectory(prefix="research-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "job.json"
        guard = ROOT / "deploy/vast/research/deadline_guard.py"
        proof = {"image_ref": self.w.RESEARCH_IMAGE, "image_tag": self.w.IMAGE, "platform": "linux/amd64",
                 "anonymous_registry_verified": True, "model": self.w.RESEARCH_MODEL,
                 "model_revision": self.w.RESEARCH_REVISION, "public_weights_verified": True,
                 "image_download_bytes": 10_000_000_000, "model_download_bytes": 30_000_000_000}
        self.proof_path = self.root / "qualification.json"
        self.proof_path.write_text(json.dumps(proof))
        now = int(time.time())
        self.manifest = {"schema_version": "1.0.0", "profile": "research-qwen-v1", "job_id": "research-qwen-fixture",
                         "attempt_label": self.w.RESEARCH_LABEL + "-" + "b" * 20, "image_ref": self.w.RESEARCH_IMAGE,
                         "model": self.w.RESEARCH_MODEL, "model_revision": self.w.RESEARCH_REVISION,
                         "created_epoch": now - 1, "deadline_epoch": now + 3599, "budget_usd": 4,
                         "download_budget_gb": 60, "upload_budget_gb": 1,
                         "qualification_path": str(self.proof_path),
                         "qualification_sha256": hashlib.sha256(self.proof_path.read_bytes()).hexdigest(),
                         "guard_path": str(guard), "guard_sha256": hashlib.sha256(guard.read_bytes()).hexdigest(),
                         "guard_ready_path": str(self.root / "research-qwen-fixture.guard-ready.json")}
        self.offer = {"id": 123, "gpu_name": "L40S", "gpu_ram": 48000, "gpu_frac": 1, "num_gpus": 1,
                      "cpu_cores_effective": 16, "cpu_ram": 64000, "disk_space": 100,
                      "dph_total": 0.5, "reliability": 0.999, "verified": True, "rentable": True,
                      "rented": False, "inet_up_cost": 0.001, "inet_down_cost": 0.001}
        self.raw = {**self.offer, "id": 999, "label": self.manifest["attempt_label"], "actual_status": "running",
                    "image_uuid": self.w.RESEARCH_IMAGE, "verification": "verified", "ports": {"22/tcp": [{"HostPort": "1234"}]}}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.manifest))

    def test_fixed_manifest_and_guard_fingerprints(self):
        manifest, digest = self.w.research_load_manifest(self.path)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(digest, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.g.validate_manifest(self.manifest)
        self.assertEqual(manifest["guard_sha256"], self.w.RESEARCH_GUARD_SHA256)
        self.assertEqual(self.g.IMAGE, self.w.RESEARCH_IMAGE)
        self.assertEqual(self.g.REVISION, self.w.RESEARCH_REVISION)

    def test_manifest_rejects_mutable_or_unqualified_inputs(self):
        cases = (("image_ref", "vllm/vllm-openai:v0.19.0"), ("model_revision", "main"),
                 ("model", "other/model"), ("guard_sha256", "c" * 64), ("qualification_sha256", "c" * 64),
                 ("budget_usd", 4.01), ("budget_usd", True), ("download_budget_gb", 60.01),
                 ("upload_budget_gb", 1.01), ("deadline_epoch", self.manifest["created_epoch"] + 7201))
        for key, value in cases:
            with self.subTest(key=key):
                original = self.manifest[key]
                self.manifest[key] = value
                self.save()
                with self.assertRaises(self.w.SafeError):
                    self.w.research_load_manifest(self.path)
                self.manifest[key] = original

    def test_optional_specialist_mode_preserves_legacy_and_guard_contract(self):
        self.assertEqual(self.w.research_execution_mode(self.manifest), "qwen-server-v1")
        self.manifest["execution_mode"] = "cad-specialists-v1"
        self.save()
        manifest, _digest = self.w.research_load_manifest(self.path)
        self.assertEqual(manifest, self.manifest)
        self.g.validate_manifest(manifest)
        self.assertEqual(hashlib.sha256(Path(manifest["guard_path"]).read_bytes()).hexdigest(),
                         self.w.RESEARCH_GUARD_SHA256)
        self.assertAlmostEqual(self.w.research_budget_cost(manifest, 0.5, 0.001, 0.001), 1.561)

    def test_specialist_mode_rejects_arbitrary_commands_and_unknown_fields(self):
        original = dict(self.manifest)
        for value in ("shell", "cad-specialists-v1; touch /tmp/forbidden", None, True, [], {}):
            with self.subTest(value=value):
                self.manifest = {**original, "execution_mode": value}
                self.save()
                with self.assertRaises(self.w.SafeError):
                    self.w.research_load_manifest(self.path)
                with self.assertRaises(self.w.SafeError):
                    self.w.research_onstart(self.manifest)
        self.manifest = {**original, "execution_mode": "cad-specialists-v1", "command": "arbitrary"}
        self.save()
        with self.assertRaises(self.w.SafeError):
            self.w.research_load_manifest(self.path)

    def test_specialist_idle_has_relative_deadline_no_model_download_or_api(self):
        manifest = {**self.manifest, "execution_mode": "cad-specialists-v1", "deadline_epoch": 2_000_003_600}
        with mock.patch.object(self.w.time, "time", return_value=2_000_000_000):
            command = self.w.research_onstart(manifest)
        self.assertIn("--kill-after=30 2340 sleep 2340", command)
        self.assertIn("unset HF_TOKEN HUGGING_FACE_HUB_TOKEN", command)
        self.assertIn("HF_HUB_DISABLE_IMPLICIT_TOKEN=1", command)
        self.assertIn("/workspace/research-cad-idle.log", command)
        for forbidden in ("vllm", "Qwen", "--model", "--host", "8000", "pip ", "curl ", "date"):
            self.assertNotIn(forbidden, command)

    def test_specialist_offers_accept_24gb_without_weakening_qwen_profile(self):
        small = {**self.offer, "gpu_name": "RTX 4090", "gpu_ram": 24000,
                 "cpu_cores_effective": 8, "cpu_ram": 32000}
        self.assertTrue(self.w.cad_specialist_offer_eligible(small))
        self.assertFalse(self.w.research_offer_eligible(small))
        ada48 = {**small, "gpu_name": "RTX 5880Ada", "gpu_ram": 49140,
                 "cpu_cores_effective": 21.33, "cpu_ram": 128974}
        self.assertTrue(self.w.cad_specialist_offer_eligible(ada48))
        self.assertFalse(self.w.research_offer_eligible(ada48))
        for field, value in (("gpu_name", "RTX 4060"), ("gpu_ram", 22999), ("cpu_cores_effective", 7),
                             ("cpu_ram", 31999), ("dph_total", 0.851), ("disk_space", 99), ("num_gpus", 2)):
            with self.subTest(field=field):
                self.assertFalse(self.w.cad_specialist_offer_eligible({**small, field: value}))
        with mock.patch.object(self.w, "vast_request", return_value={"offers": [small, {**small, "id": 456}]}) as call, \
             redirect_stderr(io.StringIO()):
            self.assertEqual(self.w.get_cad_specialist_offers("synthetic", 123), [small])
        query = call.call_args.kwargs["payload"]
        self.assertEqual(query["gpu_ram"], {"gte": 23000})
        self.assertEqual(query["cpu_cores_effective"], {"gte": 8})
        self.assertEqual(query["cpu_ram"], {"gte": 32000})
        self.assertEqual(query["gpu_name"], {"in": list(self.w.RESEARCH_CAD_GPUS)})
        self.assertEqual(query["allocated_storage"], 100)

    def test_specialist_contract_and_pending_state_use_fixed_small_resource_floor(self):
        manifest = {**self.manifest, "execution_mode": "cad-specialists-v1"}
        offer = {**self.offer, "gpu_name": "RTX 3090", "gpu_ram": 24000,
                 "cpu_cores_effective": 8, "cpu_ram": 32000}
        raw = {**self.raw, **{key: offer[key] for key in ("gpu_name", "gpu_ram", "cpu_cores_effective", "cpu_ram")}}
        self.w.research_contract(raw, 999, manifest, offer)
        with self.assertRaises(self.w.SafeError):
            self.w.research_contract(raw, 999, self.manifest, offer)
        pending = {**raw, "ports": None, "actual_status": "loading"}
        self.assertTrue(self.w.research_metadata_pending(pending, offer, manifest))
        self.assertFalse(self.w.research_metadata_pending({**pending, "gpu_ram": 22999}, offer, manifest))
        self.assertFalse(self.w.research_metadata_pending({**pending, "ports": {"8000/tcp": [{}]}}, offer, manifest))
        diagnostic = self.w.research_contract_diagnostic(raw, 999, manifest, offer, "contract")
        self.assertEqual(diagnostic["expected"]["gpu_ram_mb_min"], 23000)
        self.assertEqual(diagnostic["expected"]["cpu_ram_mb_min"], 32000)
        self.assertEqual(diagnostic["observed"]["gpu"], "RTX 3090")

    def test_specialist_selection_reuses_listing_query_without_changing_bundle_window(self):
        small = {**self.offer, "gpu_name": "RTX 3090", "gpu_ram": 24000,
                 "cpu_cores_effective": 8, "cpu_ram": 32000}
        def bundles(_key, _path, **kwargs):
            # Changing Vast's query window can produce different bundle IDs.
            return {"offers": [small, {**small, "id": 456}] if kwargs["payload"]["limit"] == 100 else []}
        with mock.patch.object(self.w, "vast_request", side_effect=bundles) as call, redirect_stderr(io.StringIO()):
            self.assertEqual(self.w.get_cad_specialist_offers("synthetic"), [small, {**small, "id": 456}])
            self.assertEqual(self.w.get_cad_specialist_offers("synthetic", 123), [small])
            self.assertEqual(self.w.get_cad_specialist_offers("synthetic", 789), [])
        self.assertEqual(call.call_args_list[0].kwargs["payload"], call.call_args_list[1].kwargs["payload"])
        self.assertEqual(call.call_args_list[0].kwargs["payload"], call.call_args_list[2].kwargs["payload"])

    def test_specialist_launch_uses_dedicated_offers_and_does_not_claim_qwen_served(self):
        self.manifest["execution_mode"] = "cad-specialists-v1"
        result = io.StringIO()
        with ExitStack() as stack:
            self.setup_launch(stack)
            stack.enter_context(redirect_stdout(result))
            dedicated = stack.enter_context(mock.patch.object(self.w, "get_cad_specialist_offers", return_value=[self.offer]))
            legacy = stack.enter_context(mock.patch.object(self.w, "get_research_offers"))
            call = stack.enter_context(mock.patch.object(self.w, "vast_request", side_effect=[{"new_contract": 999}, {"instances": self.raw}]))
            self.assertEqual(self.w.launch_research("synthetic", 123, self.manifest, "a" * 64), 0)
            dedicated.assert_called_once_with("synthetic", 123)
            legacy.assert_not_called()
        payload = call.call_args_list[0].kwargs["payload"]
        self.assertEqual(payload["image"], self.w.RESEARCH_IMAGE)
        self.assertEqual(payload["env"], {})
        self.assertNotIn("vllm", payload["onstart"])
        receipt = json.loads(result.getvalue())
        self.assertEqual(receipt["execution_mode"], "cad-specialists-v1")
        self.assertIsNone(receipt["model"])
        self.assertIsNone(receipt["model_revision"])
        self.assertIsNone(receipt["api_bind"])
        self.assertFalse(receipt["model_ready_verified"])
        self.assertFalse(receipt["specialist_weights_verified"])
        self.assertEqual(receipt["base_profile_model"], self.w.RESEARCH_MODEL)

    def test_specialist_selection_diagnostic_reports_exact_ids_without_provider_fields(self):
        secret = "PRIVATE_PROVIDER_NEVER_PRINT"
        raw = [self.offer, {**self.offer, "id": 456, "env": {"HF_TOKEN": secret}},
               {**self.offer, "id": 789, "gpu_name": secret}, {"id": secret}, {"id": True}, None]
        result = io.StringIO()
        with mock.patch.object(self.w, "vast_request", return_value={"offers": raw}), redirect_stderr(result):
            self.assertEqual(self.w.get_cad_specialist_offers("synthetic", 789), [])
        rendered = result.getvalue()
        self.assertNotIn(secret, rendered)
        self.assertNotIn("HF_TOKEN", rendered)
        self.assertNotIn("gpu_name", rendered)
        diagnostic = json.loads(rendered.split(" ", 1)[1])
        self.assertEqual(diagnostic["selected_offer_id"], 789)
        self.assertEqual(diagnostic["raw_count"], 6)
        self.assertEqual(diagnostic["raw_offer_ids"], [123, 456, 789])
        self.assertEqual(diagnostic["eligible_offer_ids"], [123, 456])
        self.assertEqual(diagnostic["raw_exact_matches"], 1)
        self.assertEqual(diagnostic["eligible_exact_matches"], 0)
        self.assertEqual(len(diagnostic["query_sha256"]), 64)

    def test_specialist_selected_offer_read_only_operation_never_creates_or_changes_keys(self):
        with mock.patch.object(self.w, "login", return_value="synthetic"), \
             mock.patch.object(self.w, "read_vast_key", return_value="synthetic"), \
             mock.patch.object(self.w, "revoke_token"), \
             mock.patch.object(self.w, "get_cad_specialist_offers", return_value=[self.offer]) as offers, \
             mock.patch.object(self.w, "launch_research") as launch, \
             mock.patch.object(self.w, "ensure_local_ssh_registered") as keys, redirect_stdout(io.StringIO()):
            self.assertEqual(self.w.run(["cad-specialist-offers", "123"]), 0)
            offers.assert_called_once_with("synthetic", 123)
            launch.assert_not_called()
            keys.assert_not_called()

    def test_unmeasured_downloads_or_wrong_architecture_rejected(self):
        proof = json.loads(self.proof_path.read_bytes())
        for change in ({"platform": "linux/arm64"}, {"image_download_bytes": 61_000_000_000},
                       {"public_weights_verified": 1}, {"model_download_bytes": None}):
            with self.subTest(change=change):
                self.proof_path.write_text(json.dumps({**proof, **change}))
                self.manifest["qualification_sha256"] = hashlib.sha256(self.proof_path.read_bytes()).hexdigest()
                self.save()
                with self.assertRaises(self.w.SafeError):
                    self.w.research_load_manifest(self.path)

    def test_expired_manifest_allows_cleanup_only(self):
        self.manifest.update(created_epoch=int(time.time()) - 3600, deadline_epoch=int(time.time()) - 1)
        self.save()
        with self.assertRaises(self.w.SafeError):
            self.w.research_load_manifest(self.path)
        self.w.research_load_manifest(self.path, require_active=False)

    def test_offer_and_all_in_price_contract(self):
        self.assertTrue(self.w.research_offer_eligible(self.offer))
        self.assertTrue(self.w.research_offer_eligible({**self.offer, "gpu_name": "RTX 6000Ada"}))
        for key, value in (("gpu_name", "RTX 4090"), ("id", True), ("num_gpus", 2), ("gpu_frac", 0),
                           ("gpu_ram", 44999), ("cpu_ram", 63999), ("cpu_cores_effective", 11),
                           ("disk_space", 99), ("dph_total", 0.851), ("inet_down_cost", 0.011), ("rented", True)):
            with self.subTest(key=key):
                self.assertFalse(self.w.research_offer_eligible({**self.offer, key: value}))
        maximum = {**self.manifest, "deadline_epoch": self.manifest["created_epoch"] + 7200}
        self.assertAlmostEqual(self.w.research_budget_cost(maximum, 0.85, 0.01, 0.01), 3.31)
        self.assertTrue(self.g.cost_valid({**self.w.safe_instance(self.raw), "dph_total": 0.85}, maximum))
        with self.assertRaises(self.w.SafeError):
            self.w.research_budget_cost({**maximum, "budget_usd": 2}, 0.85, 0.01, 0.01)

    def test_offer_refresh_has_allocated_disk_and_local_id_filter(self):
        with mock.patch.object(self.w, "vast_request", return_value={"offers": [self.offer, {**self.offer, "id": 456}]} ) as call:
            self.assertEqual(self.w.get_research_offers("synthetic", 123), [self.offer])
        query = call.call_args.kwargs["payload"]
        self.assertNotIn("id", query)
        self.assertEqual(query["allocated_storage"], 100)
        self.assertEqual(query["limit"], 1000)
        self.assertEqual(query["gpu_name"], {"in": ["L40S", "RTX 6000Ada"]})
        self.assertEqual(query["gpu_frac"], {"gt": 0, "lte": 1})

    def test_gpu_fraction_is_host_share_and_must_match_selected_offer(self):
        for fraction in (0.125, 0.25, 0.5, 1):
            offer = {**self.offer, "gpu_frac": fraction}
            raw = {**self.raw, "gpu_frac": fraction}
            with self.subTest(fraction=fraction):
                self.assertTrue(self.w.research_offer_eligible(offer))
                self.w.research_contract(raw, 999, self.manifest, offer)
                self.assertTrue(self.w.research_metadata_pending({**raw, "actual_status": "loading"}, offer))
                changed = {**raw, "gpu_frac": fraction / 2}
                with self.assertRaises(self.w.SafeError):
                    self.w.research_contract(changed, 999, self.manifest, offer)
                self.assertFalse(self.w.research_metadata_pending({**changed, "actual_status": "loading"}, offer))
        for fraction in (0, -0.1, 1.001, None, True, float("nan")):
            with self.subTest(invalid=fraction):
                self.assertFalse(self.w.research_offer_eligible({**self.offer, "gpu_frac": fraction}))
                with self.assertRaises(self.w.SafeError):
                    self.w.research_contract({**self.raw, "gpu_frac": fraction}, 999, self.manifest, self.offer)

    def test_loopback_fixed_revision_and_no_public_port(self):
        command = self.w.research_onstart(self.manifest)
        for expected in ("--host 127.0.0.1", "--max-model-len 16384", "--max-num-seqs 4", "--enforce-eager",
                         "--revision " + self.w.RESEARCH_REVISION, "timeout --signal=TERM", "test \"$(id -u)\" = 0"):
            self.assertIn(expected, command)
        self.assertNotIn("0.0.0.0", command)
        self.w.research_contract(self.raw, 999, self.manifest, self.offer)
        exposed = {**self.raw, "ports": {**self.raw["ports"], "8000/tcp": [{"HostPort": "8765"}]}}
        with self.assertRaises(self.w.SafeError):
            self.w.research_contract(exposed, 999, self.manifest, self.offer)
        self.assertFalse(self.g.cost_valid(self.w.safe_instance(exposed), self.manifest))
        self.assertFalse(self.g.only_cost_metadata_missing({"api_port": 8765}, None))

    def test_server_timeout_uses_local_duration_and_never_provider_wall_clock(self):
        local_now = 2_000_000_000
        for remaining in (1320, 1800, 7200):
            with self.subTest(remaining=remaining), mock.patch.object(self.w.time, "time", return_value=local_now):
                manifest = {**self.manifest, "deadline_epoch": local_now + remaining}
                command = self.w.research_onstart(manifest)
                duration = remaining - 900 - 300 - 60
                self.assertIn(f"--kill-after=30 {duration} python3", command)
                self.assertNotIn("date", command)
                self.assertNotIn(str(manifest["deadline_epoch"]), command)
                # The same relative timer works with the observed +11480s
                # host offset and with an equally delayed provider clock.
                for host_offset in (-11480, 11480):
                    remote_start = local_now + host_offset + 900
                    expires_in_local_time = remote_start + duration + 30 - host_offset
                    self.assertLessEqual(expires_in_local_time, manifest["deadline_epoch"] - 300)

    def test_insufficient_server_ttl_refuses_before_put_and_attempt_consumption(self):
        now = int(time.time())
        self.manifest["deadline_epoch"] = now + 1319
        with ExitStack() as stack:
            self.setup_launch(stack)
            stack.enter_context(mock.patch.object(self.w.time, "time", return_value=now))
            request = stack.enter_context(mock.patch.object(self.w, "vast_request"))
            consume = stack.enter_context(mock.patch.object(self.w, "picogk_consume_attempt"))
            with self.assertRaisesRegex(self.w.SafeError, "sixty-second server run"):
                self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
            request.assert_not_called()
            consume.assert_not_called()

    def setup_launch(self, stack):
        for name, value in (("simready_launch_lock", nullcontext()), ("read_local_ssh_public_key", "synthetic public"),
                            ("ensure_local_ssh_registered", None), ("picogk_singleton", None),
                            ("picogk_account_balance", {"conservative_available_usd": 38.275}),
                            ("get_research_offers", [self.offer]), ("research_verify_guard", None),
                            ("instance_lists_approved_ssh_key", True)):
            stack.enter_context(mock.patch.object(self.w, name, return_value=value))
        stack.enter_context(redirect_stdout(io.StringIO()))
        stack.enter_context(redirect_stderr(io.StringIO()))

    def test_create_once_requires_preconditions_then_instance_key_and_cleanup_on_failure(self):
        with ExitStack() as stack:
            self.setup_launch(stack)
            call = stack.enter_context(mock.patch.object(self.w, "vast_request", side_effect=[{"new_contract": 999}, {"instances": self.raw}]))
            self.assertEqual(self.w.launch_research("synthetic", 123, self.manifest, "a" * 64), 0)
        payload = call.call_args_list[0].kwargs["payload"]
        self.assertEqual(payload["env"], {})
        self.assertEqual(payload["image"], self.w.RESEARCH_IMAGE)
        self.assertEqual(payload["runtype"], "ssh_direct")
        receipt = Path(self.manifest["guard_ready_path"]).parent / (self.manifest["job_id"] + ".paid-attempt.json")
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        with ExitStack() as stack:
            self.setup_launch(stack)
            call = stack.enter_context(mock.patch.object(self.w, "vast_request"))
            with self.assertRaisesRegex(self.w.SafeError, "consumed"):
                self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
            call.assert_not_called()

    def test_no_create_when_pair_account_inventory_or_guard_preflight_fails(self):
        for name in ("read_local_ssh_public_key", "ensure_local_ssh_registered", "picogk_singleton", "research_verify_guard"):
            with self.subTest(name=name), ExitStack() as stack:
                self.setup_launch(stack)
                stack.enter_context(mock.patch.object(self.w, name, side_effect=self.w.SafeError("rejected")))
                call = stack.enter_context(mock.patch.object(self.w, "vast_request"))
                with self.assertRaises(self.w.SafeError):
                    self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
                call.assert_not_called()

    def test_uncertain_create_never_replays_and_routes_to_exact_reconcile(self):
        with ExitStack() as stack:
            self.setup_launch(stack)
            call = stack.enter_context(mock.patch.object(self.w, "vast_request", side_effect=self.w.SafeError("lost PUT acknowledgement")))
            cleanup = stack.enter_context(mock.patch.object(self.w, "research_reconcile", return_value={"verified_absent": True}))
            with self.assertRaises(self.w.SafeError):
                self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
            self.assertEqual(call.call_count, 1)
            cleanup.assert_called_once_with("synthetic", self.manifest, "a" * 64, expected_instance_id=None)

    def test_provider_id_is_durable_before_first_instance_lookup(self):
        receipt_path = self.root / (self.manifest["job_id"] + ".provider-created.json")
        def request(_key, path, **_kwargs):
            if "/asks/" in path:
                self.assertFalse(receipt_path.exists())
                return {"new_contract": 999, "private_provider_field": "NEVER_PRINT"}
            receipt = json.loads(receipt_path.read_bytes())
            self.assertEqual(receipt["instance_id"], 999)
            self.assertEqual(receipt["manifest_sha256"], "a" * 64)
            self.assertTrue(receipt["provider_create_acknowledged"])
            self.assertFalse(receipt["instance_identity_checked"])
            self.assertEqual(receipt_path.stat().st_mode & 0o777, 0o600)
            return {"instances": self.raw}
        with ExitStack() as stack:
            self.setup_launch(stack)
            stack.enter_context(mock.patch.object(self.w, "vast_request", side_effect=request))
            self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
        original = receipt_path.read_bytes()
        with self.assertRaisesRegex(self.w.SafeError, "refusing to overwrite"):
            self.w.research_write_receipt(self.manifest, "provider-created", {"instance_id": 111})
        self.assertEqual(receipt_path.read_bytes(), original)

    def test_contract_failure_diagnostic_precedes_cleanup_and_excludes_private_provider_data(self):
        secret = "PRIVATE_PROVIDER_NEVER_PRINT"
        failed = {**self.raw, "actual_status": "unknown", "cur_state": "running", "intended_status": "running",
                  "dph_total": 0.51, "status_msg": secret, "env": {"HF_TOKEN": secret},
                  "ports": {"22/tcp": [{"HostPort": "1234", "HostIp": secret}], "8000/tcp": [{"HostPort": "4321"}]}}
        output = io.StringIO()
        def cleanup(*_args, **_kwargs):
            self.assertIn("OPENBAO_VASTAI_RESEARCH_CONTRACT", output.getvalue())
            return {"instance_id": 999, "verified_absent": True, "destroyed": True}
        with ExitStack() as stack:
            self.setup_launch(stack)
            stack.enter_context(redirect_stderr(output))
            stack.enter_context(mock.patch.object(self.w, "vast_request", side_effect=[{"new_contract": 999}, {"instances": failed}]))
            stack.enter_context(mock.patch.object(self.w, "research_reconcile", side_effect=cleanup))
            with self.assertRaises(self.w.SafeError):
                self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
        rendered = output.getvalue()
        self.assertNotIn(secret, rendered)
        self.assertNotIn("HostPort", rendered)
        self.assertNotIn("HF_TOKEN", rendered)
        self.assertNotIn("status_msg", rendered)
        diagnostics = [json.loads(line.split(" ", 1)[1]) for line in rendered.splitlines()]
        contract = diagnostics[1]
        self.assertEqual(contract["instance_id"], 999)
        self.assertEqual(contract["expected"]["dph_total"], 0.5)
        self.assertEqual(contract["observed"]["dph_total"], 0.51)
        self.assertEqual(contract["observed"]["status"], "unknown")
        self.assertEqual(contract["observed"]["published_port_names"], ["22/tcp", "8000/tcp"])
        proof = json.loads((self.root / (self.manifest["job_id"] + ".cleanup.json")).read_bytes())
        self.assertEqual(proof["instance_id"], 999)
        self.assertTrue(proof["verified_absent"])
        self.assertTrue(diagnostics[-1]["receipt_persisted"])

    def test_failed_cleanup_receipt_never_claims_billing_stopped(self):
        with ExitStack() as stack:
            self.setup_launch(stack)
            stack.enter_context(mock.patch.object(self.w, "vast_request", side_effect=self.w.SafeError("uncertain PUT")))
            stack.enter_context(mock.patch.object(self.w, "research_reconcile", side_effect=self.w.SafeError("inventory unavailable")))
            with self.assertRaises(self.w.SafeError):
                self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
        proof = json.loads((self.root / (self.manifest["job_id"] + ".cleanup.json")).read_bytes())
        self.assertFalse(proof["verified_absent"])
        self.assertFalse(proof["destroyed"])
        self.assertIsNone(proof["instance_id"])

    def test_reconcile_refuses_unjournaled_and_only_destroys_exact_attempt(self):
        with self.assertRaises(self.w.SafeError):
            self.w.research_reconcile("synthetic", self.manifest, "a" * 64)
        self.w.picogk_consume_attempt(self.manifest, "a" * 64, 123)
        unrelated = {**self.raw, "id": 444, "label": "other-user-work"}
        with mock.patch.object(self.w, "strict_instance_inventory", return_value=[unrelated, self.raw]), \
             mock.patch.object(self.w, "destroy_instance_verified") as destroy:
            proof = self.w.research_reconcile("synthetic", self.manifest, "a" * 64)
        self.assertTrue(proof["verified_absent"])
        destroy.assert_called_once_with("synthetic", 999, expected_label=self.manifest["attempt_label"], expected_image=self.w.RESEARCH_IMAGE)

    def test_uncertain_delete_ack_can_be_proven_by_stable_absence(self):
        self.w.picogk_consume_attempt(self.manifest, "a" * 64, 123)
        with mock.patch.object(self.w, "strict_instance_inventory", side_effect=[[self.raw], [], [], [], [], []]), \
             mock.patch.object(self.w, "destroy_instance_verified", side_effect=self.w.SafeError("ack lost")) as destroy, \
             mock.patch.object(self.w.time, "sleep"):
            proof = self.w.research_reconcile("synthetic", self.manifest, "a" * 64)
        self.assertTrue(proof["verified_absent"])
        destroy.assert_called_once()

    def test_reconcile_never_calls_relabelled_instance_absent_or_accepts_changed_manifest(self):
        self.w.picogk_consume_attempt(self.manifest, "a" * 64, 123)
        with self.assertRaisesRegex(self.w.SafeError, "exact consumed"):
            self.w.research_reconcile("synthetic", self.manifest, "c" * 64)
        changed = {**self.raw, "label": "other-work"}
        with mock.patch.object(self.w, "strict_instance_inventory", return_value=[changed]), \
             mock.patch.object(self.w, "destroy_instance_verified") as destroy:
            with self.assertRaisesRegex(self.w.SafeError, "label changed"):
                self.w.research_reconcile("synthetic", self.manifest, "a" * 64, expected_instance_id=999)
            destroy.assert_not_called()

    def test_guard_reuses_resilient_cleanup_and_rejects_identity_changes(self):
        engine = self.g.engine
        safe = self.w.safe_instance(self.raw)
        with mock.patch.object(engine, "wrapper_call", side_effect=[engine.GuardError("transient"), [safe], [], [], [], [], []]), \
             mock.patch.object(engine, "destroy_exact", side_effect=engine.GuardError("lost ack")), \
             mock.patch.object(engine.time, "sleep"), redirect_stdout(io.StringIO()):
            self.assertTrue(engine.cleanup_until_absent(999, self.manifest)["verified_absent"])
        with self.assertRaises(engine.GuardError):
            engine.exact_match([{**safe, "image": "unrelated"}], self.manifest, 999)

    def test_guard_signal_requests_cleanup_without_ending_monitor(self):
        self.assertTrue(self.g.cost_valid(self.w.safe_instance(self.raw), self.manifest))
        self.g.request_cleanup(None, None)
        self.assertFalse(self.g.cost_valid(self.w.safe_instance(self.raw), self.manifest))
        self.assertFalse(self.g.only_cost_metadata_missing({}, None))

    def test_late_put_after_twenty_minutes_is_still_destroyed(self):
        self.manifest["deadline_epoch"] = self.manifest["created_epoch"] + 7200
        self.save()
        safe = self.w.safe_instance(self.raw)
        with mock.patch.object(self.g, "initial_guard", return_value={"reason": "no_instance_observed"}), \
             mock.patch.object(self.g.engine, "wrapper_call", side_effect=[[], [], [safe]]), \
             mock.patch.object(self.g.time, "monotonic", side_effect=[0, 1300, 1300, 1500, 1500]), \
             mock.patch.object(self.g.time, "sleep"), \
             mock.patch.object(self.g.engine, "cleanup_until_absent", return_value={"verified_absent": True}) as destroy:
            proof = self.g.guard(self.path)
        self.assertEqual(proof["reason"], "late_creation_cleanup")
        destroy.assert_called_once_with(999, self.manifest)

    def test_unknown_put_absence_only_finishes_after_deadline_and_five_reads(self):
        responses = [[], self.g.engine.GuardError("transient"), [], [], [], [], []]
        with mock.patch.object(self.g, "initial_guard", return_value={"reason": "no_instance_observed"}), \
             mock.patch.object(self.g.engine, "wrapper_call", side_effect=responses) as call, \
             mock.patch.object(self.g.time, "monotonic", side_effect=[0, 8000, 8000, 8000, 8000, 8000, 8000]), \
             mock.patch.object(self.g.time, "sleep"):
            proof = self.g.guard(self.path)
        self.assertEqual(proof["reason"], "no_creation_by_deadline")
        self.assertTrue(proof["verified_absent"])
        self.assertEqual(call.call_count, 7)

    def test_known_startup_contract_violation_is_not_missing_metadata(self):
        pending = {**self.raw, "actual_status": "loading", "gpu_frac": None, "ports": None}
        self.assertTrue(self.w.research_metadata_pending(pending, self.offer))
        for change in ({"gpu_frac": 0.5}, {"gpu_name": "RTX 4090"}, {"cpu_ram": 1000},
                       {"dph_total": 0.86}, {"inet_down_cost": 0.02}, {"ports": {"8000/tcp": [{"HostPort": "1234"}]}}):
            with self.subTest(change=change):
                self.assertFalse(self.w.research_metadata_pending({**pending, **change}, self.offer))

    def test_observed_running_without_actual_status_waits_for_missing_ports(self):
        offer = {**self.offer, "gpu_frac": 0.25}
        snapshot = {**self.raw, "gpu_frac": 0.25, "actual_status": None, "cur_state": "running",
                    "intended_status": "running", "next_state": "running", "ports": None, "cpu_ram": 515565}
        self.assertTrue(self.w.research_metadata_pending(snapshot, offer))
        with self.assertRaises(self.w.SafeError):
            self.w.research_contract(snapshot, 999, self.manifest, offer)
        for change in ({"gpu_frac": 0.5}, {"dph_total": 0.51}, {"gpu_ram": 40000},
                       {"actual_status": "exited"}, {"actual_status": "unknown"},
                       {"ports": {"8000/tcp": [{"HostPort": "1234"}]}}):
            with self.subTest(change=change):
                self.assertFalse(self.w.research_metadata_pending({**snapshot, **change}, offer))

    def test_running_missing_ports_wait_is_bounded_and_never_checks_key_or_returns_ready(self):
        current = [time.time()]
        initial = current[0]
        snapshot = {**self.raw, "actual_status": None, "cur_state": "running",
                    "intended_status": "running", "next_state": "running", "ports": None}
        def request(_key, path, **_kwargs):
            return {"new_contract": 999} if "/asks/" in path else {"instances": snapshot}
        with ExitStack() as stack:
            self.setup_launch(stack)
            stack.enter_context(mock.patch.object(self.w, "vast_request", side_effect=request))
            stack.enter_context(mock.patch.object(self.w.time, "time", side_effect=lambda: current[0]))
            sleep = stack.enter_context(mock.patch.object(self.w.time, "sleep", side_effect=lambda seconds: current.__setitem__(0, current[0] + seconds)))
            key = stack.enter_context(mock.patch.object(self.w, "instance_lists_approved_ssh_key"))
            cleanup = stack.enter_context(mock.patch.object(self.w, "research_reconcile", return_value={"instance_id": 999, "verified_absent": True, "destroyed": True}))
            with self.assertRaises(self.w.SafeError):
                self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
            self.assertEqual(current[0] - initial, 900)
            self.assertEqual(sleep.call_count, 180)
            key.assert_not_called()
            cleanup.assert_called_once()

    def test_image_loading_wait_cannot_consume_global_cleanup_reserve(self):
        current = [int(time.time())]
        initial = current[0]
        self.manifest["deadline_epoch"] = initial + 1500
        snapshot = {**self.raw, "actual_status": "loading", "ports": None}
        def request(_key, path, **_kwargs):
            if "/asks/" in path:
                current[0] += 600  # Delayed provider response cannot reset the global deadline.
                return {"new_contract": 999}
            return {"instances": snapshot}
        with ExitStack() as stack:
            self.setup_launch(stack)
            stack.enter_context(mock.patch.object(self.w, "vast_request", side_effect=request))
            stack.enter_context(mock.patch.object(self.w.time, "time", side_effect=lambda: current[0]))
            sleep = stack.enter_context(mock.patch.object(self.w.time, "sleep", side_effect=lambda seconds: current.__setitem__(0, current[0] + seconds)))
            cleanup = stack.enter_context(mock.patch.object(self.w, "research_reconcile", return_value={"instance_id": 999, "verified_absent": True, "destroyed": True}))
            with self.assertRaises(self.w.SafeError):
                self.w.launch_research("synthetic", 123, self.manifest, "a" * 64)
            self.assertEqual(current[0], self.manifest["deadline_epoch"] - 300)
            self.assertEqual(sleep.call_count, 120)
            cleanup.assert_called_once()

    def test_live_guard_pid_must_match_helper_and_manifest_not_unrelated_process(self):
        manifest = {**self.manifest, "_manifest_path": str(self.path)}
        Path(manifest["guard_ready_path"]).write_text(json.dumps({"pid": 123}))
        for command, succeeds in (("python3 " + manifest["guard_path"] + " " + str(self.path), True),
                                  ("python3 /unrelated/guard.py " + str(self.path), False)):
            with self.subTest(command=command), \
                 mock.patch.object(self.w, "picogk_verify_armed_guard"), \
                 mock.patch.object(self.w.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=command)):
                if succeeds:
                    self.w.research_verify_guard(manifest, "a" * 64)
                else:
                    with self.assertRaises(self.w.SafeError):
                        self.w.research_verify_guard(manifest, "a" * 64)

    def test_existing_profile_caps_are_unchanged(self):
        self.assertEqual(self.w.PICOGK_MAX_DPH, 0.80)
        self.assertEqual(self.w.PICOGK_MIN_CPU, 32)
        old = load("deploy/vast/picogk/deadline_guard.py", "unchanged_guard_test")
        self.assertIsNot(old.cost_valid, self.g.cost_valid)


if __name__ == "__main__":
    unittest.main()
