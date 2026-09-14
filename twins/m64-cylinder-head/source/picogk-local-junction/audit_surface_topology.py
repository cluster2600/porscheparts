#!/usr/bin/env python3
"""Read-only combinatorial audit of the three hash-bound 0.2 witness STL files.

Exact coordinate indexing and exact dyadic collinearity predicates; no face
deletion, repair, shell filtering or geometric-intersection qualification.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import tempfile
import time

import numpy as np

MAX_FACES = 150_000
MAX_VERTICES = 450_000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DisjointSet:
    def __init__(self, count):
        self.parents = list(range(count))
        self.ranks = [0] * count

    def find(self, value):
        while self.parents[value] != value:
            self.parents[value] = self.parents[self.parents[value]]
            value = self.parents[value]
        return value

    def union(self, first, second):
        first, second = self.find(first), self.find(second)
        if first == second:
            return
        if self.ranks[first] < self.ranks[second]:
            first, second = second, first
        self.parents[second] = first
        if self.ranks[first] == self.ranks[second]:
            self.ranks[first] += 1


def load_binary_stl(path):
    if not 84 < path.stat().st_size <= 84 + MAX_FACES * 50:
        raise ValueError('Binary STL exceeds bounded file size')
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError('Binary STL header missing')
    count = struct.unpack_from('<I', data, 80)[0]
    if not 0 < count <= MAX_FACES or len(data) != 84 + count * 50:
        raise ValueError('Binary STL size or bounded face count mismatch')
    dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)),
                      ('attribute', '<u2')])
    records = np.frombuffer(data, dtype=dtype, count=count, offset=84)
    return records['vertices'].astype(np.float64), hashlib.sha256(data).hexdigest()


def exact_zero_area_mask(vertices, faces):
    # IEEE floats are dyadic rationals. A common power-of-two denominator
    # yields integer cross products without rounded area/tolerance decisions.
    values = np.unique(vertices)
    ratios = [float(value).as_integer_ratio() for value in values]
    exponents = [denominator.bit_length() - 1 for _, denominator in ratios]
    exponent = max(exponents, default=0)
    integers = {float(value): numerator << (exponent - power)
                for value, (numerator, _), power in zip(values, ratios, exponents)}
    points = [tuple(integers[float(value)] for value in point) for point in vertices]
    zero = []
    for ids in faces:
        a, b, c = (points[int(index)] for index in ids)
        u = tuple(b[i] - a[i] for i in range(3))
        v = tuple(c[i] - a[i] for i in range(3))
        zero.append(u[1]*v[2] == u[2]*v[1] and
                    u[2]*v[0] == u[0]*v[2] and
                    u[0]*v[1] == u[1]*v[0])
    return np.asarray(zero, dtype=bool)


def link_type(link_edges, repeated_vertex_face=False):
    """Circle/path in the simple vertex-link graph; keep all incidences."""
    if repeated_vertex_face:
        return 'invalid'
    if not link_edges:
        return 'isolated'
    unique = {tuple(sorted(edge)) for edge in link_edges}
    if len(unique) != len(link_edges) or any(a == b for a, b in unique):
        return 'invalid'
    adjacency = defaultdict(set)
    for a, b in unique:
        adjacency[a].add(b)
        adjacency[b].add(a)
    pending = [next(iter(adjacency))]
    visited = set()
    while pending:
        node = pending.pop()
        if node not in visited:
            visited.add(node)
            pending.extend(adjacency[node] - visited)
    if len(visited) != len(adjacency):
        return 'invalid'
    degrees = [len(neighbors) for neighbors in adjacency.values()]
    if len(degrees) >= 3 and all(degree == 2 for degree in degrees):
        return 'circle'
    if degrees.count(1) == 2 and all(degree in (1, 2) for degree in degrees):
        return 'path'
    return 'invalid'


def audit_arrays(vertices, faces):
    vertices, faces = np.asarray(vertices, dtype=np.float64), np.asarray(faces)
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or
            faces.ndim != 2 or faces.shape[1] != 3 or
            faces.dtype.kind not in 'iu' or not 0 < len(faces) <= MAX_FACES or
            not 0 < len(vertices) <= MAX_VERTICES or not np.isfinite(vertices).all() or
            np.any(faces < 0) or np.any(faces >= len(vertices))):
        raise ValueError('Invalid or unbounded triangle arrays')
    points, inverse = np.unique(vertices, axis=0, return_inverse=True)
    faces = inverse[faces]
    zero = exact_zero_area_mask(points, faces)
    face_sets = DisjointSet(len(faces))
    vertex_face_sets = DisjointSet(len(faces))
    edge_faces = defaultdict(list)
    vertex_faces = defaultdict(list)
    links = defaultdict(list)
    repeated_vertices = set()
    duplicate_faces = defaultdict(list)
    for face_id, triangle in enumerate(faces):
        a, b, c = map(int, triangle)
        duplicate_faces[tuple(sorted((a, b, c)))].append(face_id)
        for vertex in {a, b, c}:
            vertex_faces[vertex].append(face_id)
        if len({a, b, c}) != 3:
            repeated_vertices.update((a, b, c))
        for vertex, first, second in ((a, b, c), (b, c, a), (c, a, b)):
            links[vertex].append((first, second))
        for first, second in ((a, b), (b, c), (c, a)):
            edge_faces[tuple(sorted((first, second)))].append(
                (face_id, 1 if first < second else -1 if first > second else 0))
    for incidents in edge_faces.values():
        for face_id, _ in incidents[1:]:
            face_sets.union(incidents[0][0], face_id)
    for incidents in vertex_faces.values():
        for face_id in incidents[1:]:
            vertex_face_sets.union(incidents[0], face_id)
    labels = [face_sets.find(index) for index in range(len(faces))]
    groups = defaultdict(list)
    for face_id, root in enumerate(labels):
        groups[root].append(face_id)
    component_edges = defaultdict(list)
    for edge, incidents in edge_faces.items():
        component_edges[labels[incidents[0][0]]].append((edge, incidents))
    component_duplicate_excess = Counter()
    for entries in duplicate_faces.values():
        if len(entries) > 1:
            component_duplicate_excess[labels[entries[0]]] += len(entries) - 1
    link_kinds = [link_type(links[index], index in repeated_vertices)
                  for index in range(len(points))]
    triangle_points = points[faces]
    with np.errstate(over='raise', invalid='raise'):
        terms = np.einsum('ij,ij->i', triangle_points[:, 0],
                          np.cross(triangle_points[:, 1], triangle_points[:, 2])) / 6
    if not np.isfinite(terms).all():
        raise ValueError('Non-finite oriented integration')
    components = []
    for root, ids in sorted(groups.items(), key=lambda item: min(item[1])):
        used_vertices = np.unique(faces[ids])
        edges = component_edges[root]
        incidence = Counter(len(entries) for _, entries in edges)
        zero_edges = sum(a == b for (a, b), _ in edges)
        orientation_conflicts = sum(len(entries) == 2 and
                                    entries[0][1] != 0 and entries[0][1] == entries[1][1]
                                    for _, entries in edges)
        vertex_links = Counter(link_kinds[int(vertex)] for vertex in used_vertices)
        duplicate_excess = component_duplicate_excess[root]
        signed_volume = math.fsum(float(terms[index]) for index in ids)
        closed_combinatorial = bool(not np.any(zero[ids]) and zero_edges == 0 and
                                    incidence.get(2, 0) == len(edges) and
                                    orientation_conflicts == 0 and duplicate_excess == 0 and
                                    vertex_links.get('circle', 0) == len(used_vertices))
        components.append({
            'component_id': len(components) + 1, 'faces': len(ids),
            'vertices_referenced': len(used_vertices), 'edges_including_self_loops': len(edges),
            'exact_zero_area_faces': int(np.count_nonzero(zero[ids])),
            'duplicate_unoriented_face_excess': duplicate_excess,
            'edge_incidence_histogram': dict(sorted(incidence.items())),
            'self_loop_edges': zero_edges,
            'two_incidence_nonloop_orientation_conflicts': orientation_conflicts,
            'winding_checked_on_two_incidence_nonloop_edges_only': True,
            'vertex_links_in_whole_mesh': dict(sorted(vertex_links.items())),
            'euler_V_minus_E_plus_F': int(len(used_vertices) - len(edges) + len(ids)),
            'euler_is_not_genus_or_cavity_count': True,
            'signed_triangle_volume_scan_units_cubed': signed_volume,
            'volume_sign': 'positive' if signed_volume > 0 else 'negative' if signed_volume < 0 else 'zero',
            'closed_oriented_combinatorial_surface_screen_pass': closed_combinatorial,
        })
    whole = math.fsum(map(float, terms))
    component_sum = math.fsum(row['signed_triangle_volume_scan_units_cubed'] for row in components)
    return {
        'input_vertices': len(vertices), 'exact_unique_vertices': len(points),
        'faces_original_and_retained': len(faces), 'faces_removed': 0,
        'unused_exact_unique_vertices_retained': len(points) - len(vertex_faces),
        'exact_zero_area_faces': int(np.count_nonzero(zero)),
        'zero_area_predicate': 'integer_cross_product_after_exact_dyadic_scaling',
        'component_connectivity': 'shared_edge_all_incidences_including_nonmanifold_no_repair',
        'edge_connected_face_components': len(components),
        'vertex_connected_face_components': len({vertex_face_sets.find(i) for i in range(len(faces))}),
        'component_face_sum_matches_original': sum(row['faces'] for row in components) == len(faces),
        'vertex_link_classification': dict(sorted(Counter(link_kinds).items())),
        'components': components,
        'signed_triangle_volume_scan_units_cubed': whole,
        'component_signed_volume_sum_scan_units_cubed': component_sum,
        'component_sum_minus_whole_integration': component_sum - whole,
        'closed_oriented_combinatorial_surface_screen_pass': bool(
            len(points) == len(vertex_faces) and all(
                row['closed_oriented_combinatorial_surface_screen_pass'] for row in components)),
        'geometric_self_or_inter_component_intersections': 'untested',
        'shell_nesting_and_cavity_classification': 'untested',
        'orientation_of_each_shell_relative_to_material': 'untested',
        'continuous_ROI_and_section_preservation': 'untested',
        'repair_or_orientation_fix_or_small_component_removal': False,
    }


def write_private_new_json(output, report):
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.parent.is_symlink() or output.parent.stat().st_mode & 0o077:
        raise ValueError('Private output directory required')
    descriptor, temporary = tempfile.mkstemp(prefix='.surface-audit-', dir=output.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)  # Atomic publication, never overwrites a receipt.
    finally:
        os.unlink(temporary)


def run(directory, raw_report, output):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    started = time.monotonic()
    source = Path(__file__)
    native_path = directory / 'run-report.json'
    code_sha, native_sha, raw_sha = sha(source), sha(native_path), sha(raw_report)
    native, raw = json.loads(native_path.read_text()), json.loads(raw_report.read_text())
    if (native['schema'] != 'm64-picogk-local-junction-witness/v1' or
            native['voxel_scan_units'] != 0.2 or native['private_head_processed'] is not False or
            raw['native_report_sha256'] != native_sha):
        raise ValueError('Only the hash-bound 0.2 synthetic witness is accepted')
    rows = {}
    for name in ('before', 'after', 'added'):
        path = directory / (name + '.stl')
        triangles, digest = load_binary_stl(path)
        if (digest != native['exports'][name]['sha256'] or digest != raw['meshes'][name]['sha256'] or
                len(triangles) != native['exports'][name]['triangles']):
            raise ValueError('STL hash or face count disagrees with existing receipts')
        rows[name] = {'STL_sha256': digest, **audit_arrays(
            triangles.reshape(-1, 3), np.arange(triangles.size // 3).reshape(-1, 3))}
    if (sha(source) != code_sha or sha(native_path) != native_sha or sha(raw_report) != raw_sha or
            any(sha(directory / (name + '.stl')) != row['STL_sha256'] for name, row in rows.items())):
        raise ValueError('An input or audit helper changed during execution')
    report = {
        'schema': 'm64-local-junction-independent-surface-topology/v1',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'auditor_sha256': code_sha, 'native_report_sha256': native_sha,
        'original_raw_audit_sha256': raw_sha, 'original_raw_audit_status_retained': raw['status'],
        'native_occupancy_status_retained': native['status'],
        'numpy_version': np.__version__, 'max_faces_per_mesh': MAX_FACES,
        'coordinate_indexing': 'identical_numeric_coordinates_only_no_rounding',
        'meshes': rows,
        'oriented_volume_residual_after_minus_before_minus_added_scan_units_cubed': (
            rows['after']['signed_triangle_volume_scan_units_cubed'] -
            rows['before']['signed_triangle_volume_scan_units_cubed'] -
            rows['added']['signed_triangle_volume_scan_units_cubed']),
        'volume_residual_cause_proved': False,
        'status': 'diagnostic_completed_no_qualification_decision',
        'source_files_unchanged': True, 'original_criteria_modified': False,
        'finer_resolution_or_private_head_executed': False,
        'CFD_qualified': False, 'manufacturing_authorized': False,
        'elapsed_seconds': time.monotonic() - started,
    }
    write_private_new_json(output, report)
    print(json.dumps({'report': str(output), 'status': report['status'],
                      'mesh_screens': {name: row['closed_oriented_combinatorial_surface_screen_pass']
                                       for name, row in rows.items()}}))
    return 0 if all(row['closed_oriented_combinatorial_surface_screen_pass'] for row in rows.values()) else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--raw-audit-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.directory, args.raw_audit_report, args.output))
