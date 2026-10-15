#!/usr/bin/env python3
"""Bound an open faceted interface corridor on the exact CFD boundary; never admit a solver."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compare_geometry as geometry
from prepare_case import PATCHES, sha


def read_patches(path, info):
    """Read only an already validated surface, checking its digest and patch counts."""
    counts = info['region_triangles']
    if set(counts) != set(PATCHES) or info.get('closed_edges') is not True:
        raise ValueError('Validated four-patch closed surface required')
    if any(type(n) is not int or not 0 < n <= 10000000 for n in counts.values()):
        raise ValueError('Bounded positive patch counts required')
    arrays = {k: np.empty((3*n, 3)) for k, n in counts.items()}
    seen, active, index = set(), None, 0
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for line in stream:
            digest.update(line)
            words = line.split()
            if not words:
                continue
            if words[0] == b'solid':
                name = words[1].decode('ascii')
                if active is not None or name not in arrays or name in seen:
                    raise ValueError('Unexpected or duplicate patch')
                active, index = name, 0
                seen.add(name)
            elif words[0] == b'vertex':
                if active is None or len(words) != 4 or index >= len(arrays[active]):
                    raise ValueError('Unexpected vertex')
                arrays[active][index] = [float(x) for x in words[1:]]
                index += 1
            elif words[0] == b'endsolid':
                if active is None or words[1].decode('ascii') != active or index != len(arrays[active]):
                    raise ValueError('Incomplete patch')
                active = None
    if active is not None or seen != set(PATCHES) or digest.hexdigest() != info['sha256']:
        raise ValueError('Surface changed or incomplete')
    return {k: geometry.checked_triangles(a.reshape(-1, 3, 3)*1000) for k, a in arrays.items()}


def bounds(rotor, stator, band_mm=0.1):
    rotor, stator = map(geometry.checked_triangles, (rotor, stator))
    if not np.isfinite(band_mm) or not .01 <= band_mm <= 1:
        raise ValueError('Band width must be in [0.01, 1] mm')
    rz0, rz1 = rotor[:, :, 2].min(axis=1), rotor[:, :, 2].max(axis=1)
    sz0, sz1 = stator[:, :, 2].min(axis=1), stator[:, :, 2].max(axis=1)
    upper = np.linalg.norm(rotor[:, :, :2], axis=2).max(axis=1) + geometry.MARGIN_MM
    lower = geometry.projected_min_radius(stator)
    first, last = math.floor(rz0.min()/band_mm), math.ceil(rz1.max()/band_mm)
    if not 0 < last-first <= 10000:
        raise ValueError('Invalid axial extent')
    rows = []
    for i in range(first, last):
        z0, z1 = i*band_mm, (i+1)*band_mm
        r = np.flatnonzero((rz0 <= z1+geometry.MARGIN_MM) & (rz1 >= z0-geometry.MARGIN_MM))
        s = np.flatnonzero((sz0 <= z1+geometry.MARGIN_MM) & (sz1 >= z0-geometry.MARGIN_MM))
        ri = int(r[np.argmax(upper[r])]) if len(r) else None
        si = int(s[np.argmin(lower[s])]) if len(s) else None
        lo, hi = (float(upper[ri]) if ri is not None else None), (float(lower[si]) if si is not None else None)
        rows.append(dict(z_low_mm=z0, z_high_mm=z1, rotor_upper_mm=lo, stator_lower_mm=hi,
                         gap_lower_mm=hi-lo if lo is not None and hi is not None else None,
                         rotor_face=ri, stator_face=si, rotor_faces=len(r), stator_faces=len(s)))
    return rows


def corridor(rows, sectors=32):
    if type(sectors) is not int or sectors < 3:
        raise ValueError('At least three angular sectors required')
    cosine = math.cos(math.pi/sectors)
    groups, current, rejected = [], [], []
    for i, row in enumerate(rows):
        lo, hi = row['rotor_upper_mm'], row['stator_lower_mm']
        if lo is not None and hi is not None and 0 <= lo/cosine < hi:
            current.append(i)
        else:
            if current:
                groups.append(current); current = []
            rejected.append(i)
    if current:
        groups.append(current)
    profiles, failed = [], []
    for group in groups:
        nodes = []
        for j in range(len(group)+1):
            neighbours = group[max(0,j-1):min(len(group),j+1)]
            low = max(rows[i]['rotor_upper_mm']/cosine for i in neighbours)
            high = min(rows[i]['stator_lower_mm'] for i in neighbours)
            if low >= high:
                failed.append(dict(band_indices=neighbours, lower_mm=low, upper_mm=high))
                break
            z = rows[group[j]]['z_low_mm'] if j < len(group) else rows[group[-1]]['z_high_mm']
            nodes.append([z, (low+high)/2])
        else:
            margins = [min(min(nodes[j][1], nodes[j+1][1])*cosine-rows[i]['rotor_upper_mm'],
                           rows[i]['stator_lower_mm']-max(nodes[j][1], nodes[j+1][1])) for j, i in enumerate(group)]
            if min(margins) <= 0:
                raise ValueError('Faceted radial separation invariant failed')
            profiles.append(dict(band_indices=group, nodes_z_radius_mm=nodes,
                                 minimum_radial_separation_bound_mm=min(margins)))
    return dict(sectors=sectors, angular_chord_factor=cosine, open_profiles=profiles,
                unresolved_band_indices=rejected, failed_adjacent_intersections=failed,
                closed_interface_verified=False, solver_admission_granted=False)


def audit(case):
    manifest_path = case/'case-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    surface = case/'constant/triSurface/domain.stl'
    patches = read_patches(surface, manifest['surface'])
    rows = bounds(patches['rotor'], patches['stator'])
    result = corridor(rows)
    unresolved = []
    for i in result['unresolved_band_indices']:
        row = rows[i]
        unresolved.append(dict(band_index=i, rotor_triangle_mm=patches['rotor'][row['rotor_face']].tolist() if row['rotor_face'] is not None else None,
                               stator_triangle_mm=patches['stator'][row['stator_face']].tolist() if row['stator_face'] is not None else None))
    return dict(schema='bionic-turbo-open-interface-corridor/v1', source_sha256=sha(Path(__file__)),
                geometry_source_sha256=sha(Path(geometry.__file__)), case_manifest_sha256=sha(manifest_path),
                surface_sha256=manifest['surface']['sha256'], region_triangles=manifest['surface']['region_triangles'],
                bands=rows, corridor=result, unresolved_witnesses=unresolved,
                performance_ranking_authorized=False,
                interpretation='Full-facet conservative radial bounds on all CFD rotor and stator patches. Open side profiles only; no end closure, fluid containment, volume mesh, wall layers or equilibrium qualification. Negative bounds are indeterminate, not collision proof. The stator patch is open, so no solid winding-number gate is applied.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = audit(args.case)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
