#!/usr/bin/env python3
"""Contrat fail-closed de la matrice LPBF/AdditiveFOAM F42."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "twins/reference-917-engine/f42-lpbf-doe.json"
PREPARE_PATH = ROOT / "twins/reference-917-engine/source/prepare_additivefoam_f42_doe.py"
EVALUATE_PATH = ROOT / "twins/reference-917-engine/source/evaluate_additivefoam_f42_doe.py"
EXTRACT_PATH = ROOT / "twins/reference-917-engine/source/extract_additivefoam_f42_metrics.py"
SLICING_PATH = ROOT / "twins/reference-917-engine/source/verify_f42_slicing.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f42-lpbf-doe"
sys.path.insert(0, str(PREPARE_PATH.parent))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


prepare = load_module("prepare_additivefoam_f42_doe", PREPARE_PATH)
evaluate_module = load_module("evaluate_additivefoam_f42_doe", EVALUATE_PATH)
extract_module = load_module("extract_additivefoam_f42_metrics", EXTRACT_PATH)
slicing_module = load_module("verify_f42_slicing", SLICING_PATH)


def metric(case_id: str, resolution: str = "nominal", peak: float = 2100.0) -> dict:
    resolution_factor = {"coarse": 1.02, "nominal": 1.0, "fine": 0.99}[resolution]
    return {
        "case_id": case_id,
        "resolution": resolution,
        "completed": True,
        "fatal_error": False,
        "finite": True,
        "temperature_max_k": peak,
        "temperature_p99_k": 1200.0 * resolution_factor,
        "molten_volume_mm3": 0.08 * resolution_factor,
        "melt_pool_length_mm": 0.50 * resolution_factor,
        "melt_pool_width_mm": 0.18 * resolution_factor,
        "melt_pool_depth_mm": 0.10 * resolution_factor,
        "maximum_courant_number": 0.3,
    }


class F42LpbfDoeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        cls.matrix = prepare.validate_spec(cls.spec, SPEC_PATH)

    def test_full_factorial_covers_exact_published_window(self) -> None:
        self.assertEqual(len(self.matrix), 27)
        self.assertEqual({row["laser_power_w"] for row in self.matrix}, {360, 380, 400})
        self.assertEqual({row["scan_speed_mm_s"] for row in self.matrix}, {1200, 1300, 1500})
        self.assertEqual({row["hatch_spacing_mm"] for row in self.matrix}, {0.13, 0.15, 0.16})
        self.assertEqual({row["layer_thickness_mm"] for row in self.matrix}, {0.05})
        self.assertIn("P380-V1300-H150", {row["case_id"] for row in self.matrix})
        observed = [row["volumetric_energy_density_j_mm3"] for row in self.matrix]
        self.assertTrue(math.isclose(min(observed), 30.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(max(observed), 51.28205128205128, rel_tol=1e-12))

    def test_machine_fit_and_50_um_layer_schedule_are_conditional(self) -> None:
        machine = self.spec["machine_reference"]
        orientation = self.spec["orientation_and_support"]
        slicing = self.spec["slicing_contract"]
        self.assertEqual(machine["model"], "BLT-S310 single laser")
        self.assertEqual(machine["build_volume_mm"], [250.0, 250.0, 400.0])
        self.assertEqual(orientation["orientation_id"], "scan_y_down")
        self.assertTrue(orientation["fit_is_conditional"])
        self.assertEqual(slicing["layer_height_um"], 50.0)
        self.assertEqual(slicing["expected_layer_count_from_oriented_height"], 4122)
        self.assertFalse(orientation["support_geometry_generated"])
        self.assertFalse(slicing["machine_build_file_generated"])

    def test_all_release_gates_remain_closed(self) -> None:
        self.assertTrue(self.spec["release_gates"])
        self.assertFalse(any(self.spec["release_gates"].values()))
        self.assertEqual(self.spec["additivefoam"]["temperature_limit_k"], 3300.0)
        self.assertEqual(
            self.spec["additivefoam"]["temperature_limit_policy"],
            "preserve_solver_limit_and_fail_closed_on_any_saturation",
        )

    def test_case_configuration_changes_process_not_temperature_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template"
            for relative in ("constant", "0", "system"):
                (template / relative).mkdir(parents=True, exist_ok=True)
            (template / "constant/createScanPathDict").write_text(
                "hatch 1e-4;\npower 195;\nspeed 0.8;\n", encoding="utf-8"
            )
            (template / "constant/transportProperties").write_text(
                '#include "$ADDITIVEFOAM_ETC/materials/IN625.cfg"\n', encoding="utf-8"
            )
            (template / "0/T").write_text("internalField uniform 300;\n", encoding="utf-8")
            (template / "Allrun").write_text(
                "runLayers -nLayers 2 -nCellsPerLayer 4 -layerThickness 40e-6\n",
                encoding="utf-8",
            )
            (template / "system/blockMeshDict").write_text(
                "hex (0 1 2 3 4 5 6 7) (150 25 30) simpleGrading (1 1 1)\n",
                encoding="utf-8",
            )
            (template / "system/controlDict").write_text(
                "type            meltPoolDimensions;\n        enabled         false;\n",
                encoding="utf-8",
            )
            (template / "system/decomposeParDict").write_text(
                "numberOfSubdomains 4;\n", encoding="utf-8"
            )
            (template / "system/fvSolution").write_text("Tmax 3300.0;\n", encoding="utf-8")
            row = next(row for row in self.matrix if row["case_id"] == "P380-V1300-H150")
            case = root / "case"
            configured = prepare.configure_case(template, case, row, self.spec, "nominal")
            scan = (case / "constant/createScanPathDict").read_text(encoding="utf-8")
            self.assertIn("power       380;", scan)
            self.assertIn("speed       1.3;", scan)
            self.assertIn("hatch       0.00015;", scan)
            self.assertIn("-nCellsPerLayer 5", (case / "Allrun").read_text(encoding="utf-8"))
            self.assertIn("-layerThickness 50e-6", (case / "Allrun").read_text(encoding="utf-8"))
            self.assertEqual(configured["temperature_limit_k_verified"], 3300.0)
            self.assertIn("Tmax 3300.0;", (case / "system/fvSolution").read_text(encoding="utf-8"))

    def test_modified_temperature_limit_is_rejected(self) -> None:
        altered = json.loads(json.dumps(self.spec))
        altered["additivefoam"]["temperature_limit_k"] = 4000.0
        with self.assertRaisesRegex(ValueError, "plafond_solveur_modifie_interdit"):
            prepare.validate_spec(altered, SPEC_PATH)

    def test_uncapped_converged_fixture_allows_numerical_ranking_only(self) -> None:
        measurements = [metric(row["case_id"]) for row in self.matrix]
        for selected in self.spec["resolution_study"]["case_ids"]:
            measurements.extend([metric(selected, "coarse"), metric(selected, "fine")])
        report = evaluate_module.evaluate(self.spec, measurements)
        self.assertTrue(report["gates"]["all_27_screening_cases_present"])
        self.assertTrue(report["gates"]["resolution_convergence_complete"])
        self.assertTrue(report["gates"]["doe_response_ranking_permitted"])
        self.assertFalse(report["gates"]["metal_print_authorized"])

    def test_3300_k_is_right_censored_and_fails_closed(self) -> None:
        measurements = [metric(row["case_id"]) for row in self.matrix]
        measurements[0]["temperature_max_k"] = 3300.0
        for selected in self.spec["resolution_study"]["case_ids"]:
            measurements.extend([metric(selected, "coarse"), metric(selected, "fine")])
        report = evaluate_module.evaluate(self.spec, measurements)
        self.assertEqual(report["temperature_limit_policy"]["cap_hit_count"], 1)
        self.assertEqual(report["measurements"][0]["temperature_observation"], "right_censored")
        self.assertFalse(report["gates"]["temperature_cap_free"])
        self.assertFalse(report["gates"]["doe_response_ranking_permitted"])

    def test_missing_resolution_or_unstable_result_fails_convergence(self) -> None:
        measurements = [metric(row["case_id"]) for row in self.matrix]
        report = evaluate_module.evaluate(self.spec, measurements)
        self.assertFalse(report["gates"]["all_three_resolution_levels_present"])
        self.assertFalse(report["gates"]["resolution_convergence_complete"])
        measurements[0]["maximum_courant_number"] = 0.51
        report = evaluate_module.evaluate(self.spec, measurements)
        self.assertFalse(report["gates"]["all_screening_solver_runs_valid_before_cap_gate"])
        measurements[0]["maximum_courant_number"] = 0.3
        measurements[0]["completed"] = "true"
        report = evaluate_module.evaluate(self.spec, measurements)
        self.assertFalse(report["gates"]["all_screening_solver_runs_valid_before_cap_gate"])

    def test_courant_parser_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            valid = Path(directory) / "valid.log"
            valid.write_text(
                "Courant Number mean: 0.10 max: 0.31\nCourant Number mean: 0.20 max: 0.42\n",
                encoding="utf-8",
            )
            self.assertEqual(extract_module.parse_max_courant([valid]), 0.42)
            absent = Path(directory) / "absent.log"
            absent.write_text("Time = 0.01\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "nombre_Courant_absent"):
                extract_module.parse_max_courant([absent])

    def test_supplier_slice_schedule_is_exhaustively_verified_without_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            layers = base / "layers.csv"
            with layers.open("w", encoding="utf-8") as stream:
                stream.write(
                    "layer_index,z_mm,part_exposure_area_mm2,support_exposure_area_mm2,"
                    "scan_length_mm,island_count\n"
                )
                for index in range(4122):
                    stream.write(f"{index},{index * 0.05:.6f},1.0,0.1,2.0,1\n")
            support = base / "supports.stl"
            support.write_bytes(b"solid supports\nendsolid supports\n")
            recoater = base / "recoater.json"
            recoater.write_text('{"collision_free": true}\n', encoding="utf-8")
            machine = base / "build-file.bin"
            machine.write_bytes(b"fixture-not-a-real-machine-file")
            supplier = {
                "orientation_id": "scan_y_down",
                "layer_height_um": 50.0,
                "layer_count": 4122,
                "build_z_offset_mm": 0.0,
                "layers_csv": {"path": layers.name, "sha256": slicing_module.sha256(layers)},
                "support_geometry": {"path": support.name, "sha256": slicing_module.sha256(support)},
                "recoater_collision_report": {
                    "path": recoater.name,
                    "sha256": slicing_module.sha256(recoater),
                },
                "machine_build_file": {
                    "path": machine.name,
                    "sha256": slicing_module.sha256(machine),
                },
            }
            report = slicing_module.verify(self.spec, supplier, base)
            self.assertEqual(report["layer_metrics"]["row_count"], 4122)
            self.assertTrue(report["gates"]["layer_schedule_complete_and_contiguous"])
            self.assertFalse(report["gates"]["metal_print_authorized"])
            layers.write_text(layers.read_text(encoding="utf-8").replace("1,0.050000", "2,0.050000", 1), encoding="utf-8")
            supplier["layers_csv"]["sha256"] = slicing_module.sha256(layers)
            with self.assertRaisesRegex(ValueError, "index_couche_non_contigu"):
                slicing_module.verify(self.spec, supplier, base)

    def test_published_matrix_is_generated_and_fail_closed(self) -> None:
        manifest = json.loads(
            (EVIDENCE / "917-head-lpbf-doe-f42-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["phase"], "F42")
        self.assertEqual(len(manifest["matrix"]), 27)
        self.assertEqual(manifest["configured_cases"], [])
        self.assertEqual(manifest["solver_results"], {})
        self.assertFalse(any(manifest["gates"].values()))
        rows = (EVIDENCE / "917-head-lpbf-doe-f42.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 28)
        image = EVIDENCE / "917-head-lpbf-doe-f42.png"
        visual = json.loads((EVIDENCE / "917-head-lpbf-doe-f42.json").read_text(encoding="utf-8"))
        self.assertEqual(image.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(visual["image"]["sha256"], slicing_module.sha256(image))
        self.assertFalse(visual["metal_print_authorized"])


if __name__ == "__main__":
    unittest.main()
