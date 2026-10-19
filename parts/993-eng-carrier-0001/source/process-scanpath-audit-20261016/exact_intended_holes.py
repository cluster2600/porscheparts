"""Normalize only convex holes already covered by the intended closed sets.

No overlay is used. A hole is partitioned by all primitive boundary supporting
lines, using rational coordinates. Every positive-area cell must belong to a
primitive, and the entire hole must belong to the allowed domain. Other holes
are retained. Existing exterior and retained hole coordinates stay unchanged.
"""
from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path

from shapely.geometry import Polygon

_PATH = Path(__file__).with_name('exact_polygon_coverage.py')
_EXPECTED = '0b1c7598a7358b9e9a384dd5b90dc66aa9e1ea53828033b6722477ec11409bed'
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != _EXPECTED:
    raise RuntimeError('The exact polygon inclusion helper identity changed')
_SPEC = importlib.util.spec_from_file_location('_intended_hole_coverage', _PATH)
_COVERAGE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_COVERAGE)
_EXACT = _COVERAGE._EXACT


def _area(points):
    return abs(sum(_EXACT.cross(a, b) for a, b in zip(points, points[1:]+points[:1])))/2


def _clip(points, a, b, side):
    direction = _EXACT.difference(b, a)
    result = []
    for first, last in zip(points, points[1:]+points[:1]):
        f = side*_EXACT.cross(direction, _EXACT.difference(first, a))
        last_side = side*_EXACT.cross(direction, _EXACT.difference(last, a))
        if f >= 0:
            result.append(first)
        if f < 0 < last_side or last_side < 0 < f:
            t = f/(f-last_side)
            result.append(tuple(first[k]+t*(last[k]-first[k]) for k in (0, 1)))
    clean = []
    for p in result:
        if not clean or clean[-1] != p:
            clean.append(p)
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()
    return clean


def _convex(points):
    turns = [_EXACT.cross(_EXACT.difference(b, a), _EXACT.difference(c, b))
             for a, b, c in zip(points, points[1:]+points[:1], points[2:]+points[:2])]
    return bool(turns) and (min(turns) >= 0 or max(turns) <= 0) and _area(points) > 0


def _union_certificate(vertices, boundaries):
    pieces = [vertices]
    for rings in boundaries:
        for ring in rings:
            for a, b in zip(ring[:-1], ring[1:]):
                if a == b:
                    continue
                split = []
                for points in pieces:
                    signs = [_EXACT.cross(_EXACT.difference(b, a), _EXACT.difference(p, a)) for p in points]
                    if min(signs) < 0 < max(signs):
                        for side in (-1, 1):
                            part = _clip(points, a, b, side)
                            if len(part) >= 3 and _area(part) > 0:
                                split.append(part)
                    else:
                        split.append(points)
                pieces = split
    cells = []
    for piece in pieces:
        point = tuple(sum(p[k] for p in piece)/len(piece) for k in (0, 1))
        covering = [i for i, rings in enumerate(boundaries) if _EXACT.inside(rings, point)]
        cells.append(dict(vertices=piece, exact_area_mm2=_area(piece),
                          interior_sample=point, covering_primitive_ids=covering))
    source_area = _area(vertices)
    area_sum = sum(cell['exact_area_mm2'] for cell in cells)
    if source_area != area_sum:
        raise ValueError('Exact convex partition did not preserve the entire hole area')
    passed = bool(cells) and all(cell['covering_primitive_ids'] for cell in cells)
    return dict(passed=passed, exact_hole_area_mm2=source_area,
                exact_partition_area_mm2=area_sum, exact_area_conserved=True, cells=cells)


def normalize_holes(result, primitives, allowed):
    """Return (candidate, receipt), retaining every hole without a full proof.

    The caller must still prove D subset candidate subset allowed afterwards.
    A completed normalization receipt is not a support admission.
    """
    primitives = list(primitives)
    for geometry in [result, allowed, *primitives]:
        if geometry.geom_type != 'Polygon' or geometry.is_empty or not geometry.is_valid:
            raise ValueError('Hole normalization requires valid nonempty Polygon inputs')
    if not primitives:
        raise ValueError('The intended primitive union must be explicit and nonempty')
    boundaries = [_EXACT.rings(primitive) for primitive in primitives]
    rows, removed, retained = [], [], []
    for index, ring in enumerate(result.interiors):
        vertices = [_EXACT.point(p) for p in list(ring.coords)[:-1]]
        row = dict(hole_index=index, hole_geometry_sha256=hashlib.sha256(Polygon(ring).wkb).hexdigest())
        if not _convex(vertices):
            row.update(status='retained_no_convex_certificate', removed=False,
                       intended_union_coverage=None, allowed_coverage=None)
        else:
            allowed_proof = _COVERAGE.prove_polygon_covered(Polygon(ring), allowed)
            union_proof = _union_certificate(vertices, boundaries)
            remove = allowed_proof['passed'] and union_proof['passed']
            row.update(status='removed_certified' if remove else 'retained_unproved_coverage',
                       removed=remove, intended_union_coverage=union_proof,
                       allowed_coverage=allowed_proof)
        rows.append(row)
        (removed if row['removed'] else retained).append(index)
    candidate = (Polygon(result.exterior.coords, [ring.coords for i, ring in enumerate(result.interiors) if i in retained])
                 if removed else result)
    if not candidate.is_valid or list(candidate.exterior.coords) != list(result.exterior.coords):
        raise ValueError('Hole normalization changed the exterior or validity')
    if [list(ring.coords) for ring in candidate.interiors] != [list(result.interiors[i].coords) for i in retained]:
        raise ValueError('Hole normalization changed retained coordinates')
    receipt = dict(schema='exact-intended-convex-hole-normalization-1', status='completed',
        scope='Only holes entirely covered by the intended primitive union and allowed domain; no support admission.',
        result_geometry_sha256=hashlib.sha256(result.wkb).hexdigest(),
        intended_primitive_geometry_sha256=[hashlib.sha256(p.wkb).hexdigest() for p in primitives],
        allowed_geometry_sha256=hashlib.sha256(allowed.wkb).hexdigest(),
        candidate_geometry_sha256=hashlib.sha256(candidate.wkb).hexdigest(),
        proof_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        exact_polygon_coverage_source_sha256=_EXPECTED,
        arithmetic='Fraction of stored IEEE coordinates; exact convex partition by all primitive boundary lines',
        closure_argument='Positive convex cells partition the complete hole. Membership is constant on each cell interior; the finite primitive union is closed, so it also contains all cell boundaries.',
        holes=rows, removed_hole_indices=removed, retained_hole_indices=retained,
        all_removed_holes_certified=all(row['intended_union_coverage']['passed'] and row['allowed_coverage']['passed']
                                       for row in rows if row['removed']),
        new_vertices_introduced=0, exterior_and_retained_coordinates_unchanged=True,
        polygon_overlay_operations=0)
    return candidate, _COVERAGE._encoded(receipt)
