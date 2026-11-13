"""Independently inspect every native owner/neighbour edge of the frozen cell graph."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regions(owner, neighbour, cells):
    assert len(owner) == len(neighbour) and cells > 0
    assert np.all((owner >= 0) & (owner < cells)) and np.all((neighbour >= 0) & (neighbour < cells))
    assert np.all(owner != neighbour)
    graph = coo_matrix((np.ones(len(owner), dtype=bool), (owner, neighbour)), shape=(cells, cells)).tocsr()
    return connected_components(graph, directed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    assert regions(np.array([0, 1]), np.array([1, 2]), 3)[0] == 1
    assert regions(np.array([0, 2]), np.array([1, 3]), 4)[0] == 2
    assert regions(np.array([0]), np.array([1]), 3)[0] == 2
    tree = ast.parse(Path(job['reader']).read_text())
    function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'values')
    namespace = {'np': np, 're': re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), job['reader'], 'exec'), namespace)
    owner = namespace['values'](Path(job['owner']), 1, np.int64)
    neighbour = namespace['values'](Path(job['neighbour']), 1, np.int64)
    assert len(owner) == 30072005 and len(neighbour) == 21853547
    cells = 12981388
    assert np.all((owner >= 0) & (owner < cells)) and np.all((neighbour >= 0) & (neighbour < cells))
    assert np.array_equal(np.bincount(owner, minlength=cells)+np.bincount(neighbour, minlength=cells), np.full(cells, 4))
    count, labels = regions(owner[:len(neighbour)], neighbour, cells)
    sizes = np.bincount(labels)
    args.output.mkdir(mode=0o700, exist_ok=False)
    np.save(args.output/'private-native-cell-regions.npy', labels)
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), cells=cells,
                  native_faces=len(owner), all_internal_face_edges_examined=len(neighbour),
                  connected_cell_regions=int(count), component_sizes_descending=np.sort(sizes)[::-1].tolist(),
                  every_cell_has_four_native_faces=True, all_native_owner_neighbour_indices_valid=True,
                  all_cells_reachable_by_shared_internal_faces=count == 1,
                  connected_disconnected_and_isolated_controls_passed=True,
                  native_face_geometric_orientation_checked=False, geometry_modified=False,
                  field_solve_executed=False, physics_admitted=False, manufacturing_qualified=False,
                  seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
