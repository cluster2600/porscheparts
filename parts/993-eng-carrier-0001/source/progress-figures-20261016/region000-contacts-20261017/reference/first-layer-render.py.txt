"""Plot retained first-layer candidates and rational contact witnesses only."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.transforms import blended_transform_factory
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE
DATA = HERE / 'data'
PINS = {
    'layers/layer-00000.npz': '8d3c4cec323ff46d9c3c17efcbf7d053421207752e202519dda320a243f25903',
    'layer-assessments.jsonl': 'c95e3b8819b6d3b87679a2171187c61ed54a3824214d011aa5049f43674329bf',
}
ROW_SHA256 = 'ebf55eebc8b6eb757b71d0173ba9cb6ec87c29e0e5d6b1a1bfbec8dd82fa8159'
BLUE, ORANGE, INK, BACKGROUND = '#0072B2', '#D55E00', '#173249', '#f5f7f9'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def coordinate(value):
    if set(value) != {'numerator', 'denominator', 'nearest_float'}:
        raise ValueError('A complete retained rational coordinate is required')
    exact = Fraction(int(value['numerator']), int(value['denominator']))
    encoded = float(exact)
    if not math.isfinite(encoded) or encoded != value['nearest_float']:
        raise ValueError('The retained nearest-float witness differs')
    return encoded


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
    if output.exists() or output.is_symlink():
        raise ValueError('The scientific rendering output must be fresh')
    frozen = {DATA / name: digest for name, digest in PINS.items()}
    frozen[Path(__file__)] = sha(__file__)
    if any(sha(p) != digest for p, digest in frozen.items()):
        raise ValueError('A retained layer, witness or rendering source differs')
    with (DATA / 'layer-assessments.jsonl').open('rb') as stream:
        first = stream.readline()
        completed_rows = 1 + sum(1 for _ in stream)
    if hashlib.sha256(first).hexdigest() != ROW_SHA256 or completed_rows != 14:
        raise ValueError('The first-layer receipt or completed-prefix count differs')
    row = json.loads(first)
    if row['layer'] != 0 or row['z_mm'] != .03 or not row['candidate_vectors']['passed']:
        raise ValueError('The retained first-layer vector/rational check differs')
    if row['candidate_vectors']['segments'] != 6753 or row['rational_confinement']['unique_rational_segments'] != 6753:
        raise ValueError('Exactly6753 checked vectors and rational sections are required')
    if any(row[key] != dict(layer_components=1, unanchored_layer_components=0)
           for key in ('connectivity', 'encoded_connectivity')):
        raise ValueError('The retained first-layer connectivity differs')
    with np.load(DATA / 'layers/layer-00000.npz', allow_pickle=False) as data:
        if set(data.files) != {'z_mm', 'candidate_support_scan_segments_mm'} or float(data['z_mm']) != .03:
            raise ValueError('Only the retained first-layer candidate vectors may be plotted')
        vectors = data['candidate_support_scan_segments_mm'].copy()
    if vectors.shape != (6753, 2, 2) or vectors.dtype != np.float64 or not np.isfinite(vectors).all():
        raise ValueError('The complete finite vector array is required')
    witnesses = row['contact_witnesses']
    if (len(witnesses) != 4024 or len({w['segment'] for w in witnesses}) != 4024 or
            any(w['side'] != 'lower' or w['anchor'] != 'plate_first_layer' or
                w['region'] != 10 or w['exact_part_overlap_intervals'] for w in witnesses)):
        raise ValueError('The retained4024 distinct plateau-anchor witnesses differ')
    contacts = np.asarray([[[coordinate(c) for c in p] for p in interval]
        for witness in witnesses for interval in witness['exact_plate_overlap_intervals']], dtype=np.float64)
    if contacts.shape != (6658, 2, 2):
        raise ValueError('Every retained plateau interval must be displayed without deduplication')
    bounds = np.array([vectors.min(axis=(0, 1)), vectors.max(axis=(0, 1))])
    centre = bounds.mean(axis=0)
    midpoints = contacts.mean(axis=1)
    zoom_index = min(range(len(contacts)), key=lambda i: (float(np.sum((midpoints[i] - centre) ** 2)), i))
    zoom_centre = midpoints[zoom_index]
    zoom_bounds = np.array([zoom_centre - 7., zoom_centre + 7.])
    padding = .06 * float(np.max(bounds[1] - bounds[0]))
    full_bounds = bounds + np.array([[-padding, -padding], [padding, padding]])
    output.mkdir(exist_ok=False)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'path.simplify': False,
                         'svg.fonttype': 'none', 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(16, 10), dpi=180, facecolor=BACKGROUND)
    bars = []
    for ax, view, title in zip(axes, [full_bounds, zoom_bounds],
            ['Ensemble — coordonnées réelles XY', 'Détail — contact le plus proche du centre']):
        ax.set_facecolor('white')
        ax.add_collection(LineCollection(vectors, colors=BLUE, linewidths=.75, alpha=.80))
        ax.add_collection(LineCollection(contacts, colors=ORANGE, linewidths=1.65, alpha=.95))
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
    fig.suptitle('Première couche — région 010', x=.055, y=.965, ha='left',
                 fontsize=26, weight='bold', color=INK)
    fig.text(.055, .915, 'Z = 0,030 mm   ·   6 753 coupes / vecteurs   ·   4 024 vecteurs ancrés',
             fontsize=16, color=INK)
    fig.text(.055, .875, '1 composante, 0 flottante — mêmes résultats sur les segments rationnels et encodés',
             fontsize=12.5, color='#486174')
    fig.text(.055, .819, '14 couches contrôlées / 1 034 ; région locale, pas de validation globale d’impression',
             fontsize=14, weight='bold', color='#995700',
             bbox=dict(facecolor='#fff2dc', edgecolor='none', boxstyle='round,pad=.55'))
    fig.legend(handles=[Line2D([0], [0], color=BLUE, lw=2, label='6 753 vecteurs candidats, tous conservés'),
                        Line2D([0], [0], color=ORANGE, lw=2.5, label='6 658 intervalles attestés au plateau')],
               loc='lower left', bbox_to_anchor=(.05, .087), ncol=2, frameon=False, fontsize=12)
    fig.text(.055, .055, 'Chaque intervalle orange provient d’un témoin rationnel conservé ; seul son encodage d’affichage est utilisé.',
             fontsize=10.5, color='#486174')
    fig.text(.055, .030, 'Aucune coupe recalculée, aucun segment décimé. Le zoom utilise les mêmes données, sans déplacement.',
             fontsize=10.5, color='#486174')
    fig.subplots_adjust(left=.07, right=.97, bottom=.285, top=.745, wspace=.28)
    fig.canvas.draw()
    proofs = []
    for ax, (line, start) in zip(axes, bars):
        endpoints = line.get_transform().transform(np.array([[start, -.16], [start + 10., -.16]]))
        delta = endpoints[1] - endpoints[0]
        matrix = ax.transData.get_affine().get_matrix()
        expected = 10. * matrix[0, 0]
        allowance = 32. * np.finfo(float).eps * max(1., float(np.max(np.abs(endpoints))), abs(expected))
        equal_scale_allowance = 32. * np.finfo(float).eps * max(1., abs(matrix[0, 0]), abs(matrix[1, 1]))
        passed = abs(delta[0] - expected) <= allowance and abs(delta[1]) <= allowance and abs(matrix[0, 0] - matrix[1, 1]) <= equal_scale_allowance
        if not passed: raise ValueError('The10mm screen projection or1:1 axis scale differs')
        proofs.append(dict(data_length_mm=10., data_x_endpoints_mm=[start, start + 10.],
            projected_endpoints_pixels=endpoints.tolist(), projected_delta_pixels=delta.tolist(),
            expected_horizontal_pixels=expected, floating_operation_allowance_pixels=allowance,
            allowance_scope='32eps times pixel magnitude; display arithmetic only, no geometric tolerance',
            x_y_equal_scale=True, passed=bool(passed)))
    for suffix in ('png', 'svg', 'pdf'):
        fig.savefig(output / ('first-layer-contacts.' + suffix), dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)
    if any(sha(p) != digest for p, digest in frozen.items()):
        raise ValueError('The retained plotting inputs or renderer changed')
    result = dict(status='rendered_retained_local_first_layer_no_global_admission', source_sha256=sha(__file__),
        inputs_sha256={str(p.relative_to(ROOT)): h for p, h in frozen.items()}, inputs_unchanged=True,
        first_jsonl_line_sha256=ROW_SHA256, first_layer_only=True, completed_prefix_rows=14,
        vectors=6753, rational_sections=6753, anchored_distinct_vector_ids=4024, retained_contact_intervals=6658,
        all_nearest_float_witness_values_verified=True, orange_intervals_deduplicated=False,
        all_input_segments_drawn_in_each_panel=True, data_decimated=False, displayed_coordinates_modified=False,
        zoom_rule='First retained interval midpoint with smallest squared distance to the full-vector bbox centre; ties use retained interval order',
        zoom_interval_index=zoom_index, zoom_bounds_mm=zoom_bounds.tolist(), full_data_bounds_mm=bounds.tolist(),
        scale_projection_checks=proofs, versions=dict(numpy=np.__version__, matplotlib=matplotlib.__version__),
        no_geometry_or_sections_recomputed=True, section_workers=0, global_print_validation=False,
        outputs_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()}, elapsed_seconds=time.monotonic() - started)
    with (output / 'render-receipt.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status=result['status'], elapsed_seconds=result['elapsed_seconds'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    main(parser.parse_args().output)
