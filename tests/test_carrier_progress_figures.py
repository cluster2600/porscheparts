"""The diagnostic colouring must describe the exact retained faces."""
import hashlib
import importlib.util
from pathlib import Path
import unittest

try:
    import numpy as np
    path = Path(__file__).resolve().parents[1] / "scripts/render_carrier_progress.py"
    spec = importlib.util.spec_from_file_location("carrier_progress", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
except ImportError:
    np = None


@unittest.skipIf(np is None, "Carrier plotting runtime unavailable")
class ProgressFigureTests(unittest.TestCase):
    def test_partition_and_geometry_identity_bind_the_colour_mask(self):
        vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        faces = np.array([[0, 1, 2], [0, 1, 3]], dtype=np.int64)
        groups = [{"id":"a", "face_range":[0, 1]}, {"id":"b", "face_range":[1, 2]}]
        graph = dict(groups=2, input_geometry_sha256=hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest(),
                     components=[dict(group_ids=["a"], passed=True), dict(group_ids=["b"], passed=False)])
        np.testing.assert_array_equal(module.rejected_faces(vertices, faces, groups, graph), [False, True])
        with self.assertRaisesRegex(ValueError, "these triangles"):
            module.rejected_faces(vertices+1, faces, groups, graph)
        with self.assertRaisesRegex(ValueError, "partition the faces"):
            module.rejected_faces(vertices, faces, [groups[0], dict(id="b", face_range=[0, 2])], graph)
        graph["components"][1]["group_ids"] = ["a"]
        with self.assertRaisesRegex(ValueError, "partition the material"):
            module.rejected_faces(vertices, faces, groups, graph)
