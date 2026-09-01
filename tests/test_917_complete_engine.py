import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "twins" / "reference-917-engine" / "complete-engine-f1.json"


class Complete917EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.counts = {item["id"]: item["count"] for item in cls.config["component_families"]}

    def test_sourced_topology_counts(self):
        self.assertEqual(self.counts["piston"], 12)
        self.assertEqual(self.counts["connecting_rod"], 12)
        self.assertEqual(self.counts["individual_cylinder"], 12)
        self.assertEqual(self.counts["individual_head"], 12)
        self.assertEqual(self.counts["camshaft"], 4)
        self.assertEqual(self.counts["spark_plug"], 24)

    def test_turbo_parts_are_variant_only(self):
        families = {item["id"]: item for item in self.config["component_families"]}
        self.assertEqual(families["turbocharger"]["variant"], "917_30_only")
        self.assertEqual(families["charge_plenum"]["variant"], "917_30_only")

    def test_layout_hypotheses_are_separate(self):
        hypotheses = self.config["layout_hypotheses"]
        self.assertIn("connecting_rod_center_distance_mm", hypotheses)
        self.assertIn("camshaft_length_mm", hypotheses)
        self.assertIn("turbo_envelope_mm", hypotheses)

    def test_local_parts_report_when_present(self):
        path = ROOT / "work" / "917-complete-engine" / "parts" / "complete-engine-parts-report.json"
        if not path.exists():
            self.skipTest("local generated report intentionally absent")
        report = json.loads(path.read_text(encoding="utf-8"))
        actual = Counter(item["family"] for item in report["placements"])
        self.assertEqual(report["prototype_count"], len(self.counts))
        self.assertEqual(actual, Counter(self.counts))
        self.assertEqual(report["property_assignment_intent"], "skip")


if __name__ == "__main__":
    unittest.main()
