from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/validate_engine_solver_authority_f46.py"
SPEC = importlib.util.spec_from_file_location("validate_engine_solver_authority_f46", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EngineSolverAuthorityF46Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads((ROOT / MODULE.CONTRACT).read_text(encoding="utf-8"))

    def test_tracked_contract_passes(self) -> None:
        self.assertEqual(MODULE.validate(ROOT), [])

    def test_unproved_ICEEngineFoam_name_cannot_be_promoted(self) -> None:
        names = self.contract["name_resolution"]
        self.assertIs(names["exact_ICEEngineFoam_executable_found_in_official_sources"], False)
        self.assertIs(names["fabricated_alias_allowed"], False)

    def test_source_revisions_and_cantera_are_locked(self) -> None:
        locks = self.contract["source_locks"]
        self.assertEqual(
            locks["current_engine_framework"]["revision"],
            "c0f75f953d67cd325d28d1300672d14288f22934",
        )
        self.assertEqual(
            locks["historical_counter_solver"]["revision"],
            "221b8ab77307b0ea3831a055bedc2cd77c1417f9",
        )
        self.assertEqual(locks["thermochemistry"]["version"], "3.2.0")

    def test_two_variants_are_comparable_and_all_gates_closed(self) -> None:
        comparison = self.contract["comparison_contract"]
        self.assertEqual(comparison["variants"], MODULE.EXPECTED_VARIANTS)
        self.assertTrue(comparison["same_external_scan_contour_required"])
        self.assertTrue(
            comparison["same_bore_stroke_compression_boost_fuel_and_boundary_conditions_required"]
        )
        self.assertTrue(all(value is False for value in self.contract["execution_gates"].values()))


if __name__ == "__main__":
    unittest.main()
