import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "twins/reference-917-engine/source/build_parametric_cad_contract_f22.py"
)
CONTRACT = (
    ROOT
    / "twins/reference-917-engine/parametric-cad-assembly-contract-f22.json"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "build_parametric_cad_contract_f22", SCRIPT
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


def all_false(value):
    if isinstance(value, bool):
        return value is False
    if isinstance(value, dict):
        return all(all_false(item) for item in value.values())
    if isinstance(value, list):
        return all(all_false(item) for item in value)
    return True


class ParametricCadAssemblyContractF22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.f12 = json.loads(
            (
                ROOT
                / "twins/reference-917-engine/whole-engine-reengineering-f12.json"
            ).read_text(encoding="utf-8")
        )
        cls.f19 = json.loads(
            (
                ROOT
                / "twins/reference-917-engine/manufacturing-routing-f19.json"
            ).read_text(encoding="utf-8")
        )

    def test_checked_contract_is_deterministic_and_fail_closed(self):
        self.assertEqual(self.module.build_contract(ROOT), self.contract)
        report = self.module.evaluate(ROOT, self.contract)
        self.assertEqual(report["report_status"], "passed")
        self.assertEqual(report["contract_errors"], [])
        self.assertFalse(report["geometry_generated"])
        self.assertTrue(all_false(report["release"]))

    def test_upstreams_are_digest_bound_and_f16_is_schema_only(self):
        sources = {
            item["id"]: item for item in self.contract["upstream_contracts"]
        }
        self.assertEqual(set(sources), set(self.module.UPSTREAMS))
        for source_id, specification in self.module.UPSTREAMS.items():
            record = sources[source_id]
            self.assertEqual(record["path"], specification["path"])
            self.assertEqual(record["sha256"], specification["sha256"])
            self.assertFalse(record["geometry_authority"])
            self.assertFalse(record["manufacturing_authority"])
        f16 = sources["kinematic_readiness_f16"]
        self.assertEqual(
            f16["reuse_scope"],
            "schema_and_null_policy_only_no_variant_values_transferred",
        )
        scope = self.contract["branch_scope"]
        self.assertEqual(scope["selected_variant"], "type_912_4_5_na")
        self.assertEqual(scope["f16_source_variant"], "type_912_5_0_na")
        self.assertFalse(scope["f16_coordinates_or_dimensions_transferred"])
        self.assertFalse(scope["other_variant_geometry_inheritance_authorized"])

    def test_no_design_or_manufacturing_dimension_is_claimed(self):
        authority = self.contract["dimension_authority"]
        self.assertEqual(authority["verified_design_dimensions"], [])
        self.assertEqual(authority["verified_manufacturing_dimensions"], [])
        for key in (
            "published_geometry_candidates",
            "published_reference_candidates_not_geometry",
            "published_topology_candidates",
        ):
            for candidate in authority[key]:
                self.assertFalse(candidate["design_lock"])
                self.assertFalse(candidate["cad_parameter_applied"])
                self.assertFalse(candidate["manufacturing_dimension"])
                self.assertIsNone(candidate["manufacturing_tolerance"])

    def test_published_candidates_remain_separate_from_null_cad_parameters(self):
        candidates = {
            item["source_fact_ref"]: item
            for item in self.contract["dimension_authority"][
                "published_geometry_candidates"
            ]
        }
        expected = {
            "FACT-45-BORE": (85.0, "mm", "P-CYLINDER-FINISHED-BORE"),
            "FACT-45-STROKE": (66.0, "mm", "P-PISTON-STROKE"),
            "FACT-45-PISTON-COMPRESSION-HEIGHT": (
                43.0,
                "mm",
                "P-PISTON-PIN-AXIS-TO-CROWN",
            ),
            "FACT-45-CRANKPIN-BEARING-DIAMETER": (
                52.0,
                "mm",
                "P-CRANKPIN-BEARING-DIAMETER",
            ),
            "FACT-45-CONNECTING-ROD-BIG-END-DIAMETER": (
                56.0,
                "mm",
                "P-ROD-BIG-END-DIAMETER",
            ),
            "F20-INTAKE-VALVE-OUTER-DIAMETER": (
                47.5,
                "mm",
                "P-INTAKE-VALVE-OUTER-DIAMETER",
            ),
            "F20-EXHAUST-VALVE-OUTER-DIAMETER": (
                40.5,
                "mm",
                "P-EXHAUST-VALVE-OUTER-DIAMETER",
            ),
            "F20-INTAKE-PORT-DIAMETER": (
                41.0,
                "mm",
                "P-INTAKE-PORT-DIAMETER",
            ),
        }
        self.assertEqual(set(candidates), set(expected))
        for fact_id, (value, unit, parameter_id) in expected.items():
            candidate = candidates[fact_id]
            self.assertEqual(candidate["candidate"]["value"], value)
            self.assertEqual(candidate["candidate"]["unit"], unit)
            self.assertEqual(candidate["parameter_id"], parameter_id)

        parameters = {
            item["id"]: item
            for group in self.contract["parameter_groups"]
            for item in group["parameters"]
        }
        for _, (_, _, parameter_id) in expected.items():
            self.assertIn(parameter_id, parameters)
            self.assertIsNone(parameters[parameter_id]["value"])
            self.assertFalse(parameters[parameter_id]["design_lock"])
        port = candidates["F20-INTAKE-PORT-DIAMETER"]
        self.assertEqual(
            port["homologation_declared_tolerance_ref"],
            "F20-TOL-INTAKE-PORT-DIAMETER",
        )
        self.assertFalse(port["homologation_tolerance_is_manufacturing_tolerance"])

        excluded = {
            item["source_fact_ref"]
            for item in self.contract["dimension_authority"][
                "f20_facts_explicitly_not_used_as_static_cad_dimensions"
            ]
        }
        self.assertEqual(
            excluded,
            {
                "F20-INTAKE-VALVE-MAX-LIFT",
                "F20-EXHAUST-VALVE-MAX-LIFT",
                "F20-INTAKE-COLD-CLEARANCE",
                "F20-EXHAUST-COLD-CLEARANCE",
                "F20-INTAKE-OPENS-BTDC",
                "F20-INTAKE-CLOSES-ABDC",
                "F20-EXHAUST-OPENS-BBDC",
                "F20-EXHAUST-CLOSES-ATDC",
            },
        )
        unresolved = self.contract["dimension_authority"][
            "f20_unresolved_inputs_preserved"
        ]
        self.assertEqual(len(unresolved), 4)
        self.assertTrue(all(item["value"] is None for item in unresolved))

    def test_measurement_registry_is_fillable_but_entirely_unknown(self):
        parameters = [
            item
            for group in self.contract["parameter_groups"]
            for item in group["parameters"]
        ]
        self.assertEqual(len(parameters), 71)
        self.assertEqual(len({item["id"] for item in parameters}), 71)
        for item in parameters:
            self.assertIsNone(item["value"])
            self.assertIsNone(item["uncertainty"])
            self.assertIsNone(item["datum_ref"])
            self.assertIsNone(item["evidence_ref"])
            self.assertIsNone(item["manufacturing_tolerance"])
            self.assertIn("measurement", item["status"])
            self.assertTrue(item["preferred_measurement_method"])

        packages = self.contract["measurement_packages"]
        self.assertEqual(len(packages), 9)
        self.assertTrue(all(not item["values_registered"] for item in packages))
        self.assertTrue(
            all(item["branch_identity_required"] == "type_912_4_5_na" for item in packages)
        )
        required = set(packages[0]["required_evidence_fields"])
        self.assertTrue(
            {
                "instrument_id",
                "calibration_certificate",
                "datum_scheme",
                "raw_measurement_artifact_sha256",
                "uncertainty_budget",
                "independent_review",
            }.issubset(required)
        )

    def test_assembly_tree_covers_na_visual_families_without_claiming_a_bom(self):
        source = {
            item["id"]: item
            for item in self.f12["family_registry"]
            if item["visual_variant"] != "917_30_only"
        }
        assembly = {item["family_id"]: item for item in self.contract["assembly_tree"]}
        self.assertEqual(len(assembly), 29)
        self.assertEqual(set(assembly), set(source))
        self.assertNotIn("turbocharger", assembly)
        self.assertNotIn("charge_plenum", assembly)
        for family_id, record in assembly.items():
            self.assertEqual(
                record["occurrence_count_candidate"], source[family_id]["visual_count"]
            )
            self.assertIn("not_real_bom", record["occurrence_count_status"])
            self.assertIsNone(record["cad_master"])
            self.assertIsNone(record["placement_transform"])
            self.assertTrue(all_false(record["release"]))

    def test_f19_routes_are_only_classifications_and_select_nothing(self):
        f19_routes = {
            item["id"]: item["functional_disposition"]["route_class"]
            for item in self.f19["family_route_registry"]
        }
        for record in self.contract["assembly_tree"]:
            self.assertEqual(
                record["functional_route_class_candidate"],
                f19_routes[record["family_id"]],
            )
            self.assertIsNone(record["selected_material_grade"])
            self.assertIsNone(record["selected_process"])
            self.assertIsNone(record["selected_tolerance_set"])
        by_family = {
            item["family_id"]: item["functional_route_class_candidate"]
            for item in self.contract["assembly_tree"]
        }
        self.assertEqual(by_family["individual_head"], "metal_additive_candidate")
        self.assertEqual(by_family["crankshaft"], "conventional_candidate")
        self.assertEqual(by_family["main_bearing"], "purchased_non_printable")
        self.assertEqual(by_family["piston"], "unresolved")

    def test_interfaces_are_unplaced_inactive_templates(self):
        interfaces = self.contract["interface_templates"]
        self.assertEqual(len(interfaces), 10)
        for item in interfaces:
            for key in (
                "frame_a",
                "frame_b",
                "mating_geometry",
                "fit_or_clearance",
                "fastener_or_retention",
                "surface_finish",
                "tolerance_stack",
                "evidence_ref",
            ):
                self.assertIsNone(item[key])
            self.assertFalse(item["count_is_verified_bom"])
            self.assertFalse(item["active"])
            self.assertFalse(item["physics_joint_enabled"])
            self.assertFalse(item["manufacturing_released"])

    def test_f21_dependency_is_digest_bound_and_remains_unsatisfied(self):
        dependency = self.contract["f21_dependency"]
        self.assertEqual(dependency["source_contract"], "scan_scale_orientation_f21")
        self.assertEqual(
            dependency["source_sha256"],
            self.module.UPSTREAMS["scan_scale_orientation_f21"]["sha256"],
        )
        self.assertEqual(
            dependency["required_gate_results"],
            {
                "scan_identity_verified": False,
                "scan_scale_verified": False,
                "scan_orientation_verified": False,
                "f11_source_identity_and_scale_adapter_ready": False,
            },
        )
        self.assertFalse(dependency["satisfied"])
        self.assertFalse(
            self.contract["release_gates"]["f21_scale_and_orientation_validated"]
        )

    def test_no_geometry_fabrication_or_physicsnemo_is_authorized(self):
        asset = self.contract["asset"]
        policy = self.contract["cad_authoring_policy"]
        self.assertFalse(asset["geometry_generated"])
        self.assertEqual(
            policy["current_outputs_allowed"],
            ["json_contract", "measurement_records"],
        )
        for key in (
            "current_geometry_generation_authorized",
            "coordinates_authorized",
            "solids_authorized",
            "meshes_authorized",
            "curves_authorized",
            "materials_authorized",
            "joints_authorized",
            "physics_schemas_authorized",
            "fabrication_exports_authorized",
            "stl_or_3mf_export_authorized",
        ):
            self.assertFalse(policy[key])
        self.assertTrue(policy["unknown_values_must_be_null"])
        self.assertTrue(all_false(self.contract["release_gates"]))
        physicsnemo = self.contract["physicsnemo_policy"]
        self.assertIn("after_qualified_geometry", physicsnemo["role"])
        self.assertTrue(
            all_false({key: value for key, value in physicsnemo.items() if isinstance(value, bool)})
        )

    def test_contract_contains_no_raw_or_manufacturing_artifact_reference(self):
        text = json.dumps(self.contract).lower()
        for forbidden in (".pdf", ".obj", ".stl", ".3mf", "work/"):
            self.assertNotIn(forbidden, text)
        self.assertFalse(self.contract["asset"]["raw_scan_in_git"])
        self.assertFalse(self.contract["asset"]["proprietary_source_in_git"])

    def test_tampered_dimension_gate_f21_or_family_selection_fails_closed(self):
        contract = copy.deepcopy(self.contract)
        contract["parameter_groups"][0]["parameters"][0]["value"] = [0, 0, 0]
        contract["release_gates"]["cad_solids_authorized"] = True
        contract["f21_dependency"]["satisfied"] = True
        contract["assembly_tree"][0]["selected_process"] = "invented_process"

        errors = self.module.validate_contract(ROOT, contract)

        self.assertIn(
            "unknown_parameter_value_must_be_null:P-ENGINE-REFERENCE-FRAME", errors
        )
        self.assertIn("release_gates_must_remain_false", errors)
        self.assertIn("f21_gate_must_remain_closed", errors)
        self.assertIn(
            "family_selection_forbidden:crankcase_half:selected_process", errors
        )
        self.assertIn("contract_differs_from_deterministic_source", errors)
        report = self.module.evaluate(ROOT, contract)
        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(all_false(report["release"]))

    def test_cli_check_validates_a_copied_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "f22.json"
            copied.write_bytes(CONTRACT.read_bytes())
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--root",
                    str(ROOT),
                    "--output",
                    str(copied),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["report_status"], "passed")


if __name__ == "__main__":
    unittest.main()
