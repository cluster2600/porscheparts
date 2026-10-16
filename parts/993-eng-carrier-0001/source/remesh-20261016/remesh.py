"""Exact PyMesh cleanup and constrained retriangulation of retained planar patches."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_stl(path):
    data = Path(path).read_bytes()
    if len(data) < 84:
        raise ValueError('Truncated binary STL')
    count = struct.unpack('<I', data[80:84])[0]
    if count == 0 or len(data) != 84 + 50 * count:
        raise ValueError('Nonempty exact-length binary STL required')
    dtype = np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
    triangles = np.frombuffer(data[84:], dtype=dtype)['vertices'].astype(np.float64)
    if not np.isfinite(triangles).all():
        raise ValueError('Finite STL coordinates required')
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    return vertices, inverse.reshape(-1, 3)


def write_stl(path, vertices, faces):
    triangles = np.asarray(vertices[faces], dtype='<f4')
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    if not np.all(lengths > 0):
        raise ValueError('Degenerate candidate triangle')
    normals /= lengths[:, None]
    dtype = np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
    records = np.zeros(len(faces), dtype=dtype)
    records['normal'], records['vertices'] = normals, triangles
    with Path(path).open('xb') as stream:
        stream.write(b'V6f exact planar retriangulation'.ljust(80, b'\0'))
        stream.write(struct.pack('<I', len(faces)))
        stream.write(records.tobytes())


def quality(vertices, faces):
    triangles = vertices[faces]
    twice_area = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                         triangles[:, 2] - triangles[:, 0]), axis=1)
    longest_squared = np.max(np.sum((triangles - np.roll(triangles, -1, axis=1)) ** 2, axis=2), axis=1)
    return np.divide(twice_area, longest_squared, out=np.zeros_like(twice_area), where=longest_squared > 0)


def edges(face):
    return [tuple(sorted((int(face[k]), int(face[(k + 1) % 3])))) for k in range(3)]


def planar_patches(vertices, faces, criteria):
    """Find edge-connected source planes containing a needle, without growing across folds."""
    adjacency = {}
    for index, face in enumerate(faces):
        for edge in edges(face):
            adjacency.setdefault(edge, set()).add(index)
    pending = set(map(int, np.flatnonzero(quality(vertices, faces) < criteria['needle_height_to_longest_edge_min'])))
    patches = []
    while pending:
        seed = min(pending)
        triangle = vertices[faces[seed]]
        normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
        normal /= np.linalg.norm(normal)
        patch, queue = {seed}, [seed]
        while queue:
            index = queue.pop()
            for edge in edges(faces[index]):
                for neighbour in adjacency[edge] - patch:
                    points = vertices[faces[neighbour]]
                    if np.max(np.abs((points - triangle[0]) @ normal)) <= criteria['coplanarity_max_mm']:
                        patch.add(neighbour)
                        queue.append(neighbour)
        pending -= patch
        patches.append(sorted(patch))
    return patches


def retriangulate(vertices, faces, criteria):
    import pymesh
    vertices = np.array(vertices, copy=True)
    faces = np.array(faces, dtype=np.int64, copy=True)
    patches = planar_patches(vertices, faces, criteria)
    keep = np.ones(len(faces), dtype=bool)
    replacements, log = [], []
    for patch in patches:
        old = faces[patch]
        ids = np.unique(old)
        points = vertices[ids]
        spread = np.ptp(points, axis=0)
        axis = int(np.argmin(spread))
        if spread[axis] > criteria['coplanarity_max_mm']:
            raise ValueError('Only exact coordinate-plane patches are supported')
        axes = [value for value in range(3) if value != axis]
        source_edges = np.vstack((old[:, [0, 1]], old[:, [1, 2]], old[:, [2, 0]]))
        keys, inverse, counts = np.unique(np.sort(source_edges, axis=1), axis=0, return_inverse=True, return_counts=True)
        boundary = source_edges[counts[inverse] == 1]
        local = np.searchsorted(ids, boundary)
        triangle = pymesh.triangle()
        triangle.points = points[:, axes]
        triangle.triangles = np.searchsorted(ids, old)
        triangle.auto_hole_detection = False
        triangle.split_boundary = False
        triangle.conforming_delaunay = False
        triangle.exact_arithmetic = True
        triangle.min_angle = criteria['Triangle_minimum_angle_deg']
        triangle.verbosity = 0
        # Orient every patch counterclockwise in its retained coordinate plane.
        p = vertices[old[0]][:, axes]
        sign = np.cross(p[1] - p[0], p[2] - p[0])
        if sign < 0:
            triangle.triangles = np.searchsorted(ids, old[:, [0, 2, 1]])
        triangle.run()
        new_points = triangle.vertices
        lookup = {tuple(point): int(index) for point, index in zip(points[:, axes], ids)}
        mapped, added = [], []
        for point in new_points:
            key = tuple(point)
            if key in lookup:
                mapped.append(lookup[key])
            else:
                xyz = np.empty(3)
                xyz[axes], xyz[axis] = point, points[0, axis]
                lookup[key] = len(vertices) + len(added)
                mapped.append(lookup[key])
                added.append(xyz)
        if added:
            vertices = np.vstack((vertices, added))
        candidate = np.array(mapped, dtype=np.int64)[triangle.faces]
        if sign < 0:
            candidate = candidate[:, [0, 2, 1]]
        keep[patch] = False
        replacements.append(candidate)
        log.append({'source_faces': patch, 'source_triangles': len(old), 'candidate_triangles': len(candidate),
                    'new_interior_vertices': len(added), 'constant_axis': axis,
                    'plane_coordinate_mm': float(points[0, axis]), 'boundary_segments': len(boundary)})
    return vertices, np.vstack([faces[keep]] + replacements), log


def run(source, output, criteria_path):
    import platform
    import pymesh
    source, output = Path(source), Path(output)
    criteria = json.loads(Path(criteria_path).read_text())
    if sha(source) != criteria['input_STL_sha256']:
        raise ValueError('Source STL hash differs from frozen criteria')
    output.mkdir(parents=True, exist_ok=False)
    vertices, faces = read_stl(source)
    mesh = pymesh.form_mesh(vertices, faces)
    mesh, duplicate_vertices = pymesh.remove_duplicated_vertices(mesh, 0.0)
    mesh, duplicate_faces = pymesh.remove_duplicated_faces(mesh)
    mesh, isolated = pymesh.remove_isolated_vertices(mesh)
    ordered = lambda points: points[np.lexsort(points.T[::-1])]
    if mesh.num_faces != len(faces) or not np.array_equal(ordered(mesh.vertices), ordered(vertices)):
        raise ValueError('Exact cleanup changed retained source geometry')
    write_stl(output / 'pymesh-exact-cleanup.stl', mesh.vertices, mesh.faces)
    before = quality(mesh.vertices, mesh.faces)
    candidate_vertices, repaired, patches = retriangulate(mesh.vertices, mesh.faces, criteria)
    write_stl(output / 'carrier-remeshed.stl', candidate_vertices, repaired)
    np.savez_compressed(str(output / 'source-and-candidate.npz'), vertices=mesh.vertices,
                        source_faces=mesh.faces, candidate_vertices=candidate_vertices, candidate_faces=repaired)
    result = {'input_STL_sha256': sha(source), 'criteria_sha256': sha(criteria_path),
              'worker_sha256': sha(__file__), 'candidate_STL_sha256': sha(output / 'carrier-remeshed.stl'),
              'pymesh_version': pymesh.__version__, 'python_version': platform.python_version(),
              'numpy_version': np.__version__, 'exact_cleanup': {
                  'merged_vertices': int(duplicate_vertices['num_vertex_merged']),
                  'removed_duplicate_faces': len(faces) - mesh.num_faces,
                  'removed_isolated_vertices': int(isolated['num_vertex_removed'])},
              'input_vertices': len(vertices), 'output_vertices': len(candidate_vertices),
              'input_triangles': len(faces), 'output_triangles': len(repaired),
              'input_needles': int((before < criteria['needle_height_to_longest_edge_min']).sum()),
              'output_needles': int((quality(candidate_vertices, repaired) < criteria['needle_height_to_longest_edge_min']).sum()),
              'vertex_movement_mm': 0.0, 'retriangulated_planar_patches': patches,
              'manufacturing_authorized': False}
    (output / 'repair.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'retriangulated_planar_patches'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--criteria', type=Path, default=Path(__file__).with_name('criteria.json'))
    args = parser.parse_args()
    run(args.source, args.output, args.criteria)
