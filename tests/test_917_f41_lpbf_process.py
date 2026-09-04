#!/usr/bin/env python3
"""Contrat fail-closed de l'ecran LPBF multi-echelle F41."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f41-lpbf-process"
LOCAL_STEP = ROOT / "work/917-f41-lpbf/917-head-lpbf-candidate-f41.step"
GEOMETRY = EVIDENCE / "917-head-lpbf-candidate-f41-report.json"
AUDIT = EVIDENCE / "917-head-lpbf-candidate-f41-audit.json"
MACRO = EVIDENCE / "917-head-lpbf-macro-f41-report.json"
CALCULIX = EVIDENCE / "917-head-lpbf-calculix-f41-report.json"
ADDITIVE = EVIDENCE / "917-head-lpbf-additivefoam-f41-report.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class F41LpbfProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load(GEOMETRY)
        cls.audit = load(AUDIT)
        cls.macro = load(MACRO)
        cls.calculix = load(CALCULIX)
        cls.additive = load(ADDITIVE)

    def test_step_is_hash_locked_and_roundtrips_as_one_solid(self) -> None:
        self.assertEqual(self.geometry["phase"], "F41")
        step = self.geometry["files"]["step"]
        self.assertEqual(step["repository_policy"], "local_only_scan_derived_BRep_rights_unverified")
        self.assertTrue(step["path"].startswith("local-only://"))
        self.assertFalse(any(EVIDENCE.glob("*.step")))
        self.assertFalse(any(EVIDENCE.glob("*.stl")))
        if LOCAL_STEP.is_file():
            self.assertEqual(step["sha256"], sha256(LOCAL_STEP))
            self.assertGreater(LOCAL_STEP.stat().st_size, 10_000_000)
        self.assertTrue(self.geometry["step_roundtrip"]["valid"])
        self.assertEqual(self.geometry["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(self.geometry["step_roundtrip"]["shell_count"], 1)
        self.assertTrue(self.geometry["mesh"]["watertight"])
        self.assertEqual(self.geometry["mesh"]["connected_components"], 1)

    def test_architecture_and_post_print_oil_policy_are_explicit(self) -> None:
        topology = self.geometry["topology"]
        self.assertEqual(topology["architecture"], "four_valve_twin_ignition_air_cooled")
        self.assertEqual(topology["valve_count"], 4)
        self.assertEqual(topology["spark_plug_count"], 2)
        self.assertFalse(topology["oil"]["printed_as_internal_cavity"])
        self.assertTrue(topology["oil"]["post_print_drilling_required"])
        self.assertTrue(topology["oil"]["straight_open_ended_after_machining"])

    def test_machine_orientation_and_40_um_schedule_are_consistent(self) -> None:
        machine = self.additive["machine_reference"]
        process = self.additive["published_process_reference"]
        selected = self.audit["orientation_and_support"]["selected"]
        layers = self.audit["virtual_layer_activation"]
        self.assertEqual(machine["build_volume_mm"], [420, 420, 450])
        self.assertEqual(machine["laser_configuration"], "2 x 500 W fibre")
        self.assertTrue(machine["fit_screen_for_f41"])
        self.assertTrue(selected["fits_inherited_250x250x325_envelope_if_scale_is_mm"])
        self.assertEqual(layers["layer_height_um"], process["layer_thickness_mm"] * 1000.0)
        self.assertEqual(layers["layer_count"], 5153)
        self.assertTrue(layers["complete_layer_schedule_generated"])
        self.assertFalse(layers["machine_build_file_generated"])

    def test_published_audit_is_bound_to_the_sanitized_geometry_report(self) -> None:
        report_input = self.audit["inputs"]["build_report"]
        self.assertEqual(report_input["sha256"], sha256(GEOMETRY))
        self.assertEqual(len(report_input["execution_sha256"]), 64)

    def test_additivefoam_ran_three_real_mpi_cases(self) -> None:
        self.assertEqual(
            self.additive["software"],
            {
                "additivefoam_revision": "9c05c5eb54db03faa342b14b0806efe740de8c44",
                "openfoam_revision": "7b05503f98a85be88af930df48623b4d152bfc35",
            },
        )
        self.assertEqual(self.additive["published_process_reference"]["mpi_ranks_per_case"], 16)
        self.assertEqual(sorted(self.additive["sensitivities"]), ["400", "450", "500"])
        for power, run in self.additive["sensitivities"].items():
            self.assertTrue(run["completed"], power)
            self.assertEqual(run["return_code"], 0)
            self.assertEqual(len(run["layer_log_checks"]), 2)
            self.assertEqual(
                [item["final_simulation_time_s"] for item in run["layer_log_checks"]],
                [0.015, 0.03],
            )
            self.assertTrue(all(item["solver_end_marker"] for item in run["layer_log_checks"]))
            self.assertTrue(all(not item["fatal_error"] for item in run["layer_log_checks"]))
            self.assertTrue(all(len(item["sha256"]) == 64 for item in run["layer_log_checks"]))

    def test_power_sensitivity_is_numerical_but_hits_solver_cap(self) -> None:
        results = self.additive["results"]
        p99 = [results[str(power)]["temperature_p99_k"] for power in (400, 450, 500)]
        lengths = [
            results[str(power)]["solver_melt_pool_dimensions"]["maximum_length_mm"]
            for power in (400, 450, 500)
        ]
        self.assertTrue(p99[0] < p99[1] < p99[2])
        self.assertTrue(lengths[0] < lengths[1] < lengths[2])
        self.assertAlmostEqual(lengths[-1], 0.83772368)
        self.assertAlmostEqual(
            results["500"]["solver_melt_pool_dimensions"]["maximum_width_mm"],
            0.24428982,
        )
        self.assertAlmostEqual(
            results["500"]["solver_melt_pool_dimensions"]["maximum_depth_mm"],
            0.28445928,
        )
        self.assertTrue(all(results[str(power)]["finite"] for power in (400, 450, 500)))
        self.assertTrue(all(results[str(power)]["solver_temperature_cap_hit"] for power in (400, 450, 500)))
        self.assertFalse(self.additive["gates"]["temperature_cap_not_hit"])
        self.assertFalse(self.additive["gates"]["local_process_screen_passes"])

    def test_whole_part_macro_model_preserves_its_limitations(self) -> None:
        self.assertTrue(self.macro["material_assumptions"]["temperature_dependence_included"])
        self.assertAlmostEqual(self.macro["results"]["maximum_temperature_k"], 1099.9295654296875)
        self.assertAlmostEqual(self.macro["results"]["maximum_free_thermal_strain_proxy"], 0.013478985987603664)
        self.assertFalse(self.macro["gates"]["mesh_convergence_complete"])
        self.assertFalse(self.macro["gates"]["machine_scan_strategy_calibrated"])
        self.assertFalse(self.macro["gates"]["lpbf_process_released"])

    def test_calculix_displacement_converges_but_stress_does_not(self) -> None:
        convergence = self.calculix["finest_pair_convergence"]
        finest = min(self.calculix["cases"], key=lambda item: item["pitch_mm"])
        self.assertEqual(finest["pitch_mm"], 3.0)
        self.assertAlmostEqual(finest["results"]["maximum_displacement_mm"], 0.5436294433869308)
        self.assertLess(convergence["maximum_displacement_relative_difference"], 0.05)
        self.assertGreater(convergence["p95_stress_relative_difference"], 0.10)
        self.assertTrue(self.calculix["gates"]["displacement_mesh_difference_below_5_percent"])
        self.assertFalse(self.calculix["gates"]["p95_stress_mesh_difference_below_10_percent"])
        self.assertFalse(self.calculix["gates"]["support_contact_and_release_simulated"])

    def test_geometry_failures_and_all_release_authorizations_stay_closed(self) -> None:
        gates = self.audit["gates"]
        self.assertTrue(gates["no_closed_void_detected_at_both_voxel_pitches"])
        self.assertFalse(gates["all_triangle_chords_resolved"])
        self.assertFalse(gates["all_resolved_chords_at_least_1_5_mm"])
        self.assertFalse(gates["machine_scan_path_and_supports_sliced"])
        self.assertFalse(gates["metal_print_authorized"])
        self.assertFalse(gates["engine_start_authorized"])
        self.assertFalse(self.additive["gates"]["supplier_parameter_card_qualified"])
        self.assertFalse(self.additive["gates"]["physical_coupon_qualified"])
        self.assertFalse(self.additive["gates"]["metal_print_authorized"])

    def test_images_and_video_are_hash_locked(self) -> None:
        image = EVIDENCE / "917-head-lpbf-additivefoam-f41.png"
        video = EVIDENCE / "917-head-lpbf-additivefoam-f41.mp4"
        self.assertEqual(image.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertIn(b"ftyp", video.read_bytes()[:32])
        self.assertEqual(sha256(image), self.additive["artifacts"][image.name]["sha256"])
        self.assertEqual(sha256(video), self.additive["artifacts"][video.name]["sha256"])


if __name__ == "__main__":
    unittest.main()
