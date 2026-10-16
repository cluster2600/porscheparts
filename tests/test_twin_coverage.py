import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import twin_coverage


def _run(*argv: str) -> str:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        status = twin_coverage.main(list(argv))
    assert status == 0
    return output.getvalue()


def _documented_parts_kg() -> float:
    """Sum the counted part entries straight from catalog/reference."""
    total = 0.0
    for path in sorted((twin_coverage.ROOT / "catalog" / "reference").glob("*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")).get("entries", []):
            if entry.get("mass_kg") is None or entry.get("quantity_per_car") is None:
                continue
            if entry.get("generation") in {"993", "generic"}:
                total += entry["mass_kg"] * entry["quantity_per_car"]
    return total


def _manual_value(value_id: str) -> dict:
    record = json.loads(twin_coverage.MANUAL_RECORD.read_text(encoding="utf-8"))
    return next(value for value in record["declared_values"] if value["value_id"] == value_id)


class TwinCoverageTests(unittest.TestCase):
    def test_carrera_engine_mass_is_read_from_the_manual_record(self) -> None:
        for transmission, value_id in (("manual", "MNL-TECH-0020"), ("tiptronic", "MNL-TECH-0021")):
            mass, citation = twin_coverage.engine_mass("Carrera", transmission)
            self.assertEqual(mass, _manual_value(value_id)["numeric_values"][0])
            self.assertIn(value_id, citation)
            self.assertIn("scope open", citation)

    def test_unsourced_turbo_engine_mass_is_not_counted(self) -> None:
        mass, reason = twin_coverage.engine_mass("Turbo", "manual")
        self.assertEqual(mass, 0.0)
        self.assertIn("no registered source", reason)

    def test_default_curb_weight_and_total_follow_the_data(self) -> None:
        kerb = _manual_value(twin_coverage.CARRERA_CURB_WEIGHT)["numeric_values"][0]
        self.assertEqual(twin_coverage.manual_mass_kg(twin_coverage.CARRERA_CURB_WEIGHT), kerb)
        documented = _documented_parts_kg() + _manual_value("MNL-TECH-0020")["numeric_values"][0]
        expected = f"Coverage: {documented:.1f} kg of {kerb:.0f} kg, i.e. {documented / kerb * 100:.1f} %"
        self.assertIn(expected, _run())

    def test_output_states_the_open_engine_scope_and_the_weighing(self) -> None:
        output = " ".join(_run().split())
        self.assertIn(f'"{_manual_value("MNL-TECH-0020")["description"]}"', output)
        self.assertIn("Engine scope is open", output)
        self.assertIn("186.9 kg", output)
        self.assertIn("unregistered community weighing", output)
        self.assertIn(twin_coverage.COMMUNITY_WEIGHING_RECORD, output)
        gap = _manual_value("MNL-TECH-0020")["numeric_values"][0] - twin_coverage.COMMUNITY_WEIGHING_KG
        self.assertIn(f"{gap:.1f} kg", output)
        self.assertTrue((twin_coverage.ROOT / twin_coverage.COMMUNITY_WEIGHING_RECORD).is_file())

    def test_unknown_or_unreviewed_manual_value_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            twin_coverage.manual_mass_kg("MNL-TECH-9999")
        with self.assertRaises(ValueError):
            twin_coverage.manual_mass_kg("MNL-TECH-0026")  # wheelbase in mm, not a mass
        self.assertEqual(_manual_value("MNL-OCR-1268")["extraction_status"], "ocr_unreviewed")
        with self.assertRaisesRegex(ValueError, "not admissible"):
            twin_coverage.manual_mass_kg("MNL-OCR-1268")  # a kg value from raw OCR

    def test_engine_is_not_counted_when_its_manual_value_is_not_admissible(self) -> None:
        record = json.loads(twin_coverage.MANUAL_RECORD.read_text(encoding="utf-8"))
        for value in record["declared_values"]:
            if value["value_id"] == "MNL-TECH-0020":
                value["extraction_status"] = "ocr_unreviewed"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MEAS-MANUAL-993-ALL.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with mock.patch.object(twin_coverage, "MANUAL_RECORD", path):
                mass, reason = twin_coverage.engine_mass("Carrera", "manual")
                output = _run()
        self.assertEqual(mass, 0.0)
        self.assertIn("not counted", reason)
        self.assertIn("not admissible", reason)
        self.assertNotIn("Engine scope is open", output)
        self.assertIn(f"Coverage: {_documented_parts_kg():.1f} kg", output)

    def test_turbo_and_tiptronic_require_a_curb_weight(self) -> None:
        for argv in (["--variant", "Turbo"], ["--transmission", "tiptronic"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()) as error:
                with self.assertRaises(SystemExit) as raised:
                    twin_coverage.main(argv)
                self.assertEqual(raised.exception.code, 2)
                self.assertIn("pass --kerb-weight", error.getvalue())

    def test_turbo_with_an_explicit_curb_weight_counts_no_engine(self) -> None:
        output = _run("--variant", "Turbo", "--kerb-weight", "1000")
        self.assertIn("Engine: not counted, no registered source gives the Turbo engine mass", output)
        self.assertIn(f"Coverage: {_documented_parts_kg():.1f} kg of 1000 kg", output)
        self.assertNotIn("Engine scope is open", output)


if __name__ == "__main__":
    unittest.main()
