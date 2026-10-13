#!/usr/bin/env python3
"""Measure the native coupons independently of the screen formulas; no qualification."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parents[1]


def load(path):
    mesh = trimesh.load_mesh(path, process=True)
    zero = mesh.area_faces <= 1e-12
    if zero.any():  # raw PicoGK meshes carry zero-area triangles; they hold no area or volume
        mesh.update_faces(~zero); mesh.remove_unreferenced_vertices(); mesh.merge_vertices()
    parts = mesh.split(only_watertight=False)
    volumes = sorted((abs(p.volume) for p in parts), reverse=True)
    return mesh, {'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'triangles': len(mesh.faces),
                  'zero_area_removed': int(zero.sum()), 'watertight': bool(mesh.is_watertight), 'volume_mm3': float(mesh.volume),
                  'components': len(parts), 'largest_component_volume_fraction': volumes[0]/sum(volumes)}


def cut_area(mesh, lo, hi, tol):
    """Area of faces lying on the coupon cut planes: they are not wetted walls."""
    v = mesh.vertices[mesh.faces]; total = 0.
    for axis in range(3):
        for plane in (lo[axis], hi[axis]):
            on = np.all(np.abs(v[:, :, axis]-plane) < tol, axis=1)
            total += float(mesh.area_faces[on].sum())
    return total


def run(screen, generated, output):
    if output.exists(): raise FileExistsError(output)
    gen = json.loads((generated/'generation.json').read_text()); rep = json.loads(screen.read_text())
    voxel = gen['voxel_mm']; tol = .6*voxel; out = {'status': 'independent_coupon_measurement_not_qualification', 'voxel_mm': voxel, 'parts': {}}
    g = gen['gyroid']; n = g['cube_mm']; s = g['window_origin_mm']; box = n**3
    analytic = rep['gyroid_break_even_lighter_than_witness']['geometry']
    meshes = {}
    for name in ('gyroid-metal', 'gyroid-charge-network', 'gyroid-cooling-network', 'helical-metal', 'helical-charge-passage'):
        meshes[name], out['parts'][name] = load(generated/f'{name}.stl')
    networks = []
    for name in ('gyroid-charge-network', 'gyroid-cooling-network'):
        m = meshes[name]; wet = m.area-cut_area(m, (s, s, s), (s+n, s+n, s+n), tol)
        frags = sorted(m.split(only_watertight=False), key=lambda p: -abs(p.volume))[1:]
        # A fragment touching the cut window is open in the coupon but would be sealed by a solid side wall.
        touching = [bool(np.any(p.bounds[0] < s+tol) or np.any(p.bounds[1] > s+n-tol)) for p in frags]
        networks.append({'name': name, 'porosity': m.volume/box, 'wetted_area_mm2': wet, 'hydraulic_diameter_mm': 4*m.volume/wet,
                         'area_density_times_cell': wet/box*g['cell_mm'], 'edge_fragments': len(frags),
                         'edge_fragment_volume_mm3': float(sum(abs(p.volume) for p in frags)), 'all_fragments_open_on_cut_window': all(touching)})
    metal = meshes['gyroid-metal'].volume/box
    out['gyroid'] = {'cube_mm': n, 'metal_fraction_measured': metal, 'metal_fraction_screen': analytic['metal_fraction'],
                     'networks': networks, 'network_porosity_screen': analytic['network_porosity'],
                     'hydraulic_diameter_screen_mm': analytic['hydraulic_diameter_mm'], 'area_density_times_cell_screen': 3.0917,
                     'volume_closure': (meshes['gyroid-metal'].volume+sum(meshes[k].volume for k in ('gyroid-charge-network', 'gyroid-cooling-network')))/box}
    h = gen['helical']; d, t, w, L = h['tube_inner_mm'], h['tube_wall_mm'], h['web_mm'], h['twist_pitch_180_mm']
    out['helical'] = {'metal_volume_measured_mm3': meshes['helical-metal'].volume,
                      'metal_volume_screen_mm3': (math.pi*((d+2*t)**2-d*d)/4+w*d)*L,
                      'passage_volume_measured_mm3': meshes['helical-charge-passage'].volume,
                      'passage_volume_screen_mm3': (math.pi*d*d/4-w*d)*L,
                      'passage_components_expected': 2}
    out['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), HERE/'source/picogk/Program.cs', HERE/'source/picogk/Cells.csproj']}
    out['generation'] = gen
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, allow_nan=False)+'\n', newline='\n')
    print(json.dumps({'gyroid': {k: v for k, v in out['gyroid'].items() if k != 'networks'}, 'networks': networks, 'helical': out['helical'],
                      'parts': {k: (v['watertight'], v['components'], round(v['largest_component_volume_fraction'], 4)) for k, v in out['parts'].items()}}, indent=1))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--screen', type=Path, default=HERE/'results/screen.json')
    p.add_argument('--generated', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); run(a.screen, a.generated, a.output)
