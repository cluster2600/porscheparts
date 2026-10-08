import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/964-chassis"
CHAIN = TWIN / "derived/datum-chain-50-05a.json"
TIE = TWIN / "evidence/scan-tie-50-05a.json"
CONTRACT = TWIN / "derived/monocoque-interface.json"
DRAWING = TWIN / "derived/plate-50-05a-scaled.json"
SPEC = importlib.util.spec_from_file_location("datum_chain_50_05a", TWIN / "source/datum_chain_50_05a.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DatumChain5005aTests(unittest.TestCase):
    def test_committed_chain_reproduces_from_the_published_dimensions(self) -> None:
        chain = json.loads(CHAIN.read_text(encoding="utf-8"))
        nominal = {k: v[0] for k, v in MODULE.DIMENSIONS.items()}
        d, via_k, via_l = MODULE.solve(nominal, MODULE.Y_HALF)
        for name, row in chain["points"].items():
            self.assertAlmostEqual(row["d_behind_0_line_mm"], round(d[int(name[1:])], 1))
        self.assertAlmostEqual(chain["p17_closure"]["via_P5_P20_K_mm"], round(via_k, 1))
        self.assertAlmostEqual(chain["p17_closure"]["via_P3_L_mm"], round(via_l, 1))

    def test_two_published_paths_to_p17_agree(self) -> None:
        closure = json.loads(CHAIN.read_text(encoding="utf-8"))["p17_closure"]
        self.assertLessEqual(abs(closure["difference_mm"]), 2.0 * closure["difference_sd_from_tolerances_mm"])

    def test_p_is_longitudinal_in_the_chain_and_the_transcription(self) -> None:
        chain = json.loads(CHAIN.read_text(encoding="utf-8"))
        self.assertAlmostEqual(chain["points"]["P5"]["d_behind_0_line_mm"]
                               - chain["points"]["P20"]["d_behind_0_line_mm"], 913.0)
        record = json.loads((ROOT / "catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json").read_text(encoding="utf-8"))
        p = next(v for v in record["declared_values"] if v["value_id"] == "MNL-964BC-0033")
        self.assertEqual(p["details"]["measurement_kind"], "longitudinal")

    def test_scan_tie_lands_on_the_p5_bosses(self) -> None:
        tie = json.loads(TIE.read_text(encoding="utf-8"))
        for side in ("left", "right"):
            boss = tie["features"][f"P5_boss_{side}"]
            self.assertLess(abs(abs(boss["y_mm"]) - 385.0), 3.0)
        self.assertLess(tie["delta"]["value_mm"], 0.0)
        self.assertLess(tie["delta"]["spread_sd_mm"], 10.0)

    def test_contract_follows_the_chain_and_the_tie(self) -> None:
        chain = json.loads(CHAIN.read_text(encoding="utf-8"))
        tie = json.loads(TIE.read_text(encoding="utf-8"))
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        points = contract["points"]
        for name in ("P20", "P3", "P5", "P17", "P18", "P19", "P12", "P21"):
            self.assertEqual(points[name]["x_statut"], "DETERMINE")
            self.assertAlmostEqual(points[name]["x_local_mm"], chain["points"][name]["x_from_P17_mm"])
        for name in ("P13", "P14", "P15"):
            self.assertEqual(points[name]["x_statut"], "MESURE_DESSIN")
        self.assertAlmostEqual(contract["cote_gouvernante"]["valeur_mm"],
                               round(points["P5"]["x_local_mm"] - points["P12"]["x_local_mm"], 1))
        self.assertAlmostEqual(contract["inconnue_globale"]["valeur_de_travail_mm"],
                               round(tie["delta"]["value_mm"] - chain["points"]["P17"]["d_behind_0_line_mm"], 1))
        self.assertFalse(contract["release_flags"]["geometry_released"])

    def test_drawing_scale_is_calibrated_and_both_plates_agree_on_p12(self) -> None:
        drawing = json.loads(DRAWING.read_text(encoding="utf-8"))
        self.assertLess(drawing["fit"]["residual_sd_mm"], 6.0)
        check = drawing["rear_chain_check"]
        self.assertLess(abs(check["drawings_differ_by_mm"]), 8.0)

    def test_drawings_and_scan_select_the_unbracketed_rear_reading(self) -> None:
        drawing = json.loads(DRAWING.read_text(encoding="utf-8"))["rear_chain_check"]["chain_minus_drawings_mm"]
        self.assertLess(abs(drawing["unbracketed"]), 10.0)
        self.assertGreater(abs(drawing["bracketed"]), 30.0)
        cradle = json.loads(TIE.read_text(encoding="utf-8"))["p21_check"]
        self.assertLess(abs(cradle["difference_chain_mm"]), 15.0)
        self.assertGreater(abs(cradle["difference_bracketed_mm"]), 30.0)
        for side in ("left", "right"):
            row = json.loads(TIE.read_text(encoding="utf-8"))["features"][f"P21_cradle_{side}"]
            self.assertLess(abs(abs(row["y_mm"]) - 320.0), 15.0)


if __name__ == "__main__":
    unittest.main()
