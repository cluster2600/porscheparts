"""Contrôle hors ``work/`` des preuves publiées de la définition F37."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f37-manufacturing-definition.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f37-manufacturing-definition"
PUBLICATION = EVIDENCE / "publication.json"
PUBLISHER = ROOT / "twins/reference-917-engine/source/publish_f37_manufacturing_evidence.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


class F37PublishedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publication = load_json("publication.json")

    def test_manifest_is_complete_and_every_hash_matches(self):
        declared = self.publication["files"]
        actual = {
            path.name
            for path in EVIDENCE.iterdir()
            if path.is_file() and path.name != "publication.json"
        }
        self.assertEqual(set(declared), actual)
        for name, digest in declared.items():
            self.assertEqual(sha256(EVIDENCE / name), digest, name)
        self.assertEqual(self.publication["contract"]["sha256"], sha256(CONTRACT))
        self.assertEqual(
            self.publication["publication_method"],
            "fail_closed_allowlist_atomic_file_replacement_manifest_written_last",
        )

    def test_publisher_is_allowlisted_atomic_and_fail_closed(self):
        source = PUBLISHER.read_text(encoding="utf-8")
        self.assertIn("sources = {", source)
        self.assertIn("fichiers résiduels hors allowlist", source)
        self.assertIn("os.replace(temporary_manifest", source)
        self.assertIn("chaîne SHA F37 incohérente", source)
        self.assertIn("cas de charge pivot F37 incohérent", source)
        self.assertIn('"rocker_pivot_resultant_load_complete": False', source)

    def test_no_raw_scan_or_derived_full_head_mesh_is_published(self):
        forbidden_suffixes = {".obj", ".ply", ".stl", ".3mf"}
        self.assertFalse(
            [path.name for path in EVIDENCE.iterdir() if path.suffix.lower() in forbidden_suffixes]
        )
        self.assertTrue((EVIDENCE / "f37-nvidia-direct-usda-normals-geometry.json").is_file())

    def test_report_chain_is_bound_to_contract_cad_and_carrier_step(self):
        contract_sha = sha256(CONTRACT)
        cad_sha = sha256(EVIDENCE / "f37-cad-report.json")
        kinematics_sha = sha256(EVIDENCE / "f37-rocker-kinematic-report.json")
        carrier_sha = sha256(EVIDENCE / "rocker-carrier-as-printed.step")

        cad = load_json("f37-cad-report.json")
        kinematics = load_json("f37-rocker-kinematic-report.json")
        oil = load_json("f37-oil-hydraulic-report.json")
        strength = load_json("f37-carrier-strength-report.json")
        calculix = load_json("f37-carrier-calculix-report.json")
        lpbf = load_json("f37-lpbf-manufacturing-report.json")
        head_mesh = load_json("f37-printable-head-mesh-report.json")

        self.assertEqual(cad["inputs"]["contract_sha256"], contract_sha)
        self.assertEqual(kinematics["inputs"]["contract_sha256"], contract_sha)
        self.assertEqual(
            kinematics["inputs"]["geometry_report_sha256"],
            cad["inputs"]["geometry_report_sha256"],
        )
        self.assertEqual(kinematics["inputs"]["cad_report_sha256"], cad_sha)
        self.assertEqual(oil["inputs"]["contract_sha256"], contract_sha)
        self.assertEqual(strength["inputs"]["contract_sha256"], contract_sha)
        self.assertEqual(strength["inputs"]["kinematics_sha256"], kinematics_sha)
        self.assertEqual(calculix["inputs"]["contract_sha256"], contract_sha)
        self.assertEqual(calculix["inputs"]["carrier_step_sha256"], carrier_sha)
        self.assertEqual(
            calculix["toolchain"]["runtime_reproducibility"],
            "local_runtime_snapshot_not_portably_reproducible",
        )
        self.assertFalse(calculix["toolchain"]["registry_digest_available"])
        self.assertTrue(calculix["gates"]["multiaxial_valve_axis_load_case_complete"])
        self.assertTrue(calculix["gates"]["pivot_reaction_magnitude_upper_envelope_applied"])
        self.assertFalse(calculix["gates"]["actual_resultant_direction_complete"])
        self.assertFalse(calculix["gates"]["rocker_pivot_resultant_load_complete"])
        self.assertFalse(calculix["gates"]["finest_maximum_below_200c_screen_yield"])
        for case in calculix["cases"]:
            self.assertEqual(
                case["mesh"]["load_direction"],
                "along_each_valve_axis_in_local_yz_plane_screen_direction_only",
            )
            self.assertAlmostEqual(case["mesh"]["design_load_per_zone_n"], 4080.7)
            self.assertTrue(any(abs(vector[0]) > 1200.0 for vector in case["mesh"]["load_vectors_yz_n"]))
        self.assertEqual(
            calculix["inputs"]["geometry_report_sha256"],
            cad["inputs"]["geometry_report_sha256"],
        )
        self.assertEqual(lpbf["inputs"]["f37_contract"]["sha256"], contract_sha)
        self.assertEqual(lpbf["inputs"]["f37_cad_report"]["sha256"], cad_sha)
        self.assertEqual(head_mesh["inputs"]["contract_sha256"], contract_sha)
        self.assertEqual(head_mesh["inputs"]["cad_report_sha256"], cad_sha)
        linkage = lpbf["validated_linkage"]
        exact_head_sha = head_mesh["local_only_artifacts"][
            "917-head-f37-printable-proof.local.stl"
        ]["sha256"]
        self.assertEqual(linkage["printability_head_sha256"], exact_head_sha)
        self.assertEqual(linkage["f37_head_artifact_sha256"], exact_head_sha)
        self.assertTrue(linkage["head_sha256_equal"])
        self.assertEqual(
            linkage["printability_geometry_report_sha256"],
            head_mesh["inputs"]["geometry_report_sha256"],
        )
        self.assertTrue(linkage["geometry_report_sha256_equal"])

    def test_numerical_passes_do_not_open_physical_release_gates(self):
        gates = self.publication["release_gates"]
        self.assertTrue(all(value is False for value in gates.values()))
        self.assertFalse(load_json("f37-carrier-calculix-report.json")["gates"]["nonlinear_contact_complete"])
        self.assertFalse(load_json("f37-carrier-calculix-report.json")["gates"]["qualified_material_card"])
        self.assertFalse(
            load_json("f37-carrier-calculix-report.json")["gates"][
                "rocker_pivot_resultant_load_complete"
            ]
        )
        self.assertFalse(load_json("f37-oil-hydraulic-report.json")["gates"]["physical_oil_rig_correlated"])
        self.assertFalse(load_json("f37-lpbf-manufacturing-report.json")["gates"]["metal_print_authorized"])
        lpbf = load_json("f37-lpbf-manufacturing-report.json")
        self.assertEqual(
            lpbf["candidate_build"]["voxel_method"],
            "surface_voxel_components_plus_chunked_winding_number_without_fill_holes",
        )
        self.assertEqual(
            lpbf["candidate_build"]["thickness_method"],
            "sampled_inward_normal_ray_uniform_grid_exact_triangle_intersection",
        )
        self.assertGreater(lpbf["candidate_build"]["coarse_trapped_void_volume_cm3"], 0.0)
        self.assertFalse(lpbf["gates"]["coarse_trapped_void_screen_zero"])
        self.assertLessEqual(
            lpbf["candidate_build"]["thickness_spatial_index_triangle_references"],
            lpbf["candidate_build"]["thickness_spatial_index_reference_limit"],
        )
        self.assertAlmostEqual(
            lpbf["candidate_build"]["head_mass_kg_if_scale_and_density_are_correct"],
            2.8429375901606653,
        )
        self.assertFalse(
            lpbf["gates"]["candidate_bare_head_mass_below_f36_2_83_kg_target"]
        )

    def test_corrected_stud_and_rocker_equations_are_preserved(self):
        strength = load_json("f37-carrier-strength-report.json")
        mount = strength["mount"]
        self.assertAlmostEqual(mount["shared_head_stud_nominal_diameter_mm"], 10.0)
        self.assertAlmostEqual(mount["carrier_finished_clearance_diameter_mm"], 10.74)
        spring_load = strength["loads"]["spring_only_design_load_per_valve_n"]
        self.assertAlmostEqual(spring_load, 1898.0)
        pivot_load = strength["loads"]["pivot_reaction_upper_envelope_per_valve_n"]
        self.assertAlmostEqual(pivot_load, 4080.7)
        self.assertAlmostEqual(
            strength["loads"]["pivot_reaction_collinear_upper_envelope_factor"],
            2.15,
        )
        expected_shear = pivot_load / (math.pi * 10.0**2 / 4.0)
        self.assertAlmostEqual(
            mount["shared_head_stud_nominal_screen_shear_stress_mpa"],
            expected_shear,
            places=9,
        )

        kinematics = load_json("f37-rocker-kinematic-report.json")
        ratio = kinematics["inputs"]["target_rocker_ratio"]
        for case in kinematics["cases"]:
            self.assertAlmostEqual(
                case["cam_side_lever_mm"],
                case["effective_tangential_lever_mm"] / ratio,
                places=9,
            )

        cad = load_json("f37-cad-report.json")
        self.assertTrue(cad["checks"]["seat_guide_allowances_follow_finish_cutter_valve_axes"])
        self.assertEqual(
            cad["checks"]["machining_allowance_valve_axis_tilt_y_deg"],
            {"intake": -18.0, "exhaust": 18.0},
        )

    def test_known_validator_and_cooling_conflicts_remain_blocking(self):
        conflicts = self.publication["known_conflicts"]
        manifold = conflicts["stl_vertex_manifold"]
        self.assertEqual(manifold["local_custom_audit_non_manifold_vertices"], 0)
        self.assertEqual(manifold["nvidia_exact_validator_non_manifold_vertices"], 8047)
        self.assertFalse(manifold["resolved"])
        self.assertTrue(manifold["blocking"])

        head_mesh = load_json("f37-printable-head-mesh-report.json")
        nvidia = head_mesh["nvidia_asset_validator_observation"]
        self.assertEqual(nvidia["rule"], "VG.007")
        self.assertEqual(nvidia["non_manifold_vertex_count"], 8047)
        self.assertFalse(nvidia["vg007_clear"])
        self.assertFalse(head_mesh["gates"]["independent_topology_validators_agree"])
        self.assertTrue(head_mesh["gates"]["geometry_redesign_required"])
        self.assertFalse(head_mesh["gates"]["metal_print_authorized"])

        cooling = conflicts["external_cooling_cross_solver"]
        self.assertGreater(cooling["fluidx3d_openfoam_heat_relative_difference"], 0.05)
        self.assertGreater(cooling["openfoam_linked_solid_maximum_c"], 260.0)
        self.assertFalse(cooling["resolved"])
        self.assertTrue(cooling["blocking"])

        pivot = conflicts["rocker_pivot_resultant"]
        self.assertAlmostEqual(pivot["spring_only_design_load_per_valve_n"], 1898.0)
        self.assertAlmostEqual(pivot["pivot_magnitude_upper_envelope_per_valve_n"], 4080.7)
        self.assertFalse(pivot["actual_resultant_direction_complete"])
        self.assertFalse(pivot["resolved"])
        self.assertTrue(pivot["blocking"])


if __name__ == "__main__":
    unittest.main()
