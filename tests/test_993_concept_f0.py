"""Concepts F0 des pieces 993 qui n'avaient aucun maitre STEP.

Le test verifie qu'un concept reste un concept : chaque STEP est lie a son
rapport par empreinte, chaque fiche du catalogue le reference sans pretendre a
une precision, et chaque dimension non publiee est declaree comme hypothese.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("concept_f0", ROOT / "scripts/build_993_concept_f0.py")
concept_f0 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(concept_f0)


class ConceptF0Tests(unittest.TestCase):
    def test_each_concept_is_hash_linked_and_never_released(self) -> None:
        for slug, concept in concept_f0.CONCEPTS.items():
            with self.subTest(part=slug):
                report = json.loads((ROOT / f"parts/{slug}/evidence/concept-f0.json").read_text(encoding="utf-8"))
                step = ROOT / report["step"]["path"]
                self.assertEqual(report["step"]["sha256"], hashlib.sha256(step.read_bytes()).hexdigest())
                self.assertEqual(report["dimensions"], concept["dims"])
                self.assertFalse(report["dimensionally_accurate"])
                self.assertFalse(report["release_authorized"])

    def test_every_dimension_declares_its_authority(self) -> None:
        for slug, concept in concept_f0.CONCEPTS.items():
            for name, dim in concept["dims"].items():
                with self.subTest(part=slug, dimension=name):
                    self.assertIn(dim["authority"], {"published", "hypothesis"})
                    self.assertTrue(dim.get("source") or dim.get("rationale"))

    def test_catalogue_records_reference_the_concept_without_accuracy(self) -> None:
        for slug in concept_f0.CONCEPTS:
            with self.subTest(part=slug):
                record = json.loads((ROOT / f"catalog/parts/{slug}.json").read_text(encoding="utf-8"))
                geometry = record["geometry"]
                report = json.loads((ROOT / f"parts/{slug}/evidence/concept-f0.json").read_text(encoding="utf-8"))
                self.assertIn(report["step"]["path"], geometry["derived_files"])
                self.assertEqual(geometry["source_type"], "estimated")
                self.assertIsNone(geometry["accuracy_mm"])


if __name__ == "__main__":
    unittest.main()
