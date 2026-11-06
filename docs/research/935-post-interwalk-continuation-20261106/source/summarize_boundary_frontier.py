"""Summarise every saved boundary descriptor; grant no cap or physical admission."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def category(row):
    origins = {int(k) for k, value in row['edge_origin_counts'].items() if value}
    if 1 not in origins:
        return 'no_actual_acquired_edge'
    if not origins <= {1, 6, 7, 8, 9}:
        return 'other_boundary_origin_present'
    if row['repeated_coordinate_visits']:
        return 'repeated_coordinate_visits'
    if row['affine_rank'] < 2:
        return 'rank_below_two'
    if not 3 <= row['edges'] <= 128:
        return 'outside_3_to_128_edge_study_scope'
    if row['bounds_diagonal_nominal_mm'] > 3:
        return 'outside_3_mm_diagonal_study_scope'
    if row['plane_maximum_residual_nominal_mm'] > .25:
        return 'compact_nonplanar_frontier_needs_new_admission'
    return 'compact_planar_frontier_still_needs_full_admission'


def summarise(rows, expected_edges, expected_walks):
    assert len(rows) == expected_walks
    assert [row['curve'] for row in rows] == list(range(len(rows)))
    assert sum(row['edges'] for row in rows) == expected_edges
    counts, edges, sizes = Counter(), Counter(), Counter()
    flags = Counter()
    for row in rows:
        assert sum(row['edge_origin_counts'].values()) == row['edges'] == row['vertices']
        assert row['closure_authorized'] is False and row['physical_classification'] == 'unreviewed'
        name = category(row)
        counts[name] += 1; edges[name] += row['edges']
        size = next(label for upper, label in ((3, '3'), (4, '4'), (8, '5_to_8'),
            (32, '9_to_32'), (128, '33_to_128'), (float('inf'), 'over_128')) if row['edges'] <= upper)
        sizes[size] += 1
        flags['repeated_coordinate_visits'] += bool(row['repeated_coordinate_visits'])
        flags['rank_below_two'] += row['affine_rank'] < 2
        flags['over_128_edges'] += row['edges'] > 128
        flags['over_3_nominal_mm'] += row['bounds_diagonal_nominal_mm'] > 3
        flags['over_0_25_nominal_mm_plane_residual'] += (
            row['plane_maximum_residual_nominal_mm'] is not None and row['plane_maximum_residual_nominal_mm'] > .25)
    assert sum(counts.values()) == expected_walks and sum(edges.values()) == expected_edges
    return dict(complete_walks=expected_walks, complete_boundary_edges=expected_edges,
        ordered_first_reason_walks=dict(counts), ordered_first_reason_edges=dict(edges),
        edge_count_bins=dict(sizes), overlapping_geometry_flags=dict(flags),
        first_reason_priority=['no_actual_acquired_edge', 'other_boundary_origin_present',
            'repeated_coordinate_visits', 'rank_below_two', 'outside_3_to_128_edge_study_scope',
            'outside_3_mm_diagonal_study_scope', 'compact_nonplanar_frontier_needs_new_admission',
            'compact_planar_frontier_still_needs_full_admission'],
        categories_are_not_physical_roles_or_root_cause_proofs=True,
        original_compact_scope_bounds_not_relaxed=True,
        projection_normal_ancestry_native_and_support_admission_not_granted=True,
        geometry_modified=False, physical_acceptance=False, manufacturing_authorized=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(Path(job['surface_proof']).read_text())
    assert proof['surface_study_checks_passed'] and proof['mesh_sha256'] == sha(job['mesh'])
    assert proof['source_sha256'] == sha(job['surface_inspector'])
    rows = json.loads(Path(job['curve_review']).read_text())
    result = summarise(rows, proof['remaining_boundary_edges'], proof['remaining_boundary_walks'])
    result.update(source_sha256=sha(__file__), job_sha256=sha(args.job),
        mesh_sha256=sha(job['mesh']), surface_proof_sha256=sha(job['surface_proof']),
        complete_curve_review_sha256=sha(job['curve_review']))
    args.output.mkdir(mode=0o700, exist_ok=False)
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
