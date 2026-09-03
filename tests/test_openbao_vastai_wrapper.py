"""Tests hors ligne du wrapper Vast.ai borné au projet."""

from __future__ import annotations

from contextlib import nullcontext
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
from pathlib import Path
import shlex
import sys
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
        # Most unit tests isolate the launch state machine from the immutable
        # production denylist. Production keeps every known-bad digest
        # denylisted; that gate has its own focused tests.
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

    def simready_attempt_label(self, token: str = "a" * 20):
        return f"{self.wrapper.SIMREADY_LABEL}-{token}"

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
            {
                "success": True,
                "instances": [{"id": 9, "label": "bounded-test"}],
                "next_token": None,
            },
            {"success": True},
            *[
                {"success": True, "instances": [], "next_token": None}
                for _ in range(self.wrapper.DESTROY_ABSENCE_STABILITY_SNAPSHOTS)
            ],
        ]
        with (
            mock.patch.object(self.wrapper, "vast_request", side_effect=responses),
            mock.patch.object(self.wrapper.time, "sleep"),
        ):
            self.wrapper.destroy_instance_verified("unused", 9)

    def test_destroy_does_not_count_malformed_inventory_as_absence(self):
        responses = [
            {
                "success": True,
                "instances": [{"id": 9, "label": "bounded-test"}],
                "next_token": None,
            },
            {"success": True},
            *[
                {"success": True, "instances": [], "next_token": None}
                for _ in range(4)
            ],
            {"success": "error", "instances": [], "next_token": None},
        ]
        with (
            mock.patch.object(self.wrapper, "vast_request", side_effect=responses),
            mock.patch.object(self.wrapper, "DESTROY_VERIFY_ATTEMPTS", 5),
            mock.patch.object(self.wrapper.time, "sleep"),
            self.assertRaisesRegex(
                self.wrapper.SafeError, "did not verify stable destruction"
            ),
        ):
            self.wrapper.destroy_instance_verified("unused", 9)

    def test_destroy_requires_a_strict_boolean_acknowledgement(self):
        for acknowledgement in (1, 1.0):
            responses = [
                {
                    "success": True,
                    "instances": [{"id": 9, "label": "bounded-test"}],
                    "next_token": None,
                },
                {"success": acknowledgement},
            ]
            with (
                self.subTest(acknowledgement=acknowledgement),
                mock.patch.object(
                    self.wrapper, "vast_request", side_effect=responses
                ),
                mock.patch.object(self.wrapper.time, "sleep") as sleep,
                self.assertRaisesRegex(
                    self.wrapper.SafeError, "exact destroy acknowledgement"
                ),
            ):
                self.wrapper.destroy_instance_verified("unused", 9)
            sleep.assert_not_called()

    def test_heavy_launch_enforces_singleton_and_contract(self):
        output = io.StringIO()
        attempt_label = self.simready_attempt_label()
        with (
            mock.patch.object(
                self.wrapper,
                "SIMREADY_IMAGE",
                "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:" + "a" * 64,
            ),
            mock.patch.object(self.wrapper, "simready_launch_lock", return_value=nullcontext()),
            mock.patch.object(self.wrapper, "require_no_simready_instance") as no_existing,
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper, "simready_attempt_label", return_value=attempt_label
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={"new_contract": 12345},
            ) as request,
            mock.patch.object(self.wrapper, "verify_single_simready_instance") as singleton,
            mock.patch.object(self.wrapper, "verify_simready_contract") as contract,
            mock.patch.object(
                self.wrapper,
                "verify_simready_ssh_ready",
                return_value=Path("/tmp/simready-known-hosts"),
            ) as ssh_ready,
            mock.patch("sys.stdout", output),
        ):
            result = self.wrapper.launch_simready_offer(
                "unused", self.eligible_offer(), disk_gb=500, enforce_singleton=True
            )
        self.assertEqual(result, 0)
        no_existing.assert_called_once_with("unused")
        singleton.assert_called_once_with("unused", 12345, attempt_label)
        contract.assert_called_once_with("unused", 12345, attempt_label)
        ssh_ready.assert_called_once_with("unused", 12345)
        self.assertEqual(request.call_args.kwargs["payload"]["label"], attempt_label)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["singleton_verified"])
        self.assertTrue(payload["contract_verified"])
        self.assertTrue(payload["ssh_batch_mode_verified"])
        self.assertTrue(payload["runtime_ready_verified"])
        self.assertTrue(payload["physicsnemo_gpu_runtime_verified"])
        self.assertFalse(payload["simulation_validated"])
        self.assertFalse(payload["manufacturing_authorized"])
        self.assertFalse(payload["target_1600_ch_validated"])
        self.assertEqual(payload["label"], attempt_label)

    def test_validation_only_launch_skips_content_agents_and_uses_exact_ready(self):
        output = io.StringIO()
        attempt_label = self.simready_attempt_label()
        with (
            mock.patch.object(
                self.wrapper,
                "SIMREADY_IMAGE",
                "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:" + "a" * 64,
            ),
            mock.patch.object(self.wrapper, "simready_launch_lock", return_value=nullcontext()),
            mock.patch.object(self.wrapper, "require_no_simready_instance"),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper, "simready_attempt_label", return_value=attempt_label
            ),
            mock.patch.object(
                self.wrapper, "vast_request", return_value={"new_contract": 12345}
            ) as request,
            mock.patch.object(self.wrapper, "verify_single_simready_instance"),
            mock.patch.object(self.wrapper, "verify_simready_contract"),
            mock.patch.object(
                self.wrapper,
                "verify_simready_ssh_ready",
                return_value=Path("/tmp/simready-known-hosts"),
            ) as ssh_ready,
            mock.patch("sys.stdout", output),
        ):
            result = self.wrapper.launch_simready_offer(
                "unused",
                self.eligible_offer(),
                disk_gb=500,
                enforce_singleton=True,
                validation_only=True,
            )
        self.assertEqual(result, 0)
        payload = request.call_args.kwargs["payload"]
        self.assertIn("simready_validation_only_ready", payload["onstart"])
        self.assertIn("physicsnemo-gpu-smoke", payload["onstart"])
        self.assertNotIn("simready-services start", payload["onstart"])
        ssh_ready.assert_called_once_with("unused", 12345, validation_only=True)
        report = json.loads(output.getvalue())
        self.assertTrue(report["validation_only"])
        self.assertEqual(report["property_assignment_intent"], "skip")
        self.assertFalse(report["content_agents_started"])

    def test_validation_only_ready_commands_are_distinct_and_fail_closed(self):
        onstart = self.wrapper.simready_validation_only_onstart_command()
        remote = self.wrapper.simready_validation_only_remote_ready_command()
        self.assertIn("simready_validation_only_ready", onstart)
        self.assertIn("property_assignment_intent", onstart)
        self.assertNotIn("simready-services start", onstart)
        self.assertIn("SIMREADY_VALIDATION_ONLY_REMOTE_READY", remote)
        self.assertIn("physicsnemo-gpu-smoke.json", remote)

    def test_simready_offer_is_revalidated_before_paid_side_effects(self):
        qualified = (
            "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:"
            + "a" * 64
        )
        for kwargs in (
            {"enforce_singleton": False, "disk_gb": 500},
            {"enforce_singleton": True, "disk_gb": 499},
            {"enforce_singleton": True, "disk_gb": 500, "offer": self.eligible_offer(gpu_ram=79999)},
        ):
            offer = kwargs.pop("offer", self.eligible_offer())
            with (
                self.subTest(kwargs=kwargs, offer=offer),
                mock.patch.object(self.wrapper, "SIMREADY_IMAGE", qualified),
                mock.patch.object(self.wrapper, "simready_launch_lock") as launch_lock,
                mock.patch.object(self.wrapper, "vast_request") as request,
                self.assertRaisesRegex(
                    self.wrapper.SafeError, "supervised heavy offer contract"
                ),
            ):
                self.wrapper.launch_simready_offer("unused", offer, **kwargs)
            launch_lock.assert_not_called()
            request.assert_not_called()

    def test_simready_every_create_error_reconciles_unique_attempt(self):
        qualified = (
            "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:"
            + "a" * 64
        )
        attempt_label = self.simready_attempt_label()
        launch_error = self.wrapper.SafeHttpError("Vast.ai", 408)
        with (
            mock.patch.object(self.wrapper, "SIMREADY_IMAGE", qualified),
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(self.wrapper, "require_no_simready_instance"),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper, "simready_attempt_label", return_value=attempt_label
            ),
            mock.patch.object(
                self.wrapper, "vast_request", side_effect=launch_error
            ),
            mock.patch.object(
                self.wrapper,
                "reconcile_uncertain_simready_launch",
                return_value=12345,
            ) as reconcile,
            self.assertRaises(self.wrapper.SafeHttpError),
        ):
            self.wrapper.launch_simready_offer(
                "unused", self.eligible_offer(), disk_gb=500, enforce_singleton=True
            )
        reconcile.assert_called_once_with("unused", attempt_label)

    def test_only_supervised_heavy_simready_launch_route_is_exposed(self):
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertIn("launch-simready-heavy <offer_id> [--attempt-label <label>]", source)
        self.assertNotIn('operation[0] == "launch-simready"', source)
        self.assertNotIn('operation == ["launch-simready-best"]', source)
        self.assertNotIn('operation == ["launch-simready-best-eu"]', source)

    def test_simready_post_create_ssh_failure_destroys_exact_instance(self):
        qualified = (
            "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:"
            + "a" * 64
        )
        attempt_label = self.simready_attempt_label()
        with (
            mock.patch.object(self.wrapper, "SIMREADY_IMAGE", qualified),
            mock.patch.object(
                self.wrapper, "simready_launch_lock", return_value=nullcontext()
            ),
            mock.patch.object(self.wrapper, "require_no_simready_instance"),
            mock.patch.object(self.wrapper, "ensure_local_ssh_registered"),
            mock.patch.object(
                self.wrapper, "simready_attempt_label", return_value=attempt_label
            ),
            mock.patch.object(
                self.wrapper, "vast_request", return_value={"new_contract": 12345}
            ),
            mock.patch.object(self.wrapper, "verify_single_simready_instance"),
            mock.patch.object(self.wrapper, "verify_simready_contract"),
            mock.patch.object(
                self.wrapper,
                "verify_simready_ssh_ready",
                side_effect=self.wrapper.SafeError("remote READY rejected"),
            ),
            mock.patch.object(
                self.wrapper,
                "reconcile_uncertain_simready_launch",
                return_value=12345,
            ) as reconcile,
            mock.patch.object(
                self.wrapper, "remove_simready_known_hosts_after_destroy"
            ) as remove_known_hosts,
            self.assertRaisesRegex(self.wrapper.SafeError, "remote READY rejected"),
        ):
            self.wrapper.launch_simready_offer(
                "unused", self.eligible_offer(), disk_gb=500, enforce_singleton=True
            )
        reconcile.assert_called_once_with("unused", attempt_label)
        remove_known_hosts.assert_called_once_with(12345)

    def test_simready_ssh_ready_uses_batch_mode_and_exact_scoped_tofu(self):
        self.assertEqual(self.wrapper.SIMREADY_SSH_READY_TIMEOUT_SECONDS, 30 * 60)
        instance = {
            "id": 12345,
            "actual_status": "running",
            "ssh_host": "ssh.example.invalid",
            "ssh_port": 22022,
        }
        captured = {}
        with tempfile.TemporaryDirectory() as temporary:
            known_hosts_dir = Path(temporary) / "known-hosts"

            def successful_probe(command, environment):
                captured["command"] = command
                captured["environment"] = environment
                option = next(
                    item for item in command if item.startswith("UserKnownHostsFile=")
                )
                path = Path(option.split("=", 1)[1])
                path.write_text(
                    "simready-12345 ssh-ed25519 AAAATEST\n", encoding="utf-8"
                )
                return self.wrapper.subprocess.CompletedProcess(
                    command, 0, "SIMREADY_REMOTE_READY\n", ""
                )

            with (
                mock.patch.object(
                    self.wrapper, "SIMREADY_KNOWN_HOSTS_DIR", known_hosts_dir
                ),
                mock.patch.object(self.wrapper, "validate_approved_ssh_private_key"),
                mock.patch.object(
                    self.wrapper,
                    "vast_request",
                    return_value={"instances": instance},
                ),
                mock.patch.object(
                    self.wrapper,
                    "run_component_factory_f41_ssh_probe",
                    side_effect=successful_probe,
                ),
                mock.patch.object(self.wrapper, "SIMREADY_SSH_READY_ATTEMPTS", 1),
            ):
                result = self.wrapper.verify_simready_ssh_ready("unused", 12345)

            self.assertEqual(result, known_hosts_dir / "simready-12345")
            command = captured["command"]
            self.assertEqual(command[1:3], ["-F", "/dev/null"])
            self.assertIn("BatchMode=yes", command)
            self.assertIn("IdentitiesOnly=yes", command)
            self.assertIn("ForwardAgent=no", command)
            self.assertIn("ClearAllForwardings=yes", command)
            self.assertIn("PermitLocalCommand=no", command)
            self.assertIn("PasswordAuthentication=no", command)
            self.assertIn("KbdInteractiveAuthentication=no", command)
            self.assertIn("StrictHostKeyChecking=accept-new", command)
            self.assertIn("UpdateHostKeys=no", command)
            self.assertIn("GlobalKnownHostsFile=/dev/null", command)
            self.assertIn("HostKeyAlias=simready-12345", command)
            self.assertEqual(captured["environment"]["LC_ALL"], "C")
            self.assertEqual(set(captured["environment"]), {"LC_ALL", "PATH"})
            self.assertNotIn("SSH_AUTH_SOCK", captured["environment"])
            remote = command[-1]
            self.assertIn("SIMREADY_REMOTE_READY", remote)
            self.assertIn("target_1600_ch_validated", remote)
            self.assertIn("physicsnemo-gpu-smoke.json", remote)

    def test_simready_remote_ready_rejects_integer_boolean_substitution(self):
        ready = {
            "schema_version": "1.0.0",
            "status": "simready_local_ai_services_ready",
            "ephemeral_ssh_host_keys": 1,
            "batch_ssh_auto_tmux_disabled": 1,
            "physicsnemo_gpu_smoke_passed": 1,
            "local_vlm_ready": 1,
            "ovrtx_ready": 1,
            "material_agent_ready": 1,
            "physics_agent_ready": 1,
            "simulation_validated": 0,
            "manufacturing_authorized": 0,
            "target_1600_ch_validated": 0,
        }
        gpu = {
            "schema_version": "1.0.0",
            "status": "passed",
            "claim_scope": "runtime GPU only; no engine simulation or physical validation",
            "physicsnemo_version": "2.2.0",
            "torch_version": "2.10.0+cu129",
            "torch_cuda_version": "12.9",
            "gpu_name": "synthetic-98GB",
            "gpu_memory_bytes": 98304 * 1024 * 1024,
            "gpu_count": 1,
            "tensor_result": 14.0,
        }
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            logs = workspace / "logs"
            logs.mkdir(parents=True)
            (workspace / "READY").write_text(json.dumps(ready), encoding="utf-8")
            (logs / "physicsnemo-gpu-smoke.json").write_text(
                json.dumps(gpu), encoding="utf-8"
            )
            for name in (
                "nvidia-smi.log",
                "simready-smoke.log",
                "simready-services-start.log",
                "simready-services-status.log",
            ):
                (logs / name).write_text("synthetic\n", encoding="utf-8")
            remote = shlex.split(self.wrapper.simready_remote_ready_command())
            script = remote[2].replace("/workspace", str(workspace))
            completed = self.wrapper.subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 43)
        self.assertEqual(completed.stdout, "")

    def test_simready_ready_contract_rejection_is_terminal(self):
        completed = self.wrapper.subprocess.CompletedProcess([], 43, "", "")
        self.assertEqual(
            self.wrapper.classify_simready_ssh_probe(completed),
            "remote_ready_contract_rejected",
        )

    def test_revoked_simready_images_block_before_paid_side_effects(self):
        for revoked_image in self.wrapper.SIMREADY_REVOKED_IMAGES:
            with (
                self.subTest(revoked_image=revoked_image),
                mock.patch.object(self.wrapper, "SIMREADY_IMAGE", revoked_image),
                mock.patch.object(self.wrapper, "simready_launch_lock") as launch_lock,
                mock.patch.object(self.wrapper, "ensure_local_ssh_registered") as ensure_ssh,
                mock.patch.object(self.wrapper, "vast_request") as request,
                self.assertRaisesRegex(self.wrapper.SafeError, "pinned SimReady image is revoked"),
            ):
                self.wrapper.launch_simready_offer(
                    "unused", self.eligible_offer(), disk_gb=500, enforce_singleton=True
                )
            launch_lock.assert_not_called()
            ensure_ssh.assert_not_called()
            request.assert_not_called()

    def test_uncertain_launch_rolls_back_the_only_project_instance(self):
        attempt_label = self.simready_attempt_label()
        with (
            mock.patch.object(
                self.wrapper,
                "list_instances",
                return_value=[
                    {
                        "id": 12345,
                        "label": attempt_label,
                        "image_uuid": "wrong-image-still-owned-by-label",
                    }
                ],
            ),
            mock.patch.object(self.wrapper, "destroy_instance_verified") as destroy,
        ):
            result = self.wrapper.reconcile_uncertain_simready_launch(
                "unused", attempt_label
            )
        self.assertEqual(result, 12345)
        destroy.assert_called_once_with(
            "unused", 12345, expected_label=attempt_label
        )

    def test_simready_attempt_labels_are_unique_bounded_and_scoped(self):
        first = self.wrapper.simready_attempt_label()
        second = self.wrapper.simready_attempt_label()
        self.assertNotEqual(first, second)
        self.assertTrue(self.wrapper.is_simready_attempt_label(first))
        self.assertTrue(self.wrapper.is_simready_family_label(first))
        self.assertTrue(self.wrapper.is_simready_family_label(self.wrapper.SIMREADY_LABEL))
        self.assertFalse(self.wrapper.is_simready_attempt_label(self.wrapper.SIMREADY_LABEL))
        self.assertFalse(
            self.wrapper.is_simready_attempt_label(
                self.wrapper.SIMREADY_LABEL + "-" + "g" * 20
            )
        )

    def test_simready_cleanup_attestation_is_exact_json(self):
        attempt_label = self.simready_attempt_label()
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            self.wrapper.emit_simready_cleanup_attestation(12345, attempt_label)
        line = stderr.getvalue().strip()
        self.assertTrue(line.startswith(self.wrapper.SIMREADY_CLEANUP_PREFIX))
        receipt = json.loads(line[len(self.wrapper.SIMREADY_CLEANUP_PREFIX) :])
        self.assertEqual(
            set(receipt),
            {
                "schema_version",
                "status",
                "instance_id",
                "label",
                "requested_image",
                "delete_acknowledged",
                "paginated_absence_verified",
                "stable_absence_snapshots",
            },
        )
        self.assertEqual(receipt["status"], "destroyed_verified_stably_absent")
        self.assertEqual(receipt["instance_id"], 12345)
        self.assertEqual(receipt["label"], attempt_label)
        self.assertEqual(receipt["requested_image"], self.wrapper.SIMREADY_IMAGE)
        self.assertIs(receipt["delete_acknowledged"], True)
        self.assertIs(receipt["paginated_absence_verified"], True)
        self.assertEqual(receipt["stable_absence_snapshots"], 5)

    def test_simready_parent_can_reconcile_one_persisted_attempt_label(self):
        attempt_label = self.simready_attempt_label()
        with (
            mock.patch.object(self.wrapper, "login", return_value="session"),
            mock.patch.object(self.wrapper, "read_vast_key", return_value="unused"),
            mock.patch.object(self.wrapper, "revoke_token") as revoke,
            mock.patch.object(
                self.wrapper,
                "reconcile_uncertain_simready_launch",
                return_value=12345,
            ) as reconcile,
            mock.patch.object(
                self.wrapper, "emit_simready_cleanup_attestation"
            ) as receipt,
        ):
            result = self.wrapper.run(
                ["reconcile-simready-attempt", attempt_label]
            )
        self.assertEqual(result, 0)
        reconcile.assert_called_once_with("unused", attempt_label)
        receipt.assert_called_once_with(12345, attempt_label)
        revoke.assert_called_once_with("session")

    def test_simready_singleton_requires_five_stable_family_snapshots(self):
        attempt_label = self.simready_attempt_label()
        other_label = self.simready_attempt_label("b" * 20)
        snapshots = [
            [{"id": 12345, "label": attempt_label}],
            [{"id": 12345, "label": attempt_label}],
            [
                {"id": 12345, "label": attempt_label},
                {"id": 12346, "label": other_label},
            ],
        ]
        with (
            mock.patch.object(
                self.wrapper, "strict_instance_inventory", side_effect=snapshots
            ),
            mock.patch.object(self.wrapper.time, "sleep"),
            self.assertRaisesRegex(self.wrapper.SafeError, "uniqueness verification"),
        ):
            self.wrapper.verify_single_simready_instance(
                "unused", 12345, attempt_label
            )

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
            "c59c53b2611a1e3a9e9de5d2cedf8bfb0cd57e72582b2d6b29f6c8fc82bf7e6b",
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
        self.assertIn(
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGE_356A,
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGES,
        )
        self.assertIn(
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGE_7155,
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGES,
        )
        self.assertNotIn(
            production_wrapper.COMPONENT_FACTORY_F41_IMAGE,
            production_wrapper.COMPONENT_FACTORY_F41_REVOKED_IMAGES,
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
        launch.assert_called_once_with("unused", selected, attempt_label=None)
        revoke.assert_called_once_with("session")

        supervised_label = self.component_factory_f41_attempt_label()
        with (
            mock.patch.object(self.wrapper, "login", return_value="session"),
            mock.patch.object(self.wrapper, "read_vast_key", return_value="unused"),
            mock.patch.object(self.wrapper, "revoke_token"),
            mock.patch.object(
                self.wrapper,
                "get_component_factory_f41_offers",
                return_value=[selected],
            ),
            mock.patch.object(
                self.wrapper,
                "launch_component_factory_f41_offer",
                return_value=0,
            ) as supervised_launch,
        ):
            result = self.wrapper.run(
                [
                    "launch-component-factory-f41",
                    str(USER_PROVIDED_COMPONENT_FACTORY_F41_CANDIDATE_ID),
                    "--attempt-label",
                    supervised_label,
                ]
            )
        self.assertEqual(result, 0)
        supervised_launch.assert_called_once_with(
            "unused", selected, attempt_label=supervised_label
        )

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
        stderr = io.StringIO()
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
            mock.patch("sys.stderr", stderr),
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
                "onstart": self.wrapper.component_factory_f41_onstart_command(),
                "cancel_unavail": True,
            },
        )
        self.assertIn("f41-onstart-status.json", payload["onstart"])
        self.assertIn("write_status running null", payload["onstart"])
        self.assertIn("write_status passed 0", payload["onstart"])
        self.assertIn('write_status failed "${onstart_rc}"', payload["onstart"])
        self.assertIn("/usr/bin/mktemp", payload["onstart"])
        self.assertIn('/bin/mv -f -- "${status_tmp}"', payload["onstart"])
        syntax = self.wrapper.subprocess.run(
            ["sh", "-n"],
            input=payload["onstart"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        serialized = json.dumps(payload).lower()
        self.assertNotIn("token", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("image_login", serialized)
        report = json.loads(output.getvalue())
        self.assertEqual(
            stderr.getvalue(),
            f"OpenBao Vast.ai F41 paid launch attempt label: {attempt_label}\n",
        )
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
            "runtime_host_keys_ready_before_cad_smoke",
            "sshd_runtime_wrapper_installed",
            "runtime_host_keys_generated_by_wrapper",
            "f41_component_factory_executed",
            "physical_claims_validated",
            "manufacturing_authorized",
            "READY_MISSING = 41",
            "REPORT_MISSING = 42",
            "CONTRACT_REJECTED = 43",
            "ONSTART_STATUS_MISSING = 44",
            "ONSTART_RUNNING = 45",
            "ONSTART_FAILED = 46",
            "os.O_NOFOLLOW",
            "os.O_NONBLOCK",
            "os.fstat",
            "REPORT_MAX_BYTES = 1024 * 1024",
            "stat.S_ISREG",
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
                self.wrapper,
                "run_component_factory_f41_ssh_probe",
                return_value=completed,
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
        self.assertEqual(run.call_args.args[1]["LC_ALL"], "C")

    def test_component_factory_f41_ssh_never_accepts_failed_ready(self):
        failed = self.wrapper.subprocess.CompletedProcess(
            args=[], returncode=41, stdout="", stderr="sensitive remote output"
        )
        expected = (
            "F41 SSH /workspace/READY and image smoke verification did not pass "
            "in time (last state: running; last probe: ready_marker_missing); do "
            "not treat the instance as ready"
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
                self.wrapper,
                "run_component_factory_f41_ssh_probe",
                return_value=failed,
            ) as run,
            mock.patch.object(
                self.wrapper,
                "prepare_component_factory_f41_known_hosts",
                return_value=Path("/tmp/f41-test-known-hosts-failed"),
            ),
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
            self.assertRaises(self.wrapper.SafeError) as raised,
        ):
            self.wrapper.verify_component_factory_f41_ssh_ready("unused", 41341)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(str(raised.exception), expected)
        self.assertNotIn("sensitive remote output", str(raised.exception))

    def test_component_factory_f41_ssh_probe_classification_is_fixed(self):
        cases = (
            (41, "sensitive ignored text", "ready_marker_missing"),
            (42, "sensitive ignored text", "image_smoke_report_missing"),
            (43, "sensitive ignored text", "remote_ready_contract_rejected"),
            (44, "sensitive ignored text", "onstart_status_missing"),
            (45, "sensitive ignored text", "onstart_running"),
            (46, "sensitive ignored text", "onstart_failed"),
            (255, "Permission denied (publickey).", "ssh_authentication_failed"),
            (255, "Connection refused", "ssh_connection_refused"),
            (255, "Connection timed out", "ssh_connection_timeout"),
            (255, "Host key verification failed.", "ssh_host_key_rejected"),
            (255, "Connection closed by remote host", "ssh_connection_closed"),
            (255, "No route to host", "ssh_network_unreachable"),
            (255, "unrecognized sensitive text", "ssh_transport_failed"),
            (1, "unrecognized sensitive text", "remote_command_rejected"),
        )
        for returncode, stderr, expected in cases:
            with self.subTest(expected=expected):
                completed = self.wrapper.subprocess.CompletedProcess(
                    args=[], returncode=returncode, stdout="", stderr=stderr
                )
                self.assertEqual(
                    self.wrapper.classify_component_factory_f41_ssh_probe(completed),
                    expected,
                )

    def test_component_factory_f41_ssh_timeout_reports_fixed_category(self):
        expected = (
            "F41 SSH /workspace/READY and image smoke verification did not pass "
            "in time (last state: running; last probe: ssh_probe_timeout); do not "
            "treat the instance as ready"
        )
        with (
            mock.patch.object(self.wrapper, "validate_approved_ssh_private_key"),
            mock.patch.object(
                self.wrapper, "COMPONENT_FACTORY_F41_SSH_READY_ATTEMPTS", 1
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={
                    "instances": self.component_factory_f41_instance(
                        ssh_host="203.0.113.41", ssh_port=32141
                    )
                },
            ),
            mock.patch.object(
                self.wrapper,
                "run_component_factory_f41_ssh_probe",
                side_effect=self.wrapper.ComponentFactoryF41ProbeTimeout(),
            ),
            mock.patch.object(
                self.wrapper,
                "prepare_component_factory_f41_known_hosts",
                return_value=Path("/tmp/f41-test-known-hosts-timeout"),
            ),
            mock.patch.object(self.wrapper.time, "sleep"),
            self.assertRaises(self.wrapper.SafeError) as raised,
        ):
            self.wrapper.verify_component_factory_f41_ssh_ready("unused", 41341)
        self.assertEqual(str(raised.exception), expected)

    def test_component_factory_f41_spamming_ssh_is_bounded_and_destroyed(self):
        attempt_label = self.component_factory_f41_attempt_label()
        offer = self.eligible_component_factory_f41_offer()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="f41-spamming-ssh-") as temporary:
            root = Path(temporary)
            fake_ssh = root / "ssh"
            pid_path = root / "fake-ssh.pid"
            fake_ssh.write_text(
                f"#!{sys.executable}\n"
                "import os\n"
                "import time\n"
                f"pid_path = {str(pid_path)!r}\n"
                "with open(pid_path, 'w', encoding='ascii') as handle:\n"
                "    handle.write(str(os.getpid()))\n"
                "payload = b'x' * 8192\n"
                "while True:\n"
                "    os.write(1, payload)\n"
                "    os.write(2, payload)\n"
                "    time.sleep(0.001)\n",
                encoding="utf-8",
            )
            fake_ssh.chmod(0o755)

            def vast_request(_api_key, path, *, method="GET", payload=None):
                if path == f"/api/v0/asks/{offer['id']}/" and method == "PUT":
                    return {"new_contract": 41341}
                if path == "/api/v0/instances/41341/" and method == "GET":
                    return {
                        "instances": self.component_factory_f41_instance(
                            label=attempt_label,
                            ssh_host="203.0.113.41",
                            ssh_port=32141,
                        )
                    }
                raise AssertionError((path, method, payload))

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
                    self.wrapper, "vast_request", side_effect=vast_request
                ),
                mock.patch.object(
                    self.wrapper, "verify_single_component_factory_f41_instance"
                ),
                mock.patch.object(
                    self.wrapper, "verify_component_factory_f41_contract"
                ),
                mock.patch.object(
                    self.wrapper, "validate_approved_ssh_private_key"
                ),
                mock.patch.object(
                    self.wrapper,
                    "prepare_component_factory_f41_known_hosts",
                    return_value=root / "known-hosts",
                ),
                mock.patch.object(
                    self.wrapper,
                    "COMPONENT_FACTORY_F41_SSH_PROBE_MAX_BYTES_PER_STREAM",
                    4096,
                ),
                mock.patch.object(
                    self.wrapper,
                    "COMPONENT_FACTORY_F41_SSH_PROBE_TIMEOUT_SECONDS",
                    5,
                ),
                mock.patch.object(
                    self.wrapper,
                    "COMPONENT_FACTORY_F41_SSH_PROBE_TERMINATE_GRACE_SECONDS",
                    0.2,
                ),
                mock.patch.dict(self.wrapper.os.environ, {"PATH": str(root)}),
                mock.patch.object(
                    self.wrapper,
                    "list_instances",
                    return_value=[{"id": 41341, "label": attempt_label}],
                ),
                mock.patch.object(
                    self.wrapper, "destroy_instance_verified"
                ) as destroy,
                mock.patch("sys.stdout", stdout),
                mock.patch("sys.stderr", stderr),
                self.assertRaisesRegex(
                    self.wrapper.SafeError, "ssh_probe_output_limit"
                ),
            ):
                self.wrapper.launch_component_factory_f41_offer(
                    "unused", offer
                )
            destroy.assert_called_once_with("unused", 41341)
            self.assertLessEqual(len(stdout.getvalue()), 1024)
            self.assertLessEqual(len(stderr.getvalue()), 1024)
            fake_pid = int(pid_path.read_text(encoding="ascii"))
            with self.assertRaises(ProcessLookupError):
                os.kill(fake_pid, 0)

    def test_component_factory_f41_local_probe_failures_are_fatal(self):
        failures = (
            (
                self.wrapper.ComponentFactoryF41ProbeOutputLimit(),
                "ssh_probe_output_limit",
            ),
            (
                self.wrapper.ComponentFactoryF41ProbeSpawnError(),
                "ssh_probe_spawn_failed",
            ),
            (
                self.wrapper.ComponentFactoryF41ProbeLocalIoError(),
                "ssh_probe_local_io_failed",
            ),
            (
                self.wrapper.ComponentFactoryF41ProbeCleanupError(),
                "ssh_probe_cleanup_failed",
            ),
        )
        for failure, category in failures:
            with (
                self.subTest(category=category),
                mock.patch.object(
                    self.wrapper, "validate_approved_ssh_private_key"
                ),
                mock.patch.object(
                    self.wrapper, "COMPONENT_FACTORY_F41_SSH_READY_ATTEMPTS", 3
                ),
                mock.patch.object(
                    self.wrapper,
                    "vast_request",
                    return_value={
                        "instances": self.component_factory_f41_instance(
                            ssh_host="203.0.113.41", ssh_port=32141
                        )
                    },
                ),
                mock.patch.object(
                    self.wrapper,
                    "run_component_factory_f41_ssh_probe",
                    side_effect=failure,
                ) as run,
                mock.patch.object(
                    self.wrapper,
                    "prepare_component_factory_f41_known_hosts",
                    return_value=Path("/tmp/f41-test-known-hosts-local-failure"),
                ),
                mock.patch.object(self.wrapper.time, "sleep") as sleep,
                self.assertRaisesRegex(self.wrapper.SafeError, category),
            ):
                self.wrapper.verify_component_factory_f41_ssh_ready(
                    "unused", 41341
                )
            run.assert_called_once()
            sleep.assert_not_called()

    def test_component_factory_f41_probe_setup_failure_is_guarded(self):
        process = mock.Mock()
        process.stdout = io.BytesIO()
        process.stderr = io.BytesIO()
        with (
            mock.patch.object(
                self.wrapper.subprocess, "Popen", return_value=process
            ) as popen,
            mock.patch.object(
                self.wrapper.selectors,
                "DefaultSelector",
                side_effect=OSError("sensitive local error"),
            ),
            mock.patch.object(
                self.wrapper,
                "terminate_component_factory_f41_probe",
                return_value=True,
            ) as terminate,
            self.assertRaises(
                self.wrapper.ComponentFactoryF41ProbeLocalIoError
            ),
        ):
            self.wrapper.run_component_factory_f41_ssh_probe(
                ["ssh", "example.invalid"], {"LC_ALL": "C"}
            )
        terminate.assert_called_once_with(process)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertIs(
            popen.call_args.kwargs["stdin"], self.wrapper.subprocess.DEVNULL
        )
        self.assertIs(
            popen.call_args.kwargs["stdout"], self.wrapper.subprocess.PIPE
        )
        self.assertIs(
            popen.call_args.kwargs["stderr"], self.wrapper.subprocess.PIPE
        )

        failed_process = mock.Mock()
        failed_process.stdout = io.BytesIO()
        failed_process.stderr = io.BytesIO()
        with (
            mock.patch.object(
                self.wrapper.subprocess, "Popen", return_value=failed_process
            ),
            mock.patch.object(
                self.wrapper.selectors,
                "DefaultSelector",
                side_effect=OSError("sensitive local error"),
            ),
            mock.patch.object(
                self.wrapper,
                "terminate_component_factory_f41_probe",
                return_value=False,
            ),
            self.assertRaises(
                self.wrapper.ComponentFactoryF41ProbeCleanupError
            ),
        ):
            self.wrapper.run_component_factory_f41_ssh_probe(
                ["ssh", "example.invalid"], {"LC_ALL": "C"}
            )

    def test_component_factory_f41_fatal_ssh_diagnostics_fail_fast(self):
        for stderr, category in (
            ("Permission denied (publickey).", "ssh_authentication_failed"),
            ("Host key verification failed.", "ssh_host_key_rejected"),
            (
                "sensitive report output",
                "image_smoke_report_missing",
            ),
            (
                "sensitive contract output",
                "remote_ready_contract_rejected",
            ),
            ("sensitive onstart output", "onstart_failed"),
            ("sensitive shell output", "remote_command_rejected"),
        ):
            returncode = {
                "ssh_authentication_failed": 255,
                "ssh_host_key_rejected": 255,
                "image_smoke_report_missing": 42,
                "remote_ready_contract_rejected": 43,
                "onstart_failed": 46,
                "remote_command_rejected": 1,
            }[category]
            completed = self.wrapper.subprocess.CompletedProcess(
                args=[],
                returncode=returncode,
                stdout="",
                stderr=stderr,
            )
            with (
                self.subTest(category=category),
                mock.patch.object(
                    self.wrapper, "validate_approved_ssh_private_key"
                ),
                mock.patch.object(
                    self.wrapper, "COMPONENT_FACTORY_F41_SSH_READY_ATTEMPTS", 3
                ),
                mock.patch.object(
                    self.wrapper,
                    "vast_request",
                    return_value={
                        "instances": self.component_factory_f41_instance(
                            ssh_host="203.0.113.41", ssh_port=32141
                        )
                    },
                ),
                mock.patch.object(
                    self.wrapper,
                    "run_component_factory_f41_ssh_probe",
                    return_value=completed,
                ) as run,
                mock.patch.object(
                    self.wrapper,
                    "prepare_component_factory_f41_known_hosts",
                    return_value=Path("/tmp/f41-test-known-hosts-fatal"),
                ),
                mock.patch.object(self.wrapper.time, "sleep") as sleep,
                self.assertRaises(self.wrapper.SafeError) as raised,
            ):
                self.wrapper.verify_component_factory_f41_ssh_ready(
                    "unused", 41341
                )
            run.assert_called_once()
            sleep.assert_not_called()
            self.assertEqual(
                str(raised.exception),
                "F41 SSH /workspace/READY and image smoke verification failed "
                f"(last state: running; last probe: {category}); do not treat the "
                "instance as ready",
            )
            self.assertNotIn(stderr, str(raised.exception))

    def test_component_factory_f41_transient_ssh_failures_can_reach_ready(self):
        missing = self.wrapper.subprocess.CompletedProcess(
            args=[],
            returncode=41,
            stdout="",
            stderr="sensitive remote output",
        )
        ready = self.wrapper.subprocess.CompletedProcess(
            args=[], returncode=0, stdout="F41_REMOTE_READY\n", stderr=""
        )
        with (
            mock.patch.object(self.wrapper, "validate_approved_ssh_private_key"),
            mock.patch.object(
                self.wrapper, "COMPONENT_FACTORY_F41_SSH_READY_ATTEMPTS", 3
            ),
            mock.patch.object(
                self.wrapper,
                "vast_request",
                return_value={
                    "instances": self.component_factory_f41_instance(
                        ssh_host="203.0.113.41", ssh_port=32141
                    )
                },
            ),
            mock.patch.object(
                self.wrapper,
                "run_component_factory_f41_ssh_probe",
                side_effect=[
                    self.wrapper.ComponentFactoryF41ProbeTimeout(),
                    missing,
                    ready,
                ],
            ) as run,
            mock.patch.object(
                self.wrapper,
                "prepare_component_factory_f41_known_hosts",
                return_value=Path("/tmp/f41-test-known-hosts-transient"),
            ),
            mock.patch.object(
                self.wrapper, "validate_component_factory_f41_known_hosts"
            ) as validate_known_hosts,
            mock.patch.object(self.wrapper.time, "sleep") as sleep,
        ):
            path = self.wrapper.verify_component_factory_f41_ssh_ready(
                "unused", 41341
            )
        self.assertEqual(path, Path("/tmp/f41-test-known-hosts-transient"))
        self.assertEqual(run.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        validate_known_hosts.assert_called_once_with(
            Path("/tmp/f41-test-known-hosts-transient"), 41341
        )

    def test_component_factory_f41_remote_probe_exit_codes_are_unambiguous(self):
        command = self.wrapper.component_factory_f41_remote_smoke_command()
        argv = shlex.split(command)
        self.assertEqual(argv[:2], ["python", "-c"])
        original = argv[2]
        with tempfile.TemporaryDirectory(prefix="f41-remote-probe-") as temporary:
            root = Path(temporary)
            status = root / "f41-onstart-status.json"
            ready = root / "READY"
            report = root / "image-smoke.json"

            def run_probe():
                script = original.replace(
                    "Path('/workspace/f41-onstart-status.json')",
                    f"Path({str(status)!r})",
                ).replace(
                    "Path('/workspace/READY')", f"Path({str(ready)!r})"
                ).replace(
                    "Path('/workspace/image-smoke.json')", f"Path({str(report)!r})"
                )
                return self.wrapper.subprocess.run(
                    [sys.executable, "-c", script],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

            missing_status = run_probe()
            self.assertEqual(missing_status.returncode, 44)
            self.assertEqual((missing_status.stdout, missing_status.stderr), ("", ""))

            status.symlink_to(ready)
            rejected_status_symlink = run_probe()
            self.assertEqual(rejected_status_symlink.returncode, 43)
            status.unlink()

            os.mkfifo(status)
            rejected_status_fifo = run_probe()
            self.assertEqual(rejected_status_fifo.returncode, 43)
            self.assertEqual(
                (rejected_status_fifo.stdout, rejected_status_fifo.stderr),
                ("", ""),
            )
            status.unlink()

            status.write_text("{\n", encoding="utf-8")
            malformed_status = run_probe()
            self.assertEqual(malformed_status.returncode, 43)

            status.write_text("x" * (16 * 1024 + 1), encoding="utf-8")
            oversized_status = run_probe()
            self.assertEqual(oversized_status.returncode, 43)
            self.assertEqual(
                (oversized_status.stdout, oversized_status.stderr), ("", "")
            )

            status.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "status": "running",
                        "exit_code": None,
                    }
                ),
                encoding="utf-8",
            )
            running = run_probe()
            self.assertEqual(running.returncode, 45)

            status.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "status": "failed",
                        "exit_code": 78,
                    }
                ),
                encoding="utf-8",
            )
            failed = run_probe()
            self.assertEqual(failed.returncode, 46)

            status.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "status": "passed",
                        "exit_code": 0,
                    }
                ),
                encoding="utf-8",
            )
            missing_ready = run_probe()
            self.assertEqual(missing_ready.returncode, 41)
            self.assertEqual((missing_ready.stdout, missing_ready.stderr), ("", ""))

            ready.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "status": "vast_onstart_ready_for_public_archive_transfer_cad_not_started",
                        "authorized_key_file_present": True,
                        "noninteractive_ssh_auto_tmux_disabled": True,
                        "runtime_host_keys_ready_before_cad_smoke": True,
                        "synthetic_build123d_step_smoke_passed": True,
                        "f41_component_factory_executed": False,
                        "physical_claims_validated": False,
                        "manufacturing_authorized": False,
                    }
                ),
                encoding="utf-8",
            )
            missing_report = run_probe()
            self.assertEqual(missing_report.returncode, 42)
            self.assertEqual((missing_report.stdout, missing_report.stderr), ("", ""))

            report.write_text("x" * (1024 * 1024 + 1), encoding="utf-8")
            oversized_report = run_probe()
            self.assertEqual(oversized_report.returncode, 43)
            self.assertEqual(
                (oversized_report.stdout, oversized_report.stderr), ("", "")
            )
            report.unlink()

            ready.unlink()
            ready.symlink_to(report)
            rejected_symlink = run_probe()
            self.assertEqual(rejected_symlink.returncode, 43)
            self.assertEqual(
                (rejected_symlink.stdout, rejected_symlink.stderr), ("", "")
            )

            ready.unlink()
            ready.write_text("{\n", encoding="utf-8")
            report.write_text("{}\n", encoding="utf-8")
            malformed_json = run_probe()
            self.assertEqual(malformed_json.returncode, 43)
            self.assertEqual(
                (malformed_json.stdout, malformed_json.stderr), ("", "")
            )

    def test_component_factory_f41_cleanup_attestation_is_exact_json(self):
        attempt_label = self.component_factory_f41_attempt_label("a" * 20)
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            self.wrapper.emit_component_factory_f41_cleanup_attestation(
                41341, attempt_label
            )
        line = stderr.getvalue().strip()
        self.assertTrue(
            line.startswith(self.wrapper.COMPONENT_FACTORY_F41_CLEANUP_PREFIX)
        )
        receipt = json.loads(
            line[len(self.wrapper.COMPONENT_FACTORY_F41_CLEANUP_PREFIX) :]
        )
        self.assertEqual(
            set(receipt),
            {
                "schema_version",
                "status",
                "instance_id",
                "label",
                "image",
                "delete_acknowledged",
                "paginated_absence_verified",
            },
        )
        self.assertEqual(receipt["instance_id"], 41341)
        self.assertEqual(receipt["label"], attempt_label)
        self.assertEqual(receipt["image"], self.wrapper.COMPONENT_FACTORY_F41_IMAGE)
        self.assertIs(receipt["delete_acknowledged"], True)
        self.assertIs(receipt["paginated_absence_verified"], True)

    def test_component_factory_f41_onstart_status_is_atomic_and_keeps_exit_code(self):
        original = self.wrapper.component_factory_f41_onstart_command()
        with tempfile.TemporaryDirectory(prefix="f41-onstart-test-") as temporary:
            workspace = Path(temporary) / "workspace"
            workspace.mkdir()
            fake_onstart = Path(temporary) / "fake-onstart"

            def run_onstart(exit_code: int):
                fake_onstart.write_text(
                    f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8"
                )
                fake_onstart.chmod(0o755)
                script = original.replace("/workspace", str(workspace)).replace(
                    "/usr/local/bin/917-cad-vast-onstart", str(fake_onstart)
                )
                return self.wrapper.subprocess.run(
                    ["sh", "-c", script],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

            passed = run_onstart(0)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            status_path = workspace / "f41-onstart-status.json"
            self.assertEqual(
                json.loads(status_path.read_text(encoding="utf-8")),
                {
                    "schema_version": "1.0.0",
                    "status": "passed",
                    "exit_code": 0,
                },
            )
            self.assertEqual(status_path.stat().st_mode & 0o777, 0o644)
            self.assertFalse(status_path.is_symlink())
            self.assertEqual(list(workspace.glob(".f41-onstart-status.*")), [])

            failed = run_onstart(78)
            self.assertEqual(failed.returncode, 78, failed.stderr)
            self.assertEqual(
                json.loads(status_path.read_text(encoding="utf-8")),
                {
                    "schema_version": "1.0.0",
                    "status": "failed",
                    "exit_code": 78,
                },
            )
            self.assertEqual(list(workspace.glob(".f41-onstart-status.*")), [])

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
            stderr = io.StringIO()
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
                mock.patch("sys.stderr", stderr),
                self.assertRaisesRegex(self.wrapper.SafeError, "F41 verification failed"),
            ):
                verifiers[failing_verifier].side_effect = self.wrapper.SafeError(
                    "F41 verification failed"
                )
                self.wrapper.launch_component_factory_f41_offer(
                    "unused", self.eligible_component_factory_f41_offer()
                )
            reconcile.assert_called_once_with("unused", attempt_label)
            cleanup_lines = [
                line
                for line in stderr.getvalue().splitlines()
                if line.startswith(self.wrapper.COMPONENT_FACTORY_F41_CLEANUP_PREFIX)
            ]
            self.assertEqual(len(cleanup_lines), 1)

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
