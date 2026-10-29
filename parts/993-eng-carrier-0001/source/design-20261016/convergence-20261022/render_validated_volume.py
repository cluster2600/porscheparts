"""Plot actual tetrahedron sections of the independently checked nominal carrier."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--archive', required=True, type=Path)
    p.add_argument('--assessment', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    report = json.loads(args.assessment.read_text())
    if args.output.exists() or report['status'] != 'exact_orientations_and_indexed_boundary_passed':
        raise ValueError('Verified complex and fresh image required')
    data = np.load(args.archive, allow_pickle=False)
    v, cells = data['vertices'], data['tetrahedra']
    if len(cells) != report['exact_positive_cells']:
        raise ValueError('Cell count differs from independent assessment')
    plane = 1.5
    polygons, values = [], []
    for begin in range(0, len(cells), 250000):
        t = v[cells[begin:begin + 250000]]
        lo, hi = t.min(axis=1), t.max(axis=1)
        mask = ((lo[:, 2] < plane) & (hi[:, 2] > plane)
                & (hi[:, 0] > 66) & (lo[:, 0] < 82)
                & (hi[:, 1] > 23) & (lo[:, 1] < 35))
        for tet in t[mask]:
            points = []
            for a, b in [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]:
                if (tet[a, 2] - plane) * (tet[b, 2] - plane) < 0:
                    points.append((tet[a] + (plane - tet[a, 2]) / (tet[b, 2] - tet[a, 2]) * (tet[b] - tet[a]))[:2])
            if len(points) < 3:
                continue
            q = np.asarray(points)
            centre = q.mean(axis=0)
            q = q[np.argsort(np.arctan2(q[:, 1] - centre[1], q[:, 0] - centre[0]))]
            volume = abs(np.dot(tet[1] - tet[0], np.cross(tet[2] - tet[0], tet[3] - tet[0]))) / 6
            polygons.append(q)
            values.append(volume)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), facecolor='#f6f7f9')
    norm = LogNorm(1e-10, .5)
    for ax, bounds, title in zip(axes, [(66, 82, 23, 35), (71.7, 72.8, 24.6, 25.7)],
                                 ['Internal region: actual volume elements', 'Zoom near the inherited crease']):
        collection = PolyCollection(polygons, array=np.asarray(values), cmap='viridis', norm=norm,
                                    edgecolors='#27323a', linewidths=.15)
        ax.add_collection(collection)
        ax.set(xlim=bounds[:2], ylim=bounds[2:], xlabel='x (mm)', ylabel='y (mm)', title=title)
        ax.set_aspect('equal')
        ax.set_facecolor('white')
    fig.suptitle('993 carrier | Independently checked tetrahedral complex', x=.06, ha='left', fontsize=18)
    fig.text(.06, .035, f"z = {plane} mm section · {len(polygons):,} intersected local cells shown\n"
             f"All {report['exact_positive_cells']:,} cells checked: exact positive orientation, oriented boundary and face cancellation.\n"
             'Geometry checkpoint. Inherited corner geometry still requires regularization before stress refinement.', fontsize=9)
    fig.subplots_adjust(left=.06, right=.9, bottom=.25, top=.83, wspace=.26)
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap='viridis'), ax=axes, fraction=.028, pad=.03)
    cb.set_label('Cell volume (mm³), logarithmic scale')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == '__main__':
    main()
