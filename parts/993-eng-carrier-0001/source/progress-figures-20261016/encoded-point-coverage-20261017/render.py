"""Plot the actual original owner13 diagnostic; no mesh or process modification."""
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    inputs = json.loads((HERE/'inputs.json').read_text())
    for name, expected in inputs['files_sha256'].items():
        if sha(HERE/name) != expected:
            raise ValueError('The real diagnostic input changed: '+name)
    assessment = json.loads((HERE/'data/assessment.json').read_text())
    execution = json.loads((HERE/'data/execution-receipt.json').read_text())
    rows = [json.loads(line) for line in (HERE/'data/layers.jsonl').read_text().splitlines()]
    if (assessment['status'] != 'all1034_original_owner13_collapsed_encoded_points_covered_no_admission'
            or assessment['global_admission'] or not assessment['inputs_unchanged']
            or execution['actual_returncode'] != 0 or not execution['no_non_zombie_group_members']
            or [r['layer'] for r in rows] != list(range(1034))
            or sum(r['collapsed_events'] for r in rows) != 703):
        raise ValueError('The completed original owner13 diagnostic is required')
    for row in rows:
        for proof in row['collapsed_point_proofs']:
            witness = proof['nonzero_same_owner_witness']
            a, b = [tuple(Q(v) for v in p) for p in witness['encoded_vector_exact']]
            p = tuple(Q(v) for v in proof['rounding_cell']['point'])
            if (a == b or witness['owner'] != proof['owner'] or proof['owner'] != 'skin-13-0'
                    or not proof['entire_encoded_point_covered']
                    or (b[0]-a[0])*(p[1]-a[1]) != (b[1]-a[1])*(p[0]-a[0])
                    or not all(min(x, y) <= v <= max(x, y) for x, y, v in zip(a, b, p))):
                raise ValueError('The plotted diagnostic contains a missing nonzero same-owner witness')
    return inputs, assessment, rows


def main():
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('60 s figure budget')))
    signal.alarm(60)
    output = Path(sys.argv[1]).absolute()
    if output.exists() or any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError('A fresh real output directory is required')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = '1'
    os.environ['MPLCONFIGDIR'] = str(HERE/'mpl-cache')
    inputs, assessment, rows = load()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
        'text.color': '#192C3B', 'axes.labelcolor': '#334D5E', 'axes.edgecolor': '#B6C3CE',
        'svg.fonttype': 'none', 'svg.hashsalt': 'owner13-encoded-point-coverage-001',
        'pdf.fonttype': 42, 'path.simplify': False})
    fig = plt.figure(figsize=(15.2, 10), facecolor='#FAFCFE')
    fig.text(.06, .955, 'RÉGION 000 · PEAU 13 · COUPES DU MAILLAGE ORIGINAL', color='#506C7D', weight='bold')
    fig.text(.06, .912, '703 points déjà couverts, sans changer la pièce', fontsize=25, weight='bold')
    fig.text(.06, .872, 'Les 1 034 hauteurs ont été contrôlées : chaque primitive réduite à un point possède un témoin non nul du même support.', fontsize=12)
    counts = fig.add_axes([.075, .595, .85, .205], facecolor='white')
    height = [float(Q(r['z_exact'])) for r in rows]
    for face, color in [(170702, '#C78635'), (170703, '#758BB0')]:
        count = [sum(p['face_id'] == face for p in r['collapsed_point_proofs']) for r in rows]
        counts.step(height, count, where='mid', color=color, lw=2, label=f'Face {face} : {sum(count)} événements')
    counts.set(xlim=(0, height[-1]), ylim=(-.08, 1.20), yticks=[0, 1],
        xlabel='Hauteur réelle de couche Z (mm)', ylabel='Point par face / couche')
    counts.grid(color='#E5EDF2');counts.legend(loc='upper right', frameon=False)
    fig.text(.075, .815, 'A · RECENSEMENT COMPLET DES DEUX FACES CONCERNÉES', weight='bold', fontsize=11)
    fig.text(.075, .525, 'B · EXEMPLE RÉEL À Z = 7,11 mm — COUCHE 118', weight='bold', fontsize=11)
    ax = fig.add_axes([.075, .18, .40, .30], facecolor='white')
    proof = next(p for p in rows[118]['collapsed_point_proofs'] if p['face_id'] == 170703)
    p = tuple(Q(v) for v in proof['rounding_cell']['point'])
    ulp = tuple(Q(math.ulp(float(v))) for v in p)
    def norm(point):
        return tuple((Q(v)-origin)/unit for v, origin, unit in zip(point, p, ulp))
    cut = [norm(v) for v in proof['original_rational_cut']]
    witness = [norm(v) for v in proof['nonzero_same_owner_witness']['encoded_vector_exact']]
    if witness[1] != (Q(0), Q(0)):
        raise ValueError('This actual figure needs the recorded witness endpoint at P')
    # Show only the portion of the actual witness inside the displayed rounding cell.
    start, end = witness
    low = max(Q(0), *[(Q(-1, 2)-start[k])/(end[k]-start[k]) for k in (0, 1) if start[k] < Q(-1, 2)])
    shown = [tuple(start[k]+low*(end[k]-start[k]) for k in (0, 1)), end]
    assert 0 <= low < 1 and all(Q(-1, 2) <= v <= Q(1, 2) for q in shown for v in q)
    ax.add_patch(Rectangle((-.5, -.5), 1, 1, facecolor='#E7F0F5', edgecolor='#7D99A8', ls='--'))
    ax.plot(*zip(*[tuple(float(v) for v in q) for q in shown]), color='#3D8A72', lw=3, label='Trajectoire 170699 (extrait)')
    ax.plot(*zip(*[tuple(float(v) for v in q) for q in cut]), color='#C78635', lw=5, label='Coupe rationnelle 170703')
    ax.scatter([0], [0], s=65, color='#192C3B', zorder=5, label='P : encodage des deux bouts')
    ax.annotate('Deux bouts exacts distincts\n→ même point machine P', xy=(float(cut[1][0]), 0), xytext=(-.48, .32),
        fontsize=10, arrowprops={'arrowstyle': '->', 'color': '#637E8D'})
    ax.set(xlim=(-.6, .6), ylim=(-.6, .6), xlabel='(X − Pₓ) / ULP(X)', ylabel='(Y − Pᵧ) / ULP(Y)')
    ax.set_aspect('equal');ax.grid(color='#E5EDF2', lw=.6)
    fig.legend(*ax.get_legend_handles_labels(), loc='lower left', bbox_to_anchor=(.065, .095),
        ncol=3, frameon=False, fontsize=9)
    card = fig.add_axes([.52, .18, .42, .30]);card.axis('off')
    card.text(0, 1, 'La coupe exacte reste conservée', fontsize=18, weight='bold', va='top')
    card.text(0, .80, 'Seule la primitive machine P → P peut être omise.\nP appartient exactement à une trajectoire non nulle\ndu même owner, au même Z et dans le même NPZ.', va='top', color='#506C7D', linespacing=1.6)
    card.text(0, .48, '1 ULP en X = '+f'{float(ulp[0]):.6g}'.replace('.', ',')+' mm\nCellule affichée : ± ½ ULP sur chaque axe.\nLes axes X et Y utilisent chacun leur propre ULP.', va='top', fontsize=10, color='#506C7D', linespacing=1.6)
    card.text(0, .15, 'Prochaine étape : les 17 384 cas de la zone 000.\nContacts et graphes d’exposition restent à recalculer.', va='top', fontsize=10, color='#9B493C', linespacing=1.6)
    fig.text(.06, .035, '703 / 703 témoins · 460 440 coupes rationnelles · 459 737 vecteurs non nuls · original c351989c…\n'
        'Périmètre : peau 13 uniquement. Aucun résultat global d’impression. Coordonnées exactes et reçus joints ; image explicative.', fontsize=9, color='#647A88', linespacing=1.6)
    fig.canvas.draw();output.mkdir()
    for extension in ('png', 'svg', 'pdf'):
        metadata = {'Date': None} if extension == 'svg' else ({'CreationDate': None, 'ModDate': None} if extension == 'pdf' else {})
        fig.savefig(output/f'carrier-703-points-couverts.{extension}', dpi=160, facecolor=fig.get_facecolor(), metadata=metadata)
    receipt = {'scope': inputs['scope'], 'inputs_sha256': inputs['files_sha256'], 'renderer_sha256': sha(__file__),
        'actual_layers': len(rows), 'actual_covered_points': 703, 'selected_layer': 118,
        'selected_face': 170703, 'witness_face': proof['nonzero_same_owner_witness']['face_id'],
        'ULP_mm_exact': [str(v) for v in ulp], 'selected_cut_in_ULP_exact': [[str(v) for v in q] for q in cut],
        'shown_witness_in_ULP_exact': [[str(v) for v in q] for q in shown],
        'global_admission': False, 'matplotlib': matplotlib.__version__,
        'exports_sha256': {f.name: sha(f) for f in output.iterdir()}}
    (output/'render-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    plt.close(fig);signal.alarm(0)
    print(json.dumps({'status': 'rendered_actual_owner13_only', 'output': str(output)}))


if __name__ == '__main__':
    main()
