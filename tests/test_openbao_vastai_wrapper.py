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

    def test_mesh_image_is_immutable_linux_amd64_candidate(self):
        image = self.wrapper.MESH_IMAGE
        self.assertEqual(
            image,
            "ghcr.io/cluster2600/3dprinting993-mesh-cfd@"
            "sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f",
        )
        self.assertNotIn(":latest", image)


if __name__ == "__main__":
    unittest.main()
