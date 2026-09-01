import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/build_parametric_interface_f13.py"
SOURCE_CONTRACT = ROOT / "twins/reference-917-engine/source-scan-integrity-f11.json"
ENGINEERING_CONTRACT = ROOT / "twins/reference-917-engine/reengineering-contract-f11.json"
REFERENCE_CONTRACT = ROOT / "twins/reference-917-engine/complete-engine-f1.json"
AMS_SOURCE = ROOT / "catalog/sources/src-ams-917-engine-technical-analysis.json"
REAL_INTERFACES = ROOT / "work/917-engine/vast-output/reports/interfaces.json"


def fixture_interfaces() -> dict:
    bank_x = {
        "positive": [-360.0, -242.0, -124.0, 49.0, 167.0, 285.0],
        "negative": [-324.0, -206.0, -88.0, 86.0, 204.0, 322.0],
    }
    diameters = {
        "positive": [86.7, 86.5, 86.3, 86.4, 85.9, 85.2],
        "negative": [86.6, 87.8, 86.9, 86.9, 87.1, 87.2],
    }
    banks = {}
    pitch = {}
    for bank_name, sign in (("positive", 1), ("negative", -1)):
        banks[bank_name] = []
        for index, (x, diameter) in enumerate(zip(bank_x[bank_name], diameters[bank_name])):
            z = -10.0 - index
            depth = 188.0 + index
            banks[bank_name].append(
                {
                    "center_longitudinal_vertical": [x, z],
                    "diameter_obj_units": diameter,
                    "circle_fit_p95_obj_units": 1.3,
                    "rim_outward_depth_mode_obj_units": depth,
                    "center_scan_coordinates": [x, sign * depth, z],
                    "axis_scan_coordinates": [0.0, float(sign), 0.0],
                }
            )
        gaps = [
            bank_x[bank_name][index + 1] - bank_x[bank_name][index]
            for index in range(5)
        ]
        regular = gaps[:2] + gaps[3:]
        pitch[bank_name] = {
            "successive_longitudinal_gaps_obj_units": gaps,
            "median_regular_pitch_obj_units": sorted(regular)[len(regular) // 2],
            "central_split_gap_obj_units": gaps[2],
            "central_split_after_cylinder": 3,
        }
    all_diameters = diameters["positive"] + diameters["negative"]
    return {
        "status": "F1_detected_exterior_interfaces",
        "units": "OBJ units; 1 unit = 1 mm is plausible but unconfirmed",
        "centroid_scan_coordinates": [10.0, 20.0, 30.0],
        "frame_rows_longitudinal_bank_axis_vertical": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        "banks": banks,
        "pitch": pitch,
        "mean_visible_opening_diameter_obj_units": sum(all_diameters) / len(all_diameters),
    }


class ParametricInterfaceF13Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.interfaces = self.base / "interfaces.json"
        self.interfaces.write_text(json.dumps(fixture_interfaces()), encoding="utf-8")
        self.output = self.base / "output"

    def tearDown(self):
        self.temp.cleanup()

    def run_generator(self, *, interfaces: Path | None = None, check: bool = True):
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--interfaces",
                str(interfaces or self.interfaces),
                "--source-contract",
                str(SOURCE_CONTRACT),
                "--engineering-contract",
                str(ENGINEERING_CONTRACT),
                "--reference-contract",
                str(REFERENCE_CONTRACT),
                "--ams-source",
                str(AMS_SOURCE),
                "--output-dir",
                str(self.output),
            ],
            text=True,
            capture_output=True,
            check=check,
        )

    def read_spec(self):
        return json.loads(
            (self.output / "917-engine-interface-master-f13.spec.json").read_text(
                encoding="utf-8"
            )
        )

    def test_generates_two_banks_of_six_and_remains_fail_closed(self):
        self.run_generator()
        spec = self.read_spec()
        self.assertEqual(spec["status"], "provisional_interface_master_fit_check_only")
        self.assertEqual(len(spec["cylinder_interfaces"]), 12)
        self.assertEqual([len(bank["cylinder_ids"]) for bank in spec["banks"]], [6, 6])
        self.assertEqual(spec["units"]["native"], "OBJ_unit")
        self.assertEqual(spec["units"]["unit_status"], "unconfirmed")
        self.assertIsNone(spec["units"]["mm_per_obj_unit"])
        self.assertFalse(any(spec["release_gates"].values()))
        self.assertEqual(spec["stud_locations"], [])
        self.assertEqual(spec["stud_status"], "not_detected_not_generated")

    def test_preserves_measurement_and_reference_provenance(self):
        self.run_generator()
        spec = self.read_spec()
        interface_source = next(
            item
            for item in spec["source_contracts"]
            if item["role"] == "detected_interface_report"
        )
        self.assertEqual(
            interface_source["sha256"],
            hashlib.sha256(self.interfaces.read_bytes()).hexdigest(),
        )
        for interface in spec["cylinder_interfaces"]:
            for field in ("layout_center", "scan_center", "scan_axis", "visible_opening_diameter", "circle_fit_p95"):
                value = interface[field]
                self.assertEqual(value["classification"], "measured_from_scan_obj_units")
                self.assertTrue(value["provenance"]["json_pointer"].startswith("/banks/"))
        candidates = spec["published_reference_candidates"]
        for bore in candidates["variant_bores"].values():
            self.assertEqual(bore["classification"], "published_reference_candidate")
            self.assertTrue(bore["provenance"]["source_ids"])
        self.assertEqual(
            candidates["regular_cylinder_pitch"]["classification"],
            "published_reference_candidate",
        )

    def test_central_split_is_a_layout_datum_not_a_machined_face(self):
        self.run_generator()
        spec = self.read_spec()
        central = next(item for item in spec["datums"] if item["id"] == "D-CENTRAL-MID-GAP")
        self.assertFalse(central["manufacturing_datum"])
        self.assertIn("not a verified crankcase split face", central["definition"])
        self.assertEqual(central["x"]["classification"], "measured_from_scan_obj_units")
        self.assertEqual(spec["component_interface_scope"]["crankcase"].split(";")[0], "central layout plane and frame only")

    def test_generated_cad_text_has_no_stl_or_invented_studs(self):
        self.run_generator()
        scad = (self.output / "917-engine-interface-master-f13.scad").read_text(encoding="utf-8")
        build123d = (
            self.output / "917-engine-interface-master-f13-build123d.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(scad.count('["CYL-'), 12)
        self.assertIn("MM_PER_OBJ_UNIT = undef", scad)
        self.assertIn("FABRICATION_RELEASED = false", scad)
        self.assertNotIn("stud_marker", scad.lower())
        self.assertIn("export_step", build123d)
        self.assertNotIn("export_stl", build123d)
        self.assertIn('if SPEC["stud_locations"]', build123d)
        self.assertIn('F13_ALLOW_UNSCALED_STEP") != "fit-check-only"', build123d)
        self.assertIn("physical_mm_conversion_released", build123d)
        self.assertNotIn(".stl", build123d.lower())

    def test_5_litre_scale_match_is_only_a_hypothesis_candidate(self):
        self.run_generator()
        spec = self.read_spec()
        comparison = spec["scan_to_published_scale_hypotheses"]
        self.assertEqual(comparison["status"], "comparison_only_no_scale_or_identity_release")
        candidates = {item["variant_id"]: item for item in comparison["candidates"]}
        self.assertEqual(
            set(candidates),
            {"type_912_4_5_na", "917_5_0_na_4999", "917_30_turbo_5374"},
        )
        five_litre = candidates["917_5_0_na_4999"]
        self.assertFalse(five_litre["identity_released"])
        self.assertFalse(five_litre["scale_released"])
        self.assertIn("not_identity_or_scale_release", five_litre["status"])
        self.assertIsNone(comparison["decision"])

    def test_rejects_a_source_hash_mismatch(self):
        bad_contract = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
        bad_contract["artifacts"][0]["sha256"] = "0" * 64
        bad_path = self.base / "bad-source-contract.json"
        bad_path.write_text(json.dumps(bad_contract), encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--interfaces",
                str(self.interfaces),
                "--source-contract",
                str(bad_path),
                "--engineering-contract",
                str(ENGINEERING_CONTRACT),
                "--reference-contract",
                str(REFERENCE_CONTRACT),
                "--ams-source",
                str(AMS_SOURCE),
                "--output-dir",
                str(self.output),
            ],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("disagree on the scan SHA-256", result.stderr)

    def test_rejects_six_plus_five_instead_of_two_banks_of_six(self):
        data = fixture_interfaces()
        data["banks"]["negative"].pop()
        self.interfaces.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_generator(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must contain exactly six openings", result.stderr)

    @unittest.skipUnless(REAL_INTERFACES.exists(), "local scan-derived interface report is outside Git")
    def test_local_real_report_regression_values_are_not_scale_release(self):
        self.run_generator(interfaces=REAL_INTERFACES)
        comparison = self.read_spec()["scan_to_published_scale_hypotheses"]
        self.assertAlmostEqual(comparison["mean_visible_opening"]["value"], 86.6270757961)
        self.assertAlmostEqual(comparison["mean_regular_pitch"]["value"], 117.9640045530)
        candidates = {item["variant_id"]: item for item in comparison["candidates"]}
        five_litre = candidates["917_5_0_na_4999"]
        self.assertAlmostEqual(five_litre["candidate_mm_per_obj_unit"]["value"], 1.0019961912)
        self.assertAlmostEqual(five_litre["implied_regular_pitch"]["value"], 118.1994832575)
        self.assertAlmostEqual(five_litre["pitch_delta_vs_118_percent"], 0.1690536080)
        self.assertFalse(five_litre["scale_released"])


if __name__ == "__main__":
    unittest.main()
