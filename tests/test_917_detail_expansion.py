import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "twins/reference-917-engine/detail-expansion-f3.json"


class Engine917DetailExpansionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_declared_counts_match_families(self):
        families = self.data["families"]
        self.assertEqual(len(families), self.data["acceptance"]["added_family_count"])
        self.assertEqual(sum(item["count"] for item in families), self.data["acceptance"]["added_instance_count"])

    def test_turbo_internals_are_variant_only(self):
        turbo = [item for item in self.data["families"] if item["id"].startswith("turbo_") or item["id"].startswith("wastegate")]
        self.assertTrue(turbo)
        self.assertTrue(all(item["variant"] == "917_30_only" for item in turbo))

    def test_unknown_dimensions_remain_non_manufacturing(self):
        self.assertIn("manufacturing_release", self.data["prohibited_use"])
        self.assertTrue(all("confidence" in item for item in self.data["families"]))


if __name__ == "__main__":
    unittest.main()
