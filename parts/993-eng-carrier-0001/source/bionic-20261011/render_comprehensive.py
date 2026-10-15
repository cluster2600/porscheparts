"""Figures from retained CAD, slices and numerical fields."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import trimesh

from render import axes


def render(root):
    folder = root/'v5/mesh-9'
    labels = ['Fx 2 kN', 'Fy 2 kN', 'Fz -2 kN', 'Mx 100 Nm', 'My 850 Nm', 'Mz 100 Nm', 'Fz -4 kN\n+ My 850 Nm']
    cases = ['lateral', 'longitudinal', 'gravity', 'torsion_x_100Nm', 'torque_y_850Nm', 'torsion_z_100Nm', 'combined']
    fig, ax = plt.subplots(figsize=(13, 6), facecolor='#f5f5f2')
    for i, fixture in enumerate(('rigid', 'spring-10000', 'spring-1000')):
        values = [json.loads((folder/f'{case}-{fixture}-static.json').read_text())['integration_point_VM_max_MPa'] for case in cases]
        ax.bar(np.arange(7)+(i-1)*.25, values, .24, label=fixture)
    ax.axhline(955, color='#a72727', linestyle='--', label='955 MPa coupon yield reference')
    ax.axhline(955/1.5, color='#7b6a2d', linestyle=':', label='Assumed 1.5-factor screen')
    ax.set_xticks(range(7), labels); ax.set_ylabel('Peak elastic von Mises demand (MPa)')
    ax.set_title('V5 — 1.185 kg | conditional load and mount sensitivity', loc='left', fontsize=16)
    ax.legend(fontsize=9); ax.grid(axis='y', alpha=.2)
    fig.text(.08, .02, 'Assumed geometry, loads and mounts. Coupon reference is not a part allowable. Combined load fails the screen.', fontsize=10)
    fig.tight_layout(rect=(0, .06, 1, 1)); fig.savefig(root/'structural-overview.png', dpi=170); plt.close(fig)

    import pyvista as pv
    ori = json.loads((root/'print-orientation.json').read_text())
    model = trimesh.load_mesh(root/'v5/carrier.stl')
    tr = np.eye(4); tr[:3, :3] = ori['rotation_matrix']; tr[:3, 3] = ori['translation_mm']; model.apply_transform(tr)
    poly = pv.PolyData(model.vertices, np.c_[np.full(len(model.faces), 3), model.faces])
    plot = pv.Plotter(off_screen=True, window_size=(1600, 1400)); plot.set_background('#f5f5f2')
    plot.add_mesh(poly, color='#8796a0', smooth_shading=True, split_sharp_edges=True, feature_angle=35, specular=.3)
    plot.add_mesh(pv.Box(bounds=(0, 400, 0, 400, 0, 20)), color='#354957')
    plot.add_mesh(pv.Box(bounds=(0, 400, 0, 400, 0, 400)), style='wireframe', color='#858d90', line_width=2)
    plot.add_text('V5 / EOS M 400-4 envelope study\n400 x 400 x 400 mm, including platform', font_size=18, color='#10242e')
    plot.add_text('Actual CAD orientation\nSupport CAD and scan paths are not defined', position='lower_left', font_size=14, color='#822b22')
    plot.camera_position = [(820, -720, 650), (200, 200, 200), (0, 0, 1)]
    plot.enable_parallel_projection(); plot.camera.parallel_scale=370
    plot.show_axes(); plot.screenshot(root/'print-orientation.png'); plot.close()

    data = np.load(root/'slices-60um.npz'); active = np.flatnonzero(np.diff(data['offsets']))
    chosen = active[np.linspace(0, len(active)-1, 8).astype(int)]
    fig, axs = plt.subplots(2, 4, figsize=(14, 7), facecolor='#f5f5f2')
    for ax, index in zip(axs.ravel(), chosen):
        seg = data['segments'][data['offsets'][index]:data['offsets'][index+1]]
        ax.add_collection(LineCollection(seg, colors='#116b80', linewidths=.9)); ax.autoscale(); ax.set_aspect('equal')
        ax.set_title(f'Layer {index+1} | Z {data["height_mm"][index]:.2f} mm', fontsize=10)
        ax.set_xlabel('machine X (mm)'); ax.set_ylabel('machine Y (mm)')
    fig.suptitle('Actual part contours at 60 µm — selected sections, no support or scan vectors', fontsize=15)
    fig.tight_layout(); fig.savefig(root/'print-slices.png', dpi=170); plt.close(fig)

    for variant in ('print-16-staged', 'print-32-staged', 'print-16-plastic', 'print-one-layer-control'):
        out = root/variant
        if not (out/'result.json').exists(): continue
        mesh = np.load(out/'mesh.npz'); result = np.load(out/'released.npz')
        xyz = mesh['xyz']; idx = np.searchsorted(mesh['tags'], mesh['faces'])
        u = result['registered']; mag = np.linalg.norm(u, axis=1)
        norm = plt.Normalize(0, mag.max()); cmap = plt.get_cmap('viridis')
        fig = plt.figure(figsize=(16, 6), facecolor='#f5f5f2')
        a = axes(fig, 111, (xyz+25*u)[idx], cmap(norm(mag[idx].mean(1))),
                 f'{variant} | released shape, deformation amplified 25x', elev=20, azim=-45)
        fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=a, shrink=.7, label='Registered displacement (mm)')
        control = variant == 'print-one-layer-control'
        fig.suptitle('Whole-part contraction control' if control else 'Rejected staged-process model — diagnostic output only', fontsize=16)
        warning = 'Uniform contraction, no deposition sequence.' if control else 'Unresolved constitutive anomaly; activation resolution not converged.'
        fig.text(.07, .06, warning+' Not a manufacturing prediction.', fontsize=11)
        fig.savefig(out/'release-distortion.png', dpi=170); plt.close(fig)


if __name__ == '__main__': render(Path(sys.argv[1]))
