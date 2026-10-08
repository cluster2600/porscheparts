#!/usr/bin/env python3
"""Plot unchanged native PicoGK mesh sections; no inferred or filled hidden surfaces."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import trimesh


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('native', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    if a.output.exists():
        p.error('output must be new')
    meshes = [trimesh.load_mesh(a.native/name, process=True) for name in
              ('tunnel-baseline.stl', 'tunnel-relief-study.stl', 'driveline-envelopes.stl')]
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    for row, (z, label) in enumerate(((310, 'Passage du tube C4'), (455, 'Ouverture du levier C2'))):
        for column, title in enumerate(('Concept initial', 'Variante avec ouvertures')):
            ax = axes[row, column]
            for mesh, color, style in ((meshes[column], '#005a8d', '-'), (meshes[2], '#c04b16', '--')):
                section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
                if section is None:
                    raise ValueError('Expected section is missing')
                for points in section.discrete:
                    ax.plot(points[:, 0], points[:, 1], color=color, linestyle=style, linewidth=1.6)
            ax.set(xlim=(350, 2020), ylim=(-200, 200), xlabel='X vers l’arrière (mm)', ylabel='Y gauche (mm)',
                   title=f'{title} — {label}, Z={z} mm')
            ax.set_aspect('equal')
            ax.grid(alpha=.2)
            ax.spines[['top', 'right']].set_visible(False)
    axes[0, 0].annotate('Nez fermé sur le tube', xy=(430, 0), xytext=(650, -140),
                       arrowprops={'arrowstyle': '->'}, fontsize=10)
    axes[1, 0].annotate('Le couvercle recouvre\nle volume du levier', xy=(980, 0), xytext=(1290, -120),
                       arrowprops={'arrowstyle': '->'}, fontsize=10)
    fig.suptitle('Tunnel : trois interférences dans le concept initial\nCoupes des maillages PicoGK — hypothèses, pas de cotes Porsche mesurées', fontsize=15)
    fig.legend(handles=[Line2D([0], [0], color='#005a8d', label='Contour du tunnel'),
                        Line2D([0], [0], color='#c04b16', linestyle='--', label='Enveloppes C2/C4 hypothétiques')],
               loc='lower center', ncol=2, bbox_to_anchor=(.5, .055))
    fig.text(.5, .015, 'Coupes Z=310 et 455 mm : le guidage C4 à Z=392 mm n’est pas montré. Aucun jeu dynamique, stratifié ou moule validé.',
             ha='center', fontsize=10)
    fig.tight_layout(rect=(0, .12, 1, .9), h_pad=3)
    fig.savefig(a.output, dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    main()
