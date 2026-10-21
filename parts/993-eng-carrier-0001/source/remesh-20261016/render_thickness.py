"""Plot actual face centres from a retained ray-thickness map without changing its values."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from analyze_thickness import read_dump, regions


def render(dump, localisation, exact_probes, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    triangles, values = read_dump(dump)
    centres, area, labels = regions(triangles)
    report = json.loads(Path(localisation).read_text())
    exact = json.loads(Path(exact_probes).read_text())
    bins = ((1.5, np.inf, '#a8adb4', '≥ 1,50'), (1.49, 1.5, '#2874b8', '1,49–1,50'),
            (1.4, 1.49, '#edbb3b', '1,40–1,49'), (1.3, 1.4, '#ed7d31', '1,30–1,40'), (0., 1.3, '#c42834', '< 1,30'))
    fig = plt.figure(figsize=(13, 8.8), layout='constrained')
    grid = fig.add_gridspec(3, 2, height_ratios=(2., 1.6, .7))
    overview = fig.add_subplot(grid[0, :])
    close = fig.add_subplot(grid[1, 0])
    bars = fig.add_subplot(grid[1, 1])
    notes = fig.add_subplot(grid[2, :]); notes.axis('off')
    for lower, upper, colour, label in bins:
        selected = (values >= lower) & (values < upper)
        overview.scatter(centres[selected, 0], centres[selected, 2], s=.25, color=colour, rasterized=True, label=label + ' mm')
        zoom = selected & (centres[:, 0] > 20) & (centres[:, 0] < 40) & (centres[:, 1] > 0) & (centres[:, 1] < 18)
        close.scatter(centres[zoom, 0], centres[zoom, 1], s=3, color=colour, rasterized=True)
    overview.set(xlabel='X [mm]', ylabel='Z [mm]', title='Vue XZ — centres des 349 898 faces, valeurs originales du checker')
    overview.legend(ncol=5, markerscale=8, loc='upper center', bbox_to_anchor=(.5, 1.28), frameon=False)
    overview.grid(alpha=.15)
    close.set(xlabel='X [mm]', ylabel='Y [mm]', title='Zone de départ des nervures : projection XY', xlim=(20, 40), ylim=(0, 18))
    close.set_aspect('equal'); close.grid(alpha=.15)
    close.annotate('Languette conservée :\n0,010 mm confirmé sur STEP', xy=(27.856, 9.597), xytext=(31, 15), fontsize=8,
                   arrowprops={'arrowstyle': '->', 'color': '#333'})
    names = ['plane_caps', 'webs', 'ribs_and_feet', 'centre_and_mount_regions', 'edges_and_transitions']
    translated = ['Peaux planes', 'Parois courbes', 'Nervures / pieds', 'Centre / extrémités', 'Bords / raccords']
    below = np.array([report['regions'][name]['area_below_mm2']['1.4'] for name in names])
    lower = np.array([report['regions'][name]['area_below_mm2']['1.3'] for name in names])
    bars.barh(translated, lower, color='#c42834', label='< 1,30 mm')
    bars.barh(translated, below - lower, left=lower, color='#ed7d31', label='1,30–1,40 mm')
    bars.invert_yaxis(); bars.set(xlabel='Aire de surface concernée [mm²]', title='Sous 1,40 mm : 2 104,38 mm² (1,132 %)')
    bars.legend(fontsize=8); bars.grid(axis='x', alpha=.15)
    measured = [p['exact_inward_normal_ray_mm'] for p in exact['probes'] if p['region'] == 'web_1p49_to_1p5_area_quartile']
    notes.text(0, .85, 'Seuil initial 1,50 mm conservé : refus. Peaux planes : aucune aire sous 1,50 mm.\n'
               'Parois courbes : 52 609,27 mm² dans [1,49 ; 1,50). Trois rayons normaux exacts STEP : '
               + ' / '.join(f'{v:.6f}' for v in measured) + ' mm.\n'
               'Régions classées par coordonnées ; les rayons proches des arêtes ne constituent pas une épaisseur minimale continue.', fontsize=9, va='top')
    fig.suptitle('Diagnostic d’épaisseur — essai 008 conservé après rejet mécanique', fontsize=15)
    for suffix in ('png', 'svg'):
        fig.savefig(output / ('carrier-thickness-008.' + suffix), dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dump', 'localisation', 'exact_probes', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    render(args.dump, args.localisation, args.exact_probes, args.output)
