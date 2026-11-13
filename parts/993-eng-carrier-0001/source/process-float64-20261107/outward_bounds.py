"""Finite binary64 interval bounds for an admitted oriented mesh and strict sections.

Each primitive uses separate NumPy binary64 operations followed by outward
nextafter. Inputs are exact binary64 values. Overflow, nonfinite bounds and a
divisor interval containing zero refuse certification. Pairwise sums propagate
intervals explicitly; neither np.sum nor math.fsum is assumed exact.

Topology, source identity and closed consistent orientation are separate required
admissions. The area theorem applies to their actual finite-coordinate polyhedron.
"""
from fractions import Fraction as Q
import math
import numpy as np


def point(value):
    a = np.asarray(value, dtype=np.float64)
    if not np.isfinite(a).all():
        raise ValueError('Interval input must be finite binary64')
    return a, a


def interval(lower, upper):
    lo, hi = np.asarray(lower, dtype=np.float64), np.asarray(upper, dtype=np.float64)
    if lo.shape != hi.shape or not np.isfinite(lo).all() or not np.isfinite(hi).all() or np.any(lo > hi):
        raise ValueError('Invalid finite ordered interval')
    return lo, hi


def outward(lo, hi):
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        lower = np.nextafter(np.asarray(lo, dtype=np.float64), -np.inf)
        upper = np.nextafter(np.asarray(hi, dtype=np.float64), np.inf)
    return interval(lower, upper)


def add(a, b):
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        return outward(a[0] + b[0], a[1] + b[1])


def sub(a, b):
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        return outward(a[0] - b[1], a[1] - b[0])


def mul(a, b):
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        products = [a[i] * b[j] for i in (0, 1) for j in (0, 1)]
    return outward(np.minimum.reduce(products), np.maximum.reduce(products))


def div(a, b):
    if np.any((b[0] <= 0) & (b[1] >= 0)):
        raise ValueError('Divisor interval contains zero')
    with np.errstate(over='ignore', invalid='ignore', under='ignore', divide='ignore'):
        quotients = [a[i] / b[j] for i in (0, 1) for j in (0, 1)]
    return outward(np.minimum.reduce(quotients), np.maximum.reduce(quotients))


def absolute(a):
    lo, hi = a
    lower = np.where(lo >= 0, lo, np.where(hi <= 0, -hi, 0.0))
    return interval(lower, np.maximum(np.abs(lo), np.abs(hi)))


def pair_sum(a):
    lo, hi = (np.asarray(x, dtype=np.float64).reshape(-1) for x in a)
    interval(lo, hi)
    if not len(lo):
        return point(0.0)
    while len(lo) > 1:
        n = len(lo) // 2 * 2
        lower, upper = add((lo[:n:2], hi[:n:2]), (lo[1:n:2], hi[1:n:2]))
        if n < len(lo):
            lower, upper = np.append(lower, lo[-1]), np.append(upper, hi[-1])
        lo, hi = lower, upper
    return interval(lo[0], hi[0])


def cross(a, b):
    lo, hi = [], []
    for j, k in ((1, 2), (2, 0), (0, 1)):
        value = sub(mul((a[0][..., j], a[1][..., j]), (b[0][..., k], b[1][..., k])),
                    mul((a[0][..., k], a[1][..., k]), (b[0][..., j], b[1][..., j])))
        lo.append(value[0]); hi.append(value[1])
    return np.stack(lo, axis=-1), np.stack(hi, axis=-1)


def packed(a):
    lo, hi = interval(*a)
    if lo.ndim or hi.ndim:
        raise ValueError('Receipt intervals must be scalar')
    return [float(lo), float(hi)]


def rational_interval(value):
    value = Q(value)
    rounded = float(value)
    if not math.isfinite(rounded):
        raise ValueError('Rational constant does not have finite enclosure')
    lo = rounded if Q(rounded) <= value else float(np.nextafter(rounded, -np.inf))
    hi = rounded if Q(rounded) >= value else float(np.nextafter(rounded, np.inf))
    return interval(lo, hi)


def validate_vertices(vertices):
    v = np.asarray(vertices)
    if v.ndim != 2 or v.shape[1] != 3 or v.dtype != np.float64 or not len(v) or not np.isfinite(v).all():
        raise ValueError('Finite nonempty Nx3 float64 vertices required')
    return v


def mesh_bounds(vertices, faces, chunk_size=16384):
    """Enclose signed volume and integral |normal_z| dS, in mm units.

    Uses one exact input vertex as the reference origin. Every subtraction of
    that origin is interval arithmetic; this is not an exact-transform claim.
    Closed, consistent orientation must be established by the caller upstream.
    """
    v, f = validate_vertices(vertices), np.asarray(faces)
    if f.ndim != 2 or f.shape[1] != 3 or f.dtype.kind not in 'iu' or not len(f):
        raise ValueError('Nonempty integer triangle faces required')
    if type(chunk_size) is not int or not 1 <= chunk_size <= 65536:
        raise ValueError('Finite mesh chunk size must be 1..65536')
    origin = point(v[0])
    volumes, projected = [], []
    for begin in range(0, len(f), chunk_size):
        ids = f[begin:begin + chunk_size]
        if np.any(ids >= len(v)) or (ids.dtype.kind == 'i' and np.any(ids < 0)):
            raise ValueError('Triangle index outside vertex array')
        a, b, c = [point(v[ids[:, k]]) for k in range(3)]
        aa, bb, cc = sub(a, origin), sub(b, origin), sub(c, origin)
        products = mul(aa, cross(bb, cc))
        volumes.append(div(pair_sum(products), point(6.0)))
        normal = cross(sub(b, a), sub(c, a))
        projected.append(mul(pair_sum(absolute((normal[0][:, 2], normal[1][:, 2]))), point(0.5)))
    def aggregate(values):
        return pair_sum((np.asarray([x[0] for x in values]), np.asarray([x[1] for x in values])))
    return dict(signed_volume_mm3=packed(aggregate(volumes)),
                projected_surface_z_mm2=packed(aggregate(projected)),
                z_support_mm=[float(v[:, 2].min()), float(v[:, 2].max())],
                reference_origin_mm=v[0].tolist(), source_vertices=len(v), source_faces=len(f),
                requires_closed_oriented_surface_admission=True,
                arithmetic='finite outward binary64 primitives and deterministic pairwise interval sums')


def edge_points_bounds(vertices, edges, z):
    """Enclose the oracle's canonical lower-source-ID strict intersections."""
    v, ids = np.asarray(vertices), np.asarray(edges)
    if v.ndim != 2 or v.shape[1] != 3 or v.dtype != np.float64:
        raise ValueError('Nx3 float64 vertices required')
    if ids.ndim != 2 or ids.shape[1] != 2 or ids.dtype.kind not in 'iu':
        raise ValueError('Integer Nx2 source edges required')
    if np.any(ids[:, 0] >= ids[:, 1]) or np.any(ids >= len(v)) or np.any(ids < 0):
        raise ValueError('Canonical valid undirected source edge IDs required')
    a, b = v[ids[:, 0]], v[ids[:, 1]]
    if not np.isfinite(a).all() or not np.isfinite(b).all() or not math.isfinite(float(z)):
        raise ValueError('Finite edge coordinates and plane required')
    if not np.all(((a[:, 2] < z) & (z < b[:, 2])) | ((b[:, 2] < z) & (z < a[:, 2]))):
        raise ValueError('Every source edge must strictly cross the unchanged plane')
    t = div(sub(point(z), point(a[:, 2])), sub(point(b[:, 2]), point(a[:, 2])))
    t = t[0][:, None], t[1][:, None]
    return add(point(a[:, :2]), mul(t, sub(point(b[:, :2]), point(a[:, :2]))))


def section_area_bounds(vertices, ring_source_edges, z, reported_area=None):
    """Enclose every oriented ring, including negative hole rings; empty is zero.

    Edge-ID cycles must come from the separately admitted strict oracle. This
    arithmetic check does not infer, repair or invent the topology.
    """
    rings, seen = [], set()
    for cycle in ring_source_edges:
        ids = np.asarray(cycle)
        if ids.ndim != 2 or ids.shape[1] != 2 or len(ids) < 4 or not np.array_equal(ids[0], ids[-1]):
            raise ValueError('Explicit closed source-edge cycle required')
        keys = [tuple(map(int, row)) for row in ids[:-1]]
        if len(set(keys)) != len(keys) or seen.intersection(keys):
            raise ValueError('Repeated source edge in section cycles')
        seen.update(keys)
        xy = edge_points_bounds(vertices, ids, z)
        # Translating by an enclosed endpoint reduces cancellation; its entire
        # uncertainty is propagated rather than silently treating it as exact.
        shifted = sub(xy, (xy[0][0], xy[1][0]))
        a = shifted[0][:-1], shifted[1][:-1]
        b = shifted[0][1:], shifted[1][1:]
        terms = sub(mul((a[0][:, 0], a[1][:, 0]), (b[0][:, 1], b[1][:, 1])),
                    mul((a[0][:, 1], a[1][:, 1]), (b[0][:, 0], b[1][:, 0])))
        rings.append(mul(pair_sum(terms), point(0.5)))
    total = point(0.0) if not rings else pair_sum((np.array([r[0] for r in rings]), np.array([r[1] for r in rings])))
    result = dict(area_mm2=packed(total), ring_signed_areas_mm2=[packed(r) for r in rings],
                  ring_count=len(rings), intersection_source_edges=len(seen), empty=not rings,
                  zero_plane_shift=True, source_edge_interpolation='canonical lower vertex ID; strict sign')
    if reported_area is not None:
        result['reported_oracle_area_mm2'] = float(reported_area)
        result['reported_oracle_roundoff_error_mm2'] = packed(absolute(sub(point(reported_area), total)))
    return result


def calendar_bound(h, indices, published_z, mesh_interval, oracle_intervals, native_areas, oracle_areas):
    """Enclose full-calendar sums and the tagged-partition BV volume inequality.

    A closed oriented polyhedral solid has cross-section A with TV(A)<=Sz,
    where Sz=sum_faces(area*abs(nz)). For a cell of width h and any interior
    tag z, |h*A(z)-integral_cell(A)|<=max(z-left,right-z)*TV_cell(A).
    Summing disjoint cells covering the solid yields (h/2+delta)*Sz. This
    bounds the total quadrature error directly, NOT the difference between
    perturbed and exact-midpoint sums. All constants and sums are enclosed.
    """
    hq = Q(float(h))
    n = len(indices)
    if hq <= 0 or not n or list(indices) != list(range(n)):
        raise ValueError('Positive finite h and every unique exact calendar index required')
    if any(len(values) != n for values in (published_z, oracle_intervals, native_areas, oracle_areas)):
        raise ValueError('Every calendar index requires all four values')
    zs = [Q(float(z)) for z in published_z]
    if any(not k * hq < z < (k + 1) * hq for k, z in enumerate(zs)):
        raise ValueError('Every actual plane must remain strictly inside its calendar cell')
    zmin, zmax = map(lambda x: Q(float(x)), mesh_interval['z_support_mm'])
    if not Q(0) <= zmin <= zmax <= n * hq:
        raise ValueError('Calendar cells do not cover the entire admitted mesh support')
    delta = max(abs(z - hq * Q(2 * k + 1, 2)) for k, z in enumerate(zs))
    volume = interval(*mesh_interval['signed_volume_mm3'])
    sz = interval(*mesh_interval['projected_surface_z_mm2'])
    if volume[0] <= 0 or sz[0] < 0:
        raise ValueError('Positive signed volume and nonnegative projected surface interval required')
    areas = np.asarray(oracle_intervals, dtype=np.float64)
    if areas.shape != (n, 2):
        raise ValueError('Nx2 oracle area intervals required')
    area_interval = interval(areas[:, 0], areas[:, 1])
    if np.any(area_interval[0] < 0):
        raise ValueError('Nonnegative net section areas must be certified')
    native, observed = point(native_areas), point(oracle_areas)
    if np.any(native[0] < 0) or np.any(observed[0] < 0):
        raise ValueError('Nonnegative observed native and oracle areas required')
    height = point(float(h))
    exact_sections = mul(height, pair_sum(area_interval))
    native_sum = mul(height, pair_sum(native))
    oracle_sum = mul(height, pair_sum(observed))
    discrepancy = mul(height, pair_sum(absolute(sub(native, observed))))
    native_to_true_sections = mul(height, pair_sum(absolute(sub(native, area_interval))))
    oracle_roundoff = mul(height, pair_sum(absolute(sub(observed, area_interval))))
    tagged = mul(rational_interval(hq / 2 + delta), sz)
    oracle_residual = absolute(sub(exact_sections, volume))
    native_residual = absolute(sub(native_sum, volume))
    native_allowance = add(tagged, native_to_true_sections)
    return dict(status='full_calendar_outward_volume_assessment', full_calendar_indices=n,
                h_exact_fraction=str(hq), delta_exact_fraction=str(delta), delta_mm=packed(rational_interval(delta)),
                tag_distance_bound_mm=packed(rational_interval(hq / 2 + delta)),
                calendar_covers_source_support=True, all_actual_planes_inside_their_cells=True,
                signed_closed_volume_mm3=packed(volume), projected_surface_z_mm2=packed(sz),
                exact_section_quadrature_mm3=packed(exact_sections), native_area_quadrature_mm3=packed(native_sum),
                reported_oracle_quadrature_mm3=packed(oracle_sum),
                measured_native_oracle_discrepancy_mm3=packed(discrepancy),
                native_true_section_discrepancy_mm3=packed(native_to_true_sections),
                summed_oracle_area_roundoff_mm3=packed(oracle_roundoff),
                tagged_partition_allowance_mm3=packed(tagged),
                oracle_volume_residual_mm3=packed(oracle_residual), native_volume_residual_mm3=packed(native_residual),
                native_volume_allowance_mm3=packed(native_allowance),
                oracle_volume_bound_passed=bool(oracle_residual[1] <= tagged[1]),
                native_volume_bound_passed=bool(native_residual[1] <= native_allowance[1]),
                proof='TV(A)<=integral_surface_abs_normal_z; perturbed interior tag bound, not a midpoint-difference bound',
                floating_allowances_retained=True, numerical_area_tolerances_changed=False)
