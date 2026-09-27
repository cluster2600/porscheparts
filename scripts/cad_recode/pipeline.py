#!/usr/bin/env python3
"""Independent, explicit stages. Generated Python is NEVER executed here."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / 'deploy/vast/cad-recode/models.lock.json'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def new_output(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path


def normalization(vertices):
    import numpy as np
    vertices = np.asarray(vertices, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError('invalid vertices')
    center = (vertices.min(0) + vertices.max(0)) / 2
    extent = float(np.ptp(vertices, axis=0).max())
    if not math.isfinite(extent) or extent <= 0 or not math.isfinite(2 / extent):
        raise ValueError('degenerate bounds')
    return center, 2 / extent


def farthest_points(points, count=256):
    import numpy as np
    if len(points) < count:
        raise ValueError('insufficient points')
    # ponytail: O(N*K), bounded to 8192*256; use upstream GPU FPS for larger clouds.
    distances = np.full(len(points), np.inf)
    indices = []
    index = 0
    for _ in range(count):
        indices.append(index)
        distances = np.minimum(distances, ((points - points[index]) ** 2).sum(1))
        index = int(np.argmax(distances))
    return points[indices]


def prepare(source, output, expected, seed=935):
    import numpy as np
    import trimesh
    source = Path(source).resolve()
    if digest(source) != expected:
        raise ValueError('source hash mismatch')
    mesh = trimesh.load(source, force='mesh', process=False)
    center, scale = normalization(mesh.vertices)
    if not len(mesh.faces) or not math.isfinite(float(mesh.area)) or mesh.area <= 0:
        raise ValueError('empty or degenerate surface')
    points, _ = trimesh.sample.sample_surface(mesh, 8192, seed=seed)
    points = farthest_points((points - center) * scale)
    output = new_output(output)
    np.save(output / 'points.npy', points.astype(np.float32), allow_pickle=False)
    # Preserve raw axes; no PCA or old interface planes are imported.
    mesh.export(output / 'reference.ply')
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    edges = mesh.edges_unique
    graph = coo_matrix((np.ones(len(edges), dtype=np.uint8), (edges[:, 0], edges[:, 1])),
                       shape=(len(mesh.vertices), len(mesh.vertices)))
    count, labels = connected_components(graph, directed=False)
    face_components = labels[mesh.faces[:, 0]]
    np.save(output / 'face-components.npy', face_components, allow_pickle=False)
    report = {
        'status': 'candidate', 'identity': '935-Wolfe-reference',
        'source_sha256': expected, 'reference_sha256': digest(output / 'reference.ply'),
        'points_sha256': digest(output / 'points.npy'),
        'units': 'unknown_OBJ_units', 'scale_verified': False,
        'center': center.tolist(), 'normalization_scale': scale,
        'cad_recode_output_factor': 100.0,
        'inverse': 'raw_xyz = generated_cad_xyz / 100 / normalization_scale + center',
        'seed': seed, 'point_count': 256, 'vertices': len(mesh.vertices),
        'triangles': len(mesh.faces), 'watertight': bool(mesh.is_watertight),
        'bounds': mesh.bounds.tolist(), 'connected_components': int(count),
        'component_face_counts': np.bincount(face_components, minlength=count).tolist(),
        'segmentation_review_required': True, 'legacy_inputs_used': [],
        'geometry_accepted': False, 'manufacturing_authorized': False,
    }
    write_json(output / 'intake.json', report)
    return report


def verify_intake(path):
    path = Path(path)
    d = json.loads((path / 'intake.json').read_text())
    for filename, key in [('points.npy', 'points_sha256'), ('reference.ply', 'reference_sha256')]:
        if digest(path / filename) != d[key]:
            raise ValueError(f'intake changed: {filename}')
    if not math.isfinite(d['normalization_scale']) or d['normalization_scale'] <= 0:
        raise ValueError('invalid transform')
    return d


def export_sandbox(code, intake, output, image, timeout=180):
    if not re.fullmatch(r'(?:[a-z0-9][a-z0-9._/:-]*@)?sha256:[0-9a-f]{64}', image):
        raise ValueError('immutable CAD image reference required')
    if not 1 <= timeout <= 600:
        raise ValueError('timeout must be 1..600 seconds')
    verify_intake(intake)
    code, intake = Path(code).resolve(), Path(intake).resolve()
    if code.stat().st_size > 1_000_000:
        raise ValueError('generated code too large')
    output = new_output(output)
    output.chmod(0o777)  # Dedicated artifact directory only; container UID is 65534.
    name = 'cad-recode-' + uuid.uuid4().hex
    command = ['docker', 'run', '--rm', '--platform=linux/amd64', '--name', name, '--network=none', '--read-only',
               '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=64',
               '--memory=4g', '--cpus=2', '--user=65534:65534', '--tmpfs=/tmp:rw,size=256m',
               '--mount', f'type=bind,src={code},dst=/input/candidate.py,readonly',
               '--mount', f'type=bind,src={intake / "intake.json"},dst=/input/intake.json,readonly',
               '--mount', f'type=bind,src={output},dst=/output',
               image, 'python', '/opt/cad-recode/worker.py']
    status = 'failed'
    with (output / 'execution.log').open('wb') as log:
        try:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            status = 'exported_unverified' if result.returncode == 0 else 'failed'
        except subprocess.TimeoutExpired:
            status = 'timeout'
        finally:
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
    report = {'status': status, 'image': image, 'code_sha256': digest(code),
              'physics_validated': False, 'manufacturing_authorized': False}
    write_json(output / 'execution.json', report)
    return report


def evaluate(intake, step, output):
    import cadquery as cq
    import numpy as np
    import trimesh
    d = verify_intake(intake)
    shape = cq.importers.importStep(str(step)).val()
    if not shape.isValid() or not shape.Solids() or shape.Volume() <= 0:
        raise ValueError('invalid STEP solid')
    vertices, faces = shape.tessellate(0.01, 0.1)
    candidate = trimesh.Trimesh([v.toTuple() for v in vertices], faces, process=False)
    reference = trimesh.load(Path(intake) / 'reference.ply', process=False)
    def deviation(a, b):
        samples, _ = trimesh.sample.sample_surface(a, 8192, seed=935)
        # Batches bound the closest-point query working set for dense raw scans.
        distances = np.concatenate([trimesh.proximity.closest_point(b, p)[1]
                                    for p in np.array_split(samples, 64)])
        return {'median': float(np.median(distances)), 'p95': float(np.percentile(distances, 95)),
                'sampled_max': float(distances.max()), 'samples': len(distances)}
    output = new_output(output)
    report = {'status': 'needs_review', 'units': d['units'], 'step_sha256': digest(step),
              'source_sha256': d['source_sha256'], 'solid_valid': True,
              'candidate_bounds': candidate.bounds.tolist(), 'reference_bounds': reference.bounds.tolist(),
              'scan_to_cad': deviation(reference, candidate), 'cad_to_scan': deviation(candidate, reference),
              'tessellation_deflection_obj_units': 0.01, 'angular_deflection_radians': 0.1,
              'sampling_seed': 935, 'acceptance_threshold': None, 'geometry_accepted': False,
              'physics_validated': False, 'manufacturing_authorized': False}
    candidate.export(output / 'candidate.ply')
    write_json(output / 'deviation.json', report)
    (output / 'report.md').write_text('# Reconstruction candidate 935\n\n'
        'Échelle inconnue. Écarts en unités OBJ ; maximum échantillonné, pas distance de Hausdorff exacte.\n\n'
        + '```json\n' + json.dumps(report, indent=2) + '\n```\n')
    return report


def readiness(inputs, output):
    data = json.loads(Path(inputs).read_text())
    required = ['scale_measurements', 'material', 'loads', 'thermal_boundaries',
                'interfaces', 'acceptance_criteria']
    missing = [key for key in required if not data.get(key)]
    # This entrypoint inventories evidence only; it never authorizes a solver.
    report = {'status': 'blocked', 'missing': missing, 'engineering_review_required': True,
              'solver_authorized': False, 'physicsnemo_training_authorized': False,
              'manufacturing_authorized': False}
    output = new_output(output)
    write_json(output / 'readiness.json', report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='stage', required=True)
    a = sub.add_parser('prepare'); a.add_argument('source', type=Path); a.add_argument('output', type=Path)
    a.add_argument('--expected-sha256', default=json.loads(LOCK.read_text())['source_sha256'])
    a = sub.add_parser('export'); a.add_argument('code', type=Path); a.add_argument('intake', type=Path)
    a.add_argument('output', type=Path); a.add_argument('--image', required=True); a.add_argument('--timeout', type=int, default=180)
    a = sub.add_parser('evaluate'); a.add_argument('intake', type=Path); a.add_argument('step', type=Path); a.add_argument('output', type=Path)
    a = sub.add_parser('readiness'); a.add_argument('inputs', type=Path); a.add_argument('output', type=Path)
    args = p.parse_args()
    try:
        if args.stage == 'prepare': r = prepare(args.source, args.output, args.expected_sha256)
        elif args.stage == 'export': r = export_sandbox(args.code, args.intake, args.output, args.image, args.timeout)
        elif args.stage == 'evaluate': r = evaluate(args.intake, args.step, args.output)
        else: r = readiness(args.inputs, args.output)
        print(json.dumps(r, allow_nan=False))
        return 0 if r['status'] in ('candidate', 'exported_unverified', 'needs_review') else 3
    except (ValueError, OSError, RuntimeError) as e:
        print(json.dumps({'status': 'failed', 'error': str(e)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
