#!/usr/bin/env python3
"""Prepare a stationary-gas witness on the open corridor between z=6 and 7 mm."""
import json
import math
from pathlib import Path
import sys

import numpy as np
from prepare_case import header, sha
import static_mrf_witness as witness


def mesh_text(nodes, half_width_mm, sectors):
    a = np.asarray(nodes, dtype=float)
    if (a.ndim != 2 or a.shape[1] != 2 or len(a) < 2 or not np.isfinite(a).all()
            or not np.all(np.diff(a[:, 0]) > 0) or not math.isfinite(half_width_mm)
            or half_width_mm <= 0 or np.min(a[:, 1]) <= half_width_mm
            or type(sectors) is not int or sectors < 3):
        raise ValueError('Finite increasing axial profile and positive shell radii required')
    vertices = [(r*math.cos(2*math.pi*i/sectors)/1000, r*math.sin(2*math.pi*i/sectors)/1000, z/1000)
                for z, radius in a for r in (radius-half_width_mm, radius, radius+half_width_mm)
                for i in range(sectors)]
    blocks, walls = [], []
    stride = 3*sectors
    for level in range(len(a)-1):
        for shell in (0, 1):
            for i in range(sectors):
                j = (i+1)%sectors
                bottom = [level*stride+shell*sectors+i, level*stride+(shell+1)*sectors+i,
                          level*stride+(shell+1)*sectors+j, level*stride+shell*sectors+j]
                v = bottom + [x+stride for x in bottom]
                zone = ' rotorZone' if shell == 0 else ''
                blocks.append('hex ('+' '.join(map(str,v))+')'+zone+' (1 1 1) simpleGrading (1 1 1)')
                walls.append([v[k] for k in ((0,4,7,3) if shell == 0 else (1,2,6,5))])
                if level == 0:
                    walls.append([v[k] for k in (0,3,2,1)])
                if level == len(a)-2:
                    walls.append([v[k] for k in (4,5,6,7)])
    vector = lambda values: '('+' '.join(f'{v:.15g}' for v in values)+')'
    return header('blockMeshDict')+'vertices ('+' '.join(map(vector,vertices))+');\nblocks ('+'\n'.join(blocks)+');\nedges ();\nboundary (walls {type wall; faces ('+' '.join(map(vector,walls))+');});\n'


def prepare(parent, case, profile_path, omega):
    report = json.loads(profile_path.read_text())
    if report['schema'] != 'bionic-turbo-open-interface-corridor/v1' or report['corridor']['sectors'] != 32:
        raise ValueError('Expected audited 32-sector corridor')
    profiles = report['corridor']['open_profiles']
    if len(profiles) != 1:
        raise ValueError('One audited open profile required')
    profile = profiles[0]
    nodes = [p for p in profile['nodes_z_radius_mm'] if 6 <= p[0] <= 7]
    if len(nodes) != 11 or nodes[0][0] != 6 or nodes[-1][0] != 7:
        raise ValueError('Complete 0.1 mm profile between z6 and z7 required')
    width = profile['minimum_radial_separation_bound_mm']/2
    text = mesh_text(nodes, width, 32)
    manifest = witness.prepare(parent, case, omega)
    (case/'system/blockMeshDict').write_text(text)
    (case/'system/topoSetDict').write_text(header('topoSetDict')+'actions ();\n')
    for name in ('system/blockMeshDict','system/topoSetDict'):
        manifest['file_sha256'][name] = sha(case/name)
    manifest['profile_witness'] = dict(source_sha256=sha(Path(__file__)), profile_sha256=sha(profile_path),
        nodes_z_radius_mm=nodes, shell_half_width_mm=width, sectors=32, expected_cells=640,
        expected_rotating_cells=320, expected_interface_faces=320,
        limitation='Synthetic stationary walls around a short real-corridor profile. Neither the actual stator junction nor the rear seal nor a turbo volume mesh is represented.')
    (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parent, case, profile = map(Path, sys.argv[1:])
    prepare(parent, case, profile, 10471.975511966)
