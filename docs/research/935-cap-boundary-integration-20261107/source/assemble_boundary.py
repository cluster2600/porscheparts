"""Insert one independently checked construction cap into a new head boundary."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def assemble(parent, tags, old, new):
    vertices, faces = parent['vertices'], parent['triangles']
    ids, removed = old['source_node_ids'], old['source_face_rows']
    original = new['original_node_rows']
    assert len(np.unique(ids)) == len(ids) and len(np.unique(removed)) == len(removed)
    assert np.array_equal(vertices[ids].view(np.uint64), old['vertices'].view(np.uint64))
    assert np.array_equal(faces[removed], ids[old['old_triangles']])
    assert np.array_equal(new['vertices'][original].view(np.uint64), old['vertices'].view(np.uint64))
    assert len(original) == len(ids) and len(np.unique(original)) == len(original)
    assert len(tags) == len(faces) and np.all(tags[removed] == tags[removed[0]]) and tags[removed[0]] > 0
    added = np.ones(len(new['vertices']), dtype=bool); added[original] = False
    mapping = np.empty(len(added), dtype=np.int64); mapping[original] = ids
    mapping[added] = np.arange(len(vertices), len(vertices)+int(added.sum()))
    keep = np.ones(len(faces), dtype=bool); keep[removed] = False
    result = dict(vertices=np.concatenate((vertices, new['vertices'][added])),
                  triangles=np.concatenate((faces[keep], mapping[new['triangles']])))
    result_tags = np.concatenate((tags[keep], np.full(len(new['triangles']), tags[removed[0]], dtype=tags.dtype)))
    return result, result_tags, mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    spec = importlib.util.spec_from_file_location('boundary_io', job['io'])
    io = importlib.util.module_from_spec(spec); spec.loader.exec_module(io)
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    checked = json.loads(Path(job['cap_check']).read_text())
    native = json.loads(Path(job['cap_native']).read_text())
    assert checked['cap_surface_graph_checks_passed'] and checked['all_cap_faces_clear_warning']
    assert checked['new_cap_sha256'] == native['cap_sha256'] == io.sha(job['new_cap'])
    with np.load(job['surface'], allow_pickle=False) as parent, np.load(job['old_cap'], allow_pickle=False) as old, np.load(job['new_cap'], allow_pickle=False) as new:
        result, tags, mapping = assemble(parent, np.load(job['tags'], allow_pickle=False), old, new)
        removed = old['source_face_rows']; old_vertices, old_faces = len(parent['vertices']), len(parent['triangles'])
        provenance = args.output/'private-cap-join.npz'
        np.savez_compressed(provenance, cap_local_to_global=mapping, removed_parent_face_rows=removed)
    surface = args.output/'candidate-surface.npz'; tag_path = args.output/'candidate-tags.npy'
    np.savez_compressed(surface, **result); np.save(tag_path, tags)
    report = dict(schema='935-cap-boundary-construction-1', source_sha256=io.sha(__file__),
        job_sha256=io.sha(args.job), parent_surface_sha256=io.sha(job['surface']),
        old_vertices=old_vertices, new_vertices=len(result['vertices']), old_triangles=old_faces,
        new_triangles=len(result['triangles']), replaced_parent_triangles=len(removed),
        candidate_surface_sha256=io.sha(surface), candidate_tags_sha256=io.sha(tag_path),
        private_join_sha256=io.sha(provenance), independent_join_check_pending=True,
        full_surface_check_pending=True, volume_modified=False, physics_admitted=False,
        manufacturing_qualified=False, new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
