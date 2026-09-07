"""Offline synthetic Python geometry witness, never a cylinder-head test."""

import importlib.metadata
import json

import numpy as np
import scipy.ndimage
import trimesh
import pyvista
import vtk


def main():
    box = trimesh.creation.box(extents=[2, 4, 6])
    assert box.is_watertight and box.is_winding_consistent
    np.testing.assert_allclose(box.volume, 48, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(
        box.contains(np.array([[0, 0, 0], [4, 0, 0]], dtype=float)),
        [True, False],
    )
    _, distance, _ = trimesh.proximity.closest_point(
        box, np.array([[0, 0, 4], [3, 0, 0]], dtype=float)
    )
    np.testing.assert_allclose(distance, [1, 2], rtol=0, atol=1e-12)
    locations, _, _ = box.ray.intersects_location(
        ray_origins=np.array([[0, 0, 0]], dtype=float),
        ray_directions=np.array([[1, 0, 0]], dtype=float),
        multiple_hits=False,
    )
    np.testing.assert_allclose(locations, [[1, 0, 0]], rtol=0, atol=1e-12)
    _, components = scipy.ndimage.label(np.array([1, 0, 1], dtype=bool))
    assert components == 2
    assert pyvista.PolyData(box.vertices).n_points == 8
    assert vtk.vtkVersion.GetVTKVersion()
    packages = ["numpy", "scipy", "trimesh", "rtree", "networkx",
                "matplotlib", "pyvista", "vtk"]
    print(json.dumps({
        "status": "PYTHON_GEOMETRY_SYNTHETIC_SMOKE_PASS",
        "packages": {name: importlib.metadata.version(name) for name in packages},
        "witness": "closed_box_volume_inside_outside_distance_ray_and_components",
        "GPU_acceleration_tested": False,
        "head_geometry_tested": False,
        "thermal_or_structural_validation": False,
        "manufacturing_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
