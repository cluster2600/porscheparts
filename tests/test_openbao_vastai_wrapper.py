"""Tests hors ligne du wrapper Vast.ai borné au projet."""

from __future__ import annotations

from contextlib import nullcontext
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = ROOT / "deploy/openbao/openbao-vastai"
# Offre communiquee par l'utilisateur le 2026-09-02. Cette fixture ne prouve
# ni sa disponibilite actuelle, ni une location.
USER_PROVIDED_WAVE_CANDIDATE_ID = 49655039


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
            mock.patch("sys.stdout", output),
        ):
            result = self.wrapper.launch_wave_f39_offer("unused", offer)
        self.assertEqual(result, 0)
        singleton.assert_called_once_with("unused")
        ensure_ssh.assert_called_once_with("unused")
        verify_singleton.assert_called_once_with("unused", 12345)
        verify_contract.assert_called_once_with("unused", 12345)
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
        self.assertLess(
            payload["onstart"].index("/opt/917-engine-wave-f39/smoke.py"),
            payload["onstart"].index("/workspace/READY"),
        )
        serialized = json.dumps(payload).lower()
        self.assertNotIn("token", serialized)
        self.assertNotIn("api_key", serialized)
        report = json.loads(output.getvalue())
        self.assertTrue(report["offer_contract_verified"])
        self.assertTrue(report["singleton_preflight_verified"])
        self.assertTrue(report["singleton_verified"])
        self.assertTrue(report["contract_verified"])

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

    def test_github_credential_is_never_forwarded_to_vast(self):
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("OPENBAO_GHCR_IMAGE_LOGIN", source)
        self.assertNotIn("image_login", source)


if __name__ == "__main__":
    unittest.main()
