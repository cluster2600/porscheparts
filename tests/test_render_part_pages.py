"""Description pages: one per record, faithful to the record, and linked from the README."""
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
    def test_carrier_current_study_precedes_archived_master_on_both_pages(self):
        record_path = ROOT / "catalog/parts/993-eng-carrier-0001.json"
        record = json.loads(record_path.read_text())
        outputs = [pages.presentation(record, record_path),
                   pages.page_markdown(record, record_path)]
        for result in outputs:
            archive = result.index("## Archived F0 catalogue concept")
            self.assertLess(result.index("media/r9/"), archive)
            self.assertGreater(result.index("media/preview.png"), archive)
            self.assertLess(result.index("carrier-R9-actual-mechanical-comparison.png"), archive)
            self.assertLess(result.index("carrier-R9-frozen-verification-English.png"), archive)
            self.assertNotIn("/carrier-R9-frozen-verification.png)", result)
            for limit in ("nonconverged", "OEM fit remains unknown", "no manufacturing release",
                          "no R10 FEM", "1.032036850", "1.031119182", "10352"):
                self.assertIn(limit, result)
            self.assertNotIn("{{", result)
            self.assertNotIn("/Users/", result)
            self.assertNotIn("/home/", result)
        self.assertEqual(record["geometry"]["master_file"], "scripts/build_993_concept_f0.py")
        self.assertEqual(record["validation"]["status"], "concept")

    def test_carrier_summary_retains_owner_verified_representation_and_site_values(self):
        folder = ROOT / "parts/993-eng-carrier-0001/media/r9"
        study = json.loads((folder / "study-public.json").read_text())
        facts = json.loads((folder / "selected-facts-and-provenance.json").read_text())
        self.assertEqual([m["mass_kg"] for m in study["masses"]],
                         [facts["geometry"]["native_dense_reference_mass_kg"],
                          facts["geometry"]["actual_STL_dense_reference_mass_kg"]])
        for row in study["mechanical_screen"]["sites"]:
            site = facts["mechanical"]["sites"][row["site"]]
            self.assertEqual(row["h_over_2_mpa"], site["h2_peak_MPa"])
            self.assertEqual(row["h_over_4_mpa"], site["h4_far_peak_MPa"])
            self.assertFalse(site["stress_convergence_proven"])

    def test_fan_rebuild_precedes_archived_geometry(self):
        record = ROOT / "catalog/parts/993-eng-cooling-impeller-alsi10mg-f0-0001.json"
        result = pages.presentation(json.loads(record.read_text()), record)
        archive = result.index("## Archived Carrera F0 concept")
        self.assertIn("MESH_RECOVERY_20261002.md", result)
        self.assertIn("QWEN_CHAIN_20261002.md", result)
        # the current Turbo rebuild leads the page, before the archived concept
        self.assertLess(result.index("results/reference/reference-review.png"), archive)
        self.assertIn("porschefanatics.com/projects/993-turbo-fan/", result)
        # the generic wheel and the schematic orthographic blocks of the
        # archived concept are no longer shown as images (removed 2026-09-29)
        self.assertNotIn("](media/preview.png)", result)
        self.assertNotIn("](media/views.png)", result)
        # the page keeps its limits: print release on hold, Turbo rotor identified
        self.assertIn("HOLD", result)
        self.assertIn("964 106 015 22", result)

    def test_one_page_per_catalogue_record(self):
        attendues = pages.attendues()
        descriptions = [c for c in attendues if c.parent.name == "pieces"]
        self.assertEqual(len(descriptions), len(FICHES))
        for chemin in attendues:
            self.assertTrue(chemin.exists(), f"missing page: {chemin.relative_to(ROOT)}")

    def test_each_part_folder_has_a_presentation_page(self):
        for chemin in FICHES:
            fiche = json.loads(chemin.read_text(encoding="utf-8"))
            dossier = ROOT / "parts" / fiche["part_id"].lower()
            if not dossier.is_dir():
                continue
            texte = (dossier / "README.md").read_text(encoding="utf-8")
            self.assertIn(fiche["part_id"], texte)
            self.assertIn("SAFETY.md", texte)
            self.assertIn(f"docs/pieces/{fiche['part_id'].lower()}.md", texte)
            tete = texte.split("## What it is")[0]
            self.assertIn("[!CAUTION]", tete)
            genre = (json.loads((dossier / "print" / "print.json").read_text(encoding="utf-8")).get("kind")
                     if (dossier / "print" / "print.json").exists() else None)
            if genre == "mockup":
                # a mock-up of a prohibited part is announced as never for use
                self.assertIn("never for use", tete)
                self.assertIn("decision 0011", tete)
                self.assertIn("Prohibited", tete)
            elif genre:
                # a printable design says so, and still says it is not validated
                self.assertIn("ready to print", tete)
                self.assertIn("not validated", tete)
                self.assertIn("decision 0010", tete)
                self.assertNotIn("not a print file", tete)
            elif (dossier / "print" / "kit.json").exists():
                # a fit-test kit is announced as such, and the part is still said unvalidated
                self.assertIn("fit-test kit is ready to print", tete)
                self.assertIn("not validated", tete)
                self.assertIn("decision 0009", tete)
            else:
                self.assertIn("Not ready to print", tete)
                if (dossier / "media" / "preview.png").exists():
                    self.assertIn("media/preview.png", texte)
                    self.assertIn("not a print file", texte)

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
            self.assertIn(chemin.name, texte, "the page must cite its record")
            self.assertIn("SAFETY.md", texte)
            self.assertIn("generated by scripts/render_part_pages.py", texte)

    def test_readme_links_to_pages_not_to_json(self):
        bloc = table.bloc()
        self.assertNotIn("](catalog/parts/", bloc)
        for chemin in FICHES:
            fiche = json.loads(chemin.read_text(encoding="utf-8"))
            self.assertIn(f"](docs/pieces/{fiche['part_id'].lower()}.md)", bloc)

    def test_drift_is_detected(self):
        chemin, attendu = next(iter(pages.attendues().items()))
        original = chemin.read_text(encoding="utf-8")
        chemin.write_text(original + "\nline added by hand\n", encoding="utf-8")
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
