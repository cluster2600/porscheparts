import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/audit_root0p7_openfoam_sets.py"
if np is not None:
    spec = importlib.util.spec_from_file_location("audit_root0p7_openfoam_sets", SOURCE)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)


@unittest.skipUnless(np is not None, "Requires NumPy")
class OpenFOAMSetLocalizationTests(unittest.TestCase):
    def test_set_header_and_indices_are_validated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "set"
            path.write_text("FoamFile\n2\n(\n0\n1\n)\n")
            self.assertEqual(audit.read_set(path, 2, 3).tolist(), [0, 1])
            path.write_text("FoamFile\n2\n(\n0\n0\n)\n")
            with self.assertRaises(ValueError):
                audit.read_set(path, 2, 3)
            path.write_text("FoamFile\n2\n(\n0\n3\n)\n")
            with self.assertRaises(ValueError):
                audit.read_set(path, 2, 3)

    def test_boundary_labels_ignore_face_orientation_and_reject_absent_face(self):
        boundary = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
        markers = np.array([4, 3], dtype=np.int64)
        faces = np.array([[2, 1, 0], [0, 1, 3]], dtype=np.int64)
        self.assertEqual(audit.boundary_labels(faces, boundary, markers).tolist(), [4, 0])

    def test_unpinned_volume_is_refused_before_outputs_are_written(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as folder:
            path = Path(folder)
            (path / "wrong.npz").write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "Audited O5 volume changed"):
                audit.main(path / "wrong.npz", path, path / "missing.json", path / "missing.log", path / "new.json")
            self.assertFalse((path / "new.json").exists())


if __name__ == "__main__":
    unittest.main()
