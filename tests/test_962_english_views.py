"""English views must preserve the source geometry and sealed receipts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "english_head_views", ROOT / "twins/962-cylinder-head-f0/source/render_english_family.py")
views = importlib.util.module_from_spec(spec)
spec.loader.exec_module(views)


class EnglishHeadViewTests(unittest.TestCase):
    def test_published_views_keep_all_four_bores_bound_to_original_meshes(self):
        family = ROOT / "twins/962-cylinder-head-f0"
        delivery = json.loads((family / "derived/family/delivery-report.json").read_text())
        for model in delivery["models"]:
            folder = family / "derived/family/english-views" / f"bore-{model['bore_mm']}"
            receipt = json.loads((folder / "render-report.json").read_text())
            original = json.loads((ROOT / model["report_path"]).read_text())
            self.assertEqual(receipt["source_report_sha256"], model["report_sha256"])
            self.assertFalse(receipt["geometry_regenerated"])
            self.assertFalse(receipt["manufacturing_authorized"])
            self.assertEqual(receipt["input_mesh_sha256"],
                             {name: row["sha256"] for name, row in original["mesh_metrics"].items()})
            self.assertEqual(set(receipt["images"]), {"exterior", "cutaway", "coolant", "chamber"})
            for name, image in receipt["images"].items():
                self.assertEqual(hashlib.sha256((folder / (name + ".png")).read_bytes()).hexdigest(),
                                 image["sha256"])

    def test_changed_geometry_is_rejected_before_rendering(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "solid.stl"
            path.write_bytes(b"changed geometry")
            with self.assertRaisesRegex(ValueError, "retained evidence"):
                views.checked(path, hashlib.sha256(b"original geometry").hexdigest())

    def test_previous_views_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "must be new"):
                views.render({}, Path(folder))

    def test_incorrect_bore_and_qualification_are_rejected_before_output(self):
        for bore, qualification in ((102, False), (95, True)):
            with self.subTest(bore=bore, qualification=qualification), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "report.json"
                path.write_text(json.dumps(dict(config=dict(geometry=dict(bore_mm=bore)),
                                                qualification=dict(strength_validated=qualification))))
                model = dict(report_path=str(path), report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             bore_mm=95)
                output = Path(folder) / "views"
                with self.assertRaisesRegex(ValueError, "matching unqualified"):
                    views.render(model, output)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
