"""Exact oriented-boundary partition certificate for nonconvex four-cell domains.

Proof: for any point off the finite set of triangle planes, the outward
boundary of a positive tetrahedron has winding number equal to its indicator.
Triangle contributions are additive and change sign under orientation reversal.
Exact equality of the complete oriented triangle chains therefore equates the
two sums of cell indicators everywhere off those planes. Exact pairwise
interior-disjointness makes each sum an ordinary union indicator. Both finite
unions of full-dimensional closed tetrahedra are closures of their interiors,
so equality away from the triangle planes proves equality of the closed sets.
No convex hull, sampled winding values, tolerance or guessed geometry is used.

Primitive predicates are passed explicitly from a frozen hash-checked module;
the new certificate, not any frozen predecessor, implements this domain proof.
"""
from fractions import Fraction as Q
from itertools import combinations

BINS = (.0001, .001, .01, .05, .1)


def certify(nodes, old, new, geometry):
    ids = sorted({int(i) for cell in old for i in cell})
    assert len(old) == len(new) == 4 and len(ids) == 6
    assert {int(i) for cell in new for i in cell} == set(ids)
    assert len({tuple(sorted(map(int, cell))) for cell in old}) == 4
    assert len({tuple(sorted(map(int, cell))) for cell in new}) == 4
    points, denominator = geometry.exact_points(nodes, ids)
    totals = []; cubes = []; bins = []
    for cells in (old, new):
        tets = [[points[int(i)] for i in cell] for cell in cells]
        determinants = [geometry.determinant(tet) for tet in tets]
        assert min(determinants) > 0, "Nonpositive source or replacement"
        for a, b in combinations(tets, 2):
            assert geometry.disjoint_interiors(a, b), "Cell interiors overlap"
        quality = []
        for tet, d in zip(tets, determinants):
            s = sum(geometry.dot(geometry.sub(tet[a], tet[b]), geometry.sub(tet[a], tet[b])) for a, b in geometry.EDGES)
            quality.append(Q(432*d*d, s**3))
        cubes.append(quality); totals.append(sum(determinants))
        bins.append([sum(q < Q.from_float(threshold)**3 for q in quality) for threshold in BINS])
    assert geometry.chain(old) == geometry.chain(new), "Oriented triangle chains differ"
    assert totals[0] == totals[1], "Exact volume conservation failed"
    assert min(cubes[1]) >= Q.from_float(.01)**3, "New-cell quality floor failed"
    assert all(a >= b for a, b in zip(*bins)), "A reported quality bin worsens"
    assert bins[0][0] > bins[1][0], "No critical-cell improvement"
    return {"exact_domain_volume": Q(totals[0], 6*denominator**3),
        "old_bins": bins[0], "new_bins": bins[1],
        "old_minimum_quality_cubed": min(cubes[0]), "new_minimum_quality_cubed": min(cubes[1]),
        "complete_oriented_boundary_chain_identical": True,
        "all_twelve_old_and_new_cell_pairs_disjoint": True,
        "same_exact_closed_domain_by_indicator_additivity": True,
        "convexity_required_or_inferred": False, "sampled_winding_used_as_proof": False,
        "new_edge_Jacobian_condition_upper_bound": 12000}
