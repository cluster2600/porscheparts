#!/usr/bin/env python3
"""Optimize private tetrahedra while explicitly checking boundary immobility."""
import argparse
import hashlib
import json
from pathlib import Path
import gmsh
import numpy as np


def quality():
    _, groups, _ = gmsh.model.mesh.getElements(3)
    tags = np.concatenate(groups)
    values = np.asarray(gmsh.model.mesh.getElementQualities(tags, 'minSICN'))
    if not len(values) or not np.isfinite(values).all():
        raise RuntimeError('missing or nonfinite element qualities')
    return {'elements': len(values), 'minimum_minSICN': float(values.min()),
            'count_le_zero': int((values <= 0).sum()),
            'count_lt_0p1': int((values < .1).sum())}


def boundary():
    result = {}
    for dimension in range(3):
        tags, xyz, _ = gmsh.model.mesh.getNodes(dimension)
        result.update(zip(map(int, tags), np.asarray(xyz).reshape(-1, 3).tolist()))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('source hash mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'porsche-volume-optimization-f53/v1',
              'source_sha256': a.sha256, 'manufacturing_authorized': False,
              'steps': []}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        gmsh.option.setNumber('General.NumThreads', 1)
        gmsh.open(str(a.input))
        original_boundary = boundary()
        report['before'] = quality()
        for method in ('', 'Relocate3D', ''):
            gmsh.model.mesh.optimize(method, force=True, niter=5)
            current_boundary = boundary()
            unchanged = original_boundary == current_boundary
            step = {'method': method or 'default', 'quality': quality(),
                    'boundary_exactly_unchanged': unchanged}
            report['steps'].append(step)
            print(json.dumps(step), flush=True)
            if not unchanged:
                raise RuntimeError('boundary changed; candidate rejected')
        path = a.output / 'candidate.msh'
        gmsh.write(str(path))
        report['mesh_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['strict_quality_accepted'] = report['steps'][-1]['quality']['count_lt_0p1'] == 0
    finally:
        gmsh.finalize()
        (a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['strict_quality_accepted'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
