"""One source-bound enlargement by complete stars of pinched cavity edges."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()

    def load(name):
        spec = importlib.util.spec_from_file_location('cavity_edge_'+name, job[name])
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    io, op = (load(k) for k in ('io', 'operator'))
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    control = op.incidences(np.array([[0, 1, 2, 3], [0, 1, 3, 4]], dtype=np.int64), [(0, 1), (2, 4)])
    assert control[op.edge_key((0, 1))] == [0, 1] and control[op.edge_key((2, 4))] == []
    refused = json.loads(Path(job['cavity_surface_report']).read_text())
    assert not refused['geometry_export_gate_passed'] and refused['nonmanifold_edges'] > 0
    with np.load(job['cavity'], allow_pickle=False) as data:
        faces, source_nodes, current = data['new_boundary'], data['source_node_ids'], data['source_cell_ids']
    pairs = np.sort(faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    unique, counts = np.unique(pairs, axis=0, return_counts=True)
    pinched = unique[counts > 2]
    assert len(pinched) == refused['nonmanifold_edges'] and pinched.max() < len(source_nodes)
    edges = source_nodes[pinched]
    with np.load(job['volume'], allow_pickle=False) as data:
        cells = data['tets']
    incident = op.incidences(cells, edges)
    required = [cell for edge in edges for cell in incident[op.edge_key(edge)]]
    selected = np.union1d(current, required); additions = np.setdiff1d(selected, current)
    assert len(additions) > 0 and np.all(np.isin(current, selected))
    assert all(incident[op.edge_key(edge)] and np.all(np.isin(incident[op.edge_key(edge)], selected)) for edge in edges)
    path = args.output/'private-closed-selection.npz'; np.savez_compressed(path, cell_ids=selected)
    trace = args.output/'private-edge-stars.json'
    trace.write_text(json.dumps([{'source_edge': list(map(int, edge)), 'complete_parent_incident_cells': incident[op.edge_key(edge)]}
                                 for edge in edges], indent=2)+'\n')
    report = dict(schema='935-cavity-edge-star-closure-1', source_sha256=io.sha(__file__),
        job_sha256=io.sha(args.job), input_volume_sha256=io.sha(job['volume']),
        controls={'literal_complete_edge_incidence_and_absent_edge': True},
        pinched_edges=len(edges), parent_cells_before=len(current), added_parent_cells=len(additions),
        parent_cells_after=len(selected), full_parent_edge_incidence_scanned=True,
        every_target_edge_star_included=True, private_selection_sha256=io.sha(path),
        private_edge_stars_sha256=io.sha(trace), independent_new_cavity_audit_pending=True,
        head_volume_modified=False, remeshing_prepared=False, physics_admitted=False,
        manufacturing_qualified=False, new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert io.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
