import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
TWIN = ROOT / "twins/reference-917-engine"
CONTRACT = TWIN / "gas-path-network-f38.json"
RUNNER = TWIN / "source/run_gas_path_network_f38.py"
AUTHOR = TWIN / "source/author_bench_overlay_f38.py"
CANONICAL_F38_REPORT = TWIN / "evidence/f38/gas-path-network-f38-report.json"
NA = "type_912_4_5_na"
TURBO = "917_30_turbo_5374"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GasPathOverlayF38Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(exist_ok=True)

    def make_temp(self):
        return tempfile.TemporaryDirectory(prefix="f38-overlay-test-", dir=WORK)

    def make_inputs(self, temp):
        f38_output = temp / "f38"
        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--project-root",
                str(ROOT),
                "--contract",
                str(CONTRACT),
                "--output",
                str(f38_output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        f38_report = f38_output / "gas-path-network-f38-report.json"
        f38 = load(f38_report)
        f37_contract = f38["source_evidence"]["integrated_bench_contract_f37"]
        f37_root = temp / "f37"
        variants = []
        for bench_variant in (NA, TURBO):
            stage = f37_root / bench_variant / "integrated-bench-f37.usda"
            stage.parent.mkdir(parents=True, exist_ok=True)
            stage.write_text(
                '#usda 1.0\n(defaultPrim = "World")\ndef Xform "World"\n{\n    def Scope "IntegratedRegistry" {}\n}\n',
                encoding="utf-8",
            )
            variants.append(
                {
                    "variant_id": bench_variant,
                    "usda_path": f"{bench_variant}/integrated-bench-f37.usda",
                    "usda_sha256": digest(stage),
                }
            )
        write_json(
            f37_root / "integrated-bench-f37-report.json",
            {
                "schema_version": "1.0.0",
                "phase": "F37",
                "status": "semantic_integrated_bench_built_all_physical_gates_blocked",
                "config": {
                    "path": f37_contract["path"],
                    "sha256": f37_contract["actual_sha256"],
                    "size_bytes": 0,
                },
                "source_integrity_checked": True,
                "physical_joint_count": 0,
                "closed_cfd_volume_count": 0,
                "release_gates": {
                    "source_integrity_complete": False,
                    "mass_and_inertia_correlated": False,
                    "physical_joints_validated": False,
                    "closed_cfd_geometry_validated": False,
                    "fluid_boundary_conditions_validated": False,
                    "engine_start_authorized": False,
                    "manufacturing_geometry_ready": False,
                    "performance_1600_hp_claim_authorized": False,
                },
                "variants": variants,
            },
        )
        return f38_report, f37_root

    def run_author(
        self,
        f38_report,
        f37_root,
        output,
        canonical_f38_report=CANONICAL_F38_REPORT,
    ):
        result = subprocess.run(
            [
                sys.executable,
                str(AUTHOR),
                "--contract",
                str(CONTRACT),
                "--f37-work-root",
                str(f37_root),
                "--f38-report",
                str(f38_report),
                "--canonical-f38-report",
                str(canonical_f38_report),
                "--output",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        report_path = output / "bench-overlay-f38-report.json"
        report = load(report_path) if report_path.is_file() else None
        return result, report

    def test_authors_two_canonical_report_verified_embedded_overlays_without_physics(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            output = temp / "overlays"
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(report["variant_count"], 2)
            self.assertTrue(report["f38_report_matches_canonical_bytes"])
            self.assertTrue(report["f37_stages_embedded"])
            self.assertTrue(report["atomic_output_commit"])
            self.assertFalse(report["existing_output_overwritten"])
            self.assertEqual(
                report["canonical_f38_report_sha256"], digest(CANONICAL_F38_REPORT)
            )
            self.assertFalse(report["geometry_authored"])
            self.assertFalse(report["physics_schema_authored"])
            self.assertFalse(report["physical_joint_authored"])
            self.assertFalse(report["target_power_proven"])
            variants = {item["bench_variant_id"]: item for item in report["variants"]}
            self.assertEqual(variants[NA]["station_count"], 5)
            self.assertEqual(variants[TURBO]["station_count"], 15)
            for bench_variant in (NA, TURBO):
                overlay = output / bench_variant / "bench-overlay-f38.usda"
                embedded = output / bench_variant / "integrated-bench-f37.usda"
                self.assertEqual(digest(overlay), variants[bench_variant]["overlay_sha256"])
                self.assertEqual(
                    digest(embedded),
                    variants[bench_variant]["embedded_f37_stage_sha256"],
                )
                self.assertEqual(
                    digest(embedded),
                    variants[bench_variant]["f37_source_stage_report_declared_sha256"],
                )
                text = overlay.read_text(encoding="utf-8")
                self.assertIn("subLayers", text)
                self.assertIn("@integrated-bench-f37.usda@", text)
                self.assertIn("f37ContractSha256", text)
                self.assertIn("embeddedF37StageSha256", text)
                self.assertIn("canonicalF38ReportSha256", text)
                self.assertIn('def Scope "F38GasPath"', text)
                self.assertIn('def Scope "Stations"', text)
                self.assertIn("physicsSchemaAuthoredByF38 = false", text)
                self.assertIn("targetPowerProven = false", text)
                self.assertNotIn("PhysicsRigidBodyAPI", text)
                self.assertNotIn("PhysicsCollisionAPI", text)
                self.assertNotIn("Physx", text)
            turbo_text = (
                output / TURBO / "bench-overlay-f38.usda"
            ).read_text(encoding="utf-8")
            self.assertIn("compressorPressureRatio = 3.215625", turbo_text)
            self.assertIn("wastegateBypassFraction = 0.234303344041", turbo_text)
            self.assertIn("compressorMapDigitized = false", turbo_text)
            expected_power = next(
                item
                for item in load(f38_report)["variants"]
                if item["bench_variant_id"] == TURBO
            )["target_comparison"]["forward_predicted_mechanical_hp"]
            authored_power = re.search(
                r"forwardPredictedMechanicalHp = ([-+0-9.eE]+)", turbo_text
            )
            self.assertIsNotNone(authored_power)
            self.assertEqual(float(authored_power.group(1)), expected_power)
            self.assertIn(repr(expected_power), turbo_text)

    def test_tampered_f37_stage_is_rejected_before_overlay_authoring(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            stage = f37_root / TURBO / "integrated-bench-f37.usda"
            stage.write_text(stage.read_text(encoding="utf-8") + "# tampered\n", encoding="utf-8")
            output = temp / "overlays"
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("F37 stage hash mismatch", result.stderr)

    def test_tampered_f38_report_is_rejected_against_canonical_bytes(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            value = load(f38_report)
            value["release_gates"]["target_power_proven"] = True
            write_json(f38_report, value)
            output = temp / "overlays"
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("F38 report canonical hash mismatch", result.stderr)

    def test_f37_report_contract_hash_must_match_canonical_f38_evidence(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            f37_report = f37_root / "integrated-bench-f37-report.json"
            value = load(f37_report)
            value["config"]["sha256"] = "0" * 64
            write_json(f37_report, value)
            output = temp / "overlays"
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("F37 report config hash does not match", result.stderr)

    def test_f37_report_contract_path_must_match_canonical_f38_evidence(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            f37_report = f37_root / "integrated-bench-f37-report.json"
            value = load(f37_report)
            value["config"]["path"] = "twins/reference-917-engine/other-f37.json"
            write_json(f37_report, value)
            output = temp / "overlays"
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("F37 report config path does not match", result.stderr)

    def test_duplicate_f38_variant_is_rejected_even_with_matching_custom_canonical(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            value = load(f38_report)
            value["variants"][1] = copy.deepcopy(value["variants"][0])
            write_json(f38_report, value)
            alternate_canonical = temp / "alternate-canonical-f38-report.json"
            write_json(alternate_canonical, value)
            output = temp / "overlays"
            result, report = self.run_author(
                f38_report,
                f37_root,
                output,
                canonical_f38_report=alternate_canonical,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("duplicate F38 variants variant_id", result.stderr)

    def test_duplicate_f37_variant_is_rejected(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            f37_report = f37_root / "integrated-bench-f37-report.json"
            value = load(f37_report)
            value["variants"][1] = copy.deepcopy(value["variants"][0])
            write_json(f37_report, value)
            output = temp / "overlays"
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("duplicate F37 variants variant_id", result.stderr)

    def test_f37_stage_path_escape_is_rejected(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            escaped = temp / "escaped.usda"
            escaped.write_text("#usda 1.0\n", encoding="utf-8")
            f37_report = f37_root / "integrated-bench-f37-report.json"
            value = load(f37_report)
            variant = next(item for item in value["variants"] if item["variant_id"] == NA)
            variant["usda_path"] = "../escaped.usda"
            variant["usda_sha256"] = digest(escaped)
            write_json(f37_report, value)
            output = temp / "overlays"
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("path must remain within F37 root", result.stderr)

    def test_colliding_f37_stage_paths_are_rejected(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            f37_report = f37_root / "integrated-bench-f37-report.json"
            value = load(f37_report)
            variants = {item["variant_id"]: item for item in value["variants"]}
            variants[TURBO]["usda_path"] = variants[NA]["usda_path"]
            variants[TURBO]["usda_sha256"] = variants[NA]["usda_sha256"]
            write_json(f37_report, value)
            output = temp / "overlays"
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("F37 stage path collision", result.stderr)

    def test_colliding_usda_station_identifiers_are_rejected(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            value = load(f38_report)
            turbo = next(item for item in value["variants"] if item["bench_variant_id"] == TURBO)
            turbo["nodes"][1]["id"] = "collision-a"
            turbo["nodes"][2]["id"] = "collision_a"
            write_json(f38_report, value)
            alternate_canonical = temp / "alternate-canonical-f38-report.json"
            write_json(alternate_canonical, value)
            output = temp / "overlays"
            result, report = self.run_author(
                f38_report,
                f37_root,
                output,
                canonical_f38_report=alternate_canonical,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("colliding USDA station identifier", result.stderr)

    def test_existing_output_is_preserved_by_atomic_no_overwrite_publication(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f38_report, f37_root = self.make_inputs(temp)
            output = temp / "overlays"
            output.mkdir()
            sentinel = output / "sentinel.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            result, report = self.run_author(f38_report, f37_root, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("atomic no-overwrite publication required", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")


if __name__ == "__main__":
    unittest.main()
