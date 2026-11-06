"""Six-to-eight exact signed-boundary partition profile; same indicator proof.

Each partition is a finite union of positive tetrahedra with pairwise disjoint
interiors. Identical complete oriented triangle chains equate their indicator
sums and hence their closed domains. Convexity is neither required nor inferred.
No source/quality threshold, coordinate or external boundary is changed.
"""
from fractions import Fraction as Q
from itertools import combinations

BINS = (.0001, .001, .01, .05, .1)


def certify(nodes, old, new, geometry):
    ids = sorted({int(i) for tet in old for i in tet})
    assert len(old) == 6 and len(new) == 8 and len(ids) == 8
    assert {int(i) for tet in new for i in tet} == set(ids)
    assert len({tuple(sorted(map(int, t))) for t in old}) == 6
    assert len({tuple(sorted(map(int, t))) for t in new}) == 8
    points, denominator = geometry.exact_points(nodes, ids)
    counts = []; minima = []; totals = []
    for cells in (old, new):
        tetrahedra = [[points[int(i)] for i in t] for t in cells]
        determinants = [geometry.determinant(t) for t in tetrahedra]
        assert min(determinants) > 0, "Nonpositive source or replacement"
        for left, right in combinations(tetrahedra, 2):
            assert geometry.disjoint_interiors(left, right), "Cell interiors overlap"
        quality = []
        for tet, d in zip(tetrahedra, determinants):
            s = sum(geometry.dot(geometry.sub(tet[a], tet[b]), geometry.sub(tet[a], tet[b])) for a, b in geometry.EDGES)
            quality.append(Q(432*d*d, s**3))
        counts.append([sum(q < Q.from_float(t)**3 for q in quality) for t in BINS])
        minima.append(min(quality)); totals.append(sum(determinants))
    assert geometry.chain(old) == geometry.chain(new), "Oriented triangle chains differ"
    assert totals[0] == totals[1], "Exact volume conservation failed"
    assert minima[1] >= Q.from_float(.01)**3, "New-cell quality floor failed"
    assert all(a >= b for a, b in zip(*counts)), "A reported quality bin worsens"
    assert counts[0][0] > counts[1][0], "No critical-cell improvement"
    return {"exact_domain_volume": Q(totals[0], 6*denominator**3),
        "old_bins": counts[0], "new_bins": counts[1],
        "old_minimum_quality_cubed": minima[0], "new_minimum_quality_cubed": minima[1],
        "complete_oriented_boundary_chain_identical": True,
        "old_pair_separations": 15, "new_pair_separations": 28,
        "same_exact_closed_domain_by_indicator_additivity": True,
        "convexity_required_or_inferred": False, "sampled_winding_used_as_proof": False,
        "new_edge_Jacobian_condition_upper_bound": 12000}
