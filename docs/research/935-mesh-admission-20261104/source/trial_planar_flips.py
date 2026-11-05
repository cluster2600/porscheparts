"""One bounded full-surface connectivity trial; no smoothing or volume solve."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import igl
import numpy as np
import pymeshlab as ml


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8388608), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, data):
    with path.open('x') as f:
        json.dump(data, f, indent=2, allow_nan=False); f.write('\n')


def write_off(path, vertices, faces):
    with path.open('x') as stream:
        stream.write(f'OFF\n{len(vertices)} {len(faces)} 0\n')
        np.savetxt(stream, vertices, fmt='%.17g')
        np.savetxt(stream, np.column_stack((np.full(len(faces), 3), faces)), fmt='%d')


def inspect(binary, path, output):
    run = subprocess.run([str(binary), str(path)], capture_output=True, text=True, timeout=300)
    result = json.loads(run.stdout)
    result['exit_code'] = run.returncode
    save_json(output, result)
    return run.returncode == 0


def quality(v, f):
    p = v[f]; a, b = p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]
    area2 = np.linalg.norm(np.cross(a, b), axis=1)
    q = 2*np.sqrt(3)*area2/np.sum(a*a+b*b+(a-b)**2, axis=1)
    return {'quantiles': np.quantile(q, [0, .001, .01, .05, .5, 1]).tolist(),
            'below_0p01': int((q < .01).sum()), 'below_0p1': int((q < .1).sum()),
            'surface_area_mm2': float(area2.sum()/2),
            'signed_volume_mm3': float(np.einsum('ij,ij->i', p[:, 0], np.cross(p[:, 1], p[:, 2])).sum()/6)}


def samples(v, f, seed):
    rng = np.random.default_rng(seed)
    p = v[f]; area = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)
    selected = rng.choice(len(f), 100000, p=area/area.sum())
    u = rng.random((100000, 2)); root = np.sqrt(u[:, 0])
    weights = np.column_stack((1-root, root*(1-u[:, 1]), root*u[:, 1]))
    return np.einsum('ij,ijk->ik', weights, p[selected])


def distances(points, v, f):
    squared, _, _ = igl.point_mesh_squared_distance(points, v, f)
    d = np.sqrt(np.maximum(squared, 0))
    return {'samples': len(d), 'p50_mm': float(np.median(d)),
            'p95_mm': float(np.quantile(d, .95)), 'sampled_max_mm': float(d.max())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solid', type=Path, required=True)
    parser.add_argument('--input-sha256', required=True)
    parser.add_argument('--scan-arrays', type=Path, required=True)
    parser.add_argument('--scan-arrays-sha256', required=True)
    parser.add_argument('--inspector', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit('Existing output refused.')
    if sha(args.solid) != args.input_sha256: raise SystemExit('Study input hash mismatch.')
    if sha(args.scan_arrays) != args.scan_arrays_sha256: raise SystemExit('Scan array hash mismatch.')
    args.output.mkdir(parents=True)
    parameters = {'pthreshold': .001, 'planartype': 2, 'iterations': 0, 'selection': False}
    save_json(args.output/'plan.json', {'parameters': parameters,
        'scope': 'Nearly coplanar edge flips only; preserve every vertex; no relaxation',
        'input_sha256': args.input_sha256, 'scan_arrays_sha256': args.scan_arrays_sha256,
        'inspector_sha256': sha(args.inspector),
        'runtime': {'pymeshlab': importlib.metadata.version('pymeshlab'),
                    'numpy': np.__version__, 'libigl': importlib.metadata.version('libigl')},
        'gates': {'identical_vertex_array': True, 'same_face_count': True,
                  'native_intersections': 0, 'parent_sampled_max_limit_mm': .001,
                  'relative_volume_change_limit': 1e-6,
                  'bad_triangle_count_must_decrease': True},
        'upstream_admissibility': 'Reconstructed assembly study only; inferred closures and unknown physical interfaces persist.'})
    # An asymmetric planar quadrilateral must flip without moving any vertex.
    cv = np.array([[0,0,0], [2,0,0], [2,1,0], [0,.1,0]], float)
    cf = np.array([[0,1,2], [0,2,3]], np.int32)
    control = ml.MeshSet(); control.add_mesh(ml.Mesh(cv, cf))
    control.apply_filter('meshing_edge_flip_by_planar_optimization', **parameters)
    cf2 = control.current_mesh().face_matrix()
    if not np.array_equal(cv, control.current_mesh().vertex_matrix()) or quality(cv, cf2)['quantiles'][0] <= quality(cv, cf)['quantiles'][0]:
        raise SystemExit('Planar flip control failed.')
    tetra_v = np.array([[0,0,0], [1,0,0], [0,1,0], [0,0,1]], float)
    tetra_f = np.array([[0,2,1], [0,1,3], [0,3,2], [1,2,3]])
    write_off(args.output/'control-tetra.off', tetra_v, tetra_f)
    if not inspect(args.inspector, args.output/'control-tetra.off', args.output/'control-tetra.json'):
        raise SystemExit('Native closed-tetrahedron control failed.')
    cross_v = np.array([[-1,-1,0], [1,-1,0], [0,1,0], [0,-.5,-1], [0,-.5,1], [0,.5,0]], float)
    write_off(args.output/'control-crossing.off', cross_v, np.array([[0,1,2], [3,4,5]]))
    inspect(args.inspector, args.output/'control-crossing.off', args.output/'control-crossing.json')
    crossing = json.loads((args.output/'control-crossing.json').read_text())
    if crossing.get('intersection_pairs') != 1: raise SystemExit('Native crossing control failed.')
    with np.load(args.solid, allow_pickle=False) as a:
        used, inverse = np.unique(a['boundary'], return_inverse=True)
        v, f = a['nodes'][used], inverse.reshape((-1, 3))
    write_off(args.output/'parent.off', v, f)
    if not inspect(args.inspector, args.output/'parent.off', args.output/'parent-native.json'):
        raise SystemExit('Parent native audit failed; candidate not executed.')
    before = quality(v, f)
    mesh = ml.MeshSet(); mesh.add_mesh(ml.Mesh(v, f.astype(np.int32)))
    started = time.time(); mesh.apply_filter('meshing_edge_flip_by_planar_optimization', **parameters)
    elapsed = time.time()-started
    v2, f2 = mesh.current_mesh().vertex_matrix(), mesh.current_mesh().face_matrix().astype(np.int64)
    np.savez_compressed(args.output/'candidate.npz', vertices=v2, triangles=f2)
    write_off(args.output/'candidate.off', v2, f2)
    native = inspect(args.inspector, args.output/'candidate.off', args.output/'candidate-native.json')
    after = quality(v2, f2)
    parent_points, candidate_points = samples(v, f, 9350401), samples(v2, f2, 9350402)
    parent_to_candidate = distances(parent_points, v2, f2)
    candidate_to_parent = distances(candidate_points, v, f)
    with np.load(args.scan_arrays, allow_pickle=False) as a:
        sv, sf = a['vertices'], a['triangles']
    scan_points = samples(sv, sf, 9350403)
    scan_to_candidate = distances(scan_points, v2, f2)
    candidate_to_scan = distances(candidate_points, sv, sf)
    checks = {'identical_vertex_array': bool(np.array_equal(v, v2)),
        'same_face_count': len(f) == len(f2), 'native_audit_passed': native,
        'parent_sampled_deviations': max(parent_to_candidate['sampled_max_mm'], candidate_to_parent['sampled_max_mm']) < .001,
        'relative_volume_change': abs(after['signed_volume_mm3']/before['signed_volume_mm3']-1) < 1e-6,
        'bad_triangle_count_decreased': after['below_0p01'] < before['below_0p01']}
    save_json(args.output/'assessment.json', {'before': before, 'after': after,
        'filter_seconds': elapsed, 'changed_face_rows': int(np.any(f != f2, axis=1).sum()) if f.shape == f2.shape else None,
        'parent_to_candidate': parent_to_candidate, 'candidate_to_parent': candidate_to_parent,
        'scan_to_candidate': scan_to_candidate, 'candidate_to_scan': candidate_to_scan,
        'checks': checks, 'accepted_for_next_study_stage': all(checks.values()),
        'functional_head_accepted': False, 'manufacturing_authorized': False,
        'limitations': 'Sampled distances are not Hausdorff bounds; parent inferred surfaces and unresolved anatomical identities persist.'})
    print(json.dumps({'output': str(args.output), 'checks': checks, 'filter_seconds': elapsed}))


if __name__ == '__main__':
    main()
