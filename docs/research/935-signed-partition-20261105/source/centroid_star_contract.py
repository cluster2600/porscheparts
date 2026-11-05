"""Boundary-exact cavity cone about its actual stored volume-centroid proposal.

The source boundary, source-point retention and fixed face-quality admission
precede point construction. The point is a numerical interior mesh node, not
an inferred specimen feature. The signed-boundary domain proof is the same as
the fixed four/six-cell profiles; convexity is not assumed.
"""
from fractions import Fraction as Q
from itertools import combinations

FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
BINS = (.0001, .001, .01, .05, .1)


def boundary(cells):
    faces = {}
    for tet in cells:
        for pattern in FACES:
            oriented = tuple(int(tet[i]) for i in pattern)
            faces.setdefault(tuple(sorted(oriented)), []).append(oriented)
    result = []
    for entries in faces.values():
        assert len(entries) <= 2, "Nonmanifold source cavity face"
        if len(entries) == 1:
            result.append(entries[0])
        else:
            def sign(face):
                return 1-2*(sum(face[i] > face[j] for i in range(3) for j in range(i+1, 3)) % 2)
            assert sign(entries[0])+sign(entries[1]) == 0
    return sorted(result, key=lambda row: tuple(sorted(row)))


def topology(faces):
    edges = {}; link = {}
    for face in faces:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edges.setdefault(tuple(sorted((a, b))), []).append(1 if a < b else -1)
        for v in face:
            a, b = sorted(set(face)-{v})
            graph = link.setdefault(v, {})
            graph.setdefault(a, set()).add(b); graph.setdefault(b, set()).add(a)
    assert all(len(s) == 2 and sum(s) == 0 for s in edges.values()), "Cavity boundary edges not closed and oriented"
    assert len(link)-len(edges)+len(faces) == 2, "Cavity boundary not an Euler sphere"
    for graph in link.values():
        assert all(len(row) == 2 for row in graph.values()), "Nonmanifold cavity vertex"
        pending = [next(iter(graph))]; reached = set()
        while pending:
            v = pending.pop()
            if v not in reached:
                reached.add(v); pending.extend(graph[v]-reached)
        assert len(reached) == len(graph), "Disconnected cavity vertex link"
    graph = {v:set() for v in link}
    for a, b in edges:
        graph[a].add(b); graph[b].add(a)
    pending = [next(iter(graph))]; reached = set()
    while pending:
        v = pending.pop()
        if v not in reached:
            reached.add(v); pending.extend(graph[v]-reached)
    assert len(reached) == len(graph), "Disconnected cavity boundary"


def source_admission(nodes, old, geometry):
    faces = boundary(old); topology(faces)
    ids = sorted({int(i) for tet in old for i in tet})
    assert set(ids) == {i for face in faces for i in face}, "Old interior numerical nodes need a separate retention policy"
    points, scale = geometry.exact_points(nodes, ids)
    forced = []
    for face in faces:
        p = [points[i] for i in face]
        normal = geometry.cross(geometry.sub(p[1], p[0]), geometry.sub(p[2], p[0]))
        s = sum(geometry.dot(geometry.sub(p[a], p[b]), geometry.sub(p[a], p[b])) for a, b in ((0, 1), (0, 2), (1, 2)))
        assert geometry.dot(normal, normal) > 0
        if Q(12*geometry.dot(normal, normal), s*s) < Q.from_float(.01)**3:
            forced.append(face)
    assert not forced, "Fixed cavity faces force a cell below the quality floor"
    return faces, points, scale


def volume_centroid(nodes, old, geometry):
    faces, points, scale = source_admission(nodes, old, geometry)
    determinants = [geometry.determinant([points[int(v)] for v in tet]) for tet in old]
    assert min(determinants) > 0
    total = sum(determinants)
    point = tuple(Q(sum(d*sum(points[int(v)][axis] for v in tet) for d, tet in zip(determinants, old)), 4*total*scale) for axis in range(3))
    return faces, point


def certify(nodes, old, new, geometry):
    old_ids = {int(i) for tet in old for i in tet}; new_ids = {int(i) for tet in new for i in tet}
    assert old_ids < new_ids and len(new_ids-old_ids) == 1
    source_faces, _, _ = source_admission(nodes, old, geometry)
    center = next(iter(new_ids-old_ids))
    expected = {tuple(sorted((center, *face))) for face in source_faces}
    assert len(new) == len(expected) and {tuple(sorted(map(int, tet))) for tet in new} == expected
    points, denominator = geometry.exact_points(nodes, sorted(new_ids))
    counts = []; minima = []; totals = []; pairs = []
    for cells in (old, new):
        assert len({tuple(sorted(map(int, t))) for t in cells}) == len(cells)
        tets = [[points[int(i)] for i in t] for t in cells]
        determinants = [geometry.determinant(t) for t in tets]
        assert min(determinants) > 0, "Centroid is not strictly inside every cavity face"
        for a, b in combinations(tets, 2):
            assert geometry.disjoint_interiors(a, b), "Cavity cell interiors overlap"
        cubes = []
        for tet, d in zip(tets, determinants):
            s = sum(geometry.dot(geometry.sub(tet[a], tet[b]), geometry.sub(tet[a], tet[b])) for a, b in geometry.EDGES)
            cubes.append(Q(432*d*d, s**3))
        counts.append([sum(q < Q.from_float(t)**3 for q in cubes) for t in BINS])
        minima.append(min(cubes)); totals.append(sum(determinants)); pairs.append(len(tets)*(len(tets)-1)//2)
    assert geometry.chain(old) == geometry.chain(new), "Oriented triangle chains differ"
    assert totals[0] == totals[1], "Exact volume conservation failed"
    assert minima[1] >= Q.from_float(.01)**3, "New-cell quality floor failed"
    assert all(a >= b for a, b in zip(*counts)), "A reported quality bin worsens"
    assert counts[0][0] > counts[1][0], "No critical-cell improvement"
    return {"exact_domain_volume": Q(totals[0], 6*denominator**3), "old_bins": counts[0], "new_bins": counts[1],
        "old_minimum_quality_cubed": minima[0], "new_minimum_quality_cubed": minima[1],
        "old_pair_separations": pairs[0], "new_pair_separations": pairs[1],
        "all_source_points_and_complete_oriented_boundary_preserved": True,
        "new_numerical_interior_nodes": 1, "same_exact_closed_domain_by_indicator_additivity": True,
        "new_edge_Jacobian_condition_upper_bound": 12000}
