"""Etapes 02 et 03 du pipeline AM pour la bague de commodo F1.

Ces controles ne disent pas que la piece est fabricable. Ils verifient que ce
qui est publie comme criblage geometrique est bien lie au master par empreinte,
que le maillage analyse est unique et etanche, que toutes les couches ont ete
reellement tranchees, et surtout que **les portes de procede restent fermees**.
Un criblage qui ouvrirait une porte de fabrication sans coupon ni machine serait
un faux, et c'est cela que le test cherche.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-INT-SWITCH-TRIM-RING-F1-0001"
PART = ROOT / "catalog/parts/993-int-switch-trim-ring-f1-0001.json"
MASTER = ROOT / "parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.step"
SURFACE = ROOT / "parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.stl"
EVIDENCE = ROOT / "twins/993-switch-trim-ring-alsi10mg-f1/evidence/lpbf-f1"
REPORT = EVIDENCE / "993-int-switch-trim-ring-f1-0001-lpbf-geometry-report.json"
METRICS = EVIDENCE / "993-int-switch-trim-ring-f1-0001-layer-metrics.csv"
POLICY = ROOT / "catalog/manufacturing/am-validation-policy.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SwitchTrimRingLpbfF1Tests(unittest.TestCase):
    def test_report_is_bound_to_the_master_and_to_the_analysed_mesh(self) -> None:
        report = load(REPORT)
        self.assertEqual(report["part_id"], PART_ID)
        self.assertEqual(report["master"]["sha256"], sha256(MASTER))
        self.assertEqual(report["analysis_surface"]["sha256"], sha256(SURFACE))
        self.assertTrue(report["gates"]["master_hash_verified"])

    def test_the_analysed_mesh_is_a_single_watertight_body(self) -> None:
        surface = load(REPORT)["analysis_surface"]
        self.assertTrue(surface["watertight"])
        self.assertTrue(surface["single_component"])
        self.assertTrue(load(REPORT)["gates"]["single_watertight_surface_mesh"])

    def test_every_layer_is_actually_sliced(self) -> None:
        slicing = load(REPORT)["full_build_slicing"]
        self.assertTrue(load(REPORT)["gates"]["full_piece_layer_slicing_completed"])
        self.assertGreater(slicing["layer_count"], 0)
        self.assertEqual(slicing["empty_internal_layers"], 0)
        # Une ligne de metriques par couche : le CSV est la preuve que le
        # decoupage a bien porte sur toute la piece, pas sur un echantillon.
        lines = METRICS.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines) - 1, slicing["layer_count"])

    def test_the_part_fits_the_candidate_machine(self) -> None:
        self.assertTrue(load(REPORT)["gates"]["bare_part_machine_envelope_fit"])

    def test_process_gates_stay_closed(self) -> None:
        """Le criblage est geometrique. Il n'autorise aucune impression."""
        gates = load(REPORT)["gates"]
        for gate in (
            "metal_print_authorized",
            "physical_coupon_qualified",
            "supplier_machine_file_signed",
            "supplier_supports_validated",
            "recoater_clearance_validated",
            "target_material_process_physics_correlated",
            "candidate_orientation_engineering_reviewed",
        ):
            self.assertFalse(gates[gate], gate)

    def test_the_pipeline_registry_records_the_two_stages_without_overclaiming(self) -> None:
        stages = load(POLICY)["part_overrides"][PART_ID]["stages"]
        self.assertEqual(stages["02_cad_brep_and_mesh_integrity"]["status"], "passed")
        # L'etape 03 ne peut pas etre 'passed' : sans supports fournisseur ni
        # criblage recoater, le tranchage n'est qu'un criblage.
        self.assertEqual(
            stages["03_full_layer_slicing_and_supports"]["status"], "completed_screening"
        )
        self.assertTrue(stages["03_full_layer_slicing_and_supports"]["blocker"])
        for stage in stages.values():
            for evidence in stage["evidence"]:
                self.assertTrue((ROOT / evidence).exists(), evidence)

    def test_the_part_record_stays_a_concept(self) -> None:
        part = load(PART)
        self.assertEqual(part["validation"]["status"], "concept")
        self.assertIn(
            "parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.stl",
            part["geometry"]["derived_files"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
