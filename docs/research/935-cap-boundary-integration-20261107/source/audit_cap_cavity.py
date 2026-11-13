"""Trace one cap vertex-star cavity and audit its fixed-boundary quality limits."""
import argparse
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def outer_faces(cells, patterns, inspector):
    outward = cells[:, patterns].reshape(-1, 3)
    keys = inspector.records(np.sort(outward, axis=1))
    _, first, inverse, counts = np.unique(keys, return_index=True, return_inverse=True, return_counts=True)
    assert np.all(counts <= 2)
    sums = np.bincount(inverse, weights=inspector.sign(outward))
    assert np.all(sums[counts == 2] == 0)
    selected = first[counts == 1]
    return outward[selected], selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()

    def load(name):
        spec = importlib.util.spec_from_file_location('cap_cavity_'+name, job[name])
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    io, inspector, attribution, quality, exact = (load(k) for k in ('io', 'inspector', 'attribution', 'quality', 'exact'))
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    admitted = json.loads(Path(job['new_surface_report']).read_text())
    assert admitted['geometry_export_gate_passed'] and admitted['input_sha256'] == io.sha(job['new_surface'])
    joined = json.loads(Path(job['join_report']).read_text())
    assert joined['parent_surface_sha256'] == io.sha(job['surface'])
    assert joined['candidate_surface_sha256'] == io.sha(job['new_surface'])
    positive = json.loads(Path(job['positive_report']).read_text())
    assert positive['mesh_sha256'] == io.sha(job['volume']) and positive['all_cells_positive_for_stored_binary_coordinates']
    assert positive['surface_sha256'] == io.sha(job['surface'])
    with np.load(job['volume'], allow_pickle=False) as data:
        nodes, cells, declared = data['nodes'], data['tets'], data['boundary']
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    assert np.array_equal(declared, faces)
    tags = np.load(job['tags'], allow_pickle=False)
    with np.load(job['old_cap'], allow_pickle=False) as data:
        seed = data['source_node_ids']; removed_faces = data['source_face_rows']
    mark = np.zeros(len(nodes), dtype=bool); mark[seed] = True
    selected = np.zeros(len(cells), dtype=bool)
    for start in range(0, len(cells), 200000):
        selected[start:start+200000] = mark[cells[start:start+200000]].any(axis=1)
    ids = np.flatnonzero(selected); local_cells = cells[ids]
    outer, slots = outer_faces(local_cells, attribution.FACES, inspector)
    source_rows, _, _, _, _ = attribution.surface_join(local_cells, faces, tags, len(nodes), inspector.records)
    source = source_rows.ravel()[slots]
    remove = np.isin(source, removed_faces)
    assert np.array_equal(np.sort(source[remove]), np.sort(removed_faces))
    # Rejoin each cavity interface against every actual parent cell, rather
    # than assuming an unpaired local face has one exterior neighbor.
    wanted = inspector.records(np.sort(outer, axis=1)); order = np.argsort(wanted)
    wanted = wanted[order]; counts = np.zeros(len(wanted), dtype=np.int64)
    outside = np.zeros(len(wanted), dtype=np.int64); orientations = np.zeros(len(wanted), dtype=np.int64)
    for start in range(0, len(cells), 200000):
        part = cells[start:start+200000]; outward = part[:, attribution.FACES].reshape(-1, 3)
        values = inspector.records(np.sort(outward, axis=1)); positions = np.searchsorted(wanted, values)
        hit = np.flatnonzero(positions < len(wanted)); hit = hit[wanted[positions[hit]] == values[hit]]
        at = positions[hit]; owners = start+hit//4
        np.add.at(counts, at, 1); np.add.at(outside, at, (~selected[owners]).astype(np.int64))
        np.add.at(orientations, at, inspector.sign(outward[hit]))
    is_interface = source[order] < 0
    assert np.all(counts == np.where(is_interface, 2, 1))
    assert np.all(outside == is_interface.astype(np.int64)) and np.all(orientations[is_interface] == 0)
    retained_outer = outer[~remove]; retained_source = source[~remove]
    used = np.unique(local_cells)
    assert np.array_equal(used[np.searchsorted(used, seed)], seed)
    with np.load(job['new_cap'], allow_pickle=False) as data:
        cap_v, cap_f, original = data['vertices'], data['triangles'], data['original_node_rows']
    assert np.array_equal(cap_v[original].view(np.uint64), nodes[seed].view(np.uint64))
    added = np.setdiff1d(np.arange(len(cap_v)), original)
    cap_map = np.full(len(cap_v), -1, dtype=np.int64)
    cap_map[original] = np.searchsorted(used, seed); cap_map[added] = np.arange(len(used), len(used)+len(added))
    compact_nodes = np.concatenate((nodes[used], cap_v[added]))
    old_outer = np.searchsorted(used, outer)
    new_outer = np.concatenate((np.searchsorted(used, retained_outer), cap_map[cap_f]))
    categories = np.r_[np.where(retained_source < 0, 0, 1), np.full(len(cap_f), 2)]
    values = [quality.quality_squared(compact_nodes[t]) for t in new_outer]
    necessary, warning = Q.from_float(.01)**3, Q.from_float(.01)**2
    census = {}
    for number, name in enumerate(('internal_interface', 'unchanged_head_skin_or_cap', 'refined_cap')):
        group = [q for i, q in enumerate(values) if categories[i] == number]
        census[name] = {'faces': len(group), 'forcing_face_count': sum(q < necessary for q in group),
            'warning_face_count': sum(q < warning for q in group), 'minimum_q_squared': float(min(group)) if group else None}

    def signed_volume(triangles):
        total = Q(0)
        for t in triangles:
            p = [tuple(Q.from_float(float(x)) for x in row) for row in compact_nodes[t]]
            total += exact.inner(p[0], exact.product(p[1], p[2]))/6
        return total

    old_volume = signed_volume(old_outer); new_volume = signed_volume(new_outer)
    delta = signed_volume(cap_map[cap_f])-signed_volume(old_outer[remove])
    assert old_volume > 0 and new_volume > 0 and new_volume-old_volume == delta
    payload = args.output/'private-cavity.npz'
    np.savez_compressed(payload, nodes=compact_nodes, old_tets=np.searchsorted(used, local_cells),
        old_boundary=old_outer, new_boundary=new_outer, boundary_categories=categories,
        source_cell_ids=ids, source_node_ids=used, added_cap_local_ids=added,
        retained_boundary_parent_rows=retained_source, new_cap_to_cavity=cap_map)
    surface_used = np.unique(new_outer)
    surface_path = args.output/'candidate-cavity-surface.npz'
    np.savez_compressed(surface_path, vertices=compact_nodes[surface_used], triangles=np.searchsorted(surface_used, new_outer))
    exact_path = args.output/'private-exact-volume.json'
    exact_path.write_text(json.dumps({'old_volume': str(old_volume), 'new_volume': str(new_volume),
                                     'signed_cap_delta': str(delta)}, indent=2)+'\n')
    with np.load(job['severe'], allow_pickle=False) as data:
        severe = int(selected[data['cell_ids']].sum())
    with np.load(job['native_bad'], allow_pickle=False) as data:
        native_bad = int(selected[data['cell_ids']].sum())
    report = dict(schema='935-cap-vertex-star-cavity-audit-1', source_sha256=io.sha(__file__),
        job_sha256=io.sha(args.job), input_volume_sha256=io.sha(job['volume']),
        original_cap_vertices=len(seed), selected_parent_cells=len(ids), selected_parent_nodes=len(used),
        old_cavity_boundary_faces=len(outer), new_cavity_boundary_faces=len(new_outer),
        replaced_parent_boundary_faces=int(remove.sum()),
        interface_faces_with_exactly_one_unchanged_exterior_neighbor=int(is_interface.sum()),
        all_interfaces_rejoined_against_complete_parent_volume=True,
        source_severe_cells_in_cavity=severe, source_native_bad_cells_in_cavity=native_bad,
        boundary_quality=census, old_signed_volume_nominal_mm3=float(old_volume),
        signed_cap_volume_change_nominal_mm3=float(delta), exact_cap_volume_delta_identity=True,
        private_cavity_sha256=io.sha(payload), candidate_cavity_surface_sha256=io.sha(surface_path),
        private_exact_volume_sha256=io.sha(exact_path),
        fixed_boundary_clears_necessary_tet_face_floor=all(c['forcing_face_count'] == 0 for c in census.values()),
        complete_cavity_surface_check_pending=True, remeshing_prepared=False, head_volume_modified=False,
        physics_admitted=False, manufacturing_qualified=False, new_paid_compute_usd=0,
        seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
