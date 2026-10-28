"""Export the private four-patch fluid PLC as an ASCII STL for cfMesh."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


SOURCE_SHA256 = "9fcd93a5c54ebfc98b8cd86d4550e3a416d3e62fb217e5ebfb67eb2f2a9f2085"
PATCHES = {1: "inlet", 2: "outlet", 3: "duct", 4: "rotor"}
EXPECTED_COUNTS = {1: 2304, 2: 2304, 3: 12394, 4: 878730}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: export_cfmesh_stl.py BOUNDARY_NPZ NEW_STL")
    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    if output.exists() or output.with_suffix(".json").exists():
        raise SystemExit("Output or receipt already exists")
    if sha256(source) != SOURCE_SHA256:
        raise SystemExit("Unexpected PLC hash")
    with np.load(source) as plc:
        vertices = plc["vertices"]
        triangles = plc["triangles"]
        markers = plc["markers"]
    if (vertices.shape, triangles.shape, markers.shape) != ((447868, 3), (895732, 3), (895732,)):
        raise SystemExit("Unexpected PLC shape")
    if not np.isfinite(vertices).all() or triangles.min() < 0 or triangles.max() >= len(vertices):
        raise SystemExit("Invalid PLC coordinates or indices")
    counts = {patch: int(np.count_nonzero(markers == patch)) for patch in PATCHES}
    if counts != EXPECTED_COUNTS or not np.isin(markers, list(PATCHES)).all():
        raise SystemExit("Unexpected PLC patches")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="ascii", buffering=1024 * 1024) as dest:
        for patch, name in PATCHES.items():
            dest.write(f"solid {name}\n")
            for face in triangles[markers == patch]:
                a, b, c = vertices[face]
                normal = np.cross(b - a, c - a)
                magnitude = np.linalg.norm(normal)
                if magnitude == 0:
                    raise SystemExit("Zero-area PLC triangle")
                normal /= magnitude
                dest.write("facet normal " + " ".join(format(value, ".17g") for value in normal) + "\n outer loop\n")
                for vertex in (a, b, c):
                    dest.write("vertex " + " ".join(format(value, ".17g") for value in vertex) + "\n")
                dest.write("endloop\nendfacet\n")
            dest.write(f"endsolid {name}\n")
    receipt = {
        "source_sha256": SOURCE_SHA256,
        "output_sha256": sha256(output),
        "output_bytes": output.stat().st_size,
        "patch_triangle_counts": {PATCHES[key]: value for key, value in counts.items()},
        "coordinate_unit": "m, conditional scale",
        "status": "exploratory_geometry_not_CFD_admitted",
    }
    output.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
