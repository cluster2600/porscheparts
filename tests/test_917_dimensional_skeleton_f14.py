import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/dimensional-skeleton-f14.json"
GENERATOR = ROOT / "twins/reference-917-engine/source/build_dimensional_skeleton_f14.py"


class DimensionalSkeletonF14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def run_generator(self, contract=CONTRACT):
        temporary = tempfile.TemporaryDirectory()
        output = Path(temporary.name) / "generated"
        result = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--contract",
                str(contract),
                "--output-dir",
                str(output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return temporary, output, result

    def test_three_variants_are_separate_and_exact(self):
        variants = {item["variant_id"]: item for item in self.contract["variants"]}
        self.assertEqual(
            set(variants),
            {"type_912_4_5_na", "917_5_0_na_4999", "917_30_turbo_5374"},
        )
        expected = {
            "type_912_4_5_na": (85.0, 66.0, 4494.0),
            "917_5_0_na_4999": (86.8, 70.4, 4999.0),
            "917_30_turbo_5374": (90.0, 70.4, 5374.0),
        }
        for variant_id, values in expected.items():
            facts = {item["fact_id"]: item for item in variants[variant_id]["facts"]}
            self.assertEqual(
                (
                    facts["bore_diameter_mm"]["value"],
                    facts["stroke_mm"]["value"],
                    facts["documented_displacement_cm3"]["value"],
                ),
                values,
            )
            self.assertEqual(facts["cylinder_count"]["value"], 12)
            self.assertTrue(all(item["source_ids"] for item in facts.values()))
            self.assertTrue(
                all(item["manufacturing_dimension"] is False for item in facts.values())
            )
        self.assertEqual(
            variants["917_5_0_na_4999"]["branch_role"],
            "scan_comparison_candidate_not_selected",
        )
        turbo_facts = {
            item["fact_id"]: item
            for item in variants["917_30_turbo_5374"]["facts"]
        }
        self.assertEqual(turbo_facts["turbocharger_count"]["value"], 2)

    def test_studs_are_unplaced_and_not_assigned_to_a_variant(self):
        stud = self.contract["shared_references"]["head_stud_reference"]
        facts = {item["fact_id"]: item for item in stud["facts"]}
        self.assertEqual(
            {key: item["value"] for key, item in facts.items()},
            {
                "stud_count": 48,
                "shaft_diameter_mm": 9.0,
                "free_length_mm": 149.5,
                "mass_each_g": 65.0,
            },
        )
        self.assertEqual(stud["candidate_scope"], "917_engine_presented_for_1970")
        self.assertEqual(stud["assigned_variant_ids"], [])
        self.assertFalse(stud["automatic_turbo_application_allowed"])
        self.assertEqual(stud["placement_status"], "unknown_unplaced")
        for field in (
            "placement_coordinates_mm",
            "thread_geometry",
            "end_geometry",
            "sleeve_geometry",
        ):
            self.assertIsNone(stud[field])

    def test_contract_is_fail_closed_and_contains_no_placement(self):
        serialized = json.dumps(self.contract, sort_keys=True)
        for forbidden in (
            "layout_hypotheses",
            "translation_mm",
            "rotation_xyz_deg",
            "position_mm",
            "center_mm",
            "interface_frame_mm",
            "envelope_mm",
        ):
            self.assertNotIn(f'"{forbidden}"', serialized)
        self.assertFalse(self.contract["authoring_policy"]["engine_component_solids_allowed"])
        self.assertEqual(self.contract["authoring_policy"]["maximum_solid_count"], 0)
        self.assertFalse(self.contract["authoring_policy"]["scan_geometry_consumed"])
        self.assertFalse(self.contract["authoring_policy"]["scan_units_converted_to_mm"])
        self.assertTrue(
            all(value is False for value in self.contract["release_gates"].values())
        )

    def test_generator_writes_only_json_and_usd_guides_by_default(self):
        temporary, output, result = self.run_generator()
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report_path = output / "917-dimensional-skeleton-f14.report.json"
        usd_path = output / "917-dimensional-skeleton-f14.usda"
        self.assertTrue(report_path.is_file())
        self.assertTrue(usd_path.is_file())
        self.assertFalse((output / "917-dimensional-skeleton-f14-guides.step").exists())
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "generated_dimension_guides_only")
        self.assertEqual(report["geometry_counts"]["solid_count"], 0)
        self.assertEqual(report["geometry_counts"]["placed_occurrence_count"], 0)
        self.assertEqual(report["geometry_counts"]["cylinder_placeholder_count"], 36)
        self.assertEqual(report["geometry_counts"]["turbocharger_placeholder_count"], 2)
        self.assertEqual(report["geometry_counts"]["head_stud_placeholder_count"], 48)
        self.assertEqual(report["outputs"]["step"]["status"], "not_requested")
        self.assertEqual(report["verified_engine_level_after_generation"], "F0_source_integrity")
        self.assertTrue(all(value is False for value in report["release"].values()))

        usda = usd_path.read_text(encoding="utf-8")
        self.assertIn("metersPerUnit = 0.001", usda)
        self.assertIn('upAxis = "Z"', usda)
        self.assertEqual(usda.count('def Xform "Cylinder_'), 36)
        self.assertEqual(usda.count('def Xform "Turbocharger_'), 2)
        self.assertEqual(usda.count('def Xform "HeadStud_'), 48)
        self.assertIn('def Xform "V_type_912_4_5_na"', usda)
        self.assertIn('def Xform "V_917_5_0_na_4999"', usda)
        self.assertIn('def Xform "V_917_30_turbo_5374"', usda)
        self.assertIn("def BasisCurves", usda)
        self.assertNotIn("def Mesh", usda)
        self.assertNotIn("Physics", usda)
        self.assertNotIn("xformOp:translate", usda)
        self.assertNotIn("xformOp:rotate", usda)

        usdchecker = shutil.which("usdchecker")
        if usdchecker:
            checked = subprocess.run(
                [usdchecker, str(usd_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_source_records_are_verified_and_hashed(self):
        temporary, output, result = self.run_generator()
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(
            (output / "917-dimensional-skeleton-f14.report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(report["sources"]), 4)
        self.assertEqual(
            {source["source_id"]: source["evidence_grade"] for source in report["sources"]},
            {
                "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS": "C",
                "SRC-KFZ-TECH-917-TYPE912-ENGINE": "D",
                "SRC-PORSCHE-NEWSROOM-91730-TURBO": "B",
                "SRC-PORSCHE-CHRISTOPHORUS-917-DILAVAR-STUDS": "A",
            },
        )
        for source in report["sources"]:
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(source["claim_tokens_verified"])

    def test_tampered_dimension_is_rejected_before_outputs(self):
        mutated = json.loads(json.dumps(self.contract))
        variant = next(
            item for item in mutated["variants"] if item["variant_id"] == "type_912_4_5_na"
        )
        next(
            item for item in variant["facts"] if item["fact_id"] == "bore_diameter_mm"
        )["value"] = 85.1
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / "tampered.json"
            contract.write_text(json.dumps(mutated), encoding="utf-8")
            temporary, output, result = self.run_generator(contract)
            self.addCleanup(temporary.cleanup)
            self.assertEqual(result.returncode, 2)
            self.assertIn("expected 85.0 mm", result.stderr)
            self.assertFalse(output.exists())

    def test_placement_or_stud_assignment_is_rejected(self):
        for mutation in ("placement", "stud_assignment"):
            with self.subTest(mutation=mutation):
                mutated = json.loads(json.dumps(self.contract))
                if mutation == "placement":
                    mutated["variants"][0]["translation_mm"] = [0, 0, 0]
                else:
                    mutated["shared_references"]["head_stud_reference"][
                        "assigned_variant_ids"
                    ] = ["917_30_turbo_5374"]
                with tempfile.TemporaryDirectory() as directory:
                    contract = Path(directory) / f"{mutation}.json"
                    contract.write_text(json.dumps(mutated), encoding="utf-8")
                    temporary, output, result = self.run_generator(contract)
                    self.addCleanup(temporary.cleanup)
                    self.assertEqual(result.returncode, 2)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
