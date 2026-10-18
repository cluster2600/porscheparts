"""Clip source contacts in two closed IEEE polygon domains without re-encoding."""
import hashlib
import importlib.util
from pathlib import Path

_SOURCE = Path(__file__).with_name('exact_contacts.py')
DEPENDENCY_SHA256 = '399db612b1d5fde6b1a0290d4d497d9b01e6afe3a28d7b63a095a2a06e271cca'
if hashlib.sha256(_SOURCE.read_bytes()).hexdigest() != DEPENDENCY_SHA256:
    raise ValueError('The frozen exact contact predicate dependency changed')
_spec = importlib.util.spec_from_file_location('carrier_exact_contacts_frozen_both', _SOURCE)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
Q = _base.Q


def clip_contacts_in_both(material, domain, interfaces_raw):
    """Return exact Fraction segments in source interface ∩ domain ∩ material.

    The source and both polygon inputs are interpreted as their exact IEEE
    coordinates. Split parameters include every ring intersection from BOTH
    polygons before any midpoint test. No intermediate intersection or float
    encoding is constructed. Closed polygon boundaries are included.
    """
    boundaries = [_base.rings(polygon) for polygon in (material, domain)]
    indices = [_base.BoundaryIndex(rings) for rings in boundaries]
    result = set()
    for path in interfaces_raw:
        points = [_base.point(p) for p in path]
        if len(points) < 2:
            raise ValueError('A source contact path needs at least two points')
        for a, b in zip(points[:-1], points[1:]):
            if a == b:
                raise ValueError('Zero source contact interface')
            direction = _base.difference(b, a)
            axis = 0 if direction[0] else 1
            split = {Q(0), Q(1)}
            for index in indices:
                for c, d in index.candidates(a, b):
                    edge = _base.difference(d, c)
                    denominator = _base.cross(direction, edge)
                    if denominator:
                        t = _base.cross(_base.difference(c, a), edge)/denominator
                        u = _base.cross(_base.difference(c, a), direction)/denominator
                        if 0 <= t <= 1 and 0 <= u <= 1:
                            split.add(t)
                    elif _base.cross(_base.difference(c, a), direction) == 0:
                        split.update((p[axis]-a[axis])/direction[axis] for p in (c, d)
                                     if 0 <= (p[axis]-a[axis])/direction[axis] <= 1)
            ordered = sorted(split)
            for first, last in zip(ordered[:-1], ordered[1:]):
                middle = tuple(a[k]+(first+last)*direction[k]/2 for k in (0, 1))
                if all(_base.inside(rings, middle, index) for rings, index in zip(boundaries, indices)):
                    segment = tuple(tuple(a[k]+t*direction[k] for k in (0, 1))
                                    for t in (first, last))
                    result.add(tuple(sorted(segment)))
    return sorted(result)


def round_contacts_in_both(material, domain, interfaces_raw):
    """Encode only the final certified intervals with float(Fraction), nearest/even."""
    result = set()
    for segment in clip_contacts_in_both(material, domain, interfaces_raw):
        encoded = tuple(sorted(tuple(float(c) for c in point) for point in segment))
        if encoded[0] == encoded[1]:
            raise ValueError('A nonzero exact contact collapses in float64')
        result.add(encoded)
    return [[list(point) for point in segment] for segment in sorted(result)]


def contact_encoding_check_in_both(material, domain, interfaces_raw, recorded):
    """Compare a recorded contact with that single final encoding, without tolerance."""
    expected = round_contacts_in_both(material, domain, interfaces_raw)
    actual = set()
    for path in recorded:
        points = [_base.point(p) for p in path]
        if len(points) < 2:
            raise ValueError('An encoded contact path needs at least two points')
        for a, b in zip(points[:-1], points[1:]):
            if a == b:
                raise ValueError('Zero encoded contact interval')
            actual.add(tuple(sorted((tuple(float(c) for c in a), tuple(float(c) for c in b)))))
    return actual == {tuple(tuple(point) for point in segment) for segment in expected}
