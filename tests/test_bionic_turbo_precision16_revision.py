"""Check the additive precision revision without executing a mesher or solver."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CFD = ROOT / "twins/bionic-turbo-f1/cfd"


def load(name):
    spec = importlib.util.spec_from_file_location(name, CFD / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrecisionRevision(unittest.TestCase):
    def test_frozen_source_is_unchanged(self):
        self.assertEqual(
            hashlib.sha256((CFD / "prepare_case.py").read_bytes()).hexdigest(),
            "f97461307b2d6a5a80f5a2cb3044b6d9bc6db09e930b2b39c7c5b340fbe371a8",
        )

    def test_only_field_write_precision_changes_for_all_mesh_levels(self):
        old, new = load("prepare_case"), load("prepare_case_v2")
        info = {"bounds_m": [[-.04, -.04, -.01], [.04, .04, .05]]}
        for level in old.LEVELS:
            for sign in (-1, 1):
                with self.subTest(level=level, sign=sign):
                    before = old.case_files(info, level, 100000., sign, 1.2, 800)
                    after = new.case_files(info, level, 100000., sign, 1.2, 800)
                    self.assertEqual(before.keys(), after.keys())
                    for path in before:
                        expected = before[path]
                        if path == "system/controlDict":
                            self.assertEqual(expected.count("writePrecision 12;"), 1)
                            expected = expected.replace("writePrecision 12;", "writePrecision 16;")
                        self.assertEqual(after[path], expected, path)

    def test_manifest_binds_new_source_and_generated_files(self):
        new = load("prepare_case_v2")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            surface = root / "synthetic-input.stl"
            surface.write_bytes(b"synthetic test payload, not an admitted surface")
            info = {"bounds_m": [[-.04, -.04, -.01], [.04, .04, .05]],
                    "sha256": new.sha(surface)}
            # Surface admission is separate; this exercises the publication path only.
            with patch.object(new, "surface_info", return_value=info):
                manifest = new.prepare(surface, root / "case", "coarse", 100000., 1, 1.2, 800)
            self.assertEqual(manifest["source_sha256"], new.sha(CFD / "prepare_case_v2.py"))
            for path, digest in manifest["file_sha256"].items():
                self.assertEqual(digest, new.sha(root / "case" / path))
            self.assertFalse(manifest["engineering_validated"])
            self.assertFalse(manifest["manufacturing_authorized"])
            self.assertIn("writePrecision 16;", (root / "case/system/controlDict").read_text())


if __name__ == "__main__":
    unittest.main()
