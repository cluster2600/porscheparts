import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "vehicle-911-917"
PREPARE = TWIN / "source" / "prepare_picogk_scan_f10.py"
PROJECT = TWIN / "picogk" / "Vehicle911917Packaging.csproj"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_picogk_f10", PREPARE)
    if spec is None or spec.loader is None:
        raise RuntimeError("module F10 impossible à charger")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Vehicle911917PicoGKPackagingF10Tests(unittest.TestCase):
    def test_check_rejects_changed_transform_inputs(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {name: root / name for name in ("OBJ", "STL", "REPORT", "PACKAGING", "INTERFACES")}
            for name in ("OBJ", "STL", "PACKAGING", "INTERFACES"):
                paths[name].write_text(name)
            report = {
                "source_obj_sha256": module.sha256(paths["OBJ"]),
                "output_stl_sha256": module.sha256(paths["STL"]),
                "transform_inputs_sha256": {name: module.sha256(paths[name]) for name in ("PACKAGING", "INTERFACES")},
                "transform": {"scale_verified": False, "orientation_verified": False},
            }
            paths["REPORT"].write_text(json.dumps(report))
            with patch.multiple(module, **paths):
                module.check()
                for name in ("PACKAGING", "INTERFACES"):
                    with self.subTest(input=name):
                        paths[name].write_text(name + " changed")
                        with self.assertRaises(SystemExit):
                            module.check()
                        paths[name].write_text(name)
                del report["transform_inputs_sha256"]
                paths["REPORT"].write_text(json.dumps(report))
                with self.assertRaises(SystemExit):
                    module.check()

    def test_obj_adapter_writes_binary_stl_without_new_dependency(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixture.obj"
            output = Path(directory) / "fixture.stl"
            source.write_text(
                "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n",
                encoding="utf-8",
            )
            vertices, triangles = module.convert_obj_to_binary_stl(
                source, output, lambda x, y, z: (x + 10, y + 20, z + 30)
            )
            self.assertEqual((vertices, triangles), (4, 2))
            self.assertEqual(output.stat().st_size, 84 + 2 * 50)
            self.assertEqual(struct.unpack("<I", output.read_bytes()[80:84])[0], 2)

    def test_picogk_contract_is_pinned_and_fail_closed(self) -> None:
        self.assertIn('PackageReference Include="PicoGK" Version="2.3.0"', PROJECT.read_text())
        report_path = ROOT / "work" / "911-917-picogk-f10" / "picogk-packaging-report-f10.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["kernel"]["package_version"], "2.3.0")
            self.assertFalse(report["transaxle"]["voxel_model_created"])
            self.assertFalse(report["release_gates"]["physical_fit_verified"])
            self.assertFalse(report["release_gates"]["manufacturing_authorized"])


if __name__ == "__main__":
    unittest.main()
