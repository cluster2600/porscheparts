import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "components" / "wheels" / "fuchs" / "source" / "wheel_interface_proxy.py"
SPEC = importlib.util.spec_from_file_location("wheel_interface_proxy", MODULE_PATH)
wheel_proxy = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(wheel_proxy)


class WheelProxyTests(unittest.TestCase):
    def test_18_inch_record_exposes_nominal_interface(self) -> None:
        record = json.loads(
            (ROOT / "catalog" / "components" / "comp-fuchs-37027.011.json").read_text(encoding="utf-8")
        )
        diameter, width, bore = wheel_proxy.parameters(record)
        self.assertAlmostEqual(diameter, 457.2)
        self.assertAlmostEqual(width, 203.2)
        self.assertAlmostEqual(bore, 71.5)

    def test_17_inch_record_exposes_approved_bore(self) -> None:
        record = json.loads(
            (ROOT / "catalog" / "components" / "comp-fuchs-37024.013.json").read_text(encoding="utf-8")
        )
        diameter, width, bore = wheel_proxy.parameters(record)
        self.assertAlmostEqual(diameter, 431.8)
        self.assertAlmostEqual(width, 177.8)
        self.assertAlmostEqual(bore, 71.58)


if __name__ == "__main__":
    unittest.main()
