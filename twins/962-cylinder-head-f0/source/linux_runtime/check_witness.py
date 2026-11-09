"""Independently measure the synthetic Linux witness STL exports with Trimesh."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def check(folder):
    checks = {}
    hashes = {}
    for name, x in (("metal_domain", 0), ("coolant_domain", 40), ("dry_domain", 80), ("lattice", None)):
        path = folder / (name + ".stl")
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        mesh = trimesh.load(path, force="mesh")
        volume = float(mesh.volume)
        item = {"watertight": bool(mesh.is_watertight), "volume_mm3": volume,
                "passed": bool(mesh.is_watertight and np.isfinite(volume) and volume > 0)}
        if x is not None:
            expected = np.array([[x - 5, -10, 0], [x + 5, 10, 30]])
            error = float(np.max(np.abs(mesh.bounds - expected)))
            relative = abs(volume - 6000) / 6000
            item.update(bounds_mm=mesh.bounds.tolist(), expected_bounds_mm=expected.tolist(),
                        max_bound_error_mm=error, relative_volume_error=relative)
            item["passed"] = bool(item["passed"] and error <= 0.5 and relative <= 0.1)
        checks[name] = item
    return {"scope": "independent_synthetic_STL_readback", "trimesh_version": trimesh.__version__,
            "bounds_tolerance_mm": 0.5, "relative_volume_tolerance": 0.1,
            "checks": checks, "mesh_sha256": hashes, "passed": all(c["passed"] for c in checks.values()),
            "physical_qualification": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    report = check(args.folder)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
