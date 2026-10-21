"""Certify that degenerate IEEE triangles add no points to one surface group."""
from fractions import Fraction as Q
import hashlib
from pathlib import Path

import numpy as np


def subtract(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross2(a, b):
    return a[0]*b[1]-a[1]*b[0]


def ratio(value):
    return [str(value.numerator), str(value.denominator)]


def segment_triangle_interval(first, last, triangle):
    """Closed parameter interval in one nondegenerate triangle, or None.

    Inputs are exact 3D rational coordinates. A transverse intersection is a
    singleton; coplanar segments are clipped by all three closed half-planes.
    A degenerate candidate triangle contributes nothing to this certificate.
    """
    a, b, c = triangle
    normal = cross(subtract(b, a), subtract(c, a))
    if not any(normal):
        return None
    direction = subtract(last, first)
    distance = dot(normal, subtract(first, a))
    slope = dot(normal, direction)
    axis = next(i for i, value in enumerate(normal) if value)
    project = lambda point: tuple(value for i, value in enumerate(point) if i != axis)
    p, r = project(first), project(direction)
    t = [project(point) for point in triangle]
    orientation = cross2(subtract(t[1], t[0]), subtract(t[2], t[0]))
    sign = 1 if orientation > 0 else -1

    def inside(value):
        point = tuple(x+value*y for x, y in zip(p, r))
        return all(sign*cross2(subtract(v, u), subtract(point, u)) >= 0
                   for u, v in zip(t, t[1:]+t[:1]))

    if slope:
        value = -distance/slope
        return (value, value) if 0 <= value <= 1 and inside(value) else None
    if distance:
        return None
    lower, upper = Q(0), Q(1)
    for u, v in zip(t, t[1:]+t[:1]):
        edge = subtract(v, u)
        value = sign*cross2(edge, subtract(p, u))
        change = sign*cross2(edge, r)
        if not change:
            if value < 0:
                return None
        elif change > 0:
            lower = max(lower, -value/change)
        else:
            upper = min(upper, -value/change)
        if lower > upper:
            return None
    return lower, upper


def union_intervals(intervals):
    merged = []
    for lower, upper in sorted(intervals):
        if merged and lower <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], upper)
        else:
            merged.append([lower, upper])
    return merged


def certify_zero_face_coverage(vertices, faces, zero_face_indices):
    """Audit ONE group, using only its nonzero faces as covering material.

    Face indices in the returned witnesses are local to the supplied group.
    This function never removes a face or alters any coordinate. It certifies
    equality of the encoded surface point sets only, not intrinsic chart area,
    topology, connectivity, scanpaths, or manufacturing admission.
    """
    vertices, faces = np.asarray(vertices), np.asarray(faces)
    if (vertices.dtype != np.float64 or vertices.ndim != 2 or vertices.shape[1] not in (2, 3)
            or not np.isfinite(vertices).all() or faces.ndim != 2 or faces.shape[1] != 3
            or not np.issubdtype(faces.dtype, np.integer) or not len(faces)
            or faces.min() < 0 or faces.max() >= len(vertices)):
        raise ValueError('Finite float64 vertices and nonempty indexed triangles of one group are required')
    zero = list(zero_face_indices)
    if (any(not isinstance(i, (int, np.integer)) for i in zero) or len(set(zero)) != len(zero)
            or any(i < 0 or i >= len(faces) for i in zero)):
        raise ValueError('Unique in-range local degenerate face indices are required')
    zero = [int(i) for i in zero]
    xyz = vertices if vertices.shape[1] == 3 else np.column_stack([vertices, np.zeros(len(vertices))])
    triangles = xyz[faces]
    bounds = np.concatenate([triangles.min(axis=1), triangles.max(axis=1)], axis=1)
    exact = {}

    def triangle(index):
        result = []
        for vertex in faces[index]:
            key = int(vertex)
            if key not in exact:
                exact[key] = tuple(Q(float(c)) for c in xyz[key])
            result.append(exact[key])
        return tuple(result)

    rows = []
    omitted = set(zero)
    for index in zero:
        target = triangle(index)
        if any(cross(subtract(target[1], target[0]), subtract(target[2], target[0]))):
            raise ValueError('A requested degenerate face has positive exact area')
        varying = next((i for i in range(3) if len({p[i] for p in target}) > 1), None)
        first = min(target, key=lambda p: p[varying]) if varying is not None else target[0]
        last = max(target, key=lambda p: p[varying]) if varying is not None else target[0]
        candidates = np.flatnonzero(np.all(bounds[:, :3] <= bounds[index, 3:], axis=1)
                                    & np.all(bounds[:, 3:] >= bounds[index, :3], axis=1))
        intervals, witnesses = [], []
        for candidate in candidates:
            candidate = int(candidate)
            if candidate in omitted:
                continue
            interval = segment_triangle_interval(first, last, triangle(candidate))
            if interval is not None:
                intervals.append(interval)
                witnesses.append(dict(face_index=candidate,
                    closed_parameter_interval=[ratio(value) for value in interval]))
        union = union_intervals(intervals)
        covered = union == [[Q(0), Q(1)]]
        rows.append(dict(face_index=index, geometry='point' if varying is None else 'closed_segment',
            endpoints_exact_ratios=[[ratio(c) for c in point] for point in (first, last)],
            candidate_triangles=len(candidates)-sum(int(i) in omitted for i in candidates),
            nonzero_covering_triangle_intersections=witnesses,
            union_closed_parameter_intervals=[[ratio(value) for value in interval] for interval in union],
            entire_encoded_geometry_covered=covered))
    return dict(status='passed' if all(row['entire_encoded_geometry_covered'] for row in rows) else 'rejected',
        scope='Encoded IEEE surface point-set coverage within this supplied group only; no change to geometry or admission.',
        method='Exact rational segment/triangle intersections, closed half-plane clipping and full interval union; AABB candidates only.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_arrays_sha256=hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest(),
        faces=len(faces), degenerate_faces=len(zero),
        all_degenerate_face_geometry_covered=all(row['entire_encoded_geometry_covered'] for row in rows),
        per_face=rows)
