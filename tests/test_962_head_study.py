"""The 962 study must retain uncertainty and reject water/dry interference."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"
spec = importlib.util.spec_from_file_location("head962", FAMILY / "source/inspect_study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class Head962StudyTests(unittest.TestCase):
    def test_original_interfaces_and_physics_stay_unknown(self):
        contract = json.loads((FAMILY / "interface-contract.json").read_text())
        self.assertIs(contract["manufacturing_authorized"], False)
        self.assertIs(contract["thermal_improvement_validated"], False)
        self.assertEqual(contract["requirements"]["valves_per_cylinder"], 4)
        self.assertEqual(contract["requirements"]["spark_plugs_per_cylinder"], 2)
        for interface in contract["interfaces"].values():
            self.assertTrue(all(v is None for v in interface.values()))
        self.assertTrue(all(v is None for v in contract["physics_inputs"].values()))

    def test_export_specs_share_geometry_without_claiming_published_dimensions(self):
        dimensions = []
        for mode, name in enumerate(study.NAMES):
            data = json.loads((FAMILY / "source" / (name + ".json")).read_text())
            self.assertEqual(data["parameters"].pop("export_mode")["value"], mode)
            self.assertEqual(data["density_g_cm3"], 0)
            self.assertEqual(data["safety_class"], "prohibited_pending_engineering")
            self.assertTrue(all(p["basis"] == "assumption" and p["source"] is None for p in data["parameters"].values()))
            dimensions.append(data["parameters"])
        self.assertTrue(all(d == dimensions[0] for d in dimensions))

    def test_receipt_is_bound_to_sources_and_checked_geometry(self):
        report = json.loads((FAMILY / "derived/study-report.json").read_text())
        for key in ("manufacturing_authorized", "is_fitment_validated", "thermal_improvement_validated", "material_qualified", "wall_thickness_qualified"):
            self.assertIs(report[key], False)
        for relative, digest in report["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
        self.assertEqual(report["preview_sha256"], hashlib.sha256((FAMILY / "derived/preview.png").read_bytes()).hexdigest())
        self.assertGreater(report["sampled_water_dry_clearance_mm"], 1)
        self.assertEqual(len(report["dry_opening_probes_mm"]), 6)
        for mesh in report["mesh_metrics"].values():
            self.assertTrue(mesh["watertight"] and mesh["consistent_winding"])
            self.assertEqual(mesh["connected_components"], 1)

    @unittest.skipUnless(importlib.util.find_spec("vtk"), "optional VTK runtime unavailable")
    def test_independent_clearance_rejects_overlap_and_near_contact(self):
        import vtk
        sphere = vtk.vtkSphereSource(); sphere.SetRadius(2); sphere.Update()
        for point in ((0, 0, 0), (2.5, 0, 0)):
            with self.assertRaisesRegex(ValueError, "Water intersects"):
                study.water_dry_clearance([point], sphere.GetOutput())
        self.assertGreater(study.water_dry_clearance([(6, 0, 0)], sphere.GetOutput()), 3)


class KitProgrammeTests(unittest.TestCase):
    def test_power_screening_uses_metric_hp_and_four_stroke_units(self):
        data = json.loads((FAMILY / "kit-program.json").read_text())
        screen = data["screening"]
        power = data["power_target"]["value"] * screen["metric_hp_to_w"]
        self.assertAlmostEqual(power, 735498.75)
        self.assertEqual(screen["power_w"], power)
        for point in screen["points"]:
            self.assertAlmostEqual(point["torque_nm"] * 2 * math.pi * point["rpm"] / 60, power)
            self.assertAlmostEqual(point["brake_mean_effective_pressure_bar"] * 1e5 *
                                   screen["assumed_displacement_l"] / 1000 / (4 * math.pi), point["torque_nm"])

    def test_1000_hp_target_cannot_grant_compatibility_or_release(self):
        data = json.loads((FAMILY / "kit-program.json").read_text())
        self.assertEqual(data["power_target"]["unit"], "metric_hp_PS")
        self.assertEqual(data["power_target"]["measurement_site"], "crankshaft")
        self.assertEqual(data["power_target"]["definition_status"], "owner_confirmed")
        self.assertEqual(data["intended_use"], "bench_then_track")
        self.assertEqual(data["confirmed_requirements"], dict(
            fuel="SP95", fuel_ron=95, displacement_l=4, turbo_count=2))
        self.assertEqual(data["donor"]["requested_engine_family"], "Mezger")
        self.assertEqual(data["architecture"]["forced_induction"], "twin_turbo")
        for key in ("document", "report"):
            self.assertTrue((ROOT / data["active_sizing"][key]).is_file())
        self.assertTrue(all(value is False for value in data["acceptance"].values()))
        self.assertTrue(all(v["compatibility"] == "unverified" for v in data["variants"]))
        self.assertTrue(all(g["status"] == "open" and g["evidence"] is None for g in data["evidence_gates"]))
        self.assertIsNone(data["donor"]["selected_engine_type"])
        self.assertTrue(all(value is None for value in data["unknown_requirements"].values()))
        for path in data["existing_references"]:
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertEqual(data["market"]["orders"], 0)


if __name__ == "__main__":
    unittest.main()
