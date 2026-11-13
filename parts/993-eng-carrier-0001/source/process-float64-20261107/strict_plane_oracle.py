"""Qualified strict plane functions copied verbatim; caller supplies all data."""
import math

def canonical_point(vertices, edge, z):
    """Interpolate from the lower source vertex ID; no sign tolerance or snapping."""
    import numpy as np
    a, b = vertices[list(edge)]
    if not ((a[2] < z < b[2]) or (b[2] < z < a[2])):
        raise ValueError('Edge does not strictly cross the unchanged plane')
    t = (float(z) - float(a[2])) / (float(b[2]) - float(a[2]))
    point = np.array([float(a[j]) + t * (float(b[j]) - float(a[j]))
                      for j in range(2)], dtype=np.float64)
    if not np.isfinite(point).all():
        raise ValueError('Nonfinite intersection point')
    return point


def stitch_cycles(edge_points, directed_segments):
    """Require degree two and consistent directed cycles without any tolerance weld."""
    import numpy as np
    outgoing, incoming, used = {}, {}, set()
    for start, end in directed_segments:
        if start == end:
            raise ValueError('Zero-length source-edge segment')
        pair = tuple(sorted((start, end)))
        if pair in used:
            raise ValueError('Duplicate intersection segment')
        used.add(pair)
        a, b = edge_points[start], edge_points[end]
        if a.shape != (2,) or b.shape != (2,) or not np.isfinite([a, b]).all():
            raise ValueError('Nonfinite or invalid segment coordinates')
        if np.array_equal(a, b):
            raise ValueError('Zero-length intersection segment')
        if start in outgoing or end in incoming:
            raise ValueError('Open or branched intersection graph')
        outgoing[start] = end
        incoming[end] = start
    if set(outgoing) != set(incoming) or set(outgoing) != set(edge_points):
        raise ValueError('Open intersection graph or unused edge point')
    rings, ring_edges, areas, visited = [], [], [], set()
    for first in sorted(outgoing):
        if first in visited:
            continue
        current, keys = first, []
        while current not in visited:
            visited.add(current)
            keys.append(current)
            current = outgoing[current]
        if current != first or len(keys) < 3:
            raise ValueError('Open, merged or undersized intersection cycle')
        keys.append(first)
        ring = np.asarray([edge_points[key] for key in keys], dtype=np.float64)
        terms = [float(a[0]) * float(b[1]) - float(b[0]) * float(a[1])
                 for a, b in zip(ring[:-1], ring[1:])]
        area = math.fsum(terms) / 2
        if not math.isfinite(area) or area == 0:
            raise ValueError('Zero or nonfinite oriented ring area')
        rings.append(ring)
        ring_edges.append(np.asarray(keys, dtype=np.int64))
        areas.append(area)
    total = math.fsum(areas)
    if rings and total <= 0:
        raise ValueError('Nonpositive net oriented section area')
    return dict(rings=rings, ring_source_edges=ring_edges,
                ring_signed_areas_mm2=areas, signed_area_mm2=total,
                intersection_segments=len(used), intersection_source_edges=len(edge_points),
                exact_edge_id_cycles_closed=True, tolerance_welding_used=False)


def slice_rings(vertices, faces, z, chunk_size=65536):
    """Return float64 rings and source-edge cycles; reject exact vertex coplanarity.

    This strict geometric reference does not reproduce native tolerance snapping.
    Consumers must compare native vectors against these rings with unchanged
    coverage checks, and retain any resulting refusal.
    """
    import numpy as np
    vertices, faces = np.asarray(vertices), np.asarray(faces)
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or vertices.dtype.kind != 'f'
            or vertices.dtype.itemsize != 8 or faces.ndim != 2 or faces.shape[1] != 3
            or faces.dtype.kind not in 'iu' or not math.isfinite(float(z))):
        raise ValueError('Finite float64 vertices and integer triangle faces required')
    minimum = math.inf
    for begin in range(0, len(vertices), chunk_size):
        block = vertices[begin:begin + chunk_size]
        if not np.isfinite(block).all():
            raise ValueError('Nonfinite source vertex')
        distance = np.abs(block[:, 2] - z)
        if np.any(distance == 0):
            raise ValueError('Exact vertex coplanarity requires a separate oracle')
        if len(distance):
            minimum = min(minimum, float(distance.min()))
    points, segments = {}, []
    starts, ends = np.array([0, 1, 2]), np.array([1, 2, 0])
    for begin in range(0, len(faces), chunk_size):
        ids = faces[begin:begin + chunk_size]
        if np.any(ids >= len(vertices)) or (ids.dtype.kind == 'i' and np.any(ids < 0)):
            raise ValueError('Source face index outside vertex array')
        if np.any((ids[:, 0] == ids[:, 1]) | (ids[:, 1] == ids[:, 2]) | (ids[:, 2] == ids[:, 0])):
            raise ValueError('Repeated vertex ID in source face')
        q = vertices[ids]
        below = q[:, :, 2] < z
        active = np.any(below, axis=1) & ~np.all(below, axis=1)
        ids, below = ids[active], below[active]
        up = below[:, starts] & ~below[:, ends]
        down = ~below[:, starts] & below[:, ends]
        if not np.all(up.sum(1) == 1) or not np.all(down.sum(1) == 1):
            raise ValueError('Invalid strict triangle crossing classification')
        for row, incoming, outgoing in zip(ids, down.argmax(1), up.argmax(1)):
            edge_ids = []
            for local in (incoming, outgoing):
                key = tuple(sorted((int(row[starts[local]]), int(row[ends[local]]))))
                if key not in points:
                    points[key] = canonical_point(vertices, key, z)
                edge_ids.append(key)
            segments.append(tuple(edge_ids))
    result = stitch_cycles(points, segments)
    result.update(z_mm=float(z), minimum_vertex_plane_distance_mm=minimum,
                  exact_coplanar_vertices=0, source_vertices=len(vertices), source_faces=len(faces))
    return result
