"""Assembly completeness and exact-mesh gates on synthetic fixtures."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from _deps import require_modules

require_modules("numpy", "scipy", "trimesh")
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/bionic-turbo-f0/assembly/inspect_assembly.py"
SPEC = importlib.util.spec_from_file_location("bionic_assembly_inspector", SCRIPT)
INSPECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSPECT)
GENERATOR = ROOT / "twins/bionic-turbo-f0/assembly/source/bin/Release/net9.0/Assembly.dll"


class BionicAssemblyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.contract = self.root / "contract.json"
        components = [{"id": "test-housing", "label": "Test housing", "group": "compressor"},
                      {"id": "test-shaft", "label": "Test shaft", "group": "rotor"}]
        self.contract.write_text(json.dumps({"components": components, "voxel_mm": .5,
                                             "noninterference_pairs": [["test-shaft", "test-housing"]]}))
        self.manifest = {"schema_version": 1, "status": "concept_assembly_generated",
                         "units": "mm", "voxel_mm": .5, "files": [],
                         "selected_voxel_intersections": [{"a": "test-shaft", "b": "test-housing",
                                                            "voxel_intersection_mm3": 0, "passed": True}]}
        for item in components:
            path = self.root / (item["id"] + ".stl")
            trimesh.creation.box().export(path)
            self.manifest["files"].append(item | {"file": path.name, "triangles": 12,
                "sha256": INSPECT.BASE.sha256(path), "explode_offset_mm": [0, 0, 50]})

    def inspect(self):
        self.manifest["contract_sha256"] = INSPECT.BASE.sha256(self.contract)
        (self.root / "report.json").write_text(json.dumps(self.manifest))
        return INSPECT.inspect_outputs(self.root, self.contract)

    def test_complete_exact_components_pass_without_function_claims(self):
        report, meshes, _ = self.inspect()
        self.assertTrue(report["geometry_passed"])
        self.assertEqual(set(meshes), {"test-housing", "test-shaft"})
        self.assertTrue(all(value["all_input_triangles_retained"] for value in report["meshes"].values()))
        self.assertFalse(report["assembly_clearances_checked"])
        self.assertFalse(report["engineering_validated"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertTrue(report["generator_selected_voxel_screen_passed"])
        self.assertFalse(report["native_intersection_screen_recomputed"])
        self.assertFalse(report["minimum_clearance_measured"])

    def test_tampered_native_screen_and_failure_marker_are_rejected(self):
        good = self.manifest["selected_voxel_intersections"][0]
        cases = [([], "native_intersection_pair_set_mismatch"),
                 ([good, good], "native_intersection_pair_set_mismatch"),
                 ([good | {"b": "uncontracted-part"}], "native_intersection_pair_set_mismatch")]
        for changes in ({"passed": False}, {"passed": 1}, {"voxel_intersection_mm3": 1},
                        {"voxel_intersection_mm3": np.nan}, {"voxel_intersection_mm3": False}):
            cases.append(([good | changes], "native_intersection_screen_failed"))
        for screen, error in cases:
            with self.subTest(screen=screen):
                self.manifest["selected_voxel_intersections"] = screen
                report, meshes, _ = self.inspect()
                self.assertFalse(report["geometry_passed"])
                self.assertEqual(meshes, {})
                self.assertIn("manifest: " + error, report["errors"])
        self.manifest["selected_voxel_intersections"] = [good]
        (self.root / "FAILED.json").write_text("{}")
        report, _, _ = self.inspect()
        self.assertIn("manifest: generation_failed_marker_present", report["errors"])

    def test_partial_and_duplicate_manifest_fail_against_independent_bom(self):
        complete = self.manifest["files"][:]
        for files in (complete[:1], [complete[0], complete[0]]):
            with self.subTest(files=files):
                self.manifest["files"] = files
                report, meshes, _ = self.inspect()
                self.assertFalse(report["geometry_passed"])
                self.assertEqual(meshes, {})
                self.assertIn("manifest: component_set_mismatch", report["errors"])

    def test_bad_facet_header_hash_and_open_mesh_fail(self):
        path = self.root / "test-housing.stl"
        original = path.read_bytes()
        path.write_bytes(original[:-1])
        report, _, _ = self.inspect()
        self.assertIn("test-housing: generation_sha256_mismatch", report["errors"])
        self.manifest["files"][0]["sha256"] = INSPECT.BASE.sha256(path)
        report, _, _ = self.inspect()
        self.assertIn("test-housing: binary_stl_facet_count_mismatch", report["errors"])
        box = trimesh.creation.box()
        trimesh.Trimesh(vertices=box.vertices, faces=box.faces[:-1], process=False).export(path)
        self.manifest["files"][0].update(sha256=INSPECT.BASE.sha256(path), triangles=11)
        report, _, _ = self.inspect()
        self.assertFalse(report["geometry_passed"])
        self.assertIn("boundary_edges", report["meshes"]["test-housing"]["failures"])

    def test_unsafe_filenames_and_nonfinite_display_offsets_fail(self):
        self.manifest["files"][0]["file"] = "../test-housing.stl"
        report, _, _ = self.inspect()
        self.assertIn("manifest: component_filename_mismatch", report["errors"])
        self.manifest["files"][0]["file"] = "test-housing.stl"
        self.manifest["files"][0]["explode_offset_mm"] = [0, np.inf, 0]
        report, _, _ = self.inspect()
        self.assertIn("manifest: invalid_explode_offset", report["errors"])

    def test_independent_voxel_and_retained_housing_hash_are_enforced(self):
        self.manifest["voxel_mm"] = .75
        report, _, _ = self.inspect()
        self.assertIn("manifest: invalid_voxel_mm", report["errors"])
        self.manifest["voxel_mm"] = .5
        contract = json.loads(self.contract.read_text())
        contract["components"][0]["id"] = "compressor-housing"
        contract["noninterference_pairs"][0][1] = "compressor-housing"
        self.manifest["selected_voxel_intersections"][0]["b"] = "compressor-housing"
        contract["compressor_housing_sha256"] = "0" * 64
        self.contract.write_text(json.dumps(contract))
        (self.root / "test-housing.stl").rename(self.root / "compressor-housing.stl")
        self.manifest["files"][0].update(id="compressor-housing", file="compressor-housing.stl")
        report, _, _ = self.inspect()
        self.assertIn("compressor-housing: independent_compressor_housing_sha256_mismatch", report["errors"])

    def test_cli_imports_and_refuses_existing_output(self):
        help_result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root), str(self.root)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "inspection.json").exists())

    @unittest.skipUnless(os.environ.get("BIONIC_DOTNET") and GENERATOR.is_file(),
                         "built assembly and BIONIC_DOTNET required; no native kernel execution")
    def test_generator_rejects_bad_input_and_preserves_existing_output(self):
        command = [os.environ["BIONIC_DOTNET"], str(GENERATOR)]
        source = self.root / "input"
        source.mkdir()
        housing = source / "housing.stl"
        housing.write_bytes(b"sentinel: validation must stop before native mesh loading")
        data = json.loads(INSPECT.CONTRACT.read_text())
        data["compressor_housing_sha256"] = INSPECT.BASE.sha256(housing)
        output = self.root / "new-output"
        for changes, message in (({"units": "inch"}, "millimetre"),
                                 ({"voxel_mm": .75}, "0.5 mm"),
                                 ({"compressor_housing_sha256": "0" * 64}, "independent contract")):
            with self.subTest(changes=changes):
                self.contract.write_text(json.dumps(data | changes))
                result = subprocess.run(command + [str(self.contract), str(source), str(output)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)
                self.assertFalse(output.exists())
        self.contract.write_text(json.dumps(data))
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_text("preserve")
        result = subprocess.run(command + [str(self.contract), str(source), str(output)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(list(output.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
