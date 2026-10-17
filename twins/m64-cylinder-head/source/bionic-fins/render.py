"""Render exact STL cross-sections and bounded fin-study results."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def section(directory):
    helper = Path(__file__).resolve().parents[1]/'picogk-local-junction/audit_surface_topology.py'
    spec = importlib.util.spec_from_file_location('fin_stl_reader', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.MAX_FACES = 2_000_000
    report = json.loads((directory/'geometry.json').read_text())
    triangles, digest = module.load_binary_stl(directory/'coupon.stl')
    if digest != report['coupon']['sha256']:
        raise ValueError('Coupon hash mismatch')
    pairs = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        first, last = triangles[:, a], triangles[:, b]
        crossed = (first[:, 1] < 0) != (last[:, 1] < 0)
        part = triangles[crossed]
        t = -first[crossed, 1]/(last[crossed, 1]-first[crossed, 1])
        points = first[crossed]+t[:, None]*(last[crossed]-first[crossed])
        pairs.extend(zip(np.flatnonzero(crossed), points[:, [0, 2]]))
    cuts = {}
    for i, p in pairs:
        cuts.setdefault(i, []).append(p)
    segments = [points for points in cuts.values() if len(points) == 2]
    if not segments:
        raise ValueError('Empty STL section')
    return segments, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('countercheck', type=Path)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = json.loads(args.countercheck.read_text())
    rows = {r['id']: r for r in report['refinement']}
    base = rows['straight']['levels'][-1]
    leaf = rows[report['best_bionic_id']]['levels'][-1]
    fig = plt.figure(figsize=(14, 9), facecolor='#eff2f4')
    grid = fig.add_gridspec(2, 2, height_ratios=(1.4, 1))
    hashes = []
    for i, (directory, title, color) in enumerate(((args.baseline, 'Témoin : ailettes droites', '#465c70'),
                                                  (args.candidate, 'Candidate bionique : racines épaisses, branches fines', '#b85b2b'))):
        ax = fig.add_subplot(grid[0, i]); lines, digest = section(directory); hashes.append(digest)
        ax.add_collection(LineCollection(lines, colors=color, linewidths=1))
        ax.set(xlim=(-22, 22), ylim=(-5, 30), xlabel='X (mm synthétiques)', ylabel='Z (mm synthétiques)', title=title)
        ax.set_aspect('equal'); ax.grid(alpha=.15)
    ax = fig.add_subplot(grid[1, :])
    for k in (12, 80, 160):
        indices = [i for i, s in enumerate(report['scenarios']) if s['k_W_mK'] == k]
        ax.plot([report['scenarios'][i]['h_W_m2K'] for i in indices],
                [(leaf[i]['conductance_W_K']/base[i]['conductance_W_K']-1)*100 for i in indices],
                marker='o', label=f'k = {k} W/(m·K), hypothèse')
    ax.set(xlabel='Coefficient de convection imposé h [W/(m²·K)]', ylabel='Gain de conductance [%]',
           title='Calcul 2D sur les formes fusionnées : volume de métal égal, grille 0,05 mm')
    ax.grid(alpha=.2); ax.legend(ncol=3)
    fig.suptitle('M64 / 4 soupapes — étude de cellules d’ailettes PicoGK + ShapeKernel', fontsize=17)
    fig.text(.5, .018, 'Coupes des STL réels, Y = 0. Cellules synthétiques séparées : aucune intégration à la culasse.\n'
             'Air à h imposé : pertes de charge, alliage, fabrication et gain moteur non validés.', ha='center', fontsize=11)
    fig.tight_layout(rect=(0, .075, 1, .95)); fig.savefig(args.output, dpi=160); plt.close(fig)
    print(json.dumps(dict(image_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(), coupon_sha256=hashes)))


if __name__ == '__main__':
    main()
