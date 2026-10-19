"""Compile a validated closed convex Fraction polygon to integer halfplanes.

No point is rounded. A positive common denominator makes each stored integer
sign exactly the sign of the original oriented rational edge determinant.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
import math


def _point(value):
    if len(value) != 2 or any(not isinstance(c, Q) for c in value):
        raise ValueError('Each coordinate must be one of exactly two Fractions')
    return tuple(value)


def _double_area(points):
    return sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(points, points[1:]+points[:1]))


def _contains(halfplanes, point):
    x, y = point
    xx, yy = x.numerator*y.denominator, y.numerator*x.denominator
    one = x.denominator*y.denominator
    return all(a*xx+b*yy+c*one >= 0 for a, b, c in halfplanes)


@dataclass(frozen=True, init=False)
class CompiledConvex:
    vertices: tuple
    halfplanes: tuple
    orientation: int

    def __init__(self, vertices):
        points = tuple(_point(p) for p in vertices)
        if len(points) < 3 or len(set(points)) != len(points):
            raise ValueError('A convex boundary requires distinct unclosed vertices')
        area = _double_area(points)
        if not area:
            raise ValueError('A convex polygon must have positive exact area')
        side, halfplanes = (1 if area > 0 else -1), []
        for a, b in zip(points, points[1:]+points[:1]):
            dx, dy = b[0]-a[0], b[1]-a[1]
            rational = (-side*dy, side*dx, side*(dy*a[0]-dx*a[1]))
            scale = math.lcm(*(c.denominator for c in rational))
            integers = tuple(c.numerator*(scale//c.denominator) for c in rational)
            divisor = math.gcd(*integers)
            halfplanes.append(tuple(c//divisor for c in integers))
        halfplanes = tuple(halfplanes)
        # Every oriented edge must support all vertices on its closed inner
        # side. This also rejects a noncyclic or self-crossing boundary order.
        if any(not _contains(halfplanes, p) for p in points):
            raise ValueError('The boundary is not convex in cyclic order')
        object.__setattr__(self, 'vertices', points)
        object.__setattr__(self, 'halfplanes', halfplanes)
        object.__setattr__(self, 'orientation', side)

    def contains(self, point):
        return _contains(self.halfplanes, _point(point))

    def contains_triangle(self, triangle):
        points = tuple(_point(p) for p in triangle)
        if len(points) != 3 or len(set(points)) != 3 or not _double_area(points):
            raise ValueError('A source triangle needs three distinct positive-area Fraction vertices')
        # A convex closed set contains the complete triangle iff it contains
        # its three vertices. Zero halfplane signs are included, without epsilon.
        return all(_contains(self.halfplanes, p) for p in points)
