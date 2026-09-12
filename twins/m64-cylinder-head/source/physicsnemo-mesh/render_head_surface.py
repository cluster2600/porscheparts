#!/usr/bin/env python3
"""Two private OFF_SCREEN views of the pinned, unchanged STEP-derived surface."""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ['PYVISTA_OFF_SCREEN'] = 'true'
import numpy as np

PIN = 'ab6f41b8802e96c5be1c159b47116e4a9818d91fe57b38139e277f3275e49d66'
SIZE = (1800, 1250)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def triangle_quality(points, triangles):
    xyz = points[triangles]
    edges = (xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 1], xyz[:, 0] - xyz[:, 2])
    twice_area = np.linalg.norm(np.cross(edges[0], -edges[2]), axis=1)
    denominator = sum(np.einsum('ij,ij->i', edge, edge) for edge in edges)
    if np.any(denominator <= 0) or np.any(twice_area <= 0):
        raise ValueError('degenerate_triangle_not_rendered_as_valid_quality')
    q = 2 * np.sqrt(3.) * twice_area / denominator
    if not np.isfinite(q).all():
        raise ValueError('nonfinite_quality')
    return q


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if sha(a.mesh) != PIN:
        raise ValueError('pinned_NPZ_mismatch')
    with np.load(a.mesh, allow_pickle=False) as data:
        points, triangles = data['points'], data['triangles']
    if (points.shape != (146648, 3) or points.dtype != np.float64 or
            triangles.shape != (293308, 3) or triangles.dtype != np.int64 or
            not np.isfinite(points).all() or triangles.min() < 0 or triangles.max() >= len(points)):
        raise ValueError('source_inventory_mismatch')
    before = (points.tobytes(), triangles.tobytes())
    q = triangle_quality(points, triangles)
    import pyvista as pv
    pv.OFF_SCREEN = True
    faces = np.column_stack((np.full(len(triangles), 3, dtype=np.int64), triangles)).ravel()
    body = pv.PolyData(points, faces, deep=True)
    body.cell_data['q'] = q
    lo, hi = points.min(axis=0), points.max(axis=0)
    center, span = (lo + hi) / 2, float(np.max(hi - lo))
    camera = [tuple(center + span * np.array([1., 1., 1.])), tuple(center), (0., 0., 1.)]
    a.output.mkdir(mode=0o700, exist_ok=False)
    outputs = {}
    for name, colored in [('head-aluminium.png', False), ('head-triangle-quality.png', True)]:
        plot = pv.Plotter(off_screen=True, window_size=SIZE)
        try:
            plot.background_color = '#111c26'
            if colored:
                plot.add_mesh(body, scalars='q', preference='cell', cmap='viridis', clim=(0., 1.),
                              lighting=False, opacity=1., show_edges=False, smooth_shading=False,
                              scalar_bar_args=dict(title='q : 0 = aplati, 1 = equilateral',
                                  color='white', n_labels=6, fmt='%.1f', vertical=False,
                                  position_x=.23, position_y=.11, width=.54, height=.07))
            else:
                plot.add_mesh(body, color='#aeb6be', opacity=1., smooth_shading=False,
                              show_edges=False, ambient=.35, diffuse=.65, specular=.15)
            plot.camera_position = camera
            plot.enable_parallel_projection()
            plot.camera.parallel_scale = span * .62
            title = 'Qualite geometrique des triangles' if colored else 'Corps de reference - aspect aluminium'
            plot.add_text(title, position='upper_left', color='white', font_size=22)
            plot.add_text('q = 4 sqrt(3) A / somme(longueurs^2)' if colored else
                          'Gris illustratif : aucun choix de materiau valide',
                          position=(35, 1160), color='#b6c5d2', font_size=15)
            plot.add_text('Reconstruction issue du scan 935 | unites non certifiees\n'
                          'Non validee M64 / CFD / fabrication | aucune temperature ou contrainte',
                          position='lower_left', color='#ffb2a4', font_size=14)
            path = a.output / name
            plot.screenshot(str(path))
            path.chmod(0o600)
            outputs[name] = sha(path)
        finally:
            plot.close()
    if (points.tobytes(), triangles.tobytes()) != before or sha(a.mesh) != PIN:
        raise ValueError('source_mutated')
    if body.points.tobytes() != before[0] or not np.array_equal(body.faces, faces):
        raise ValueError('render_representation_geometry_changed')
    receipt = dict(schema='m64-private-surface-render/v1', source_NPZ_sha256=PIN,
                   renderer_sha256=sha(__file__), PyVista_version=pv.__version__,
                   images_sha256=outputs, pixels=list(SIZE), triangles=len(triangles),
                   q_min=float(q.min()), q_max=float(q.max()), q_scale=[0., 1.],
                   q_is_dimensionless_triangle_shape_not_CFD_acceptance=True,
                   source_and_render_coordinates_connectivity_unchanged=True,
                   projection='orthographic_isometric_same_camera_both_views',
                   smoothing=False, decimation=False, CAD_tessellation=False,
                   length_unit='scan_unit', absolute_scale_certified=False,
                   CFD_authorized=False, manufacturing_authorized=False, generative_image=False)
    (a.output / 'render-report.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps(receipt, allow_nan=False))


if __name__ == '__main__':
    main()
