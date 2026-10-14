"""Simulation d'impression LPBF de chaque piece 993 dotee d'un maitre STEP.

Le test ne dit pas qu'une piece est imprimable. Il verifie que chaque rapport
publie est lie a son maitre et a sa surface par empreinte, que le tranchage a
bien couvert toute la hauteur, qu'une image accompagne le rapport, que la fiche
de la piece montre cette image, et qu'aucune porte d'impression n'est ouverte.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_print_screen_sections as sections


def reports():
    return sorted(ROOT.glob("parts/*/evidence/lpbf-f0/*-lpbf-geometry-report.json"))


class PrintScreensF0Tests(unittest.TestCase):
    def test_preview_selects_the_report_surface_and_rejects_missing_hash(self) -> None:
        import render_print_simulation_visuals as visuals

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            derived = root / "parts/test-part/derived"
            reports_folder = root / "parts/test-part/evidence/lpbf-f0"
            derived.mkdir(parents=True)
            reports_folder.mkdir(parents=True)
            (derived / "a-unanalysed.stl").write_bytes(b"other mesh")
            matching = derived / "b-analysed.stl"
            matching.write_bytes(b"analysed mesh")
            report = {"analysis_surface": {"sha256": visuals.sha256(matching)}}
            (reports_folder / "test-lpbf-geometry-report.json").write_text(json.dumps(report))
            mesh_loader = Mock()
            with patch.object(visuals, "ROOT", root), \
                 patch.dict(sys.modules, {"trimesh": mesh_loader}):
                visuals.load_inputs("test-part")
                mesh_loader.load_mesh.assert_called_once_with(matching, process=True)
                matching.unlink()
                with self.assertRaisesRegex(SystemExit, "no surface matching"):
                    visuals.load_inputs("test-part")
                self.assertEqual(mesh_loader.load_mesh.call_count, 1)

    def test_we43_screen_does_not_claim_a_qualified_eos_process_or_supports(self) -> None:
        slug = "993-eng-cooling-impeller-we43-f1-0001"
        text = sections.section(slug, ROOT / "docs/993" / sections.SHEETS[slug], {})
        self.assertNotIn("LPBF print simulation", text)
        self.assertNotIn("EOS M 290 route", text)
        self.assertIn("not an EOS catalogue material", text)
        self.assertIn("hypothetical support envelope", text)
        self.assertIn("not a metal consumption estimate", text)
        self.assertIn("Process physics has not been calculated", text)

    def test_plate_warning_is_in_the_image_not_only_its_caption(self) -> None:
        import render_print_simulation_visuals as visuals

        report_path = next((ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001/evidence/lpbf-f0")
                           .glob("*-report.json"))
        report = json.loads(report_path.read_text())
        plotter = Mock()
        with patch.object(visuals, "plotter", return_value=plotter), \
             patch.object(visuals, "add_machine"), patch.object(visuals, "frame_camera"):
            visuals.render_build_plate(Path("unused.png"), Mock(), Mock(n_cells=0),
                                       (250, 250, 325), report)
        label = plotter.add_text.call_args.args[0]
        self.assertIn("HYPOTHETICAL", label)
        self.assertIn("NO process physics", label)
        self.assertIn("45 deg geometric heuristic", label)
        self.assertNotIn("build simulation", label)

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
