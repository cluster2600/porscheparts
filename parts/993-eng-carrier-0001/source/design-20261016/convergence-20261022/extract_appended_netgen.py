"""Explicitly isolate Netgen's appended block after refusing the combined double volume."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def extract(original, combined):
    v, t, f = original
    vertices, cells, faces = combined
    if (len(cells) <= len(t) or not np.array_equal(vertices[:len(v)], v)
            or not np.array_equal(cells[:len(t)], t) or not np.array_equal(faces, f)):
        raise ValueError('Complete unchanged original prefixes and boundary required')
    appended = cells[len(t):]
    used = np.unique(appended)
    mapping = np.full(len(vertices), -1, dtype=np.int64)
    mapping[used] = np.arange(len(used))
    if np.any(mapping[faces] < 0):
        raise ValueError('Appended block omits original boundary vertices')
    return vertices[used], mapping[appended], mapping[faces]


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--combined', type=Path, required=True)
    p.add_argument('--expected-original-sha256', required=True)
    p.add_argument('--expected-combined-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if a.output.exists() or sha(a.original) != a.expected_original_sha256 or sha(a.combined) != a.expected_combined_sha256:
        raise ValueError('Fresh output and exact source identities required')
    def read(path):
        with np.load(path, allow_pickle=False) as data:
            return tuple(data[k].copy() for k in ['vertices', 'tetrahedra', 'boundary'])
    original, combined = read(a.original), read(a.combined)
    vertices, cells, faces = extract(original, combined)
    a.output.mkdir(parents=True)
    target = a.output/'volume.npz'
    np.savez_compressed(target, vertices=vertices, tetrahedra=cells, boundary=faces)
    used = np.unique(faces)
    mapping = np.full(len(vertices), -1, dtype=np.int64)
    mapping[used] = np.arange(len(used))
    boundary = a.output/'boundary.mesh64'
    with boundary.open('w') as stream:
        stream.write(f'{len(used)} {len(faces)}\n')
        np.savetxt(stream, vertices[used], fmt='%.17g')
        np.savetxt(stream, mapping[faces], fmt='%d')
    report = dict(status='appended_block_extracted_independent_audit_required',
                  original_cells_removed=len(original[1]), appended_cells=len(cells), nodes=len(vertices),
                  complete_original_prefix_identity_verified=True, original_boundary_retained=True,
                  combined_volume_refused=True, mechanical_mesh_admitted=False,
                  source_sha256={str(path):sha(path) for path in [a.original, a.combined, Path(__file__)]},
                  output_sha256={path.name:sha(path) for path in [target, boundary]})
    (a.output/'assessment.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
