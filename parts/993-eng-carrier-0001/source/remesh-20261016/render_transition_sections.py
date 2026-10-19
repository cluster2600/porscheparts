"""Draw exact STEP sections and the two identified analytic thin-region rays."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
from build123d import import_step, Plane, section, Vector


def render(step, probes, output):
    step, probes, output = map(Path, (step, probes, output))
    record = json.loads(probes.read_text())
    if hashlib.sha256(step.read_bytes()).hexdigest() != record['STEP_sha256']:
        raise ValueError('STEP does not match the analytic probe receipt')
    output.mkdir(parents=True, exist_ok=False)
    body = import_step(step)
    rows = [next(p for p in record['probes'] if p['region'] == 'webs'),
            next(p for p in record['probes'] if p['region'] == 'junction_X160_Y-1' and p['centroid_mm'][0] < 0)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), layout='constrained')
    for ax, row, bounds, title in zip(axes, rows, ((79, 93, 9, 21), (-164, -156, -30, -22)),
        ('Raccord central : cylindre / extrusion', 'Trou secondaire Ø4 : cylindre / paroi extérieure')):
        a, b = np.array(row['exact_surface_point_mm']), np.array(row['opposite_exact_point_mm'])
        midpoint = (a + b) / 2
        row['ray_midpoint_inside_exact_solid'] = body.solids()[0].is_inside(Vector(*midpoint))
        if not row['ray_midpoint_inside_exact_solid']:
            raise ValueError('Probe ray midpoint is not inside exact material')
        curves = []
        for edge in section(body, Plane.XY, height=float(a[2])).edges():
            box = edge.bounding_box()
            if box.max.X < bounds[0] or box.min.X > bounds[1] or box.max.Y < bounds[2] or box.min.Y > bounds[3]:
                continue
            points = [edge.position_at(float(t)) for t in np.linspace(0, 1, 401)]
            curves.append(np.array([[p.X, p.Y] for p in points]))
        ax.add_collection(LineCollection(curves, colors='#17465c', linewidths=1.8))
        ax.plot([a[0], b[0]], [a[1], b[1]], color='#c42834', linewidth=3)
        ax.scatter([a[0], b[0]], [a[1], b[1]], color='#c42834', s=20, zorder=3)
        ax.annotate(f"{row['exact_inward_normal_ray_mm']:.6f} mm\ndans la matière", xy=midpoint[:2],
                    xytext=(bounds[0] + .4, bounds[3] - .4), va='top', fontsize=10,
                    arrowprops={'arrowstyle': '->', 'color': '#c42834'})
        ax.set(title=title + f"\nSection exacte Z = {a[2]:.4f} mm", xlabel='X [mm]', ylabel='Y [mm]',
               xlim=bounds[:2], ylim=bounds[2:])
        ax.set_aspect('equal'); ax.grid(alpha=.18)
    fig.suptitle('Localisation des lames minces — STEP « thick-skins » inchangé', fontsize=15)
    fig.supxlabel('Contours issus du STEP ; rayons analytiques vérifiés par appartenance à la matière. Aucun remplissage ni lissage.', fontsize=9)
    for suffix in ('png', 'svg'):
        fig.savefig(output / ('carrier-exact-thin-regions.' + suffix), dpi=180)
    (output / 'transition-sections.json').write_text(json.dumps({'STEP_sha256': record['STEP_sha256'],
        'probe_receipt_sha256': hashlib.sha256(probes.read_bytes()).hexdigest(), 'probes': rows}, indent=2) + '\n')
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('step', 'probes', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    render(args.step, args.probes, args.output)
