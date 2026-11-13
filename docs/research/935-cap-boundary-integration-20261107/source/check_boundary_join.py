"""Independently rejoin all retained facets, source bits and mapped feature edges."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def feature_counts(faces, wanted):
    """Complete edge incidence with bounded temporary storage."""
    wanted = np.unique(wanted); counts = np.zeros(len(wanted), dtype=np.int64)
    for start in range(0, len(faces), 200000):
        rows = faces[start:start+200000]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            key = (np.minimum(rows[:, a], rows[:, b]).astype(np.uint64) << np.uint64(32)) | np.maximum(rows[:, a], rows[:, b]).astype(np.uint64)
            positions = np.searchsorted(wanted, key); valid = positions < len(wanted)
            hit = np.flatnonzero(valid); hit = hit[wanted[positions[hit]] == key[hit]]
            np.add.at(counts, positions[hit], 1)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    spec = importlib.util.spec_from_file_location('boundary_join_io', job['io'])
    io = importlib.util.module_from_spec(spec); spec.loader.exec_module(io)
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    cap_report = json.loads(Path(job['cap_check']).read_text())
    assert cap_report['new_cap_sha256'] == io.sha(job['new_cap']) and cap_report['cap_surface_graph_checks_passed']
    with np.load(job['surface'], allow_pickle=False) as parent, np.load(job['candidate'], allow_pickle=False) as candidate, np.load(job['old_cap'], allow_pickle=False) as old, np.load(job['new_cap'], allow_pickle=False) as new:
        v, f, nv, nf = parent['vertices'], parent['triangles'], candidate['vertices'], candidate['triangles']
        ids, removed, original = old['source_node_ids'], old['source_face_rows'], new['original_node_rows']
        assert np.array_equal(v[ids].view(np.uint64), old['vertices'].view(np.uint64))
        assert np.array_equal(f[removed], ids[old['old_triangles']])
        assert np.array_equal(nv[:len(v)].view(np.uint64), v.view(np.uint64))
        assert np.array_equal(new['vertices'][original].view(np.uint64), v[ids].view(np.uint64))
        additions = np.setdiff1d(np.arange(len(new['vertices'])), original)
        assert np.array_equal(nv[len(v):].view(np.uint64), new['vertices'][additions].view(np.uint64))
        local_to_global = np.full(len(new['vertices']), -1, dtype=np.int64)
        local_to_global[original] = ids; local_to_global[additions] = np.arange(len(v), len(nv))
        keep = np.setdiff1d(np.arange(len(f)), removed)
        assert np.array_equal(nf[:len(keep)], f[keep])
        assert np.array_equal(nf[len(keep):], local_to_global[new['triangles']])
        tags = np.load(job['tags'], allow_pickle=False); candidate_tags = np.load(job['candidate_tags'], allow_pickle=False)
        assert np.array_equal(candidate_tags[:len(keep)], tags[keep])
        assert np.all(tags[removed] == tags[removed[0]]) and tags[removed[0]] > 0
        assert np.all(candidate_tags[len(keep):] == tags[removed[0]])
        with np.load(job['mapping'], allow_pickle=False) as data:
            mapping, retained = data['mapping'], data['used_source_vertices']
        inverse = np.full(len(mapping), -1, dtype=np.int64); inverse[retained] = np.arange(len(retained))
        original_keys = np.load(job['features'], allow_pickle=False)
        marked = inverse[mapping[np.column_stack((original_keys//len(mapping), original_keys % len(mapping)))]]
        assert np.all(marked >= 0) and len(nv) < 1 << 32
        marked = marked[marked[:, 0] != marked[:, 1]]
        wanted = (np.minimum(marked[:, 0], marked[:, 1]).astype(np.uint64) << np.uint64(32)) | np.maximum(marked[:, 0], marked[:, 1]).astype(np.uint64)
        counts = feature_counts(nf, wanted); assert np.all(counts == 2)
        old_vertices, new_vertices, old_faces, new_faces = len(v), len(nv), len(f), len(nf)
    report = dict(schema='935-cap-boundary-independent-join-1', source_sha256=io.sha(__file__),
        job_sha256=io.sha(args.job), parent_surface_sha256=io.sha(job['surface']),
        candidate_surface_sha256=io.sha(job['candidate']), candidate_tags_sha256=io.sha(job['candidate_tags']),
        old_vertices=old_vertices, new_vertices=new_vertices, old_triangles=old_faces, new_triangles=new_faces,
        every_parent_point_bit_preserved=True, every_retained_oriented_facet_preserved=True,
        every_added_point_and_facet_joins_checked_cap=True, all_construction_tags_rejoined=True,
        mapped_required_edges=len(counts), every_mapped_required_edge_has_two_surface_uses=True,
        complete_correspondence_bound_nominal_mm=cap_report['composed_hypothesis_correspondence_nominal_mm_upper'],
        bound_scope='Identity off the replaced cap and the separately checked complete cap graph correspondence',
        full_surface_check_pending=True, volume_modified=False, physics_admitted=False,
        manufacturing_qualified=False, new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
