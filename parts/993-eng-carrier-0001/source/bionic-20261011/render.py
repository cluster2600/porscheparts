"""Render the actual exported CAD or solver fields, never an illustrative mesh."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
import trimesh

from simulate import elements


def axes(fig, slot, triangles, colors, title, elev=38, azim=-65):
    import pyvista as pv
    ax = fig.add_subplot(slot)
    el, az = np.radians([elev, azim])
    view = np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])
    right = np.array([-np.sin(az), np.cos(az), 0])
    up = np.cross(view, right)
    projected = triangles @ np.stack([right, up], axis=1)
    lo, hi = projected.reshape(-1, 2).min(0), projected.reshape(-1, 2).max(0)
    faces = np.column_stack([np.full(len(triangles), 3), np.arange(3*len(triangles)).reshape(-1, 3)])
    mesh = pv.PolyData(triangles.reshape(-1, 3), faces)
    mesh.cell_data['colour'] = np.rint(np.asarray(colors)*255).astype(np.uint8)
    # A depth buffer handles overlapping long faces and hollow ribs correctly.
    plot = pv.Plotter(off_screen=True, window_size=(2100, 600))
    plot.set_background(fig.get_facecolor()[:3])
    plot.add_mesh(mesh, scalars='colour', rgb=True, lighting=False, show_scalar_bar=False)
    centre = (triangles.reshape(-1, 3).min(0)+triangles.reshape(-1, 3).max(0))/2
    plot.camera_position = [centre+view*1200, centre, up]
    plot.enable_parallel_projection()
    plot.camera.parallel_scale = max(hi[1]-lo[1], (hi[0]-lo[0])/3.5)*.53
    pixels = plot.screenshot(return_img=True)
    plot.close()
    ax.imshow(pixels)
    ax.set_facecolor(fig.get_facecolor())
    ax.set_title(title, fontsize=12, loc='left')
    ax.set_axis_off()
    return ax


def render(folder, case=None):
    if case is None:
        model = trimesh.load(folder/'carrier.stl', force='mesh')
        checks = {'watertight': bool(model.is_watertight),
                  'consistent_winding': bool(model.is_winding_consistent),
                  'components': len(model.split()), 'STL_volume_mm3': float(model.volume)}
        assert checks['watertight'] and checks['consistent_winding'] and checks['components'] == 1
        (folder/'surface-check.json').write_text(json.dumps(checks, indent=2)+'\n')
        shade = .35+.55*np.maximum(0, model.face_normals @ np.array([.2, -.4, .8]))
        colors = np.c_[shade*.88, shade*.95, shade, np.ones(len(shade))]
        config = json.loads((folder/'study.json').read_text())
        shell = config['geometry'].get('arm_shell')
        fig = plt.figure(figsize=(16, 11 if shell else 8), facecolor='#f5f5f2')
        axes(fig, 311 if shell else 211, model.triangles, colors, 'Actual CAD — oblique view')
        axes(fig, 312 if shell else 212, model.triangles, colors, 'Top view — four central bores and two large openings', 90, -90)
        if shell:
            section = model.slice_plane([0, 0, 0], [0, 1, 0])
            shade = .35+.55*np.maximum(0, section.face_normals @ np.array([.2, -.4, .8]))
            colours = np.c_[shade*.88, shade*.95, shade, np.ones(len(shade))]
            axes(fig, 313, section.triangles, colours,
                 'Longitudinal cut at Y = 0 — open cutaway shows hollow arms', 22, -75)
            mass = json.loads((folder/'geometry.json').read_text())['dense_reference_mass_kg']
            fig.text(.08, .055, f"{mass:.3f} kg nominal Ti reference • arm skins/webs {shell['cap_mm']:g}/{shell['web_mm']:g} mm • assumed bolt pads {config['geometry']['thickness_mm']:g} mm", fontsize=11)
        fig.suptitle('993 Turbo bionic carrier | PROVISIONAL STUDY — assumed dimensions', fontsize=16)
        fig.text(.08, .035, 'Editable STEP solid • six primary attachment bores • fitment and manufacture unverified', fontsize=11)
        output = folder/'cad-views.png'
    else:
        mesh = np.load(folder/'mesh.npz')
        result = np.load(folder/(case+'.npz'))
        tags, xyz, faces = mesh['tags'], mesh['xyz'], mesh['faces']
        indices = np.searchsorted(tags, faces)
        connect = elements(folder/'mesh.inp')
        face_elements = {}
        for eid, nodes in connect.items():
            for ids in [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]:
                face_elements[tuple(sorted(nodes[i] for i in ids))] = eid
        eids, inverse = np.unique(result['element_ids'], return_inverse=True)
        evm = np.bincount(inverse, weights=result['VM'])/np.bincount(inverse)
        face_ids = np.array([face_elements[tuple(sorted(face))] for face in faces])
        svm = evm[np.searchsorted(eids, face_ids)]
        umag = np.linalg.norm(result['displacement'], axis=1)
        unorm, snorm = Normalize(0, umag.max()), Normalize(0, result['VM'].max())
        cmap = plt.get_cmap('viridis')
        fig = plt.figure(figsize=(16, 8), facecolor='#f5f5f2')
        a = axes(fig, 211, (xyz+result['displacement'])[indices], cmap(unorm(umag[indices].mean(1))),
                 'Deformed shape at true scale (1×); colours: displacement magnitude')
        fig.colorbar(plt.cm.ScalarMappable(norm=unorm, cmap=cmap), ax=a, shrink=.65, label='mm')
        a = axes(fig, 212, xyz[indices], cmap(snorm(svm)),
                 'Undeformed top view; colours: element-mean von Mises stress', 90, -90)
        fig.colorbar(plt.cm.ScalarMappable(norm=snorm, cmap=cmap), ax=a, shrink=.65, label='MPa')
        fig.suptitle(f'Conditional FEA | {case}', fontsize=16)
        fig.text(.08, .035, 'Assumed geometry, loads and dense Ti-6Al-4V elasticity. No strength allowable or physical validation.', fontsize=11)
        output = folder/(case+'.png')
    fig.subplots_adjust(top=.9, bottom=.08, hspace=.1, left=.04, right=.9)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('--case')
    args = parser.parse_args()
    render(args.folder, args.case)
