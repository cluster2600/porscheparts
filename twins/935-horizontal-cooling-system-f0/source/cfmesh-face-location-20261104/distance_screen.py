#!/usr/bin/env python3
"""Screen face vertex-mean positions against vertices of an OpenFOAM patch.

Distances are upper bounds to the polygonal patch, not exact closest distances.
Coordinates retain the case's conditional units; no scan calibration is implied.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def body(path):
    with path.open() as f:
        for line in f:
            if re.fullmatch(r'\s*\d+\s*', line):
                count = int(line)
                if next(f).strip() != '(':
                    raise ValueError('invalid list opening')
                for _ in range(count):
                    yield next(f).strip()
                if next(f).strip() != ')':
                    raise ValueError('invalid list ending')
                return
    raise ValueError('missing list count')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('poly_mesh', type=Path)
    parser.add_argument('sets', nargs='+')
    args = parser.parse_args()
    p = args.poly_mesh
    boundary = (p / 'boundary').read_text()
    matches = re.findall(r'rotor\s*\{[^{}]*?nFaces\s+(\d+)\s*;[^{}]*?startFace\s+(\d+)\s*;', boundary, re.S)
    if len(matches) != 1:
        raise ValueError('expected exactly one rotor patch')
    count, start = map(int, matches[0])
    selections = {}
    for name in args.sets:
        if Path(name).name != name:
            raise ValueError('invalid set name')
        ids = [int(x) for x in body(p / 'sets' / name)]
        if len(ids) != len(set(ids)) or any(i < 0 or i >= start for i in ids):
            raise ValueError('expected unique internal face indices')
        selections[name] = ids
    wanted = set(i for ids in selections.values() for i in ids)
    faces = {}
    rotor_vertices = set()
    total = 0
    for index, line in enumerate(body(p / 'faces')):
        total += 1
        if index not in wanted and not start <= index < start + count:
            continue
        match = re.fullmatch(r'(\d+)\(([^()]*)\)', line)
        if not match:
            raise ValueError('unsupported face format')
        vertices = [int(x) for x in match.group(2).split()]
        if len(vertices) != int(match.group(1)) or len(vertices) < 3:
            raise ValueError('invalid face vertices')
        if index in wanted:
            faces[index] = vertices
        if start <= index < start + count:
            rotor_vertices.update(vertices)
    if len(faces) != len(wanted) or start + count > total:
        raise ValueError('missing face or rotor range')
    points = []
    for line in body(p / 'points'):
        if not line.startswith('(') or not line.endswith(')'):
            raise ValueError('invalid point')
        xyz = [float(x) for x in line[1:-1].split()]
        if len(xyz) != 3:
            raise ValueError('invalid point dimension')
        points.append(xyz)
    points = np.asarray(points, dtype=np.float64)
    used = list(rotor_vertices)
    if not used or max(used) >= len(points) or not np.isfinite(points).all():
        raise ValueError('invalid rotor vertices or points')
    tree = cKDTree(points[used])
    result = {'method': 'nearest rotor mesh vertex to face vertex-mean; upper bound to patch distance',
              'boundary_sha256': digest(p / 'boundary'), 'faces_sha256': digest(p / 'faces'),
              'points_sha256': digest(p / 'points'), 'rotor_unique_vertices': len(used),
              'units': 'case coordinates; metre only under unverified scale assumption', 'sets': {}}
    for name, ids in selections.items():
        centres = np.array([points[faces[i]].mean(axis=0) for i in ids])
        distances = tree.query(centres, workers=1)[0]
        result['sets'][name] = {'sha256': digest(p / 'sets' / name), 'count': len(ids),
            'min': float(distances.min()), 'median': float(np.median(distances)),
            'p95': float(np.percentile(distances,95)), 'max': float(distances.max()),
            'below_0p001_case_units': int(np.count_nonzero(distances < .001)),
            'below_0p005_case_units': int(np.count_nonzero(distances < .005))}
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
