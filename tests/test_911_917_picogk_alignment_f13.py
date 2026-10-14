import copy
from contextlib import ExitStack, contextmanager, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "twins/vehicle-911-917/source"
sys.path.insert(0, str(SOURCE))
import prepare_picogk_alignment_f13 as alignment
from annotate_picogk_mechanical_f13 import validate_report


class ScanAlignmentTests(unittest.TestCase):
    @contextmanager
    def alignment_fixture(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            scan = alignment.scan
            paths = {name: root / path.relative_to(scan.ROOT) for name, path in (
                ("OBJ", scan.OBJ), ("STL", scan.STL), ("REPORT", scan.REPORT),
                ("PACKAGING", scan.PACKAGING), ("INTERFACES", scan.INTERFACES), ("OUTPUT", scan.OUTPUT))}
            for path in paths.values():
                path.parent.mkdir(parents=True, exist_ok=True)
            paths["OBJ"].write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
            registry = [{"bank": bank, "geometric_index": index + 1,
                         "center_scan_coordinates_obj_units": [index, sign * 2, 0]}
                        for bank, sign in (("positive", 1), ("negative", -1)) for index in range(6)]
            paths["INTERFACES"].write_text(json.dumps({"interface_registry": registry}))
            paths["PACKAGING"].write_text(json.dumps({
                "scan_screening": {"screening_frame": {
                    "basis_columns_in_scan_coordinates": np.eye(3).tolist(),
                    "oriented_bounds_obj_units": {"minimum": [-2.5, -2, 0]},
                    "screening_size_mm": [6, 4, 1], "scale_mm_per_obj_unit": 1}},
                "layout_screening": {"selected_layout_id": "fixture", "trials": [{
                    "layout_id": "fixture", "engine_scan_bounds_x_mm": [1472, 1478],
                    "engine_mating_plane_x_mm": 2622}]}}))
            config = root / "twins/vehicle-911-917/picogk-mechanical-f13.json"
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(json.dumps({"shaft_reference_z_mm": 300}))
            for name in ("prepare_picogk_scan_f10.py", "prepare_picogk_alignment_f13.py"):
                destination = root / "twins/vehicle-911-917/source" / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SOURCE / name, destination)
            stack.enter_context(patch.multiple(scan, ROOT=root, **paths))
            output = root / "work/911-917-picogk-f13"
            stack.enter_context(patch.multiple(alignment, ROOT=root, STL=paths["STL"], OUTPUT=output))
            stack.enter_context(redirect_stdout(io.StringIO()))
            scan.build()
            alignment.build()
            yield root, output / "scan-alignment-f13.json"

    def test_receipt_rejects_every_changed_alignment_input(self):
        with self.alignment_fixture() as (root, path):
            report = json.loads(path.read_text())
            alignment.validate_alignment(report)
            native_report = {"phase": "F13", "release_gates": {"physical_fit_verified": False},
                             "scope": {"turbo_count": 2, "rear_halfshaft_count": 2}, "alignment": report}
            validate_report(native_report)
            for relative in report["inputs_sha256"]:
                with self.subTest(input=relative):
                    source = root / relative
                    original = source.read_bytes()
                    source.write_bytes(original + b"\n")
                    with self.assertRaises((ValueError, SystemExit)):
                        alignment.validate_alignment(report)
                    with self.assertRaises((ValueError, SystemExit)):
                        validate_report(native_report)
                    source.write_bytes(original)
            config = root / "twins/vehicle-911-917/picogk-mechanical-f13.json"
            config.write_text(json.dumps({"shaft_reference_z_mm": 305}))
            alignment.build()
            rebuilt = json.loads(path.read_text())
            alignment.validate_alignment(rebuilt)
            self.assertAlmostEqual(rebuilt["matrix4x4_row_vector"][3][2] - report["matrix4x4_row_vector"][3][2], 5)

    def test_receipt_rejects_unbound_or_nonrigid_alignment(self):
        with self.alignment_fixture() as (_, path):
            report = json.loads(path.read_text())
            changed = copy.deepcopy(report)
            del changed["inputs_sha256"]
            with self.assertRaises(ValueError):
                alignment.validate_alignment(changed)
            for matrix in ([[1, 0]], np.diag([2, 1, 1, 1]).tolist(),
                           np.diag([-1, 1, 1, 1]).tolist(), np.full((4, 4), np.nan).tolist()):
                with self.subTest(matrix=matrix):
                    changed = copy.deepcopy(report)
                    changed["matrix4x4_row_vector"] = matrix
                    with self.assertRaises(ValueError):
                        alignment.validate_alignment(changed)

    @unittest.skipUnless(shutil.which("dotnet"), "local .NET SDK absent")
    def test_native_reader_rejects_stale_receipts_and_nonrigid_matrices(self):
        with self.alignment_fixture() as (root, receipt):
            project = root / "native-test"
            project.mkdir()
            shutil.copyfile(SOURCE.parent / "picogk/ScanAlignment.cs", project / "ScanAlignment.cs")
            (project / "Native.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
                '<OutputType>Exe</OutputType><TargetFramework>net9.0</TargetFramework>'
                '<ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>')
            (project / "Program.cs").write_text('using System.Text.Json; namespace Vehicle911917; '
                'internal static partial class Program { static int Main(string[] args) { try { '
                'using var report = JsonDocument.Parse(File.ReadAllText(args[0])); '
                'ValidatedAlignment(report.RootElement, args[1], args[2]); return 0; '
                '} catch (Exception error) { Console.Error.WriteLine(error.Message); return 1; } } }')
            build = subprocess.run(["dotnet", "build", str(project / "Native.csproj"), "--nologo", "-v", "quiet"],
                                   capture_output=True, text=True, timeout=120)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            command = ["dotnet", str(project / "bin/Debug/net9.0/Native.dll"), str(receipt), str(root), str(alignment.STL)]
            def run():
                return subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(run().returncode, 0)
            report = json.loads(receipt.read_text())
            for relative in report["inputs_sha256"]:
                with self.subTest(input=relative):
                    source = root / relative
                    original = source.read_bytes()
                    source.write_bytes(original + b"\n")
                    result = run()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("F13 alignment input changed", result.stderr)
                    source.write_bytes(original)
            for matrix in ([[1, 0]], np.diag([2, 1, 1, 1]).tolist(), np.diag([-1, 1, 1, 1]).tolist()):
                changed = copy.deepcopy(report)
                changed["matrix4x4_row_vector"] = matrix
                receipt.write_text(json.dumps(changed))
                self.assertNotEqual(run().returncode, 0)

    def test_staggered_banks_do_not_rotate_engine(self):
        angle = np.deg2rad(31)
        rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                             [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
        registry = []
        for name, sign in (("positive", 1), ("negative", -1)):
            for index, x in enumerate((0, 118, 236, 409, 527, 645), 1):
                p = np.array([x + sign * 35, sign * 250, 0]) @ rotation.T + [14, -25, 80]
                registry.append({"bank": name, "geometric_index": index,
                                 "center_scan_coordinates_obj_units": p.tolist()})
        frame = alignment.bank_frame(registry)
        np.testing.assert_allclose(frame[0], rotation[:, 0], atol=1e-12)
        np.testing.assert_allclose(frame @ frame.T, np.eye(3), atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(frame), 1.0)
        points = np.array([v["center_scan_coordinates_obj_units"] for v in registry[:6]]) @ frame.T
        np.testing.assert_allclose(points[:, 1], points[0, 1], atol=1e-10)

    def test_missing_bank_is_rejected(self):
        with self.assertRaises(ValueError):
            alignment.bank_frame([])

    def test_annotator_refuses_physical_release_claim(self):
        report = {"phase": "F13", "release_gates": {"physical_fit_verified": True}}
        with self.assertRaises(ValueError):
            validate_report(report)

    def test_local_geometry_and_interfaces_when_available(self):
        output = SOURCE.parents[2] / "work/911-917-picogk-f13"
        path = output / "picogk-mechanical-report-f13.json"
        if not path.exists():
            self.skipTest("résultats privés PicoGK absents")
        report = json.loads(path.read_text())
        validate_report(report)
        np.testing.assert_allclose(report["alignment"]["fitted_longitudinal_axis_in_vehicle"], [1, 0, 0], atol=1e-7)
        refs = report["kinematic_references"]
        self.assertEqual(refs["differential_x_mm"], refs["rear_axle_x_mm"])
        np.testing.assert_allclose(refs["rear_hub_centres_mm"], refs["halfshaft_outer_joint_centres_mm"])
        for key in ("engine_scan", "transaxle_schematic", "turbo_left", "turbo_right", "rear_halfshafts_and_CV_joints"):
            layer = report["layers"][key]
            self.assertGreater(layer["properties"]["volume_mm3"], 0)
            self.assertTrue((output / layer["vdb"]).is_file())
        # L'interférence héritée ne doit pas disparaître silencieusement du diagnostic.
        self.assertTrue(report["checks"]["halfshafts_vs_structure"]["collision"])


if __name__ == "__main__":
    unittest.main()
