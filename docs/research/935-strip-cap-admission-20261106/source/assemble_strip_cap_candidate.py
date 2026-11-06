"""Assemble independently inspected strip-border caps with distinct provenance."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compose(base, patches):
    n = len(base['triangles']); faces = []; labels = []
    for curve, patch in sorted(patches.items()):
        patch = np.asarray(patch, dtype=np.int64).reshape(-1, 3)
        assert curve >= 0 and len(patch) and patch.min() >= 0 and patch.max() < len(base['points'])
        faces.append(patch); labels.extend([curve]*len(patch))
    added = np.concatenate(faces) if faces else np.empty((0, 3), dtype=np.int64)
    labels = np.array(labels, dtype=np.int64); result = dict(base)
    result['triangles'] = np.concatenate((base['triangles'], added))
    for key, values in base.items():
        if key in ('points', 'triangles', 'global_node_ids'):
            continue
        assert values.shape == (n,), key
        new = np.full(len(added), -1, dtype=values.dtype)
        if key == 'inferred_surface_kind':
            new[:] = 5
        elif key == 'source_patch_curve_ids':
            new[:] = 40000000+labels
        result[key] = np.concatenate((values, new))
    result['source_strip_cap_curve_ids'] = np.r_[np.full(n, -1, dtype=np.int64), labels]
    result['strip_cap_immediate_parent_face_rows'] = np.r_[np.arange(n), np.full(len(added), -1, dtype=np.int64)]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'local-checks', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--rejected-proof', type=Path)
    parser.add_argument('--expected-rejected-proof-sha256')
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    inspection = json.loads((args.local_checks/'report.json').read_text())
    assert inspection['job_sha256'] == sha(job['local_inspection_job']) and inspection['complete_parent_incident_fans_verified']
    rejected = set()
    if args.rejected_proof is not None:
        assert args.expected_rejected_proof_sha256 and sha(args.rejected_proof) == args.expected_rejected_proof_sha256
        proof = json.loads(args.rejected_proof.read_text()); assert proof['parent_mesh_sha256'] == sha(job['mesh'])
        rejected = set(proof['rejected_strip_cap_curve_ids'])
    with np.load(job['mesh'], allow_pickle=False) as data:
        base = {key:data[key] for key in data.files}
    patches = {}; local_ids = set()
    for row in inspection['private_patch_results']:
        if not row['accepted']:
            continue
        curve = row['curve']; local_ids.add(curve)
        if curve in rejected:
            continue
        path = args.local_checks/('private-patch-'+str(curve).zfill(4)+'.npz')
        assert sha(path) == row['private_patch_sha256']
        with np.load(path, allow_pickle=False) as data:
            assert int(data['parent_curve']) == curve; patches[curve] = data['triangles']
    assert rejected <= local_ids
    result = compose(base, patches); args.output.mkdir(mode=0o700, exist_ok=False)
    np.savez_compressed(args.output/'candidate.npz', **result)
    with (args.output/'candidate.obj').open('w') as stream:
        for point in result['points']:
            stream.write('v '+' '.join(format(float(x), '.17g') for x in point)+'\n')
        for face in result['triangles']:
            stream.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), parent_mesh_sha256=sha(job['mesh']),
                  mesh_sha256=sha(args.output/'candidate.npz'), obj_sha256=sha(args.output/'candidate.obj'),
                  retained_caps=len(patches), whole_caps_removed=len(rejected), added_triangles=len(result['triangles'])-len(base['triangles']),
                  parent_faces_removed=0, coordinates_changed=0, thresholds_relaxed=False, alternate_reselection=False,
                  full_candidate_checks_pending=True, physical_acceptance=False, manufacturing_authorized=False)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
