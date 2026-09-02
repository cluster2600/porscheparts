import copy
import csv
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/kinematic-interface-readiness-f16.json"
RUNNER = ROOT / "twins/reference-917-engine/source/build_kinematic_interface_readiness_f16.py"
SOURCE_PATHS = {
    "fact_registry": ROOT / "twins/reference-917-engine/classical-solver-cases-f13.json",
    "dimensional_skeleton": ROOT / "twins/reference-917-engine/dimensional-skeleton-f14.json",
    "scan_metrology": ROOT / "twins/reference-917-engine/scan-metrology-f13.json",
    "mechanical_connections": ROOT / "twins/reference-917-engine/mechanical-connections-f8.json",
    "mechanical_cycle_closure": ROOT / "twins/reference-917-engine/mechanical-cycle-closure-f15.json",
}


def load_module():
    spec = importlib.util.spec_from_file_location("kinematic_interface_readiness_917_f16", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class KinematicInterfaceReadiness917F16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.sources = {
            key: json.loads(path.read_text(encoding="utf-8"))
            for key, path in SOURCE_PATHS.items()
        }
        cls.report = cls.module.build_report(
            cls.contract,
            cls.sources["fact_registry"],
            cls.sources["dimensional_skeleton"],
            cls.sources["scan_metrology"],
            cls.sources["mechanical_connections"],
            cls.sources["mechanical_cycle_closure"],
            SOURCE_PATHS,
            contract_path=CONTRACT,
            project_root=ROOT,
        )

    def validate(self, contract=None, **source_overrides):
        sources = {**self.sources, **source_overrides}
        return self.module.validate_contract(
            contract if contract is not None else self.contract,
            sources["fact_registry"],
            sources["dimensional_skeleton"],
            sources["scan_metrology"],
            sources["mechanical_connections"],
            sources["mechanical_cycle_closure"],
            ROOT,
        )

    def test_current_contract_passes_but_all_kinematics_remain_blocked(self):
        self.assertEqual(self.validate(), [])
        self.assertEqual(
            self.report["status"],
            "passed_readiness_generation_all_kinematics_blocked",
        )
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))
        summary = self.report["readiness_summary"]
        self.assertEqual(summary["verified_coordinate_count"], 0)
        self.assertEqual(summary["solid_count"], 0)
        self.assertEqual(summary["physics_joint_count"], 0)
        self.assertEqual(summary["animated_prim_count"], 0)
        self.assertEqual(summary["physicsnemo_sample_count"], 0)

    def test_reference_branch_is_explicitly_unbound_from_scan(self):
        branch = self.report["work_branch"]

        self.assertEqual(branch["variant_id"], "type_912_5_0_na")
        self.assertEqual(branch["role"], "engineering_reference_branch_not_scan_identification")
        self.assertFalse(branch["scan_binding"])
        self.assertIsNone(branch["scan_asset_id"])
        self.assertEqual(branch["scan_identity_status"], "unbound")
        self.assertIsNone(branch["scan_scale_mm_per_unit"])
        self.assertFalse(branch["variant_identity_proven"])

    def test_only_six_sourced_facts_and_one_transparent_derivation_are_present(self):
        facts = {item["fact_ref"]: item for item in self.report["resolved_source_facts"]}

        self.assertEqual(set(facts), set(self.module.EXPECTED_FACTS))
        self.assertEqual(facts["FACT-CYLINDER-COUNT"]["value"], 12)
        self.assertEqual(facts["FACT-50-BORE"]["value"], 86.8)
        self.assertEqual(facts["FACT-50-STROKE"]["value"], 70.4)
        self.assertEqual(facts["FACT-MAIN-BEARING-COUNT"]["value"], 8)
        self.assertTrue(all(item["source_refs"] for item in facts.values()))
        self.assertTrue(all(item["manufacturing_dimension"] is False for item in facts.values()))

        self.assertEqual(len(self.report["transparent_derivations"]), 1)
        radius = self.report["transparent_derivations"][0]
        self.assertEqual(radius["formula"], "stroke_mm / 2")
        self.assertAlmostEqual(radius["value"], 35.2, places=12)
        self.assertFalse(radius["manufacturing_dimension"])
        self.assertFalse(radius["geometry_authority"])
        self.assertFalse(radius["load_model_authority"])

    def test_datums_bearing_stations_and_components_are_complete_and_unplaced(self):
        datums = self.report["datum_registry"]
        fixed = [item for item in datums if "ordinal" not in item]
        cylinders = [item for item in datums if item.get("kind") == "cylinder_axis"]
        self.assertEqual(len(fixed), 5)
        self.assertEqual(len(cylinders), 12)
        self.assertTrue(all(item.get("origin_mm") is None for item in datums))
        self.assertTrue(
            all(
                item.get("orientation", item.get("direction", item.get("normal"))) is None
                for item in datums
            )
        )

        stations = self.report["main_bearing_station_registry"]
        self.assertEqual(len(stations), 8)
        for station in stations:
            self.assertIsNone(station["axial_coordinate_mm"])
            self.assertIsNone(station["seat_center_mm"])
            self.assertIsNone(station["seat_diameter_mm"])
            self.assertFalse(station["manufacturing_dimension"])

        instances = self.report["component_instance_registry"]
        counts = Counter(item["family"] for item in instances)
        self.assertEqual(dict(counts), self.module.EXPECTED_COMPONENT_COUNTS)
        self.assertEqual(len(instances), 58)
        self.assertEqual(len({item["id"] for item in instances}), 58)
        for instance in instances:
            self.assertIsNone(instance["transform_mm"])
            self.assertIsNone(instance["orientation"])
            self.assertIsNone(instance["geometry_ref"])
            self.assertIsNone(instance["material_specification"])
            self.assertIsNone(instance["mass_kg"])
            self.assertFalse(instance["physics_body_enabled"])
            self.assertFalse(instance["manufacturing_released"])

    def test_minimal_graph_has_68_inactive_requirements_and_no_joint(self):
        graph = self.report["minimal_graph"]
        relation_counts = Counter(item["group_id"] for item in graph["relations"])

        self.assertEqual(len(graph["nodes"]), 58)
        self.assertEqual(len(graph["relations"]), 68)
        self.assertEqual(
            dict(relation_counts),
            {key: value[0] for key, value in self.module.EXPECTED_RELATIONS.items()},
        )
        self.assertTrue(graph["all_relations_inactive"])
        self.assertEqual(graph["physics_joint_count"], 0)
        for relation in graph["relations"]:
            self.assertIsNone(relation["coordinates"])
            self.assertFalse(relation["active"])
            self.assertFalse(relation["physics_joint_enabled"])
        pin_relation = next(
            item for item in graph["relations"] if item["group_id"] == "piston_pin_to_piston"
        )
        self.assertIsNone(pin_relation["source_connection_ref"])
        self.assertEqual(pin_relation["requirement_role"], "required_topology_not_evidence")

    def test_measurement_campaign_is_a_null_cmm_ct_teardown_template(self):
        measurements = self.report["measurement_campaign"]

        self.assertEqual(len(measurements), 14)
        self.assertEqual({item["id"] for item in measurements}, self.module.EXPECTED_MEASUREMENT_IDS)
        self.assertTrue(all(item["value"] is None for item in measurements))
        self.assertTrue(all(item["status"] == "missing" for item in measurements))
        for item in measurements:
            evidence = item["evidence"]
            self.assertEqual(evidence["review_status"], "missing")
            self.assertIsNone(evidence["instrument_id"])
            self.assertIsNone(evidence["calibration_certificate"])
            self.assertIsNone(evidence["uncertainty"])
            self.assertIsNone(evidence["evidence_path"])

    def test_contract_rejects_any_unverified_coordinate_or_measurement(self):
        mutated = copy.deepcopy(self.contract)
        mutated["datum_registry_contract"]["fixed_datums"][1]["origin_mm"] = [0, 0, 0]
        mutated["main_bearing_station_contract"]["axial_coordinate_mm"] = 42.0
        mutated["instance_null_template"]["transform_mm"] = [0, 0, 0]
        mutated["minimal_graph_contract"]["relation_groups"][0]["coordinates"] = [0, 0, 0]
        mutated["measurement_campaign_template"][0]["value"] = "917/30"

        errors = self.validate(contract=mutated)

        self.assertIn(
            "datum_registry_contract.crankshaft_axis: exact kind, null coordinates and status required",
            errors,
        )
        self.assertIn(
            "main_bearing_station_contract.axial_coordinate_mm: unmeasured value must be null",
            errors,
        )
        self.assertIn(
            "instance_null_template: exact null fields, false authorities and safe status required",
            errors,
        )
        self.assertIn(
            "minimal_graph_contract.crankcase_supports_crankshaft: exact endpoints, count, planned relation and inactive flags required",
            errors,
        )
        self.assertIn(
            "measurement_campaign_template.MC-IDENTITY-01: exact target, quantity, unit, method, minimum occurrences and null value required",
            errors,
        )

    def test_contract_rejects_scan_binding_radius_prefill_or_release_gate(self):
        mutated = copy.deepcopy(self.contract)
        mutated["work_branch"]["scan_binding"] = True
        mutated["work_branch"]["scan_asset_id"] = "local-scan"
        mutated["work_branch"]["scan_scale_mm_per_unit"] = 1.0
        mutated["transparent_derivations"][0]["value_in_contract"] = 35.2
        mutated["transparent_derivations"][0]["manufacturing_dimension"] = True
        mutated["release_gates"]["kinematic_joints_authorized"] = True

        errors = self.validate(contract=mutated)

        self.assertIn(
            "work_branch: scan must remain unbound from the 5.0 L NA reference branch",
            errors,
        )
        self.assertIn(
            "transparent_derivations[0]: only stroke/2 with no manufacturing authority is allowed",
            errors,
        )
        self.assertIn("release_gates: every gate must remain false", errors)

    def test_contract_rejects_a_changed_or_unlocked_source_fact(self):
        mutated_registry = copy.deepcopy(self.sources["fact_registry"])
        stroke = next(
            item for item in mutated_registry["fact_registry"] if item["id"] == "FACT-50-STROKE"
        )
        stroke["candidate"]["value"] = 71.0
        stroke["design_lock"] = True

        errors = self.validate(fact_registry=mutated_registry)

        self.assertIn("fact_registry.FACT-50-STROKE.candidate: published value changed", errors)
        self.assertIn("fact_registry.FACT-50-STROKE.design_lock: must remain false", errors)

    def test_contract_rejects_forged_fact_provenance_usage_or_contradictions(self):
        mutated_registry = copy.deepcopy(self.sources["fact_registry"])
        stroke = next(
            item for item in mutated_registry["fact_registry"] if item["id"] == "FACT-50-STROKE"
        )
        stroke["source_refs"] = ["SRC-FORGED"]
        stroke["usage"] = "released"
        stroke["contradiction_refs"] = []

        errors = self.validate(fact_registry=mutated_registry)

        self.assertIn("fact_registry.FACT-50-STROKE.source_refs: exact provenance changed", errors)
        self.assertIn("fact_registry.FACT-50-STROKE.usage: must remain candidate_only", errors)
        self.assertIn(
            "fact_registry.FACT-50-STROKE.contradiction_refs: exact unresolved set changed",
            errors,
        )

    def test_contract_rejects_any_changed_parent_authority_flag_or_key(self):
        mutated_cycle = copy.deepcopy(self.sources["mechanical_cycle_closure"])
        mutated_cycle["authority_boundary"]["cantera_execution_authorized"] = True
        mutated_cycle["authority_boundary"]["performance_claim_authorized"] = True
        mutated_cycle["authority_boundary"]["unexpected_authority"] = False

        errors = self.validate(mechanical_cycle_closure=mutated_cycle)

        self.assertIn(
            "mechanical_cycle_closure.authority_boundary: expected the exact F15 authority set and booleans",
            errors,
        )

        wrong_type = copy.deepcopy(self.sources["mechanical_cycle_closure"])
        wrong_type["authority_boundary"]["turbo_simulation_authorized"] = 0
        self.assertIn(
            "mechanical_cycle_closure.authority_boundary: expected the exact F15 authority set and booleans",
            self.validate(mechanical_cycle_closure=wrong_type),
        )

    def test_contract_rejects_changed_relation_endpoints_type_or_duplicate_prefix(self):
        mutated = copy.deepcopy(self.contract)
        relation = next(
            item
            for item in mutated["minimal_graph_contract"]["relation_groups"]
            if item["id"] == "piston_to_cylinder"
        )
        relation["from_family"] = "connecting_rod"
        relation["to_family"] = "piston_pin"
        relation["planned_relation"] = "fixed_claim"
        piston = next(
            item
            for item in mutated["component_instance_contract"]
            if item["family"] == "piston"
        )
        piston["id_prefix"] = "piston_pin_geometric_"

        errors = self.validate(contract=mutated)

        self.assertIn(
            "minimal_graph_contract.piston_to_cylinder: exact endpoints, count, planned relation and inactive flags required",
            errors,
        )
        self.assertIn(
            "component_instance_contract.piston: exact family, id_prefix, count and provenance required",
            errors,
        )
        self.assertIn(
            "component_instance_contract: expected exactly 58 unique semantic instance ids",
            errors,
        )

    def test_contract_rejects_changed_measurement_semantics_or_minimum_occurrences(self):
        mutated = copy.deepcopy(self.contract)
        measurement = next(
            item
            for item in mutated["measurement_campaign_template"]
            if item["id"] == "MC-BEARING-01"
        )
        measurement.update(
            target="not_a_bearing",
            quantity="nothing",
            unit="fiction",
            preferred_method="none",
            minimum_occurrences=0,
        )

        errors = self.validate(contract=mutated)

        self.assertIn(
            "measurement_campaign_template.MC-BEARING-01: exact target, quantity, unit, method, minimum occurrences and null value required",
            errors,
        )

    def test_contract_and_usda_builder_reject_unsafe_semantic_tokens(self):
        mutated = copy.deepcopy(self.contract)
        mutated["instance_null_template"]["status"] = (
            'x"\n        def Mesh "Injected" {}\n        #'
        )

        errors = self.validate(contract=mutated)

        self.assertIn(
            "instance_null_template: exact null fields, false authorities and safe status required",
            errors,
        )
        with self.assertRaisesRegex(ValueError, "unsafe USD string token refused"):
            self.module._usd_string_token(mutated["instance_null_template"]["status"], "test")
        with self.assertRaisesRegex(ValueError, "unsafe USD identifier refused"):
            self.module._safe_usd_name("unsafe-name")

    def test_csv_contains_only_sourced_scalars_and_blank_coordinates(self):
        csv_text = self.module.build_registry_csv(self.report)
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(len(rows), 172)
        structural = [
            row
            for row in rows
            if row["record_kind"]
            in {
                "datum",
                "main_bearing_station",
                "component_instance",
                "relation_requirement",
                "measurement_requirement",
            }
        ]
        self.assertTrue(all(row["position_mm"] == "" for row in structural))
        self.assertTrue(all(row["orientation"] == "" for row in structural))
        self.assertTrue(all(row["coordinates_verified"] == "false" for row in structural))
        radius = next(row for row in rows if row["id"] == "candidate_crank_radius")
        self.assertEqual(radius["value"], "35.2")
        self.assertEqual(radius["manufacturing_dimension"], "false")

    def test_usda_contains_only_coordinate_free_xforms_and_scopes(self):
        usda = self.module.build_semantic_usda(self.report)

        self.assertEqual(usda.count("def Xform"), 84)
        self.assertEqual(usda.count("def Scope"), 3)
        for forbidden in (
            "xformOp:",
            "timeSamples",
            "def Mesh",
            "def Cube",
            "def Sphere",
            "def BasisCurves",
            "def Material",
            "PhysicsRigidBodyAPI",
            "PhysicsJoint",
            "UsdPhysics",
        ):
            self.assertNotIn(forbidden, usda)
        self.assertIn("custom bool f16:scanBound = false", usda)
        self.assertIn("custom bool f16:coordinatesVerified = false", usda)
        self.assertIn("custom bool f16:physicsBodyEnabled = false", usda)

    def test_cli_writes_deterministic_json_csv_and_usda(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "--project-root",
                    str(ROOT),
                    "--contract",
                    str(CONTRACT),
                    "--output-dir",
                    temp_dir,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            output = Path(temp_dir)
            generated_report = json.loads(
                (output / "kinematic-interface-readiness.json").read_text(encoding="utf-8")
            )
            generated_csv = (output / "kinematic-interface-registry.csv").read_text(
                encoding="utf-8"
            )
            generated_usda = (output / "kinematic-interface-axes.usda").read_text(
                encoding="utf-8"
            )

        self.assertEqual(generated_report, self.report)
        self.assertEqual(generated_csv, self.module.build_registry_csv(self.report))
        self.assertEqual(generated_usda, self.module.build_semantic_usda(self.report))
        self.assertIn("58 semantic instances", completed.stdout)
        self.assertIn("0 verified coordinates", completed.stdout)

    def test_cli_rejects_but_does_not_dereference_a_mutated_source_path(self):
        mutated = copy.deepcopy(self.contract)
        mutated["source_contracts"]["fact_registry"] = "../../etc/passwd"
        with tempfile.TemporaryDirectory() as temp_dir:
            contract = Path(temp_dir) / "mutated-contract.json"
            contract.write_text(json.dumps(mutated), encoding="utf-8")
            completed = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "--project-root",
                    str(ROOT),
                    "--contract",
                    str(contract),
                    "--output-dir",
                    str(Path(temp_dir) / "output"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("invalid contract", completed.stderr)
        self.assertIn("source_contracts: expected", completed.stderr)
        self.assertNotIn("cannot read fact_registry", completed.stderr)


if __name__ == "__main__":
    unittest.main()
