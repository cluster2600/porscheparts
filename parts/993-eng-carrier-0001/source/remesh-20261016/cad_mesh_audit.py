"""Audit exact trimmed-face CAD samples against STL and independently audit its topology."""
import argparse
import json
from pathlib import Path

import igl
import igl.predicates
import numpy as np
from importlib.metadata import version

from audit import distance, interface_dimensions, load, sha, topology


def run(candidate, brep_receipt, samples_path, output, expected_samples_sha256=None):
    candidate, brep_receipt, samples_path, output = map(Path, (candidate, brep_receipt, samples_path, output))
    receipt = json.loads(brep_receipt.read_text())
    if sha(candidate) != receipt['results']['candidate_STL']['sha256']:
        raise ValueError('Candidate does not match the exact-CAD audit receipt')
    expected = receipt.get('exact_CAD_surface_samples_sha256', expected_samples_sha256)
    if not expected or sha(samples_path) != expected:
        raise ValueError('Exact CAD sample archive hash mismatch or missing')
    if expected_samples_sha256 is not None and expected_samples_sha256 != expected:
        raise ValueError('Conflicting CAD sample archive hash')
    with np.load(samples_path, allow_pickle=False) as archive:
        samples = archive['points_mm']
    if samples.shape != (receipt['exact_CAD_surface_samples'], 3) or not np.isfinite(samples).all():
        raise ValueError('Exact CAD sample archive count/shape/finite-data mismatch')
    if output.exists():
        raise ValueError('Fresh output directory required')
    vertices, faces = load(candidate)
    quality = topology(vertices, faces)
    found, pairs, _ = igl.predicates.find_self_intersections(vertices, faces, False)
    inverse = distance(samples, vertices, faces)
    failures = [name for name in ('boundary_edges', 'nonmanifold_edges', 'inconsistent_orientation_edges',
                                  'degenerate_triangles', 'needle_triangles') if quality[name]]
    if quality['connected_components'] != 1 or quality['volume_mm3'] <= 0:
        failures.append('one_positive_volume_component')
    if found or len(pairs):
        failures.append('self_intersections')
    if inverse['maximum_mm'] > .06:
        failures.append('CAD_to_mesh_distance')
    if not receipt['candidate_sampled_chord_screen_pass']:
        failures.append('mesh_to_CAD_distance')
    interfaces = interface_dimensions(vertices, faces)
    if any(row['samples'] < 8 or row.get('maximum_expected_cylinder_error_mm', 1) > .01 for row in interfaces['bores']):
        failures.append('mesh_bore_dimension')
    if any(row['triangles'] == 0 for row in interfaces['seat_planes']):
        failures.append('mesh_seating_plane')
    volume_error = abs(quality['volume_mm3'] / receipt['exact_CAD_volume_mm3'] - 1) if 'exact_CAD_volume_mm3' in receipt else None
    bounds_error = float(np.abs(np.array([vertices.min(0), vertices.max(0)]) - receipt['exact_CAD_bounds_mm']).max()) if 'exact_CAD_bounds_mm' in receipt else None
    if volume_error is not None and volume_error > .002:
        failures.append('mesh_volume_error_to_exact_CAD')
    if bounds_error is not None and bounds_error > .06:
        failures.append('mesh_bounds_error_to_exact_CAD')
    result = {'candidate_STL_sha256': sha(candidate), 'BRep_receipt_sha256': sha(brep_receipt),
              'exact_CAD_surface_samples_sha256': sha(samples_path), 'STEP_sha256': receipt['STEP_sha256'],
              'audit_source_sha256': sha(__file__), 'libigl_version': version('libigl'), 'numpy_version': np.__version__,
              'CAD_sampling': receipt['CAD_sampling'], 'distance_limit_mm': .06, 'scope': 'sampled bidirectional distances, not a continuous bound',
              'mesh_to_exact_CAD': receipt['results']['candidate_STL'], 'exact_CAD_to_mesh': inverse,
              'topology': quality, 'self_intersection_pairs': int(len(pairs)), 'interface_dimensions': interfaces,
              'relative_mesh_volume_error_to_exact_CAD': volume_error, 'relative_volume_error_limit': .002,
              'mesh_bounds_error_to_exact_CAD_mm': bounds_error, 'bounds_error_limit_mm': .06,
              'historical_receipt_missing_volume_or_bounds': volume_error is None or bounds_error is None,
              'failures': failures, 'status': 'passed' if not failures else 'rejected', 'manufacturing_authorized': False}
    output.mkdir(parents=True)
    (output / 'cad-mesh-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate', 'brep_receipt', 'samples', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--expected-samples-sha256', help='Explicit sample identity for historical receipts without this field')
    args = parser.parse_args()
    result = run(args.candidate, args.brep_receipt, args.samples, args.output, args.expected_samples_sha256)
    if result['status'] != 'passed':
        raise SystemExit(2)
