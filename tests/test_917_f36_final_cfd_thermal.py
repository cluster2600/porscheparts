#!/usr/bin/env python3

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/build_f36_final_cfd_thermal_evidence.py"
PUBLISHED = ROOT / "twins/reference-917-engine/evidence/f36-final-cfd-thermal"
SPEC = importlib.util.spec_from_file_location("f36_final_cfd_thermal", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FinalCfdThermalEvidenceTests(unittest.TestCase):
    @staticmethod
    def digest(path: Path) -> str:
        result = hashlib.sha256()
        result.update(path.read_bytes())
        return result.hexdigest()

    def make_case(self, root: Path, with_heat: bool) -> Path:
        case = root / "coarse"
        (case / "constant/polyMesh").mkdir(parents=True)
        (case / "constant/polyMesh/boundary").write_text(
            "4\n(\nhead\n{\n type wall;\n nFaces 123;\n startFace 456;\n}\n)\n",
            encoding="utf-8",
        )
        (case / "log.fluid-recovered").write_text("solver output\nEnd\n", encoding="utf-8")
        (case / "log.checkMesh-recovered-default").write_text(
            "    cells: 200305\nMesh OK.\n", encoding="utf-8"
        )
        (case / "log.checkMesh-recovered-strict").write_text("Mesh OK.\n", encoding="utf-8")
        data = {
            "outletMassFlow/0/surfaceFieldValue.dat": "0 0.85\n",
            "weightedOutletTemperature/0/surfaceFieldValue.dat": "0 340\n",
            "inletPressure/0/surfaceFieldValue.dat": "0 102000\n",
            "outletTotalEnergyTerms/0/surfaceFieldValue.dat": "0 0 1000\n",
        }
        if with_heat:
            data["headHeatFlux/0/wallHeatFlux.dat"] = (
                "0 head 0 0 27000 100000\n"
                "1 head 0 0 27200 101000\n"
            )
        for relative, content in data.items():
            target = case / "postProcessing" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return case

    def test_rejects_case_without_head_heat_flux_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            result = MODULE.parse_openfoam(self.make_case(Path(directory), with_heat=False))
        self.assertEqual(result["status"], "incomplete_or_rejected")
        self.assertFalse(result["head_heat_flux_rows_present"])

    def test_accepts_geometry_resolved_completed_case(self):
        with tempfile.TemporaryDirectory() as directory:
            result = MODULE.parse_openfoam(self.make_case(Path(directory), with_heat=True))
        self.assertEqual(result["status"], "completed_geometry_resolved_screen")
        self.assertEqual(result["head_patch_faces"], 123)
        self.assertEqual(result["cells"], 200305)
        self.assertTrue(all(result["checks"].values()))

    def test_does_not_accept_partial_solver_with_heat_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(Path(directory), with_heat=True)
            (case / "log.fluid-recovered").write_text(
                "Time = 6s\nFloating point exception\n", encoding="utf-8"
            )
            result = MODULE.parse_openfoam(case)
        self.assertEqual(result["status"], "completed_with_failed_checks")
        self.assertFalse(result["solver_completed"])
        self.assertFalse(result["checks"]["solver_completed"])

    def test_restart_series_uses_latest_time_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for start, content in (
                ("0", "0 1\n40 2\n"),
                ("40", "100 3\n120 4\n"),
                ("100", "790 5\n800 6\n"),
            ):
                target = root / "headHeatFlux" / start / "wallHeatFlux.dat"
                target.parent.mkdir(parents=True)
                target.write_text(content, encoding="utf-8")
            latest, previous = MODULE.function_rows(root, "headHeatFlux", "wallHeatFlux.dat")
        self.assertEqual(latest, ["800", "6"])
        self.assertEqual(previous, ["790", "5"])

    def test_restart_duplicate_time_prefers_later_restart_and_records_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for start, content in (
                ("0", "0 1\n120 2\n"),
                ("100", "120 3\n130 4\n"),
            ):
                target = root / "headHeatFlux" / start / "wallHeatFlux.dat"
                target.parent.mkdir(parents=True)
                target.write_text(content, encoding="utf-8")
            selection = MODULE.function_selection(root, "headHeatFlux", "wallHeatFlux.dat")
        self.assertEqual(selection["previous"]["row"], ["120", "3"])
        self.assertEqual(selection["previous"]["path"].parent.name, "100")
        self.assertEqual(selection["duplicate_time_rows_removed"], 1)

    def test_compact_copy_removes_stale_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_case(root / "source", with_heat=True)
            destination = root / "published/coarse"
            MODULE.copy_openfoam_evidence(source, destination)
            (destination / "stale.txt").write_text("stale", encoding="utf-8")
            MODULE.copy_openfoam_evidence(source, destination)
            self.assertFalse((destination / "stale.txt").exists())

    def test_published_bundle_manifest_covers_exact_compact_tree(self):
        manifest = json.loads((PUBLISHED / "bundle-manifest.json").read_text(encoding="utf-8"))
        records = {item["path"]: item for item in manifest["artifacts"]}
        expected = {
            "cross-solver-report.json",
            "openfoam-run-manifest.json",
            "917-head-f36-final-cfd-thermal.png",
            *{
                path.relative_to(PUBLISHED).as_posix()
                for path in (PUBLISHED / "openfoam-runs").rglob("*")
                if path.is_file()
            },
        }
        self.assertEqual(set(records), expected)
        self.assertEqual(manifest["artifact_count"], len(expected))
        for relative, record in records.items():
            path = PUBLISHED / relative
            self.assertEqual(record["bytes"], path.stat().st_size)
            self.assertEqual(record["sha256"], self.digest(path))

        runs = json.loads((PUBLISHED / "openfoam-run-manifest.json").read_text(encoding="utf-8"))["runs"]
        self.assertEqual(len(runs), 8)
        self.assertEqual(
            {item["case_id"] for item in runs if item["case_id"].startswith("shroud-")},
            {
                "shroud-gap10-nonslip-coarse",
                "shroud-gap20-kepsilon-base7p5",
                "shroud-gap20-kepsilon-base5",
                "shroud-gap20-kepsilon-long-base7p5",
                "shroud-gap20-kepsilon-long-base5",
                "shroud-gap20-laminar-base7p5",
                "shroud-gap20-laminar-base5",
            },
        )
        for run in runs:
            fixed = run["input_evidence"]["fixed_files"]
            self.assertIn("case_metadata", fixed)
            self.assertIn("mesh_check_strict", fixed)
            for selection in run["input_evidence"]["numerical_selections"].values():
                if selection["selected"]:
                    source_record = selection["selected"]["source"]
                    self.assertIn(source_record["path"], records)


if __name__ == "__main__":
    unittest.main()
