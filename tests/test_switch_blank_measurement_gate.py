"""The switch blank master builds from a physical measurement session, never from declared values.

Decision 0013 records the declared opening and blank sizes of pilot 1 as
documented specifications. These tests keep the measured-input gate of
`switch_blank.py`, and of the twin fit check, closed while only declared data
exist for the part.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-INT-SWITCH-BLANK-0001"
REGISTER = ROOT / "catalog" / "measurements"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


switch_blank = load_module("switch_blank", ROOT / "parts" / "993-int-switch-blank-0001" / "source" / "switch_blank.py")
check_fit = load_module("check_fit", ROOT / "twins" / "993-cabin-dashboard-switch-0001" / "source" / "check_fit.py")


def declared_records() -> list[Path]:
    found = []
    for path in sorted(REGISTER.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if (record.get("subject") or {}).get("part_id") == PART_ID and \
                record.get("record_kind") == "documented_specification":
            found.append(path)
    return found


class SwitchBlankMeasurementGateTests(unittest.TestCase):
    def test_declared_records_exist_and_carry_no_readings(self) -> None:
        paths = declared_records()
        self.assertGreaterEqual(len(paths), 1, "the desk test of decision 0013 must stay in the register")
        for path in paths:
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["readings"], [], path.name)
            self.assertEqual(record["instruments"], [], path.name)

    def test_master_refuses_every_declared_record(self) -> None:
        for path in declared_records():
            with self.assertRaises(SystemExit) as raised:
                switch_blank.load_dimensions(path)
            self.assertIn("documented_specification", str(raised.exception.code))

    def test_twin_fit_check_refuses_every_declared_record(self) -> None:
        for path in declared_records():
            with self.assertRaises(SystemExit) as raised:
                check_fit.load_readings(path)
            self.assertIn("documented_specification", str(raised.exception.code))

    def test_declared_record_with_injected_readings_is_still_refused(self) -> None:
        # Synthetic test fixture, not part data: a declared record that someone
        # filled with readings must not become a geometry input.
        record = json.loads(declared_records()[0].read_text(encoding="utf-8"))
        record["readings"] = [
            {"dimension_id": key, "unit": "mm", "value": float(i), "uncertainty": 0.1}
            for i, key in enumerate(switch_blank.NEEDED, start=1)
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "declared.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                switch_blank.load_dimensions(path)
            self.assertIn("declared values do not define this geometry", str(raised.exception.code))
            record["readings"] = [
                {"dimension_id": key, "unit": "mm", "value": float(i), "uncertainty": 0.1}
                for i, key in enumerate(check_fit.REQUIRED, start=1)
            ]
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                check_fit.load_readings(path)
            self.assertIn("declared values do not feed a fit check", str(raised.exception.code))

    def test_default_input_is_not_shadowed_by_a_declared_record(self) -> None:
        default = switch_blank.DEFAULT_MEASUREMENTS
        # A case-insensitive file system (macOS) must not resolve the default
        # input to a declared record either.
        for path in declared_records():
            self.assertNotEqual(path.name.lower(), default.name.lower())
        if not default.exists():
            with self.assertRaises(SystemExit) as raised:
                switch_blank.load_dimensions(default)
            self.assertIn("no measurement record", str(raised.exception.code))
        else:
            record = json.loads(default.read_text(encoding="utf-8"))
            self.assertEqual(record.get("record_kind", "physical_measurement"), "physical_measurement")


if __name__ == "__main__":
    unittest.main()
