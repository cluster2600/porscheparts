"""Pure arithmetic/refusal tests; no OpenUSD or native asset execution."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "author_usd_face_normals", ROOT / "twins/962-cylinder-head-f0/source/author_usd_face_normals.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FaceNormalTests(unittest.TestCase):
    def geometry(self):
        return (np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32),
                np.array([3, 3], dtype=np.int32),
                np.array([0, 1, 2, 0, 2, 1], dtype=np.int32))

    def test_known_oblique_and_reversed_winding_normals(self):
        geometry = self.geometry()
        normals = module.face_normals(*geometry)
        v = np.float32(1 / math.sqrt(3))
        expected = np.array([[v, v, v], [-v, -v, -v]], dtype=np.float32)
        self.assertEqual(normals.tobytes(), expected.tobytes())
        result = module.assess_normals(*geometry, normals)
        self.assertEqual(result["faces_checked"], 2)
        self.assertLessEqual(result["max_unit_length_error"], module.VECTOR_BOUND)
        self.assertLessEqual(result["max_angle_radians"], module.ANGLE_BOUND_RAD)

    def test_nearly_distinct_points_indices_and_multiplicity_remain_exact(self):
        p = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 1],
                      [0, 1, np.nextafter(np.float32(1), np.float32(2))]], dtype=np.float32)
        c = np.array([3, 3, 3], dtype=np.int32)
        i = np.array([0, 1, 2, 0, 1, 3, 0, 1, 2], dtype=np.int32)
        before = [a.tobytes() for a in [p, c, i]]
        normals = module.face_normals(p, c, i)
        module.assess_normals(p, c, i, normals)
        self.assertEqual([a.tobytes() for a in [p, c, i]], before)
        self.assertEqual(len(normals), 3)
        self.assertEqual(normals[0].tobytes(), normals[2].tobytes())

    def test_axis_faces_keep_signed_zero_points_and_opposite_orientation(self):
        p = np.array([[0., -0., 0.], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        c = np.array([3, 3], dtype=np.int32)
        i = np.array([0, 1, 2, 0, 2, 1], dtype=np.int32)
        before = p.tobytes()
        normals = module.face_normals(p, c, i)
        self.assertTrue(np.array_equal(normals, np.array([[0, 0, 1], [0, 0, -1]],
                                                        dtype=np.float32)))
        module.assess_normals(p, c, i, normals)
        self.assertEqual(p.tobytes(), before)

    def test_nontriangular_invalid_indices_or_nonfinite_points_are_refused(self):
        p, c, i = self.geometry()
        for counts, indices in [(np.array([6]), i), (c, i[:-1]),
                                (c, i.astype(float)), (c, np.array([-1, 1, 2, 0, 1, 2])),
                                (c, np.array([0, 1, 99, 0, 1, 2]))]:
            with self.subTest(counts=counts, indices=indices):
                with self.assertRaises(ValueError):
                    module.face_normals(p, counts, indices)
        for bad in [float("inf"), float("nan")]:
            changed = p.copy(); changed[0, 0] = bad
            with self.assertRaisesRegex(ValueError, "Finite binary32"):
                module.face_normals(changed, c, i)

    def test_degenerate_faces_are_refused_without_repair(self):
        p, c, i = self.geometry(); p[2] = p[1]
        with self.assertRaisesRegex(ValueError, "degenerate"):
            module.face_normals(p, c, i)
        with self.assertRaisesRegex(ValueError, "degenerate"):
            module.assess_normals(p, c, i, np.ones((2, 3), dtype=np.float32))

    def test_wrong_normals_count_dtype_direction_scale_and_nan_are_refused(self):
        geometry = self.geometry(); normals = module.face_normals(*geometry)
        bad_nan = normals.copy(); bad_nan[0, 0] = np.nan
        for bad in [normals[:1], normals.astype(np.float64), -normals,
                    normals * np.float32(2), bad_nan]:
            with self.subTest(shape=bad.shape, dtype=bad.dtype):
                with self.assertRaises(ValueError):
                    module.assess_normals(*geometry, bad)

    def test_rounding_bounds_are_fixed_from_binary32_not_observed_fields(self):
        self.assertEqual(module.COMPONENT_BOUND, float(np.finfo(np.float32).eps / 2))
        self.assertEqual(module.VECTOR_BOUND, math.sqrt(3) * 2**-24)
        self.assertEqual(module.ANGLE_BOUND_RAD,
                         math.asin(module.VECTOR_BOUND / (1 - module.VECTOR_BOUND)))

    def test_existing_output_and_symlink_refuse_before_runtime_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "prior.usdc"; target.write_bytes(b"prior evidence")
            link = Path(temporary) / "link.usdc"; link.symlink_to(target)
            for path in [target, link]:
                with self.assertRaises(FileExistsError):
                    module.author(Path(temporary) / "missing.usdc", path, "missing")
            self.assertEqual(target.read_bytes(), b"prior evidence")

    def test_source_drift_refuses_before_runtime_import_or_output_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.usdc"; source.write_bytes(b"changed")
            output = Path(temporary) / "new.usdc"
            with self.assertRaisesRegex(ValueError, "Source hash drift before output creation"):
                module.author(source, output, "0" * 64)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
