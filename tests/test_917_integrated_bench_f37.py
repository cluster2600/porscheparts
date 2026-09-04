import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
TWIN = ROOT / "twins/reference-917-engine"
CONFIG = TWIN / "integrated-bench-assembly-f37.json"
BUILDER = TWIN / "source/build_integrated_bench_f37.py"
DUCTS = TWIN / "ducts-f8.json"
NA = "type_912_4_5_na"
TURBO = "917_30_turbo_5374"
EXPECTED_COUNTS = {
    "crankshaft": 1,
    "main_bearing": 8,
    "connecting_rod": 12,
    "piston": 12,
    "piston_pin": 12,
    "piston_ring": 36,
}
EXPECTED_FRAME_COUNTS = {
    "crankshaft_axis": 1,
    "main_journal_centres_01_to_08": 8,
    "crankpin_centres_01_to_06": 6,
    "rod_big_end_axis": 12,
    "rod_small_end_axis": 12,
    "piston_pin_axis": 12,
    "piston_crown_datum": 12,
    "piston_ring_groove_datums": 36,
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def false_gates():
    return {
        "mass_and_inertia_correlated": False,
        "physical_joints_validated": False,
        "engine_start_authorized": False,
        "manufacturing_geometry_ready": False,
        "performance_1600_hp_claim_authorized": False,
    }


def make_f35_fixture(root):
    contract_sha = "a" * 64
    run_variants = []
    for variant_id in (NA, TURBO):
        variant_root = root / variant_id
        interface_frames = [
            {
                "id": f"{family}_{index:02d}",
                "family": family,
                "physical_joint_enabled": False,
            }
            for family, count in EXPECTED_FRAME_COUNTS.items()
            for index in range(1, count + 1)
        ]
        geometry = {
            "schema_version": "1.0.0",
            "phase": "F35",
            "variant_id": variant_id,
            "contract_sha256": contract_sha,
            "component_instance_counts": {
                **EXPECTED_COUNTS,
                "main_bearing_pair": EXPECTED_COUNTS["main_bearing"],
            },
            "candidate_joint_counts": {"total": 37, "enabled": 0},
            "interface_frames": interface_frames,
            "interface_frame_total": 99,
            "interface_frame_family_counts": EXPECTED_FRAME_COUNTS,
            "release_gates": false_gates(),
        }
        geometry["component_instance_counts"].pop("main_bearing")
        geometry_path = variant_root / "geometry-report.json"
        write_json(geometry_path, geometry)

        usdc_path = variant_root / "usd/rotating-assembly-f35.usdc"
        usdc_path.parent.mkdir(parents=True, exist_ok=True)
        usdc_path.write_bytes(f"PXR-USDC-F35-FIXTURE:{variant_id}\n".encode())
        usd_report = {
            "schema_version": "1.0.0",
            "phase": "F35",
            "variant_id": variant_id,
            "contract_sha256": contract_sha,
            "usd_sha256": digest(usdc_path),
            "component_occurrence_counts": EXPECTED_COUNTS,
            "component_occurrence_total": 81,
            "candidate_interfaces": {
                "total": 37,
                "enabled": 0,
                "physical_joint_authored": 0,
            },
            "authored_physics": {
                "active_joint_count": 0,
                "rigid_body_count": 0,
                "collider_count": 0,
                "mass_property_count": 0,
                "inertia_property_count": 0,
            },
            "datum_frames": {
                "total": 99,
                "family_counts": EXPECTED_FRAME_COUNTS,
                "measured": 0,
                "physical_joint_authored": 0,
            },
            "release_gates": false_gates(),
            "simulationValidated": False,
            "manufacturingReleased": False,
            "powerValidated": False,
        }
        write_json(variant_root / "usd/rotating-assembly-f35-report.json", usd_report)
        run_variants.append(
            {
                "variant_id": variant_id,
                "report": f"{variant_id}/geometry-report.json",
                "report_sha256": digest(geometry_path),
            }
        )
    write_json(
        root / "run-report.json",
        {
            "schema_version": "1.0.0",
            "phase": "F35",
            "status": "two_rotating_assembly_design_studies_built",
            "contract_sha256": contract_sha,
            "variant_count": 2,
            "variants": run_variants,
            "physical_kinematics_ready": False,
            "manufacturing_geometry_ready": False,
            "engine_power_proven": False,
        },
    )


def rebind_geometry_report(root, variant_id):
    geometry_path = root / variant_id / "geometry-report.json"
    run_path = root / "run-report.json"
    run = load(run_path)
    next(item for item in run["variants"] if item["variant_id"] == variant_id)[
        "report_sha256"
    ] = digest(geometry_path)
    write_json(run_path, run)


class IntegratedBenchF37Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(exist_ok=True)
        cls.config = load(CONFIG)

    def make_temp(self):
        return tempfile.TemporaryDirectory(prefix="f37-test-", dir=WORK)

    def run_builder(self, temp, config_path=CONFIG):
        f35 = temp / "f35"
        output = temp / "output"
        if not f35.exists():
            make_f35_fixture(f35)
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--project-root",
                str(ROOT),
                "--config",
                str(config_path),
                "--f35-work-root",
                str(f35),
                "--output",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        report_path = output / "integrated-bench-f37-report.json"
        report = load(report_path) if report_path.is_file() else None
        return result, f35, output, report

    def test_contract_is_explicitly_fail_closed_and_crosswalk_does_not_merge_variants(self):
        self.assertEqual(self.config["phase"], "F37")
        self.assertEqual(
            set(self.config["classification_vocabulary"]), {"proxy", "not_modelled"}
        )
        self.assertTrue(all(value is False for value in self.config["release_gates"].values()))
        variants = {item["variant_id"]: item for item in self.config["variants"]}
        self.assertEqual(set(variants), {NA, TURBO})
        self.assertEqual(variants[NA]["f28_variant_id"], "type_912_5_0_na")
        self.assertFalse(variants[NA]["f28_identity_match"])
        self.assertIn("no_dimension_geometry", variants[NA]["f28_reuse_scope"])
        self.assertFalse(variants[TURBO]["f28_identity_match"])
        self.assertFalse(self.config["output_policy"]["physics_schema_authored"])
        self.assertFalse(self.config["output_policy"]["cfd_volume_authored"])
        self.assertEqual(self.config["f35_expected"]["interface_frame_total"], 99)
        self.assertEqual(
            self.config["f35_expected"]["interface_frame_family_counts"],
            EXPECTED_FRAME_COUNTS,
        )

    def test_builder_publishes_two_hash_bound_semantic_registries(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            result, _, output, report = self.run_builder(temp)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(
                report["status"],
                "semantic_integrated_bench_built_all_physical_gates_blocked",
            )
            self.assertTrue(report["source_integrity_checked"])
            self.assertTrue(report["semantic_registry_built"])
            self.assertFalse(report["openusd_runtime_used"])
            for key in (
                "engine_start_authorized",
                "manufacturing_geometry_ready",
                "performance_1600_hp_claim_authorized",
            ):
                self.assertFalse(report[key])
            self.assertEqual(report["physical_joint_count"], 0)
            self.assertEqual(report["closed_cfd_volume_count"], 0)
            self.assertEqual(len(report["source_contract_evidence"]), 6)
            self.assertEqual(len(report["f35_runtime_evidence"]), 7)
            for item in report["source_contract_evidence"] + report["f35_runtime_evidence"]:
                self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

            variants = {item["variant_id"]: item for item in report["variants"]}
            expected = {
                NA: {
                    "families": (45, 6, 39),
                    "mechanical": (17, 117),
                    "ducts": (14, 82),
                    "seals": (22, 170),
                    "external": (4, 4),
                    "states": (49, 75, 267, 252),
                },
                TURBO: {
                    "families": (53, 6, 47),
                    "mechanical": (18, 119),
                    "ducts": (19, 92),
                    "seals": (28, 192),
                    "external": (6, 6),
                    "states": (52, 94, 271, 284),
                },
            }
            for variant_id, values in expected.items():
                self.assertEqual(variants[variant_id]["f35_component_counts"], EXPECTED_COUNTS)
                self.assertEqual(variants[variant_id]["f35_component_occurrence_total"], 81)
                self.assertEqual(variants[variant_id]["f35_interface_frame_total"], 99)
                self.assertEqual(
                    variants[variant_id]["f35_interface_frame_family_counts"],
                    EXPECTED_FRAME_COUNTS,
                )
                counts = variants[variant_id]["counts"]
                families = counts["collections"]["component_families"]
                self.assertEqual(
                    (
                        families["group_count"],
                        families["proxy_group_count"],
                        families["not_modelled_group_count"],
                    ),
                    values["families"],
                )
                for key, collection in (
                    ("mechanical", "mechanical_connections"),
                    ("ducts", "ducts"),
                    ("seals", "sealing_interfaces"),
                    ("external", "external_interfaces"),
                ):
                    self.assertEqual(
                        (
                            counts["collections"][collection]["group_count"],
                            counts["collections"][collection]["declared_instance_count"],
                        ),
                        values[key],
                    )
                self.assertEqual(
                    (
                        counts["model_states"]["proxy"]["group_count"],
                        counts["model_states"]["not_modelled"]["group_count"],
                        counts["model_states"]["proxy"]["declared_instance_count"],
                        counts["model_states"]["not_modelled"]["declared_instance_count"],
                    ),
                    values["states"],
                )
                stage = output / variants[variant_id]["usda_path"]
                text = stage.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("#usda 1.0"))
                self.assertIn(f'custom string variantId = "{variant_id}"', text)
                self.assertIn("custom int f35InterfaceFrameTotal = 99", text)
                self.assertIn("custom int f35MeasuredInterfaceFrameCount = 0", text)
                self.assertIn('custom token modelState = "proxy"', text)
                self.assertIn('custom token modelState = "not_modelled"', text)
                for token in (
                    "PhysicsJoint",
                    "PhysicsRigidBodyAPI",
                    "PhysicsCollisionAPI",
                    "PhysicsScene",
                    "def Mesh",
                    "def Volume",
                ):
                    self.assertNotIn(token, text)

    def test_tampered_f35_usdc_is_rejected_before_usda_authoring(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            make_f35_fixture(temp / "f35")
            target = temp / "f35" / NA / "usd/rotating-assembly-f35.usdc"
            target.write_bytes(target.read_bytes() + b"tamper")
            result, _, output, report = self.run_builder(temp)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(report["status"], "blocked_before_authoring")
            self.assertTrue(any("USDC hash" in item for item in report["errors"]))
            self.assertEqual(list(output.rglob("*.usda")), [])

    def test_true_f35_release_gate_is_rejected(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            make_f35_fixture(temp / "f35")
            report_path = temp / "f35" / TURBO / "usd/rotating-assembly-f35-report.json"
            usd_report = load(report_path)
            usd_report["release_gates"]["performance_1600_hp_claim_authorized"] = True
            write_json(report_path, usd_report)
            result, _, output, report = self.run_builder(temp)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("must be explicitly false" in item for item in report["errors"]))
            self.assertEqual(list(output.rglob("*.usda")), [])

    def test_mutated_geometry_interface_frame_inventory_is_rejected_even_when_rehashed(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f35 = temp / "f35"
            make_f35_fixture(f35)
            geometry_path = f35 / NA / "geometry-report.json"
            geometry = load(geometry_path)
            geometry["interface_frames"].pop()
            geometry["interface_frame_total"] = 98
            geometry["interface_frame_family_counts"]["piston_ring_groove_datums"] = 35
            write_json(geometry_path, geometry)
            rebind_geometry_report(f35, NA)
            result, _, output, report = self.run_builder(temp)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("interface frame total" in item for item in report["errors"]))
            self.assertTrue(any("interface frame family counts" in item for item in report["errors"]))
            self.assertEqual(list(output.rglob("*.usda")), [])

    def test_mutated_usd_datum_frame_inventory_is_rejected(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            f35 = temp / "f35"
            make_f35_fixture(f35)
            report_path = f35 / TURBO / "usd/rotating-assembly-f35-report.json"
            usd_report = load(report_path)
            usd_report["datum_frames"]["measured"] = 1
            write_json(report_path, usd_report)
            result, _, output, report = self.run_builder(temp)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("USD datum frame" in item for item in report["errors"]))
            self.assertEqual(list(output.rglob("*.usda")), [])

    def test_closed_cfd_claim_without_hash_bound_watertight_proof_is_rejected(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            ducts = copy.deepcopy(load(DUCTS))
            ducts["ducts"][0]["geometry_released"] = True
            tampered_ducts = temp / "ducts-with-unsupported-claim.json"
            write_json(tampered_ducts, ducts)
            config = copy.deepcopy(self.config)
            config["source_contracts"]["ducts_f8"] = {
                "path": str(tampered_ducts),
                "expected_sha256": digest(tampered_ducts),
            }
            config_path = temp / "f37-unsupported-cfd-claim.json"
            write_json(config_path, config)
            result, _, output, report = self.run_builder(temp, config_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("complete proof required" in item for item in report["errors"]))
            self.assertEqual(list(output.rglob("*.usda")), [])


if __name__ == "__main__":
    unittest.main()
