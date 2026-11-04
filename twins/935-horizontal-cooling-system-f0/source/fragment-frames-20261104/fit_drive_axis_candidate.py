#!/usr/bin/env python3
"""Fit a visually selected open drive-scan arc in the provisional assembly frame."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reconstruct_hub_surfaces import fit_surface

SCAN_SHA = 'fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35'
COUNT = 2484656
DTYPE = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)),
                  ('attribute', '<u2')])


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def select(triangles):
    triangles = np.asarray(triangles, dtype=float)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3):
        raise ValueError('Expected triangle vertices')
    centres = triangles.mean(axis=1)
    cross = np.cross(triangles[:, 1] - triangles[:, 0],
                     triangles[:, 2] - triangles[:, 0])
    length = np.linalg.norm(cross, axis=1)
    normals = np.divide(cross, length[:, None], out=np.zeros_like(cross),
                        where=length[:, None] > 0)
    radius = np.linalg.norm(centres[:, :2], axis=1)
    keep = ((radius > 5.5) & (radius < 8) & (centres[:, 2] > -36)
            & (centres[:, 2] < -3) & (np.abs(normals[:, 2]) < .3)
            & (length > 0) & np.isfinite(triangles).all(axis=(1, 2)))
    return centres, normals, keep


def run(scan, output):
    scan, output = Path(scan), Path(output)
    private = (Path.cwd() / 'work').resolve()
    if output.exists() or not output.resolve().is_relative_to(private):
        raise ValueError('Use a fresh private work/ output directory')
    if digest(scan) != SCAN_SHA or scan.stat().st_size != 84 + 50 * COUNT:
        raise ValueError('Pinned complete binary scan required')
    vertices = np.memmap(scan, dtype=DTYPE, mode='r', offset=84,
                         shape=(COUNT,))['vertices']
    point_chunks, normal_chunks, index_chunks = [], [], []
    for start in range(0, COUNT, 50000):
        points, normals, selected = select(vertices[start:start + 50000])
        point_chunks.append(points[selected])
        normal_chunks.append(normals[selected])
        index_chunks.append(start + np.flatnonzero(selected))
    points, normals, indices = map(np.concatenate, (point_chunks, normal_chunks, index_chunks))
    model = fit_surface(points, normals, np.array([0., 0., 0., 0., 7.]),
                        (5., 10.), 'cylinder', normal_weight=2., robust_scale=.3)
    if digest(scan) != SCAN_SHA:
        raise ValueError('Input changed during fitting')
    output.mkdir(parents=True, mode=0o700)
    selection = output / 'private-selection.npz'
    np.savez_compressed(selection, points=points, normals=normals, face_indices=indices)
    result = {'status': 'visual_selection_cylinder_candidate_not_a_mating_datum',
              'source_sha256': SCAN_SHA, 'selection_sha256': digest(selection),
              'selection': {'radial_range': [5.5, 8.], 'z_range': [-36, -3],
                            'abs_normal_z_max': .3},
              'selected_faces': len(points), 'model': model,
              'same_scan_holdout_only': True, 'physical_registration_verified': False,
              'scale_verified': False, 'manufacturing_authorized': False}
    (output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'selected_faces': len(points), 'status': result['status']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scan', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.scan, args.output)
