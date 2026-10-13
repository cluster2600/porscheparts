import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "vehicle-911-917"
ANNOTATE = TWIN / "source" / "annotate_picogk_visualization_f11.py"


def load_module():
    spec = importlib.util.spec_from_file_location("annotate_picogk_f11", ANNOTATE)
    if spec is None or spec.loader is None:
        raise RuntimeError("module F11 impossible à charger")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Vehicle911917PicoGKVisualizationF11Tests(unittest.TestCase):
    def test_capture_crop_and_fail_closed_contract(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "capture.tga"
            image = Image.new("RGB", (400, 400), "white")
            ImageDraw.Draw(image).rectangle((180, 180, 220, 220), fill="black")
            image.save(source)
            cropped = module.cropped_capture(source)
            self.assertEqual(cropped.size, (181, 181))

        report_path = ROOT / "work" / "911-917-picogk-f11" / "picogk-visualization-report-f11.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["firewall_clearance"]["resolved_at_selected_voxel_size"])
            self.assertFalse(report["release_gates"]["physical_fit_verified"])


if __name__ == "__main__":
    unittest.main()
