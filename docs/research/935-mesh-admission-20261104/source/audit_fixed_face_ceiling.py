"""Bound achievable tetrahedron mean ratio when a boundary triangle is fixed."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_helper(filename, digest, module_name):
    path = Path(__file__).with_name(filename)
    if sha(path) != digest:
        raise ValueError('Registered helper changed')
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def triangle_quality(points):
    a, b = points[:, 1]-points[:, 0], points[:, 2]-points[:, 0]
    return 2*np.sqrt(3)*np.linalg.norm(np.cross(a, b), axis=1)/np.sum(a*a+b*b+(a-b)**2, axis=1)


def controls(metrics):
    rng = np.random.default_rng(935)
    checks = {}
    triangles = [np.array([[0, 0, 0], [1, 0, 0], [.5, np.sqrt(3)/2, 0.]]),
                 np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0.]]),
                 np.array([[0, 0, 0], [1, 0, 0], [0, .0001, 0.]]),
                 np.array([[3, -2, 1], [4, -1, 1], [3.1, -1, 2.]])]
    for i, triangle in enumerate(triangles):
        q = triangle_quality(triangle[None])[0]
        denominator = sum(np.sum((triangle[j]-triangle[k])**2) for j in range(3) for k in range(j))
        normal = np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
        normal /= np.linalg.norm(normal)
        optimum = triangle.mean(0)+normal*np.sqrt(2*denominator/9)
        _, quality = metrics(np.concatenate((triangle, optimum[None]))[None])
        checks['optimal_apex_equality_'+str(i)] = bool(abs(quality[0]-q**(2/3)) < 1e-12)
        apices = triangle.mean(0)+rng.normal(size=(300, 3))*np.sqrt(denominator)
        tets = np.concatenate((np.broadcast_to(triangle, (len(apices), 3, 3)), apices[:, None]), axis=1)
        _, quality = metrics(tets)
        checks['off_optimum_samples_bounded_'+str(i)] = bool(np.all(quality <= q**(2/3)+1e-12))
    checks['regular_face_ceiling_one'] = bool(abs(triangle_quality(triangles[0][None])[0]**(2/3)-1) < 1e-14)
    if not all(checks.values()):
        raise ValueError('Fixed-face bound controls failed')
    return checks


def packed_faces(faces, node_count):
    if node_count**3 >= np.iinfo(np.int64).max:
        raise ValueError('Packed face IDs would overflow')
    ordered = np.sort(faces, axis=1)
    return (ordered[:, 0]*node_count+ordered[:, 1])*node_count+ordered[:, 2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('mesh', 'surface', 'parent', 'protected', 'tet-verification', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing fixed-face audit refused')
    tet_report = json.loads(args.tet_verification.read_text())
    if not tet_report['study_mesh_geometry_passed']:
        raise SystemExit('Actual tetrahedral boundary has not been independently verified')
    expected = [(args.mesh, tet_report['mesh_audit']['input_sha256']),
                (args.surface, tet_report['surface_sha256']),
                (args.parent, 'e6878961194caf209cbb0521709b5041cf6ff62cced7f63560acddeef9252f94'),
                (args.protected, 'f9172eabbabd4ea979c93b47afa72f3952feb325daf5c95045c3a5ca6b43b6e2')]
    for path, digest in expected:
        if sha(path) != digest:
            raise SystemExit('Registered fixed-face input mismatch')
    helper = load_helper('audit_retained_meshes.py', 'c1d93c8018e03c628cda261c16304b0dca26eb575967953e828e9a16cb9f610c', 'fixed_face_tet_metrics')
    motion = load_helper('verify_bounded_relocation.py', 'eee9271dd7934f7dd23edfcd8d3e9d8979f3a59c0eb37ff3edd3df45b04b6ede', 'fixed_face_locks')
    tested = controls(helper.tetra_metrics)
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, tets = data['nodes'], data['tets']
    with np.load(args.surface, allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    with np.load(args.parent, allow_pickle=False) as data:
        original, original_faces = data['vertices'], data['triangles']
    if not np.array_equal(faces, original_faces):
        raise ValueError('Original connectivity changed')
    protected = np.load(args.protected, allow_pickle=False)
    cross, _, _ = motion.face_data(original, faces)
    locked, _ = motion.derive_locks(original, faces, protected, cross)
    if not np.array_equal(original[locked], vertices[locked]):
        raise ValueError('Registered locked coordinates changed')
    protected_mask = np.zeros(len(faces), bool)
    protected_mask[protected] = True
    faceq = triangle_quality(vertices[faces])
    ceiling = faceq**(2/3)
    forced = np.flatnonzero(ceiling < .01)
    cellq = np.empty(len(tets))
    for start in range(0, len(tets), 100000):
        end = min(start+100000, len(tets))
        _, cellq[start:end] = helper.tetra_metrics(nodes[tets[start:end]])
    bad = np.flatnonzero(cellq < .01)
    if len(bad) != tet_report['mesh_audit']['diagnostic_bins'][0]['count']:
        raise ValueError('Independent low-quality cell count mismatch')
    candidates = tets[bad][:, [[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]]].reshape(-1, 3)
    keys = packed_faces(candidates, len(nodes))
    order = np.argsort(keys, kind='stable')
    sorted_keys = keys[order]
    targets = packed_faces(faces[forced], len(nodes))
    lower, upper = np.searchsorted(sorted_keys, targets, side='left'), np.searchsorted(sorted_keys, targets, side='right')
    if not np.all(upper-lower == 1):
        raise ValueError('Every forced exterior face must have one matching low-quality tetrahedron')
    cells = bad[order[lower]//4]
    if not np.all(cellq[cells] <= ceiling[forced]+1e-10):
        raise ValueError('Actual tetrahedron exceeds the analytic fixed-face ceiling')
    immobile = locked[faces[forced]].all(1)
    fixed_protected = protected_mask[forced]
    args.output.mkdir(parents=True)
    np.savez_compressed(args.output/'provenance.npz', face_ids=forced, cell_ids=cells,
                        face_quality=faceq[forced], tetra_mean_ratio_ceiling=ceiling[forced],
                        actual_tetra_mean_ratio=cellq[cells], all_vertices_locked=immobile,
                        directly_protected=fixed_protected)
    report = {'scope': 'Necessary shape-quality bound for exact fixed study boundary triangles; no physical-part verdict',
        'source_sha256': sha(__file__), 'input_sha256': {name: sha(getattr(args, name)) for name in ('mesh', 'surface', 'parent', 'protected')},
        'tet_verification_sha256': sha(args.tet_verification), 'controls': tested,
        'formula': 'maximum tetrahedron mean ratio = triangle shape quality ** (2/3)',
        'diagnostic_mean_ratio_threshold': .01, 'tetrahedra': len(tets),
        'actual_cells_below_threshold': len(bad), 'boundary_faces_forcing_subthreshold_tets': len(forced),
        'distinct_actual_cells_adjacent_to_forced_faces': len(np.unique(cells)),
        'forced_faces_all_vertices_locked': int(immobile.sum()),
        'distinct_cells_forced_by_all_vertex_locked_faces': len(np.unique(cells[immobile])),
        'forced_faces_directly_protected': int(fixed_protected.sum()),
        'distinct_cells_forced_by_directly_protected_faces': len(np.unique(cells[fixed_protected])),
        'minimum_boundary_triangle_quality': float(faceq.min()),
        'smallest_fixed_face_tetra_mean_ratio_ceiling': float(ceiling.min()),
        'actual_cell_bound_checks_pass': True, 'all_forced_faces_match_one_actual_low_quality_cell': True,
        'provenance_sha256': sha(args.output/'provenance.npz'),
        'bound_limit': 'Double-precision analytic evaluation; diagnostic threshold, not an engineering allowable. Applies while these exact boundary triangles are retained; no bound on alternative surface tessellations.',
        'physics_admitted': False, 'physical_acceptance': False, 'manufacturing_authorized': False}
    (args.output/'assessment.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
