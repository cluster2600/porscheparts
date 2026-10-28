"""Certify a triangle covered by a closed convex union using exact subtraction."""
from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path

_PATH = Path(__file__).with_name('exact_intended_holes.py')
_EXPECTED = 'bfcc3177f68b83c9c3139cb26e79d0633342caf04143565c2c80845cee403a7f'
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != _EXPECTED:
    raise RuntimeError('The exact convex clip helper changed')
_SPEC = importlib.util.spec_from_file_location('_convex_union_clip', _PATH)
_CLIP = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CLIP)
_EXACT = _CLIP._EXACT


def _orientation(points):
    if (len(points) < 3 or any(len(p) != 2 for p in points) or len(set(points)) != len(points) or
            any(not isinstance(c, Q) for point in points for c in point)):
        raise ValueError('Distinct convex polygon vertices must be exact Fractions')
    area = sum(_EXACT.cross(a, b) for a, b in zip(points, points[1:]+points[:1]))
    if not area:
        raise ValueError('A convex polygon must have positive exact area')
    side = 1 if area > 0 else -1
    if any(side*_EXACT.cross(_EXACT.difference(b, a), _EXACT.difference(p, a)) < 0
           for a, b in zip(points, points[1:]+points[:1]) for p in points):
        raise ValueError('A primitive is not a convex boundary in cyclic order')
    return side


def _subtract(piece, primitive, side):
    current, outside = piece, []
    for a, b in zip(primitive, primitive[1:]+primitive[:1]):
        part = _CLIP._clip(current, a, b, -side)
        if len(part) >= 3 and _CLIP._area(part) > 0:
            outside.append(part)
        current = _CLIP._clip(current, a, b, side)
        if len(current) < 3 or _CLIP._area(current) == 0:
            current = []
            break
    inside_area = _CLIP._area(current) if current else Q(0)
    if sum(_CLIP._area(p) for p in outside)+inside_area != _CLIP._area(piece):
        raise ValueError('Exact convex subtraction did not conserve area')
    return outside, inside_area


def union_certificate(triangle_fraction, primitives_fraction):
    """Return Fraction-valued coverage evidence; never encode intermediate points."""
    triangle, primitives = list(triangle_fraction), [list(p) for p in primitives_fraction]
    if len(triangle) != 3:
        raise ValueError('The source must be one exact positive-area triangle')
    _orientation(triangle)
    sides = [_orientation(p) for p in primitives]
    source_area = _CLIP._area(triangle)
    remaining, removed, steps = [triangle], Q(0), []
    for index, (primitive, side) in enumerate(zip(primitives, sides)):
        next_pieces, delta = [], Q(0)
        for piece in remaining:
            outside, inside_area = _subtract(piece, primitive, side)
            next_pieces.extend(outside)
            delta += inside_area
        remaining, removed = next_pieces, removed+delta
        left = sum((_CLIP._area(p) for p in remaining), Q(0))
        if removed+left != source_area:
            raise ValueError('The complete exact union subtraction lost area')
        steps.append(dict(primitive_id=index, exact_removed_area_mm2=delta,
                          exact_remaining_area_mm2=left, remaining_convex_pieces=len(remaining)))
        if not remaining:
            break
    witnesses = []
    for piece in remaining:
        point = tuple(sum(p[k] for p in piece)/len(piece) for k in (0, 1))
        if any(_EXACT.inside([p+[p[0]]], point) for p in primitives):
            raise ValueError('An alleged uncovered cell lies in a covered primitive')
        witnesses.append(dict(vertices=piece, interior_sample=point, exact_area_mm2=_CLIP._area(piece)))
    return dict(passed=not remaining, method='exact_successive_convex_subtraction',
        exact_source_area_mm2=source_area, exact_removed_area_mm2=removed,
        exact_remaining_area_mm2=source_area-removed, exact_area_conserved=True,
        closed_union_argument='Every positive source cell is covered. The finite primitive union is closed; closure also covers all source boundary points.',
        primitive_count=len(primitives), steps=steps, uncovered_cells=witnesses)
