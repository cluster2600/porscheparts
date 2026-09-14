"""Schéma et cohérence du registre groupe 15 (culasse/distribution 993)."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "catalog/manual/993-workshop-manual-group15-cylinder-head.json"
spec = importlib.util.spec_from_file_location("m64_vt_g15", ROOT / "twins/m64-cylinder-head/source/valvetrain/valvetrain.py")
vt = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vt
spec.loader.exec_module(vt)


class Group15RegistryTests(unittest.TestCase):
    def setUp(self):
        self.reg = json.loads(REG.read_text(encoding="utf-8"))
        self.by_id = {r["id"]: r for r in self.reg["records"]}

    def test_schema(self):
        self.assertEqual(self.reg["source_id"], "SRC-PORSCHE-WORKSHOP-MANUAL-993")
        self.assertTrue((ROOT / self.reg["source_record"]).exists())
        self.assertEqual(len(self.by_id), len(self.reg["records"]))
        for r in self.reg["records"]:
            for key in ("id", "topic", "label", "value", "unit", "pdf_page", "status"):
                self.assertIn(key, r, r.get("id"))
            self.assertEqual(r["status"], "page_checked")
            pages = r["pdf_page"] if isinstance(r["pdf_page"], list) else [r["pdf_page"]]
            self.assertTrue(all(1 <= p <= 1481 for p in pages))

    def test_applicability_is_2v_not_released(self):
        app = self.reg["applicability"]
        self.assertEqual(app["valves_per_cylinder"], 2)
        self.assertEqual(app["design_target_valves_per_cylinder"], 4)
        self.assertFalse(app["manufacturing_authorized"])

    def test_timing_conflict_kept_open(self):
        self.assertEqual(self.by_id["timing_general_ec"]["value"], 6)
        self.assertEqual(self.by_id["timing_g15_m64_05_06"]["value"]["exhaust_closes_ATDC"], 2)
        self.assertIn("timing_ec_6_vs_2", {c["id"] for c in self.reg["conflicts"]})

    def test_key_values(self):
        self.assertEqual(self.by_id["guide_bore_g"]["value"], "8.00 à 8.015")
        self.assertEqual(self.by_id["guide_tilt_wear_limit"]["value"], 0.80)
        self.assertEqual(self.by_id["lifter_travel_max"]["value"], {"intake": 1.85, "exhaust": 2.25})
        self.assertEqual(self.by_id["spring_installed_length_A"]["value"]["M64/05/06/07/08"]["intake"], "36.7 + 0.3")

    def test_no_long_text(self):
        for r in self.reg["records"]:
            self.assertLess(len(json.dumps(r["value"], ensure_ascii=False)), 600)


class StockManualParameterTests(unittest.TestCase):
    def test_defaults_untouched_and_stock_sourced(self):
        d = vt.default_parameters()
        s = vt.stock_993_manual_parameters()
        self.assertEqual(vt.check_provenance(s), [])
        self.assertEqual(d["intake"]["centreline_crank_deg"]["value"], 105.0)
        self.assertAlmostEqual(s["intake"]["centreline_crank_deg"]["value"], 119.5)
        self.assertAlmostEqual(s["exhaust"]["centreline_crank_deg"]["value"], 610.5)
        self.assertEqual(s["intake"]["lash_cold_mm"]["value"], 0.0)
        self.assertEqual(s["intake"]["centreline_crank_deg"]["status"], "sourced_reference")
        self.assertEqual(s["manual_reference"]["timing_1mm_exhaust_closes_ATDC_deg"]["value"], 6)

    def test_stock_law_is_computable(self):
        s = vt.stock_993_manual_parameters()
        law = vt.CamLaw.from_params(s["intake"])
        lift = law.valve_lift(law.centreline_rad)
        self.assertGreater(float(max(lift.ravel())) if hasattr(lift, "ravel") else float(lift), 0.0)


if __name__ == "__main__":
    unittest.main()
