"""Display all retained Q/E positive contact intervals, without new geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.transforms import blended_transform_factory
import numpy as np

HERE = Path(__file__).resolve().parent
BLUE, ORANGE, INK, BACKGROUND = '#0072B2', '#D55E00', '#173249', '#f5f7f9'
METHOD = 'own_source_parametric_encoded_contact_1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scale_bar(ax, mm=10.):
    low, high = ax.get_xlim()
    start = (low + high - mm) / 2
    transform = blended_transform_factory(ax.transData, ax.transAxes)
    line, = ax.plot([start, start + mm], [-.16, -.16], transform=transform,
                    color=INK, lw=2.8, solid_capstyle='butt', clip_on=False)
    ax.text(.5, -.215, '10 mm', transform=ax.transAxes, ha='center', va='center',
            fontsize=11, color=INK)
    return line, start


def main(output):
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('60-second display-only render budget')))
    signal.alarm(60)
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError('The display output must be fresh and have no symlink ancestor')
    inputs = json.loads((HERE / 'inputs.json').read_text())
    frozen = dict(inputs['files_sha256'], **{'render.py': inputs['render_sha256'], 'inputs.json': sha(HERE / 'inputs.json')})
    if any(sha(HERE / name) != digest for name, digest in frozen.items()):
        raise ValueError('A retained display source/input differs')
    versions = dict(python=sys.version.split()[0], numpy=np.__version__, matplotlib=matplotlib.__version__)
    if versions != inputs['versions']: raise ValueError('The recorded display runtime differs')
    fonts = {weight: sha(findfont(FontProperties(family='DejaVu Sans', weight=weight))) for weight in ('normal', 'bold')}
    if fonts != inputs['font_sha256']: raise ValueError('The recorded display fonts differ')
    data = json.loads((HERE / 'data/figure-data.json').read_text())
    if (data['method'] != METHOD or data['source_index'] != 0 or data['layer'] != 0 or data['z_mm'] != .03 or
            data['groups'] != 337 or data['upper_anchors'] != 0 or data['part_minimum_z_mm'] != 10. or
            data['global_admission'] is not False or data['six_admissions_available'] is not False):
        raise ValueError('Only the completed original000 native first-layer contact diagnostic is in scope')
    with np.load(HERE / 'data/contact-intervals.npz', allow_pickle=False) as archive:
        q, e = archive['Q_intervals_mm'].copy(), archive['E_positive_intervals_mm'].copy()
        qids, eids = archive['Q_witness_index'].copy(), archive['E_Q_witness_index'].copy()
    if (q.shape != (129026, 2, 2) or e.shape != (129023, 2, 2) or q.dtype != np.float64 or e.dtype != np.float64 or
            not np.isfinite(q).all() or not np.isfinite(e).all() or qids.shape != (129026,) or eids.shape != (129023,) or
            len(set(qids.tolist())) != 70144 or len(set(eids.tolist())) != 70141):
        raise ValueError('The complete retained positive-interval arrays differ')
    omitted = data['omissions']
    omitted_ids = [row['q_witness_index'] for row in omitted]
    if sorted(set(qids.tolist()) - set(eids.tolist())) != sorted(omitted_ids) or len(omitted) != 3:
        raise ValueError('The three excluded point contacts differ')
    points = []
    for index in omitted_ids:
        rows = q[qids == index]
        if rows.shape != (1, 2, 2) or not np.array_equal(rows[0, 0], rows[0, 1]):
            raise ValueError('The excluded retained Q display interval is not its encoded point')
        points.append(rows[0, 0])
    points = np.asarray(points)
    bounds = np.array([np.minimum(q.min(axis=(0, 1)), e.min(axis=(0, 1))),
                       np.maximum(q.max(axis=(0, 1)), e.max(axis=(0, 1)))])
    centre = bounds.mean(axis=0)
    zoom_index = min(range(3), key=lambda i: (float(np.sum((points[i] - centre) ** 2)), i))
    zoom_bounds = np.array([points[zoom_index] - 7., points[zoom_index] + 7.])
    padding = .055 * float(np.max(bounds[1] - bounds[0]))
    full_bounds = bounds + np.array([[-padding, -padding], [padding, padding]])
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'path.simplify': False, 'svg.fonttype': 'none',
        'svg.hashsalt': 'carrier-original000-anchored-intervals-figure19-20261017', 'pdf.fonttype': 42})
    output.mkdir(exist_ok=False)
    fig, axes = plt.subplots(1, 2, figsize=(16, 11), dpi=180, facecolor=BACKGROUND)
    bars, drawn = [], []
    for ax, view, title in zip(axes, [full_bounds, zoom_bounds],
            ['Ensemble — coordonnées réelles XY', 'Détail — autour d’un des trois points exclus']):
        ax.set_facecolor('white')
        collections = [LineCollection(q, colors=BLUE, linewidths=1.10, alpha=.76, rasterized=True),
                       LineCollection(e, colors=ORANGE, linewidths=.45, alpha=.95, rasterized=True)]
        for collection in collections: ax.add_collection(collection)
        if [len(c.get_segments()) for c in collections] != [129026, 129023]:
            raise ValueError('An interval was omitted from a display panel')
        drawn.append([len(c.get_segments()) for c in collections])
        ax.scatter(points[:, 0], points[:, 1], s=115, facecolors='none', edgecolors=INK, linewidths=1.3, zorder=5)
        ax.set(xlim=view[:, 0], ylim=view[:, 1], xlabel='X (mm)', ylabel='Y (mm)')
        ax.set_aspect('equal', adjustable='box')
        ax.ticklabel_format(useOffset=False, style='plain')
        ax.grid(color='#cdd6de', alpha=.48, lw=.6)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=10, colors=INK)
        ax.set_title(title, fontsize=13, loc='left', color=INK, pad=15)
        bars.append(scale_bar(ax))
    axes[0].add_patch(Rectangle(zoom_bounds[0], *(zoom_bounds[1] - zoom_bounds[0]),
        fill=False, edgecolor=INK, lw=1.1, linestyle='--'))
    axes[1].annotate('Point exclu des ancres E', points[zoom_index], xytext=(12, 22), textcoords='offset points',
        fontsize=10.5, color=INK, arrowprops=dict(arrowstyle='-', color=INK, lw=.8),
        bbox=dict(facecolor='white', edgecolor='none', alpha=.88, boxstyle='round,pad=.25'))
    fig.suptitle('Contacts au plateau — région 000', x=.055, y=.966, ha='left', fontsize=26, weight='bold', color=INK)
    fig.text(.055, .922, 'Couche native 0   ·   Z = 0,030 mm   ·   337 groupes / 171 694 faces', fontsize=15.5, color=INK)
    fig.text(.055, .883, '70 144 segments Q ancrés   →   70 141 vecteurs E ancrés par transport paramétrique', fontsize=14.5, color=INK)
    fig.text(.055, .845, 'Diagnostic local : 1 couche / 1 034   ·   1 région / 7   ·   aucune admission globale',
        fontsize=13, weight='bold', color='#995700',
        bbox=dict(facecolor='#fff2dc', edgecolor='none', boxstyle='round,pad=.5'))
    fig.legend(handles=[Line2D([0], [0], color=BLUE, lw=2.5, label='129 026 intervalles Q attestés'),
                        Line2D([0], [0], color=ORANGE, lw=2.5, label='129 023 intervalles E positifs reclipés'),
                        Line2D([0], [0], marker='o', markerfacecolor='none', markeredgecolor=INK,
                            color='none', markersize=8, label='3 contacts Q devenus points : aucune ancre E')],
        loc='lower left', bbox_to_anchor=(.045, .155), ncol=2, frameon=False, fontsize=11.4)
    fig.text(.055, .135, 'Les 3 omissions sont des points couverts, sans ancrage transmis au vecteur qui les couvre.', fontsize=11.5, color=INK)
    fig.text(.055, .110, 'Contact haut absent : la couche précède la pièce (Z min. = 10 mm). Une composante, aucune sans ancre basse.', fontsize=11, color='#486174')
    fig.text(.055, .085, 'Chevauchement littéral E : 68 246 ancrages ; le contrat paramétrique est distinct et attesté par chaque coupe source.', fontsize=10.8, color='#486174')
    fig.text(.055, .058, 'Tous les intervalles conservés sont dessinés dans les deux panneaux, sans décimation ; les 94 734 vecteurs complets ne sont pas représentés.', fontsize=10, color='#486174')
    fig.text(.055, .034, 'Méthode : own_source_parametric_encoded_contact_1   ·   aucune coupe, aucun contact recalculé pour cette image.', fontsize=10, color='#486174')
    fig.subplots_adjust(left=.07, right=.97, bottom=.335, top=.762, wspace=.25)
    fig.canvas.draw()
    checks = []
    for ax, (line, start) in zip(axes, bars):
        endpoints = line.get_transform().transform(np.array([[start, -.16], [start + 10., -.16]]))
        delta = endpoints[1] - endpoints[0]
        matrix = ax.transData.get_affine().get_matrix()
        expected = 10. * matrix[0, 0]
        allowance = 32. * np.finfo(float).eps * max(1., float(np.max(np.abs(endpoints))), abs(expected))
        equal_scale_allowance = 32. * np.finfo(float).eps * max(1., abs(matrix[0, 0]), abs(matrix[1, 1]))
        passed = abs(delta[0] - expected) <= allowance and abs(delta[1]) <= allowance and abs(matrix[0, 0] - matrix[1, 1]) <= equal_scale_allowance
        if not passed: raise ValueError('The10mm screen projection or1:1 axis scale differs')
        checks.append(dict(data_length_mm=10., data_x_endpoints_mm=[start, start + 10.],
            projected_endpoints_pixels=endpoints.tolist(), projected_delta_pixels=delta.tolist(),
            expected_horizontal_pixels=expected, floating_operation_allowance_pixels=allowance,
            allowance_scope='32eps times pixel magnitude; display arithmetic only, no geometric tolerance',
            x_y_equal_scale=True, passed=bool(passed)))
    exports = {}
    for suffix in ('png', 'svg', 'pdf'):
        target = output / ('region000-anchored-contact-intervals.' + suffix)
        metadata = {'Creator': 'Carrier retained anchored-contact interval renderer'}
        if suffix == 'png': metadata = {'Software': 'Carrier retained anchored-contact interval renderer'}
        if suffix == 'svg': metadata.update(Date=None)
        if suffix == 'pdf': metadata.update(CreationDate=None, ModDate=None)
        fig.savefig(target, dpi=180, facecolor=fig.get_facecolor(), metadata=metadata)
        exports[target.name] = sha(target)
    plt.close(fig)
    if any(sha(HERE / name) != digest for name, digest in frozen.items()):
        raise ValueError('A retained plotting input/source changed')
    receipt = dict(status='rendered_retained_original000_contact_intervals_no_global_admission', method=METHOD,
        inputs_sha256=frozen, inputs_unchanged=True, exports_sha256=exports, versions=versions, font_sha256=fonts,
        Q_intervals=129026, E_positive_intervals=129023, Q_anchored_segments=70144, E_anchored_vectors=70141,
        displayed_intervals_per_panel=drawn, interval_order_and_duplicates_preserved=True,
        all_retained_intervals_drawn_in_each_panel=True, data_decimated=False, displayed_coordinates_modified=False,
        display_scope='Retained positively anchored contact intervals only, not all machine vectors.',
        vector_format_collection_rendering='All interval paths rendered at180dpi; SVG/PDF embed those raster layers and retain vector axes/text.',
        omitted_Q_point_ids=omitted_ids, zoom_rule='Excluded point closest to full displayed bbox centre; ties use retained omission order.',
        zoom_witness_index=omitted_ids[zoom_index], zoom_bounds_mm=zoom_bounds.tolist(), full_data_bounds_mm=bounds.tolist(),
        scale_projection_checks=checks, original_source_index=0, native_layer=0, z_mm=.03, authenticated_groups=337,
        upper_contacts=0, part_minimum_z_mm=10., no_Q_point_anchor_transferred=True,
        literal_encoded_overlap_and_parametric_transport_distinct=True, no_geometry_or_contacts_recomputed=True,
        global_admission=False, section_workers=0, elapsed_seconds=time.monotonic() - started)
    with (output / 'render-receipt.json').open('x') as stream: json.dump(receipt, stream, indent=2); stream.write('\n')
    signal.alarm(0)
    print(json.dumps({k: receipt[k] for k in ('status', 'elapsed_seconds', 'Q_intervals', 'E_positive_intervals', 'exports_sha256')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    main(parser.parse_args().output)
