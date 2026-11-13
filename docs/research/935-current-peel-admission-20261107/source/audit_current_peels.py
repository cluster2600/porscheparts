"""Read-only continuation of the frozen exact peel contract on the kernel candidate."""
import argparse
from collections import Counter
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
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    began = time.monotonic()
    args.output.mkdir(mode=0o700, exist_ok=False)

    def module(name):
        spec = importlib.util.spec_from_file_location(name, job[name])
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result

    operator, attribution, record = (module(name) for name in ('operator', 'attribution', 'record'))
    controls = {'operator': operator.controls(), 'surface_join': attribution.controls(record.records)}
    (args.output/'controls.json').write_text(json.dumps(controls, indent=2)+'\n')
    mesh_hash = sha(job['mesh'])
    assert mesh_hash == 'd618763474f2eeb7bf680ce18f6f2efce22795e538263b7dfc639ffb68be62c5'
    assert sha(job['surface']) == '16553493632d689fbb78f18403d7a3734a7ed4a111f67cf89f93864cfbec57e9'
    assert sha(job['features']) == 'e5087c3cd5c90208acb56adff830bb39edc58bb0d93362b9a57b5cbf944b70f3'
    condition = json.loads(Path(job['condition_report']).read_text())
    volume = json.loads(Path(job['volume_report']).read_text())
    parent = json.loads(Path(job['surface_report']).read_text())
    assert condition['input_mesh_sha256'] == volume['mesh_sha256'] == mesh_hash
    assert volume['all_cells_positive_for_stored_binary_coordinates']
    assert volume['actual_complete_boundary_and_orientation_exact']
    assert not volume['diagnostic_quality_passed'] and not condition['absolute_quality_gate_passed']
    assert parent['candidate_surface_sha256'] == sha(job['surface'])
    assert parent['candidate_tags_sha256'] == sha(job['tags'])
    assert condition['private_ids_sha256'] == sha(job['severe_ids'])
    with np.load(job['mesh'], allow_pickle=False) as data:
        nodes, cells, boundary = data['nodes'], data['tets'], data['boundary']
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    assert np.array_equal(boundary, faces)
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    del boundary
    tags = np.load(job['tags'], allow_pickle=False)
    with np.load(job['severe_ids'], allow_pickle=False) as data:
        ids = data['cell_ids']
    assert len(ids) == condition['counts_kappa_F_at_least']['1e12'] == 15251
    assert len(np.unique(ids)) == len(ids) and np.all((ids >= 0) & (ids < len(cells)))
    rows, labels, _, _, caps = attribution.surface_join(cells[ids], faces, tags, len(nodes), record.records)
    np.savez_compressed(args.output/'private-current-attribution.npz', cell_ids=ids,
                        source_boundary_face_ids=rows, construction_tags=labels, vertex_cap_memberships=caps)
    with np.load(job['mapping'], allow_pickle=False) as data:
        mapping, used = data['mapping'], data['used_source_vertices']
    inverse = np.full(len(mapping), -1, dtype=np.int64)
    inverse[used] = np.arange(len(used))
    old = np.load(job['features'], allow_pickle=False)
    marked = inverse[mapping[np.column_stack((old//len(mapping), old % len(mapping)))]]
    assert np.all(marked >= 0)
    protected = {operator.edge_key(edge) for edge in marked if edge[0] != edge[1]}
    bound = Fraction(512, 1 << 52)*max(Fraction.from_float(float(x)) for x in np.ptp(vertices, axis=0))
    parent_bound = Fraction.from_float(parent['composed_complete_surface_correspondence_bound_nominal_mm'])
    assert parent_bound+bound < Fraction.from_float(.01)
    reasons, proposed = Counter(), []
    for position, cell_id in enumerate(ids):
        slots = np.flatnonzero(rows[position] >= 0).tolist()
        if len(slots) != 2:
            reasons['not_two_boundary_faces'] += 1
            continue
        cell = cells[cell_id]
        if caps[position].any() or np.any(tags[rows[position, slots]] != 0):
            reasons['construction_cap_constraint'] += 1
            continue
        diagonal = sorted(set(map(int, cell[operator.FACES[slots[0]]])) & set(map(int, cell[operator.FACES[slots[1]]])))
        other = sorted(set(map(int, cell))-set(diagonal))
        if operator.edge_key(diagonal) in protected:
            reasons['protected_marked_curve'] += 1
            continue
        verdict, proof = operator.geometry(nodes[cell], slots, bound)
        reasons[verdict] += 1
        if proof is not None:
            proposed.append((int(cell_id), slots, diagonal, other, proof, rows[position, slots]))
    incidence = operator.incidences(cells, [edge for row in proposed for edge in row[2:4]])
    skin_incidence = operator.incidences(faces, [row[3] for row in proposed])
    admitted = []
    for row in proposed:
        cell_id, slots, diagonal, other, proof, source_rows = row
        if incidence[operator.edge_key(diagonal)] != [cell_id]:
            reasons['old_diagonal_tet_valence_not_one'] += 1
        elif skin_incidence[operator.edge_key(other)]:
            reasons['new_diagonal_already_on_surface'] += 1
        elif not operator.links(cells[incidence[operator.edge_key(other)]], other):
            reasons['new_diagonal_source_link_not_simple_cycle'] += 1
        else:
            admitted.append(row)
    packed, occupied = [], set()
    for row in sorted(admitted, key=lambda item: (item[4]['removed_volume'], item[0])):
        vertices_here = set(map(int, cells[row[0]]))
        if occupied & vertices_here:
            reasons['simultaneous_vertex_conflict'] += 1
            continue
        occupied.update(vertices_here)
        packed.append(row)
    assert len(packed)+reasons['simultaneous_vertex_conflict'] == len(admitted)
    assert len(occupied) == 4*len(packed)
    proposal = args.output/'private-admitted-peels.npz'
    np.savez_compressed(proposal, cell_ids=np.asarray([row[0] for row in packed], dtype=np.int64),
                        boundary_slots=np.asarray([row[1] for row in packed], dtype=np.int64).reshape(-1, 2),
                        source_surface_face_ids=np.asarray([row[5] for row in packed], dtype=np.int64).reshape(-1, 2))
    maximum = max((row[4]['deviation'] for row in packed), default=Fraction(0))
    loss = sum((row[4]['removed_volume'] for row in packed), Fraction(0))
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), input_mesh_sha256=mesh_hash,
                  controls=controls, severe_cells_examined=len(ids), source_surface_faces_scanned=len(faces),
                  cells_by_boundary_face_count=np.bincount((rows >= 0).sum(axis=1), minlength=5).tolist(),
                  exact_geometry_and_global_incidence_admitted=len(admitted), vertex_disjoint_peels_admitted=len(packed),
                  reasons=dict(reasons), fixed_graph_deviation_limit_nominal_mm=float(bound),
                  maximum_proposed_exact_graph_deviation_fraction=[str(maximum.numerator), str(maximum.denominator)],
                  parent_complete_correspondence_bound_nominal_mm=float(parent_bound),
                  proposed_total_correspondence_bound_fraction=[str((parent_bound+maximum).numerator), str((parent_bound+maximum).denominator)],
                  exact_material_loss_fraction=[str(loss.numerator), str(loss.denominator)],
                  private_proposals_sha256=sha(proposal),
                  private_attribution_sha256=sha(args.output/'private-current-attribution.npz'),
                  geometry_modified=False, printing_master_changed=False, independent_proposal_verification_pending=bool(packed),
                  physics_admitted=False, manufacturing_qualified=False, new_paid_compute_usd=0,
                  seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
