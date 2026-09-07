#!/usr/bin/env python3
"""Trial fin thickening with unchanged lateral scan contours and overall bounds."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path


def thicken(profiles, target):
    if not math.isfinite(target) or target <= 1.5:
        raise ValueError('target must exceed source fin spacing')
    result = copy.deepcopy(profiles)
    count = 0
    for index, item in enumerate(profiles):
        if item['kind'] != 'fin_lower':
            continue
        if index + 1 == len(profiles):
            raise ValueError('unpaired fin contour')
        upper = profiles[index + 1]
        if upper['kind'] != 'fin_upper':
            raise ValueError('unpaired fin contour')
        spacing = upper['z'] - item['z']
        if abs(spacing - 1.5) > 1e-9:
            raise ValueError('unexpected source fin spacing')
        midpoint = .5 * (item['z'] + upper['z'])
        result[index]['z'] = midpoint - .5 * target
        result[index + 1]['z'] = midpoint + .5 * target
        count += 1
    if not count or any(b['z'] <= a['z'] for a, b in zip(result, result[1:])):
        raise ValueError('profile order changed or missing fins')
    if result[0] != profiles[0] or result[-1] != profiles[-1]:
        raise ValueError('end envelope changed')
    return result, count


def main():
    import gmsh
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profiles', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--target', type=float, default=2.0)
    p.add_argument('--reference', action='store_true', help='Build unchanged input profiles as control')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if hashlib.sha256(a.profiles.read_bytes()).hexdigest() != a.sha256:
        raise ValueError('source hash mismatch')
    source = json.loads(a.profiles.read_text())
    if a.reference:
        profiles, count = copy.deepcopy(source['profiles']), 0
    else:
        profiles, count = thicken(source['profiles'], a.target)
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / 'private-profiles.json').write_text(json.dumps(profiles)+'\n')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        gmsh.option.setNumber('Geometry.Tolerance', 1e-7)
        gmsh.model.add('f54_thickened_scan_fins')
        occ = gmsh.model.occ
        wires = []
        for item in profiles:
            points = [occ.addPoint(x, y, item['z']) for x, y in item['points_xy']]
            edges = [occ.addLine(points[i], points[(i + 1) % len(points)])
                     for i in range(len(points))]
            wires.append(occ.addWire(edges, checkClosed=True))
        occ.addThruSections(wires, makeSolid=True, makeRuled=True, maxDegree=3)
        occ.synchronize()
        if len(gmsh.model.getEntities(3)) != 1:
            raise RuntimeError('candidate is not one volume')
        path = a.output / 'candidate-outer.step'
        gmsh.write(str(path))
    finally:
        gmsh.finalize()
    report = {'schema': 'porsche-fin-thickening-trial-f54/v1',
              'source_profiles_sha256': a.sha256, 'fin_pairs_modified': count,
              'source_spacing_scan_units': 1.5,
              'target_spacing_scan_units': 1.5 if a.reference else a.target,
              'unchanged_reference_control': a.reference,
              'xy_contours_unchanged': True, 'end_profiles_unchanged': True,
              'step_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'internal_geometry_present': False, 'absolute_scale_certified': False,
              'wall_thickness_and_cooling_accepted': False,
              'manufacturing_authorized': False}
    (a.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
