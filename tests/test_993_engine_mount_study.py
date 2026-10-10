"""Independent checks of the mount study's acceptance and artifact boundaries."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/993-engine-mount-system-f0"
spec = importlib.util.spec_from_file_location("mount_study", FAMILY / "source/build_study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def tetrahedron(path):
    vertices = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)]
    faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
    rows = [struct.pack("<12fH", 0, 0, 0, *(v for i in f for v in vertices[i]), 0) for f in faces]
    path.write_bytes(b"test".ljust(80, b" ") + struct.pack("<I", 4) + b"".join(rows))


class EngineMountStudyTests(unittest.TestCase):
    def test_oem_counts_are_preserved_and_acceptance_stays_blocked(self):
        contract = json.loads((FAMILY / "interface-contract.json").read_text())
        self.assertEqual(study.preflight()["decision"], "blocked")
        self.assertIsNone(contract["interfaces"]["bracket_to_engine"]["attachment_sites"])
        for name, count in study.REQUIRED.items():
            changed = copy.deepcopy(contract)
            changed["interfaces"][name]["attachment_sites"] = 0 if count else 4
            with self.assertRaisesRegex(ValueError, "cannot be weakened"):
                study.preflight(changed)
        changed = copy.deepcopy(contract)
        changed["manufacturing_authorized"] = True
        with self.assertRaisesRegex(ValueError, "cannot authorize"):
            study.preflight(changed)
        for interface in contract["interfaces"].values():
            interface["reference"] = "measured"
            interface["measurement_evidence"] = "model_says_verified"
        self.assertIs(study.preflight(contract)["manufacturing_authorized"], False)

    def test_no_functional_or_overwriting_export_before_native_execution(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(study.subprocess, "run") as native:
            output = Path(directory) / "output"
            with self.assertRaisesRegex(ValueError, "--shape-study"):
                study.generate(output, Path("absent.dll"))
            self.assertFalse(output.exists())
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "must be new"):
                study.generate(output, Path("absent.dll"), shape_study=True)
            native.assert_not_called()

    def test_binary_mesh_inspection_rejects_open_or_nonfinite_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tetra.stl"
            tetrahedron(path)
            metrics = study.mesh_check(path)
            self.assertAlmostEqual(metrics["volume_mm3"], 1/6)
            self.assertEqual(metrics["connected_components"], 1)
            original = path.read_bytes()
            path.write_bytes(original[:80] + struct.pack("<I", 3) + original[84:-50])
            with self.assertRaisesRegex(ValueError, "closure"):
                study.mesh_check(path)
            data = bytearray(original)
            struct.pack_into("<f", data, 96, float("nan"))
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "Nonfinite"):
                study.mesh_check(path)

    def test_cleanup_only_removes_exact_zero_area_faces(self):
        with tempfile.TemporaryDirectory() as directory:
            path, cleaned = Path(directory) / "raw.stl", Path(directory) / "clean.stl"
            tetrahedron(path)
            original = path.read_bytes()
            zero = struct.pack("<12fH", *([0] * 13))
            path.write_bytes(original[:80] + struct.pack("<I", 5) + original[84:] + zero)
            self.assertEqual(study.remove_degenerate_faces(path, cleaned), 1)
            self.assertEqual(cleaned.read_bytes(), original)
            self.assertTrue(study.mesh_check(cleaned)["closed_edges"])

    def test_committed_artifacts_and_pinned_inputs_pass_independent_inspection(self):
        report = study.check(FAMILY / "derived")
        self.assertEqual(len(report["meshes"]), 4)
        self.assertIs(report["interface_audit"]["is_fitment_validated"], False)
        self.assertEqual(report["pose_status"], "exploded_illustration_only_not_measured_assembly")

    def test_preview_follows_retained_geometry_and_renderer(self):
        media = FAMILY / "media"
        record = json.loads((media / "engine-mount-study.json").read_text())
        self.assertIs(record["triangle_subsampling"], False)
        self.assertEqual(record["status"], "illustration_only")
        self.assertEqual(len(record["inputs"]), 5)
        for name, digest in record["inputs"].items():
            self.assertEqual(study.sha256(FAMILY / name), digest)
        self.assertEqual(study.sha256(media / "engine-mount-study.png"), record["image_sha256"])

    def test_missing_inspection_and_forged_material_are_rejected(self):
        report = json.loads((FAMILY / "derived/study-report.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            changed = copy.deepcopy(report)
            changed["meshes"] = {}
            (output / "study-report.json").write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "Missing independent mesh"):
                study.check(output)
            changed = copy.deepcopy(report)
            changed["selected_material"] = "qualified titanium"
            (output / "study-report.json").write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "cannot qualify"):
                study.check(output)

    def test_picogk_catalogue_master_is_supported_by_schema_and_validator(self):
        from scripts.validate_catalog import validate_record
        for name in ("993-eng-bracket-0001", "993-eng-mounting-0001"):
            record = json.loads((ROOT / "catalog/parts" / (name + ".json")).read_text())
            self.assertEqual(validate_record(record), [])
            self.assertEqual(record["geometry"]["master_format"], "PicoGK")
            self.assertEqual(record["validation"]["status"], "concept")
        schema = json.loads((ROOT / "catalog/schemas/part.schema.json").read_text())
        self.assertIn("PicoGK", schema["properties"]["geometry"]["properties"]["master_format"]["enum"])
