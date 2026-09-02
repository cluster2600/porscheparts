"""Tests des preuves EF de référence F31 pour la culasse 917."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/head-reference-cae-f31.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f31"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HeadReferenceCaeF31Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_json(CONTRACT)
        cls.report = load_json(EVIDENCE / "report.json")
        cls.publication = load_json(EVIDENCE / "publication.json")

    def test_contract_is_explicitly_defeatured_and_fail_closed(self):
        self.assertEqual(self.contract["phase"], "F31")
        self.assertEqual(
            self.contract["solver"]["load_cases"],
            ["pressure_only", "thermal_only", "combined"],
        )
        self.assertEqual(
            self.contract["solver_geometry"]["kind"], "defeatured_deck_volume"
        )
        self.assertTrue(self.contract["solver_geometry"]["excluded_features"])
        self.assertTrue(
            all(value is False for value in self.contract["release_gates"].values())
        )

    def test_tracked_report_contains_36_successful_calculix_runs(self):
        self.assertEqual(
            self.report["status"],
            "passed_reference_solver_screening_not_physical_validation",
        )
        self.assertEqual(self.report["checks"]["variant_count"], 4)
        self.assertEqual(self.report["checks"]["case_count"], 12)
        self.assertEqual(self.report["checks"]["calculix_run_count"], 36)
        self.assertTrue(self.report["checks"]["all_calculix_runs_returned_zero"])
        self.assertTrue(
            self.report["checks"]["all_pressure_reaction_balances_passed"]
        )
        self.assertTrue(self.report["checks"]["all_mesh_convergence_checks_passed"])

    def test_each_variant_has_three_meshes_and_three_load_cases(self):
        expected_load_cases = {"pressure_only", "thermal_only", "combined"}
        for variant in self.report["variants"]:
            self.assertEqual(len(variant["cases"]), 3)
            self.assertTrue(variant["convergence"]["passed"])
            for case in variant["cases"]:
                self.assertEqual(set(case["load_cases"]), expected_load_cases)
                self.assertGreater(case["tetrahedron_count"], 5000)
                balance = case["load_cases"]["pressure_only"][
                    "pressure_reaction_balance_relative_error"
                ]
                self.assertLessEqual(
                    balance,
                    self.contract["acceptance"][
                        "pressure_only_reaction_balance_relative_error_maximum"
                    ],
                )

    def test_comparison_keeps_scenarios_separate(self):
        self.assertEqual(
            {item["scenario_id"] for item in self.report["comparisons"]},
            {"type_912_5_0_na", "917_30_1973_turbo_5374"},
        )
        for comparison in self.report["comparisons"]:
            self.assertEqual(
                comparison["decision_scope"],
                "same_boundary_condition_linear_FEA_screen_only",
            )

    def test_claims_and_release_gates_do_not_overstate_validation(self):
        self.assertTrue(
            self.report["claims"]["three_dimensional_linear_fea_executed"]
        )
        for claim in (
            "measured_917_geometry_used",
            "validated_boundary_conditions_used",
            "hot_material_card_used",
            "fatigue_or_tmf_solved",
            "physical_correlation_completed",
            "manufacturing_or_engine_start_authorized",
        ):
            self.assertFalse(self.report["claims"][claim])
        self.assertTrue(
            all(value is False for value in self.report["release_gates"].values())
        )

    def test_publication_hashes_cover_report_and_figures(self):
        for relative_path, expected in self.publication["files"].items():
            path = EVIDENCE / relative_path
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path), expected)
        for name in ("reference-fea-2v-4v.png", "mesh-convergence.png"):
            path = EVIDENCE / "figures" / name
            self.assertGreater(path.stat().st_size, 20_000)
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_omniverse_preflight_is_published_blocked_and_sanitized(self):
        preflight_path = EVIDENCE / "omniverse" / "preflight.json"
        preflight = load_json(preflight_path)
        self.assertEqual(preflight["status"], "blocked")
        self.assertIn("content-agents", preflight["targets"])
        serialized = preflight_path.read_text(encoding="utf-8")
        self.assertIn("${PROJECT_ROOT}", serialized)
        self.assertIn("${PHYSICAL_AI_SKILL_HOME}", serialized)
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("/private/tmp/", serialized)


if __name__ == "__main__":
    unittest.main()
