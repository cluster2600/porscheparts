"""Remove whole rejected strip hypotheses without changing thresholds or the parent."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compose(data, rejected):
    labels = data['source_untried_pair_ids']
    assert set(rejected) <= set(map(int, labels[labels >= 0]))
    keep = ~np.isin(labels, sorted(rejected))
    assert np.all(keep[labels == -1])
    result = {}
    for key, values in data.items():
        if key in ('points', 'global_node_ids'):
            result[key] = values.copy()
        else:
            assert len(values) == len(labels), key
            result[key] = values[keep]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('mesh', 'inspection', 'expected-mesh-sha256', 'expected-inspection-sha256', 'output'):
        parser.add_argument('--'+name, required=True, type=Path if name in ('mesh', 'inspection', 'output') else str)
    args = parser.parse_args()
    assert sha(args.mesh) == args.expected_mesh_sha256 and sha(args.inspection) == args.expected_inspection_sha256
    inspection = json.loads(args.inspection.read_text()); assert inspection['mesh_sha256'] == args.expected_mesh_sha256
    assert inspection['parent_vertices_faces_and_all_provenance_preserved'] and inspection['npz_and_obj_exact_readback']
    with np.load(args.mesh, allow_pickle=False) as data:
        base = {key: data[key] for key in data.files}
    rejected = set(inspection['rejected_untried_pair_ids']); result = compose(base, rejected)
    args.output.mkdir(mode=0o700, exist_ok=False)
    np.savez_compressed(args.output/'candidate.npz', **result)
    with (args.output/'candidate.obj').open('w') as stream:
        for point in result['points']:
            stream.write('v '+' '.join(format(float(x), '.17g') for x in point)+'\n')
        for face in result['triangles']:
            stream.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')
    assert sha(args.mesh) == args.expected_mesh_sha256 and sha(args.inspection) == args.expected_inspection_sha256
    report = dict(source_sha256=sha(__file__), input_mesh_sha256=args.expected_mesh_sha256,
                  inspection_sha256=args.expected_inspection_sha256, mesh_sha256=sha(args.output/'candidate.npz'),
                  obj_sha256=sha(args.output/'candidate.obj'), removed_whole_pairs=len(rejected),
                  retained_pairs=len(np.unique(result['source_untried_pair_ids'][result['source_untried_pair_ids'] >= 0])),
                  triangles=len(result['triangles']), parent_faces_removed=0, coordinates_changed=0,
                  thresholds_relaxed=False, alternative_reselection=False, downstream_checks_pending=True,
                  physical_acceptance=False, manufacturing_authorized=False)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
