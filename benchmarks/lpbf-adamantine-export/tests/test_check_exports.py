"""Small parser check; these synthetic fields are not native regression evidence."""
from pathlib import Path
from tempfile import TemporaryDirectory

import meshio
import numpy as np

from check_exports import assess, invariant, tensors, self_check

self_check()
points = np.array([[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.],
                   [0., 0., 1.], [1., 0., 1.], [1., 1., 1.], [0., 1., 1.]])
with TemporaryDirectory() as temporary:
    root = Path(temporary)
    for mode in ["mechanical", "coupled"]:
        (root / mode).mkdir()
        for i, samples in enumerate(tensors()):
            expected = np.mean([invariant(sample) for sample in samples])
            mesh = meshio.Mesh(points, [("hexahedron", [[0, 1, 2, 3, 4, 5, 6, 7]])],
                               cell_data={"stress": [np.array([expected])]})
            mesh.write(root / mode / f"witness.{i}.0.vtu")
    assert assess(root)["status"] == "passed"
    path = root / "mechanical/witness.1.0.vtu"
    original = path.read_bytes()
    for value in [0., float("nan")]:
        mesh = meshio.read(path)
        mesh.cell_data["stress"] = [np.array([value])]
        mesh.write(path)
        assert assess(root)["status"] == "failed"
        path.write_bytes(original)
    mesh = meshio.read(path)
    del mesh.cell_data["stress"]
    mesh.write(path)
    assert assess(root)["status"] == "failed"
    path.unlink()
    assert assess(root)["status"] == "failed"
print("checker self-check passed: valid fields plus four rejection fixtures")
