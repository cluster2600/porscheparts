"""Small explicit mesh formats and exact checks for tool-boundary controls."""

from collections import Counter
from fractions import Fraction
import gzip
import math
from pathlib import Path

from ft_common import finite


def read_surface(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as stream:
        if ".mesh64" in str(path):
            npoints, nfaces = map(int, stream.readline().split())
            if not 3 <= npoints <= 2000000 or not 1 <= nfaces <= 4000000:
                raise ValueError("bounded mesh required")
            points = [
                [finite(float(x)) for x in stream.readline().split()]
                for _ in range(npoints)
            ]
            faces = [[int(x) for x in stream.readline().split()] for _ in range(nfaces)]
            if stream.read().strip():
                raise ValueError("trailing mesh data")
        else:
            points, faces = [], []
            for line in stream:
                values = line.split()
                if values and values[0] == "v":
                    points.append([finite(float(x)) for x in values[1:]])
                elif values and values[0] == "f":
                    faces.append([int(x) - 1 for x in values[1:]])
    if not points or not faces or any(len(p) != 3 for p in points):
        raise ValueError("nonempty 3D triangular surface required")
    if any(
        len(f) != 3 or len(set(f)) != 3 or min(f) < 0 or max(f) >= len(points)
        for f in faces
    ):
        raise ValueError("invalid triangle indices")
    return points, faces


def closed_surface(points, faces):
    edges = Counter()
    directed = Counter()
    for a, b, c in faces:
        for x, y in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((x, y)))] += 1
            directed[(x, y)] += 1
    if (
        not edges
        or any(count != 2 for count in edges.values())
        or any(directed[(a, b)] != directed[(b, a)] for a, b in edges)
    ):
        raise ValueError("closed consistently oriented manifold shell required")


def determinant(points):
    a, b, c, d = [[Fraction.from_float(float(x)) for x in point] for point in points]
    u, v, w = [[row[i] - a[i] for i in range(3)] for row in (b, c, d)]
    return (
        u[0] * (v[1] * w[2] - v[2] * w[1])
        - u[1] * (v[0] * w[2] - v[2] * w[0])
        + u[2] * (v[0] * w[1] - v[1] * w[0])
    )


def verify_tets(points, tets, original_points, original_faces):
    boundary = Counter()
    for tet in tets:
        if (
            len(tet) != 4
            or len(set(tet)) != 4
            or min(tet) < 0
            or max(tet) >= len(points)
        ):
            raise ValueError("invalid tetrahedron")
        if determinant([points[i] for i in tet]) <= 0:
            raise ValueError("inverted or degenerate tetrahedron")
        a, b, c, d = tet
        for face in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)):
            boundary[tuple(sorted(tuple(points[i]) for i in face))] += 1
    if not tets or any(count > 2 for count in boundary.values()):
        raise ValueError("missing or nonmanifold volume")
    actual = {face for face, count in boundary.items() if count == 1}
    expected = {
        tuple(sorted(tuple(original_points[i]) for i in face))
        for face in original_faces
    }
    if actual != expected:
        raise ValueError("volume boundary differs from input shell")
    return {
        "tetrahedra": len(tets),
        "exact_positive_determinants": True,
        "exact_boundary_identity": True,
    }


def write_obj(path, points, faces):
    with Path(path).open("x") as stream:
        for point in points:
            stream.write(
                "v " + " ".join(format(finite(x), ".17g") for x in point) + "\n"
            )
        for face in faces:
            stream.write("f " + " ".join(str(x + 1) for x in face) + "\n")


def rigid_points(points, matrix):
    if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
        raise ValueError("4x4 rigid transform required")
    matrix = [[finite(x) for x in row] for row in matrix]
    if matrix[3] != [0, 0, 0, 1]:
        raise ValueError("homogeneous rigid transform required")
    for i in range(3):
        for j in range(3):
            if (
                abs(sum(matrix[k][i] * matrix[k][j] for k in range(3)) - int(i == j))
                > 1e-10
            ):
                raise ValueError("rotation must not scale or shear")
    rotation_det = sum(
        matrix[0][i]
        * (
            matrix[1][(i + 1) % 3] * matrix[2][(i + 2) % 3]
            - matrix[1][(i + 2) % 3] * matrix[2][(i + 1) % 3]
        )
        for i in range(3)
    )
    if abs(rotation_det - 1) > 1e-10:
        raise ValueError("proper rotation required")
    return [
        [
            finite(
                sum(matrix[i][j] * finite(point[j]) for j in range(3)) + matrix[i][3]
            )
            for i in range(3)
        ]
        for point in points
    ]
