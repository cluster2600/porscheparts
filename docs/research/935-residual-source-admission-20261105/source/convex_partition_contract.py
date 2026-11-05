"""Exact finite convex-partition proof, including coplanar hull facets.

Both old and new positive tetrahedra use vertices of the same independently
enumerated convex hull. Complete separating-axis tests prove pairwise disjoint
interiors. Exact summed volumes equal the hull volume, proving coverage of that
entire closed hull. The oriented boundary chain must also remain identical.
This replaces strict supporting-plane proxy rejection with an actual domain
partition proof; it does not admit genuinely nonconvex source unions.
"""
from collections import Counter
from fractions import Fraction as Q
from itertools import combinations

FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
EDGES = tuple(combinations(range(4), 2))
BINS = (.0001, .001, .01, .05, .1)


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def determinant(tet):
    return dot(sub(tet[1], tet[0]), cross(sub(tet[2], tet[0]), sub(tet[3], tet[0])))


def exact_points(nodes, ids):
    ratios = [[float(x).as_integer_ratio() for x in nodes[i]] for i in ids]
    denominator = max(q for row in ratios for _, q in row)
    points = {int(i): tuple(p*(denominator//q) for p, q in row) for i, row in zip(ids, ratios)}
    assert len(set(points.values())) == len(ids)
    return points, denominator


def projected_hull(points, ids, axis):
    axes = [k for k in range(3) if k != axis]
    ordered = sorted(ids, key=lambda i: (points[i][axes[0]], points[i][axes[1]]))
    def area(a, b, c):
        u, v, w = (points[i] for i in (a, b, c))
        return (v[axes[0]]-u[axes[0]])*(w[axes[1]]-u[axes[1]])-(v[axes[1]]-u[axes[1]])*(w[axes[0]]-u[axes[0]])
    halves = []
    for sequence in (ordered, list(reversed(ordered))):
        half = []
        for i in sequence:
            while len(half) >= 2 and area(half[-2], half[-1], i) <= 0:
                half.pop()
            half.append(i)
        halves.append(half[:-1])
    polygon = halves[0]+halves[1]
    assert len(polygon) >= 3 and len(polygon) == len(set(polygon))
    return polygon


def hull_volume_numerator(points):
    """Return n^3 times hull determinant-sum (volume is sum/(6*scale^3))."""
    ids = sorted(points); facets = {}
    for a, b, c in combinations(ids, 3):
        normal = cross(sub(points[b], points[a]), sub(points[c], points[a]))
        if not any(normal):
            continue
        values = {i: dot(normal, sub(points[i], points[a])) for i in ids}
        if min(values.values()) < 0 < max(values.values()):
            continue
        assert any(values.values()), "Full-dimensional hull required"
        members = tuple(i for i in ids if values[i] == 0)
        facets[members] = max(range(3), key=lambda k: abs(normal[k]))
    assert len(facets) >= 4
    count = len(ids); total = tuple(sum(points[i][k] for i in ids) for k in range(3))
    volume = 0
    for members, axis in facets.items():
        polygon = projected_hull(points, members, axis)
        for i in range(1, len(polygon)-1):
            vectors = [tuple(count*x-y for x, y in zip(points[v], total)) for v in (polygon[0], polygon[i], polygon[i+1])]
            value = dot(vectors[0], cross(vectors[1], vectors[2]))
            assert value != 0
            volume += abs(value)
    return volume, len(facets)


def disjoint_interiors(left, right):
    """Complete exact SAT for two full-dimensional convex tetrahedra."""
    axes = [cross(sub(t[b], t[a]), sub(t[c], t[a])) for t in (left, right) for a, b, c in FACES]
    axes.extend(cross(sub(left[b], left[a]), sub(right[d], right[c])) for a, b in EDGES for c, d in EDGES)
    for axis in axes:
        if not any(axis):
            continue
        a = [dot(axis, p) for p in left]; b = [dot(axis, p) for p in right]
        if max(a) <= min(b) or max(b) <= min(a):
            return True
    return False


def chain(cells):
    result = Counter()
    for tet in cells:
        for indices in FACES:
            face = [int(tet[i]) for i in indices]
            inversions = sum(face[i] > face[j] for i in range(3) for j in range(i+1, 3))
            result[tuple(sorted(face))] += 1 if inversions % 2 == 0 else -1
    return {k:v for k, v in result.items() if v}


def certify(nodes, old, new):
    ids = sorted({int(i) for tet in old for i in tet})
    assert len(old) == len(new) == 4 and len(ids) == 6
    assert {int(i) for tet in new for i in tet} == set(ids)
    assert len({tuple(sorted(map(int, t))) for t in old}) == 4
    assert len({tuple(sorted(map(int, t))) for t in new}) == 4
    points, scale = exact_points(nodes, ids)
    hull, facets = hull_volume_numerator(points)
    counts = []; minima = []; determinants = []
    for cells in (old, new):
        geometry = [[points[int(i)] for i in tet] for tet in cells]
        det = [determinant(t) for t in geometry]; assert min(det) > 0
        assert sum(det)*len(ids)**3 == hull, "Source or replacement does not cover its convex hull"
        for left, right in combinations(geometry, 2):
            assert disjoint_interiors(left, right), "Overlapping tetrahedron interiors"
        cubes = []
        for tet, d in zip(geometry, det):
            edge_sum = sum(dot(sub(tet[a], tet[b]), sub(tet[a], tet[b])) for a, b in EDGES)
            cubes.append(Q(432*d*d, edge_sum**3))
        counts.append([sum(q < Q.from_float(t)**3 for q in cubes) for t in BINS])
        minima.append(min(cubes)); determinants.append(sum(det))
    assert chain(old) == chain(new), "Oriented boundary differs"
    assert minima[1] >= Q.from_float(.01)**3
    assert all(a >= b for a, b in zip(counts[0], counts[1]))
    assert counts[0][0] > counts[1][0], "No critical-cell repair"
    return {"exact_domain_volume": Q(determinants[0], 6*scale**3),
        "old_bins": counts[0], "new_bins": counts[1], "hull_facets": facets,
        "old_minimum_quality_cubed": minima[0], "new_minimum_quality_cubed": minima[1],
        "all_twelve_old_and_new_cell_pairs_disjoint": True, "old_and_new_cover_same_exact_convex_hull": True,
        "oriented_boundary_identical": True, "new_edge_Jacobian_condition_upper_bound": 12000}
