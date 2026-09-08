import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "993-carbon-safety-cell"
DERIVED = TWIN / "derived"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CarbonSafetyCellTests(unittest.TestCase):
    def test_simulation_program_uses_repository_stack_and_keeps_release_closed(self) -> None:
        program = load_json(TWIN / "simulation-program.json")
        stages = {item["stage_id"]: item for item in program["stages"]}

        self.assertEqual(program["software_stack_source"], "docs/SOFTWARE_STACK.md")
        self.assertIn("CalculiX composite shells", stages["S04_MEASURED_SHELL_CAE"]["tools"])
        self.assertIn("OpenUSD", stages["S05_SIMREADY"]["tools"])
        self.assertIn("NVIDIA PhysicsNeMo 2.2.1", stages["S06_SURROGATE"]["tools"])
        self.assertTrue(stages["S04_MEASURED_SHELL_CAE"]["status"].startswith("blocked"))
        for key in ("manufacturing_release", "road_release", "track_release", "homologation_release"):
            self.assertFalse(program[key])

    def test_manufacturing_simulation_is_reproducible_and_unreleased(self) -> None:
        completed = subprocess.run(
            ["python3", str(TWIN / "source" / "simulate_manufacturing.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

        report = load_json(DERIVED / "manufacturing-process-screening.json")
        self.assertEqual(
            report["status"],
            "manufacturing_hypothesis_screening_complete_not_correlated",
        )
        self.assertEqual(len(report["thermal_cure_cases"]), 6)
        self.assertFalse(report["decision"]["manufacturing_route_selected"])
        self.assertFalse(report["decision"]["tool_material_selected"])
        self.assertFalse(any(report["release_gates"].values()))
        self.assertIn("drape shear, wrinkling and bridging", report["not_simulated"])

    def test_final_product_global_cases_are_reproducible_and_unreleased(self) -> None:
        completed = subprocess.run(
            ["python3", str(TWIN / "source" / "simulate_final_product.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

        report = load_json(DERIVED / "final-product-f1-screening.json")
        self.assertEqual(
            report["status"],
            "global_load_screening_complete_not_structural_validation",
        )
        self.assertEqual(report["architecture_id"], "all_carbon_multicell_x10")
        self.assertEqual(
            {case["case_id"] for case in report["global_inertial_cases"]},
            {"vertical_bump_3g", "braking_1_5g", "cornering_1_8g"},
        )
        self.assertTrue(all(not case["passes_release_requirement"] for case in report["global_inertial_cases"]))
        self.assertTrue(all(case["axial_response"]["allowable_or_factor_of_safety"] is None for case in report["global_inertial_cases"]))
        self.assertFalse(any(report["release_gates"].values()))

    def test_generated_screening_is_reproducible(self) -> None:
        completed = subprocess.run(
            ["python3", str(TWIN / "source" / "build_structural_screening.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_selected_topology_only_passes_provisional_screening(self) -> None:
        report = load_json(DERIVED / "structural-screening.json")
        selected_id = report["selection"]["architecture_id"]
        selected = next(item for item in report["architectures"] if item["architecture_id"] == selected_id)

        self.assertEqual(report["status"], "screening_complete_not_validated")
        self.assertEqual(selected_id, "all_carbon_multicell_x10")
        self.assertEqual(selected["primary_structure_materials"], ["carbon_equivalent"])
        self.assertTrue(selected["meets_primary_structure_material_policy"])
        self.assertAlmostEqual(selected["torsion"]["stiffness_Nm_per_deg"], 21011.7, places=1)
        self.assertGreater(selected["screening"]["relative_torsional_stiffness"], 7.3)
        self.assertTrue(selected["screening"]["passes_provisional_torsion_target"])
        self.assertTrue(selected["screening"]["passes_primary_structure_material_policy"])
        self.assertFalse(any(report["release_gates"].values()))
        self.assertFalse(report["selection"]["manufacturing_release"])
        self.assertFalse(report["selection"]["road_release"])
        self.assertFalse(report["selection"]["track_release"])

    def test_calculix_cross_check_has_no_release_credit(self) -> None:
        report = load_json(DERIVED / "calculix-verification.json")

        self.assertTrue(report["passed"])
        self.assertLess(report["relative_error"], report["tolerance"])
        self.assertFalse(report["road_or_track_release"])
        self.assertTrue(any("pas sa fidélité" in item for item in report["claim_limits"]))

    def test_cad_and_tooling_are_clean_sheet_but_unreleased(self) -> None:
        report = load_json(DERIVED / "cad-generation-report.json")

        self.assertTrue(report["source_boundary"]["clean_sheet"])
        self.assertFalse(report["source_boundary"]["zesad_or_ruf_surfaces_used"])
        self.assertFalse(report["source_boundary"]["vehicle_scan_used"])
        self.assertEqual(report["tooling"]["tool_count"], 10)
        self.assertEqual(report["tooling"]["cavity_subtraction_failures"], [])
        self.assertTrue(report["tooling"]["tunnel_mandrel_modelled"])
        self.assertEqual(report["cell"]["primary_structure_material"], "CFRP")
        self.assertFalse(report["cell"]["local_metallic_hardware_modelled"])
        self.assertTrue(report["cell"]["central_tunnel_is_hollow"])
        self.assertTrue(report["cell"]["door_apertures_modelled"])
        self.assertTrue(report["cell"]["seat_and_pedal_zones_modelled"])
        self.assertTrue(report["cell"]["protected_service_ducts_modelled"])
        self.assertGreaterEqual(report["cell"]["functional_groups"]["central_tunnel"], 4)
        self.assertEqual(report["mass_basis"]["target_vehicle_mass_kg"], 1200.0)
        self.assertEqual(set(report["platform_modules"]), {
            "964_Carrera_2_Coupe",
            "993_Carrera_narrow_reference",
        })
        self.assertTrue(all(
            not platform["suspension_pickup_coordinates_modelled"]
            for platform in report["platform_modules"].values()
        ))
        self.assertFalse(any(report["release_gates"].values()))
        for name in (
            "993-carbon-safety-cell-concept.step",
            "993-carbon-safety-cell-tooling-concept.step",
            "964-carbon-interface-modules-concept.step",
            "993-carbon-interface-modules-concept.step",
        ):
            self.assertGreater((DERIVED / name).stat().st_size, 100_000)
        for name in (
            "964-c2-packaging-envelope.step",
            "964-c4-packaging-envelope.step",
            "993-c2-packaging-envelope.step",
            "993-c4-packaging-envelope.step",
        ):
            self.assertGreater((DERIVED / name).stat().st_size, 20_000)

        self.assertEqual(set(report["driveline_packages"]), {"964_C2", "964_C4", "993_C2", "993_C4"})
        for generation in ("964", "993"):
            self.assertIn("external_shift_rod_clearance", report["driveline_packages"][f"{generation}_C2"]["feature_ids"])
            self.assertIn("central_tube_clearance", report["driveline_packages"][f"{generation}_C4"]["feature_ids"])
            self.assertIn("front_final_drive_clearance", report["driveline_packages"][f"{generation}_C4"]["feature_ids"])
            self.assertIn("front_halfshaft_clearance", report["driveline_packages"][f"{generation}_C4"]["feature_ids"])

    def test_usd_package_is_reproducible_and_fail_closed(self) -> None:
        completed = subprocess.run(
            ["python3", str(TWIN / "source" / "build_usd.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

        root_layer = (DERIVED / "993-carbon-safety-cell-digital-twin.usda").read_text(encoding="utf-8")
        structural = (DERIVED / "993-carbon-safety-cell-structural.usda").read_text(encoding="utf-8")
        tooling = (DERIVED / "993-carbon-safety-cell-tooling.usda").read_text(encoding="utf-8")
        self.assertIn("993-carbon-safety-cell-structural.usda", root_layer)
        self.assertIn("993-carbon-safety-cell-tooling.usda", root_layer)
        self.assertIn("roadOrTrackReleased = false", structural)
        self.assertIn("screeningTorsionalStiffnessNmPerDeg = 21011.7", structural)
        self.assertIn("allCarbonPrimaryStructure = true", structural)
        self.assertIn("targetVehicleMassKg = 1200", structural)
        self.assertIn('def Xform "DrivelinePackages"', structural)
        self.assertIn('def Xform "C2"', structural)
        self.assertIn('def Xform "C4"', structural)
        self.assertIn("ExternalShiftRodClearance", structural)
        self.assertIn("CentralTubePropShaftShiftGuideFrontHalfshafts", structural)
        self.assertIn("ProtectedServiceChannels", structural)
        self.assertIn("C2C4DynamicClearanceValidated = false", structural)
        self.assertNotIn("SteelPaths", structural)
        self.assertIn("fabricationReleased = false", tooling)
        self.assertNotIn("ZESAD", structural)
        self.assertNotIn("RUF", structural)

    def test_manufacturing_and_use_gates_remain_closed(self) -> None:
        contract = load_json(TWIN / "engineering-validation-contract.json")
        mold = load_json(TWIN / "mold-plan.json")
        simready = load_json(TWIN / "simready-readiness.json")

        self.assertFalse(any(contract["release_gates"].values()))
        self.assertFalse(contract["screening_evidence"]["release_credit"])
        self.assertFalse(any(mold["release_gates"].values()))
        self.assertEqual(simready["simready_preflight"]["status"], "blocked")
        self.assertFalse(simready["decision"]["vast_launch_allowed"])
        self.assertFalse(simready["decision"]["vast_launch_executed"])

    def test_964_993_interface_contract_is_fail_closed(self) -> None:
        contract = load_json(TWIN / "platform-interface-contract.json")
        decision = contract["decision"]

        self.assertEqual(contract["common_public_constraint"]["wheelbase_mm"], 2272.0)
        self.assertEqual(contract["documentary_deltas_993_minus_964_mm"]["front_track"], 31.0)
        self.assertEqual(contract["documentary_deltas_993_minus_964_mm"]["rear_track"], 70.0)
        self.assertEqual(contract["mass_contract"]["target_vehicle_mass_kg"], 1200.0)
        self.assertTrue(all(
            value is None
            for value in contract["required_measured_interfaces_per_platform"].values()
        ))
        self.assertFalse(decision["dimensionally_compatible_with_964"])
        self.assertFalse(decision["dimensionally_compatible_with_993"])
        self.assertFalse(decision["manufacturing_authorized"])
        self.assertFalse(decision["road_or_track_use_authorized"])

    def test_german_dimension_register_separates_vehicle_data_from_body_datums(self) -> None:
        register = load_json(TWIN / "tuv-dimensions-de.json")
        tables = register["official_porsche_variant_tables"]

        self.assertEqual(register["dataset_id"], "964-993-CARBON-MONOCOQUE-TUV-DIMENSIONS-DE-0004")
        self.assertEqual(tables["964"]["rows"][0]["wheelbase_mm"], 2272)
        self.assertEqual(tables["964"]["rows"][0]["front_track_mm"], 1380)
        self.assertEqual(tables["964"]["rows"][0]["rear_track_mm"], 1374)
        self.assertEqual(tables["993"]["rows"][1]["variant"], "Carrera_4")
        self.assertEqual(tables["993"]["rows"][1]["front_track_mm"], 1405)
        self.assertEqual(tables["993"]["rows"][1]["rear_track_mm"], 1444)
        self.assertEqual(register["mass_basis_correction"]["published_964_C4_maximum_permitted_mass_kg"], 1790)
        self.assertEqual(register["mass_basis_correction"]["status"], "design_target_only")
        body_datums = next(
            group for group in register["critical_structural_dimensions"]
            if group["group_id"] == "BODY_DATUMS"
        )
        self.assertTrue(body_datums["public_numeric_data"])
        self.assertIn("partial_964_pairwise_constraints", body_datums["status"])
        self.assertEqual(
            register["documented_964_body_repair_constraints"]["key_constraints_mm"]["transmission_crossmember_P12_left_right"],
            {"nominal": 278.0, "tolerance": 1.0},
        )
        self.assertEqual(
            register["documented_964_body_repair_constraints"]["coordinate_reconstruction_status"],
            "pairwise_constraint_graph_only_not_unique_xyz",
        )
        self.assertFalse(register["decision"]["detailed_design_authorized"])

    def test_964_body_manual_dimensions_are_documented_not_measured_xyz(self) -> None:
        record = load_json(ROOT / "catalog" / "measurements" / "MEAS-MANUAL-964-BODY-REPAIR-DIMENSIONS.json")
        values = {item["details"]["dimension_key"]: item for item in record["declared_values"]}

        self.assertEqual(record["record_kind"], "documented_specification")
        self.assertEqual(record["source_id"], "SRC-PORSCHE-WORKSHOP-MANUAL-964-VOLUME5")
        self.assertEqual(len(values), 17)
        self.assertEqual(values["G"]["details"]["nominal_mm"], 278.0)
        self.assertEqual(values["G"]["details"]["tolerance_mm"], 1.0)
        self.assertEqual(values["R"]["details"]["nominal_mm"], 1245.0)
        self.assertEqual(values["S"]["details"]["nominal_mm"], 1328.0)
        self.assertEqual(record["evidence"]["level"], "C")
        self.assertEqual(record["readings"], [])

    def test_C2_C4_packaging_contract_is_complete_but_unreleased(self) -> None:
        contract = load_json(TWIN / "vehicle-packaging-contract.json")
        matrix = contract["variant_matrix"]

        self.assertEqual(set(matrix), {"964_C2", "964_C4", "993_C2", "993_C4"})
        self.assertEqual(matrix["964_C2"]["longitudinal_propeller_shaft"], "absent")
        self.assertEqual(matrix["993_C2"]["front_final_drive"], "absent")
        self.assertEqual(matrix["964_C4"]["longitudinal_propeller_shaft"], "required_in_central_tube")
        self.assertEqual(matrix["993_C4"]["front_halfshafts"], "required")
        self.assertFalse(contract["required_measurement_campaign"]["complete"])
        self.assertFalse(any(contract["release_gates"].values()))
        self.assertGreaterEqual(len(contract["common_packaging_obligations"]), 10)

    def test_packaging_clearance_check_is_reproducible_and_has_no_release_credit(self) -> None:
        completed = subprocess.run(
            ["python3", str(TWIN / "source" / "check_vehicle_packaging.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = load_json(DERIVED / "packaging-clearance-check.json")
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["checks"]), 6)
        self.assertTrue(all(item["passed"] for item in report["checks"]))
        self.assertFalse(any(report["release_gates"].values()))
        self.assertTrue(any("hypothétiques" in item for item in report["claim_limits"]))


if __name__ == "__main__":
    unittest.main()
