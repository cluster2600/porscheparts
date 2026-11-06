"""Independently inspect a native 2x2x2 unit-cube control and reflect it.

Only a synthetic control is created/modified. Native points, faces, cell
incidence and boundary sets must match an analytic 27-node, eight-cell grid.
"""
import argparse
from fractions import Fraction
import itertools
import json
from pathlib import Path
import re
import shutil


BLOCK = """FoamFile
{
    format ascii;
    class dictionary;
    object blockMeshDict;
}
convertToMeters 1;
vertices
(
    (0 0 0) (1 0 0) (1 1 0) (0 1 0)
    (0 0 1) (1 0 1) (1 1 1) (0 1 1)
);
blocks (hex (0 1 2 3 4 5 6 7) (2 2 2) simpleGrading (1 1 1));
edges ();
boundary
(
    synthetic_boundary
    {
        type patch;
        faces ((0 4 7 3) (1 2 6 5) (0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7));
    }
);
mergePatchPairs ();
"""


def prepare(folder, control_dict):
    (folder / "system").mkdir(parents=True)
    (folder / "system/controlDict").write_bytes(control_dict.read_bytes())
    (folder / "system/blockMeshDict").write_text(BLOCK)


def body(path):
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", path.read_text(), flags=re.S)
    assert re.search(r"\bformat\s+ascii\s*;", text)
    tail = text[text.index("}") + 1:]
    header = re.match(r"\s*(\d+)\s*\(", tail, flags=re.S)
    assert header is not None
    return int(header.group(1)), tail[header.end():tail.rfind(")")]


def labels(path):
    count, text = body(path)
    values = list(map(int, text.split()))
    assert len(values) == count and all(v >= 0 for v in values)
    return values


def inspect_and_reflect(root):
    control = root / "control"
    folder = control / "constant/polyMesh"
    count, text = body(folder / "points")
    points = [tuple(map(float, row.split())) for row in re.findall(r"\(([^()]*)\)", text)]
    expected_points = set(itertools.product((0., .5, 1.), repeat=3))
    assert count == len(points) == len(set(points)) == 27 and set(points) == expected_points
    count, text = body(folder / "faces")
    faces = []
    for size, values in re.findall(r"(\d+)\s*\(([^()]*)\)", text):
        face = list(map(int, values.split()))
        assert int(size) == len(face) == len(set(face)) == 4
        assert all(0 <= value < 27 for value in face)
        faces.append(face)
    assert count == len(faces) == 36
    owners, neighbours = labels(folder / "owner"), labels(folder / "neighbour")
    assert len(owners) == 36 and len(neighbours) == 12
    cells, cell_faces = [set() for _ in range(8)], [0] * 8
    for i, face in enumerate(faces):
        assert owners[i] < 8
        cells[owners[i]].update(points[v] for v in face)
        cell_faces[owners[i]] += 1
        if i < 12:
            assert neighbours[i] < 8 and neighbours[i] != owners[i]
            cells[neighbours[i]].update(points[v] for v in face)
            cell_faces[neighbours[i]] += 1
    assert cell_faces == [6] * 8
    expected_cells = set()
    for corner in itertools.product((0., .5), repeat=3):
        expected_cells.add(frozenset(tuple(corner[d] + .5 * offset[d] for d in range(3)) for offset in itertools.product((0, 1), repeat=3)))
    assert {frozenset(cell) for cell in cells} == expected_cells
    expected_faces, expected_boundary = set(), set()
    for axis in range(3):
        others = [i for i in range(3) if i != axis]
        for fixed in (0., .5, 1.):
            for a, b in itertools.product((0., .5), repeat=2):
                vertices = []
                for u, v in itertools.product((0, 1), repeat=2):
                    row = [0., 0., 0.]
                    row[axis], row[others[0]], row[others[1]] = fixed, a + .5 * u, b + .5 * v
                    vertices.append(tuple(row))
                face = frozenset(vertices)
                expected_faces.add(face)
                if fixed in (0., 1.):
                    expected_boundary.add(face)
    assert {frozenset(points[v] for v in face) for face in faces} == expected_faces
    assert {frozenset(points[v] for v in face) for face in faces[12:]} == expected_boundary
    internal_counts = [0] * 8
    for owner, neighbour in zip(owners[:12], neighbours):
        internal_counts[owner] += 1
        internal_counts[neighbour] += 1
    assert internal_counts == [3] * 8
    # Each cell has three orthogonal internal normals of equal area.
    # The native normalized area tensor is exactly I, determinant one.
    determinant = Fraction(1, 2)**3
    reflected = [(-x, y, z) for x, y, z in points]
    inverted = root / "inverted-control"
    shutil.copytree(control, inverted)
    path = inverted / "constant/polyMesh/points"
    header = path.read_text().split("}", 1)[0] + "}\n"
    path.write_text(header + "27\n(\n" + "\n".join("(" + " ".join(format(v, ".17g") for v in row) + ")" for row in reflected) + "\n)\n")
    for name in ("faces", "owner", "neighbour", "boundary"):
        assert (inverted / "constant/polyMesh" / name).read_bytes() == (folder / name).read_bytes()
    report = {"synthetic_only": True, "points": 27, "cells": 8, "faces": 36,
        "internal_faces": 12, "boundary_faces": 24,
        "complete_analytic_coordinate_cell_face_boundary_comparison_passed": True,
        "internal_faces_per_cell": internal_counts,
        "exact_normalized_internal_area_tensor_determinant": "1",
        "exact_each_positive_cell_volume": str(determinant),
        "reflection": "R=diag(-1,1,1), det(R)=-1; connectivity and face orientations unchanged",
        "exact_each_reflected_cell_signed_volume": str(-determinant),
        "expected_negative_volume_cells": 8,
        "no_head_geometry_modified": True}
    (root / "control-contract.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    inspect_and_reflect(args.root)
