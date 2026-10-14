#!/usr/bin/env python3
"""Independent connectivity measurement and review render of the two-pass topology coupon."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

HERE = Path(__file__).resolve().parents[1]
PARTS = ('two-pass-metal', 'two-pass-charge', 'two-pass-charge-without-tank', 'two-pass-metal-open-view')


def load(path):
    mesh = trimesh.load_mesh(path, process=True)
    # Raw PicoGK meshes hold zero-area triangles; dropping them leaves the volume unchanged.
    mesh.update_faces(mesh.nondegenerate_faces() & mesh.unique_faces()); mesh.remove_unreferenced_vertices()
    return mesh


def bodies(mesh):
    """Volumes of the face-connected components, without building one mesh per component."""
    labels = trimesh.graph.connected_component_labels(mesh.face_adjacency, node_count=len(mesh.faces))
    t = mesh.triangles; signed = np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2]))/6
    volumes = np.bincount(labels, weights=signed)
    return [float(v) for v in volumes if abs(v) > 1e-6]


def simplify(mesh, target):
    poly = pv.PolyData(mesh.vertices, np.column_stack((np.full(len(mesh.faces), 3), mesh.faces)))
    out = poly.decimate_pro(max(0, 1-target/len(mesh.faces)), preserve_topology=True, splitting=False, boundary_vertex_deletion=False)
    review = trimesh.Trimesh(out.points, out.faces.reshape(-1, 4)[:, 1:], process=True)
    review.update_faces(review.nondegenerate_faces() & review.unique_faces()); review.remove_unreferenced_vertices()
    return review


def run(generated, measurement, derived):
    for p in (measurement, derived):
        if p.exists(): raise FileExistsError(p)
    gen = json.loads((generated/'generation.json').read_text()); meshes = {n: load(generated/f'{n}.stl') for n in PARTS}
    records = {}
    for n, m in meshes.items():
        b = bodies(m)
        records[n] = {'file_sha256': hashlib.sha256((generated/f'{n}.stl').read_bytes()).hexdigest(), 'watertight': bool(m.is_watertight),
                      'components': len(b), 'volume_mm3': float(m.volume), 'component_volumes_mm3': sorted(b, reverse=True)}
    x, y, z = gen['coupon_extents_mm']; envelope = x*y*z
    closure = (records['two-pass-metal']['volume_mm3']+records['two-pass-charge']['volume_mm3'])/envelope
    result = {'status': 'independent_topology_measurement_not_qualification', 'generation': gen, 'parts': records,
              'envelope_volume_mm3': envelope, 'volume_closure': closure,
              'metal_single_closed_body': records['two-pass-metal']['watertight'] and records['two-pass-metal']['components'] == 1,
              'passes_joined_only_by_return_tank': records['two-pass-charge']['components'] == 1 and records['two-pass-charge-without-tank']['components'] == 2,
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), HERE/'source/picogk/Program.cs', HERE/'source/picogk/Passes.csproj', HERE/'results/passes.json')}}
    if not result['metal_single_closed_body'] or not result['passes_joined_only_by_return_tank'] or abs(closure-1) > .01: raise ValueError(f'Topology rejected: {json.dumps(result, indent=1)}')

    derived.mkdir(parents=True); scene = trimesh.Scene(); review = []
    plot = pv.Plotter(off_screen=True, window_size=(1600, 900), shape=(1, 2))
    for col, (name, color) in enumerate((('two-pass-metal-open-view', [200, 204, 212]), ('two-pass-charge', [70, 130, 200]))):
        m = simplify(meshes[name], 400000); err = abs(m.volume/meshes[name].volume-1)
        if err > .01: raise ValueError(f'Review simplification changed volume: {name}')
        (derived/f'{name}.stl.gz').write_bytes(gzip.compress(m.export(file_type='stl'), mtime=0))
        review.append({'name': name, 'review_triangles': len(m.faces), 'review_volume_relative_error': float(err), 'components': len(bodies(m))})
        shown = m.copy(); shown.visual.face_colors = color+[255]; shown.apply_scale(.001); scene.add_geometry(shown, node_name=name)
        plot.subplot(0, col); plot.add_mesh(pv.wrap(m), color=[c/255 for c in color], smooth_shading=True, specular=.3)
        plot.add_text('metal, top wall removed for view' if col == 0 else 'charge domain: two passes joined by the tank', font_size=11)
        plot.set_background('white'); plot.camera_position = [(-30, -38, 42), (gen['coupon_extents_mm'][0]/2, y/2, z/2), (0, 0, 1)]
    plot.screenshot(str(derived/'two-pass-coupon.png')); plot.close()
    (derived/'two-pass-coupon.glb').write_bytes(scene.export(file_type='glb'))
    (derived/'coupon-review.json').write_text(json.dumps({'status': 'review_meshes_not_qualification', 'units': {'stl': 'mm', 'glb': 'm'}, 'records': review}, indent=2)+'\n', newline='\n')
    measurement.parent.mkdir(parents=True, exist_ok=True)
    measurement.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', newline='\n')
    print(json.dumps({k: result[k] for k in ('volume_closure', 'metal_single_closed_body', 'passes_joined_only_by_return_tank')}, indent=1))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--generated', type=Path, required=True); p.add_argument('--measurement', type=Path, required=True); p.add_argument('--derived', type=Path, required=True)
    a = p.parse_args(); run(a.generated, a.measurement, a.derived)
