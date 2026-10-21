"""Construct a continuous sheet from its boundary without polygon overlays.

This is a conservative prototype. A vertical strip is added only on an entire
boundary edge covered by attested source segments. Partial edges are reported,
never rounded into a new intersection. Positive triangle chains certify the
assembled surface; the independent intended-band proof remains mandatory.
"""
from fractions import Fraction as Q
import hashlib
import importlib.util
import math
from pathlib import Path

import shapely
from shapely.geometry import Polygon

_AUDIT = Path(__file__).resolve().parent
if not (_AUDIT / 'exact_band_union.py').is_file():
    _AUDIT = _AUDIT.parent / 'process-scanpath-audit-20261016'
BAND_SOURCE_SHA256 = '760a34fcfeb2de640864b91837dc797e3579da2b255ac5b07575c74b2154d44e'
if hashlib.sha256((_AUDIT / 'exact_band_union.py').read_bytes()).hexdigest() != BAND_SOURCE_SHA256:
    raise ValueError('The original intended-band source identity changed')
_SPEC = importlib.util.spec_from_file_location('_combinatorial_band', _AUDIT / 'exact_band_union.py')
_BAND = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BAND)
_EXACT = _BAND._EXACT


def _coverage(a, b, paths):
    """Exact parameters covered by collinear attested segments on edge AB."""
    delta = _EXACT.difference(b, a)
    axis = 0 if delta[0] else 1
    intervals = []
    for path_index, path in enumerate(paths):
        points = [_EXACT.point(p) for p in path]
        for segment_index, (c, d) in enumerate(zip(points[:-1], points[1:])):
            if c == d:
                raise ValueError('Zero attested source segment')
            if (_EXACT.cross(delta, _EXACT.difference(c, a)) or
                    _EXACT.cross(delta, _EXACT.difference(d, a))):
                continue
            first, last = sorted(((p[axis] - a[axis]) / delta[axis] for p in (c, d)))
            first, last = max(Q(0), first), min(Q(1), last)
            if first < last:
                intervals.append((first, last, path_index, segment_index))
    end = Q(0)
    for first, last, _, _ in sorted(intervals):
        if first > end:
            break
        end = max(end, last)
    return end == 1, intervals


def _atomic_chain(triangles):
    """Cancel whole or subdivided collinear edges at existing endpoints only."""
    lines = {}
    for ring in triangles:
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a == b:
                continue
            dx, dy = b[0] - a[0], b[1] - a[1]
            coefficients = (dy, -dx, dx*a[1] - dy*a[0])
            scale = next(c for c in coefficients if c)
            line = tuple(c / scale for c in coefficients)
            lines.setdefault(line, []).append((a, b))
    chain = {}
    for edges in lines.values():
        axis = 0 if edges[0][0][0] != edges[0][1][0] else 1
        points = {p[axis]: p for edge in edges for p in edge}
        events = {}
        for a, b in edges:
            low, high = sorted((a[axis], b[axis]))
            sign = 1 if b[axis] > a[axis] else -1
            events[low] = events.get(low, 0) + sign
            events[high] = events.get(high, 0) - sign
        ordered = sorted(points)
        multiplicity = 0
        for low, high in zip(ordered[:-1], ordered[1:]):
            multiplicity += events.get(low, 0)
            if multiplicity:
                a, b = points[low], points[high]
                if a > b:
                    a, b = b, a
                    count = -multiplicity
                else:
                    count = multiplicity
                chain[(a, b)] = count
    return chain


def _cycles(chain):
    outgoing, incoming = {}, {}
    for (a, b), count in chain.items():
        if abs(count) != 1:
            raise ValueError('The boundary has repeated positive multiplicity')
        if count < 0:
            a, b = b, a
        if a in outgoing or b in incoming:
            raise ValueError('The boundary has a branch or a point contact')
        outgoing[a], incoming[b] = b, a
    if set(outgoing) != set(incoming):
        raise ValueError('The boundary has an open endpoint')
    unused = set(outgoing)
    result = []
    while unused:
        first = min(unused)
        ring, current = [], first
        while current in unused:
            ring.append(current)
            unused.remove(current)
            current = outgoing[current]
        if current != first:
            raise ValueError('Boundary cycles unexpectedly meet')
        result.append(ring)
    return result


def _assemble(triangles):
    boundary = _atomic_chain(triangles)
    generated = _cycles(boundary)
    outers = [ring for ring in generated if _BAND._signed_area(ring) > 0]
    holes = [ring for ring in generated if _BAND._signed_area(ring) < 0]
    if len(outers) != 1 or len(outers) + len(holes) != len(generated):
        raise ValueError('The boundary does not describe one positive sheet')
    generated = [outers[0], *holes]
    result = Polygon([[float(c) for c in p] for p in generated[0]],
                     [[[float(c) for c in p] for p in ring] for ring in generated[1:]])
    chain_equal = boundary == _atomic_chain(generated)
    area = sum(_BAND._signed_area(t) for t in triangles)
    exact_ring_area = sum(_BAND._signed_area(ring) for ring in generated)
    if (not result.is_valid or result.is_empty or not chain_equal or area != exact_ring_area or
            any(p[1] < 0 for ring in generated for p in ring)):
        error = ValueError('The assembled positive triangle chain is not one valid sheet')
        error.receipt = _BAND._COVERAGE._encoded(dict(valid=result.is_valid,
            explain_validity=shapely.is_valid_reason(result), chain_equal=chain_equal,
            area_equal=area == exact_ring_area,
            below_plate=any(p[1] < 0 for ring in generated for p in ring), result_wkb_hex=result.wkb_hex))
        raise error
    return result, area


def _exact_boundary_check(polygon):
    if polygon.geom_type != 'Polygon' or polygon.is_empty:
        raise ValueError('Exact boundary simplicity requires a nonempty Polygon')
    boundaries = [[_EXACT.point(p) for p in ring.coords]
                  for ring in [polygon.exterior, *polygon.interiors]]
    records = [(ri, i, a, b) for ri, ring in enumerate(boundaries)
               for i, (a, b) in enumerate(zip(ring[:-1], ring[1:]))]
    index = shapely.STRtree([shapely.LineString([[float(c) for c in p] for p in (a, b)])
                            for _, _, a, b in records])
    checked = 0
    for first, (ri, ei, a, b) in enumerate(records):
        bounds = shapely.box(min(float(a[0]), float(b[0])), min(float(a[1]), float(b[1])),
                             max(float(a[0]), float(b[0])), max(float(a[1]), float(b[1])))
        for second in index.query(bounds):
            if second <= first:
                continue
            rj, ej, c, d = records[second]
            checked += 1
            shared = set((a, b)).intersection((c, d))
            adjacent = ri == rj and ((ei-ej) % (len(boundaries[ri])-1) in (1, len(boundaries[ri])-2))
            allowed = shared if adjacent else set()
            r, s = _EXACT.difference(b, a), _EXACT.difference(d, c)
            denominator = _EXACT.cross(r, s)
            if denominator:
                t = _EXACT.cross(_EXACT.difference(c, a), s) / denominator
                u = _EXACT.cross(_EXACT.difference(c, a), r) / denominator
                if 0 <= t <= 1 and 0 <= u <= 1:
                    p = tuple(a[k]+t*r[k] for k in (0, 1))
                    if p not in allowed:
                        raise ValueError('Exact boundary edges cross or meet outside a shared adjacent vertex')
            elif not _EXACT.cross(_EXACT.difference(c, a), r):
                axis = 0 if r[0] else 1
                low = max(min(a[axis], b[axis]), min(c[axis], d[axis]))
                high = min(max(a[axis], b[axis]), max(c[axis], d[axis]))
                if low < high:
                    raise ValueError('Exact boundary edges overlap along a positive interval')
                if low == high:
                    t = (low-a[axis])/r[axis]
                    p = tuple(a[k]+t*r[k] for k in (0, 1))
                    if p not in allowed:
                        raise ValueError('Exact boundary edges have a forbidden point contact')
    outer, holes = boundaries[0], boundaries[1:]
    for i, hole in enumerate(holes):
        if not _EXACT.inside([outer], hole[0]):
            raise ValueError('A hole is outside the outer boundary')
        for j, other in enumerate(holes):
            if i != j and _EXACT.inside([other], hole[0]):
                raise ValueError('Boundary holes are nested')
    return dict(status='passed', arithmetic='Fraction of stored IEEE endpoints',
                checked_edge_pairs=checked, boundary_edges=len(records),
                adjacent_edges_meet_only_at_shared_vertex=True,
                all_other_edge_intersections_empty=True, holes_inside_outer_and_not_nested=True)


def construct(domain, interfaces, penetration):
    """Return (Polygon, receipt), with no overlay and no new XY coordinate."""
    if (domain.geom_type != 'Polygon' or domain.is_empty or not domain.is_valid or
            not math.isfinite(penetration) or penetration <= 0):
        raise ValueError('A valid Polygon and positive finite penetration are required')
    if set(interfaces) != {'upper', 'lower'}:
        raise ValueError('Attested upper and lower interfaces are required')
    triangles, partition = _BAND._triangulation(domain)
    rings = [[_EXACT.point(p) for p in list(ring.coords)[:-1]]
             for ring in [domain.exterior, *domain.interiors]]
    for index, ring in enumerate(rings):
        if (_BAND._signed_area(ring) > 0) != (index == 0):
            ring.reverse()
    edge_rows = []
    all_triangles = list(triangles)
    for ring_index, ring in enumerate(rings):
        kinds = []
        for edge_index, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
            matches = {name: _coverage(a, b, paths) for name, paths in interfaces.items()}
            dx = b[0] - a[0]
            kind = 0
            if dx:
                upper, lower = matches['upper'][0], matches['lower'][0]
                if upper and lower:
                    raise ValueError('One boundary edge has contradictory interface roles')
                if upper:
                    if dx >= 0:
                        raise ValueError('An upper interface points toward the material interior')
                    kind = 1
                elif lower:
                    if dx <= 0:
                        raise ValueError('A lower interface points toward the material interior')
                    if not (a[1] == b[1] == 0):
                        if min(a[1], b[1]) <= Q(penetration):
                            raise ValueError('A lower strip would need a new plate intersection')
                        kind = -1
            kinds.append(kind)
            edge_rows.append(dict(ring=ring_index, edge=edge_index, direction=kind,
                source_edge=[a,b],
                whole_edge_attested={name: value[0] for name, value in matches.items()},
                exact_coverage_parameters={name: value[1] for name, value in matches.items()}))
            if kind:
                aa = (a[0], Q(float(a[1]) + kind * penetration))
                bb = (b[0], Q(float(b[1]) + kind * penetration))
                additions = []
                for tri in ([a, aa, bb], [a, bb, b]):
                    area = _BAND._signed_area(tri)
                    if area < 0:
                        raise ValueError('An added strip has negative orientation')
                    if area:
                        additions.append(tri)
                edge_rows[-1]['proposed_strip_exact_area_mm2'] = sum(_BAND._signed_area(t) for t in additions)
                try:
                    _assemble(all_triangles + additions)
                except ValueError as exc:
                    edge_rows[-1]['strip_status'] = 'excluded_would_not_form_simple_positive_sheet'
                    edge_rows[-1]['exclusion_receipt'] = getattr(exc, 'receipt', dict(error=str(exc)))
                else:
                    all_triangles.extend(additions)
                    edge_rows[-1]['strip_status'] = 'included'
    result, area = _assemble(all_triangles)
    simplicity = _exact_boundary_check(result)
    inclusion = _BAND._COVERAGE.prove_polygon_covered(domain, result)
    if not inclusion['passed']:
        raise ValueError('The assembled sheet lost source material')
    return result, _BAND._COVERAGE._encoded(dict(schema='combinatorial-continuous-interfaces-prototype-1',
        status='constructed_not_admitted', domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
        result_geometry_sha256=hashlib.sha256(result.wkb).hexdigest(), penetration_mm=penetration,
        polygon_overlay_operations=0, exact_positive_triangle_boundary_chain_equal=True,
        edge_subdivision='Exact collinear endpoints already present in source triangles or vertical strips',
        rational_boundary_simplicity=simplicity,
        exact_triangle_area_mm2=area, source_partition=partition, generated_triangles=len(all_triangles),
        added_triangles=len(all_triangles)-len(triangles), whole_edge_interfaces=edge_rows,
        included_strips=sum(row.get('strip_status') == 'included' for row in edge_rows),
        explicitly_excluded_strips=sum(row.get('strip_status','').startswith('excluded') for row in edge_rows),
        partially_attested_edges_not_extended=sum(not any(row['whole_edge_attested'].values()) and
            any(row['exact_coverage_parameters'].values()) for row in edge_rows),
        source_domain_coverage=inclusion,
        partial_source_edges_extended=False, intended_band_proof_required=True))
