#!/usr/bin/env python3
"""Screen a fixed boundary-candidate subset against Mi F/G; never register it."""

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
EDGE_PAIRS = tuple(itertools.combinations(range(4), 2))
LIMIT_MM = 100.0  # Generous diagnostic rejection only, not an engineering tolerance.


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def nominal_network(data):
    mi = data['mi']
    if mi['unit']['interpreted_unit'] != 'mm':
        raise ValueError('Mi millimetre interpretation is required')
    edges = [e for e in mi['longitudinal_projections'] if (e['from'], e['to']) == ('F', 'G')]
    if len(edges) != 1 or edges[0]['dimension_kind'] != 'longitudinal_projection':
        raise ValueError('One explicit projected F-to-G dimension is required')
    projection = edges[0]['printed_value']
    result = []
    for key, x in [('F', 0.0), ('G', projection)]:
        points = [p for p in mi['points'] if p['point_id'] == key]
        if len(points) != 1:
            raise ValueError('Missing or duplicate F/G contact')
        p = points[0]
        if p['contact_definition_printed'] != 'Center of 25 x 34mm Hole':
            raise ValueError('F/G must describe the printed aperture centre')
        width = p['half_width_if_equal_sides']
        heights = p['height_above_printed_datum_line']
        if width is None or width <= 0 or 2 * width != p['combined_equal_left_right_width'] or set(heights) != {'hole_center'}:
            raise ValueError('Missing or contradictory F/G width/contact height')
        result.extend([(x, width, heights['hole_center']), (x, -width, heights['hole_center'])])
    network = np.asarray(result, dtype=float)
    if not np.isfinite(network).all() or not math.isfinite(projection) or projection <= 0:
        raise ValueError('Finite positive F/G longitudinal span required')
    return network


def candidate_points(audit, source_ids, vertices):
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError('Expected finite Nx3 retained vertices')
    rows = [r for r in audit['candidates'] if r['broad_25x34_size_candidate']]
    if not 4 <= len(rows) <= 32 or len(rows) != audit['broad_25x34_size_candidates']:
        raise ValueError('Expected a bounded complete subset of 4 to 32 candidates')
    used, components, centres = set(), set(), []
    for row in rows:
        component = row['component_id']
        key = f'component_{component}'
        if component in components or key not in source_ids:
            raise ValueError('Missing or duplicate candidate component IDs')
        components.add(component)
        ids = np.asarray(source_ids[key])
        if (ids.ndim != 1 or ids.dtype.kind not in 'iu' or len(ids) != row['vertices']
                or not len(ids) or ids.min() < 0 or ids.max() >= len(vertices)
                or len(np.unique(ids)) != len(ids) or used.intersection(ids.tolist())):
            raise ValueError('Foreign, repeated or invalid original vertex IDs')
        used.update(ids.tolist())
        centre = vertices[ids].astype(float).mean(axis=0)
        if not np.allclose(centre, row['centroid_vehicle_mm'], rtol=0, atol=1e-8):
            raise ValueError('Candidate centroid disagrees with original vertex IDs')
        centres.append(centre)
    return np.asarray(centres)


def screen(source, points):
    if (source.shape != (4, 3) or not np.isfinite(source).all() or points.ndim != 2
            or points.shape[1] != 3 or not 4 <= len(points) <= 32 or not np.isfinite(points).all()):
        raise ValueError('Finite four-point source and 4 to 32 candidates required')
    a, b = np.array(EDGE_PAIRS).T
    target = np.linalg.norm(source[a] - source[b], axis=1)
    assignments = np.array(list(itertools.permutations(range(len(points)), 4)), dtype=np.int16)
    q = points[assignments]
    errors = np.linalg.norm(q[:, a] - q[:, b], axis=2) - target
    maximum = np.abs(errors).max(axis=1)
    rms = np.sqrt(np.mean(errors ** 2, axis=1))
    return {
        'classification': 'source_contact_network_screen_not_registration',
        'source_network_order': ['F_side1', 'F_side2', 'G_side1', 'G_side2'],
        'source_edge_pairs': [list(p) for p in EDGE_PAIRS],
        'source_edge_lengths_mm': target.tolist(),
        'candidate_count': len(points), 'permutations_checked': len(assignments),
        'diagnostic_rejection': {'generous_all_edge_limit_mm': LIMIT_MM,
                                 'compatible_ordered_quartets': int((maximum <= LIMIT_MM).sum()),
                                 'limit_is_not_scanner_uncertainty_or_acceptance_tolerance': True},
        'minimum_six_edge_rms_mm': float(rms.min()),
        'minimum_worst_edge_error_mm': float(maximum.min()),
        'scope': 'Only the fixed upstream candidate subset; no absence claim about the full scan.',
        'ambiguity': 'Distance-only compatibility does not establish contact identities, physical side or surface normals.',
        'rigid_transform': None, 'engineering_admission': False,
        'new_contacts_identified': 0, 'geometry_modified': False,
    }


def verify_metrics(source, points, report):
    """Independent scalar distance table and combination-first enumeration."""
    table = {(i, j): math.dist(points[i], points[j]) for i in range(len(points)) for j in range(len(points))}
    target = [math.dist(source[a], source[b]) for a, b in EDGE_PAIRS]
    count, matches, best_rms, best_max = 0, 0, math.inf, math.inf
    for group in itertools.combinations(range(len(points)), 4):
        for assignment in itertools.permutations(group):
            errors = [table[assignment[a], assignment[b]] - t for (a, b), t in zip(EDGE_PAIRS, target)]
            worst = max(map(abs, errors))
            count += 1
            matches += worst <= LIMIT_MM
            best_rms = min(best_rms, math.sqrt(sum(e * e for e in errors) / 6))
            best_max = min(best_max, worst)
    if (len(points) != report['candidate_count'] or report['source_edge_pairs'] != [list(p) for p in EDGE_PAIRS]
            or count != report['permutations_checked'] or matches != report['diagnostic_rejection']['compatible_ordered_quartets']
            or report['diagnostic_rejection']['generous_all_edge_limit_mm'] != LIMIT_MM
            or not np.allclose(target, report['source_edge_lengths_mm'], rtol=0, atol=1e-8)
            or not math.isclose(best_rms, report['minimum_six_edge_rms_mm'], rel_tol=0, abs_tol=1e-8)
            or not math.isclose(best_max, report['minimum_worst_edge_error_mm'], rel_tol=0, abs_tol=1e-8)
            or report['engineering_admission'] or report['rigid_transform'] is not None
            or report['new_contacts_identified'] or report['geometry_modified']):
        raise ValueError('Independent metric or admission-gate verification failed')
    return {'method': 'scalar_pair_distance_table_combination_first_enumeration', 'passed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-data', 'audit', 'candidate-ids', 'vertices', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    for name in ('source', 'audit', 'candidate-ids'):
        parser.add_argument('--' + name + '-sha256', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'work') or output.exists():
        raise ValueError('Output must be a new private directory under work/')
    pinned = {args.source_data: args.source_sha256, args.audit: args.audit_sha256,
              args.candidate_ids: args.candidate_ids_sha256}
    for path, expected in pinned.items():
        if digest(path) != expected:
            raise ValueError('Pinned source/audit/ID hash mismatch')
    data, audit = json.loads(args.source_data.read_text()), json.loads(args.audit.read_text())
    if audit.get('candidate_source_ids_sha256') != args.candidate_ids_sha256:
        raise ValueError('Candidate ID hash disagrees with extractor audit binding')
    hashes = [h for p, h in audit['input_sha256'].items() if Path(p).name == 'verts_vehicle.npy']
    if len(hashes) != 1 or digest(args.vertices) != hashes[0]:
        raise ValueError('Retained vertex hash mismatch')
    pinned[args.vertices] = hashes[0]
    vertices = np.load(args.vertices, allow_pickle=False)
    with np.load(args.candidate_ids, allow_pickle=False) as ids:
        points = candidate_points(audit, ids, vertices)
    source = nominal_network(data)
    report = screen(source, points)
    report['independent_metric_verification'] = verify_metrics(source, points, report)
    if any(digest(p) != h for p, h in pinned.items()):
        raise ValueError('An input changed during screening')
    report['input_sha256'] = {p.name: h for p, h in pinned.items()}
    report['screen_sha256'] = digest(__file__)
    report['inputs_unchanged_after_run'] = True
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / 'screen.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report['diagnostic_rejection']))


if __name__ == '__main__':
    main()
