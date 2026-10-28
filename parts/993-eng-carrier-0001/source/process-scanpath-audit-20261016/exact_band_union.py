"""Certify a sheet in the intended vertical band, before a rounded overlay.

Positive oriented triangle chains must equal the source boundary exactly. Their
winding numbers therefore partition the source without gaps or overlaps. Each
material triangle is then covered by a finite union of closed convex sweeps.
"""
from collections import Counter
from fractions import Fraction as Q
import hashlib
import importlib.util
import math
from pathlib import Path

import shapely
from shapely.geometry import MultiPoint, box

_PATH = Path(__file__).with_name('exact_intended_holes.py')
_EXPECTED = 'bfcc3177f68b83c9c3139cb26e79d0633342caf04143565c2c80845cee403a7f'
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != _EXPECTED:
    raise RuntimeError('The exact convex-union helper identity changed')
_SPEC = importlib.util.spec_from_file_location('_band_union_partition', _PATH)
_PARTITION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PARTITION)
_EXACT, _COVERAGE = _PARTITION._EXACT, _PARTITION._COVERAGE


def _signed_area(points):
    return sum(_EXACT.cross(a, b) for a, b in zip(points, points[1:]+points[:1]))/2


def _chain(rings):
    result = Counter()
    for points in rings:
        for a, b in zip(points, points[1:]+points[:1]):
            if a != b:
                result[tuple(sorted((a, b)))] += 1 if a < b else -1
    return {edge: count for edge, count in result.items() if count}


def _triangulation(polygon):
    if polygon.geom_type != 'Polygon' or polygon.is_empty or not polygon.is_valid:
        raise ValueError('An exact band proof requires valid nonempty Polygons')
    rings = [[_EXACT.point(p) for p in list(ring.coords)[:-1]]
             for ring in [polygon.exterior, *polygon.interiors]]
    for index, points in enumerate(rings):
        if (_signed_area(points) > 0) != (index == 0):
            points.reverse()
    triangles = []
    for triangle in shapely.get_parts(shapely.constrained_delaunay_triangles(polygon)):
        points = [_EXACT.point(p) for p in list(triangle.exterior.coords)[:-1]]
        if len(points) != 3 or not _signed_area(points):
            raise ValueError('The band triangulation has a non-triangle or exact zero face')
        if _signed_area(points) < 0:
            points.reverse()
        triangles.append(points)
    if not triangles or _chain(triangles) != _chain(rings):
        raise ValueError('The positive triangle chain differs from the exact source boundary')
    area = sum(_signed_area(ring) for ring in rings)
    if sum(_signed_area(t) for t in triangles) != area or area <= 0:
        raise ValueError('The exact triangle partition area differs from its source')
    return triangles, dict(triangles=len(triangles), exact_boundary_chain_identical=True,
                          exact_area_mm2=area, positive_oriented_triangles=True)


def _primitives(domain, penetration):
    triangles, partition = _triangulation(domain)
    result = []
    for triangle in triangles:
        # Retain the same rounded +/- penetration coordinates as the frozen
        # vertical_contact_band; only the subsequent overlay is avoided.
        shifted = [(float(p[0]), float(p[1])+sign*penetration)
                   for sign in (1, -1) for p in triangle]
        hull = MultiPoint(shifted).convex_hull
        points = [_EXACT.point(p) for p in list(hull.exterior.coords)[:-1]]
        if (not _PARTITION._convex(points) or
                not all(_EXACT.inside([points+[points[0]]], _EXACT.point(p)) for p in shifted) or
                not all(_EXACT.inside([points+[points[0]]], p) for p in triangle) or
                not set(points).issubset({_EXACT.point(p) for p in shifted})):
            raise ValueError('The proposed sweep is not the exact hull of its stored endpoints')
        points = _PARTITION._clip(points, (Q(0), Q(0)), (Q(1), Q(0)), 1)
        if len(points) >= 3 and _PARTITION._area(points) > 0:
            result.append(points)
    if not result:
        raise ValueError('The intended band has no positive area above the plate')
    return result, partition


def prove_band_covered(material, domain, penetration):
    """Return an exact receipt, without changing the material or domain."""
    if not math.isfinite(penetration) or penetration <= 0:
        raise ValueError('Positive finite penetration is required')
    triangles, material_partition = _triangulation(material)
    primitives, domain_partition = _primitives(domain, penetration)
    boxes = [box(math.nextafter(float(min(p[0] for p in points)), -math.inf),
                 math.nextafter(float(min(p[1] for p in points)), -math.inf),
                 math.nextafter(float(max(p[0] for p in points)), math.inf),
                 math.nextafter(float(max(p[1] for p in points)), math.inf))
             for points in primitives]
    tree = shapely.STRtree(boxes)
    rows = []
    for index, triangle in enumerate(triangles):
        extent = box(min(float(p[0]) for p in triangle), min(float(p[1]) for p in triangle),
                     max(float(p[0]) for p in triangle), max(float(p[1]) for p in triangle))
        candidates = sorted(int(i) for i in tree.query(extent))
        boundaries = [[primitives[i]+[primitives[i][0]]] for i in candidates]
        containing = next((i for i, rings in zip(candidates, boundaries)
                           if all(_EXACT.inside(rings, p) for p in triangle)), None)
        if containing is not None:
            proof = dict(passed=True, method='all_vertices_in_one_closed_convex_primitive',
                         primitive_id=containing)
        else:
            proof = _PARTITION._union_certificate(triangle, boundaries)
            proof['candidate_primitive_ids'] = candidates
        rows.append(dict(triangle=index, receipt=proof))
    passed = all(row['receipt']['passed'] for row in rows)
    encoded = _COVERAGE._encoded
    primitive_hash = hashlib.sha256(repr(primitives).encode()).hexdigest()
    return encoded(dict(schema='exact-intended-vertical-band-union-1',
        status='passed' if passed else 'refused', passed=passed,
        source_geometry_sha256=hashlib.sha256(material.wkb).hexdigest(),
        free_domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
        penetration_mm=penetration, plate_Z_mm=0.,
        proof_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        exact_convex_union_source_sha256=_EXPECTED,
        intended_convex_primitives=len(primitives), primitives_sha256=primitive_hash,
        material_triangulation=material_partition, domain_triangulation=domain_partition,
        arithmetic='Fraction of stored IEEE endpoints; plate half-plane clipped rationally',
        closure_argument='Positive oriented triangle chains equal the complete source boundary. Winding numbers partition the Polygon. Each triangle is covered by a finite closed convex union, including its boundaries.',
        polygon_overlay_operations=0, new_material_vertices=0, triangles=rows))
