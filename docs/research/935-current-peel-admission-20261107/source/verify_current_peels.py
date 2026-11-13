"""Independently certify and export the current proposed calculation-surface peels."""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    args.output.mkdir(mode=0o700, exist_ok=False)
    assert sha(job['verifier']) == '986bae3440420f1220b790f5ae8d54a92ebd427fb0c4a2c706712733317ddaf6'
    spec = importlib.util.spec_from_file_location('independent_fraction_peel', job['verifier'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    tested = helper.controls()
    (args.output/'controls.json').write_text(json.dumps(tested, indent=2)+'\n')
    proposal_root = Path(job['proposal_root'])
    admission = json.loads((proposal_root/'report.json').read_text())
    proposal = proposal_root/'private-admitted-peels.npz'
    assert admission['source_sha256'] == job['audit_source_sha256']
    assert sha(proposal) == admission['private_proposals_sha256']
    assert sha(job['mesh']) == admission['input_mesh_sha256'] == 'd618763474f2eeb7bf680ce18f6f2efce22795e538263b7dfc639ffb68be62c5'
    with np.load(proposal, allow_pickle=False) as data:
        ids, slots, rows = data['cell_ids'], data['boundary_slots'], data['source_surface_face_ids']
    assert len(ids) == admission['vertex_disjoint_peels_admitted'] > 0
    assert len(np.unique(ids)) == len(ids) and slots.shape == rows.shape == (len(ids), 2)
    with np.load(job['mesh'], allow_pickle=False) as data:
        nodes, cells, boundary = data['nodes'], data['tets'], data['boundary']
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    assert np.array_equal(boundary, faces)
    del boundary
    assert np.all((ids >= 0) & (ids < len(cells)))
    assert np.all((slots >= 0) & (slots < 4)) and np.all(slots[:, 0] != slots[:, 1])
    assert np.all((rows >= 0) & (rows < len(faces))) and np.all(rows[:, 0] != rows[:, 1])
    assert len(np.unique(cells[ids])) == 4*len(ids), 'Proposed patches share vertices'
    tags = np.load(job['tags'], allow_pickle=False)
    assert np.all(tags[rows] == 0)
    assert not np.isin(cells[ids], np.unique(faces[tags > 0])).any()
    with np.load(job['mapping'], allow_pickle=False) as data:
        mapping, used = data['mapping'], data['used_source_vertices']
    inverse = np.full(len(mapping), -1, dtype=np.int64)
    inverse[used] = np.arange(len(used))
    original = np.load(job['features'], allow_pickle=False)
    curves = inverse[mapping[np.column_stack((original//len(mapping), original % len(mapping)))]]
    assert np.all(curves >= 0)
    protected = {helper.key(a, b) for a, b in curves if a != b}
    bound = Fraction(512, 1 << 52)*max(Fraction.from_float(float(x)) for x in np.ptp(vertices, axis=0))
    parent = json.loads(Path(job['surface_report']).read_text())
    parent_bound = Fraction.from_float(parent['composed_complete_surface_correspondence_bound_nominal_mm'])
    maximum, loss, old_edges, new_edges, replacement_faces = Fraction(0), Fraction(0), [], [], []
    for cell_id, old_slots, source_rows in zip(ids, slots, rows):
        cell = cells[cell_id]
        old_faces = cell[helper.PATTERN[old_slots]]
        assert np.array_equal(np.sort(old_faces, axis=1), np.sort(faces[source_rows], axis=1))
        diagonal = sorted(set(map(int, old_faces[0])) & set(map(int, old_faces[1])))
        alternate = sorted(set(map(int, cell))-set(diagonal))
        assert len(diagonal) == len(alternate) == 2 and helper.key(*diagonal) not in protected
        delta, removed, _, new = helper.patch_proof(nodes[cell], old_slots.tolist(), bound)
        maximum = max(maximum, delta)
        loss += removed
        old_edges.append(diagonal)
        new_edges.append(alternate)
        replacement_faces.append(cell[np.asarray(new)])
    assert parent_bound+maximum < Fraction.from_float(.01)
    incident = helper.all_edge_cells(cells, {helper.key(*edge) for edge in old_edges+new_edges})
    on_surface = helper.all_edge_cells(faces, {helper.key(*edge) for edge in new_edges})
    for cell_id, previous, alternate in zip(ids, old_edges, new_edges):
        assert incident[helper.key(*previous)] == [int(cell_id)]
        assert not on_surface[helper.key(*alternate)]
        helper.cycle_link(cells[incident[helper.key(*alternate)]], alternate)
    changed = faces.copy()
    changed[rows.reshape(-1)] = np.asarray(replacement_faces).reshape(-1, 3)
    assert np.array_equal(changed[tags > 0], faces[tags > 0])
    retained = np.ones(len(cells), dtype=bool)
    retained[ids] = False
    kept = cells[retained]
    volume_path, surface_path = args.output/'candidate-volume.npz', args.output/'candidate-surface.npz'
    np.savez_compressed(volume_path, nodes=nodes, tets=kept, boundary=changed)
    np.savez_compressed(surface_path, vertices=vertices, triangles=changed)
    np.save(args.output/'candidate-tags.npy', tags)
    np.save(args.output/'private-removed-source-cell-ids.npy', np.sort(ids))
    with np.load(volume_path, allow_pickle=False) as data:
        assert np.array_equal(data['nodes'].view(np.uint64), nodes.view(np.uint64))
        assert np.array_equal(data['tets'], kept) and np.array_equal(data['boundary'], changed)
    with np.load(surface_path, allow_pickle=False) as data:
        assert np.array_equal(data['vertices'].view(np.uint64), vertices.view(np.uint64))
        assert np.array_equal(data['triangles'], changed)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    report = dict(source_sha256=sha(__file__), frozen_fraction_verifier_sha256=sha(job['verifier']),
                  job_sha256=sha(args.job), controls=tested, input_mesh_sha256=sha(job['mesh']),
                  independent_exact_local_proofs=len(ids), removed_tetrahedra=len(ids), retained_tetrahedra=len(kept),
                  changed_surface_faces=2*len(ids), every_source_coordinate_bit_retained=True,
                  all_retained_tetrahedron_tuples_exact=True, every_cap_face_exact=True,
                  marked_curve_images_preserved=True, patches_pairwise_vertex_disjoint=True,
                  complete_source_edge_incidence_checked=True, every_new_edge_link_simple_cycle=True,
                  maximum_local_correspondence_bound_nominal_mm=helper.upper(maximum),
                  composed_complete_surface_correspondence_bound_nominal_mm=helper.upper(parent_bound+maximum),
                  exact_material_loss_fraction=[str(loss.numerator), str(loss.denominator)],
                  candidate_volume_sha256=sha(volume_path), candidate_surface_sha256=sha(surface_path),
                  candidate_tags_sha256=sha(args.output/'candidate-tags.npy'),
                  exact_same_surface_claimed=False, whole_surface_and_volume_validation_pending=True,
                  original_printing_master_changed=False, physics_admitted=False, manufacturing_qualified=False,
                  new_paid_compute_usd=0, seconds=time.monotonic()-began)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
