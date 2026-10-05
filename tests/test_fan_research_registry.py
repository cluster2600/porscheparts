"""Keep research references and unknowns explicit during dossier integration."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

FAN = Path(__file__).resolve().parents[1] / "twins/993-engine-cooling-fan-system-f0"
spec = importlib.util.spec_from_file_location("fan_research", FAN / "source/check_research_registry.py")
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)
index_spec = importlib.util.spec_from_file_location("fan_research_index", FAN / "source/build_research_index.py")
index_builder = importlib.util.module_from_spec(index_spec)
index_spec.loader.exec_module(index_builder)


class ResearchRegistryTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(registry.REGISTRY.read_text())

    def test_project_pages_cannot_be_independent_corroboration(self):
        source = next(s for s in self.data["sources"] if s["source_kind"] == "project_model")
        source["independent_of_project"] = True
        with self.assertRaises(ValueError):
            registry.validate(self.data)

    def test_numeric_parameter_needs_units_and_conditions(self):
        for field in ("unit", "conditions", "source_ids"):
            data = copy.deepcopy(self.data)
            data["parameters"][0][field] = None if field == "unit" else []
            with self.subTest(field=field), self.assertRaises(ValueError):
                registry.validate(data)

    def test_unknowns_remain_null_and_literature_grants_no_release(self):
        self.assertTrue(any(p["value"] is None for p in registry.validate(self.data)["parameters"]))
        self.data["claims"][0]["engineering_validation"] = True
        with self.assertRaises(ValueError):
            registry.validate(self.data)

    def test_dangling_source_and_contradiction_references_rejected(self):
        for group, field in (("claims", "source_ids"), ("contradictions", "record_ids")):
            data = copy.deepcopy(self.data)
            data[group][0][field] = ["missing-source"]
            with self.subTest(group=group), self.assertRaises(ValueError):
                registry.validate(data)

    def test_original_text_change_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(index_builder.RESEARCH / "corpus", root / "corpus")
            report = root / "corpus/oem/research_report.md"
            report.write_text(report.read_text() + "\nchanged\n")
            with patch.object(index_builder, "RESEARCH", root), self.assertRaisesRegex(ValueError, "Original research text changed"):
                index_builder.build()

    def test_complete_index_preserves_origins_and_open_gates(self):
        data = index_builder.build()
        self.assertFalse(data["engineering_validation"])
        self.assertEqual(data, json.loads((index_builder.RESEARCH / "source-index.json").read_text()))
        self.assertTrue(all(not r["engineering_validation"] for r in data["records"]))
        project_sources = [s for s in data["sources"] if "porschefanatics.com" in (s["normalized_url"] or "")]
        self.assertTrue(project_sources)
        self.assertTrue(all(not s["independent_of_project"] for s in project_sources))


if __name__ == "__main__":
    unittest.main()
