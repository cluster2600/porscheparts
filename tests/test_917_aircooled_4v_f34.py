"""Garde-fous de la campagne F34 de culasse 4V refroidie par air."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/aircooled-4v-scan-f34.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f34"
PUBLISHER = ROOT / "twins/reference-917-engine/source/publish_aircooled_4v_f34.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AirCooledFourValveF34Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load(CONTRACT)
        cls.report = load(EVIDENCE / "report.json")
        cls.publication = load(EVIDENCE / "publication.json")
        cls.publisher = load_module("publish_aircooled_4v_f34", PUBLISHER)

    def test_scan_boundary_and_four_valve_scope_are_explicit(self):
        self.assertEqual(self.contract["phase"], "F34")
        source = self.report["source_geometry"]
        self.assertFalse(source["engine_case_scan"]["contains_heads"])
        self.assertFalse(source["engine_case_scan"]["absolute_scale_confirmed"])
        self.assertIn("morphology", source["head_morphology_scan"]["use"])
        self.assertEqual(self.contract["cad"]["valves"]["intake"]["count"], 2)
        self.assertEqual(self.contract["cad"]["valves"]["exhaust"]["count"], 2)

    def test_geometry_and_render_are_local_only_not_published(self):
        geometry = load(EVIDENCE / "geometry-report.json")
        self.assertEqual(geometry["geometry"]["solid_count"], 1)
        self.assertEqual(geometry["geometry"]["fin_count"], 18)
        self.assertEqual(geometry["geometry"]["valve_count"], 4)
        self.assertGreater(geometry["geometry"]["external_cooling_envelope"]["surface_area_m2"], 0.60)
        binary_names = {
            "917-head-aircooled-4v-f34-process-prototype.step",
            "product-aircooled-4v-f34.png",
        }
        self.assertTrue(all(not (EVIDENCE / name).exists() for name in binary_names))
        self.assertTrue(binary_names.isdisjoint(self.publication["files"]))
        self.assertEqual(self.publication["schema_version"], "1.1.0")
        self.assertEqual(
            self.publication["status"],
            "tracked_textual_metadata_only_geometry_and_render_local_unpublished",
        )
        self.assertTrue(self.publication["output_policy"]["git_ignored_work_root_required"])
        self.assertTrue(self.publication["output_policy"]["geometry_and_render_local_only"])
        self.assertFalse(self.publication["output_policy"]["publication_authorized"])
        self.assertFalse(self.publication["output_policy"]["tracked_output_authorized"])

    def test_publisher_refuses_tracked_or_external_output_roots(self):
        local = ROOT / "work/917-aircooled-4v-f34-publication"
        self.assertEqual(self.publisher.require_local_unpublished_output(local), local.resolve())
        with self.assertRaisesRegex(ValueError, "doit rester sous work"):
            self.publisher.require_local_unpublished_output(EVIDENCE)
        with self.assertRaisesRegex(ValueError, "doit rester sous work"):
            self.publisher.require_local_unpublished_output(Path("/tmp/f34-published"))
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("--output work/917-aircooled-4v-f34-publication", makefile)
        self.assertIn("work/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_two_external_cooling_methods_really_executed(self):
        cooling = self.report["external_cooling_3d_cross_verification"]
        openfoam = cooling["method_a"]
        fluidx = cooling["method_b"]
        self.assertEqual(openfoam["solver"], "OpenFOAM_14_fluid_kOmegaSST")
        self.assertTrue(openfoam["solver_completed"])
        self.assertTrue(openfoam["mesh"]["standard_check_mesh_passed"])
        self.assertGreater(openfoam["mesh"]["cells"], 500_000)
        self.assertEqual(fluidx["solver"], "FluidX3D_D3Q19_TRT_FP32")
        self.assertEqual(len(fluidx["rows"]), 3)
        self.assertTrue(fluidx["all_runs_statistically_converged"])
        self.assertFalse(openfoam["mesh_independence_demonstrated"])
        self.assertGreater(cooling["openfoam_mass_flow_to_design_ratio"], 5.0)
        self.assertGreater(cooling["fluidx3d_mass_flow_to_design_ratio"], 5.0)
        self.assertFalse(cooling["boundary_mass_flow_matches_design"])
        self.assertFalse(cooling["cross_method_passed"])

    def test_x86_images_are_smoked_and_open_hfdib_is_only_assessed(self):
        audit = load(EVIDENCE / "toolchain-audit.json")
        self.assertEqual(audit["images"]["cae_linux_amd64"]["architecture"], "amd64")
        self.assertTrue(audit["images"]["cae_linux_amd64"]["runtime_smoke_passed"])
        self.assertTrue(audit["images"]["fluidx3d_linux_amd64"]["runtime_smoke_passed"])
        self.assertFalse(audit["remote_compute"]["vast_rental_used"])
        hfdib = self.report["toolchain"]["open_hfdib_assessment"]
        self.assertTrue(hfdib["evaluated"])
        self.assertFalse(hfdib["selected_for_f34"])

    def test_calculix_mesh_sequence_blocks_release_on_peak_stress(self):
        fea = self.report["thermomechanical_fea"]
        self.assertEqual(fea["solver"], "CalculiX_2.21")
        self.assertEqual(len(fea["rows"]), 3)
        self.assertGreater(fea["rows"][-1]["linear_tetrahedra"], 300_000)
        self.assertFalse(fea["finest_mesh_maximum_below_hot_yield"])
        self.assertFalse(fea["stress_mesh_independence_passed"])
        self.assertTrue(fea["displacement_mesh_independence_passed"])
        self.assertFalse(fea["nonlinear_contact_creep_fatigue_tmf_included"])

    def test_two_vs_four_valve_comparison_is_preserved_as_equivalent_port_only(self):
        comparison = self.report["two_vs_four_valve_reference"]
        self.assertGreater(comparison["four_valve_fine_mass_flow_gain_percent"], 0.0)
        self.assertGreater(comparison["quasi_steady_virtual_flowbench_gain_percent"], 0.0)
        self.assertFalse(comparison["full_scan_seeded_2v_4v_cross_validation_complete"])

    def test_cantera_wiebe_disagreement_and_physicsnemo_block_are_retained(self):
        cycle = self.report["cycle_cross_verification"]
        self.assertTrue(cycle["power_cross_check_passed"])
        self.assertFalse(cycle["peak_pressure_cross_check_passed"])
        self.assertIn("Cantera", cycle["method_a"]["id"])
        physicsnemo = self.report["physicsnemo"]
        self.assertEqual(physicsnemo["converged_classical_cases"], 0)
        self.assertFalse(physicsnemo["training_authorized"])
        self.assertFalse(physicsnemo["training_executed"])

    def test_omniverse_preflight_is_sanitized_and_fail_closed(self):
        path = EVIDENCE / "omniverse-preflight.json"
        preflight = load(path)
        self.assertEqual(preflight["status"], "blocked")
        serialized = path.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("/private/tmp/", serialized)
        self.assertFalse(self.report["omniverse"]["simready_conversion_executed"])

    def test_all_release_gates_are_closed_and_files_are_hashed(self):
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))
        claims = self.report["claims"]
        self.assertFalse(claims["metal_print_authorized"])
        self.assertFalse(claims["engine_start_authorized"])
        self.assertFalse(claims["physical_validation_complete"])
        for relative, expected in self.publication["files"].items():
            path = EVIDENCE / relative
            self.assertTrue(path.is_file())
            self.assertIn(path.suffix.lower(), {".json", ".md"})
            self.assertEqual(sha256(path), expected)


if __name__ == "__main__":
    unittest.main()
