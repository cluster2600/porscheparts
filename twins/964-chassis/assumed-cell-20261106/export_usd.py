#!/usr/bin/env python3
"""Export the exact rectangular plate union as a private standalone study USD.

Compressed Cartesian cells produce the outer and cavity boundary without mesh
repair, voxel offsets or tessellation of the earlier rejected vehicle shell.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def boundary(boxes):
    cuts = [sorted({b[k][a] for b in boxes for k in ("min_mm", "max_mm")}) for a in range(3)]
    occupied = set()
    for i in range(len(cuts[0]) - 1):
        for j in range(len(cuts[1]) - 1):
            for k in range(len(cuts[2]) - 1):
                idx = (i, j, k)
                point = [(cuts[a][idx[a]] + cuts[a][idx[a] + 1]) / 2 for a in range(3)]
                if any(all(b["min_mm"][a] < point[a] < b["max_mm"][a] for a in range(3)) for b in boxes):
                    occupied.add(idx)
    vertices, faces, lookup = [], [], {}
    for cell in sorted(occupied):
        for n in range(3):
            u, v = (n + 1) % 3, (n + 2) % 3
            for sign in (-1, 1):
                other = list(cell); other[n] += sign
                if tuple(other) in occupied:
                    continue
                corners = []
                for du, dv in ((0, 0), (0, 1), (1, 1), (1, 0)):
                    grid = list(cell); grid[n] += int(sign > 0); grid[u] += du; grid[v] += dv
                    key = tuple(grid)
                    if key not in lookup:
                        lookup[key] = len(vertices)
                        vertices.append([cuts[a][grid[a]] for a in range(3)])
                    corners.append(lookup[key])
                faces.append(corners if sign < 0 else corners[::-1])
    edges = Counter(tuple(sorted((a, b))) for face in faces for a, b in zip(face, face[1:] + face[:1]))
    assert set(edges.values()) == {2}, "Union boundary is not closed/manifold by edge incidence"
    volume6 = 0.0
    for face in faces:
        a, b, c, d = [vertices[x] for x in face]
        for q, r in ((b, c), (c, d)):
            cross = [q[1]*r[2]-q[2]*r[1], q[2]*r[0]-q[0]*r[2], q[0]*r[1]-q[1]*r[0]]
            volume6 += sum(a[k] * cross[k] for k in range(3))
    assert volume6 > 0
    return vertices, faces, volume6 / 6


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("Output directory exists; use a fresh review revision.")
    raw = args.model.read_bytes(); model = json.loads(raw)
    assert model["status"] == "assumed" and model["donor_transform"] is None
    vertices, faces, volume = boundary(model["plate_boxes"])
    sha = hashlib.sha256(raw).hexdigest()
    points = ", ".join("(" + ", ".join(format(x, ".10g") for x in p) + ")" for p in vertices)
    indices = ", ".join(str(x) for f in faces for x in f)
    counts = ", ".join("4" for _ in faces)
    stage = f'''#usda 1.0
(
    defaultPrim = "AssumedCentralCell"
    metersPerUnit = 0.001
    upAxis = "Z"
    documentation = "Independent assumed central-tub study. No measured Porsche interfaces or physical validation."
)
def Xform "AssumedCentralCell" (
    customData = {{
        string studyStatus = "assumed_not_vehicle_validated"
        string canonicalModelSHA256 = "{sha}"
        bool physicalInterfacesAdmitted = false
        bool manufacturingAuthorized = false
    }}
)
{{
    def Mesh "PlateUnion"
    {{
        uniform token subdivisionScheme = "none"
        uniform token orientation = "rightHanded"
        bool doubleSided = false
        point3f[] points = [{points}]
        int[] faceVertexCounts = [{counts}]
        int[] faceVertexIndices = [{indices}]
        color3f[] primvars:displayColor = [(0.10, 0.14, 0.17)]
    }}
}}
'''
    args.output.mkdir(parents=True)
    target = args.output / "assumed-cell.usda"; target.write_text(stage)
    report = dict(classification="exact_assumed_plate_union_USD_export",
                  canonical_model_sha256=sha,
                  exporter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  stage_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                  vertices=len(vertices), quads=len(faces), all_boundary_edges_incidence_two=True,
                  signed_enclosed_volume_mm3=volume, relative_dependencies=[],
                  units_mm=True, Z_up=True, native_omniverse_validation=False,
                  physical_or_manufacturing_validation=False)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
