"""Remove a ring only when its complete certified convex hull is intended material.

The exterior must already be valid. Invalid/nonconvex holes may be retained
only if the final Polygon remains valid; no make_valid, buffer or epsilon is
used. Callers must still prove the final source inclusion and confinement.
"""
import hashlib
import importlib.util
from pathlib import Path

from shapely.geometry import MultiPoint, Polygon

_PATH = Path(__file__).with_name('exact_intended_holes.py')
_EXPECTED = 'bfcc3177f68b83c9c3139cb26e79d0633342caf04143565c2c80845cee403a7f'
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != _EXPECTED:
    raise ValueError('The frozen intended-hole proof helper changed')
_SPEC = importlib.util.spec_from_file_location('_intended_hole_v2_frozen', _PATH)
_OLD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_OLD)
_EXACT, _COVERAGE = _OLD._EXACT, _OLD._COVERAGE


def _hull_certificate(ring):
    vertices = [_EXACT.point(p) for p in list(ring.coords)[:-1]]
    hull = MultiPoint(list(ring.coords)[:-1]).convex_hull
    if hull.geom_type != 'Polygon' or not hull.is_valid:
        raise ValueError('The ring has no valid positive-area convex hull')
    points = [_EXACT.point(p) for p in list(hull.exterior.coords)[:-1]]
    if len(set(points)) != len(points) or len(points) < 3 or not set(points).issubset(set(vertices)):
        raise ValueError('Convex-hull vertices must be distinct original ring vertices')
    signed = sum(_EXACT.cross(a, b) for a, b in zip(points, points[1:]+points[:1]))
    if not signed:
        raise ValueError('The ring hull has zero exact area')
    side = 1 if signed > 0 else -1
    edges = list(zip(points, points[1:]+points[:1]))
    for collection in (points, vertices):
        if any(side*_EXACT.cross(_EXACT.difference(b, a), _EXACT.difference(p, a)) < 0
               for a, b in edges for p in collection):
            raise ValueError('A hull edge fails the exact closed convexity/ring coverage certificate')
    return hull, points, dict(hull_vertices_from_original_ring=True,
        closed_convexity_certified=True, all_ring_vertices_covered=True,
        all_ring_segments_covered=True, ring_segments_checked=len(vertices),
        segment_argument='Each endpoint satisfies every closed hull halfplane; each whole segment does so by linearity.',
        exact_hull_area_mm2=abs(signed)/2)


def normalize_holes(result, primitives, allowed):
    primitives = list(primitives)
    if result.geom_type != 'Polygon' or result.is_empty:
        raise ValueError('Hole normalization requires one nonempty Polygon')
    exterior = Polygon(result.exterior.coords)
    if exterior.is_empty or not exterior.is_valid:
        raise ValueError('The exterior must be valid before hole normalization')
    for p in result.exterior.coords:
        _EXACT.point(p)
    for geometry in [allowed, *primitives]:
        if geometry.geom_type != 'Polygon' or geometry.is_empty or not geometry.is_valid:
            raise ValueError('Intended primitives and allowed domain must be valid nonempty Polygons')
    if not primitives:
        raise ValueError('The intended primitive union must be explicit and nonempty')
    boundaries = [_EXACT.rings(p) for p in primitives]
    rows, removed, retained = [], [], []
    for index, ring in enumerate(result.interiors):
        row = dict(hole_index=index, ring_polygon_valid=Polygon(ring).is_valid,
                   ring_geometry_sha256=hashlib.sha256(Polygon(ring).wkb).hexdigest())
        try:
            hull, vertices, certificate = _hull_certificate(ring)
            allowed_proof = _COVERAGE.prove_polygon_covered(hull, allowed)
            union_proof = _OLD._union_certificate(vertices, boundaries)
            remove = allowed_proof['passed'] and union_proof['passed']
            row.update(status='removed_certified' if remove else 'retained_unproved_hull_coverage',
                removed=remove, hull_geometry_sha256=hashlib.sha256(hull.wkb).hexdigest(),
                hull_coordinates_mm=list(hull.exterior.coords), hull_certificate=certificate,
                allowed_coverage=allowed_proof, intended_union_coverage=union_proof)
        except ValueError as error:
            row.update(status='retained_no_hull_certificate', removed=False, reason=str(error))
        rows.append(row)
        (removed if row['removed'] else retained).append(index)
    candidate = (Polygon(result.exterior.coords, [ring.coords for i, ring in enumerate(result.interiors) if i in retained])
                 if removed else result)
    coordinates_unchanged = (list(candidate.exterior.coords) == list(result.exterior.coords) and
        [list(r.coords) for r in candidate.interiors] == [list(result.interiors[i].coords) for i in retained])
    if not coordinates_unchanged:
        raise ValueError('Hole normalization changed retained coordinates')
    receipt = _COVERAGE._encoded(dict(schema='exact-intended-hull-hole-normalization-v2',
        status='completed' if candidate.is_valid else 'refused',
        scope='Only complete ring hulls covered by intended primitives and allowed; no final material admission.',
        result_geometry_sha256=hashlib.sha256(result.wkb).hexdigest(),
        intended_primitive_geometry_sha256=[hashlib.sha256(p.wkb).hexdigest() for p in primitives],
        allowed_geometry_sha256=hashlib.sha256(allowed.wkb).hexdigest(),
        normalized_geometry_sha256=hashlib.sha256(candidate.wkb).hexdigest(),
        input_polygon_valid=result.is_valid, final_polygon_valid=candidate.is_valid,
        removed_holes=removed, retained_holes=retained, new_vertices=0,
        exterior_and_retained_holes_unchanged=coordinates_unchanged, frozen_helper_sha256=_EXPECTED,
        proof_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), holes=rows))
    if not candidate.is_valid:
        error = ValueError('Certified hole removal did not produce one valid Polygon')
        error.receipt = receipt
        raise error
    return candidate, receipt
