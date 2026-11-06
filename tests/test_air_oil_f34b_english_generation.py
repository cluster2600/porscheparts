"""The English generation must preserve numerical inputs and frozen sources."""

import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
GENERATION = ROOT / "containers/air-oil-cycle-f34b-en-20261106"
spec = importlib.util.spec_from_file_location("english_f34b", GENERATION / "prepare_context.py")
generation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generation)


class EnglishF34bTests(unittest.TestCase):
    def test_translated_sources_have_identical_executable_syntax(self):
        translations = {
            "Bundle autonome de seeds air/huile F34 pour construction de l'image F34b; aucune exécution solveur ni preuve physique.": "Self-contained F34 air/oil seed bundle for building the F34b image; no solver execution or physical evidence.",
            "la mutation doit être rejetée en fail-closed": "the mutation must be rejected by the fail-closed checks",
            "erreur attendue ": "expected error ",
            "; erreurs reçues: ": "; received errors: ",
        }
        def normalise(path, translate):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and ast.get_docstring(node) is not None:
                    node.body[0].value.value = "docstring"
                if translate and isinstance(node, ast.Constant) and isinstance(node.value, str):
                    node.value = translations.get(node.value, node.value)
            return ast.dump(tree)
        for translated in sorted((GENERATION / "source").rglob("*.py")):
            original = ROOT / translated.relative_to(GENERATION / "source")
            with self.subTest(source=original):
                self.assertEqual(normalise(original, True), normalise(translated, False))

    def test_generates_equivalent_inputs_without_changing_sources(self):
        originals = {p: (ROOT / p).read_bytes() for p in (generation.MANIFEST, generation.SEEDS)}
        with tempfile.TemporaryDirectory() as temporary:
            context = Path(temporary) / "context"
            receipt = generation.prepare(context)
            self.assertTrue(receipt["numerical_inputs_and_authority_unchanged"])
            self.assertEqual(receipt["canonical_doe_cases_executed"], 0)
            self.assertFalse(receipt["physical_qualification"])
            self.assertEqual(receipt, json.loads((context / "generation.json").read_text()))
        for path, data in originals.items():
            self.assertEqual((ROOT / path).read_bytes(), data)

    def test_rejects_existing_symlink_and_repository_destinations(self):
        with tempfile.TemporaryDirectory() as temporary:
            existing = Path(temporary)
            link = existing / "link"
            link.symlink_to(existing, target_is_directory=True)
            for destination in (existing, link, ROOT / "must-not-create-f34b-context"):
                with self.subTest(destination=destination), self.assertRaises(ValueError):
                    generation.prepare(destination)

    def test_rejects_changed_input_before_creating_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            lock = json.loads((GENERATION / "inputs.lock.json").read_text())
            lock["files"][0]["sha256"] = "0" * 64
            (directory / "inputs.lock.json").write_text(json.dumps(lock))
            with patch.object(generation, "GENERATION", directory), self.assertRaisesRegex(ValueError, "source hash mismatch"):
                generation.prepare(directory / "context")
            self.assertFalse((directory / "context").exists())

    def test_comparison_detects_numerical_gate_and_shape_changes(self):
        old = {"cases": [{"value": 12}], "release": False}
        for new, expected in (
            ({"cases": [{"value": 13}], "release": False}, {("cases", 0, "value")}),
            ({"cases": [{"value": 12}], "release": True}, {("release",)}),
            ({"cases": [], "release": False}, {("cases",)}),
            ({"cases": [{"value": 12.0}], "release": False}, {("cases", 0, "value")}),
        ):
            self.assertEqual(generation.differences(old, new), expected)


if __name__ == "__main__":
    unittest.main()
