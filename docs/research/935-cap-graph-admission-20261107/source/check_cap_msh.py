"""Read back the actual native cap MSH and join every node and oriented facet."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def canonical(triangles):
    rows = np.asarray(triangles, dtype=np.int64)
    start = rows.argmin(axis=1)
    rows = np.take_along_axis(rows, (start[:, None]+np.arange(3)) % 3, axis=1)
    return rows[np.lexsort(rows.T[::-1])]


def controls():
    rows = np.array([[5, 2, 3], [9, 0, 4]])
    assert np.array_equal(canonical(rows), canonical(np.roll(rows[::-1], 1, axis=1)))
    assert not np.array_equal(canonical(rows), canonical(rows[:, ::-1]))
    return {'cyclic_order_and_row_permutation_match': True, 'reversed_orientation_refused': True}


def main():
    import gmsh
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    spec = importlib.util.spec_from_file_location('cap_msh_io', job['diagnostic'])
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False); tested = controls()
    with np.load(job['cap'], allow_pickle=False) as data:
        xy = data['vertices'][:, data['projection_axes']]; expected = data['triangles']
    order = np.lexsort((xy[:, 1], xy[:, 0])); rank = np.empty(len(xy), dtype=np.int64); rank[order] = np.arange(len(xy))
    assert np.all(np.any(xy[order][1:] != xy[order][:-1], axis=1))
    gmsh.initialize()
    try:
        gmsh.open(str(job['msh']))
        labels, coordinates, _ = gmsh.model.mesh.getNodes(); coordinates = coordinates.reshape(-1, 3)
        assert len(labels) == len(xy) and np.all(coordinates[:, 2] == 0)
        native_order = np.lexsort((coordinates[:, 1], coordinates[:, 0]))
        assert np.array_equal(coordinates[native_order, :2].view(np.uint64), xy[order].view(np.uint64))
        label_rank = {int(labels[row]): r for r, row in enumerate(native_order)}
        kinds, _, nodes = gmsh.model.mesh.getElements(2); assert list(kinds) == [2]
        actual = np.asarray([[label_rank[int(x)] for x in t] for t in nodes[0].reshape(-1, 3)], dtype=np.int64)
        assert np.array_equal(canonical(actual), canonical(rank[expected]))
    finally:
        gmsh.finalize()
    report = dict(schema='935-cap-native-readback-1', source_sha256=helper.sha(__file__),
        job_sha256=helper.sha(args.job), controls=tested, nodes=len(xy), triangles=len(expected),
        native_msh_sha256=helper.sha(job['msh']), cap_sha256=helper.sha(job['cap']),
        all_native_node_coordinate_bits_joined=True, every_oriented_triangle_joined=True,
        full_head_modified=False, volume_remesh_admitted=False, physics_admitted=False,
        manufacturing_qualified=False, new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
