"""Premiere piece titane du depot : selection, geometrie et deux routes.

Le test ne dit pas que l'embout est imprimable. Il verifie que la selection est
le produit de la grille ecrite appliquee a tout le catalogue et non d'un choix
d'humeur, que le criblage refuse de tourner si une fiche n'est pas jugee, et que
les deux routes titane restent exclusives : le Ti-6Al-4V bloque sur la
temperature, le Ti-6242 bloque sur tout le reste. Une carte qui ouvrirait les
deux a la fois serait un faux.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-EXH-OVAL-TIP-TI-F1-0001"
PART = ROOT / "catalog/parts/993-exh-oval-tip-ti-f1-0001.json"
MASTER = ROOT / "parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.step"
SURFACE = ROOT / "parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.stl"
EVIDENCE = ROOT / "twins/993-exhaust-tip-ti-f0/evidence"
SELECTION = EVIDENCE / "selection/titanium-candidate-screen.json"
GEOMETRY = EVIDENCE / "lpbf-f1/993-exh-oval-tip-ti-f1-0001-lpbf-geometry-report.json"
ROUTE_TI64 = EVIDENCE / "route-ti64/993-exh-oval-tip-ti-f1-0001-process-route-card.json"
ROUTE_TI6242 = EVIDENCE / "route-ti6242/993-exh-oval-tip-ti-f1-0001-process-route-card.json"
SCREEN_TI64 = ROOT / "parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti64.json"
INPUTS = ROOT / "catalog/manufacturing/titanium-am-screen-inputs.json"
POLICY = ROOT / "catalog/manufacturing/am-validation-policy.json"
SCREEN_SCRIPT = ROOT / "scripts/screen_titanium_candidates.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def gates(card: dict) -> dict:
    return {entry["gate"]: entry for entry in card["gates"]}


class ExhaustTipTitaniumF1Tests(unittest.TestCase):
    def test_the_selection_screened_the_whole_catalogue(self) -> None:
        selection = load(SELECTION)
        catalogue = len(list((ROOT / "catalog/parts").glob("*.json")))
        self.assertEqual(selection["parts_screened"], catalogue)
        self.assertEqual(selection["selected"], PART_ID)
        self.assertFalse(selection["selection_is_contested"])

    def test_the_screen_refuses_to_run_on_an_unjudged_part(self) -> None:
        inputs = load(INPUTS)
        inputs["parts"].pop(PART_ID)
        with tempfile.TemporaryDirectory() as tmp:
            trimmed = Path(tmp) / "inputs.json"
            trimmed.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCREEN_SCRIPT),
                    "--inputs",
                    str(trimmed),
                    "--output",
                    str(Path(tmp) / "out.json"),
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ne couvre pas le catalogue", result.stderr)

    def test_the_hot_candidates_are_disqualified_by_temperature_not_by_taste(self) -> None:
        ranking = {entry["part_id"]: entry for entry in load(SELECTION)["ranking"]}
        manifold = ranking["993-ENG-EXHAUST-MANIFOLD-IN625-F0-0001"]
        self.assertGreater(manifold["score"], ranking[PART_ID]["score"])
        self.assertFalse(manifold["eligible"])
        self.assertTrue(
            any("cas nickel" in reason for reason in manifold["disqualifiers"])
        )

    def test_the_mesh_is_a_single_watertight_body_bound_to_the_master(self) -> None:
        report = load(GEOMETRY)
        self.assertEqual(report["part_id"], PART_ID)
        self.assertEqual(
            report["master"]["sha256"], hashlib.sha256(MASTER.read_bytes()).hexdigest()
        )
        self.assertEqual(
            report["analysis_surface"]["sha256"],
            hashlib.sha256(SURFACE.read_bytes()).hexdigest(),
        )
        self.assertTrue(report["analysis_surface"]["watertight"])
        self.assertTrue(report["analysis_surface"]["single_component"])

    def test_no_manufacturing_gate_is_opened_on_either_route(self) -> None:
        for path in (ROUTE_TI64, ROUTE_TI6242):
            with self.subTest(route=path.parent.name):
                card = load(path)
                self.assertFalse(card["metal_print_authorized"])
                self.assertEqual(card["status"], "blocked_missing_input")

    def test_the_two_titanium_routes_stay_mutually_exclusive(self) -> None:
        ti64 = gates(load(ROUTE_TI64))
        ti6242 = gates(load(ROUTE_TI6242))
        ceiling = "alloy_ceiling_above_declared_service_temperature"
        # Ti-6Al-4V : route reelle, bloquee par la temperature seule.
        self.assertFalse(ti64[ceiling]["pass"])
        self.assertTrue(ti64["layer_thickness_consistent"]["pass"])
        self.assertTrue(ti64["screened_wall_above_process_minimum"]["pass"])
        self.assertTrue(ti64["heat_treatment_route_defined"]["pass"])
        # Ti-6242 : passe la temperature, perd la route.
        self.assertTrue(ti6242[ceiling]["pass"])
        self.assertFalse(ti6242["layer_thickness_consistent"]["pass"])
        self.assertFalse(ti6242["route_available_from_a_service_supplier"]["pass"])

    def test_the_deciding_temperature_is_declared_as_never_measured(self) -> None:
        thermal = load(SCREEN_TI64)["temperature_screen"]
        self.assertLess(thermal["margin_c"], 0.0)
        self.assertFalse(thermal["alloy_adequate_at_declared_temperature"])
        self.assertIn("never measured", thermal["declared_tip_surface_authority"])

    def test_the_catalogue_and_the_pipeline_agree(self) -> None:
        part = load(PART)
        self.assertEqual(part["classification"]["safety_class"], "functional")
        self.assertTrue(part["titanium"]["applicable"])
        stages = load(POLICY)["part_overrides"][PART_ID]["stages"]
        self.assertEqual(stages["02_cad_brep_and_mesh_integrity"]["status"], "passed")
        self.assertEqual(
            stages["04_material_machine_process_card"]["status"], "blocked_missing_input"
        )


if __name__ == "__main__":
    unittest.main()
