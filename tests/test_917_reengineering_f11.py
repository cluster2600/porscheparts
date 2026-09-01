import hashlib
import importlib.util
import json
import copy
import tempfile
import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/build_reengineering_readiness_f11.py"
CONTRACT = ROOT / "twins/reference-917-engine/reengineering-contract-f11.json"
INPUTS = ROOT / "twins/reference-917-engine/engineering-inputs-f11.template.json"
ASSET_ID = "porsche-917-engine-reengineering-f11"
BOTH_VARIANTS = ["type_912_4_5_na", "917_30_turbo_5374"]


def load_module():
    spec = importlib.util.spec_from_file_location("reengineering_917_f11", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class Reengineering917F11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.inputs = json.loads(INPUTS.read_text(encoding="utf-8"))

    def build_artifact_fixture(self, root: Path, contract: dict | None = None) -> None:
        contract = contract or self.contract
        expected_hash = contract["asset"]["source_scan_sha256"]
        write_json(
            root / "work/917-engine/vast-output/reports/mesh-preparation.json",
            {
                "source_sha256": expected_hash,
                "identity": "Porsche 917 suggested by filename; not independently verified",
                "units": "OBJ units; millimetres plausible but unconfirmed",
                "topology": {"source": {"boundary_edges": 101809, "watertight": False}},
            },
        )
        write_json(
            root / "work/917-engine/vast-output/reports/output-verification.json",
            {"status": "passed"},
        )
        write_json(
            root
            / "work/917-engine/vast-output/cfd/external-cooling/cfd-validation.json",
            {
                "status": "blocked_mesh_quality",
                "solver_allowed": False,
                "failed_mesh_checks": 2,
                "duplicate_faces": 21,
                "non_consecutive_shared_point_faces": 170,
                "scope": "external geometry mesh only; no boundary conditions or flow solution",
            },
        )
        variants = [
            {"variant_id": "type_912_4_5_na"},
            {"variant_id": "917_30_turbo_5374"},
        ]
        write_json(
            root / "work/917-variant-geometry-f10/variant-config-generation-report.json",
            {
                "status": "passed",
                "variants": variants,
                "manufacturing_geometry_ready": False,
                "physical_kinematics_ready": False,
            },
        )
        write_json(
            root / "work/917-variant-geometry-f10/run-complete.json",
            {
                "status": "passed",
                "variant_ids": [item["variant_id"] for item in variants],
                "manufacturing_geometry_ready": False,
                "physical_kinematics_ready": False,
            },
        )
        write_json(
            root / "work/917-test-bench/virtual-start-report.json",
            {
                "status": "stopped_at_preflight_as_designed",
                "highest_completed_stage": "kinematic_dry_crank_visualization_only",
                "fired_run_executed": False,
            },
        )

    def evidence(self, root: Path, name: str, content: str = "evidence") -> dict:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def typed_evidence(
        self,
        root: Path,
        *,
        evidence_id: str,
        evidence_kind: str,
        claim_id: str,
        variant_ids: list[str],
        result_extra: dict | None = None,
        signature: dict | None = None,
        artifact_path: Path | None = None,
        artifact_role: str = "evidence",
        asset_id: str = ASSET_ID,
    ) -> dict:
        if artifact_path is None:
            artifact_path = root / "artifacts" / f"{evidence_id}.dat"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(f"artifact:{evidence_id}", encoding="utf-8")
        result = {
            "status": "passed",
            "measured_or_simulated": "measured",
            "acceptance_criteria": ["declared criterion passed"],
        }
        if result_extra:
            result.update(result_extra)
        manifest = {
            "schema_version": "1.0.0",
            "evidence_id": evidence_id,
            "evidence_kind": evidence_kind,
            "claim_id": claim_id,
            "asset_id": asset_id,
            "variant_ids": variant_ids,
            "revision": "test-r1",
            "issued_at": "2026-09-01T00:00:00Z",
            "producer": {
                "name": "Test laboratory",
                "role": "independent validation",
                "organization": "Test organization",
            },
            "method": {
                "name": "controlled test fixture",
                "description": "Structured regression evidence generated in a temporary directory.",
            },
            "artifacts": [
                {
                    "path": str(artifact_path),
                    "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                    "role": artifact_role,
                }
            ],
            "result": result,
        }
        if signature is not None:
            manifest["signature"] = signature
        manifest_path = root / "manifests" / f"{evidence_id}-{claim_id.replace('.', '-')}.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(manifest_path, manifest)
        return {
            "path": str(manifest_path),
            "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        }

    def source_integrity_fixture(
        self, root: Path
    ) -> tuple[dict, Path, Path, dict]:
        scan_path = root / "private" / "917-engine.obj"
        scan_path.parent.mkdir(parents=True, exist_ok=True)
        scan_path.write_bytes(b"private 917 scan fixture\n")
        contract = copy.deepcopy(self.contract)
        contract["asset"]["source_scan_sha256"] = hashlib.sha256(
            scan_path.read_bytes()
        ).hexdigest()
        contract_path = root / "reengineering-contract-f11.json"
        write_json(contract_path, contract)
        self.build_artifact_fixture(root, contract)
        inputs = copy.deepcopy(self.inputs)
        inputs["source_scan"] = self.typed_evidence(
            root,
            evidence_id="EV-SOURCE-SCAN",
            evidence_kind="source_scan_integrity",
            claim_id="source_scan.integrity",
            variant_ids=["917_unspecified"],
            artifact_path=scan_path,
            artifact_role="raw_obj_scan",
        )
        return inputs, contract_path, scan_path, contract

    def full_release_fixture(self, root: Path) -> tuple[dict, Path]:
        inputs, contract_path, _, contract = self.source_integrity_fixture(root)
        sequence = 0

        def manifest(
            claim_id: str,
            evidence_kind: str,
            *,
            variant_ids: list[str] | None = None,
            result_extra: dict | None = None,
            signature: dict | None = None,
        ) -> dict:
            nonlocal sequence
            sequence += 1
            return self.typed_evidence(
                root,
                evidence_id=f"EV-{sequence:03d}",
                evidence_kind=evidence_kind,
                claim_id=claim_id,
                variant_ids=variant_ids or BOTH_VARIANTS,
                result_extra=result_extra,
                signature=signature,
            )

        inputs["variant_selection"]["selected_variant_ids"] = BOTH_VARIANTS
        inputs["variant_selection"]["selection_basis"] = manifest(
            "variant_selection.selection_basis", "variant_selection_report"
        )
        scale = inputs["source_identity_and_scale"]
        scale["identity_report"] = manifest(
            "source_identity_and_scale.identity_report",
            "identity_metrology_report",
            variant_ids=["917_unspecified"],
        )
        scale["mm_per_obj_unit"] = 1.0
        for index, control in enumerate(scale["scale_controls"], start=1):
            control.update(
                scan_obj_units=float(index * 100),
                physical_mm=float(index * 100),
                uncertainty_mm=0.05,
                scan_region=f"independent-region-{index}",
                evidence=manifest(
                    f"source_identity_and_scale.scale_controls.{control['feature_id']}",
                    "scale_control_metrology_report",
                    variant_ids=["917_unspecified"],
                ),
            )

        for key in inputs["measured_head_geometry"]:
            inputs["measured_head_geometry"][key] = manifest(
                f"measured_head_geometry.{key}", "measured_head_geometry_report"
            )
        for branch_name, branch in inputs["architecture_geometry"].items():
            for key in branch:
                if key != "valves_per_cylinder":
                    branch[key] = manifest(
                        f"architecture_geometry.{branch_name}.{key}",
                        "parametric_geometry_report",
                    )

        material = inputs["material_characterization"]
        material["selected_head_material_id"] = contract["head_material_candidates"][0]["id"]
        for key in material:
            if key != "selected_head_material_id":
                material[key] = manifest(
                    f"material_characterization.{key}",
                    "material_characterization_report",
                )

        group_kinds = {
            "operating_loads": "operating_load_report",
            "valvetrain_inputs": "valvetrain_measurement_report",
            "turbo_inputs": "turbo_characterization_report",
            "reference_solver_evidence": "reference_solver_validation_report",
            "experimental_correlation": "experimental_correlation_report",
            "manufacturing_qualification": "manufacturing_qualification_report",
            "prototype_validation": "prototype_validation_report",
            "engine_bench_validation": "engine_bench_test_report",
        }
        solver_validation = {
            "validation": {
                "solver_name": "reference-solver",
                "solver_version": "test-version",
                "model_family": "declared-reference-model",
                "converged": True,
                "mesh_independence_passed": True,
                "balance_tolerance_passed": True,
                "boundary_conditions_defined": True,
            }
        }
        for group, kind in group_kinds.items():
            for key in inputs[group]:
                result_extra = None
                if group == "reference_solver_evidence":
                    result_extra = solver_validation
                elif group == "engine_bench_validation":
                    result_extra = {
                        "validation": {
                            "test_id": f"BENCH-{key}",
                            "instrumentation_calibrated": True,
                            "shutdown_system_verified": True,
                            "data_complete": True,
                            "acceptance_met": True,
                        }
                    }
                variant_ids = None
                if group == "turbo_inputs" or (
                    group == "engine_bench_validation" and key == "fired_turbo_test_results"
                ):
                    variant_ids = ["917_30_turbo_5374"]
                elif group == "engine_bench_validation" and key == "fired_NA_test_results":
                    variant_ids = ["type_912_4_5_na"]
                inputs[group][key] = manifest(
                    f"{group}.{key}",
                    kind,
                    variant_ids=variant_ids,
                    result_extra=result_extra,
                )

        inputs["professional_review"].update(
            reviewer="Independent engine engineer",
            scope="F6 manufacturing, engine test and performance release",
            signed_report=manifest(
                "professional_review.signed_report",
                "signed_professional_review",
                result_extra={
                    "covered_levels": ["F6_instrumented_engine_bench"],
                    "covered_releases": [
                        "manufacturing",
                        "metal_print",
                        "engine_start",
                        "performance_claim_1600_hp",
                    ],
                },
                signature={
                    "status": "verified",
                    "type": "detached",
                    "key_id": "independent-review-test-key",
                },
            ),
        )
        return inputs, contract_path

    @staticmethod
    def gates(report: dict) -> dict[str, dict]:
        return {item["id"]: item for item in report["gates"]}

    @staticmethod
    def release_flags(report: dict) -> tuple[bool, bool, bool, bool]:
        release = report["release"]
        return (
            release["manufacturing_authorized"],
            release["metal_print_authorized"],
            release["engine_start_authorized"],
            release["performance_claim_1600_hp_authorized"],
        )

    def test_empty_inputs_fail_closed_before_source_integrity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.build_artifact_fixture(root)
            input_path = root / "engineering-inputs.json"
            write_json(input_path, self.inputs)
            report = self.module.evaluate(root, CONTRACT, input_path)

        self.assertEqual(report["report_status"], "passed")
        self.assertEqual(report["highest_verified_level"], "unverified")
        self.assertEqual(report["visual_model_level"], "F10_separate_variant_hypothesis_stages")
        self.assertEqual(self.gates(report)["scan_source_integrity"]["status"], "blocked")
        self.assertEqual(
            report["current_artifact_observations"]["external_cooling_cfd"]["status"],
            "blocked_mesh_quality",
        )
        self.assertFalse(report["release"]["manufacturing_authorized"])
        self.assertFalse(report["release"]["metal_print_authorized"])
        self.assertFalse(report["release"]["engine_start_authorized"])
        self.assertFalse(report["release"]["performance_claim_1600_hp_authorized"])
        self.assertTrue(
            all(item["status"] == "blocked" for item in report["physics_model_readiness"])
        )

    def test_contract_excludes_non_917_head_geometry(self):
        asset = self.contract["asset"]
        excluded = self.contract["scope_boundaries"]["not_accepted_as_917_head_geometry"]

        self.assertFalse(asset["head_geometry_in_source_scan"])
        self.assertIn("scan de culasse 935", excluded)
        self.assertIn("proxies de soupapes 993", excluded)

    def test_two_and_four_valve_branches_are_independent(self):
        variants = {item["id"]: item for item in self.contract["architecture_variants"]}

        self.assertEqual(variants["917_2v_baseline"]["valves_per_cylinder"], 2)
        self.assertEqual(variants["917_2v_baseline"]["engine_valve_count"], 24)
        self.assertEqual(variants["917_4v_concept"]["valves_per_cylinder"], 4)
        self.assertEqual(variants["917_4v_concept"]["engine_valve_count"], 48)
        self.assertIn("independante", variants["917_4v_concept"]["role"])

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = json.loads(json.dumps(self.inputs["architecture_geometry"]))
            for index, key in enumerate((
                "parametric_cad",
                "chamber_ports_seats_and_guides",
                "valve_layout_lift_and_actuation",
                "clearance_and_tolerance_report",
            ), start=1):
                data["baseline_2v"][key] = self.typed_evidence(
                    root,
                    evidence_id=f"EV-BASELINE-{index}",
                    evidence_kind="parametric_geometry_report",
                    claim_id=f"architecture_geometry.baseline_2v.{key}",
                    variant_ids=BOTH_VARIANTS,
                )
            registry = self.module.EvidenceRegistry()
            baseline_ready, _ = self.module.architecture_geometry_ready(
                data, "baseline_2v", 2, root, registry
            )
            concept_ready, _ = self.module.architecture_geometry_ready(
                data, "concept_4v", 4, root, registry
            )

        self.assertTrue(baseline_ready)
        self.assertFalse(concept_ready)

    def test_component_routes_keep_valves_and_springs_out_of_lpbf(self):
        strategy = self.contract["component_strategy"]

        self.assertIn("not_additive", strategy["intake_valve"]["manufacturing"])
        self.assertIn("not_additive", strategy["exhaust_valve"]["manufacturing"])
        self.assertIn("not_additive", strategy["valve_spring"]["manufacturing"])
        self.assertIn("LPBF", strategy["individual_head"]["manufacturing"])

    def test_three_consistent_controls_validate_only_scale_gate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs, contract_path, _, _ = self.source_integrity_fixture(root)
            inputs["source_identity_and_scale"]["identity_report"] = self.typed_evidence(
                root,
                evidence_id="EV-IDENTITY",
                evidence_kind="identity_metrology_report",
                claim_id="source_identity_and_scale.identity_report",
                variant_ids=["917_unspecified"],
            )
            inputs["source_identity_and_scale"]["mm_per_obj_unit"] = 1.0
            for index, control in enumerate(
                inputs["source_identity_and_scale"]["scale_controls"], start=1
            ):
                control["scan_obj_units"] = float(index * 100)
                control["physical_mm"] = float(index * 100)
                control["uncertainty_mm"] = 0.05
                control["scan_region"] = f"independent-region-{index}"
                control["evidence"] = self.typed_evidence(
                    root,
                    evidence_id=f"EV-SCALE-{index}",
                    evidence_kind="scale_control_metrology_report",
                    claim_id=(
                        "source_identity_and_scale.scale_controls."
                        f"{control['feature_id']}"
                    ),
                    variant_ids=["917_unspecified"],
                )
            input_path = root / "engineering-inputs.json"
            write_json(input_path, inputs)
            report = self.module.evaluate(root, contract_path, input_path)

        gates = {item["id"]: item for item in report["gates"]}
        self.assertEqual(gates["source_identity_and_scale"]["status"], "passed")
        self.assertEqual(report["highest_verified_level"], "F0_source_integrity")
        self.assertFalse(report["release"]["manufacturing_authorized"])

    def test_physicsnemo_is_surrogate_only_and_training_is_blocked(self):
        policy = self.contract["physicsnemo_surrogate_policy"]
        families = {item["id"] for item in policy["candidate_families"]}

        self.assertIn("surrogate_only", policy["role"])
        self.assertEqual(
            families,
            {"DoMINO", "FIGConvNet", "Transolver_or_GeoTransolver", "MeshGraphNet"},
        )
        self.assertFalse(policy["current_training_authorized"])

    def test_tampered_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = self.evidence(root, "measurement.json", "first")
            (root / "measurement.json").write_text("changed", encoding="utf-8")
            ready, finding = self.module.evidence_ready(evidence, root)

        self.assertFalse(ready)
        self.assertIn("mismatch", finding)

    def test_one_arbitrary_file_reused_for_every_claim_cannot_advance_beyond_f0(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs, contract_path, _, contract = self.source_integrity_fixture(root)
            arbitrary = self.evidence(root, "one-arbitrary-file.txt")

            inputs["variant_selection"]["selected_variant_ids"] = BOTH_VARIANTS
            inputs["variant_selection"]["selection_basis"] = arbitrary
            scale = inputs["source_identity_and_scale"]
            scale["identity_report"] = arbitrary
            scale["mm_per_obj_unit"] = 1.0
            for index, control in enumerate(scale["scale_controls"], start=1):
                control.update(
                    scan_obj_units=float(index * 100),
                    physical_mm=float(index * 100),
                    uncertainty_mm=0.05,
                    evidence=arbitrary,
                )
            for key in inputs["measured_head_geometry"]:
                inputs["measured_head_geometry"][key] = arbitrary
            for branch in inputs["architecture_geometry"].values():
                for key in branch:
                    if key != "valves_per_cylinder":
                        branch[key] = arbitrary
            material = inputs["material_characterization"]
            material["selected_head_material_id"] = contract["head_material_candidates"][0]["id"]
            for key in material:
                if key != "selected_head_material_id":
                    material[key] = arbitrary
            for group in (
                "operating_loads",
                "valvetrain_inputs",
                "turbo_inputs",
                "reference_solver_evidence",
                "experimental_correlation",
                "manufacturing_qualification",
                "prototype_validation",
                "engine_bench_validation",
            ):
                for key in inputs[group]:
                    inputs[group][key] = arbitrary
            inputs["professional_review"].update(
                reviewer="Unverified reviewer",
                scope="Everything",
                signed_report=arbitrary,
            )
            input_path = root / "engineering-inputs.json"
            write_json(input_path, inputs)
            report = self.module.evaluate(root, contract_path, input_path)

        self.assertEqual(report["highest_verified_level"], "F0_source_integrity")
        self.assertTrue(
            all(item["status"] == "blocked" for item in report["physics_model_readiness"])
        )
        self.assertFalse(any(self.release_flags(report)))

    def test_f0_rehashes_the_actual_raw_scan_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs, contract_path, scan_path, _ = self.source_integrity_fixture(root)
            input_path = root / "engineering-inputs.json"
            write_json(input_path, inputs)
            initial = self.module.evaluate(root, contract_path, input_path)

            scan_path.write_bytes(b"tampered after manifest creation\n")
            tampered = self.module.evaluate(root, contract_path, input_path)

        self.assertEqual(initial["highest_verified_level"], "F0_source_integrity")
        self.assertEqual(self.gates(initial)["scan_source_integrity"]["status"], "passed")
        self.assertNotEqual(tampered["highest_verified_level"], "F0_source_integrity")
        self.assertEqual(self.gates(tampered)["scan_source_integrity"]["status"], "blocked")
        self.assertFalse(any(self.release_flags(tampered)))

    def test_manifests_require_exact_kind_claim_asset_and_unique_evidence_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs, contract_path, _, _ = self.source_integrity_fixture(root)
            inputs["variant_selection"]["selected_variant_ids"] = BOTH_VARIANTS

            for field, incorrect in (
                ("evidence_kind", "generic_document"),
                ("claim_id", "variant_selection.unrelated_claim"),
                ("asset_id", "another-engine"),
            ):
                with self.subTest(field=field):
                    reference = self.typed_evidence(
                        root,
                        evidence_id=f"EV-WRONG-{field}",
                        evidence_kind="variant_selection_report",
                        claim_id="variant_selection.selection_basis",
                        variant_ids=BOTH_VARIANTS,
                        asset_id=ASSET_ID,
                    )
                    manifest_path = Path(reference["path"])
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest[field] = incorrect
                    write_json(manifest_path, manifest)
                    reference["sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                    candidate = copy.deepcopy(inputs)
                    candidate["variant_selection"]["selection_basis"] = reference
                    input_path = root / f"inputs-wrong-{field}.json"
                    write_json(input_path, candidate)
                    report = self.module.evaluate(root, contract_path, input_path)
                    self.assertEqual(
                        self.gates(report)["variant_selection"]["status"], "blocked"
                    )

            duplicate_id = "EV-DUPLICATE-ID"
            selection = self.typed_evidence(
                root,
                evidence_id=duplicate_id,
                evidence_kind="variant_selection_report",
                claim_id="variant_selection.selection_basis",
                variant_ids=BOTH_VARIANTS,
            )
            review = self.typed_evidence(
                root,
                evidence_id=duplicate_id,
                evidence_kind="signed_professional_review",
                claim_id="professional_review.signed_report",
                variant_ids=BOTH_VARIANTS,
                result_extra={"covered_levels": ["F6_instrumented_engine_bench"]},
                signature={"status": "verified", "type": "detached", "key_id": "test-key"},
            )
            inputs["variant_selection"]["selection_basis"] = selection
            inputs["professional_review"].update(
                reviewer="Independent engineer",
                scope="F6 release review",
                signed_report=review,
            )
            input_path = root / "inputs-duplicate-id.json"
            write_json(input_path, inputs)
            duplicate_report = self.module.evaluate(root, contract_path, input_path)

        duplicate_gates = self.gates(duplicate_report)
        self.assertFalse(
            duplicate_gates["variant_selection"]["status"] == "passed"
            and duplicate_gates["professional_review"]["status"] == "passed"
        )
        self.assertFalse(any(self.release_flags(duplicate_report)))

    def test_f6_requires_structured_solver_bench_and_signed_review_manifests(self):
        def evaluate_fixture(root: Path, mutation: str | None = None) -> dict:
            inputs, contract_path = self.full_release_fixture(root)
            if mutation == "solver":
                reference = inputs["reference_solver_evidence"][
                    "solver_names_versions_and_models"
                ]
                manifest_path = Path(reference["path"])
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                payload["result"].pop("validation")
                write_json(manifest_path, payload)
                reference["sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            elif mutation == "bench":
                reference = inputs["engine_bench_validation"]["fired_turbo_test_results"]
                manifest_path = Path(reference["path"])
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                payload["result"]["validation"]["instrumentation_calibrated"] = False
                write_json(manifest_path, payload)
                reference["sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            elif mutation == "review":
                reference = inputs["professional_review"]["signed_report"]
                manifest_path = Path(reference["path"])
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                payload["signature"]["status"] = "unverified"
                write_json(manifest_path, payload)
                reference["sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            input_path = root / "engineering-inputs.json"
            write_json(input_path, inputs)
            return self.module.evaluate(root, contract_path, input_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            released = evaluate_fixture(base / "released")
            no_solver_validation = evaluate_fixture(base / "no-solver-validation", "solver")
            no_bench_validation = evaluate_fixture(base / "no-bench-validation", "bench")
            unsigned_review = evaluate_fixture(base / "unsigned-review", "review")

        self.assertEqual(released["highest_verified_level"], "F6_instrumented_engine_bench")
        self.assertFalse(any(self.release_flags(released)))

        self.assertEqual(
            self.gates(no_solver_validation)["reference_solver_evidence"]["status"],
            "blocked",
        )
        self.assertEqual(
            self.gates(no_bench_validation)["engine_bench_validation"]["status"],
            "blocked",
        )
        self.assertEqual(
            self.gates(unsigned_review)["professional_review"]["status"], "blocked"
        )
        for report in (no_solver_validation, no_bench_validation, unsigned_review):
            self.assertFalse(any(self.release_flags(report)))

    def test_self_declared_manifests_are_not_a_release_authority(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs, contract_path = self.full_release_fixture(root)
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            input_path = root / "engineering-inputs.json"
            write_json(input_path, inputs)
            report = self.module.evaluate(root, contract_path, input_path)

        authority = contract["release_authority"]
        self.assertIs(authority["verifier_implemented"], False)
        self.assertEqual(authority["trusted_key_ids"], [])
        self.assertIs(authority["solver_result_parsers_qualified"], False)
        self.assertIs(authority["bench_result_parsers_qualified"], False)
        self.assertIs(authority["manufacturing_release_enabled"], False)
        self.assertIs(authority["engine_start_release_enabled"], False)
        self.assertEqual(report["highest_verified_level"], "F6_instrumented_engine_bench")
        self.assertFalse(any(self.release_flags(report)))

    def test_self_declared_f6_does_not_authorize_physicsnemo_training(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs, contract_path = self.full_release_fixture(root)
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            input_path = root / "engineering-inputs.json"
            write_json(input_path, inputs)
            report = self.module.evaluate(root, contract_path, input_path)

        policy = contract["physicsnemo_surrogate_policy"]
        self.assertIs(policy["current_training_authorized"], False)
        self.assertIs(policy["dataset_parser_qualified"], False)
        self.assertIs(policy["holdout_validator_qualified"], False)
        self.assertIs(policy["ood_guard_qualified"], False)
        self.assertIs(
            contract["release_authority"]["solver_result_parsers_qualified"], False
        )
        self.assertEqual(report["highest_verified_level"], "F6_instrumented_engine_bench")
        self.assertIs(report["physicsnemo"]["training_authorized"], False)

    def test_contract_flags_alone_cannot_activate_runtime_release_or_training(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs, contract_path = self.full_release_fixture(root)
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            authority = contract["release_authority"]
            authority.update(
                verifier_implemented=True,
                trusted_key_ids=["independent-review-test-key"],
                solver_result_parsers_qualified=True,
                bench_result_parsers_qualified=True,
                manufacturing_release_enabled=True,
                engine_start_release_enabled=True,
            )
            physicsnemo = contract["physicsnemo_surrogate_policy"]
            physicsnemo.update(
                current_training_authorized=True,
                dataset_parser_qualified=True,
                holdout_validator_qualified=True,
                ood_guard_qualified=True,
            )
            write_json(contract_path, contract)
            input_path = root / "engineering-inputs.json"
            write_json(input_path, inputs)
            report = self.module.evaluate(root, contract_path, input_path)

        self.assertEqual(report["highest_verified_level"], "F6_instrumented_engine_bench")
        self.assertIs(report["release"]["external_release_authority_ready"], False)
        self.assertFalse(any(self.release_flags(report)))
        self.assertIs(report["physicsnemo"]["training_authorized"], False)


if __name__ == "__main__":
    unittest.main()
