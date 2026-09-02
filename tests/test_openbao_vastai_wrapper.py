"""Tests hors ligne du wrapper Vast.ai borné au projet."""

from __future__ import annotations

from contextlib import nullcontext
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = ROOT / "deploy/openbao/openbao-vastai"
# Offre communiquee par l'utilisateur le 2026-09-02. Cette fixture ne prouve
# ni sa disponibilite actuelle, ni une location.
USER_PROVIDED_WAVE_CANDIDATE_ID = 49655039
USER_PROVIDED_COMPONENT_FACTORY_F41_CANDIDATE_ID = 49655039


def load_wrapper():
    loader = SourceFileLoader("openbao_vastai", str(WRAPPER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class OpenBaoVastAiWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper = load_wrapper()

    def setUp(self):
        # Most unit tests exercise the launch state machine as if a corrected
        # digest had already passed the live Vast qualification. Production
        # keeps the known-bad digest denylisted; that gate has its own test.
        patcher = mock.patch.object(
            self.wrapper, "COMPONENT_FACTORY_F41_REVOKED_IMAGES", frozenset()
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def eligible_offer(self, **overrides):
        offer = {
            "id": 7,
            "gpu_name": "RTX PRO 6000 WS",
            "gpu_ram": 98304,
            "gpu_frac": 1,
            "num_gpus": 1,
            "cpu_cores_effective": 24,
            "cpu_ram": 128000,
            "disk_space": 500,
            "dph_total": 2.0,
            "reliability": 0.999,
            "verified": True,
            "rentable": True,
            "rented": False,
        }
        offer.update(overrides)
        return offer

    def eligible_wave_offer(self, **overrides):
        offer = {
            "id": USER_PROVIDED_WAVE_CANDIDATE_ID,
            "gpu_name": "RTX 4090",
            "cpu_cores_effective": 384,
            "cpu_ram": 774000,
            "disk_space": 6600,
            "dph_total": 1.112,
            "inet_up_cost": 0.01,
            "inet_down_cost": 0.01,
            "reliability": 0.988,
            "verified": True,
            "rentable": True,
            "rented": False,
            "geolocation": "Vietnam, VN",
        }
        offer.update(overrides)
        return offer

    def wave_instance(self, **overrides):
        instance = {
            "id": 12345,
            "label": self.wrapper.WAVE_LABEL,
            "actual_status": "running",
            "verification": "verified",
            "cpu_cores_effective": 64,
            "cpu_ram": 256000,
            "disk_space": 300,
            "dph_total": 1.25,
            "image_uuid": self.wrapper.WAVE_IMAGE,
        }
        instance.update(overrides)
        return instance

    def eligible_component_factory_f41_offer(self, **overrides):
        offer = {
            "id": USER_PROVIDED_COMPONENT_FACTORY_F41_CANDIDATE_ID,
            "gpu_name": "RTX 3060 Ti",
            "cpu_cores_effective": 384,
            "cpu_ram": 774000,
            "disk_space": 6600,
            "dph_total": 1.112,
            "inet_up_cost": 0.01,
            "inet_down_cost": 0.01,
            "reliability": 0.988,
            "verified": True,
            "rentable": True,
            "rented": False,
            "geolocation": "Vietnam, VN",
        }
        offer.update(overrides)
        return offer

    def component_factory_f41_instance(self, **overrides):
        instance = {
            "id": 41341,
            "label": self.component_factory_f41_attempt_label(),
            "actual_status": "running",
            "verification": "verified",
            "cpu_cores_effective": 64,
            "cpu_ram": 256000,
            "disk_space": 300,
            "dph_total": 1.25,
            "inet_up_cost": 0.01,
            "inet_down_cost": 0.01,
            "image_uuid": self.wrapper.COMPONENT_FACTORY_F41_IMAGE,
        }
        instance.update(overrides)
        return instance

    def component_factory_f41_attempt_label(self, token: str = "a" * 20):
        return f"{self.wrapper.COMPONENT_FACTORY_F41_LABEL}-{token}"

    def test_heavy_contract_is_exact_and_prices_500_gb(self):
        query = self.wrapper.heavy_offer_query()
        self.assertEqual(self.wrapper.HEAVY_GPU_NAME, "RTX PRO 6000 WS")
        self.assertEqual(query["allocated_storage"], 500)
        self.assertEqual(query["gpu_frac"], {"eq": 1})
        self.assertTrue(self.wrapper.heavy_offer_eligible(self.eligible_offer()))
        self.assertFalse(
            self.wrapper.heavy_offer_eligible(
                self.eligible_offer(gpu_name="RTX PRO 6000 S")
            )
        )
        self.assertFalse(
            self.wrapper.heavy_offer_eligible(self.eligible_offer(gpu_frac=0.5))
        )

    def test_wave_contract_is_cpu_only_bounded_and_prices_300_gb(self):
        query = self.wrapper.wave_offer_query()
        self.assertEqual(query["allocated_storage"], 300)
        self.assertEqual(query["cpu_cores_effective"], {"gte": 64})
        self.assertEqual(query["cpu_ram"], {"gte": 256000})
        self.assertEqual(query["disk_space"], {"gte": 300})
        self.assertEqual(query["verified"], {"eq": True})
        self.assertNotIn("gpu_name", query)
        self.assertNotIn("gpu_ram", query)
        self.assertEqual(
            self.wrapper.WAVE_IMAGE,
            "ghcr.io/cluster2600/3dprinting993-wave-action-f39@sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3",
        )
        self.assertEqual(self.wrapper.WAVE_MAX_DPH, 1.25)
        self.assertEqual(self.wrapper.WAVE_MIN_RELIABILITY, 0.985)
        self.assertTrue(self.wrapper.wave_offer_eligible(self.eligible_wave_offer()))

    def test_wave_contract_fails_closed_on_each_paid_resource_gate(self):
        rejected = (
            {"dph_total": 1.250001},
            {"dph_total": None, "dph": 0.1},
            {"cpu_cores_effective": 63.999},
            {"cpu_ram": 255999},
            {"disk_space": 299.999},
            {"reliability": 0.984999},
            {"verified": False},
            {"rentable": False},
            {"rented": True},
            {"rented": None},
            {"id": "49655039"},
        )
        for override in rejected:
            with self.subTest(override=override):
                self.assertFalse(
                    self.wrapper.wave_offer_eligible(
                        self.eligible_wave_offer(**override)
                    )
                )

    def test_wave_launch_uses_exact_image_ssh_smoke_and_no_credentials(self):
        output = io.StringIO()
        offer = self.eligible_wave_offer()
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(self.wrapper, "require_no_wave_instance") as singleton,
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered") as ensure_ssh,
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 12345},
            ) as request,
            mock.patch.object(
                self.wrapper, "verify_single_wave_instance"
            ) as verify_singleton,
            mock.patch.object(
                self.wrapper, "verify_wave_contract"
            ) as verify_contract,
            mock.patch.object(
                self.wrapper, "verify_wave_ssh_ready"
            ) as verify_runtime,
            mock.patch("sys.stdout", output),
        ):
            result = self.wrapper.launch_wave_f39_offer("unused", offer)
        self.assertEqual(result, 0)
        singleton.assert_called_once_with("unused")
        ensure_ssh.assert_called_once_with("unused")
        verify_singleton.assert_called_once_with("unused", 12345)
        verify_contract.assert_called_once_with("unused", 12345)
        verify_runtime.assert_called_once_with("unused", 12345)
        self.assertEqual(
            request.call_args.args[1],
            f"/api/v0/asks/{USER_PROVIDED_WAVE_CANDIDATE_ID}/",
        )
        self.assertEqual(request.call_args.kwargs["method"], "PUT")
        payload = request.call_args.kwargs["payload"]
        self.assertEqual(payload["image"], self.wrapper.WAVE_IMAGE)
        self.assertEqual(payload["label"], "3dprinting993-wave-action-f39")
        self.assertEqual(payload["disk"], 300)
        self.assertEqual(payload["runtype"], "ssh_direct")
        self.assertEqual(payload["env"], {})
        self.assertIn("/opt/917-engine-wave-f39/smoke.py", payload["onstart"])
        self.assertIn("/workspace/READY", payload["onstart"])
        self.assertTrue(payload["onstart"].startswith("rm -f /workspace/READY;"))
        self.assertLess(
            payload["onstart"].index("/opt/917-engine-wave-f39/smoke.py"),
            payload["onstart"].rindex("/workspace/READY"),
        )
        serialized = json.dumps(payload).lower()
        self.assertNotIn("token", serialized)
        self.assertNotIn("api_key", serialized)
        report = json.loads(output.getvalue())
        self.assertTrue(report["offer_contract_verified"])
        self.assertTrue(report["singleton_preflight_verified"])
        self.assertTrue(report["singleton_verified"])
        self.assertTrue(report["contract_verified"])
        self.assertTrue(report["running_state_verified"])
        self.assertTrue(report["ssh_batch_mode_verified"])
        self.assertTrue(report["runtime_smoke_verified"])

    def test_wave_launch_revalidates_before_ssh_or_paid_request(self):
        with (
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered") as ensure_ssh,
            mock.patch.object(self.wrapper, "vast_request") as request,
            self.assertRaisesRegex(self.wrapper.SafeError, "fixed safety and price limits"),
        ):
            self.wrapper.launch_wave_f39_offer(
                "unused", self.eligible_wave_offer(cpu_ram=255999)
            )
        ensure_ssh.assert_not_called()
        request.assert_not_called()

    def test_wave_launch_refuses_a_second_project_instance(self):
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[{"id": 12345, "label": self.wrapper.WAVE_LABEL}],
            ),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered") as ensure_ssh,
            mock.patch.object(self.wrapper, "vast_request") as request,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "wave-action F39 instance already exists"
            ),
        ):
            self.wrapper.launch_wave_f39_offer("unused", self.eligible_wave_offer())
        ensure_ssh.assert_not_called()
        request.assert_not_called()

    def test_wave_post_launch_singleton_requires_only_the_created_id(self):
        with mock.patch.object(
            self.wrapper,
            "list_instances",
            return_value=[{"id": 12345, "label": self.wrapper.WAVE_LABEL}],
        ):
            self.wrapper.verify_single_wave_instance("unused", 12345)

        with (
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[
                    {"id": 12345, "label": self.wrapper.WAVE_LABEL},
                    {"id": 12346, "label": self.wrapper.WAVE_LABEL},
                ],
            ),
            self.assertRaisesRegex(
                self.wrapper.SafeError, "post-launch uniqueness verification failed"
            ),
        ):
            self.wrapper.verify_single_wave_instance("unused", 12345)

    def test_wave_post_launch_contract_is_read_back_and_fail_closed(self):
        with mock.patch.object(
            self.wrapper,
            "vast_request",
            return_value={"instances": self.wave_instance()},
        ):
            self.wrapper.verify_wave_contract("unused", 12345)

        rejected = (
            ({"image_uuid": "ghcr.io/example/wrong@sha256:deadbeef"}, "image digest"),
            ({"actual_status": "exited"}, "status"),
            ({"cpu_cores_effective": 63.999}, "effective CPU threads"),
            ({"cpu_ram": 255999}, "CPU RAM"),
            ({"disk_space": 299.999}, "disk"),
            ({"dph_total": 1.250001}, "dph_total"),
            ({"verification": "unverified"}, "machine verification"),
        )
        for override, message in rejected:
            with (
                self.subTest(override=override),
                mock.patch.object(
                    self.wrapper,
                    "vast_request",
                    return_value={"instances": self.wave_instance(**override)},
                ),
                self.assertRaisesRegex(self.wrapper.SafeError, message),
            ):
                self.wrapper.verify_wave_contract("unused", 12345)

    def test_wave_contract_waits_for_running_before_returning(self):
        with (
            mock.patch.object(
                self.wrapper,
                "vast_request",
                side_effect=[
                    {"instances": self.wave_instance(actual_status="loading")},
                    {"instances": self.wave_instance(actual_status="running")},
                ],
            ) as request,
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
        ):
            instance = self.wrapper.verify_wave_contract("unused", 12345)
        self.assertEqual(instance["status"], "running")
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(self.wrapper.POLL_INTERVAL_SECONDS)

    def test_wave_post_create_contract_failure_rolls_back_exact_instance(self):
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(self.wrapper, "require_no_wave_instance"),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 12345},
            ),
            mock.patch.object(self.wrapper, "verify_single_wave_instance"),
            mock.patch.object(
                self.wrapper,
                "verify_wave_contract",
                side_effect=self.wrapper.SafeError("bad F39 contract"),
            ),
            mock.patch.object(self.wrapper, "destroy_instance_verified") as destroy,
            self.assertRaisesRegex(self.wrapper.SafeError, "bad F39 contract"),
        ):
            self.wrapper.launch_wave_f39_offer(
                "unused", self.eligible_wave_offer()
            )
        destroy.assert_called_once_with("unused", 12345)

    def test_wave_post_create_ssh_smoke_failure_rolls_back_exact_instance(self):
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(self.wrapper, "require_no_wave_instance"),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 12345},
            ),
            mock.patch.object(self.wrapper, "verify_single_wave_instance"),
            mock.patch.object(self.wrapper, "verify_wave_contract"),
            mock.patch.object(
                self.wrapper,
                "verify_wave_ssh_ready",
                side_effect=self.wrapper.SafeError("F39 smoke failed"),
            ),
            mock.patch.object(self.wrapper, "destroy_instance_verified") as destroy,
            self.assertRaisesRegex(self.wrapper.SafeError, "F39 smoke failed"),
        ):
            self.wrapper.launch_wave_f39_offer(
                "unused", self.eligible_wave_offer()
            )
        destroy.assert_called_once_with("unused", 12345)

    def test_wave_post_create_duplicate_rolls_back_the_created_instance(self):
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper,
                "list_instances",
                side_effect=[
                    [],
                    [
                        {"id": 12345, "label": self.wrapper.WAVE_LABEL},
                        {"id": 12346, "label": self.wrapper.WAVE_LABEL},
                    ],
                ],
            ),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 12345},
            ),
            mock.patch.object(self.wrapper, "verify_wave_contract") as contract,
            mock.patch.object(self.wrapper, "destroy_instance_verified") as destroy,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "post-launch uniqueness verification failed"
            ),
        ):
            self.wrapper.launch_wave_f39_offer(
                "unused", self.eligible_wave_offer()
            )
        contract.assert_not_called()
        destroy.assert_called_once_with("unused", 12345)

    def test_wave_uncertain_create_reconciles_but_definite_4xx_does_not(self):
        uncertain_errors = (
            self.wrapper.SafeHttpError("Vast.ai", 503),
            self.wrapper.SafeError("Vast.ai is unavailable"),
        )
        for error in uncertain_errors:
            with (
                self.subTest(error=type(error).__name__),
                mock.patch.object(
                    self.wrapper, "simready_launch_lock", return_value=nullcontext()
                ),
                mock.patch.object(self.wrapper, "require_no_wave_instance"),
                mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
                mock.patch.object(
                    self.wrapper, "vast_request", side_effect=error
                ) as request,
                mock.patch.object(
                    self.wrapper, "reconcile_uncertain_wave_launch"
                ) as reconcile,
                self.assertRaises(type(error)),
            ):
                self.wrapper.launch_wave_f39_offer(
                    "unused", self.eligible_wave_offer()
                )
            request.assert_called_once()
            reconcile.assert_called_once_with("unused")

        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(self.wrapper, "require_no_wave_instance"),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                side_effect=self.wrapper.SafeHttpError("Vast.ai", 409),
            ) as request,
            mock.patch.object(
                self.wrapper, "reconcile_uncertain_wave_launch"
            ) as reconcile,
            self.assertRaises(self.wrapper.SafeHttpError),
        ):
            self.wrapper.launch_wave_f39_offer(
                "unused", self.eligible_wave_offer()
            )
        request.assert_called_once()
        reconcile.assert_not_called()

    def test_uncertain_wave_launch_rolls_back_only_the_sole_label_instance(self):
        with (
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[{"id": 12345, "label": self.wrapper.WAVE_LABEL}],
            ),
            mock.patch.object(self.wrapper, "destroy_instance_verified") as destroy,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "automatically destroyed and verified absent"
            ),
        ):
            self.wrapper.reconcile_uncertain_wave_launch("unused")
        destroy.assert_called_once_with("unused", 12345)

        with (
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[
                    {"id": 12345, "label": self.wrapper.WAVE_LABEL},
                    {"id": 12346, "label": self.wrapper.WAVE_LABEL},
                ],
            ),
            mock.patch.object(self.wrapper, "destroy_instance_verified") as destroy,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "not uniquely mapped"
            ),
        ):
            self.wrapper.reconcile_uncertain_wave_launch("unused")
        destroy.assert_not_called()

    def test_uncertain_wave_reconciliation_expiry_explicitly_forbids_retry(self):
        with (
            mock.patch.object(self.wrapper, "list_instances", return_value=[]),
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
            self.assertRaisesRegex(
                self.wrapper.SafeError,
                "do not retry automatically",
            ),
        ):
            self.wrapper.reconcile_uncertain_wave_launch("unused")
        self.assertEqual(sleep.call_count, 30)

    def test_wave_ssh_ready_uses_approved_key_batch_mode_and_smoke_marker(self):
        completed = self.wrapper.subprocess.CompletedProcess(
            args=[], returncode=0, stdout="F39_REMOTE_READY\n", stderr=""
        )
        with (
            mock.patch.object(
                self.wrapper, "validate_approved_ssh_private_key"
            ) as validate_key,
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={
                    "instances": self.wave_instance(
                        ssh_host="203.0.113.8",
                        ssh_port=32122,
                    )
                },
            ),
            mock.patch.object(
                self.wrapper.subprocess, "run", return_value=completed
            ) as run,
        ):
            self.wrapper.verify_wave_ssh_ready("unused", 12345)
        validate_key.assert_called_once_with()
        command = run.call_args.args[0]
        self.assertIn(str(self.wrapper.SSH_PRIVATE_KEY_FILE), command)
        self.assertIn("BatchMode=yes", command)
        self.assertIn("IdentitiesOnly=yes", command)
        self.assertIn("root@203.0.113.8", command)
        self.assertIn("32122", command)
        self.assertNotIn("ssh-add", command)
        self.assertIn("/workspace/READY", command[-1])
        self.assertIn("wave-action-f39-smoke.json", command[-1])

    def test_wave_ssh_ready_never_accepts_failed_smoke(self):
        failed = self.wrapper.subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="not ready"
        )
        with (
            mock.patch.object(
                self.wrapper, "validate_approved_ssh_private_key"
            ),
            mock.patch.object(self.wrapper, "WAVE_SSH_READY_ATTEMPTS", 2),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={
                    "instances": self.wave_instance(
                        ssh_host="203.0.113.8",
                        ssh_port=32122,
                    )
                },
            ),
            mock.patch.object(
                self.wrapper.subprocess, "run", return_value=failed
            ) as run,
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "do not treat the instance as ready"
            ),
        ):
            self.wrapper.verify_wave_ssh_ready("unused", 12345)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(sleep.call_count, 2)

    def test_ssh_registration_reads_public_key_without_ssh_agent(self):
        with (
            mock.patch.object(
                self.wrapper,
                "read_local_ssh_public_key",
                return_value="ssh-ed25519 public-material",
            ) as read_key,
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"success": True},
            ) as request,
            mock.patch.object(self.wrapper.subprocess, "run") as run,
        ):
            self.wrapper.ensure_local_ssh_registered("unused")
        read_key.assert_called_once_with()
        run.assert_not_called()
        self.assertEqual(
            request.call_args.kwargs["payload"],
            {"ssh_key": "ssh-ed25519 public-material"},
        )

    def test_stop_requires_acknowledgement_and_final_stopped_state(self):
        with (
            mock.patch.object(
                self.wrapper,
                "vast_request",
                side_effect=[
                    {"success": True},
                    {"instances": self.wave_instance(actual_status="stopping")},
                    {"instances": self.wave_instance(actual_status="stopped")},
                ],
            ) as request,
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
        ):
            self.wrapper.set_instance_state_verified("unused", 12345, "stopped")
        self.assertEqual(request.call_count, 3)
        self.assertEqual(
            request.call_args_list[0].kwargs["payload"], {"state": "stopped"}
        )
        sleep.assert_called_once_with(self.wrapper.POLL_INTERVAL_SECONDS)

        with (
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"success": False},
            ),
            self.assertRaisesRegex(
                self.wrapper.SafeError, "did not confirm the stopped request"
            ),
        ):
            self.wrapper.set_instance_state_verified("unused", 12345, "stopped")

    def test_wave_offers_is_read_only_and_no_best_launch_route_exists(self):
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("launch-wave-best", source)
        output = io.StringIO()
        with (
            mock.patch.object(self.wrapper, "login", return_value="session"),
            mock.patch.object(self.wrapper, "read_vast_key", return_value="unused"),
            mock.patch.object(self.wrapper, "revoke_token"),
            mock.patch.object(
                self.wrapper, "get_wave_offers", return_value=[]
            ) as offers,
            mock.patch.object(self.wrapper, "launch_wave_f39_offer") as launch,
            mock.patch("sys.stdout", output),
        ):
            result = self.wrapper.run(["wave-offers"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), [])
        offers.assert_called_once_with("unused")
        launch.assert_not_called()

    def test_wave_command_matches_the_user_selected_id_locally(self):
        selected = self.eligible_wave_offer()
        with (
            mock.patch.object(self.wrapper, "login", return_value="session"),
            mock.patch.object(self.wrapper, "read_vast_key", return_value="unused"),
            mock.patch.object(self.wrapper, "revoke_token") as revoke,
            mock.patch.object(
                self.wrapper, "get_wave_offers", return_value=[selected]
            ) as offers,
            mock.patch.object(
                self.wrapper, "launch_wave_f39_offer", return_value=0
            ) as launch,
        ):
            result = self.wrapper.run(
                ["launch-wave-f39", str(USER_PROVIDED_WAVE_CANDIDATE_ID)]
            )
        self.assertEqual(result, 0)
        offers.assert_called_once_with("unused", USER_PROVIDED_WAVE_CANDIDATE_ID)
        launch.assert_called_once_with("unused", selected)
        revoke.assert_called_once_with("session")

    def test_instance_listing_reads_every_page(self):
        pages = [
            {
                "success": True,
                "instances": [{"id": 1, "label": self.wrapper.SIMREADY_LABEL}],
                "next_token": "next",
            },
            {
                "success": True,
                "instances": [{"id": 2, "label": self.wrapper.SIMREADY_LABEL}],
                "next_token": None,
            },
        ]
        with mock.patch.object(self.wrapper, "vast_request", side_effect=pages) as request:
            instances = self.wrapper.list_instances(
                "unused", label=self.wrapper.SIMREADY_LABEL
            )
        self.assertEqual([item["id"] for item in instances], [1, 2])
        self.assertIn("after_token=next", request.call_args_list[1].args[1])

    def test_destroy_is_proven_by_complete_paginated_absence(self):
        responses = [
            {"success": True},
            {"success": True, "instances": [], "next_token": None},
        ]
        with mock.patch.object(self.wrapper, "vast_request", side_effect=responses):
            self.wrapper.destroy_instance_verified("unused", 9)

    def test_heavy_launch_enforces_singleton_and_contract(self):
        output = io.StringIO()
        with (
            mock.patch.object(self.wrapper, "simready_launch_lock", return_value=nullcontext()),
            mock.patch.object(self.wrapper, "require_no_simready_instance") as no_existing,
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 12345},
            ),
            mock.patch.object(self.wrapper, "verify_single_simready_instance") as singleton,
            mock.patch.object(self.wrapper, "verify_simready_contract") as contract,
            mock.patch("sys.stdout", output),
        ):
            result = self.wrapper.launch_simready_offer(
                "unused", self.eligible_offer(), disk_gb=500, enforce_singleton=True
            )
        self.assertEqual(result, 0)
        no_existing.assert_called_once_with("unused")
        singleton.assert_called_once_with("unused", 12345)
        contract.assert_called_once_with("unused", 12345)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["singleton_verified"])
        self.assertTrue(payload["contract_verified"])

    def test_uncertain_launch_rolls_back_the_only_project_instance(self):
        with (
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[{"id": 12345, "label": self.wrapper.SIMREADY_LABEL}],
            ),
            mock.patch.object(self.wrapper, "destroy_instance_verified") as destroy,
        ):
            with self.assertRaisesRegex(
                self.wrapper.SafeError, "automatically destroyed and verified absent"
            ):
                self.wrapper.reconcile_uncertain_simready_launch("unused")
        destroy.assert_called_once_with("unused", 12345)

    def test_component_factory_f41_contract_is_cpu_only_and_digest_pinned(self):
        query = self.wrapper.component_factory_f41_offer_query()
        self.assertEqual(query["allocated_storage"], 300)
        self.assertEqual(query["cpu_cores_effective"], {"gte": 64})
        self.assertEqual(query["cpu_ram"], {"gte": 256000})
        self.assertEqual(query["disk_space"], {"gte": 300})
        self.assertEqual(query["inet_up_cost"], {"lte": 0.05})
        self.assertEqual(query["inet_down_cost"], {"lte": 0.05})
        self.assertEqual(query["reliability"], {"gte": 0.985})
        self.assertEqual(query["verified"], {"eq": True})
        self.assertEqual(query["rentable"], {"eq": True})
        self.assertEqual(query["rented"], {"eq": False})
        self.assertNotIn("gpu_name", query)
        self.assertNotIn("gpu_ram", query)
        self.assertNotIn("num_gpus", query)
        self.assertEqual(
            self.wrapper.COMPONENT_FACTORY_F41_IMAGE,
            "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
            "66cef346acfd8b3d84e87fa5c53d112ade07d4e183a3e1c00165d6a1c922f70a",
        )
        self.assertNotEqual(
            self.wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGE_DD0,
            self.wrapper.COMPONENT_FACTORY_F41_IMAGE,
        )
        self.assertRegex(
            self.wrapper.COMPONENT_FACTORY_F41_IMAGE,
            r"^ghcr\.io/cluster2600/3dprinting993-cad-author-f28@sha256:[0-9a-f]{64}$",
        )
        self.assertTrue(
            self.wrapper.component_factory_f41_offer_eligible(
                self.eligible_component_factory_f41_offer(
                    cpu_cores_effective=64,
                    cpu_ram=256000,
                    disk_space=300,
                    dph_total=1.25,
                    reliability=0.985,
                )
            )
        )

    def test_component_factory_f41_revoked_digests_block_before_paid_side_effects(self):
        production_wrapper = load_wrapper()
        self.assertIn(
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGE_DD0,
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGES,
        )
        self.assertIn(
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGE_66C,
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGES,
        )
        self.assertEqual(
            production_wrapper.COMPONENT_FACTORY_F41_IMAGE,
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGE_66C,
        )
        for revoked_image in production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGES:
            with (
                self.subTest(revoked_image=revoked_image),
                mock.patch.object(
                    production_wrapper,
                    "COMPONENT_FACTORY_F41_IMAGE",
                    revoked_image,
                ),
                mock.patch.object(production_wrapper, "simready_launch_lock") as launch_lock,
                mock.patch.object(production_wrapper, "vast_request") as request,
                self.assertRaisesRegex(
                    production_wrapper.SafeError,
                    "runtime image is revoked",
                ),
            ):
                production_wrapper.launch_component_factory_f41_offer(
                    "unused", self.eligible_component_factory_f41_offer()
                )
            launch_lock.assert_not_called()
            request.assert_not_called()

    def test_component_factory_f41_offer_fails_closed_on_every_paid_gate(self):
        rejected = (
            {"dph_total": 1.250001},
            {"dph_total": -0.001},
            {"dph_total": None, "dph": 0.1},
            {"dph_total": float("nan")},
            {"cpu_cores_effective": 63.999},
            {"cpu_ram": 255999},
            {"disk_space": 299.999},
            {"inet_up_cost": None},
            {"inet_up_cost": -0.001},
            {"inet_up_cost": 0.050001},
            {"inet_up_cost": float("nan")},
            {"inet_down_cost": None},
            {"inet_down_cost": -0.001},
            {"inet_down_cost": 0.050001},
            {"inet_down_cost": float("inf")},
            {"reliability": 0.984999},
            {"verified": False},
            {"rentable": False},
            {"rented": True},
            {"rented": None},
            {"id": "49655039"},
            {"id": True},
        )
        for override in rejected:
            with self.subTest(override=override):
                self.assertFalse(
                    self.wrapper.component_factory_f41_offer_eligible(
                        self.eligible_component_factory_f41_offer(**override)
                    )
                )

    def test_component_factory_f41_offer_search_is_bounded_and_sorted(self):
        offers = [
            self.eligible_component_factory_f41_offer(id=3, cpu_cores_effective=64),
            self.eligible_component_factory_f41_offer(id=2, cpu_cores_effective=128),
            self.eligible_component_factory_f41_offer(id=1, dph_total=1.3),
            "invalid",
        ]
        with mock.patch.object(
            self.wrapper, "vast_request", return_value={"offers": offers}
        ) as request:
            selected = self.wrapper.get_component_factory_f41_offers("unused", 2)
        self.assertEqual([offer["id"] for offer in selected], [2, 3])
        self.assertEqual(request.call_args.kwargs["method"], "POST")
        query = request.call_args.kwargs["payload"]
        self.assertEqual(query["limit"], 1000)
        self.assertNotIn("id", query)

    def test_component_factory_f41_commands_are_explicit_and_read_only_listing(self):
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("launch-component-factory-f41-best", source)
        output = io.StringIO()
        selected = self.eligible_component_factory_f41_offer()
        with (
            mock.patch.object(self.wrapper, "login", return_value="session"),
            mock.patch.object(self.wrapper, "read_vast_key", return_value="unused"),
            mock.patch.object(self.wrapper, "revoke_token") as revoke,
            mock.patch.object(
                self.wrapper,
                "get_component_factory_f41_offers",
                return_value=[selected],
            ) as offers,
            mock.patch.object(
                self.wrapper, "launch_component_factory_f41_offer"
            ) as launch,
            mock.patch("sys.stdout", output),
        ):
            result = self.wrapper.run(["component-factory-f41-offers"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())[0]["id"], selected["id"])
        offers.assert_called_once_with("unused")
        launch.assert_not_called()
        revoke.assert_called_once_with("session")

    def test_component_factory_f41_launch_route_requires_one_exact_offer_id(self):
        selected = self.eligible_component_factory_f41_offer()
        with (
            mock.patch.object(self.wrapper, "login", return_value="session"),
            mock.patch.object(self.wrapper, "read_vast_key", return_value="unused"),
            mock.patch.object(self.wrapper, "revoke_token") as revoke,
            mock.patch.object(
                self.wrapper,
                "get_component_factory_f41_offers",
                return_value=[selected],
            ) as offers,
            mock.patch.object(
                self.wrapper,
                "launch_component_factory_f41_offer",
                return_value=0,
            ) as launch,
        ):
            result = self.wrapper.run(
                [
                    "launch-component-factory-f41",
                    str(USER_PROVIDED_COMPONENT_FACTORY_F41_CANDIDATE_ID),
                ]
            )
        self.assertEqual(result, 0)
        offers.assert_called_once_with(
            "unused", USER_PROVIDED_COMPONENT_FACTORY_F41_CANDIDATE_ID
        )
        launch.assert_called_once_with("unused", selected)
        revoke.assert_called_once_with("session")

        for returned in (
            [],
            [self.eligible_component_factory_f41_offer(id=7)],
            [selected, dict(selected)],
        ):
            with (
                self.subTest(returned_count=len(returned)),
                mock.patch.object(self.wrapper, "login", return_value="session"),
                mock.patch.object(
                    self.wrapper, "read_vast_key", return_value="unused"
                ),
                mock.patch.object(self.wrapper, "revoke_token"),
                mock.patch.object(
                    self.wrapper,
                    "get_component_factory_f41_offers",
                    return_value=returned,
                ),
                mock.patch.object(
                    self.wrapper, "launch_component_factory_f41_offer"
                ) as launch,
                self.assertRaisesRegex(
                    self.wrapper.SafeError, "unavailable or outside"
                ),
            ):
                self.wrapper.run(
                    [
                        "launch-component-factory-f41",
                        str(USER_PROVIDED_COMPONENT_FACTORY_F41_CANDIDATE_ID),
                    ]
                )
            launch.assert_not_called()

    def test_component_factory_f41_launch_uses_exact_ssh_direct_contract(self):
        output = io.StringIO()
        offer = self.eligible_component_factory_f41_offer()
        attempt_label = self.component_factory_f41_attempt_label()
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper, "require_no_component_factory_f41_instance"
            ) as no_existing,
            mock.patch.object(
                self.wrapper, "ensure_local_ssh_registered"
            ) as ensure_ssh,
            mock.patch.object(
                self.wrapper,
                "component_factory_f41_attempt_label",
                return_value=attempt_label,
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 41341},
            ) as request,
            mock.patch.object(
                self.wrapper, "verify_single_component_factory_f41_instance"
            ) as singleton,
            mock.patch.object(
                self.wrapper, "verify_component_factory_f41_contract"
            ) as contract,
            mock.patch.object(
                self.wrapper,
                "verify_component_factory_f41_ssh_ready",
                return_value=Path("/tmp/f41-41341-known-hosts"),
            ) as ready,
            mock.patch("sys.stdout", output),
        ):
            result = self.wrapper.launch_component_factory_f41_offer(
                "unused", offer
            )
        self.assertEqual(result, 0)
        no_existing.assert_called_once_with("unused")
        ensure_ssh.assert_called_once_with("unused")
        singleton.assert_called_once_with("unused", 41341, attempt_label)
        contract.assert_called_once_with("unused", 41341, attempt_label)
        ready.assert_called_once_with("unused", 41341)
        self.assertEqual(
            request.call_args.args[1],
            f"/api/v0/asks/{USER_PROVIDED_COMPONENT_FACTORY_F41_CANDIDATE_ID}/",
        )
        self.assertEqual(request.call_args.kwargs["method"], "PUT")
        payload = request.call_args.kwargs["payload"]
        self.assertEqual(
            payload,
            {
                "image": self.wrapper.COMPONENT_FACTORY_F41_IMAGE,
                "label": attempt_label,
                "disk": 300,
                "runtype": "ssh_direct",
                "env": {},
                "onstart": "/usr/local/bin/917-cad-vast-onstart",
                "cancel_unavail": True,
            },
        )
        serialized = json.dumps(payload).lower()
        self.assertNotIn("token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("image_login", serialized)
        report = json.loads(output.getvalue())
        self.assertEqual(report["label"], attempt_label)
        self.assertEqual(
            report["selected_offer"]["inet_up_cost_usd_per_gb"], 0.01
        )
        self.assertEqual(
            report["selected_offer"]["inet_down_cost_usd_per_gb"], 0.01
        )
        self.assertTrue(report["offer_contract_verified"])
        self.assertTrue(report["singleton_preflight_verified"])
        self.assertTrue(report["singleton_verified"])
        self.assertTrue(report["contract_verified"])
        self.assertTrue(report["running_state_verified"])
        self.assertTrue(report["ssh_batch_mode_verified"])
        self.assertTrue(report["image_transport_smoke_verified"])
        self.assertEqual(report["host_key_alias"], "f41-41341")
        self.assertEqual(
            report["known_hosts_path"], "/tmp/f41-41341-known-hosts"
        )
        self.assertFalse(report["f41_component_factory_executed"])
        self.assertFalse(report["physical_claims_validated"])
        self.assertFalse(report["manufacturing_authorized"])

    def test_component_factory_f41_launch_revalidates_before_any_side_effect(self):
        with (
            mock.patch.object(self.wrapper, "simready_launch_lock") as launch_lock,
            mock.patch.object(
                self.wrapper, "ensure_local_ssh_registered"
            ) as ensure_ssh,
            mock.patch.object(self.wrapper, "vast_request") as request,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "fixed safety and price limits"
            ),
        ):
            self.wrapper.launch_component_factory_f41_offer(
                "unused",
                self.eligible_component_factory_f41_offer(reliability=0.984),
            )
        launch_lock.assert_not_called()
        ensure_ssh.assert_not_called()
        request.assert_not_called()

    def test_component_factory_f41_duplicate_guard_precedes_ssh_and_create(self):
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[
                    {
                        "id": 41341,
                        "label": self.component_factory_f41_attempt_label("b" * 20),
                    }
                ],
            ),
            mock.patch.object(
                self.wrapper, "ensure_local_ssh_registered"
            ) as ensure_ssh,
            mock.patch.object(self.wrapper, "vast_request") as request,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "component-factory F41 instance already exists"
            ),
        ):
            self.wrapper.launch_component_factory_f41_offer(
                "unused", self.eligible_component_factory_f41_offer()
            )
        ensure_ssh.assert_not_called()
        request.assert_not_called()

    def test_component_factory_f41_post_create_singleton_is_exact(self):
        attempt_label = self.component_factory_f41_attempt_label()
        with mock.patch.object(
            self.wrapper,
            "list_instances",
            return_value=[
                {"id": 41341, "label": attempt_label}
            ],
        ):
            self.wrapper.verify_single_component_factory_f41_instance(
                "unused", 41341, attempt_label
            )

        rejected = (
            [
                {"id": 41341, "label": attempt_label},
                {"id": 41342, "label": attempt_label},
            ],
            [{"id": 41342, "label": attempt_label}],
            [{"id": True, "label": attempt_label}],
            [{"id": 41341, "label": self.component_factory_f41_attempt_label("b" * 20)}],
        )
        for instances in rejected:
            with (
                self.subTest(instances=instances),
                mock.patch.object(
                    self.wrapper, "list_instances", return_value=instances
                ),
                self.assertRaisesRegex(
                    self.wrapper.SafeError, "post-launch uniqueness verification failed"
                ),
            ):
                self.wrapper.verify_single_component_factory_f41_instance(
                    "unused", 41341, attempt_label
                )

    def test_component_factory_f41_concurrent_labels_rollback_only_this_attempt(self):
        attempt_label = self.component_factory_f41_attempt_label()
        other_label = self.component_factory_f41_attempt_label("b" * 20)
        family = [
            {"id": 41341, "label": attempt_label},
            {"id": 41342, "label": other_label},
        ]

        def list_for_scope(_api_key, *, label=None):
            if label is None:
                return family
            return [instance for instance in family if instance["label"] == label]

        output = io.StringIO()
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper, "require_no_component_factory_f41_instance"
            ),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "component_factory_f41_attempt_label",
                return_value=attempt_label,
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 41341},
            ),
            mock.patch.object(
                self.wrapper, "list_instances", side_effect=list_for_scope
            ),
            mock.patch.object(
                self.wrapper, "verify_component_factory_f41_contract"
            ) as contract,
            mock.patch.object(
                self.wrapper, "verify_component_factory_f41_ssh_ready"
            ) as ready,
            mock.patch.object(
                self.wrapper, "destroy_instance_verified"
            ) as destroy,
            mock.patch("sys.stdout", output),
            self.assertRaisesRegex(
                self.wrapper.SafeError, "post-launch uniqueness verification failed"
            ),
        ):
            self.wrapper.launch_component_factory_f41_offer(
                "unused", self.eligible_component_factory_f41_offer()
            )
        destroy.assert_called_once_with("unused", 41341)
        contract.assert_not_called()
        ready.assert_not_called()
        self.assertNotIn("singleton_verified", output.getvalue())

    def test_component_factory_f41_singleton_rejects_delayed_second_label(self):
        attempt_label = self.component_factory_f41_attempt_label()
        other_label = self.component_factory_f41_attempt_label("b" * 20)
        snapshots = [
            [{"id": 41341, "label": attempt_label}],
            [
                {"id": 41341, "label": attempt_label},
                {"id": 41342, "label": other_label},
            ],
        ]
        with (
            mock.patch.object(
                self.wrapper, "list_instances", side_effect=snapshots
            ) as instances,
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "post-launch uniqueness verification failed"
            ),
        ):
            self.wrapper.verify_single_component_factory_f41_instance(
                "unused", 41341, attempt_label
            )
        self.assertEqual(instances.call_count, 2)
        sleep.assert_called_once_with(self.wrapper.POLL_INTERVAL_SECONDS)

    def test_component_factory_f41_post_launch_contract_is_fail_closed(self):
        attempt_label = self.component_factory_f41_attempt_label()
        with mock.patch.object(
            self.wrapper,
            "vast_request",
            return_value={"instances": self.component_factory_f41_instance()},
        ):
            instance = self.wrapper.verify_component_factory_f41_contract(
                "unused", 41341, attempt_label
            )
        self.assertEqual(instance["status"], "running")

        rejected = (
            ({"id": 41342}, "instance id"),
            ({"label": "wrong"}, "label"),
            ({"image_uuid": "ghcr.io/example/wrong@sha256:deadbeef"}, "image digest"),
            ({"actual_status": "exited"}, "status"),
            ({"cpu_cores_effective": 63.999}, "effective CPU threads"),
            ({"cpu_ram": 255999}, "CPU RAM"),
            ({"disk_space": 299.999}, "disk"),
            ({"dph_total": 1.250001}, "dph_total"),
            ({"inet_up_cost": -0.001}, "inet_up_cost"),
            ({"inet_up_cost": 0.050001}, "inet_up_cost"),
            ({"inet_up_cost": float("nan")}, "inet_up_cost"),
            ({"inet_down_cost": -0.001}, "inet_down_cost"),
            ({"inet_down_cost": 0.050001}, "inet_down_cost"),
            ({"inet_down_cost": float("inf")}, "inet_down_cost"),
            ({"verification": "unverified"}, "machine verification"),
        )
        for override, message in rejected:
            with (
                self.subTest(override=override),
                mock.patch.object(
                    self.wrapper,
                    "vast_request",
                    return_value={
                        "instances": self.component_factory_f41_instance(**override)
                    },
                ),
                self.assertRaisesRegex(self.wrapper.SafeError, message),
            ):
                self.wrapper.verify_component_factory_f41_contract(
                    "unused", 41341, attempt_label
                )

    def test_component_factory_f41_contract_waits_until_running(self):
        attempt_label = self.component_factory_f41_attempt_label()
        with (
            mock.patch.object(
                self.wrapper,
                "vast_request",
                side_effect=[
                    {
                        "instances": self.component_factory_f41_instance(
                            actual_status="loading"
                        )
                    },
                    {"instances": self.component_factory_f41_instance()},
                ],
            ) as request,
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
        ):
            instance = self.wrapper.verify_component_factory_f41_contract(
                "unused", 41341, attempt_label
            )
        self.assertEqual(instance["status"], "running")
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(self.wrapper.POLL_INTERVAL_SECONDS)

    def test_component_factory_f41_ssh_ready_is_strict_and_batch_only(self):
        remote_command = self.wrapper.component_factory_f41_remote_smoke_command()
        strict_markers = (
            "ready == {",
            "vast_onstart_ready_for_public_archive_transfer_cad_not_started",
            "offline_transport_and_cad_step_smoke_passed_vast_f41_and_manufacturing_validation_blocked",
            "synthetic_build123d_step_smoke_passed",
            "synthetic_step_roundtrip_executed",
            "synthetic_closed_solid_after_roundtrip",
            "runtime_host_keys_generated_before_onstart",
            "sshd_runtime_wrapper_installed",
            "runtime_host_keys_generated_by_wrapper",
            "f41_component_factory_executed",
            "physical_claims_validated",
            "manufacturing_authorized",
            "F41_REMOTE_READY",
        )
        for marker in strict_markers:
            self.assertIn(marker, remote_command)

        completed = self.wrapper.subprocess.CompletedProcess(
            args=[], returncode=0, stdout="F41_REMOTE_READY\n", stderr=""
        )
        with (
            mock.patch.object(
                self.wrapper, "validate_approved_ssh_private_key"
            ) as validate_key,
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={
                    "instances": self.component_factory_f41_instance(
                        ssh_host="203.0.113.41",
                        ssh_port=32141,
                    )
                },
            ),
            mock.patch.object(
                self.wrapper.subprocess, "run", return_value=completed
            ) as run,
            mock.patch.object(
                self.wrapper,
                "prepare_component_factory_f41_known_hosts",
                return_value=Path("/tmp/f41-test-known-hosts"),
            ) as prepare_known_hosts,
            mock.patch.object(
                self.wrapper, "validate_component_factory_f41_known_hosts"
            ) as validate_known_hosts,
        ):
            known_hosts_path = self.wrapper.verify_component_factory_f41_ssh_ready(
                "unused", 41341
            )
        validate_key.assert_called_once_with()
        prepare_known_hosts.assert_called_once_with(41341)
        self.assertEqual(known_hosts_path, Path("/tmp/f41-test-known-hosts"))
        validate_known_hosts.assert_called_once_with(
            Path("/tmp/f41-test-known-hosts"), 41341
        )
        command = run.call_args.args[0]
        self.assertIn(str(self.wrapper.SSH_PRIVATE_KEY_FILE), command)
        self.assertIn("BatchMode=yes", command)
        self.assertIn("IdentitiesOnly=yes", command)
        self.assertIn("StrictHostKeyChecking=accept-new", command)
        self.assertIn("UpdateHostKeys=no", command)
        self.assertIn("GlobalKnownHostsFile=/dev/null", command)
        self.assertIn("HashKnownHosts=no", command)
        self.assertIn("HostKeyAlias=f41-41341", command)
        self.assertIn("UserKnownHostsFile=/tmp/f41-test-known-hosts", command)
        self.assertIn("root@203.0.113.41", command)
        self.assertIn("32141", command)
        self.assertNotIn("ssh-add", command)
        self.assertIn("/workspace/READY", command[-1])
        self.assertIn("/workspace/image-smoke.json", command[-1])

    def test_component_factory_f41_ssh_never_accepts_failed_ready(self):
        failed = self.wrapper.subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="not ready"
        )
        with (
            mock.patch.object(self.wrapper, "validate_approved_ssh_private_key"),
            mock.patch.object(
                self.wrapper, "COMPONENT_FACTORY_F41_SSH_READY_ATTEMPTS", 2
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={
                    "instances": self.component_factory_f41_instance(
                        ssh_host="203.0.113.41",
                        ssh_port=32141,
                    )
                },
            ),
            mock.patch.object(
                self.wrapper.subprocess, "run", return_value=failed
            ) as run,
            mock.patch.object(
                self.wrapper,
                "prepare_component_factory_f41_known_hosts",
                return_value=Path("/tmp/f41-test-known-hosts-failed"),
            ),
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
            self.assertRaisesRegex(
                self.wrapper.SafeError, "do not treat the instance as ready"
            ),
        ):
            self.wrapper.verify_component_factory_f41_ssh_ready("unused", 41341)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(sleep.call_count, 2)

    def test_component_factory_f41_known_hosts_is_scoped_private_and_exclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            known_hosts_dir = Path(temporary) / "cache" / "known-hosts"
            with mock.patch.object(
                self.wrapper,
                "COMPONENT_FACTORY_F41_KNOWN_HOSTS_DIR",
                known_hosts_dir,
            ):
                path = self.wrapper.prepare_component_factory_f41_known_hosts(41341)
                self.assertEqual(path, known_hosts_dir / "f41-41341")
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(known_hosts_dir.stat().st_mode & 0o777, 0o700)
                with self.assertRaisesRegex(
                    self.wrapper.SafeError, "already exists"
                ):
                    self.wrapper.prepare_component_factory_f41_known_hosts(41341)
                path.write_text("f41-41341 ssh-ed25519 AAAATEST\n", encoding="utf-8")
                self.wrapper.validate_component_factory_f41_known_hosts(path, 41341)
                with self.assertRaisesRegex(
                    self.wrapper.SafeError, "exactly one expected alias"
                ):
                    self.wrapper.validate_component_factory_f41_known_hosts(path, 41342)
                self.wrapper.remove_component_factory_f41_known_hosts_after_destroy(
                    41341
                )
                self.assertFalse(path.exists())

    def test_component_factory_f41_post_create_failures_reconcile_exact_attempt(self):
        failing_verifiers = (
            "verify_single_component_factory_f41_instance",
            "verify_component_factory_f41_contract",
            "verify_component_factory_f41_ssh_ready",
        )
        attempt_label = self.component_factory_f41_attempt_label()
        for failing_verifier in failing_verifiers:
            patches = {
                name: mock.DEFAULT
                for name in failing_verifiers
            }
            with (
                self.subTest(failing_verifier=failing_verifier),
                mock.patch.object(
                    self.wrapper, "simready_launch_lock", return_value=nullcontext()
                ),
                mock.patch.object(
                    self.wrapper, "require_no_component_factory_f41_instance"
                ),
                mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
                mock.patch.object(
                    self.wrapper,
                    "component_factory_f41_attempt_label",
                    return_value=attempt_label,
                ),
                mock.patch.object(
                    self.wrapper,
                    "vast_request",
                    return_value={"new_contract": 41341},
                ),
                mock.patch.multiple(self.wrapper, **patches) as verifiers,
                mock.patch.object(
                    self.wrapper,
                    "reconcile_uncertain_component_factory_f41_launch",
                    return_value=41341,
                ) as reconcile,
                self.assertRaisesRegex(self.wrapper.SafeError, "F41 verification failed"),
            ):
                verifiers[failing_verifier].side_effect = self.wrapper.SafeError(
                    "F41 verification failed"
                )
                self.wrapper.launch_component_factory_f41_offer(
                    "unused", self.eligible_component_factory_f41_offer()
                )
            reconcile.assert_called_once_with("unused", attempt_label)

    def test_component_factory_f41_uncertain_create_reconciles_including_4xx(self):
        attempt_label = self.component_factory_f41_attempt_label()
        uncertain_errors = (
            self.wrapper.SafeHttpError("Vast.ai", 408),
            self.wrapper.SafeHttpError("Vast.ai", 409),
            self.wrapper.SafeHttpError("Vast.ai", 503),
            self.wrapper.SafeError("Vast.ai is unavailable"),
        )
        for error in uncertain_errors:
            with (
                self.subTest(error=type(error).__name__),
                mock.patch.object(
                    self.wrapper, "simready_launch_lock", return_value=nullcontext()
                ),
                mock.patch.object(
                    self.wrapper, "require_no_component_factory_f41_instance"
                ),
                mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
                mock.patch.object(
                    self.wrapper,
                    "component_factory_f41_attempt_label",
                    return_value=attempt_label,
                ),
                mock.patch.object(
                    self.wrapper, "vast_request", side_effect=error
                ) as request,
                mock.patch.object(
                    self.wrapper,
                    "reconcile_uncertain_component_factory_f41_launch",
                    return_value=41341,
                ) as reconcile,
                self.assertRaises(type(error)),
            ):
                self.wrapper.launch_component_factory_f41_offer(
                    "unused", self.eligible_component_factory_f41_offer()
                )
            request.assert_called_once()
            reconcile.assert_called_once_with("unused", attempt_label)

    def test_component_factory_f41_uncertain_reconciliation_is_unambiguous(self):
        attempt_label = self.component_factory_f41_attempt_label()
        with (
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[
                    {"id": 41341, "label": attempt_label}
                ],
            ),
            mock.patch.object(
                self.wrapper, "destroy_instance_verified"
            ) as destroy,
        ):
            reconciled_id = (
                self.wrapper.reconcile_uncertain_component_factory_f41_launch(
                    "unused", attempt_label
                )
            )
        self.assertEqual(reconciled_id, 41341)
        destroy.assert_called_once_with("unused", 41341)

        ambiguous = [
            {"id": 41341, "label": attempt_label},
            {"id": 41342, "label": attempt_label},
        ]
        with (
            mock.patch.object(
                self.wrapper, "list_instances", return_value=ambiguous
            ),
            mock.patch.object(
                self.wrapper, "destroy_instance_verified"
            ) as destroy,
            self.assertRaisesRegex(self.wrapper.SafeError, "not mapped to one valid"),
        ):
            self.wrapper.reconcile_uncertain_component_factory_f41_launch(
                "unused", attempt_label
            )
        destroy.assert_not_called()

    def test_component_factory_f41_attempt_labels_are_unique_bounded_and_scoped(self):
        first = self.wrapper.component_factory_f41_attempt_label()
        second = self.wrapper.component_factory_f41_attempt_label()
        self.assertNotEqual(first, second)
        self.assertLessEqual(len(first), 64)
        self.assertTrue(self.wrapper.is_component_factory_f41_attempt_label(first))
        self.assertTrue(self.wrapper.is_component_factory_f41_family_label(first))
        self.assertTrue(
            self.wrapper.is_component_factory_f41_family_label(
                self.wrapper.COMPONENT_FACTORY_F41_LABEL
            )
        )
        self.assertFalse(
            self.wrapper.is_component_factory_f41_attempt_label(
                self.wrapper.COMPONENT_FACTORY_F41_LABEL
            )
        )

    def test_component_factory_f41_never_destroys_unrelated_attempt(self):
        attempt_label = self.component_factory_f41_attempt_label()
        other_label = self.component_factory_f41_attempt_label("b" * 20)
        with (
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[{"id": 90001, "label": other_label}],
            ),
            mock.patch.object(
                self.wrapper, "destroy_instance_verified"
            ) as destroy,
            self.assertRaisesRegex(self.wrapper.SafeError, "not mapped to one valid"),
        ):
            self.wrapper.reconcile_uncertain_component_factory_f41_launch(
                "unused", attempt_label
            )
        destroy.assert_not_called()

    def test_component_factory_f41_wrong_new_contract_destroys_only_correlated_id(self):
        attempt_label = self.component_factory_f41_attempt_label()
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper, "require_no_component_factory_f41_instance"
            ),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "component_factory_f41_attempt_label",
                return_value=attempt_label,
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 41341},
            ),
            mock.patch.object(
                self.wrapper,
                "verify_single_component_factory_f41_instance",
                side_effect=self.wrapper.SafeError("returned id is not correlated"),
            ),
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[{"id": 90001, "label": attempt_label}],
            ),
            mock.patch.object(
                self.wrapper, "destroy_instance_verified"
            ) as destroy,
            self.assertRaisesRegex(self.wrapper.SafeError, "not correlated"),
        ):
            self.wrapper.launch_component_factory_f41_offer(
                "unused", self.eligible_component_factory_f41_offer()
            )
        destroy.assert_called_once_with("unused", 90001)
        self.assertNotEqual(destroy.call_args.args[1], 41341)

    def test_component_factory_f41_keyboard_interrupt_reconciles_and_propagates(self):
        attempt_label = self.component_factory_f41_attempt_label()
        for interruption_point in ("create", "verification"):
            create_result = (
                KeyboardInterrupt()
                if interruption_point == "create"
                else {"new_contract": 41341}
            )
            verifier_effect = (
                None if interruption_point == "create" else KeyboardInterrupt()
            )
            with (
                self.subTest(interruption_point=interruption_point),
                mock.patch.object(
                    self.wrapper, "simready_launch_lock", return_value=nullcontext()
                ),
                mock.patch.object(
                    self.wrapper, "require_no_component_factory_f41_instance"
                ),
                mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
                mock.patch.object(
                    self.wrapper,
                    "component_factory_f41_attempt_label",
                    return_value=attempt_label,
                ),
                mock.patch.object(
                    self.wrapper,
                    "vast_request",
                    side_effect=create_result
                    if isinstance(create_result, BaseException)
                    else None,
                    return_value=create_result
                    if isinstance(create_result, dict)
                    else None,
                ),
                mock.patch.object(
                    self.wrapper,
                    "verify_single_component_factory_f41_instance",
                    side_effect=verifier_effect,
                ),
                mock.patch.object(
                    self.wrapper, "verify_component_factory_f41_contract"
                ),
                mock.patch.object(
                    self.wrapper, "verify_component_factory_f41_ssh_ready"
                ),
                mock.patch.object(
                    self.wrapper,
                    "list_instances",
                    return_value=[{"id": 41341, "label": attempt_label}],
                ),
                mock.patch.object(
                    self.wrapper, "destroy_instance_verified"
                ) as destroy,
                self.assertRaises(KeyboardInterrupt),
            ):
                self.wrapper.launch_component_factory_f41_offer(
                    "unused", self.eligible_component_factory_f41_offer()
                )
            destroy.assert_called_once_with("unused", 41341)

    def test_component_factory_f41_cleanup_failure_does_not_swallow_interrupt(self):
        attempt_label = self.component_factory_f41_attempt_label()
        stderr = io.StringIO()
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper, "require_no_component_factory_f41_instance"
            ),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "component_factory_f41_attempt_label",
                return_value=attempt_label,
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 41341},
            ),
            mock.patch.object(
                self.wrapper,
                "verify_single_component_factory_f41_instance",
                side_effect=KeyboardInterrupt(),
            ),
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[{"id": 41341, "label": attempt_label}],
            ),
            mock.patch.object(
                self.wrapper,
                "destroy_instance_verified",
                side_effect=self.wrapper.SafeError("destroy unavailable"),
            ),
            mock.patch("sys.stderr", stderr),
            self.assertRaises(KeyboardInterrupt) as interrupted,
        ):
            self.wrapper.launch_component_factory_f41_offer(
                "unused", self.eligible_component_factory_f41_offer()
            )
        self.assertIsInstance(interrupted.exception.__cause__, self.wrapper.SafeError)
        self.assertIn("CRITICAL: F41 rollback was not verified", stderr.getvalue())
        self.assertIn("may still be running and billed", stderr.getvalue())
        self.assertIn(attempt_label, stderr.getvalue())

    def test_component_factory_f41_local_trust_cleanup_does_not_swallow_interrupt(self):
        attempt_label = self.component_factory_f41_attempt_label()
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper, "require_no_component_factory_f41_instance"
            ),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "component_factory_f41_attempt_label",
                return_value=attempt_label,
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 41341},
            ),
            mock.patch.object(
                self.wrapper,
                "verify_single_component_factory_f41_instance",
                side_effect=KeyboardInterrupt(),
            ),
            mock.patch.object(
                self.wrapper,
                "reconcile_uncertain_component_factory_f41_launch",
                return_value=41341,
            ) as reconcile,
            mock.patch.object(
                self.wrapper,
                "remove_component_factory_f41_known_hosts_after_destroy",
                side_effect=self.wrapper.SafeError("local trust cleanup failed"),
            ) as remove_known_hosts,
            self.assertRaises(KeyboardInterrupt) as interrupted,
        ):
            self.wrapper.launch_component_factory_f41_offer(
                "unused", self.eligible_component_factory_f41_offer()
            )
        reconcile.assert_called_once_with("unused", attempt_label)
        remove_known_hosts.assert_called_once_with(41341)
        self.assertIsInstance(interrupted.exception.__cause__, self.wrapper.SafeError)
        notes = getattr(interrupted.exception, "__notes__", None)
        if notes is not None:
            self.assertIn("remote destruction was verified", "\n".join(notes))

    def test_component_factory_f41_cli_surfaces_billing_risk_on_cancel(self):
        attempt_label = self.component_factory_f41_attempt_label()
        offer = self.eligible_component_factory_f41_offer()
        stderr = io.StringIO()
        with (
            mock.patch("sys.argv", ["openbao-vastai", "launch-component-factory-f41", str(offer["id"])]),
            mock.patch.object(self.wrapper, "login", return_value="session"),
            mock.patch.object(self.wrapper, "read_vast_key", return_value="unused"),
            mock.patch.object(self.wrapper, "revoke_token") as revoke,
            mock.patch.object(
                self.wrapper,
                "get_component_factory_f41_offers",
                return_value=[offer],
            ),
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper, "require_no_component_factory_f41_instance"
            ),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "component_factory_f41_attempt_label",
                return_value=attempt_label,
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 41341},
            ),
            mock.patch.object(
                self.wrapper,
                "verify_single_component_factory_f41_instance",
                side_effect=KeyboardInterrupt(),
            ),
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[{"id": 41341, "label": attempt_label}],
            ),
            mock.patch.object(
                self.wrapper,
                "destroy_instance_verified",
                side_effect=self.wrapper.SafeError("destroy unavailable"),
            ),
            mock.patch("sys.stderr", stderr),
        ):
            status = self.wrapper.cli()
        self.assertEqual(status, 130)
        self.assertIn("CRITICAL: F41 rollback was not verified", stderr.getvalue())
        self.assertIn("may still be running and billed", stderr.getvalue())
        self.assertIn(attempt_label, stderr.getvalue())
        self.assertIn("OpenBao Vast.ai: cancelled", stderr.getvalue())
        revoke.assert_called_once_with("session")

    def test_component_factory_f41_invalid_create_id_is_reconciled(self):
        attempt_label = self.component_factory_f41_attempt_label()
        with (
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(
                self.wrapper, "require_no_component_factory_f41_instance"
            ),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper,
                "component_factory_f41_attempt_label",
                return_value=attempt_label,
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": True},
            ),
            mock.patch.object(
                self.wrapper,
                "reconcile_uncertain_component_factory_f41_launch",
                return_value=41341,
            ) as reconcile,
            self.assertRaisesRegex(self.wrapper.SafeError, "did not return a new"),
        ):
            self.wrapper.launch_component_factory_f41_offer(
                "unused", self.eligible_component_factory_f41_offer()
            )
        reconcile.assert_called_once_with("unused", attempt_label)

    def test_github_credential_is_never_forwarded_to_vast(self):
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("OPENBAO_GHCR_IMAGE_LOGIN", source)
        self.assertNotIn("image_login", source)


if __name__ == "__main__":
    unittest.main()
