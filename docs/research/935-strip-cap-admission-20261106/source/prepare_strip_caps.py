"""Prepare exact parent-fan masks for independently admitted strip-border caps."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key:data[key] for key in data.files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(Path(job['admission_proof']).read_text())
    assert proof['admission_independently_verified'] and proof['mesh_sha256'] == sha(job['mesh'])
    assert proof['job_sha256'] == sha(job['admission_job'])
    control = json.loads(Path(job['native_control_proof']).read_text())
    assert control['native_controls_independently_verified'] and control['job_sha256'] == sha(job['native_control_job'])
    body, boundary = load(job['mesh']), load(job['boundaries'])
    selected = np.load(Path(job['admission'])/'private-admitted-walk-ids.npy', allow_pickle=False)
    assert len(selected) == proof['admitted_trials']
    decisions = json.loads((Path(job['admission'])/'private-all-walk-decisions.json').read_text())
    assert selected.tolist() == [row['curve'] for row in decisions if row['admitted']]
    spec = importlib.util.spec_from_file_location('frozen_halo_atlas', job['builder_source'])
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    flags = np.zeros(len(body['points']), dtype=bool)
    for curve in selected:
        a, b = boundary['offsets'][curve:curve+2]; ids = boundary['cycle_edges'][a:b]
        assert set(map(int, boundary['edge_origin_kind'][ids])) <= {1, 6}
        assert 6 in boundary['edge_origin_kind'][ids]
        flags[boundary['boundary'][ids, 0]] = True
    incident = defaultdict(list)
    for row in np.flatnonzero(flags[body['triangles']].any(axis=1)):
        for vertex in body['triangles'][row]:
            if flags[vertex]:
                incident[int(vertex)].append(int(row))
    args.output.mkdir(mode=0o700, exist_ok=False); records = []
    for curve in selected:
        curve = int(curve); a, b = boundary['offsets'][curve:curve+2]; edge_ids = boundary['cycle_edges'][a:b]
        edges = boundary['boundary'][edge_ids]; nodes = edges[:, 0]
        assert np.array_equal(edges[:, 1], np.roll(nodes, -1)) and len(np.unique(nodes)) == len(nodes)
        halo = np.array(sorted({row for node in nodes for row in incident[int(node)]}), dtype=np.int64)
        used, inverse = np.unique(body['triangles'][halo], return_inverse=True)
        points, faces, mapping, _, topology = builder.atlas(body['points'][used], inverse.reshape(-1, 3))
        assert np.array_equal(used[mapping[faces]], body['triangles'][halo])
        wanted = []
        for edge, owner in zip(edges, boundary['owners'][edge_ids]):
            row = int(np.searchsorted(halo, owner)); assert halo[row] == owner
            original = body['triangles'][owner].tolist()
            corner = list(zip(original, original[1:]+original[:1])).index(tuple(map(int, edge)))
            wanted.append((int(faces[row, corner]), int(faces[row, (corner+1)%3])))
        wanted = np.array(wanted, dtype=np.int64)
        assert np.array_equal(wanted[:, 1], np.roll(wanted[:, 0], -1))
        path = args.output/('curve-'+str(curve).zfill(4)); path.mkdir(mode=0o700)
        with (path/'input.obj').open('w') as stream:
            for point in points:
                stream.write('v '+' '.join(format(float(x), '.17g') for x in point)+'\n')
            for face in faces:
                stream.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')
        (path/'target-edges.txt').write_text(str(curve)+' '+str(wanted[0, 0])+' '+str(wanted[0, 1])+'\n')
        np.savez_compressed(path/'private-halo-map.npz', points=points, triangles=faces, source_body_vertex_ids=used[mapping],
                            body_face_rows=halo, ordered_hole_nodes=wanted[:, 0], expected_source_boundary_edges=wanted,
                            original_global_hole_nodes=body['global_node_ids'][nodes], parent_boundary_edge_ids=edge_ids,
                            parent_boundary_edge_origins=boundary['edge_origin_kind'][edge_ids])
        records.append(dict(curve=curve, edges=len(nodes), halo_faces=len(faces),
                            input_OBJ_sha256=sha(path/'input.obj'), target_sha256=sha(path/'target-edges.txt'),
                            halo_map_sha256=sha(path/'private-halo-map.npz'), native_source_topology=topology))
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  complete_target_denominator=len(records), private_targets=records, source_geometry_changed=False,
                  physical_acceptance=False, manufacturing_authorized=False, seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'private_targets'}), flush=True)


if __name__ == '__main__':
    main()
