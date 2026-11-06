"""Separate Fraction plane/dual checks and boundary-preserving cone verification."""
from fractions import Fraction as F
from itertools import combinations

import numpy as np


def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), F(0))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def fraction(pair):
    return F(*map(int, pair))


def dual(rows, bounds, proof):
    support = proof["support"]; weights = list(map(fraction, proof["weights"]))
    assert len(support) == len(weights) and 0 < len(support) <= 4
    assert len(support) == len(set(support)) and all(type(i) is int and 0 <= i < len(rows) for i in support)
    assert min(weights) >= 0 and sum(weights) == 1
    assert all(sum(w*rows[i][a] for i, w in zip(support, weights)) == 0 for a in range(3))
    upper = sum(w*bounds[i] for i, w in zip(support, weights))
    assert upper == fraction(proof["normalized_margin_upper_bound"])
    assert proof["no_strict_kernel_proved"] == (upper <= 0)
    return upper


def controls():
    rows = [(F(1), F(0), F(0)), (F(-1), F(0), F(0))]
    for rhs, expected in (([F(0), F(-1)], F(-1, 2)), ([F(0), F(0)], F(0))):
        proof = {"support": [0, 1], "weights": [["1", "2"], ["1", "2"]],
                 "normalized_margin_upper_bound": [str(expected.numerator), str(expected.denominator)], "no_strict_kernel_proved": True}
        assert dual(rows, rhs, proof) == expected
        for bad in ({**proof, "weights": [["1", "2"], ["1", "4"]]},
                    {**proof, "normalized_margin_upper_bound": ["1", "1"]}):
            try:
                dual(rows, rhs, bad)
            except AssertionError:
                pass
            else:
                raise AssertionError("Forged independent dual accepted")
    return {"independent_negative_and_zero_dual_controls": True, "forged_weights_and_upper_bounds_refused": True}


def check(nodes, faces, proposal):
    frame = proposal["exact_affine_frame"]
    denominator = frame["denominator"]; span_integer = frame["span"]
    assert type(denominator) is int and denominator > 0 and denominator & (denominator-1) == 0
    assert type(span_integer) is int and span_integer > 0 and span_integer & (span_integer-1) == 0
    origin = tuple(F(v, denominator) for v in frame["origin"]); span = F(span_integer, denominator)
    points = [tuple(F.from_float(float(x)) for x in p) for p in nodes]
    assert origin == points[0]
    assert all(abs(p[a]-origin[a]) <= span for p in points for a in range(3))
    rows = []; bounds = []
    for face in faces:
        a, b, c = [points[int(i)] for i in face]
        normal = cross(sub(b, a), sub(c, a)); norm = sum(abs(x) for x in normal); assert norm > 0
        rows.append(tuple(x/norm for x in normal)); bounds.append(dot(normal, sub(a, origin))/(norm*span))
    point = tuple(F.from_float(float.fromhex(x)) for x in proposal["point_hex"])
    local = tuple(x/span for x in sub(point, origin))
    margin = min(b-dot(row, local) for row, b in zip(rows, bounds))
    assert margin == fraction(proposal["exact_stored_normalized_margin"])
    assert proposal["strict_kernel_for_stored_point"] == (margin > 0)
    upper = dual(rows, bounds, proposal["exact_dual"]) if proposal["exact_dual"] is not None else None
    if upper is not None:
        assert margin <= upper
    return {"independent_Fraction_stored_point_margin_matches": True,
            "strict_stored_point": margin > 0, "exact_dual_checked": upper is not None,
            "no_strict_single_point_kernel_proved": upper is not None and upper <= 0}


def cone(nodes, old, point, new, contract, geometry, oracle, verifier):
    old_geometry, old_volume, old_cubes = oracle.fractions(nodes, old)
    volumes = [dot(sub(p[1], p[0]), cross(sub(p[2], p[0]), sub(p[3], p[0])))/6 for p in old_geometry]
    centroid = tuple(sum((v*sum(p[i][a] for i in range(4))/4 for v, p in zip(volumes, old_geometry)), F(0))/old_volume for a in range(3))
    assert not np.any(np.all(nodes == point, axis=1))
    augmented = np.vstack((nodes, point)); old_boundary = verifier.independent_chain(old)
    assert old_boundary == verifier.independent_chain(new)
    expected = {tuple(sorted((len(nodes), *face))) for face in old_boundary}
    assert len(expected) == len(new) and {tuple(sorted(map(int, row))) for row in new} == expected
    assert {int(i) for tet in old for i in tet} == {v for face in old_boundary for v in face}
    shared = contract.certify(augmented, old, new, geometry)
    new_geometry, new_volume, new_cubes = oracle.fractions(augmented, new)
    assert new_volume == old_volume == shared["exact_domain_volume"]
    before = [sum(q < F.from_float(t)**3 for q in old_cubes) for t in contract.BINS]
    after = [sum(q < F.from_float(t)**3 for q in new_cubes) for t in contract.BINS]
    assert before == shared["old_bins"] and after == shared["new_bins"]
    assert min(new_cubes) >= F.from_float(.01)**3 and all(a >= b for a, b in zip(before, after))
    planes = [oracle.witness(a, b) for group in (old_geometry, new_geometry) for a, b in combinations(group, 2)]
    assert len(planes) == shared["old_pair_separations"]+shared["new_pair_separations"]
    return augmented, centroid, before, after, planes, shared
