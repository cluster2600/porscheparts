#!/usr/bin/env python3
"""Retain topology-checked review meshes and a render of the native metal coupons."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

COUPONS = [('gyroid-metal', [180, 195, 212, 255]), ('helical-metal', [215, 162, 77, 255])]


def run(native, output):
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True); records = []; scene = trimesh.Scene(); plot = pv.Plotter(off_screen=True, window_size=(1400, 800))
    offset = 0.
    for name, color in COUPONS:
        path = native/f'{name}.stl'; mesh = trimesh.load_mesh(path, process=True); before = mesh.volume
        mesh.update_faces(mesh.nondegenerate_faces() & mesh.unique_faces()); mesh.remove_unreferenced_vertices()
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.body_count != 1 or mesh.volume <= 0: raise ValueError(f'Native topology rejected: {name}')
        if abs(mesh.volume/before-1) > 1e-7: raise ValueError('Cleanup changed volume')
        poly = pv.PolyData(mesh.vertices, np.column_stack((np.full(len(mesh.faces), 3), mesh.faces))); attempts = []
        for target in (250000, 600000, 1500000):
            simplified = poly.decimate_pro(max(0, 1-target/len(mesh.faces)), preserve_topology=True, splitting=False, boundary_vertex_deletion=False)
            review = trimesh.Trimesh(simplified.points, simplified.faces.reshape(-1, 4)[:, 1:], process=True)
            review.update_faces(review.nondegenerate_faces() & review.unique_faces()); review.remove_unreferenced_vertices()
            error = abs(review.volume/mesh.volume-1)
            attempts.append({'target': target, 'watertight': bool(review.is_watertight), 'bodies': int(review.body_count), 'volume_error': float(error)})
            if review.is_watertight and review.body_count == 1 and error <= .005: break
        else: raise ValueError(f'Review simplification rejected: {name}')
        (output/f'{name}.stl.gz').write_bytes(gzip.compress(review.export(file_type='stl'), mtime=0))
        records.append({'name': name, 'native_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'native_triangles': len(mesh.faces),
                        'native_volume_mm3': float(mesh.volume), 'native_bodies': 1, 'simplification_attempts': attempts,
                        'review_triangles': len(review.faces), 'review_volume_relative_error': float(error)})
        review.apply_translation([offset-review.bounds[0][0], 0, 0])
        plot.add_mesh(pv.wrap(review), color=[c/255 for c in color[:3]], smooth_shading=True, specular=.4)
        offset += review.extents[0]+6
        shown = review.copy(); shown.visual.face_colors = color; shown.apply_scale(.001); scene.add_geometry(shown, node_name=name)
        del mesh, poly
    (output/'coupons.glb').write_bytes(scene.export(file_type='glb'))
    plot.set_background('white'); plot.camera_position = 'iso'; plot.camera.zoom(1.2)
    plot.screenshot(str(output/'coupons.png')); plot.close()
    (output/'review.json').write_text(json.dumps({'status': 'review_meshes_not_qualification', 'units': {'stl': 'mm', 'glb': 'm'},
                                                  'records': records, 'all_voids_inspected': False}, indent=2)+'\n', newline='\n')
    print(json.dumps(records, indent=1))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--native', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); run(a.native, a.output)
