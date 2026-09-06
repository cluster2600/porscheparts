#!/usr/bin/env python3
"""Private wall probes: compare inscribed-sphere and normal-ray screening."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from trimesh.proximity import thickness


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--samples', type=int, default=2000)
    a = p.parse_args()
    if a.samples < 1:
        raise ValueError('positive sample count required')
    if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('source hash mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    mesh = trimesh.load_mesh(a.input)
    if not mesh.is_watertight:
        raise ValueError('watertight mesh required')
    if not mesh.is_winding_consistent:
        mesh.fix_normals()
    cumulative = np.cumsum(mesh.area_faces)
    targets = (np.arange(a.samples) + .5) * cumulative[-1] / a.samples
    indices = np.searchsorted(cumulative, targets)
    points, normals = mesh.triangles_center[indices], mesh.face_normals[indices]
    values = {}
    for method in ('max_sphere', 'ray'):
        values[method] = np.asarray(thickness(mesh, points, normals=normals, method=method))
        if not np.isfinite(values[method]).all() or (values[method] < 0).any():
            raise RuntimeError('invalid thickness probes')
    np.savez_compressed(a.output / 'private-wall-probes.npz', points=points,
                        normals=normals, face_indices=indices, **values)
    flags = {key: value < 1.5 for key, value in values.items()}
    report = {'schema': 'porsche-wall-localization-f53/v1',
              'source_sha256': a.sha256, 'sample_count': a.samples,
              'threshold_scan_units': 1.5, 'absolute_scale_certified': False,
              'classification': 'two_geometric_screens_not_certified_minimum_wall',
              'below_threshold': {key: int(value.sum()) for key, value in flags.items()},
              'below_both': int((flags['ray'] & flags['max_sphere']).sum()),
              'methods_disagree': int((flags['ray'] != flags['max_sphere']).sum()),
              'manufacturing_authorized': False}
    (a.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
