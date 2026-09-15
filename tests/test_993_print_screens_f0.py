"""Simulation d'impression LPBF de chaque piece 993 dotee d'un maitre STEP.

Le test ne dit pas qu'une piece est imprimable. Il verifie que chaque rapport
publie est lie a son maitre et a sa surface par empreinte, que le tranchage a
bien couvert toute la hauteur, qu'une image accompagne le rapport, que la fiche
de la piece montre cette image, et qu'aucune porte d'impression n'est ouverte.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def reports():
    return sorted(ROOT.glob("parts/*/evidence/lpbf-f0/*-lpbf-geometry-report.json"))


class PrintScreensF0Tests(unittest.TestCase):
    def test_at_least_one_screen_is_published(self) -> None:
        self.assertTrue(reports())

    def test_each_screen_is_hash_linked_sliced_and_closed(self) -> None:
        for path in reports():
            with self.subTest(report=path.name):
                report = json.loads(path.read_text(encoding="utf-8"))
                derived = path.parents[2] / "derived"
                step = next(derived.glob("*.step"))
                stl = step.with_suffix(".stl")
                self.assertEqual(report["master"]["sha256"], hashlib.sha256(step.read_bytes()).hexdigest())
                self.assertEqual(report["analysis_surface"]["sha256"], hashlib.sha256(stl.read_bytes()).hexdigest())
                self.assertTrue(report["analysis_surface"]["watertight"])
                slicing = report["full_build_slicing"]
                self.assertGreater(slicing["layer_count"], 0)
                self.assertAlmostEqual(
                    slicing["layer_count"] * slicing["layer_thickness_mm"],
                    slicing["build_height_mm"],
                    delta=2 * slicing["layer_thickness_mm"],
                )
                self.assertTrue(report["gates"]["full_piece_layer_slicing_completed"])
                self.assertFalse(report["gates"]["metal_print_authorized"])
                self.assertFalse(report["gates"]["supplier_machine_file_signed"])
                image = path.with_name(path.name.replace("-report.json", "-screen.png"))
                self.assertTrue(image.is_file())

    def test_each_screened_part_sheet_shows_its_image(self) -> None:
        sheets = {p: p.read_text(encoding="utf-8") for p in (ROOT / "docs/993").glob("*.md")}
        for path in reports():
            image = path.name.replace("-report.json", "-screen.png")
            with self.subTest(image=image):
                self.assertTrue(any(image in text for text in sheets.values()))


if __name__ == "__main__":
    unittest.main()
