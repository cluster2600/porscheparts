"""Draw the actual carrier mesh with the explicitly assumed interface dimensions."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np


def render(stl, study, output, expected):
    raw = stl.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('STL identity mismatch')
    count = int.from_bytes(raw[80:84], 'little')
    if len(raw) != 84 + 50 * count:
        raise ValueError('Expected a complete binary STL')
    records = np.frombuffer(raw, dtype=np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')]), offset=84)
    triangles = records['vertices'].astype(float)
    if not count or not np.isfinite(triangles).all():
        raise ValueError('Invalid STL coordinates')
    g = json.loads(study.read_text())['geometry']
    xends = g['end_centres_x_mm']
    bolts = np.asarray(g['central_bolt_centres_xy_mm'], dtype=float)
    assert len(xends) == 2 and bolts.shape == (4, 2)
    ink, orange, pale = '#192c38', '#bd4a26', '#cbd5d7'
    figure = plt.figure(figsize=(14, 10), facecolor='white')
    grid = figure.add_gridspec(3, 2, height_ratios=[1.15, 1.15, 1.6], hspace=.6, wspace=.35)
    axes = [figure.add_subplot(grid[0, :]), figure.add_subplot(grid[1, :]), figure.add_subplot(grid[2, 0])]
    text = figure.add_subplot(grid[2, 1]); text.axis('off')

    def projection(ax, dims):
        xy = triangles[:, :, dims]
        area = np.abs(np.cross(xy[:, 1] - xy[:, 0], xy[:, 2] - xy[:, 0]))
        ax.add_collection(PolyCollection(xy[area > 1e-8], facecolors=pale, edgecolors='none', rasterized=True))
        ax.set_aspect('equal')
        ax.tick_params(labelsize=9)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(alpha=.15)

    def horizontal(ax, a, b, y, origin_y, label):
        ax.plot([a, a], [origin_y, y], color=orange, lw=.7)
        ax.plot([b, b], [origin_y, y], color=orange, lw=.7)
        ax.annotate('', (a, y), (b, y), arrowprops={'arrowstyle': '<->', 'color': orange, 'lw': 1})
        ax.text((a+b)/2, y+2, label, ha='center', va='bottom', color=orange, fontsize=11, weight='bold')

    projection(axes[0], [0, 1])
    axes[0].set(xlim=(-315, 315), ylim=(-48, 65), ylabel='Y (mm)', title='Vue de dessus — axes des deux extrémités')
    axes[0].plot(xends, [0, 0], '+', color=ink, ms=10)
    horizontal(axes[0], *xends, 50, 0, f'{xends[1]-xends[0]:g} mm entre axes')
    projection(axes[1], [0, 2])
    axes[1].set(xlim=(-315, 315), ylim=(-35, 48), xlabel='X (mm)', ylabel='Z (mm)', title='Vue de face — épaisseur, nervures et dégagements')
    projection(axes[2], [0, 1])
    axes[2].set(xlim=(-72, 72), ylim=(-43, 45), xlabel='X (mm)', ylabel='Y (mm)', title='Détail de la platine centrale')
    axes[2].plot(bolts[:, 0], bolts[:, 1], '+', color=ink, ms=10)
    xmin, ymin = bolts.min(0); xmax, ymax = bolts.max(0)
    horizontal(axes[2], xmin, xmax, 35, ymax, f'{xmax-xmin:g} mm')
    axes[2].annotate('', (64, ymin), (64, ymax), arrowprops={'arrowstyle': '<->', 'color': orange})
    axes[2].text(67, 0, f'{ymax-ymin:g} mm', rotation=90, ha='left', va='center', color=orange, fontsize=11, weight='bold')
    labels = [
        'COTES DU MODÈLE D’ÉTUDE',
        f"Platine : {g['thickness_mm']:g} mm",
        f"Quatre alésages centraux : Ø {2*g['central_bore_radius_mm']:g} mm",
        f"Deux alésages d’extrémité : Ø {2*g['end_bore_radius_mm']:g} mm",
        'Axes centraux selon Z ; axes d’extrémité selon Y.',
        '',
        'Les cotes viennent des paramètres de la révision.',
        'Elles ne sont pas déduites de la photographie.',
        'L’unité de la géométrie est le millimètre.',
    ]
    text.text(0, .95, '\n'.join(labels), va='top', fontsize=11, linespacing=1.7, color=ink)
    figure.suptitle('Support moteur 993 — repères pour l’atelier', fontsize=21, weight='bold', color=ink, y=.98)
    figure.text(.075, .025, f'Surface réelle du fichier STL · SHA-256 {expected[:16]}… · dimensions de travail explicites', fontsize=10, color=ink)
    output.mkdir(parents=True, exist_ok=False)
    figure.savefig(output / 'carrier-dimensions.png', dpi=180)
    figure.savefig(output / 'carrier-dimensions.svg')
    plt.close(figure)
    (output / 'drawing.json').write_text(json.dumps({'STL_sha256': expected, 'study_sha256': hashlib.sha256(study.read_bytes()).hexdigest(), 'dimension_source': 'study.geometry', 'assumed_dimensions_mm': g}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stl', 'study', 'output'):
        parser.add_argument(name, type=Path)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument('--sha256')
    identity.add_argument('--identity-receipt', type=Path)
    args = parser.parse_args()
    expected = json.loads(args.identity_receipt.read_text())['candidate_STL_sha256'] if args.identity_receipt else args.sha256
    render(args.stl, args.study, args.output, expected)
