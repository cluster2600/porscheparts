#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import gzip
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f38-cooling-redesign.json"
SOURCE = ROOT / "twins/reference-917-engine/source/run_f38_cooling_redesign.py"
PUBLISHED = ROOT / "twins/reference-917-engine/evidence/f38-cooling-redesign"
SPEC = importlib.util.spec_from_file_location("f38_cooling", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class F38CoolingRedesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_keeps_release_gates_false(self) -> None:
        gates = self.contract["release_gates"]
        self.assertFalse(gates["absolute_scale_confirmed"])
        self.assertFalse(gates["full_head_conjugate_heat_transfer_complete"])
        self.assertFalse(gates["hot_material_coupon_card_qualified"])
        self.assertFalse(gates["metal_print_authorized"])
        self.assertFalse(gates["engine_start_authorized"])

    def test_boundary_conditions_reuse_prior_nominal_point(self) -> None:
        bc = self.contract["boundary_conditions"]
        self.assertEqual(bc["nominal_head_air_mass_flow_kg_s"], 0.85)
        self.assertEqual(bc["air_inlet_temperature_k"], 308.15)
        self.assertEqual(bc["maximum_burst_bridge_temperature_c"], 260.0)

    def test_fin_pack_is_not_thinner_than_lpbf_screen(self) -> None:
        design = self.contract["f38_fin_pack"]
        self.assertGreaterEqual(design["minimum_as_designed_thickness_mm"], 1.5)
        self.assertGreaterEqual(design["fin_thickness_mm"], 1.5)
        self.assertGreater(design["clear_gap_mm"], design["fin_thickness_mm"])
        self.assertEqual(design["fin_pitch_mm"], 6.5)
        self.assertEqual(design["passage_count_equivalent"], 22)

    def test_passage_velocity_is_geometry_derived(self) -> None:
        bc = self.contract["boundary_conditions"]
        design = self.contract["f38_fin_pack"]
        expected = (
            bc["nominal_head_air_mass_flow_kg_s"]
            * design["air_capture_fraction"]
            / (bc["air_density_kg_m3"] * design["open_passage_area_m2"])
        )
        self.assertAlmostEqual(design["passage_velocity_m_s"], expected, delta=0.08)

    def test_global_surface_is_scan_proxy_not_rejected_brep(self) -> None:
        design = self.contract["f38_fin_pack"]
        self.assertAlmostEqual(design["whole_head_wetted_surface_area_m2"], 0.18486967359948758)
        self.assertIn("F37_scan_conforming", design["whole_head_wetted_surface_area_status"])
        projection = MODULE.thermal_projection(self.contract, 220.0)
        self.assertFalse(projection["wetted_area_measured_from_F38_BRep"])
        self.assertIn("not_F38_BRep", projection["global_temperature_status"])

    def test_analytical_method_is_finite_and_turbulent(self) -> None:
        result = MODULE.analytical(self.contract)
        self.assertTrue(all(math.isfinite(value) for value in result.values() if isinstance(value, float)))
        self.assertGreater(result["reynolds"], 10000)
        self.assertGreater(result["effective_h_w_m2k"], 0)
        self.assertGreater(result["pressure_drop_straight_channel_pa"], 0)
        self.assertFalse(result["hot_material_coupon_card_qualified"])

    def test_variant_sweep_contains_pressure_and_temperature_failures(self) -> None:
        variants = MODULE.design_sweep(self.contract)
        self.assertEqual(len(variants), 4)
        self.assertTrue(any(not item["blower_pressure_screen_passed"] for item in variants))
        self.assertTrue(all(not item["temperature_screen_passed"] for item in variants))
        self.assertTrue(all("not_F38_BRep" in item["global_temperature_status"] for item in variants))

    def test_prepared_case_contains_real_thermal_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case = Path(directory) / "coarse"
            MODULE.prepare_case(case, self.contract, [18, 6, 4])
            self.assertIn("hotFins", (case / "system/blockMeshDict").read_text())
            self.assertIn("wallHeatFlux", (case / "system/controlDict").read_text())
            self.assertIn("fixedValue", (case / "0/T").read_text())
            metadata = json.loads((case / "case-metadata.json").read_text())
            self.assertFalse(metadata["absolute_scale_confirmed"])
            self.assertFalse(metadata["release_claim"])

    def test_published_report_is_converged_but_rejected(self) -> None:
        report = json.loads((PUBLISHED / "f38-cooling-cross-check.json").read_text())
        self.assertEqual([item["cell_count"] for item in report["openfoam"]["cases"]], [17280, 138240])
        self.assertTrue(report["openfoam"]["two_grid_h_agreement_below_5_percent"])
        self.assertTrue(report["openfoam"]["fine_energy_balance_below_5_percent"])
        self.assertTrue(report["cross_method"]["h_agreement_below_20_percent"])
        self.assertFalse(report["cross_method"]["pressure_agreement_below_20_percent"])
        self.assertGreater(report["cross_method"]["pressure_drop_relative_difference"], 0.20)
        self.assertGreater(report["thermal_projection"]["from_openfoam"]["bridge_temperature_c"], 300.0)
        self.assertFalse(report["decision"]["temperature_screen_passed"])
        self.assertFalse(report["decision"]["whole_head_CHT_complete"])
        self.assertFalse(report["decision"]["metal_print_authorized"])
        self.assertFalse(report["decision"]["engine_start_authorized"])

    def test_published_manifest_and_solver_logs(self) -> None:
        publication = json.loads((PUBLISHED / "publication.json").read_text())
        for relative, expected in publication["files"].items():
            path = PUBLISHED / relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(path.stat().st_size, expected["bytes"])
            self.assertEqual(digest, expected["sha256"])
        for case in ("coarse", "fine"):
            case_dir = PUBLISHED / "openfoam" / case
            with gzip.open(case_dir / "log.checkMesh.gz", "rt", errors="replace") as stream:
                self.assertIn("Mesh OK", stream.read())
            with gzip.open(case_dir / "log.foamRun.gz", "rt", errors="replace") as stream:
                self.assertIn("End", stream.read())


if __name__ == "__main__":
    unittest.main()
