"""Certify inclusion of closed polygonal sets on their stored IEEE coordinates.

GEOS supplies the polygon validity gate and an outward-bounded broad phase.
Every inclusion predicate, intersection parameter and witness is rational.
No polygon overlay, buffer, geometric tolerance or coordinate change is used.
"""
from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path

_PATH = Path(__file__).with_name('exact_contacts.py')
_EXPECTED = '399db612b1d5fde6b1a0290d4d497d9b01e6afe3a28d7b63a095a2a06e271cca'
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != _EXPECTED:
    raise RuntimeError('The frozen exact contact kernel identity changed')
_SPEC = importlib.util.spec_from_file_location('_polygon_coverage_contacts', _PATH)
_EXACT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_EXACT)


def _encoded(value):
    if isinstance(value, Q):
        return dict(numerator=str(value.numerator), denominator=str(value.denominator),
                    nearest_float=float(value))
    if isinstance(value, dict):
        return {key: _encoded(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encoded(item) for item in value]
    return value


def _splits(a, b, index):
    direction = _EXACT.difference(b, a)
    axis = 0 if direction[0] else 1
    split = {Q(0), Q(1)}
    for c, d in index.candidates(a, b):
        edge = _EXACT.difference(d, c)
        denominator = _EXACT.cross(direction, edge)
        if denominator:
            t = _EXACT.cross(_EXACT.difference(c, a), edge)/denominator
            u = _EXACT.cross(_EXACT.difference(c, a), direction)/denominator
            if 0 <= t <= 1 and 0 <= u <= 1:
                split.add(t)
        elif _EXACT.cross(_EXACT.difference(c, a), direction) == 0:
            split.update((p[axis]-a[axis])/direction[axis] for p in (c, d)
                         if 0 <= (p[axis]-a[axis])/direction[axis] <= 1)
    return sorted(split)


def _slab_points(boundaries):
    """One rational point in every open horizontal arrangement cell.

    Valid polygon rings have no crossings away from vertices. Consequently the
    order of edge intersections stays fixed between consecutive vertex heights.
    """
    ys = sorted({p[1] for ring in boundaries for p in ring})
    for low, high in zip(ys[:-1], ys[1:]):
        y = (low+high)/2
        xs = sorted({a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1])
                     for ring in boundaries for a, b in zip(ring[:-1], ring[1:])
                     if (a[1] > y) != (b[1] > y)})
        for left, right in zip(xs[:-1], xs[1:]):
            yield ((left+right)/2, y)


def prove_polygon_covered(source_polygon, target_polygon):
    """Return an exact passed/refused receipt for source subset target.

    Once every source boundary is covered, a connected complement of target
    cannot cross a source boundary. For a Polygon, each hole interior is one
    bounded complement component. This deliberately accepts only Polygon pairs;
    the continuous construction is checked per single free interval. A union
    with material islands would need a different complement-component proof.
    """
    for geometry in (source_polygon, target_polygon):
        if (geometry.geom_type != 'Polygon' or
                geometry.is_empty or not geometry.is_valid):
            raise ValueError('Expected a valid nonempty Polygon for each free interval')
    source = _EXACT.rings(source_polygon)
    target = _EXACT.rings(target_polygon)
    source_index = _EXACT.BoundaryIndex(source)
    target_index = _EXACT.BoundaryIndex(target)
    witnesses = []
    boundary_intervals = 0
    for ring_index, ring in enumerate(source):
        for edge_index, (a, b) in enumerate(zip(ring[:-1], ring[1:])):
            if not _EXACT.inside(target, a, target_index):
                witnesses.append(dict(kind='source_boundary_vertex_outside_target',
                                      ring=ring_index, edge=edge_index, point=a))
            if a == b:
                continue
            split = _splits(a, b, target_index)
            for first, last in zip(split[:-1], split[1:]):
                boundary_intervals += 1
                p = tuple(a[k]+(first+last)*(b[k]-a[k])/2 for k in (0, 1))
                if not _EXACT.inside(target, p, target_index):
                    witnesses.append(dict(kind='source_boundary_interval_outside_target',
                        ring=ring_index, edge=edge_index, parameter=(first, last), point=p))
    boundary_passed = not witnesses
    samples = []
    if boundary_passed:
        for hole_index, raw in enumerate(target_polygon.interiors):
            hole = [_EXACT.point(p) for p in raw.coords]
            p = next(p for p in _slab_points([hole]) if _EXACT.inside([hole], p))
            if _EXACT.inside(target, p, target_index):
                raise ValueError('A target hole sample is not in its complement')
            covered = not _EXACT.inside(source, p, source_index)
            samples.append(dict(kind='target_hole_sample', hole=hole_index,
                                point=p, outside_source=covered))
            if not covered:
                witnesses.append(dict(kind='target_hole_inside_source', hole=hole_index, point=p))
    passed = not witnesses
    return _encoded(dict(schema='closed-ieee-polygon-inclusion-1',
        status='passed' if passed else 'refused', passed=passed,
        source_geometry_sha256=hashlib.sha256(source_polygon.wkb).hexdigest(),
        target_geometry_sha256=hashlib.sha256(target_polygon.wkb).hexdigest(),
        proof_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        exact_contact_kernel_sha256=_EXPECTED,
        arithmetic='Fraction of stored float64 coordinates; no intermediate encoding',
        validity_gate='GEOS valid nonempty Polygon pair; no overlay used by proof',
        boundary_intervals_checked=boundary_intervals,
        entire_source_boundary_covered=boundary_passed,
        bounded_target_complements_outside_source=(not any(not row['outside_source'] for row in samples)
                                                 if boundary_passed else None),
        complement_sampling='one_rational_interior_point_per_target_hole',
        complement_samples=samples, witnesses=witnesses))
