"""Pages de description : une par fiche, fidèles à la fiche, et liées depuis le README."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_part_pages as pages  # noqa: E402
import render_parts_table as table  # noqa: E402

FICHES = sorted((ROOT / "catalog" / "parts").glob("*.json"))


class PartPageTests(unittest.TestCase):
    def test_one_page_per_catalogue_record(self):
        attendues = pages.attendues()
        self.assertEqual(len(attendues), len(FICHES))
        for chemin in attendues:
            self.assertTrue(chemin.exists(), f"page absente : {chemin.relative_to(ROOT)}")

    def test_check_passes_on_the_committed_pages(self):
        argv = sys.argv
        sys.argv = ["render_part_pages.py", "--check"]
        try:
            self.assertEqual(pages.main(), 0)
        finally:
            sys.argv = argv

    def test_each_page_cites_its_record_identifier_and_safety(self):
        for chemin in FICHES:
            fiche = json.loads(chemin.read_text(encoding="utf-8"))
            page = ROOT / "docs" / "pieces" / f"{fiche['part_id'].lower()}.md"
            texte = page.read_text(encoding="utf-8")
            self.assertIn(fiche["part_id"], texte)
            self.assertIn(chemin.name, texte, "la page doit citer sa fiche")
            self.assertIn("SAFETY.md", texte)
            self.assertIn("engendre par scripts/render_part_pages.py", texte)

    def test_readme_links_to_pages_not_to_json(self):
        bloc = table.bloc()
        self.assertNotIn("](catalog/parts/", bloc)
        for chemin in FICHES:
            fiche = json.loads(chemin.read_text(encoding="utf-8"))
            self.assertIn(f"](docs/pieces/{fiche['part_id'].lower()}.md)", bloc)

    def test_drift_is_detected(self):
        chemin, attendu = next(iter(pages.attendues().items()))
        original = chemin.read_text(encoding="utf-8")
        chemin.write_text(original + "\nligne ajoutee a la main\n", encoding="utf-8")
        argv = sys.argv
        sys.argv = ["render_part_pages.py", "--check"]
        try:
            self.assertEqual(pages.main(), 1)
        finally:
            sys.argv = argv
            chemin.write_text(original, encoding="utf-8")
        self.assertEqual(chemin.read_text(encoding="utf-8"), attendu)


if __name__ == "__main__":
    unittest.main()
