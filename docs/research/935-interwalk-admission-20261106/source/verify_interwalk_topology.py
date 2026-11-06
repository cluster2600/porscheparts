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
    spec = importlib.util.spec_from_file_location('independent_interwalk_topology', job['census_inspector'])
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    mesh = checker.load(args.mesh)
    census = checker.load(job['census'])
    boundaries = checker.load(args.surface_proof.parent/'private-boundaries-and-fans.npz')
    parent_faces = len(census['face_component_ids'])
    labels, after = checker.vertex_components(mesh['triangles'], len(mesh['points']), boundaries)
    before = census['component_V_E_F_B_chi_genus']
    assert after.shape == before.shape
    assert np.array_equal(labels[:parent_faces], census['face_component_ids'])
    assert np.array_equal(before[:, 0], after[:, 0])
    added = np.bincount(labels[parent_faces:], minlength=len(before))
    assert np.array_equal(after[:, 2]-before[:, 2], added)
    assert np.all(added % 2 == 0)
    pair_ids = mesh['source_continuation_pair_ids'][parent_faces:]
    accepted = np.unique(pair_ids)
    for pair_id in accepted:
        rows = np.flatnonzero(pair_ids == pair_id)
        assert len(rows) == 2
        local = int(pair_id)-job['first_global_pair_id']
        assert np.all(labels[parent_faces+rows] == census['selected_pair_component_ids'][local])
        assert census['selected_pair_walk_ids'][local, 0] != census['selected_pair_walk_ids'][local, 1]
    delta = after-before
    assert int(added.sum()) == proof['added_triangles']
    assert np.array_equal(delta[:, 4], delta[:, 2]-delta[:, 1])
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(args.mesh),
        full_surface_proof_sha256=sha(args.surface_proof),
        component_columns=['used_vertices', 'unique_edges', 'faces', 'boundary_walks', 'chi', 'genus'],
        before=before.tolist(), after=after.tolist(), delta=delta.tolist(),
        accepted_interwalk_pairs=len(accepted), source_component_count_unchanged=True,
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
