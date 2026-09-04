"""Tests hors ligne du contrôleur Vast F46; aucune API et aucun secret."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/f46-vast-cfd-cae-controller.json"
JOBS_PATH = ROOT / "twins/reference-917-engine/f46-vast-job-manifest.json"
FIXTURE_PATH = ROOT / "tests/fixtures/917-f46-vast-controller-synthetic.json"
CONTROLLER_PATH = ROOT / "deploy/vast/f46/_f46_controller.py"
RUNNER_PATH = ROOT / "deploy/vast/f46/run-controller.sh"
VAST_WRAPPER_PATH = ROOT / "deploy/openbao/openbao-vastai"
GHCR_WRAPPER_PATH = ROOT / "deploy/openbao/openbao-ghcr"


def load_module(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


CTRL = load_module("f46_controller", CONTROLLER_PATH)
VAST = load_module("f46_vast_wrapper", VAST_WRAPPER_PATH)
GHCR = load_module("f46_ghcr_wrapper", GHCR_WRAPPER_PATH)


class F46ControllerTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.jobs = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def plan(self, **overrides):
        inputs = {
            "offers": deepcopy(self.fixture["offers"]),
            "image_proof": deepcopy(self.fixture["image_proof"]),
            "inventory_before": deepcopy(self.fixture["inventory_empty"]),
            "ledger": deepcopy(self.fixture["ledger_empty"]),
            "now_epoch": self.fixture["now_epoch"],
            "operator_deadline_epoch": self.fixture["operator_deadline_epoch"],
        }
        inputs.update(overrides)
        return CTRL.build_plan(
            self.contract,
            self.jobs,
            inputs["offers"],
            inputs["image_proof"],
            inputs["inventory_before"],
            inputs["ledger"],
            now_epoch=inputs["now_epoch"],
            operator_deadline_epoch=inputs["operator_deadline_epoch"],
            root=ROOT,
            allow_synthetic=True,
        )

    def test_contract_is_23_usd_fail_closed_and_jobs_are_complete(self):
        CTRL.validate_contract(self.contract, self.jobs, ROOT)
        budget = self.contract["budget"]
        self.assertEqual(budget["hard_total_usd"], 23.0)
        self.assertEqual(
            budget["planned_compute_ceiling_usd"] + budget["planned_network_ceiling_usd"],
            budget["planned_workload_ceiling_usd"],
        )
        self.assertEqual(
            budget["planned_workload_ceiling_usd"] + budget["cleanup_and_billing_reserve_usd"],
            23.0,
        )
        self.assertEqual(
            self.contract["offer_policy"]["maximum_inet_up_cost_usd_per_gb"],
            0.01,
        )
        self.assertEqual(
            self.contract["offer_policy"]["maximum_inet_down_cost_usd_per_gb"],
            0.01,
        )
        self.assertEqual(budget["maximum_image_pull_gb"], 4.0)
        self.assertEqual(budget["maximum_input_bundle_gb"], 0.1)
        self.assertEqual(budget["maximum_output_bundle_gb"], 1.0)
        self.assertEqual({item["family"] for item in self.jobs["jobs"]}, CTRL.REQUIRED_FAMILIES)
        self.assertEqual(self.jobs["planned_case_count"], 26)
        self.assertEqual(self.jobs["executable_case_count"], 0)
        self.assertTrue(all(item["command"] is None for item in self.jobs["jobs"]))
        self.assertTrue(all(value is False for value in self.contract["current_release_gates"].values()))

    def test_solver_authority_replaces_unproved_executable_alias(self):
        solver = self.jobs["solver_authority"]
        self.assertIs(solver["exact_ICEEngineFoam_executable_found"], False)
        self.assertIs(solver["fabricated_alias_allowed"], False)
        self.assertEqual(solver["current_engine_framework"], "AATE_OpenFOAM_ICengines")
        self.assertEqual(solver["cantera_version"], "3.2.0")
        self.assertIn(
            (str(CTRL.SOLVER_AUTHORITY_PATH), CTRL.SOLVER_AUTHORITY_SHA256),
            {(item["path"], item["sha256"]) for item in self.jobs["source_contracts"]},
        )
        for job in self.jobs["jobs"]:
            executable = job.get("required_executable")
            self.assertFalse(
                isinstance(executable, str)
                and executable.casefold() == "iceenginefoam"
            )

        mutated = deepcopy(self.jobs)
        aate = next(job for job in mutated["jobs"] if job["family"] == "AATE_ICengines")
        aate["required_executable"] = "iceEngineFoam"
        with self.assertRaisesRegex(CTRL.ContractError, "alias d.exécutable"):
            CTRL.validate_contract(self.contract, mutated, ROOT)

    def test_runtime_smokes_are_authority_named_and_historical_is_conditional(self):
        image_policy = self.contract["image_policy"]
        self.assertEqual(set(image_policy["required_tools"]), CTRL.REQUIRED_TOOL_KEYS)
        self.assertEqual(set(image_policy["optional_tools"]), CTRL.OPTIONAL_TOOL_KEYS)
        proof = self.fixture["image_proof"]
        self.assertIs(proof["exact_ICEEngineFoam_executable_found"], False)
        self.assertEqual(proof["tools"]["cantera_3_2"]["version"], "3.2.0")
        self.assertEqual(
            proof["tools"]["aate_icengines"]["version"], CTRL.AATE_REVISION
        )
        self.assertIs(proof["tools"]["historical_enginefoam"]["available"], False)
        self.assertIs(proof["tools"]["historical_enginefoam"]["passed"], False)

    def test_forbidden_geometry_names_and_revision_aliases_fail_closed(self):
        for value in (
            {"section": "oval-port"},
            {"shape": "ellipse"},
            {"geometry_artifact": "head-f39.step"},
            {"mesh": "F42-domain.msh"},
        ):
            with self.subTest(value=value), self.assertRaises(CTRL.ContractError):
                CTRL.reject_forbidden_geometry_names(value, "fixture")
        CTRL.reject_forbidden_geometry_names(
            {"geometry_artifact": "head-f46.step", "section": "circular"},
            "fixture",
        )
        CTRL.validate_functional_sections(
            {
                "functional_sections": [
                    {"shape": "circular", "justification": "interface cylindrique mesurée"}
                ]
            },
            "fixture",
        )
        with self.assertRaisesRegex(CTRL.ContractError, "non circulaire"):
            CTRL.validate_functional_sections(
                {
                    "functional_sections": [
                        {"shape": "rectangular", "justification": "fixture négative"}
                    ]
                },
                "fixture",
            )

    def test_synthetic_plan_exercises_selection_deadlines_and_budget_but_never_launches(self):
        plan = self.plan()
        self.assertEqual(plan["selected_offer"]["id"], 6000)
        self.assertEqual(plan["local_deadline_epoch"], plan["remote_deadline_epoch"])
        self.assertEqual(plan["local_deadline_epoch"], self.fixture["operator_deadline_epoch"])
        self.assertLessEqual(float(plan["projected_cumulative_spend_usd"]), 20.0)
        self.assertEqual(plan["reserved_network_transfer_usd"], "0.000000")
        self.assertFalse(plan["launch_authorized"])
        self.assertIn("fixture synthétique", " ".join(plan["blockers"]))
        self.assertTrue(all(value is False for value in plan["release_gates"].values()))

    def test_synthetic_fixture_is_rejected_without_explicit_test_flag(self):
        with self.assertRaisesRegex(CTRL.ContractError, "fixture synthétique"):
            CTRL.build_plan(
                self.contract,
                self.jobs,
                self.fixture["offers"],
                self.fixture["image_proof"],
                self.fixture["inventory_empty"],
                self.fixture["ledger_empty"],
                now_epoch=self.fixture["now_epoch"],
                operator_deadline_epoch=self.fixture["operator_deadline_epoch"],
                root=ROOT,
            )

    def test_image_tag_arm64_or_missing_smoke_is_rejected(self):
        for mutation in (
            {"immutable_ref": "ghcr.io/cluster2600/3dprinting993-cfd-cae-f46:latest"},
            {"architecture": "arm64"},
            {"runtime_smoke_verified": False},
        ):
            proof = deepcopy(self.fixture["image_proof"])
            proof.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(CTRL.ContractError):
                self.plan(image_proof=proof)

    def test_stale_offer_nonempty_inventory_and_exhausted_ledger_are_rejected(self):
        offers = deepcopy(self.fixture["offers"])
        offers["captured_at_epoch"] -= 1000
        with self.assertRaisesRegex(CTRL.ContractError, "périmé"):
            self.plan(offers=offers)
        inventory = deepcopy(self.fixture["inventory_empty"])
        inventory["instances"] = [{"id": 9, "label": "3dprinting993-f46-cfd-cae"}]
        with self.assertRaisesRegex(CTRL.ContractError, "non vide"):
            self.plan(inventory_before=inventory)
        ledger = deepcopy(self.fixture["ledger_empty"])
        ledger["entries"] = [{"charge_id": "old", "provider_charge_usd": 20, "finalized": True}]
        ledger["cumulative_spend_usd"] = 20
        with self.assertRaisesRegex(CTRL.ContractError, "déjà consommé"):
            self.plan(ledger=ledger)
        offers = deepcopy(self.fixture["offers"])
        offers["offers"][0]["inet_down_cost_usd_per_gb"] = 0.010001
        offers["offers"][1]["inet_down_cost_usd_per_gb"] = 0.010001
        with self.assertRaisesRegex(CTRL.ContractError, "aucune offre"):
            self.plan(offers=offers)

    def test_conservative_cost_uses_larger_of_elapsed_and_provider_charge(self):
        plan = self.plan()
        plan["classification"] = "production_controller_plan"
        plan["launch_authorized"] = True
        plan["selected_instance_id"] = 77
        plan["expected_label"] = "3dprinting993-f46-cfd-cae-" + "c" * 20
        ledger = {"classification": "production_wrapper_evidence", "entries": [], "cumulative_spend_usd": 0}
        instance = {
            "classification": "production_wrapper_evidence",
            "id": 77,
            "label": plan["expected_label"],
            "image": plan["expected_image"],
            "gpu": plan["selected_offer"]["gpu"],
            "gpu_ram_mb": plan["selected_offer"]["gpu_ram_mb"],
            "num_gpus": plan["selected_offer"]["num_gpus"],
            "gpu_fraction": plan["selected_offer"]["gpu_fraction"],
            "cpu_cores_effective": plan["selected_offer"]["cpu_cores_effective"],
            "cpu_ram_mb": plan["selected_offer"]["cpu_ram_mb"],
            "disk_space_gb": plan["selected_offer"]["disk_space_gb"],
            "machine_verification": "verified",
            "status": "running",
            "dph_total": float(plan["selected_dph_total_usd"]),
            "started_at_epoch": self.fixture["now_epoch"],
            "provider_charge_usd": 3.0,
        }
        result = CTRL.cost_check(
            self.contract,
            plan,
            ledger,
            instance,
            now_epoch=self.fixture["now_epoch"] + 3600,
        )
        self.assertEqual(result["current_conservative_charge_usd"], "3.000000")
        self.assertTrue(result["continue_compute"])
        instance["provider_charge_usd"] = 20.0
        stop = CTRL.cost_check(
            self.contract,
            plan,
            ledger,
            instance,
            now_epoch=self.fixture["now_epoch"] + 3600,
        )
        self.assertTrue(stop["cleanup_required"])

    def test_finalize_requires_destroy_and_empty_complete_inventory(self):
        plan = self.plan()
        plan["selected_instance_id"] = 77
        plan["expected_label"] = "3dprinting993-f46-cfd-cae-" + "c" * 20
        production = lambda value: {"classification": "production_wrapper_evidence", **value}
        states = production({"jobs": [{"id": key, "status": "cancelled"} for key in plan["job_ids"]]})
        ledger = production({
            "entries": [{"charge_id": "vast-77", "provider_charge_usd": 4.25, "finalized": True}],
            "cumulative_spend_usd": 4.25,
        })
        destroy = production({"instance_id": 77, "destroyed": True, "verified_absent": True})
        inventory = production({
            "pagination_complete": True,
            "label_filter": plan["expected_label_family"],
            "instances": [],
        })
        result = CTRL.finalize(self.contract, plan, states, ledger, destroy, inventory)
        self.assertTrue(result["cleanup_verified"])
        self.assertTrue(result["empty_final_inventory_verified"])
        self.assertFalse(result["simulation_validated"])
        inventory["instances"] = [{"id": 77, "label": plan["expected_label"]}]
        with self.assertRaisesRegex(CTRL.ContractError, "non vide"):
            CTRL.finalize(self.contract, plan, states, ledger, destroy, inventory)

    def test_current_cli_check_is_read_only(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(CONTROLLER_PATH),
                "--contract", str(CONTRACT_PATH),
                "--jobs", str(JOBS_PATH),
                "--root", str(ROOT),
                "check",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("live launch gates remain closed", completed.stdout)

    def test_preparation_report_is_offline_and_hash_bound(self):
        report = CTRL.preparation_report(self.contract, self.jobs, ROOT)
        self.assertEqual(report["status"], "controller_prepared_launch_blocked")
        self.assertEqual(report["spend_incurred_by_this_preparation_usd"], 0.0)
        self.assertFalse(report["vast_api_called_by_preparation"])
        self.assertFalse(report["instance_created"])
        self.assertEqual(report["planned_case_count"], 26)
        self.assertIs(report["exact_ICEEngineFoam_executable_found"], False)
        self.assertEqual(report["solver_authority_sha256"], CTRL.SOLVER_AUTHORITY_SHA256)
        self.assertTrue(all(value is False for value in report["release_gates"].values()))

    def test_shell_arms_cleanup_before_launch_and_has_two_ttls(self):
        source = RUNNER_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index("trap cleanup_instance_on_exit EXIT"), source.index("launch-vast-f46"))
        self.assertIn("NO-RETRIEVAL:${JOB_ID}:${INSTANCE_ID}:${EXPECTED_IMAGE}", source)
        self.assertIn("reconcile-f46-attempt", source)
        self.assertIn("--attempt-label", source)
        self.assertIn("--workflow-profile f46-cfd-cae-v1", source)
        self.assertIn("inventory-after.json", source)
        self.assertIn("cost-check", source)
        self.assertIn("local_deadline_epoch", CONTROLLER_PATH.read_text(encoding="utf-8"))
        self.assertIn("remote_deadline_epoch", CONTROLLER_PATH.read_text(encoding="utf-8"))
        check_instance = (ROOT / "deploy/vast/simready/check-instance.sh").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(check_instance.count("--expected-gpu-name"), 2)
        self.assertGreaterEqual(check_instance.count("--min-gpu-ram-mb"), 2)
        self.assertNotIn("security find", source)
        self.assertNotIn("raw secret", source.lower())


class F46WrapperTests(unittest.TestCase):
    def eligible_offer(self, **updates):
        result = {
            "id": 6000,
            "gpu_name": "RTX PRO 6000 WS",
            "gpu_ram": 98304,
            "gpu_frac": 1,
            "num_gpus": 1,
            "cpu_cores_effective": 32,
            "cpu_ram": 131072,
            "disk_space": 500,
            "dph_total": 2.4,
            "inet_up_cost": 0.0,
            "inet_down_cost": 0.0,
            "reliability": 0.999,
            "verified": True,
            "rentable": True,
            "rented": False,
            "type": "on-demand",
        }
        result.update(updates)
        return result

    def test_f46_offer_filter_is_exact_and_budgeted(self):
        self.assertTrue(VAST.f46_offer_eligible(self.eligible_offer()))
        self.assertTrue(
            VAST.f46_offer_eligible(
                self.eligible_offer(rentable_type=None, rental_type=None)
            )
        )
        self.assertTrue(VAST.f46_offer_eligible(self.eligible_offer(gpu_name="RTX A6000", gpu_ram=49152)))
        self.assertTrue(VAST.f46_offer_eligible(self.eligible_offer(inet_up_cost=0.01, inet_down_cost=0.01)))
        self.assertFalse(VAST.f46_offer_eligible(self.eligible_offer(gpu_name="RTX 4090")))
        self.assertFalse(VAST.f46_offer_eligible(self.eligible_offer(dph_total=2.51)))
        self.assertFalse(VAST.f46_offer_eligible(self.eligible_offer(type="interruptible")))
        self.assertFalse(VAST.f46_offer_eligible(self.eligible_offer(inet_down_cost=0.010001)))

    def test_existing_heavy_offer_listing_is_not_regressed(self):
        offer = self.eligible_offer()
        with mock.patch.object(VAST, "vast_request", return_value={"offers": [offer]}):
            self.assertEqual(VAST.get_heavy_offers("unused"), [offer])

    def test_f46_launch_rolls_back_if_postconditions_fail(self):
        offer = self.eligible_offer()
        image = "ghcr.io/cluster2600/3dprinting993-cfd-cae-f46@sha256:" + "a" * 64
        attempt_label = VAST.F46_LABEL + "-" + "c" * 20
        deadline = int(VAST.time.time()) + 3600
        with (
            mock.patch.object(VAST, "simready_launch_lock", return_value=mock.MagicMock(__enter__=mock.Mock(), __exit__=mock.Mock(return_value=False))),
            mock.patch.object(VAST, "require_no_f46_instance"),
            mock.patch.object(VAST, "ensure_local_ssh_registered"),
            mock.patch.object(VAST, "vast_request", return_value={"new_contract": 77}),
            mock.patch.object(VAST, "verify_single_f46_instance"),
            mock.patch.object(VAST, "verify_f46_contract", side_effect=VAST.SafeError("drift")),
            mock.patch.object(VAST, "reconcile_uncertain_f46_launch", return_value=77) as reconcile,
            mock.patch.object(VAST, "emit_f46_cleanup_attestation"),
        ):
            with self.assertRaisesRegex(VAST.SafeError, "drift"):
                VAST.launch_f46_offer(
                    "unused",
                    offer,
                    image,
                    deadline,
                    attempt_label=attempt_label,
                )
        reconcile.assert_called_once_with("unused", attempt_label, image)

    def test_f46_launch_uses_unique_attempt_label_and_remote_deadline(self):
        offer = self.eligible_offer()
        image = "ghcr.io/cluster2600/3dprinting993-cfd-cae-f46@sha256:" + "a" * 64
        attempt_label = VAST.F46_LABEL + "-" + "d" * 20
        deadline = int(VAST.time.time()) + 3600
        with (
            mock.patch.object(VAST, "simready_launch_lock", return_value=mock.MagicMock(__enter__=mock.Mock(), __exit__=mock.Mock(return_value=False))),
            mock.patch.object(VAST, "require_no_f46_instance"),
            mock.patch.object(VAST, "ensure_local_ssh_registered"),
            mock.patch.object(VAST, "vast_request", return_value={"new_contract": 77}) as request,
            mock.patch.object(VAST, "verify_single_f46_instance") as verify_single,
            mock.patch.object(VAST, "verify_f46_contract") as verify_contract,
            mock.patch("sys.stdout"),
        ):
            self.assertEqual(
                VAST.launch_f46_offer(
                    "unused",
                    offer,
                    image,
                    deadline,
                    attempt_label=attempt_label,
                ),
                0,
            )
        payload = request.call_args.kwargs["payload"]
        self.assertEqual(payload["label"], attempt_label)
        self.assertEqual(
            payload["onstart"], f"f46-vast-onstart --deadline-epoch {deadline}"
        )
        self.assertEqual(payload["env"], {})
        verify_single.assert_called_once_with("unused", 77, attempt_label)
        verify_contract.assert_called_once_with(
            "unused", 77, attempt_label, image, offer
        )

    def test_f46_reconciliation_destroys_only_exact_attempt_and_digest(self):
        image = "ghcr.io/cluster2600/3dprinting993-cfd-cae-f46@sha256:" + "a" * 64
        attempt_label = VAST.F46_LABEL + "-" + "f" * 20
        matching = {
            "id": 77,
            "label": attempt_label,
            "image_uuid": image,
        }
        unrelated = {
            "id": 78,
            "label": VAST.F46_LABEL + "-" + "e" * 20,
            "image_uuid": image,
        }
        with (
            mock.patch.object(
                VAST, "strict_instance_inventory", return_value=[matching, unrelated]
            ),
            mock.patch.object(VAST, "destroy_instance_verified") as destroy,
        ):
            self.assertEqual(
                VAST.reconcile_uncertain_f46_launch(
                    "unused", attempt_label, image
                ),
                77,
            )
        destroy.assert_called_once_with(
            "unused", 77, expected_label=attempt_label, expected_image=image
        )

    def test_ghcr_f46_command_never_forwards_github_credential(self):
        image = "ghcr.io/cluster2600/3dprinting993-cfd-cae-f46@sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "openbao-vastai"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o700)
            with mock.patch.object(GHCR, "VAST_WRAPPER", executable), mock.patch.object(
                GHCR.subprocess, "run", return_value=mock.Mock(returncode=0)
            ) as run:
                self.assertEqual(
                    GHCR.run_vast(
                        [
                            "launch-vast-f46",
                            "6000",
                            image,
                            "2000003600",
                            "--attempt-label",
                            "3dprinting993-f46-cfd-cae-" + "e" * 20,
                        ]
                    ),
                    0,
                )
        self.assertEqual(
            run.call_args.args[0],
            [
                str(executable),
                "launch-f46",
                "6000",
                image,
                "2000003600",
                "--attempt-label",
                "3dprinting993-f46-cfd-cae-" + "e" * 20,
            ],
        )

    def test_ghcr_proof_binds_index_and_single_linux_amd64_manifest(self):
        index_digest = "sha256:" + "a" * 64
        platform_digest = "sha256:" + "b" * 64
        image = "ghcr.io/cluster2600/3dprinting993-cfd-cae-f46@" + index_digest
        replies = [
            ({"token": "registry-session"}, {}),
            (
                {
                    "manifests": [
                        {
                            "digest": platform_digest,
                            "platform": {"os": "linux", "architecture": "amd64"},
                        }
                    ]
                },
                {"docker-content-digest": index_digest},
            ),
            ({}, {"docker-content-digest": platform_digest}),
        ]
        with mock.patch.object(GHCR, "request", side_effect=replies):
            proof = GHCR.f46_registry_proof("cluster2600", "not-exposed", image)
        self.assertEqual(proof["immutable_ref"], image)
        self.assertEqual(proof["platform_manifest_digest"], platform_digest)
        self.assertTrue(proof["registry_digest_verified"])
        self.assertFalse(proof["runtime_smoke_verified"])


if __name__ == "__main__":
    unittest.main()
