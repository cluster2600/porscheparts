import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("station_demo", Path(__file__).resolve().parents[1] / "scripts/run_picogk_station_demo.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StationDemoTests(unittest.TestCase):
    def test_parameter_bounds_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "new"
            module.validate_inputs(out, 30, 0.25)
            for span, voxel in [(float("nan"), 0.25), (81, 0.25), (30, 0), (30, float("inf"))]:
                with self.assertRaises(ValueError):
                    module.validate_inputs(out, span, voxel)
            out.mkdir()
            with self.assertRaises(ValueError):
                module.validate_inputs(out, 30, 0.25)


if __name__ == "__main__":
    unittest.main()
