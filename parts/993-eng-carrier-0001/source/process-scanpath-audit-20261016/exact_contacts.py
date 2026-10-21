"""Closed IEEE polygon/line contacts, without GEOS intersection predicates.

Intervals are split at every exact ring intersection; a midpoint parity test
then certifies the entire closed interval. Boundary segments are included.
"""
from fractions import Fraction as Q
import math
import shapely


def point(p):
    if len(p) != 2 or not all(math.isfinite(float(c)) for c in p):
        raise ValueError('Invalid contact coordinate')
    return tuple(Q(float(c)) for c in p)


def cross(a, b):
    return a[0]*b[1]-a[1]*b[0]


def difference(a, b):
    return a[0]-b[0], a[1]-b[1]


def on_segment(a, b, p):
    return (cross(difference(b, a), difference(p, a)) == 0 and
            all(min(a[k], b[k]) <= p[k] <= max(a[k], b[k]) for k in (0, 1)))


def rings(material):
    if material.is_empty or not material.is_valid:
        raise ValueError('Invalid contact material')
    polygons = [material] if material.geom_type == 'Polygon' else list(material.geoms)
    if any(p.geom_type != 'Polygon' for p in polygons):
        raise ValueError('Contact material must be polygonal')
    return [[point(p) for p in ring.coords] for polygon in polygons
            for ring in [polygon.exterior, *polygon.interiors]]


class BoundaryIndex:
    """Only an outward-bounded broad phase; predicates remain rational."""
    def __init__(self, boundaries):
        self.edges = [(a, b) for ring in boundaries for a, b in zip(ring[:-1], ring[1:])]
        self.tree = shapely.STRtree([shapely.LineString([[float(c) for c in p] for p in edge]) for edge in self.edges])
        self.maximum_x = max(p[0] for edge in self.edges for p in edge)

    def candidates(self, a, b):
        values = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
        rounded = []
        for i, value in enumerate(values):
            f = float(value)
            if i < 2 and Q(f) > value:
                f = math.nextafter(f, -math.inf)
            if i >= 2 and Q(f) < value:
                f = math.nextafter(f, math.inf)
            rounded.append(f)
        return [self.edges[i] for i in self.tree.query(shapely.box(*rounded))]


def inside(boundaries, p, index=None):
    parity = False
    if index is not None and p[0] > index.maximum_x:
        return False
    edges = (index.candidates(p, (index.maximum_x, p[1])) if index is not None else
             [(a, b) for ring in boundaries for a, b in zip(ring[:-1], ring[1:])])
    for a, b in edges:
        if on_segment(a, b, p):
            return True
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if x > p[0]:
                parity = not parity
    return parity


def clip_contacts(material, interfaces):
    boundaries = rings(material)
    index = BoundaryIndex(boundaries)
    result = set()
    for path in interfaces:
        points = [point(p) for p in path]
        for a, b in zip(points[:-1], points[1:]):
            if a == b:
                raise ValueError('Zero source contact interface')
            r = difference(b, a)
            axis = 0 if r[0] else 1
            split = {Q(0), Q(1)}
            for c, d in index.candidates(a, b):
                s = difference(d, c)
                den = cross(r, s)
                if den:
                    t = cross(difference(c, a), s)/den
                    u = cross(difference(c, a), r)/den
                    if 0 <= t <= 1 and 0 <= u <= 1:
                        split.add(t)
                elif cross(difference(c, a), r) == 0:
                    split.update((p[axis]-a[axis])/r[axis] for p in (c, d)
                                 if 0 <= (p[axis]-a[axis])/r[axis] <= 1)
            ordered = sorted(split)
            for first, last in zip(ordered[:-1], ordered[1:]):
                middle = tuple(a[k]+(first+last)*r[k]/2 for k in (0, 1))
                if inside(boundaries, middle, index):
                    segment = tuple(tuple(a[k]+t*r[k] for k in (0, 1)) for t in (first, last))
                    result.add(tuple(sorted(segment)))
    return sorted(result)


def round_contact_traces(material, interfaces):
    """Generator adapter: encode each proven whole interval, nearest/even."""
    result = set()
    for segment in clip_contacts(material, interfaces):
        encoded = tuple(sorted(tuple(float(c) for c in p) for p in segment))
        if encoded[0] == encoded[1]:
            raise ValueError('A nonzero exact contact collapses in float64')
        result.add(encoded)
    return [[list(p) for p in segment] for segment in sorted(result)]


def contact_encoding_check(material, interfaces, recorded):
    expected = round_contact_traces(material, interfaces)
    actual = set()
    for path in recorded:
        points = [point(p) for p in path]
        for a, b in zip(points[:-1], points[1:]):
            if a == b:
                raise ValueError('Zero encoded contact interval')
            actual.add(tuple(sorted((tuple(float(c) for c in a), tuple(float(c) for c in b)))))
    encoded = {tuple(tuple(p) for p in segment) for segment in expected}
    return actual == encoded
