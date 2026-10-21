"""Published dimensions constrain a bionic study without becoming fitment evidence."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"


class BionicFamilyTests(unittest.TestCase):
    def test_delivery_binds_compiler_inputs_and_delegated_inspection_code(self):
        report = json.loads((FAMILY / "derived/family/delivery-report.json").read_text())
        required = {str(p.relative_to(ROOT)) for p in (ROOT / "parts/picogk-catalog/common").glob("*.cs")}
        required.update(("twins/993-engine-mount-system-f0/source/build_study.py",
                         "twins/962-cylinder-head-f0/source/architecture/references.json",
                         "twins/962-cylinder-head-f0/source/bionic/references.json"))
        self.assertTrue(required <= report["source_hashes"].keys())
        for relative, digest in report["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
        for model in report["models"]:
            self.assertEqual(hashlib.sha256((ROOT / model["report_path"]).read_bytes()).hexdigest(), model["report_sha256"])
        invalid = json.loads((FAMILY / "derived/family/invalid-inputs.json").read_text())
        self.assertEqual(len(invalid["cases"]), 7)
        self.assertTrue(all(case["returncode"] != 0 and case["output_directory_absent"] for case in invalid["cases"]))

    def test_wrong_native_variant_is_rejected_before_any_inspection_output(self):
        spec = importlib.util.spec_from_file_location("family_inspection", FAMILY / "source/family/inspect_family.py")
        inspection = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inspection)
        config_path = FAMILY / "source/family/configs/bore-102.json"
        config = json.loads(config_path.read_text())
        for fields in (
            dict(variant_id="962-bionic-bore-95", geometry_assumptions_mm=config["geometry"]),
            dict(variant_id=config["id"], geometry_assumptions_mm={**config["geometry"], "bore_mm": 95}),
        ):
            with tempfile.TemporaryDirectory() as folder:
                native, output = Path(folder), Path(folder) / "inspected"
                (native / "native-fields-report.json").write_text(json.dumps(fields))
                with self.assertRaisesRegex(ValueError, "does not match"):
                    inspection.inspect(native, config_path, output)
                self.assertFalse(output.exists())

    def test_displacements_use_six_cylinders_and_preserve_stroke_only_geometry_reuse(self):
        data = json.loads((FAMILY / "bionic-family.json").read_text())
        self.assertFalse(data["manufacturing_authorized"])
        self.assertFalse(data["interchangeability_validated"])
        self.assertEqual(len(data["variants"]), 6)
        self.assertEqual([v["nominal_l"] for v in data["variants"]], [3.0, 3.2, 3.4, 3.6, 3.8, 4.0])
        for variant in data["variants"]:
            actual = math.pi / 4 * variant["bore_mm"] ** 2 * variant["stroke_mm"] * 6 / 1000
            self.assertAlmostEqual(actual, variant["calculated_displacement_cm3"])
            self.assertLessEqual(actual, 4000 + 1e-9)
            config = json.loads((FAMILY / variant["geometry_config"]).read_text())
            self.assertEqual(config["geometry"]["bore_mm"], variant["bore_mm"])
            self.assertNotIn("stroke_mm", config["geometry"])
        self.assertEqual(data["variants"][0]["geometry_config"], data["variants"][1]["geometry_config"])
        self.assertEqual(data["variants"][-2]["geometry_config"], data["variants"][-1]["geometry_config"])
        self.assertEqual((data["variants"][0]["bore_mm"], data["variants"][0]["stroke_mm"]), (95, 70.4))

    def test_published_values_retain_source_scope_and_unmeasured_interfaces(self):
        research = json.loads((FAMILY / "dimensional-research.json").read_text())
        source_ids = {item["id"] for item in research["sources"]}
        self.assertEqual(len(source_ids), len(research["sources"]))
        for source in research["sources"]:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertEqual(source["rights"], "copyright_reference_only_no_third_party_geometry")
        self.assertFalse(research["assumption_authorization"]["manufacturing_authorized"])
        for bore in (95, 98, 100, 102):
            config = json.loads((FAMILY / f"source/family/configs/bore-{bore}.json").read_text())
            self.assertEqual(config["geometry"]["intake_valve_diameter_mm"], 35)
            self.assertEqual(config["geometry"]["exhaust_valve_diameter_mm"], 30.5)
            self.assertFalse(any(config["qualification"].values()))
            self.assertIn("assumption", config["dimensional_basis"]["valve_diameters"])

    def test_native_receipts_keep_topology_clearance_and_uncertified_partition(self):
        for bore in (95, 98, 100, 102):
            path = FAMILY / f"derived/family/bore-{bore}-report.json"
            report = json.loads(path.read_text())
            config = FAMILY / f"source/family/configs/bore-{bore}.json"
            self.assertEqual(report["config_sha256"], hashlib.sha256(config.read_bytes()).hexdigest())
            self.assertEqual(report["config"]["geometry"]["bore_mm"], bore)
            self.assertFalse(any(report["qualification"].values()))
            self.assertGreaterEqual(report["sampled_water_dry_clearance_mm"], 4)
            for mesh in report["mesh_metrics"].values():
                self.assertTrue(mesh["watertight"] and mesh["consistent_winding"] and mesh["finite_vertices"])
                self.assertEqual(mesh["surface_components"], 1)
                self.assertGreater(mesh["volume_mm3"], 0)
            fields = report["native_fields_report"]
            self.assertTrue(fields["vdb_domains_equal"] and fields["all_active_values_checked_bidirectionally"])
            self.assertEqual(len(fields["fields"]), 5)
            self.assertGreater(fields["scalar_values_checked_each_direction"], 0)
            self.assertFalse(fields["whole_head_scaling_executed"])
            self.assertFalse(fields["fluid_solver_executed"])
            for relative, digest in report["source_hashes"].items():
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
