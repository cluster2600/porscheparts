"""Committed thermal results must retain their inputs, fields and physical limits."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001"
EVIDENCE = PART / "evidence/lpbf-thermal-20261012"


class ThermalEvidenceTests(unittest.TestCase):
    def test_polymer_mockup_keeps_geometry_provenance_and_separate_use(self):
        card = json.loads((PART / "source/polymer-mockup.json").read_text())
        for key in ("parent", "output"):
            self.assertEqual(card[key + "_sha256"], hashlib.sha256((ROOT / card[key]).read_bytes()).hexdigest())
        self.assertEqual(card["orientation"], "roll_y_45")
        self.assertEqual((card["units"], card["scale"]), ("mm", 1))
        for flag in ("rotating_use_authorized", "manufacturing_ready", "thermal_study_applicable",
                     "continuous_fiber_process_qualified"):
            self.assertIs(card[flag], False)
        self.assertIsNone(card["printer"])
        self.assertIsNone(card["slicer_profile"])

    def test_complete_cases_match_sources_energy_and_unqualified_status(self):
        for name, pitch, substeps in (("p2-s4", 2., 4), ("p2-s8", 2., 8), ("p3-s4", 3., 4),
                                     ("flat/p2-s8", 2., 8), ("flat/p2-s4", 2., 4), ("flat/p3-s4", 3., 4)):
            with self.subTest(case=name):
                card_path = (EVIDENCE / "flat/inputs/study.json" if name.startswith("flat/")
                             else PART / "source/lpbf-thermal-study.json")
                card = json.loads(card_path.read_text())
                inputs = {"card": card_path, "script": PART / "source/simulate_lpbf_thermal.py",
                          "reused_solver": ROOT / "twins/993-engine-cooling-fan-system-f0/source/simulate_zrapid_print.py"}
                inputs.update({key: ROOT / card[key] for key in ("surface", "layers", "geometry_report")})
                case = EVIDENCE / name
                report = json.loads((case / "summary.json").read_text())
                self.assertEqual(report["status"], "transient_3d_bulk_thermal_solve_completed")
                self.assertEqual((report["pitch_mm"], report["substeps"]), (pitch, substeps))
                self.assertEqual(report["hashes"], {key: hashlib.sha256(path.read_bytes()).hexdigest()
                                                    for key, path in inputs.items()})
                for filename in ("thermal-fields.npz", "history.json"):
                    self.assertEqual(hashlib.sha256((case / filename).read_bytes()).hexdigest(),
                                     report["output_hashes"][filename])
                for flag in ("manufacturing_authorized", "machine_calibrated", "melt_pool_resolved",
                             "powder_conduction_resolved", "distortion_computed"):
                    self.assertIs(report[flag], False)
                self.assertLess(report["maximum_step_energy_residual"], 1e-6)
                self.assertLess(abs(report["global_energy_residual_j"]), 1e-3)
                self.assertLess(abs(report["voxel_relative_volume_error"]), .02)
                self.assertEqual(report["cp_reference_temperature_range_exceeded"],
                                 report["peak_bulk_part_k"] > card["material"]["cp_reference_range_k"][1])
                process = card["process"]
                incident = process["power_w"] / (process["scan_speed_mm_s"] * process["hatch_mm"] * process["layer_mm"])
                expected = report["absorptivity"] * incident * (report["sliced_volume_mm3"]
                                                               + report["assumed_support_solid_volume_mm3"])
                self.assertAlmostEqual(report["absorbed_energy_j"] / expected, 1., places=10)

    def test_flat_comparison_changes_only_geometry_and_keeps_adapter_provenance(self):
        flat = json.loads((EVIDENCE / "flat/inputs/study.json").read_text())
        tilted = json.loads((PART / "source/lpbf-thermal-study.json").read_text())
        for key in ("geometry_report", "layers"):
            flat.pop(key)
            tilted.pop(key)
        self.assertEqual(flat, tilted)
        geometry = json.loads((EVIDENCE / "flat/inputs/geometry.json").read_text())
        self.assertEqual(geometry["source_sha256"], hashlib.sha256(
            (PART / "source/run_flat_lpbf_thermal.py").read_bytes()).hexdigest())
        self.assertEqual(geometry["selected_candidate_orientation"], "build_z")

    def test_visualizations_match_computed_cases_and_renderer(self):
        for output, cases in ((EVIDENCE / "flat", EVIDENCE / "flat"), (EVIDENCE / "tilted", EVIDENCE)):
            with self.subTest(figure=output.name):
                manifest = json.loads((output / "visuals.json").read_text())
                self.assertEqual(manifest["image_sha256"], hashlib.sha256((output / "thermal-study.png").read_bytes()).hexdigest())
                self.assertEqual(manifest["renderer_sha256"], hashlib.sha256((PART / "source/render_lpbf_thermal.py").read_bytes()).hexdigest())
                for item in manifest["input_summaries"]:
                    self.assertEqual(item["sha256"], hashlib.sha256((cases / item["case"] / "summary.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
