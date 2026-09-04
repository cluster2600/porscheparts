"""Vérification indépendante et fail-closed de la définition fonctionnelle F37."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f37-manufacturing-definition.json"
BUILDER = ROOT / "twins/reference-917-engine/source/build_f37_manufacturing_definition.py"
OIL_SOURCE = ROOT / "twins/reference-917-engine/source/screen_f37_oil_system.py"
KINEMATICS_SOURCE = ROOT / "twins/reference-917-engine/source/screen_f37_rocker_kinematics.py"
STRENGTH_SOURCE = ROOT / "twins/reference-917-engine/source/screen_f37_carrier_strength.py"
CALCULIX_SOURCE = ROOT / "twins/reference-917-engine/source/run_f37_carrier_calculix.py"
HEAD_MESH_SOURCE = ROOT / "twins/reference-917-engine/source/build_f37_printable_head_mesh.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def function_source(path: Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item
        for item in tree.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name
    )
    return ast.get_source_segment(source, node) or ""


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot_import:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ManufacturingDefinitionF37ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_scale_qualified_and_release_fail_closed(self):
        self.assertEqual(self.contract["phase"], "F37")
        self.assertEqual(self.contract["parent"]["phase"], "F36")
        self.assertRegex(self.contract["parent"]["head_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(self.contract["coordinate_system"]["absolute_scale_confirmed"])
        self.assertFalse(self.contract["surface_definition"]["whole_head_single_brep"])
        reason = self.contract["surface_definition"]["reason"].lower()
        self.assertIn("open scan", reason)
        self.assertIn("without confirmed scale", reason)
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))

    def test_allowances_are_positive_and_diametral_stock_is_coherent(self):
        allowances = self.contract["machining_allowances_mm_if_scale_is_mm"]
        self.assertTrue(all(0.0 < float(value) <= 1.0 for value in allowances.values()))

        rocker = self.contract["rocker_carrier"]
        shaft_radial_stock = (
            float(rocker["shaft_final_diameter_mm"])
            - float(rocker["shaft_as_printed_bore_diameter_mm"])
        ) / 2.0
        self.assertAlmostEqual(
            shaft_radial_stock,
            float(allowances["rocker_shaft_bore_radial"]),
            places=9,
        )
        self.assertGreater(
            float(rocker["mount_final_clearance_diameter_mm"]),
            float(rocker["mount_as_printed_pilot_mm"]),
        )
        self.assertAlmostEqual(
            (
                float(rocker["mount_final_clearance_diameter_mm"])
                - float(rocker["mount_as_printed_pilot_mm"])
            )
            / 2.0,
            float(allowances["head_stud_bore_radial"]),
            places=9,
        )
        self.assertFalse(rocker["shaft_to_carrier_fit_numeric_limits_confirmed"])
        self.assertFalse(rocker["extended_head_stud_and_clamp_stack_released"])
        self.assertAlmostEqual(float(rocker["shared_head_stud_nominal_diameter_mm"]), 10.0)
        self.assertGreater(
            float(rocker["mount_final_clearance_diameter_mm"]),
            float(rocker["shared_head_stud_nominal_diameter_mm"]),
        )

        stud = next(
            item
            for item in self.contract["thread_and_finish_map"]
            if item["id"] == "head_stud_clearance"
        )
        self.assertAlmostEqual(
            (float(stud["final_diameter_mm"]) - float(stud["as_printed_pilot_mm"])) / 2.0,
            float(allowances["head_stud_bore_radial"]),
            places=9,
        )

    def test_thread_map_is_complete_but_not_released(self):
        thread_map = self.contract["thread_and_finish_map"]
        self.assertEqual(
            {item["id"] for item in thread_map},
            {
                "spark_insert",
                "carrier_mount",
                "oil_gallery_plug",
                "temperature_sensor",
                "head_stud_clearance",
            },
        )
        self.assertTrue(all(item["quantity"] > 0 for item in thread_map))
        self.assertTrue(all(item["released"] is False for item in thread_map))

    def test_carrier_mounts_and_allowances_follow_f36_stud_centres(self):
        build_carrier = function_source(BUILDER, "build_carrier")
        build_rockers = function_source(BUILDER, "build_rockers")
        build_allowances = function_source(BUILDER, "build_allowances")
        for source in (build_carrier, build_allowances):
            self.assertIn("stud_centres_local_mm", source)
        self.assertNotIn("for y in (-50.0, 50.0)", build_allowances)
        self.assertIn("valve_axis_cylinder", build_allowances)
        self.assertIn('data["tilt_y_deg"]', build_allowances)
        rocker = self.contract["rocker_carrier"]
        self.assertEqual(
            rocker["mount_centres_source"],
            "F36_geometry_report_stud_centres_local_mm",
        )
        self.assertEqual(
            rocker["mount_strategy"],
            "detachable_carrier_clamped_on_four_shared_extended_head_studs",
        )
        self.assertEqual(rocker["rail_size_xyz_mm"], [110.0, 34.0, 40.0])
        self.assertEqual(rocker["mount_bridge_height_z_mm"], 24.0)
        self.assertEqual(rocker["rocker_window_size_xy_mm"], [15.0, 36.0])
        self.assertEqual(rocker["rocker_arm_section_xz_mm"], [11.0, 12.0])
        self.assertIn('rocker["rocker_window_size_xy_mm"]', build_carrier)
        self.assertIn('rocker["rocker_arm_section_xz_mm"]', build_rockers)

    def test_rocker_pivot_reaction_envelope_is_consistent_and_fail_closed(self):
        screen = self.contract["rocker_pivot_reaction_screen"]
        self.assertEqual(screen["model"], "ideal_rocker_collinear_upper_envelope")
        self.assertAlmostEqual(
            screen["cam_to_valve_force_ratio"],
            self.contract["rocker_carrier"]["target_rocker_ratio"],
        )
        self.assertAlmostEqual(
            screen["collinear_upper_envelope_factor"],
            1.0 + screen["cam_to_valve_force_ratio"],
        )
        self.assertFalse(screen["actual_resultant_direction_complete"])
        self.assertFalse(
            self.contract["release_gates"]["rocker_pivot_resultant_load_complete"]
        )

        builder = load_module(BUILDER, "f37_pivot_screen_builder")
        builder.validate_rocker_pivot_reaction_screen(self.contract)
        inconsistent = json.loads(json.dumps(self.contract))
        inconsistent["rocker_pivot_reaction_screen"][
            "collinear_upper_envelope_factor"
        ] = 2.14
        with self.assertRaisesRegex(
            RuntimeError, "rocker_pivot_collinear_envelope_factor_mismatch"
        ):
            builder.validate_rocker_pivot_reaction_screen(inconsistent)

    def test_parent_geometry_report_is_hash_and_size_bound_to_head(self):
        builder = load_module(BUILDER, "f37_manufacturing_builder")

        with tempfile.TemporaryDirectory() as temporary:
            head = Path(temporary) / "parent.local.stl"
            head.write_bytes(b"exact-parent-head")
            digest = sha256(head)
            contract = {"parent": {"head_sha256": digest}}
            geometry = {
                "files_local_only": {
                    head.name: {"sha256": digest, "bytes": head.stat().st_size}
                }
            }
            builder.validate_parent_geometry_link(contract, geometry, head)
            geometry["files_local_only"][head.name]["sha256"] = "0" * 64
            with self.assertRaisesRegex(
                RuntimeError, "geometry_report_parent_head_hash_mismatch"
            ):
                builder.validate_parent_geometry_link(contract, geometry, head)

    def test_kinematics_rejects_a_cad_report_bound_to_another_contract(self):
        kinematics = load_module(KINEMATICS_SOURCE, "f37_rocker_kinematics")
        with tempfile.TemporaryDirectory() as temporary:
            contract = Path(temporary) / "contract.json"
            geometry = Path(temporary) / "geometry.json"
            contract.write_text('{"phase":"F37"}\n', encoding="utf-8")
            geometry.write_text('{"phase":"F36"}\n', encoding="utf-8")
            cad = {
                "inputs": {
                    "contract_sha256": sha256(contract),
                    "geometry_report_sha256": sha256(geometry),
                }
            }
            self.assertEqual(
                kinematics.validate_contract_cad_link(contract, geometry, cad),
                (sha256(contract), sha256(geometry)),
            )
            cad["inputs"]["contract_sha256"] = "0" * 64
            with self.assertRaisesRegex(
                RuntimeError, "cad_report_contract_hash_mismatch"
            ):
                kinematics.validate_contract_cad_link(contract, geometry, cad)
            cad["inputs"]["contract_sha256"] = sha256(contract)
            cad["inputs"]["geometry_report_sha256"] = "0" * 64
            with self.assertRaisesRegex(
                RuntimeError, "cad_report_geometry_hash_mismatch"
            ):
                kinematics.validate_contract_cad_link(contract, geometry, cad)

    def test_analysis_sources_keep_physical_and_material_gates_closed(self):
        oil = OIL_SOURCE.read_text(encoding="utf-8")
        kinematics = KINEMATICS_SOURCE.read_text(encoding="utf-8")
        strength = STRENGTH_SOURCE.read_text(encoding="utf-8")
        calculix = CALCULIX_SOURCE.read_text(encoding="utf-8")
        for source in (oil, kinematics, strength, calculix):
            ast.parse(source)
        self.assertIn('"physical_oil_rig_correlated": False', oil)
        self.assertIn('"contract_sha256": sha256(args.contract)', oil)
        self.assertIn('"measured_cam_profile_available": False', kinematics)
        self.assertIn('"contract_sha256": contract_sha', kinematics)
        self.assertIn('"geometry_report_sha256": geometry_report_sha', kinematics)
        self.assertIn("validate_contract_cad_link(", kinematics)
        self.assertIn('"dynamic_contact_and_flexure_fea_complete": False', kinematics)
        self.assertIn('"spintron_correlated": False', kinematics)
        self.assertIn("cam_lever = effective_lever / ratio", kinematics)
        self.assertNotIn("cam_lever = valve_lever / ratio", kinematics)
        self.assertIn('"nonlinear_contact_fea_complete": False', strength)
        self.assertIn('rocker["shared_head_stud_nominal_diameter_mm"]', strength)
        self.assertNotIn('stud_diameter = float(rocker["mount_final_clearance_diameter_mm"])', strength)
        self.assertIn('"contract_sha256": sha256(args.contract)', strength)
        self.assertIn('"kinematics_sha256": sha256(args.kinematics)', strength)
        self.assertIn('"material_cards_qualified": bool(material["material_cards_qualified"])', strength)
        self.assertIn('"fatigue_rig_correlated": False', strength)
        self.assertIn('pivot_screen = contract["rocker_pivot_reaction_screen"]', strength)
        self.assertIn("pivot_envelope_load = spring_design_load * pivot_envelope_factor", strength)
        self.assertIn('rocker["rocker_arm_section_xz_mm"]', strength)
        self.assertIn('"actual_resultant_direction_complete": False', strength)
        self.assertIn('"rocker_pivot_resultant_load_complete": False', strength)
        self.assertIn('"carrier_step_sha256": sha256(args.step)', calculix)
        self.assertIn("design_load = spring_design_load * pivot_envelope_factor", calculix)
        self.assertIn('"actual_resultant_direction_complete": False', calculix)
        self.assertIn('"rocker_pivot_resultant_load_complete": False', calculix)
        self.assertIn('"finest_maximum_below_200c_screen_yield"', calculix)
        self.assertIn('"nonlinear_contact_complete": False', calculix)
        self.assertIn('"qualified_material_card": False', calculix)

    def test_head_topology_gate_is_computed_after_stl_reload(self):
        main_source = function_source(HEAD_MESH_SOURCE, "main")
        reload_position = main_source.index('final_topology = topology(exported_head)')
        gate_position = main_source.index('topology_printable = bool(', reload_position)
        self.assertGreater(gate_position, reload_position)

    def test_head_flow_core_is_bound_to_f36_report_and_secondary_volume_fails_closed(self):
        main_source = function_source(HEAD_MESH_SOURCE, "main")
        flow_source = function_source(HEAD_MESH_SOURCE, "load_flow_mesh")
        self.assertIn('expected_flow = geometry_report["files_local_only"]', main_source)
        self.assertIn('sha256(args.flow_core) != expected_flow["sha256"]', main_source)
        self.assertIn('args.flow_core.stat().st_size != int(expected_flow["bytes"])', main_source)
        self.assertIn("FLOW_DEBRIS_VOLUME_TOLERANCE_MM3", flow_source)
        self.assertIn("composante secondaire volumique refusée", flow_source)

    def test_oil_equations_are_dimensionally_consistent_at_nominal_hot_case(self):
        oil = self.contract["oil_system"]
        screen = self.contract["oil_hydraulic_screen"]
        viscosity = float(screen["dynamic_viscosity_pa_s_hot_110c"])
        density = float(screen["oil_density_kg_m3"])
        total_flow = float(screen["target_total_flow_l_min"]) / 60_000.0
        branch_flow = float(screen["target_flow_per_rocker_l_min"]) / 60_000.0
        lengths = screen["worst_path_lengths_mm"]
        segments = (
            (lengths["lateral_feed_d6"], oil["head_feed_lateral"]["diameter_mm"], total_flow),
            (lengths["header_d6"], oil["head_header"]["diameter_mm"], total_flow),
            (lengths["metering_branch_d3"], oil["four_metering_branches_diameter_mm"], branch_flow),
            (lengths["carrier_gallery_d5"], oil["carrier_gallery_diameter_mm"], branch_flow),
        )
        distributed_pressure_pa = sum(
            128.0
            * viscosity
            * (float(length_mm) / 1000.0)
            * flow_m3_s
            / (math.pi * (float(diameter_mm) / 1000.0) ** 4)
            for length_mm, diameter_mm, flow_m3_s in segments
        )
        branch_diameter_m = float(oil["four_metering_branches_diameter_mm"]) / 1000.0
        branch_velocity = branch_flow / (math.pi * branch_diameter_m**2 / 4.0)
        minor_pressure_pa = (
            float(screen["minor_loss_coefficient_worst_path"])
            * density
            * branch_velocity**2
            / 2.0
        )
        total_kpa = (distributed_pressure_pa + minor_pressure_pa) / 1000.0
        self.assertGreater(total_kpa, 0.0)
        self.assertLess(total_kpa, float(screen["maximum_hot_pressure_drop_kpa"]))
        self.assertFalse(self.contract["release_gates"]["oil_flow_pressure_and_drainage_correlated"])


class ManufacturingDefinitionF37EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("F37_EVIDENCE_DIR")
        cls.evidence = (
            Path(configured)
            if configured
            else ROOT / "work/917-scan-conforming-f37/cad"
        )
        report_path = cls.evidence / "f37-cad-report.json"
        if not report_path.is_file():
            raise unittest.SkipTest(
                "preuve CAO F37 absente; definir F37_EVIDENCE_DIR pour la verifier"
            )
        cls.report = json.loads(report_path.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_report_is_bound_to_the_current_contract_and_parent(self):
        self.assertEqual(self.report["phase"], "F37")
        self.assertEqual(self.report["inputs"]["contract_sha256"], sha256(CONTRACT))
        self.assertEqual(
            self.report["inputs"]["parent_head_sha256"],
            self.contract["parent"]["head_sha256"],
        )
        self.assertIn("release_blocked", self.report["status"])

    def test_report_has_expected_closed_occt_artifact_counts(self):
        artifacts = {item["id"]: item for item in self.report["artifacts"]}
        self.assertEqual(
            set(artifacts),
            {
                "rocker-carrier-as-printed",
                "four-rocker-envelopes",
                "two-rocker-shafts",
                "machining-allowance-volumes",
                "oil-gallery-core",
                "finish-machining-cutters",
            },
        )
        expected_solids = {
            "rocker-carrier-as-printed": 1,
            "four-rocker-envelopes": 4,
            "two-rocker-shafts": 2,
            "oil-gallery-core": 1,
        }
        for identifier, artifact in artifacts.items():
            for stage in ("created", "reopened_step"):
                metrics = artifact[stage]
                self.assertTrue(metrics["valid"], (identifier, stage))
                self.assertTrue(metrics["manifold"], (identifier, stage))
                self.assertTrue(metrics["all_solids_closed"], (identifier, stage))
                self.assertGreater(metrics["solid_count"], 0, (identifier, stage))
                self.assertGreater(metrics["volume_mm3"], 0.0, (identifier, stage))
            self.assertLessEqual(artifact["step_roundtrip_relative_volume_drift"], 1.0e-5)
        for identifier, count in expected_solids.items():
            self.assertEqual(artifacts[identifier]["created"]["solid_count"], count)
            self.assertEqual(artifacts[identifier]["reopened_step"]["solid_count"], count)

    def test_every_artifact_matches_recorded_size_hash_and_canonical_header(self):
        for artifact in self.report["artifacts"]:
            for kind in ("step", "stl"):
                record = artifact[kind]
                path = self.evidence / record["path"]
                self.assertTrue(path.is_file(), path)
                self.assertEqual(path.stat().st_size, record["bytes"], path)
                self.assertEqual(sha256(path), record["sha256"], path)
            step_path = self.evidence / artifact["step"]["path"]
            self.assertIn(
                "1970-01-01T00:00:00",
                step_path.read_text(encoding="utf-8")[:1024],
                step_path,
            )

    def test_report_checks_do_not_override_release_boundary(self):
        checks = self.report["checks"]
        self.assertTrue(checks["all_created_shapes_valid_and_closed"])
        self.assertTrue(checks["all_step_roundtrips_valid_and_closed"])
        self.assertTrue(checks["oil_core_is_one_connected_solid"])
        self.assertTrue(checks["oil_passages_declared_straight_drillable_or_open_ended"])
        self.assertFalse(checks["oil_passage_ends_verified_against_head_skin"])
        self.assertEqual(checks["rocker_carrier_interference_volume_mm3"], 0)
        self.assertEqual(checks["rocker_shaft_interference_volume_mm3"], 0)
        self.assertEqual(checks["rocker_window_size_xy_mm"], [15.0, 36.0])
        self.assertEqual(checks["rocker_arm_section_xz_mm"], [11.0, 12.0])
        self.assertTrue(checks["rocker_pivot_collinear_envelope_factor_consistent"])
        self.assertEqual(
            checks["rocker_to_carrier_window_clearances_mm"],
            {
                "arm_to_window_per_side_x": 2.0,
                "window_overcut_beyond_rail_per_side_y": 1.0,
                "boss_to_window_bottom_z": 0.5,
                "boss_to_window_top_z": 6.5,
            },
        )
        self.assertEqual(
            checks["rocker_to_carrier_window_minimum_clearance_mm"], 0.5
        )
        self.assertTrue(
            checks["rocker_to_carrier_window_minimum_clearance_at_least_0_5_mm"]
        )
        self.assertFalse(checks["whole_head_single_brep"])
        self.assertEqual(self.report["release_gates"], self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))

    def test_kinematic_report_is_bound_to_this_cad_report_when_supplied(self):
        kinematic_path = (
            self.evidence.parent
            / "kinematics"
            / "f37-rocker-kinematic-report.json"
        )
        if not kinematic_path.is_file():
            self.skipTest("rapport cinématique F37 non fourni avec la preuve CAO")
        kinematics = json.loads(kinematic_path.read_text(encoding="utf-8"))
        self.assertEqual(
            kinematics["inputs"]["cad_report_sha256"],
            sha256(self.evidence / "f37-cad-report.json"),
        )
        self.assertEqual(kinematics["inputs"]["contract_sha256"], sha256(CONTRACT))
        self.assertEqual(
            kinematics["inputs"]["geometry_report_sha256"],
            self.report["inputs"]["geometry_report_sha256"],
        )
        self.assertEqual(len(kinematics["cases"]), 4)
        self.assertTrue(kinematics["gates"]["static_brep_interference_zero"])
        self.assertFalse(kinematics["gates"]["measured_cam_profile_available"])
        self.assertFalse(kinematics["gates"]["dynamic_contact_and_flexure_fea_complete"])
        self.assertFalse(kinematics["gates"]["spintron_correlated"])

    def test_oil_report_is_bound_to_the_current_contract_when_supplied(self):
        oil_path = self.evidence.parent / "oil" / "f37-oil-hydraulic-report.json"
        if not oil_path.is_file():
            self.skipTest("rapport hydraulique F37 non fourni avec la preuve CAO")
        oil = json.loads(oil_path.read_text(encoding="utf-8"))
        self.assertEqual(oil["inputs"]["contract_sha256"], sha256(CONTRACT))
        self.assertTrue(oil["gates"]["two_methods_agree_within_1e_9"])
        self.assertTrue(oil["gates"]["laminar_assumption_valid"])
        self.assertFalse(oil["gates"]["physical_oil_rig_correlated"])

    def test_strength_report_is_bound_to_contract_and_kinematics_when_supplied(self):
        strength_path = (
            self.evidence.parent / "strength" / "f37-carrier-strength-report.json"
        )
        kinematic_path = (
            self.evidence.parent
            / "kinematics"
            / "f37-rocker-kinematic-report.json"
        )
        if not strength_path.is_file() or not kinematic_path.is_file():
            self.skipTest("rapports résistance/cinématique F37 incomplets")
        strength = json.loads(strength_path.read_text(encoding="utf-8"))
        self.assertEqual(strength["inputs"]["contract_sha256"], sha256(CONTRACT))
        self.assertEqual(strength["inputs"]["kinematics_sha256"], sha256(kinematic_path))
        expected_spring = (
            self.contract["component_material_and_load_screen"][
                "worst_open_spring_load_per_valve_n"
            ]
            * self.contract["component_material_and_load_screen"]["dynamic_load_factor"]
        )
        expected_pivot = expected_spring * self.contract["rocker_pivot_reaction_screen"][
            "collinear_upper_envelope_factor"
        ]
        self.assertAlmostEqual(
            strength["loads"]["spring_only_design_load_per_valve_n"], expected_spring
        )
        self.assertAlmostEqual(
            strength["loads"]["pivot_reaction_upper_envelope_per_valve_n"],
            expected_pivot,
        )
        self.assertEqual(strength["rocker"]["arm_section_xz_mm"], [11.0, 12.0])
        self.assertTrue(strength["gates"]["pivot_reaction_magnitude_upper_envelope_applied"])
        self.assertFalse(strength["gates"]["actual_resultant_direction_complete"])
        self.assertFalse(strength["gates"]["rocker_pivot_resultant_load_complete"])
        self.assertFalse(strength["gates"]["nonlinear_contact_fea_complete"])
        self.assertFalse(strength["gates"]["material_cards_qualified"])
        self.assertFalse(strength["gates"]["fatigue_rig_correlated"])

    def test_lpbf_report_is_bound_to_final_f37_but_keeps_failed_gates(self):
        lpbf_path = self.evidence.parent / "lpbf" / "f37-lpbf-manufacturing-report.json"
        if not lpbf_path.is_file():
            self.skipTest("rapport LPBF F37 non fourni avec la preuve CAO")
        lpbf = json.loads(lpbf_path.read_text(encoding="utf-8"))
        inputs = lpbf["inputs"]
        self.assertEqual(inputs["f37_contract"]["sha256"], sha256(CONTRACT))
        self.assertEqual(
            inputs["f37_cad_report"]["sha256"],
            sha256(self.evidence / "f37-cad-report.json"),
        )
        image = self.evidence.parent / "lpbf" / "917-head-f37-lpbf-manufacturing.png"
        self.assertEqual(image.stat().st_size, lpbf["artifacts"][image.name]["bytes"])
        self.assertEqual(sha256(image), lpbf["artifacts"][image.name]["sha256"])
        gates = lpbf["gates"]
        self.assertFalse(gates["sampled_p01_thickness_at_least_1_5_mm"])
        self.assertFalse(gates["coarse_layer_support_fraction_below_0_5_percent"])
        self.assertFalse(gates["coarse_trapped_void_screen_zero"])
        self.assertFalse(gates["calibrated_layer_activation_distortion_model"])
        self.assertFalse(gates["whole_head_single_valid_brep"])
        self.assertFalse(gates["metal_print_authorized"])
        self.assertEqual(
            lpbf["candidate_build"]["voxel_method"],
            "surface_voxel_components_plus_chunked_winding_number_without_fill_holes",
        )
        self.assertEqual(
            lpbf["candidate_build"]["thickness_method"],
            "sampled_inward_normal_ray_uniform_grid_exact_triangle_intersection",
        )

    def test_calculix_grid_report_is_bound_to_final_carrier_when_supplied(self):
        calculix_path = (
            self.evidence.parent
            / "carrier-calculix"
            / "f37-carrier-calculix-report.json"
        )
        if not calculix_path.is_file():
            self.skipTest("rapport CalculiX convergé F37 non fourni")
        calculix = json.loads(calculix_path.read_text(encoding="utf-8"))
        inputs = calculix["inputs"]
        self.assertEqual(inputs["contract_sha256"], sha256(CONTRACT))
        self.assertEqual(
            inputs["geometry_report_sha256"],
            self.report["inputs"]["geometry_report_sha256"],
        )
        carrier = next(
            item
            for item in self.report["artifacts"]
            if item["id"] == "rocker-carrier-as-printed"
        )
        carrier_step = self.evidence / carrier["step"]["path"]
        self.assertEqual(inputs["carrier_step_sha256"], sha256(carrier_step))
        self.assertEqual(inputs["carrier_step_sha256"], carrier["step"]["sha256"])

        cases = calculix["cases"]
        self.assertGreaterEqual(len(cases), 3)
        self.assertTrue(
            all(
                cases[index]["mesh"]["mesh_size_mm"]
                > cases[index + 1]["mesh"]["mesh_size_mm"]
                for index in range(len(cases) - 1)
            )
        )
        self.assertTrue(
            all(
                cases[index]["mesh"]["elements"]
                < cases[index + 1]["mesh"]["elements"]
                for index in range(len(cases) - 1)
            )
        )
        expected_spring = (
            self.contract["component_material_and_load_screen"][
                "worst_open_spring_load_per_valve_n"
            ]
            * self.contract["component_material_and_load_screen"]["dynamic_load_factor"]
        )
        expected_pivot = expected_spring * self.contract["rocker_pivot_reaction_screen"][
            "collinear_upper_envelope_factor"
        ]
        for case in cases:
            mesh = case["mesh"]
            self.assertAlmostEqual(mesh["spring_only_design_load_per_zone_n"], expected_spring)
            self.assertAlmostEqual(mesh["design_load_per_zone_n"], expected_pivot)
            self.assertEqual(
                mesh["load_classification"],
                "pivot_reaction_magnitude_upper_envelope_applied_along_valve_axis_screen_direction",
            )
            self.assertFalse(mesh["actual_resultant_direction_complete"])
        gates = calculix["gates"]
        self.assertTrue(gates["p95_grid_change_below_5_percent"])
        self.assertTrue(gates["displacement_grid_change_below_5_percent"])
        self.assertTrue(gates["finest_p99_below_200c_screen_yield"])
        self.assertTrue(gates["finest_displacement_below_0_15_mm"])
        self.assertTrue(gates["multiaxial_valve_axis_load_case_complete"])
        self.assertFalse(gates["finest_maximum_below_200c_screen_yield"])
        self.assertTrue(gates["pivot_reaction_magnitude_upper_envelope_applied"])
        self.assertFalse(gates["actual_resultant_direction_complete"])
        self.assertFalse(gates["rocker_pivot_resultant_load_complete"])
        self.assertFalse(gates["nonlinear_contact_complete"])
        self.assertFalse(gates["qualified_material_card"])


if __name__ == "__main__":
    unittest.main()
