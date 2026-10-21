"""Real chart152 data only: render stored IEEE polygons; no AM or proof recomputation."""
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def polygon(hexadecimal):
    data = bytes.fromhex(hexadecimal)
    if not data or data[0] != 1 or struct.unpack_from('<I', data, 1)[0] != 3:
        raise ValueError('The real little-endian Polygon WKB is required')
    rings, offset = [], 9
    for unused in range(struct.unpack_from('<I', data, 5)[0]):
        count = struct.unpack_from('<I', data, offset)[0];offset += 4
        ring = [struct.unpack_from('<dd', data, offset + 16 * i) for i in range(count)];offset += 16 * count
        if len(ring) < 4 or ring[0] != ring[-1] or any(not math.isfinite(c) for point in ring for c in point):
            raise ValueError('A finite closed stored ring is required')
        rings.append(ring)
    if offset != len(data) or len(rings) != 1:
        raise ValueError('These two real single-ring chart polygons are required')
    return rings[0]


def rational(record):
    q = Q(int(record['numerator']), int(record['denominator']))
    if (str(q.numerator) != record['numerator'] or str(q.denominator) != record['denominator']
            or float(q).hex() != float(record['nearest_float']).hex()):
        raise ValueError('The encoded rational source edge differs')
    return q


def load():
    inputs = json.loads((HERE / 'inputs.json').read_text())
    for name, expected in inputs['files_sha256'].items():
        path = HERE / name
        if path.is_symlink() or sha(path) != expected:
            raise ValueError('The source figure inputs changed: ' + name)
    a = json.loads((HERE / 'data/assessment.json').read_text())
    c = json.loads((HERE / 'data/authentic-chart.json').read_text())
    if (a['status'] != 'authentic_chart5047_repair_required_contacts_band_passed_no_global_admission'
            or a['global_admission'] is not False or a['generated_component_contact_flags'] != [False]
            or a['exact_redundant_whole_strip_count'] != 2 or a['lower_interface_absent_is_not_invented'] is not True
            or len(c['source_face_indices']) != 88 or a['remapping']['triangles'] != 24
            or a['source_domain_geometry_wkb_hex'] != c['source_domain_geometry_wkb_hex']):
        raise ValueError('The real local chart scope/remaining refusal changed')
    for stem in ('source_domain', 'generated_material'):
        if hashlib.sha256(bytes.fromhex(a[stem + '_geometry_wkb_hex'])).hexdigest() != a[stem + '_geometry_sha256']:
            raise ValueError('A retained polygon WKB digest differs')
    interval, = a['infill']['continuous_interface_reconstruction']['intervals']
    interfaces = interval['attested_source_interfaces']
    if (interfaces != c['unfolding']['source_interface_traces_2d_mm'] or interfaces['lower'] != [] or len(interfaces['upper']) != 3
            or hashlib.sha256(json.dumps(interfaces, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != interval['attested_source_interfaces_sha256']):
        raise ValueError('The three upper traces and absent lower traces must stay authentic')
    domain_sha, material_sha = a['source_domain_geometry_sha256'], a['generated_material_geometry_sha256']
    free, band = interval['exact_free_domain_coverage'], interval['exact_intended_band_union_confinement']
    if (free['passed'] is not True or free['source_geometry_sha256'] != domain_sha or free['target_geometry_sha256'] != material_sha
            or band['passed'] is not True or band['source_geometry_sha256'] != material_sha or band['free_domain_geometry_sha256'] != domain_sha):
        raise ValueError('The existing exact proof references differ; no proof is recomputed by the renderer')
    quads = []
    for edge in interval['combinatorial_construction']['whole_edge_interfaces']:
        if edge.get('strip_status') != 'excluded_redundant_inside_source_domain':
            continue
        proof = edge['redundancy_certificate'];coverage = proof['exact_redundancy_coverage']
        raw = bytes.fromhex(proof['proposed_strip_geometry_wkb_hex'])
        if (proof['status'] != 'certified_redundant_no_addition' or proof['original_contact_role'] != 'upper'
                or proof['contact_role_unchanged'] is not True or proof['source_trace_unchanged'] is not True
                or hashlib.sha256(raw).hexdigest() != proof['proposed_strip_geometry_sha256']
                or coverage['passed'] is not True or coverage['source_geometry_sha256'] != proof['proposed_strip_geometry_sha256']
                or coverage['target_geometry_sha256'] != domain_sha):
            raise ValueError('A complete whole-strip inclusion receipt is required')
        points = polygon(raw.hex())
        source = [tuple(rational(v) for v in p) for p in edge['source_edge']]
        if len(points) != 5 or [tuple(Q(v) for v in p) for p in points[:2]] != source:
            raise ValueError('The shown quadrilateral does not start at its attested exact edge')
        quads.append(dict(edge=edge['edge'], points=points, geometry_sha256=proof['proposed_strip_geometry_sha256'],
            width_mm=float(abs(Q(points[1][0]) - Q(points[0][0]))),
            height_mm=float(abs(Q(points[2][1]) - Q(points[1][1]))),
            decoded_IEEE_coordinates_Q=[[[str(Q(v).numerator), str(Q(v).denominator)] for v in p] for p in points],
            existing_inclusion_status=coverage['status'], existing_proof_source_sha256=coverage['proof_source_sha256']))
    if len(quads) != 2 or [q['edge'] for q in quads] != [1, 2]:
        raise ValueError('Only the two actual inward quads are plotted')
    return inputs, a, c, polygon(a['source_domain_geometry_wkb_hex']), polygon(a['generated_material_geometry_wkb_hex']), quads, interfaces


def fr(value, digits=4):
    return f'{value:.{digits}f}'.replace('.', ',')


def main():
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('60 s chart figure budget')))
    signal.setitimer(signal.ITIMER_REAL, 60)
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = '1'
    os.environ['MPLCONFIGDIR'] = str(HERE / 'mpl-cache')
    inputs, assessment, chart, domain, material, quads, interfaces = load()
    output = Path(sys.argv[1]).absolute()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError('A fresh real output directory is required')
    frozen = {str(HERE / name): sha(HERE / name) for name in ['render.py', 'inputs.json', 'data/assessment.json', 'data/authentic-chart.json']}
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.backends.backend_agg
    import matplotlib.backends.backend_svg
    import matplotlib.backends.backend_pdf
    from matplotlib.patches import Polygon
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FuncFormatter
    from matplotlib import font_manager
    import numpy as np
    import PIL
    font = font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'), fallback_to_default=False)
    runtime_paths = {str(Path(sys.executable).resolve()), font}
    runtime_paths.update(str(Path(module.__file__).resolve()) for name, module in list(sys.modules.items())
        if name.split('.')[0] in ('matplotlib', 'numpy', 'PIL') and getattr(module, '__file__', None) and Path(module.__file__).is_file())
    runtime = {path: sha(path) for path in sorted(runtime_paths)}
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'text.color': '#192C3B',
        'axes.labelcolor': '#334D5E', 'axes.edgecolor': '#B6C3CE', 'xtick.color': '#506C7D', 'ytick.color': '#506C7D',
        'svg.fonttype': 'none', 'svg.hashsalt': 'carrier-source008-chart152-001', 'pdf.fonttype': 42, 'path.simplify': False})
    fig = plt.figure(figsize=(15.2, 10.5), facecolor='#FAFCFE')
    fig.text(.06, .955, 'RÉGION 008 · CHART 152 · DIAGNOSTIC LOCAL RÉEL', fontsize=11, weight='bold', color='#506C7D')
    fig.text(.06, .912, 'Quand une bande est déjà dans la matière', fontsize=25, weight='bold')
    fig.text(.06, .873, 'Deux bandes de rôle «upper» sont déjà contenues dans D ; les reçus lient aussi D à la matière générée R.', fontsize=12.4, color='#506C7D')
    fig.text(.06, .821, 'A · DOMAINE ENTIER — Z HORIZONTAL POUR LA LISIBILITÉ', fontsize=11, weight='bold')
    whole = fig.add_axes([.075, .605, .85, .185], facecolor='white')
    zoom = fig.add_axes([.075, .185, .53, .285], facecolor='white')
    domain_color, material_color = '#CEE6EF', '#7E75A9'
    colors = ['#D99634', '#E8B45E']
    formatter = FuncFormatter(lambda x, unused: f'{x:g}'.replace('.', ','))
    def draw(ax, swap=False):
        def p(points):return [(z, t) if swap else (t, z) for t, z in points]
        ax.add_patch(Polygon(p(material), closed=True, facecolor='#F0EDF7', edgecolor=material_color, lw=2.1, zorder=1))
        ax.add_patch(Polygon(p(domain), closed=True, facecolor=domain_color, edgecolor='#337493', lw=1.2, zorder=2))
        for i, quad in enumerate(quads):
            ax.add_patch(Polygon(p(quad['points']), closed=True, facecolor=colors[i], edgecolor='#A56C1D',
                                 lw=1.2, hatch='///' if i == 0 else '..', alpha=.87, zorder=3))
        for trace in interfaces['upper']:
            line = p(trace);ax.plot([q[0] for q in line], [q[1] for q in line], color='#A6473C', lw=2.6, zorder=4)
        ax.set_aspect('equal');ax.xaxis.set_major_formatter(formatter);ax.yaxis.set_major_formatter(formatter)
        ax.grid(color='#E5EDF2', lw=.65);ax.set_axisbelow(True)
    draw(whole, True)
    t0, t1 = min(t for t, z in domain), max(t for t, z in domain)
    z0, z1 = min(z for t, z in domain), max(z for t, z in domain)
    whole.set_xlim(z0 - .6, z1 + .7);whole.set_ylim(t0 - .38, t1 + .40)
    whole.set_xlabel('Z dans le repère d’impression (mm)');whole.set_ylabel('t intrinsèque (mm)')
    whole.annotate('', xy=(z1, t1 + .22), xytext=(z0, t1 + .22), arrowprops=dict(arrowstyle='<->', color='#334D5E', lw=1))
    whole.text((z0 + z1) / 2, t1 + .29, 'Étendue de D en Z : ' + fr(z1 - z0) + ' mm', ha='center', va='bottom', fontsize=10)
    whole.plot([40, 45], [t0 - .23] * 2, color='#192C3B', lw=3, solid_capstyle='butt')
    whole.text(42.5, t0 - .19, '5 mm', ha='center', va='bottom', fontsize=9)
    whole.annotate('Zoom B', xy=(z0 + .10, (t0 + t1) / 2), xytext=(z0 + 2, t0 - .18),
        arrowprops=dict(arrowstyle='->', color='#A56C1D', lw=1.1), color='#A56C1D', fontsize=10)
    fig.text(.075, .522, 'B · DEUX QUADS RÉELS, À L’INTÉRIEUR DU DOMAINE SOURCE', fontsize=11, weight='bold')
    draw(zoom)
    zoom.set_xlim(t0 - .14, t1 + .27);zoom.set_ylim(z0 - .13, z0 + .58)
    zoom.set_xlabel('t intrinsèque (mm)');zoom.set_ylabel('Z (mm)')
    for i, quad in enumerate(quads):
        pts = quad['points'];center = (pts[0][0] + pts[1][0]) / 2
        zoom.text(center, z0 + .105, str(i + 1), ha='center', va='center', weight='bold', fontsize=12, color='#694510')
        yy = z0 + .31
        zoom.annotate('', xy=(pts[1][0], yy), xytext=(pts[0][0], yy), arrowprops=dict(arrowstyle='<->', color='#7C5A27', lw=1))
        zoom.text(center, yy + .025, fr(quad['width_mm']) + ' mm', ha='center', va='bottom', fontsize=9.5, color='#7C5A27')
    xx = t1 + .13
    zoom.annotate('', xy=(xx, quads[1]['points'][2][1]), xytext=(xx, z0), arrowprops=dict(arrowstyle='<->', color='#7C5A27', lw=1.2))
    zoom.text(xx + .025, z0 + .10, 'ΔZ = ' + fr(quads[1]['height_mm']) + ' mm', rotation=90, va='center', fontsize=9.5, color='#7C5A27')
    zoom.plot([0, .2], [z0 - .065] * 2, color='#192C3B', lw=3, solid_capstyle='butt')
    zoom.text(.1, z0 - .05, '0,2 mm', ha='center', va='bottom', fontsize=9)
    zoom.text((t0 + t1) / 2, z0 - .105, 'Traces «upper» : rôle source conservé ; aucune trace «lower» inventée.', ha='center', fontsize=9.2, color='#7C3E37')
    card = fig.add_axes([.66, .185, .29, .34]);card.axis('off')
    card.text(0, 1, 'LE REÇU, PAS L’IMAGE, PORTE LA PREUVE', weight='bold', fontsize=10, color='#506C7D', va='top')
    card.text(0, .86, '2 bandes entièrement dans D', weight='bold', fontsize=16, va='top')
    card.text(0, .74, 'Couverture rationnelle de chaque quad : PASS.\nAucune de ces deux bandes n’est ajoutée.\nTraces et rôle «upper» inchangés.', fontsize=11, color='#506C7D', va='top', linespacing=1.6)
    card.text(0, .47, 'Contacts du composant non validés', weight='bold', fontsize=14, va='top', color='#9B493C')
    card.text(0, .35, 'generated_component_contact_flags = [false]', fontsize=9, family='DejaVu Sans Mono', va='top', color='#9B493C')
    card.text(0, .24, '88 faces source · 24 triangles remappés.\nPas de graphe matière global ni d’exposition.\nAucune admission régionale ou globale.', fontsize=11, color='#506C7D', va='top', linespacing=1.6)
    handles = [Line2D([0], [0], color='#337493', lw=8, alpha=.6, label='D : domaine source'),
        Line2D([0], [0], color=material_color, lw=2, label='R : matière générée'),
        Line2D([0], [0], color='#D99634', lw=8, label='Deux bandes redondantes'),
        Line2D([0], [0], color='#A6473C', lw=2.6, label='Trois interfaces upper réelles')]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(.065, .093), ncol=4, frameon=False, fontsize=10)
    fig.text(.06, .048, 'Coordonnées intrinsèques en mm, sans modification de la géométrie. Dimensions affichées arrondies ; valeurs IEEE exactes liées au reçu.\n'
        'Rejeu 0ab2792b… · domaine 66dee15e… · quads 5f4f0ce0… / c263c7b2… · la vue ne remplace aucune preuve ni aucun contrôle restant.',
        fontsize=9.2, color='#647A88', linespacing=1.6)
    fig.canvas.draw()
    scale_checks = []
    for name, ax, first, last, span in [('A', whole, (40., t0 - .23), (45., t0 - .23), 5.),
                                       ('B', zoom, (0., z0 - .065), (.2, z0 - .065), .2)]:
        projected = ax.transData.transform([first, last])
        x_unit = ax.transData.transform((1., 0.)) - ax.transData.transform((0., 0.))
        y_unit = ax.transData.transform((0., 1.)) - ax.transData.transform((0., 0.))
        equal = math.isclose(float(np.linalg.norm(x_unit)), float(np.linalg.norm(y_unit)), rel_tol=1e-12)
        pixels = float(np.linalg.norm(projected[1] - projected[0]))
        if not equal or not math.isclose(pixels / float(np.linalg.norm(x_unit)), span, rel_tol=1e-12):
            raise ValueError('A rendered scale bar does not equal its real coordinate span')
        scale_checks.append(dict(view=name, span_mm=span, projected_pixels_at_figure_dpi=pixels, equal_axis_unit_scale=equal))
    output.mkdir();stem = 'source008-chart152-bandes-deja-contenues'
    fig.savefig(output / (stem + '.png'), dpi=200, metadata={'Software': 'Real chart152 stored-geometry figure'})
    fig.savefig(output / (stem + '.svg'), metadata={'Date': None, 'Creator': 'Real chart152 stored-geometry figure'})
    fig.savefig(output / (stem + '.pdf'), metadata={'CreationDate': None, 'ModDate': None, 'Creator': 'Real chart152 stored-geometry figure'})
    plt.close(fig)
    if any(sha(path) != expected for path, expected in {**frozen, **runtime}.items()):
        raise ValueError('Figure source/input/runtime changed')
    receipt = dict(schema='source008-chart152-stored-geometry-figure-1', status='rendered_local_diagnostic_no_admission',
        source_and_inputs_sha256=frozen, source_origins=inputs['source_origins'], runtime_files_sha256=runtime,
        runtime_versions=dict(python=sys.version.split()[0], matplotlib=matplotlib.__version__, numpy=np.__version__, Pillow=PIL.__version__),
        quads=quads, domain_extent_t_mm=t1 - t0, domain_extent_Z_mm=z1 - z0,
        overview_axes=['Z_mm', 'intrinsic_t_mm'], overview_equal_scale=True, zoom_axes=['intrinsic_t_mm', 'Z_mm'], zoom_equal_scale=True,
        scale_bars=[dict(view='A', axis='Z', endpoints=[40., 45.], span_mm=5.), dict(view='B', axis='t', endpoints=[0., .2], span_mm=.2)],
        rendered_scale_checks=scale_checks,
        drawn_source_upper_traces=3, source_lower_traces=0, generated_component_contact_flags=assessment['generated_component_contact_flags'],
        source_faces=88, remapped_triangles=24, proof_recomputed=False, geometry_modified=False, AM_run=False,
        global_admission=False, inputs_and_runtime_unchanged=True, worker_processes=0, wall_seconds=time.monotonic() - started,
        outputs_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()})
    (output / 'render-receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(dict(status=receipt['status'], wall_seconds=receipt['wall_seconds'], receipt_sha256=sha(output / 'render-receipt.json'))))


if __name__ == '__main__':
    main()
