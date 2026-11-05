#!/usr/bin/env python3
"""Replay the historical rotor-to-wall sample in uncalibrated source units."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def sampled_distances(source, wall, indices):
    """Query after converting the wall to source coordinates, not case units."""
    import trimesh

    scaled_wall = trimesh.Trimesh(vertices=np.asarray(wall.vertices) * 1000,
                                 faces=wall.faces, process=False)
    points = np.asarray(source.triangles_center)[indices]
    distances = []
    for start in range(0, len(points), 32):
        _, values, _ = trimesh.proximity.closest_point(scaled_wall, points[start:start + 32])
        distances.extend(values)
    distances = np.asarray(distances)
    if not np.isfinite(distances).all():
        raise ValueError('invalid distances')
    return distances


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rotor', type=Path)
    parser.add_argument('wall', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('output exists')
    rotor_hash, wall_hash = sha(args.rotor), sha(args.wall)
    if (rotor_hash != '7d273b6072449c1e9140a995847fc4704990944fbb888d74a6a10a5a3db79091'
            or wall_hash != '60f8564a87add660078b8609b09d6bfe6b8e439f146afe02ad6de91457b37f35'):
        raise SystemExit('unexpected input hash')
    import trimesh

    source = trimesh.load_mesh(args.rotor, process=False, maintain_order=True)
    wall = trimesh.load_mesh(args.wall, process=False, maintain_order=True)
    if len(source.faces) != 878612 or len(wall.faces) != 699084:
        raise ValueError('unexpected triangle count')
    ids = np.linspace(0, len(source.faces) - 1, 4096, dtype=int)
    d = sampled_distances(source, wall, ids)
    result = {'status': 'source_scale_sampled_distance_not_surface_bound',
              'unit': 'uncalibrated_source_unit', 'rotor_sha256': rotor_hash,
              'wall_sha256': wall_hash, 'point_count': len(d),
              'median': float(np.median(d)), 'p95': float(np.percentile(d, 95)),
              'max': float(d.max()), 'over_0p05': int(np.count_nonzero(d > .05)),
              'over_0p5': int(np.count_nonzero(d > .5)),
              'physical_scale_verified': False, 'cfd_admitted': False}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
