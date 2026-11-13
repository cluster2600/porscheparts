"""One source-bound enlargement by complete stars of pinched cavity vertices."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import time

import igl
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()

    def load(name):
        spec = importlib.util.spec_from_file_location('cavity_vertex_'+name, job[name])
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    io, topology = (load(k) for k in ('io', 'topology'))
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    control = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3],
                        [0, 5, 4], [0, 4, 6], [4, 5, 6], [5, 0, 6]], dtype=np.int64)
    fans, border = topology.vertex_fans(control, 7)
    assert fans.tolist() == [2, 1, 1, 1, 1, 1, 1] and len(border) == 0
    assert np.array_equal(igl.is_vertex_manifold(control), fans == 1)
    refused = json.loads(Path(job['cavity_surface_report']).read_text())
    assert not refused['geometry_export_gate_passed'] and not refused['vertex_manifold'] and refused['nonmanifold_edges'] == 0
    with np.load(job['cavity'], allow_pickle=False) as data:
        nodes, faces, source_nodes, current = data['nodes'], data['new_boundary'], data['source_node_ids'], data['source_cell_ids']
    used = np.unique(faces); compact = np.searchsorted(used, faces)
    assert io.sha(job['cavity_surface']) == refused['input_sha256']
    with np.load(job['cavity_surface'], allow_pickle=False) as data:
        assert np.array_equal(data['vertices'].view(np.uint64), nodes[used].view(np.uint64))
        assert np.array_equal(data['triangles'], compact)
    fans, border = topology.vertex_fans(compact, len(used))
    assert len(border) == 0 and np.array_equal(igl.is_vertex_manifold(compact), fans == 1)
    bad = used[np.flatnonzero(fans > 1)]
    assert len(bad) > 0 and bad.max() < len(source_nodes)
    source_bad = source_nodes[bad]
    with np.load(job['volume'], allow_pickle=False) as data:
        cells = data['tets']
    mark = np.zeros(int(cells.max())+1, dtype=bool); mark[source_bad] = True
    selected = np.zeros(len(cells), dtype=bool); selected[current] = True
    for start in range(0, len(cells), 200000):
        selected[start:start+200000] |= mark[cells[start:start+200000]].any(axis=1)
    ids = np.flatnonzero(selected); additions = np.setdiff1d(ids, current); assert len(additions) > 0
    path = args.output/'private-vertex-closed-selection.npz'; np.savez_compressed(path, cell_ids=ids)
    trace = args.output/'private-pinched-vertices.npy'; np.save(trace, source_bad)
    report = dict(schema='935-cavity-vertex-star-closure-1', source_sha256=io.sha(__file__),
        job_sha256=io.sha(args.job), input_volume_sha256=io.sha(job['volume']),
        controls={'two_closed_tetrahedra_pinched_only_at_one_vertex': True,
                  'native_and_corner_graph_vertex_fans_agree': True},
        pinched_vertices=len(bad), parent_cells_before=len(current), added_parent_cells=len(additions),
        parent_cells_after=len(ids), complete_parent_vertex_stars_scanned=True,
        private_selection_sha256=io.sha(path), private_pinched_vertices_sha256=io.sha(trace),
        new_cavity_audit_pending=True, head_volume_modified=False, remeshing_prepared=False,
        physics_admitted=False, manufacturing_qualified=False, new_paid_compute_usd=0,
        seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
