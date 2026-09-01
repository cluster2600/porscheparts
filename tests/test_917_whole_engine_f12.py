import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "twins/reference-917-engine/source/build_whole_engine_readiness_f12.py"
)
CONTRACT = ROOT / "twins/reference-917-engine/whole-engine-reengineering-f12.json"
VISUAL = ROOT / "twins/reference-917-engine/complete-engine-f1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("whole_engine_917_f12", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class WholeEngine917F12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.visual = json.loads(VISUAL.read_text(encoding="utf-8"))

    def evaluate_contract(self, contract: dict) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            contract_path = Path(temp_dir) / "whole-engine-f12.json"
            write_json(contract_path, contract)
            return self.module.evaluate(ROOT, contract_path, VISUAL)

    def typed_evidence(
        self,
        root: Path,
        *,
        family_id: str,
        workstream_id: str,
        evidence_id: str | None = None,
        artifact_path: Path | None = None,
    ) -> dict:
        rule = self.module.WORKSTREAM_RULES[workstream_id]
        family = next(
            item for item in self.contract["family_registry"] if item["id"] == family_id
        )
        variants = (
            list(self.module.TURBO_VARIANT)
            if family["visual_variant"] == "917_30_only"
            else list(self.module.ALL_VARIANTS)
        )
        if artifact_path is None:
            artifact_path = root / "artifacts" / f"{family_id}-{workstream_id}.dat"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                f"artifact:{family_id}:{workstream_id}", encoding="utf-8"
            )
        manifest = {
            "schema_version": "1.0.0",
            "evidence_id": evidence_id or f"EV-{family_id}-{workstream_id}",
            "evidence_kind": rule["evidence_kind"],
            "claim_id": f"family.{family_id}.{workstream_id}",
            "asset_id": self.module.ASSET_ID,
            "family_id": family_id,
            "workstream_id": workstream_id,
            "variant_ids": variants,
            "revision": "test-r1",
            "issued_at": "2026-09-02T00:00:00Z",
            "producer": {
                "name": "Test laboratory",
                "role": "independent test fixture",
                "organization": "Test organization",
            },
            "method": {
                "name": "controlled fixture",
                "description": "Unique typed evidence used only by this regression claim.",
            },
            "artifacts": [
                {
                    "path": str(artifact_path),
                    "sha256": file_sha256(artifact_path),
                    "role": workstream_id,
                }
            ],
            "result": {
                "status": "passed",
                "measured_or_simulated": "measured",
                "acceptance_criteria": ["test criterion passed"],
            },
        }
        manifest_path = root / "manifests" / f"{family_id}-{workstream_id}.json"
        write_json(manifest_path, manifest)
        return {"path": str(manifest_path), "sha256": file_sha256(manifest_path)}

    def mark_family_evidence_package_ready(
        self, contract: dict, root: Path, family: dict
    ) -> None:
        family.update(
            provenance_status="verified",
            parametric_geometry_status="validated",
            parametric_master=f"masters/{family['id']}.step",
            interfaces_tolerances_status="validated",
            datum_scheme=f"datums/{family['id']}.json",
            tolerance_stack_report=f"reports/{family['id']}-tolerances.json",
            material_mass_status="characterized",
            material_specification=f"SPEC-{family['id']}",
            mass_kg=1.0,
            manufacturing_status="qualified",
            manufacturing_plan=f"plans/{family['id']}-manufacturing.json",
            physics_status="validated_and_correlated",
            reference_solver_validated=True,
            physical_correlation_validated=True,
            test_status="passed",
            test_plan=f"tests/{family['id']}.json",
        )
        family["workstream_evidence_refs"] = {
            workstream_id: [
                self.typed_evidence(
                    root,
                    family_id=family["id"],
                    workstream_id=workstream_id,
                )
            ]
            for workstream_id in self.module.WORKSTREAM_RULES
        }
        family["release"] = {
            "status": "released",
            "functional": True,
            "printable": True,
            "assembly": True,
        }

    def test_visual_snapshot_is_exact_but_not_a_real_bom(self):
        report = self.module.evaluate(ROOT, CONTRACT, VISUAL)

        self.assertEqual(report["report_status"], "passed")
        self.assertEqual(report["bom_assessment"]["family_count"], 31)
        self.assertEqual(report["bom_assessment"]["na_visual_instance_count"], 271)
        self.assertEqual(
            report["bom_assessment"]["turbo_only_visual_instance_delta"], 4
        )
        self.assertEqual(report["bom_assessment"]["turbo_visual_instance_count"], 275)
        self.assertIsNone(report["bom_assessment"]["real_bom_item_count"])
        self.assertFalse(report["bom_assessment"]["real_bom_complete"])
        self.assertEqual(
            report["bom_assessment"]["status"], "visual_snapshot_not_real_bom"
        )
        self.assertGreater(
            report["bom_assessment"]["unbounded_backlog_category_count"], 0
        )

    def test_every_visual_family_remains_blocked_for_function_and_print(self):
        report = self.module.evaluate(ROOT, CONTRACT, VISUAL)

        self.assertEqual(len(report["families"]), 31)
        self.assertTrue(
            all(not item["functional_release_authorized"] for item in report["families"])
        )
        self.assertTrue(
            all(not item["print_release_authorized"] for item in report["families"])
        )
        self.assertEqual(
            report["family_gap_summary"]["blocked_family_count"], 31
        )
        self.assertEqual(
            report["family_gap_summary"]["families_with_functional_release"], 0
        )
        self.assertEqual(
            report["family_gap_summary"]["families_with_print_release"], 0
        )

    def test_declared_release_flags_cannot_promote_proxy_or_scan(self):
        contract = copy.deepcopy(self.contract)
        for family in contract["family_registry"]:
            family["release"] = {
                "status": "released",
                "functional": True,
                "printable": True,
                "assembly": True,
            }

        report = self.evaluate_contract(contract)

        self.assertEqual(report["report_status"], "passed")
        self.assertTrue(
            all(item["release_claim_conflict"] for item in report["families"])
        )
        self.assertTrue(
            all(not item["functional_release_authorized"] for item in report["families"])
        )
        self.assertTrue(
            all(not item["print_release_authorized"] for item in report["families"])
        )
        self.assertFalse(report["release"]["whole_engine_functional_authorized"])

    def test_backlog_has_no_invented_quantities_or_dimensions(self):
        backlog = self.contract["unbounded_bom_backlog"]

        self.assertTrue(backlog)
        self.assertTrue(all(item["quantity"] is None for item in backlog))
        self.assertTrue(all(item["dimensions"] is None for item in backlog))
        ids = {item["id"] for item in backlog}
        self.assertTrue(
            {
                "fasteners_and_threaded_hardware",
                "gaskets_and_dynamic_seals",
                "retaining_hardware",
                "fluid_lines_and_fittings",
                "internal_fluid_passages",
                "additional_bearings_bushings_and_thrust_elements",
                "sensors_and_instrumentation",
            }.issubset(ids)
        )

    def test_inventing_a_backlog_quantity_fails_contract_integrity(self):
        contract = copy.deepcopy(self.contract)
        contract["unbounded_bom_backlog"][0]["quantity"] = 1

        report = self.evaluate_contract(contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "invented_backlog_data:fasteners_and_threaded_hardware",
            report["contract_integrity_errors"],
        )
        self.assertFalse(report["release"]["whole_engine_functional_authorized"])

    def test_missing_visual_family_fails_contract_integrity(self):
        contract = copy.deepcopy(self.contract)
        contract["family_registry"] = [
            family
            for family in contract["family_registry"]
            if family["id"] != "crankshaft"
        ]

        report = self.evaluate_contract(contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "registry_missing_families:crankshaft",
            report["contract_integrity_errors"],
        )

    def test_arbitrary_hashed_file_cannot_satisfy_typed_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract = copy.deepcopy(self.contract)
            family = contract["family_registry"][0]
            self.mark_family_evidence_package_ready(contract, root, family)
            arbitrary = root / "arbitrary.txt"
            arbitrary.write_text("not a typed evidence manifest", encoding="utf-8")
            pointer = {"path": str(arbitrary), "sha256": file_sha256(arbitrary)}
            family["workstream_evidence_refs"] = {
                workstream_id: [pointer]
                for workstream_id in self.module.WORKSTREAM_RULES
            }
            contract_path = root / "contract.json"
            write_json(contract_path, contract)

            report = self.module.evaluate(root, contract_path, VISUAL)

        audited = report["families"][0]
        self.assertFalse(audited["evidence_package_ready"])
        self.assertTrue(
            all(
                item["status"] == "blocked"
                and any("not_valid_json_object" in gap for gap in item["missing"])
                for item in audited["workstreams"]
            )
        )
        self.assertFalse(audited["functional_release_authorized"])
        self.assertFalse(audited["print_release_authorized"])

    def test_incompatible_evidence_id_and_artifact_reuse_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registry = self.module.EvidenceRegistry()
            shared_artifact = root / "shared.dat"
            shared_artifact.write_text("one artifact", encoding="utf-8")
            first = self.typed_evidence(
                root,
                family_id="crankcase_half",
                workstream_id="provenance",
                evidence_id="EV-REUSED",
                artifact_path=shared_artifact,
            )
            second = self.typed_evidence(
                root,
                family_id="crankcase_half",
                workstream_id="parametric_geometry",
                evidence_id="EV-REUSED",
                artifact_path=shared_artifact,
            )
            first_ready, _ = self.module.verify_evidence_manifest(
                first,
                root,
                family_id="crankcase_half",
                workstream_id="provenance",
                evidence_kind="family_provenance_report",
                variant_ids=self.module.ALL_VARIANTS,
                registry=registry,
            )
            second_ready, second_finding = self.module.verify_evidence_manifest(
                second,
                root,
                family_id="crankcase_half",
                workstream_id="parametric_geometry",
                evidence_kind="family_parametric_geometry_report",
                variant_ids=self.module.ALL_VARIANTS,
                registry=registry,
            )

        self.assertTrue(first_ready)
        self.assertFalse(second_ready)
        self.assertIn("evidence_id_reused_by_incompatible_claim", second_finding)
        self.assertIn("artifact_digest_reused_by_incompatible_claim", second_finding)
        self.assertIn("artifact_path_reused_by_incompatible_claim", second_finding)

    def test_one_manifest_cannot_satisfy_an_incompatible_claim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference = self.typed_evidence(
                root,
                family_id="crankcase_half",
                workstream_id="provenance",
            )
            registry = self.module.EvidenceRegistry()
            first_ready, _ = self.module.verify_evidence_manifest(
                reference,
                root,
                family_id="crankcase_half",
                workstream_id="provenance",
                evidence_kind="family_provenance_report",
                variant_ids=self.module.ALL_VARIANTS,
                registry=registry,
            )
            second_ready, second_finding = self.module.verify_evidence_manifest(
                reference,
                root,
                family_id="crankcase_half",
                workstream_id="physics",
                evidence_kind="family_reference_physics_correlation_report",
                variant_ids=self.module.ALL_VARIANTS,
                registry=registry,
            )

        self.assertTrue(first_ready)
        self.assertFalse(second_ready)
        self.assertIn("workstream_id_mismatch", second_finding)

    def test_all_typed_packages_and_true_flags_still_cannot_self_release(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract = copy.deepcopy(self.contract)
            for family in contract["family_registry"]:
                self.mark_family_evidence_package_ready(contract, root, family)
            for gate_id in contract["whole_engine_gates"]:
                contract["whole_engine_gates"][gate_id] = True
            contract_path = root / "contract.json"
            write_json(contract_path, contract)

            report = self.module.evaluate(root, contract_path, VISUAL)

        self.assertEqual(report["report_status"], "passed")
        self.assertEqual(
            report["family_gap_summary"]["families_with_evidence_package_ready"],
            31,
        )
        self.assertTrue(
            all(item["evidence_package_ready"] for item in report["families"])
        )
        self.assertTrue(
            all(not item["functional_release_authorized"] for item in report["families"])
        )
        self.assertTrue(
            all(not item["print_release_authorized"] for item in report["families"])
        )
        self.assertTrue(
            all(not item["assembly_release_authorized"] for item in report["families"])
        )
        self.assertTrue(
            all(
                verifier["implementation_status"] == "not_implemented"
                and verifier["verified"] is False
                for verifier in report["runtime_verifiers"].values()
            )
        )
        self.assertFalse(report["release"]["whole_engine_functional_authorized"])
        self.assertFalse(report["release"]["mixed_route_manufacturing_authorized"])
        self.assertFalse(report["release"]["lpbf_part_package_authorized"])
        self.assertFalse(report["release"]["engine_start_authorized"])
        self.assertFalse(report["physicsnemo"]["training_authorized"])

    def test_runtime_verifier_configuration_cannot_self_enable(self):
        contract = copy.deepcopy(self.contract)
        for verifier_id in self.module.RUNTIME_VERIFIERS:
            contract["runtime_verifier_contract"][verifier_id] = "implemented"
        contract["runtime_verifier_contract"]["configuration_is_authority"] = True
        for gate_id in contract["whole_engine_gates"]:
            contract["whole_engine_gates"][gate_id] = True

        report = self.evaluate_contract(contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(
            any(
                error.startswith("runtime_verifier_contract_mismatch:")
                for error in report["contract_integrity_errors"]
            )
        )
        self.assertIn(
            "runtime_configuration_cannot_be_release_authority",
            report["contract_integrity_errors"],
        )
        self.assertFalse(report["release"]["whole_engine_functional_authorized"])
        self.assertFalse(report["release"]["engine_start_authorized"])
        self.assertFalse(report["physicsnemo"]["training_authorized"])

    def test_routes_do_not_invent_forgings_or_additive_conversion(self):
        routes = {
            item["id"]: item["manufacturing_route"]
            for item in self.contract["family_registry"]
        }

        self.assertEqual(routes["crankcase_half"], "cast")
        self.assertEqual(routes["connecting_rod"], "forged")
        self.assertEqual(routes["exhaust_primary"], "fabricated")
        self.assertEqual(routes["exhaust_collector"], "fabricated")
        for family_id in ("piston", "camshaft", "output_shaft"):
            self.assertEqual(routes[family_id], "route_not_selected")

    def test_physicsnemo_is_not_authorized_from_visual_geometry(self):
        report = self.module.evaluate(ROOT, CONTRACT, VISUAL)

        self.assertFalse(report["physicsnemo"]["training_authorized"])
        self.assertIn("surrogate", report["physicsnemo"]["role"])
        self.assertEqual(report["engineering_status"], "blocked")
        self.assertFalse(report["release"]["engine_start_authorized"])


if __name__ == "__main__":
    unittest.main()
