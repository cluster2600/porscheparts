import contextlib
import io
import unittest

from scripts import twin_coverage


class TwinCoverageTests(unittest.TestCase):
    def test_carrera_engine_mass_is_read_from_the_manual_record(self) -> None:
        self.assertEqual(twin_coverage.engine_mass("Carrera", "manual")[0], 232.0)
        self.assertEqual(twin_coverage.engine_mass("Carrera", "tiptronic")[0], 224.0)
        self.assertIn("MNL-TECH-0020", twin_coverage.engine_mass("Carrera", "manual")[1])

    def test_unsourced_turbo_engine_mass_is_not_counted(self) -> None:
        mass, reason = twin_coverage.engine_mass("Turbo", "manual")
        self.assertEqual(mass, 0.0)
        self.assertIn("no registered source", reason)

    def test_default_curb_weight_and_total_are_sourced(self) -> None:
        self.assertEqual(twin_coverage.manual_mass_kg(twin_coverage.CARRERA_CURB_WEIGHT), 1370.0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(twin_coverage.main([]), 0)
        self.assertIn("Coverage: 476.0 kg of 1370 kg, i.e. 34.7 %", output.getvalue())

    def test_unknown_manual_value_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            twin_coverage.manual_mass_kg("MNL-TECH-9999")
        with self.assertRaises(ValueError):
            twin_coverage.manual_mass_kg("MNL-TECH-0026")  # wheelbase in mm, not a mass


if __name__ == "__main__":
    unittest.main()
