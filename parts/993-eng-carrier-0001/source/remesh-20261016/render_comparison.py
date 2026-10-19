"""Plot actual V6f triangulation and exact STEP sections in shared coordinates."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
import numpy as np
from build123d import import_step, Plane, section

from remesh import read_stl, quality


def plane_segments(vertices, faces, z):
    triangles = vertices[faces]
    # Reconstruct each triangular section directly so unrelated crossings are never joined.
    lines = []
    active = triangles[(triangles[:, :, 2].min(1) < z) & (triangles[:, :, 2].max(1) > z)]
    for triangle in active:
        hits = []
        for a, b in zip(triangle, np.roll(triangle, -1, axis=0)):
            if (a[2] - z) * (b[2] - z) < 0:
                hits.append(a + (z - a[2]) / (b[2] - a[2]) * (b - a))
        if len(hits) == 2:
            lines.append(np.asarray(hits)[:, :2])
    return lines


def run(step, source, candidate, output, audit=None):
    sv, sf = read_stl(source)
    cv, cf = read_stl(candidate)
    old_needles = int(np.count_nonzero(quality(sv, sf) < .001))
    new_needles = int(np.count_nonzero(quality(cv, cf) < .001))
    note = f'Triangles aiguilles sur les maillages complets : {old_needles} → {new_needles}. Même maître STEP, mêmes coordonnées.'
    if audit:
        receipt = json.loads(Path(audit).read_text())
        assert receipt['STEP_sha256'] == hashlib.sha256(Path(step).read_bytes()).hexdigest()
        assert receipt['candidate_STL_sha256'] == hashlib.sha256(Path(candidate).read_bytes()).hexdigest()
        forward = receipt['mesh_to_exact_CAD']['maximum_distance_to_STEP_shell_mm']
        inverse = receipt['exact_CAD_to_mesh']['maximum_mm']
        note += f'\nÉcarts maximaux échantillonnés : STL → STEP {forward:.5f} mm ; STEP → STL {inverse:.5f} mm.'
    figure, axes = plt.subplots(2, 2, figsize=(15, 8), gridspec_kw={'height_ratios': [1, 2]}, facecolor='white')
    for ax, vertices, faces, title in ((axes[0, 0], sv, sf, 'Avant : triangulation héritée'),
                                     (axes[0, 1], cv, cf, 'Après : Gmsh depuis le STEP')):
        triangles = vertices[faces]
        select = (np.abs(triangles[:, :, 2] - 22) < 1e-5).all(1)
        triangles = triangles[select]
        selected_faces = faces[select]
        local = (triangles[:, :, 0].max(1) > -162) & (triangles[:, :, 0].min(1) < -158) & (triangles[:, :, 1].max(1) > -28.3) & (triangles[:, :, 1].min(1) < -27.5)
        triangles, selected_faces = triangles[local], selected_faces[local]
        ax.add_collection(PolyCollection(triangles[:, :, :2], facecolor='none', edgecolor='#167da2', linewidth=.7))
        bad = quality(vertices, selected_faces) < .001
        if bad.any():
            ax.add_collection(PolyCollection(triangles[bad, :, :2], facecolor='#e45756', edgecolor='#b22428', alpha=.7))
        ax.set(xlim=(-162, -158), ylim=(-28.3, -27.5), title=title)
        ax.set_aspect('equal')
    z = 21.94566388009001
    exact = section(import_step(step), Plane.XY, height=z)
    curves = []
    for edge in exact.edges():
        box = edge.bounding_box()
        if box.max.X < 204 or box.min.X > 211 or box.max.Y < -26 or box.min.Y > -23:
            continue
        points = [edge.position_at(float(t)) for t in np.linspace(0, 1, 501)]
        curves.append(np.array([[p.X, p.Y] for p in points]))
    for ax, vertices, faces, color, title in ((axes[1, 0], sv, sf, '#c63835', 'Ancien STL / référence STEP'),
                                           (axes[1, 1], cv, cf, '#008caa', 'Nouveau STL / même référence STEP')):
        ax.add_collection(LineCollection(curves, colors='#17283a', linewidths=2.8, label='Section du STEP exact'))
        ax.add_collection(LineCollection(plane_segments(vertices, faces, z), colors=color, linewidths=1.2, label='Section du STL réel'))
        ax.set(xlim=(204, 211), ylim=(-26, -23), title=title)
        ax.set_aspect('equal')
        ax.legend(loc='lower left', fontsize=9)
    for ax in axes.ravel():
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.grid(alpha=.2)
    figure.suptitle('Support 993 — correction de la représentation triangulée', fontsize=18, weight='bold')
    figure.text(.5, .035, note, ha='center', fontsize=10)
    figure.subplots_adjust(left=.065, right=.985, top=.86, bottom=.17, hspace=.55, wspace=.18)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    figure.savefig(output / 'carrier-remesh-comparison.png', dpi=180)
    figure.savefig(output / 'carrier-remesh-comparison.svg')
    plt.close(figure)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('step', 'source', 'candidate', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--audit', type=Path, help='Hash-bound bidirectional CAD/mesh receipt to annotate')
    args = parser.parse_args()
    run(args.step, args.source, args.candidate, args.output, args.audit)
