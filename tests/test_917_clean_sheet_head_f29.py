"""Tests du criblage de culasse conceptuelle 2V/4V F29."""

from __future__ import annotations

import ast
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/clean-sheet-cylinder-head-f29.json"
HANDOFF = ROOT / "twins/reference-917-engine/omniverse-handoff-f29.json"
STUDY_SCRIPT = ROOT / "twins/reference-917-engine/source/run_clean_sheet_head_trade_study_f29.py"
CAD_SCRIPT = ROOT / "twins/reference-917-engine/source/build_clean_sheet_head_cad_f29.py"
VALIDATOR = ROOT / "twins/reference-917-engine/source/validate_clean_sheet_head_f29.py"
FIGURE_SCRIPT = ROOT / "twins/reference-917-engine/source/render_clean_sheet_head_results_f29.py"
EVIDENCE_ROOT = ROOT / "twins/reference-917-engine/evidence/f29"


def load_module(path: Path, name: str):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot_import:{path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


class CleanSheetHeadF29Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
        cls.study_module = load_module(STUDY_SCRIPT, "f29_trade_study")

    def test_contract_is_four_concepts_and_fail_closed(self):
        self.assertEqual(self.contract["phase"], "F29")
        self.assertEqual(self.contract["asset"]["concept_count"], 4)
        self.assertEqual(self.contract["asset"]["architecture_variants"], ["2v", "4v"])
        self.assertEqual(
            {item["id"] for item in self.contract["scenarios"]},
            {"type_912_5_0_na", "917_30_1973_turbo_5374"},
        )
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        boundary = self.contract["authority_boundary"]
        self.assertFalse(boundary["f28_geometry_or_dimensions_transferred"])
        self.assertIn("validated_digital_twin", boundary["forbidden_claims"])
        self.assertIn("ready_for_metal_print", boundary["forbidden_claims"])

    def test_material_valve_and_spring_choices_keep_manufacturing_boundary(self):
        materials = self.contract["material_screening"]
        self.assertEqual(materials["screening_selection"], "AlF357_LPBF_screening")
        self.assertGreater(len(materials["selection_limits"]), 5)
        self.assertTrue(all(item["source"].startswith("https://") for item in materials["head_candidates"]))
        valvetrain = self.contract["valvetrain_screening"]
        self.assertFalse(valvetrain["intake_valve"]["additive_manufacturing_allowed"])
        self.assertFalse(valvetrain["exhaust_valve"]["additive_manufacturing_allowed"])
        self.assertFalse(valvetrain["spring"]["additive_manufacturing_allowed"])
        self.assertIn("INCONEL", valvetrain["exhaust_valve"]["candidate"])
        self.assertIn("silicon_chromium", valvetrain["spring"]["candidate"])

    def test_effective_area_is_limited_by_valve_throat(self):
        diameter_mm = 40.0
        count = 2
        coefficient = 0.72
        throat_limit = coefficient * count * math.pi * (0.86 * diameter_mm) ** 2 / 4.0
        actual = self.study_module.effective_area_mm2(count, diameter_mm, 100.0, coefficient)
        self.assertAlmostEqual(actual, throat_limit, places=9)

    def test_design_study_builds_four_packaged_variants(self):
        study = self.study_module.build_study(CONTRACT, self.contract)
        self.assertEqual(study["variant_count"], 4)
        self.assertTrue(all(value is False for value in study["release_gates"].values()))
        expected = {
            "type_912_5_0_na_2v",
            "type_912_5_0_na_4v",
            "917_30_1973_turbo_5374_2v",
            "917_30_1973_turbo_5374_4v",
        }
        self.assertEqual({item["id"] for item in study["variants"]}, expected)
        for item in study["variants"]:
            self.assertGreaterEqual(
                item["minimum_seat_bridge_mm"],
                self.contract["architecture_search"]["minimum_seat_bridge_mm"],
            )
            self.assertGreaterEqual(
                item["chamber_edge_margin_mm"],
                self.contract["architecture_search"]["minimum_chamber_edge_margin_mm"],
            )
            self.assertLess(item["intake_maximum_lift_mm"], item["intake_diameter_mm"])
            self.assertLess(item["exhaust_maximum_lift_mm"], item["exhaust_diameter_mm"])
        self.assertTrue(all(item["screening_lead"] == "4v" for item in study["comparisons"]))
        self.assertTrue(
            all(
                item["four_valve_change_percent"]["combined_mean_effective_area"] > 0.0
                for item in study["comparisons"]
            )
        )
        published_study = json.loads((EVIDENCE_ROOT / "design-study.json").read_text(encoding="utf-8"))
        self.assertEqual(published_study, study)

    def test_cad_builder_requires_closed_step_roundtrip_and_immutable_lock(self):
        source = CAD_SCRIPT.read_text(encoding="utf-8")
        ast.parse(source)
        for fragment in (
            "from build123d import export_step, export_stl, import_step",
            'created_metrics["solid_count"] == 1',
            'created_metrics["all_solids_closed"]',
            'reopened_metrics["solid_count"] == 1',
            'reopened_metrics["all_solids_closed"]',
            "relative_volume_difference <= 1.0e-5",
            'toolchain_lock["image"]["immutable_reference"]',
            '"scan_used": False',
            '"fitment_verified": False',
            '"manufacturing_verified": False',
            "canonicalize_step_header(step_path)",
            "1970-01-01T00:00:00",
        ):
            self.assertIn(fragment, source)
        for path in sorted((EVIDENCE_ROOT / "cad").glob("*.step")):
            self.assertIn("1970-01-01T00:00:00", path.read_text(encoding="utf-8")[:512])

    def test_omniverse_handoff_does_not_misrepresent_physx_as_fea(self):
        self.assertEqual(self.handoff["status"], "handoff_prepared_preflight_blocked_no_usd_or_simready_result")
        self.assertTrue(self.handoff["omniverse_test_scope"]["not_a_structural_solver"])
        self.assertTrue(
            self.handoff["omniverse_test_scope"][
                "physx_does_not_validate_head_stress_or_thermomechanical_fatigue"
            ]
        )
        self.assertTrue(all(value is False for value in self.handoff["release_gates"].values()))
        self.assertFalse(self.handoff["current_preflight"]["usd_convert_cad_ready"])
        self.assertGreaterEqual(len(self.handoff["required_external_reference_solvers"]["fea"]), 5)

    def test_vast_attempt_is_recorded_as_blocked_and_destroyed(self):
        attempt = self.handoff["remote_execution_attempt"]
        self.assertEqual(attempt["status"], "blocked_instance_never_ready_no_remote_job_executed")
        self.assertFalse(attempt["ssh_authenticated"])
        self.assertFalse(attempt["remote_ready"])
        self.assertFalse(attempt["cad_transferred"])
        self.assertFalse(attempt["remote_preflight_executed"])
        self.assertEqual(attempt["usd_output_count"], 0)
        self.assertEqual(attempt["rendered_image_count"], 0)
        self.assertFalse(attempt["simready_validated"])
        self.assertFalse(attempt["simulation_validated"])
        self.assertTrue(attempt["instance_destroyed"])
        self.assertRegex(attempt["readiness_evidence"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(attempt["destruction_evidence"]["sha256"], r"^[0-9a-f]{64}$")

    def test_published_evidence_and_figures_remain_explicitly_non_simulation(self):
        bundle = self.handoff["published_evidence_bundle"]
        self.assertTrue(bundle["contains_four_step_masters"])
        self.assertTrue(bundle["contains_cad_preview_figures"])
        self.assertFalse(bundle["contains_omniverse_render"])
        self.assertFalse(bundle["contains_cfd_or_fea_result"])
        self.assertTrue(bundle["preflight_local_paths_portabilized"])
        self.assertFalse(bundle["raw_preflight_report_committed"])
        for relative_path in (
            "README.md",
            "design-study.json",
            "cad/geometry-report.json",
            "figures/cad-comparison-2v-4v.png",
            "figures/trade-study-4v-vs-2v.png",
            "omniverse/preflight.json",
            "vast/instance-ready.json",
            "vast/destroy-report.json",
        ):
            path = EVIDENCE_ROOT / relative_path
            self.assertTrue(path.is_file() and path.stat().st_size > 0, relative_path)
        source = FIGURE_SCRIPT.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("PAS UN RESULTAT CFD, FEA OU OMNIVERSE", source)
        self.assertIn("pas rendement moteur", source)
        preflight_text = (EVIDENCE_ROOT / "omniverse/preflight.json").read_text(encoding="utf-8")
        self.assertNotIn("/Users/", preflight_text)
        self.assertIn("${PROJECT_ROOT}", preflight_text)

    def test_validator_is_fail_closed_and_checks_no_usd(self):
        source = VALIDATOR.read_text(encoding="utf-8")
        ast.parse(source)
        for fragment in (
            "study_contract_digest_stale",
            "geometry_study_digest_stale",
            "geometry_contract_digest_stale",
            "blocked_preflight_must_not_create_usd",
            "remote_readiness_digest_mismatch",
            "remote_instance_absence_not_verified",
            "omniverse_render_must_not_be_claimed",
            "cad_preview_not_omniverse_or_simulation",
            "step_roundtrip_relative_volume_difference",
            '"digital_twin_validated": False',
            '"manufacturing_authorized": False',
        ):
            self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
