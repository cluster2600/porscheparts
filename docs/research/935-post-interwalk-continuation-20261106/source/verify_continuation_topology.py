"""Bind an accepted saved surface to exact component Euler/boundary/genus changes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_change(mesh, parent, census, boundaries, parent_boundaries, checker, first_global):
    """Check exact component membership and actual combined topology of same-walk bands."""
    n = len(parent['triangles'])
    assert np.array_equal(mesh['points'], parent['points'])
    assert np.array_equal(mesh['triangles'][:n], parent['triangles'])
    before_labels, before = checker.vertex_components(parent['triangles'], len(parent['points']), parent_boundaries)
    labels, after = checker.vertex_components(mesh['triangles'], len(mesh['points']), boundaries)
    assert after.shape == before.shape
    assert np.array_equal(labels[:n], before_labels)
    assert np.array_equal(before[:, 0], after[:, 0])
    added = np.bincount(labels[n:], minlength=len(before))
    assert np.array_equal(after[:, 2]-before[:, 2], added)
    assert np.all(added % 2 == 0)
    pair_ids = mesh['source_continuation_pair_ids'][n:]
    accepted = np.unique(pair_ids)
    for pair_id in accepted:
        rows = np.flatnonzero(pair_ids == pair_id)
        assert len(rows) == 2
        local = int(pair_id)-first_global
        assert 0 <= local < len(census['selected_pair_edge_ids'])
        edges = census['selected_pair_edge_ids'][local]
        curves = census['edge_curve_ids'][edges]
        assert curves[0] == curves[1] == census['selected_pair_curve_ids'][local]
        components = before_labels[parent_boundaries['owners'][edges]]
        assert components[0] == components[1]
        assert np.all(labels[n+rows] == components[0])
    delta = after-before
    assert np.array_equal(delta[:, 4], delta[:, 2]-delta[:, 1])
    return before, after, delta, len(accepted)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'mesh', 'surface-proof', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(args.surface_proof.read_text())
    assert proof['surface_study_checks_passed'] and proof['mesh_sha256'] == sha(args.mesh)
    assert proof['parent_vertices_faces_and_all_provenance_preserved']
    assert proof['source_sha256'] == sha(job['surface_inspector_source'])
    spec = importlib.util.spec_from_file_location('independent_continuation_topology', job['topology_inspector_source'])
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    mesh, parent, census = map(checker.load, (args.mesh, job['mesh'], job['census']))
    boundaries = checker.load(args.surface_proof.parent/'private-boundaries-and-fans.npz')
    parent_boundaries = checker.load(job['boundaries'])
    before, after, delta, accepted = inspect_change(mesh, parent, census, boundaries,
        parent_boundaries, checker, job['first_global_pair_id'])
    assert int(delta[:, 2].sum()) == proof['added_triangles']
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(args.mesh),
        full_surface_proof_sha256=sha(args.surface_proof), parent_mesh_sha256=sha(job['mesh']),
        component_columns=['used_vertices', 'unique_edges', 'faces', 'boundary_walks', 'chi', 'genus'],
        before=before.tolist(), after=after.tolist(), delta=delta.tolist(),
        accepted_same_walk_pairs=accepted, source_component_count_unchanged=True,
        source_component_membership_unchanged=True, source_vertices_unchanged=True,
        exact_final_Euler_boundary_genus_verified=True,
        independent_band_genus_changes_not_multiplied=True,
        topology_is_not_anatomical_or_passage_validation=True,
        physical_acceptance=False, manufacturing_authorized=False)
    args.output.mkdir(mode=0o700, exist_ok=False)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
