"""Independent libigl distances/intersections and exact topology of a remeshed STL."""
import argparse
import hashlib
import json
from pathlib import Path

import igl
import igl.predicates
import numpy as np
from importlib.metadata import version


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    points, faces = igl.read_triangle_mesh(str(path))
    vertices, inverse = np.unique(points, axis=0, return_inverse=True)
    return vertices, inverse[faces]


def topology(vertices, faces):
    triangles = vertices[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    twice = np.linalg.norm(cross, axis=1)
    longest_squared = np.max(np.sum((triangles - np.roll(triangles, -1, axis=1)) ** 2, axis=2), axis=1)
    edges = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    undirected, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    signed = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    orientation = np.bincount(inverse, weights=signed)
    parent = np.arange(len(vertices))
    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index
    for a, b in undirected:
        parent[find(a)] = find(b)
    return {'vertices': len(vertices), 'triangles': len(faces),
            'boundary_edges': int((counts == 1).sum()), 'nonmanifold_edges': int((counts > 2).sum()),
            'inconsistent_orientation_edges': int(((counts == 2) & (orientation != 0)).sum()),
            'degenerate_triangles': int((twice == 0).sum()),
            'needle_triangles': int((twice / longest_squared < .001).sum()),
            'connected_components': len({find(int(index)) for index in np.unique(faces)}),
            'volume_mm3': float(np.einsum('ij,ij->i', triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6)}


def sample(vertices, faces, seed):
    triangles = vertices[faces]
    area = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
    rng = np.random.RandomState(seed)
    selected = triangles[rng.choice(len(faces), size=100000, p=area / area.sum())]
    u, v = rng.random_sample((2, len(selected)))
    root = np.sqrt(u)
    random = (1 - root[:, None]) * selected[:, 0] + (root * (1 - v))[:, None] * selected[:, 1] + (root * v)[:, None] * selected[:, 2]
    return np.vstack((vertices, triangles.mean(axis=1), random))


def distance(points, vertices, faces):
    squared, _, _ = igl.point_mesh_squared_distance(points, vertices, faces)
    values = np.sqrt(np.maximum(squared, 0))
    return {'samples': len(points), 'maximum_mm': float(values.max()),
            'p99_mm': float(np.quantile(values, .99)), 'mean_mm': float(values.mean())}


def triangle_keys(vertices, faces):
    return {tuple(sorted(map(tuple, triangle))) for triangle in vertices[faces]}


def interface_dimensions(vertices, faces):
    triangles = vertices[faces]
    def slice_points(axis):
        edges = np.vstack((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]))
        a, b = edges[:, 0], edges[:, 1]
        crossed = (a[:, axis] * b[:, axis]) < 0
        denominator = b[crossed, axis] - a[crossed, axis]
        points = a[crossed] - (a[crossed, axis] / denominator)[:, None] * (b[crossed] - a[crossed])
        return np.unique(np.vstack((points, a[np.abs(a[:, axis]) < 1e-10])), axis=0)
    rows = []
    for axis, centres, axes, radius in ((2, [(x, y) for x in (-50, 50) for y in (-20, 20)], [0, 1], 5.5),
                                        (1, [(-280, 0), (280, 0)], [0, 2], 6.75)):
        points = slice_points(axis)[:, axes]
        for centre in centres:
            radial = np.linalg.norm(points - centre, axis=1)
            selected = points[(radial > radius - 1) & (radial < radius + 1)]
            if len(selected) < 8:
                rows.append({'axis': axis, 'centre_mm': centre, 'samples': len(selected), 'passed': False})
                continue
            x, y, d = np.linalg.lstsq(np.c_[2 * selected, np.ones(len(selected))], (selected ** 2).sum(1), rcond=None)[0]
            rows.append({'axis': axis, 'centre_mm': centre, 'samples': len(selected),
                         'fitted_centre_mm': [float(x), float(y)],
                         'fitted_radius_mm': float(np.sqrt(d + x*x + y*y)),
                         'maximum_expected_cylinder_error_mm': float(np.abs(np.linalg.norm(selected - centre, axis=1) - radius).max())})
    seats = []
    for axis, values in ((2, (-4, 4)), (1, (-23, 23))):
        for value in values:
            on_plane = (np.abs(triangles[:, :, axis] - value) < 1e-5).all(axis=1)
            if axis == 1:
                on_plane &= (np.abs(triangles[:, :, 0]) > 260).all(axis=1)
            else:
                on_plane &= (np.abs(triangles[:, :, 0]) < 75).all(axis=1)
            seats.append({'axis': axis, 'coordinate_mm': value, 'triangles': int(on_plane.sum()),
                          'maximum_plane_error_mm': float(np.abs(triangles[on_plane, :, axis] - value).max()) if on_plane.any() else None})
    return {'bores': rows, 'seat_planes': seats}


def audit(source, candidate, criteria_path, output):
    criteria = json.loads(Path(criteria_path).read_text())
    if sha(source) != criteria['input_STL_sha256']:
        raise ValueError('Reference STL hash mismatch')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    source_v, source_f = load(source)
    candidate_v, candidate_f = load(candidate)
    before, after = topology(source_v, source_f), topology(candidate_v, candidate_f)
    found, pairs, _ = igl.predicates.find_self_intersections(candidate_v, candidate_f, False)
    source_to_candidate = distance(sample(source_v, source_f, criteria['random_seed']), candidate_v, candidate_f)
    candidate_to_source = distance(sample(candidate_v, candidate_f, criteria['random_seed'] + 1), source_v, source_f)
    source_points = set(map(tuple, source_v))
    candidate_points = set(map(tuple, candidate_v))
    source_triangles = source_v[source_f]
    bore = np.zeros(len(source_f), dtype=bool)
    for x in (-50, 50):
        for y in (-20, 20):
            radial = np.linalg.norm(source_triangles[:, :, :2] - [x, y], axis=2)
            bore |= (np.abs(radial - 5.5) < 1e-4).all(axis=1) & (np.abs(source_triangles[:, :, 2]) <= 4.0001).all(axis=1)
    eyes = (np.abs(source_triangles[:, :, 0]) > 260).all(axis=1)
    protected = triangle_keys(source_v, source_f[bore | eyes])
    missing_protected = protected - triangle_keys(candidate_v, candidate_f)
    bounds_change = float(np.abs(np.vstack((source_v.min(0), source_v.max(0))) - np.vstack((candidate_v.min(0), candidate_v.max(0)))).max())
    relative_volume = abs(after['volume_mm3'] / before['volume_mm3'] - 1)
    failures = []
    for key in ('boundary_edges', 'nonmanifold_edges', 'inconsistent_orientation_edges', 'degenerate_triangles', 'needle_triangles'):
        if after[key] != criteria['required_' + key]:
            failures.append('{}={}'.format(key, after[key]))
    if after['connected_components'] != criteria['required_connected_components']:
        failures.append('connected_components')
    if found or len(pairs):
        failures.append('self_intersections')
    if criteria.get('source_STL_vertices_must_be_preserved', True) and source_points - candidate_points:
        failures.append('missing_or_moved_source_vertex')
    interfaces = interface_dimensions(candidate_v, candidate_f)
    if criteria.get('source_STL_vertices_must_be_preserved', True):
        if missing_protected:
            failures.append('protected_bore_or_eye_triangle_changed')
    else:
        for row in interfaces['bores']:
            if row['samples'] < 8 or row.get('maximum_expected_cylinder_error_mm', 1) > criteria['maximum_mesh_interface_deviation_mm']:
                failures.append('mesh_bore_dimension')
        if any(row['triangles'] == 0 for row in interfaces['seat_planes']):
            failures.append('mesh_seating_plane')
    if relative_volume > criteria['maximum_relative_mesh_volume_change']:
        failures.append('volume_change')
    if bounds_change > criteria['maximum_bounds_change_mm']:
        failures.append('bounds_change')
    if max(source_to_candidate['maximum_mm'], candidate_to_source['maximum_mm']) > criteria['maximum_sampled_bidirectional_surface_distance_mm']:
        failures.append('surface_distance')
    result = {'source_STL_sha256': sha(source), 'candidate_STL_sha256': sha(candidate),
              'criteria_sha256': sha(criteria_path), 'audit_source_sha256': sha(__file__),
              'libigl_version': version('libigl'), 'numpy_version': np.__version__,
              'source': before, 'candidate': after, 'self_intersection_pairs': int(len(pairs)),
              'source_to_candidate': source_to_candidate, 'candidate_to_source': candidate_to_source,
              'source_vertices_preserved_exactly': not bool(source_points - candidate_points),
              'protected_central_bore_triangles': int(bore.sum()), 'protected_eye_and_seat_triangles': int(eyes.sum()),
              'protected_triangles_changed': len(missing_protected), 'bounds_change_mm': bounds_change,
              'relative_mesh_volume_change': relative_volume, 'interface_dimensions': interfaces, 'failures': failures,
              'status': 'passed' if not failures else 'rejected', 'manufacturing_authorized': False}
    (output / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--criteria', type=Path, required=True)
    args = parser.parse_args()
    audit(args.source, args.candidate, args.criteria, args.output)
