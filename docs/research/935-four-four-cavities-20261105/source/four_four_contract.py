"""Source-derived contract for convex four-to-four edge cavities.

No coordinates are generated here. The new edge must connect opposite vertices
of the old four-cycle, and the four alternative cell sets are uniquely specified.
"""
import numpy as np


FACES = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
BINS = (.0001, .001, .01, .05, .1)


def ring_data(old, center):
    keep = ~np.any(old[:, :, :, None] == center[:, None, None, :], axis=3)
    assert np.all(keep.sum(axis=2) == 2)
    others = np.sort(old[keep].reshape(-1, 8), axis=1)
    assert np.all(others[:, ::2] == others[:, 1::2])
    ring = others[:, ::2]
    assert np.all(np.diff(ring.astype(np.int64), axis=1) > 0)
    edges = np.sort(old[keep].reshape(-1, 4, 2), axis=2)
    return ring, edges


def strict_support(nodes, old, center, exact):
    ring, _ = ring_data(old, center)
    vertices = np.column_stack((center, ring))
    faces = old[:, :, FACES].reshape(-1, 16, 3)
    internal = np.all(np.any(faces[:, :, :, None] == center[:, None, None, :], axis=2), axis=2)
    assert np.all(internal.sum(axis=1) == 8)
    hull = faces[~internal].reshape(-1, 8, 3)
    missing = ~np.any(vertices[:, None, :, None] == hull[:, :, None, :], axis=3)
    assert np.all(missing.sum(axis=2) == 3)
    other = np.broadcast_to(vertices[:, None, :], missing.shape)[missing].reshape(-1, 8, 3)
    probes = np.concatenate((np.broadcast_to(hull[:, :, None, :], (len(old), 8, 3, 3)), other[:, :, :, None]), axis=3)
    xyz = nodes[probes.reshape(-1, 4)]
    low, high = exact.determinant_interval(xyz)
    low, high = low.reshape(-1, 24), high.reshape(-1, 24)
    passed = ~np.any(low >= 0, axis=1)
    fallback = coplanar = 0
    xyz = xyz.reshape(-1, 24, 4, 3)
    for row in np.flatnonzero(passed & np.any(high >= 0, axis=1)):
        for column in np.flatnonzero(high[row] >= 0):
            value = exact.exact_determinant(xyz[row, column])
            fallback += 1
            if value >= 0:
                passed[row] = False
                coplanar += int(value == 0)
                break
    return passed, fallback, coplanar


def chain_equal(old, new):
    faces = np.concatenate((old[:, :, FACES].reshape(-1, 16, 3), new[:, :, FACES].reshape(-1, 16, 3)), axis=1)
    inversions = ((faces[:, :, 0] > faces[:, :, 1]).astype(np.int8)
        + (faces[:, :, 0] > faces[:, :, 2]).astype(np.int8)
        + (faces[:, :, 1] > faces[:, :, 2]).astype(np.int8))
    signs = 1 - 2 * (inversions % 2)
    signs[:, 16:] *= -1
    keys = np.sort(faces, axis=2)
    order = np.lexsort((keys[:, :, 2], keys[:, :, 1], keys[:, :, 0]), axis=1)
    ordered = np.take_along_axis(keys, order[:, :, None], axis=1)
    signs = np.take_along_axis(signs, order, axis=1)
    return (np.all(ordered[:, ::2] == ordered[:, 1::2], axis=(1, 2))
        & np.all(signs[:, ::2] + signs[:, 1::2] == 0, axis=1)
        & np.all(np.any(ordered[:, 2::2] != ordered[:, :-2:2], axis=2), axis=1))


def expected_sets(old, center, diagonal, new):
    ring, old_edges = ring_data(old, center)
    assert np.all(diagonal[:, 0] < diagonal[:, 1])
    assert np.all(np.any(diagonal[:, :, None] == ring[:, None, :], axis=2))
    assert not np.any(np.all(old_edges == diagonal[:, None, :], axis=2))
    remaining = ring[~np.any(ring[:, :, None] == diagonal[:, None, :], axis=2)].reshape(-1, 2)
    expected = np.stack([np.column_stack((diagonal, center[:, a], remaining[:, b]))
        for a, b in ((0, 0), (0, 1), (1, 0), (1, 1))], axis=1)
    expected, actual = np.sort(expected, axis=2), np.sort(new, axis=2)
    def canonical(value):
        order = np.lexsort(tuple(value[:, :, i] for i in reversed(range(4))), axis=1)
        return np.take_along_axis(value, order[:, :, None], axis=1)
    assert np.array_equal(canonical(expected), canonical(actual))


def validate(nodes, old, center, diagonal, new, exact, quality):
    assert old.shape == new.shape == (len(old), 4, 4)
    expected_sets(old, center, diagonal, new)
    assert chain_equal(old, new).all(), "Changed cavity boundary"
    support, _, _ = strict_support(nodes, old, center, exact)
    assert support.all(), "Strict old hull support failed"
    old_q = quality(nodes[old].reshape(-1, 4, 3), exact).reshape(-1, 4)
    new_q = quality(nodes[new].reshape(-1, 4, 3), exact).reshape(-1, 4)
    assert np.all(new_q >= .01)
    gain = (old_q < .0001).sum(axis=1) - (new_q < .0001).sum(axis=1)
    assert np.all(gain > 0)
    for value in BINS:
        assert np.all((new_q < value).sum(axis=1) <= (old_q < value).sum(axis=1)), "A quality bin regressed"
    return gain, old_q, new_q
