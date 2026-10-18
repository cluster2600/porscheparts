"""Render every recorded FEA energy state; no solver or numerical audit is run."""
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
from fractions import Fraction

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sci_fr(value):
    mantissa, exponent = f'{value:.3e}'.split('e')
    superscript = str(int(exponent)).translate(str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'))
    return mantissa.replace('.', ',') + ' × 10' + superscript


def validate(data):
    comparison = data['comparison.json']
    if comparison['status'] != 'comparison_completed_all_refined_numeric_checks_pass':
        raise ValueError('Completed comparison with passing refined checks required')
    if comparison['thresholds'] != {'ENER': 0.001, 'Piola': 0.0001}:
        raise ValueError('Frozen thresholds changed')
    if comparison['unloaded_residual']['acceptance_threshold'] is not None:
        raise ValueError('No residual acceptance threshold is defined')
    for n in [16, 32]:
        ener, piola = data[f'ener-{n}.json'], data[f'piola-{n}.json']
        ef, pf = ener['frames'], piola['frames']
        times = [Fraction(i, n // 2) for i in range(1, n + 1)]
        for frames in [ef, pf]:
            if [Fraction(f['total_time']) for f in frames] != times:
                raise ValueError('Every recorded state in time order is required')
            if any(Fraction(f['load_factor']) != (t if t <= 1 else 2 - t)
                   for f, t in zip(frames, times)):
                raise ValueError('Load/unload factors differ')
        if ener['work_relative_tolerance'] != 0.001 or piola['relative_work_tolerance'] != 0.0001:
            raise ValueError('Audit thresholds differ')
        for frames, field, tag in [(ef, 'work_relative_to_gross_error', 'ENER'),
                                   (pf, 'relative_to_gross_work', 'Piola')]:
            values = [f[field] for f in frames]
            if any(not math.isfinite(v) or v <= 0 for v in values):
                raise ValueError('Positive finite values required for logarithmic axes')
            key = 'baseline' if n == 16 else 'refined'
            if max(values) != comparison[f'worst_{tag}_relative_to_gross'][key]:
                raise ValueError('Maximum differs from independent comparison')
        if ener['runtime_sha256'] != sha(HERE / 'data' / f'runtime-{n}.json'):
            raise ValueError('Audit/runtime identity differs')
        if piola['runtime_sha256'] != ener['runtime_sha256']:
            raise ValueError('Auditors used different solver runtime receipts')
        if ef[-1]['displacement_max_mm'] != comparison['unloaded_residual']['displacement_max_mm'][
                'baseline' if n == 16 else 'refined']:
            raise ValueError('Residual differs')
    return data


def load():
    manifest = json.loads((HERE / 'inputs.json').read_text())
    data = {}
    for name, row in manifest['files'].items():
        p = HERE / 'data' / name
        if sha(p) != row['sha256']:
            raise ValueError('Copied source evidence changed: ' + name)
        data[name] = json.loads(p.read_text())
    return manifest, validate(data)


def main():
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('60 s render budget')))
    signal.setitimer(signal.ITIMER_REAL, 60)
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
        os.environ[name] = '1'
    os.environ['MPLBACKEND'] = 'Agg'
    output = Path(sys.argv[1]).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Use a fresh output folder')
    manifest, data = load()
    pins = {str(HERE / 'inputs.json'): sha(HERE / 'inputs.json'), str(Path(__file__)): sha(__file__)}
    pins.update({str(HERE / 'data' / n): r['sha256'] for n, r in manifest['files'].items()})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.backends.backend_agg
    import matplotlib.backends.backend_pdf
    import matplotlib.backends.backend_svg
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FixedLocator, FuncFormatter, LogFormatterMathtext
    import numpy as np
    import PIL
    versions = {'python': sys.version.split()[0], 'matplotlib': matplotlib.__version__,
                'numpy': np.__version__, 'Pillow': PIL.__version__}
    if versions != manifest['renderer_runtime_versions']:
        raise ValueError('Use the pinned rendering package versions')
    font = font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'), fallback_to_default=False)
    runtime_paths = {str(Path(sys.executable).resolve()), font}
    runtime_paths.update(str(Path(m.__file__).resolve()) for name, m in list(sys.modules.items())
                         if name.split('.')[0] in ['matplotlib', 'numpy', 'PIL']
                         and getattr(m, '__file__', None) and Path(m.__file__).is_file())
    runtime_hashes = {p: sha(p) for p in sorted(runtime_paths)}
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
        'axes.titlesize': 15, 'axes.labelsize': 11, 'axes.edgecolor': '#B6C3CE',
        'text.color': '#192C3B', 'axes.labelcolor': '#334D5E',
        'xtick.color': '#334D5E', 'ytick.color': '#334D5E',
        'svg.fonttype': 'none', 'svg.hashsalt': 'carrier-ener-increments-001',
        'pdf.fonttype': 42, 'path.simplify': False})
    fig = plt.figure(figsize=(15.2, 10.8), facecolor='#FAFCFE')
    fig.text(0.075, 0.952, 'BILANS NUMÉRIQUES · CARRIER · Ti Grade 23 ELI',
             fontsize=11, weight='bold', color='#506C7D')
    fig.text(0.075, 0.914, 'Incréments divisés par deux : deux contrôles, deux évolutions',
             fontsize=21, weight='bold')
    fig.text(0.075, 0.880, 'Même maillage, loi, appuis et charges · cycle quasi statique en charge puis décharge',
             fontsize=12, color='#506C7D')
    handles = [Line2D([], [], color='#C87520', marker='D', markersize=5, markerfacecolor='white',
                      ls='--', label='16 états · Δt = 1/8'),
               Line2D([], [], color='#086C99', marker='o', markersize=4, lw=2,
                      label='32 états · Δt = 1/16'),
               Line2D([], [], color='#B44942', ls=(0, (5, 3)), lw=1.5,
                      label='Seuil fixé avant le raffinement')]
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.068, 0.865),
               frameon=False, ncol=3, fontsize=11, columnspacing=2.1)
    comparison = data['comparison.json']
    specs = [('ENER', 'work_relative_to_gross_error', [0.075, 0.535, 0.87, 0.235],
              (4e-7, 3e-3), 'ENER — le maximum diminue et passe le seuil',
              comparison['worst_ENER_relative_to_gross']),
             ('Piola', 'relative_to_gross_work', [0.075, 0.218, 0.87, 0.235],
              (3e-9, 2.2e-4), 'Piola — le maximum augmente, sous le seuil',
              comparison['worst_Piola_relative_to_gross'])]
    plotted = {}
    for metric, field, bounds, ylim, title, maximum in specs:
        ax = fig.add_axes(bounds, facecolor='white')
        ax.axvspan(0, 1, color='#E9F1F7', zorder=0)
        ax.axvspan(1, 2, color='#F3F0E8', zorder=0)
        ax.axvline(1, color='#90A2AD', lw=1)
        ax.set_title(title, loc='left', y=1.19, pad=0, weight='bold')
        subtitle = f'Maximum : {sci_fr(maximum["baseline"])}  →  {sci_fr(maximum["refined"])}'
        ax.text(0, 1.075, subtitle, transform=ax.transAxes, fontsize=11, color='#506C7D')
        ax.text(0.25, 1.015, 'CHARGE  0 → 1', transform=ax.transAxes, ha='center', va='bottom',
                fontsize=9, color='#657A88')
        ax.text(0.75, 1.015, 'DÉCHARGE  1 → 0', transform=ax.transAxes, ha='center', va='bottom',
                fontsize=9, color='#786F58')
        for n, color, marker, line in [(16, '#C87520', 'D', '--'), (32, '#086C99', 'o', '-')]:
            frames = data[f'{"ener" if metric == "ENER" else "piola"}-{n}.json']['frames']
            xs, ys = [f['total_time'] for f in frames], [f[field] for f in frames]
            ax.plot(xs, ys, color=color, ls=line, marker=marker,
                    markerfacecolor='white' if n == 16 else color, markersize=4.5 if n == 16 else 3.8,
                    markeredgewidth=1.0, lw=1.5 if n == 16 else 1.9, zorder=3)
            plotted[f'{metric}_{n}'] = {'points': len(xs), 'time': xs, 'values': ys}
            peak = max(range(len(ys)), key=ys.__getitem__)
            ax.scatter([xs[peak]], [ys[peak]], s=95, facecolors='none', edgecolors=color, lw=1.2, zorder=5)
        limit = comparison['thresholds'][metric]
        ax.axhline(limit, color='#B44942', ls=(0, (5, 3)), lw=1.5, zorder=2)
        ax.text(2.018, limit, '10⁻³' if metric == 'ENER' else '10⁻⁴',
                color='#A13B36', fontsize=11, va='center')
        ax.set_xlim(0, 2)
        ax.set_yscale('log')
        ax.set_ylim(*ylim)
        ax.yaxis.set_major_formatter(LogFormatterMathtext())
        ax.xaxis.set_major_locator(FixedLocator([0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:g}'.replace('.', ',')))
        ax.grid(axis='y', which='major', color='#CFDAE2', lw=0.6)
        ax.spines[['top', 'right']].set_visible(False)
        ax.set_ylabel('Écart relatif au\ntravail externe brut')
        if metric == 'Piola':
            ax.set_xlabel('Temps normalisé du cycle, t  ·  charge maximale à t = 1 ; charge nulle à t = 2', labelpad=9)
        else:
            ax.tick_params(axis='x', labelbottom=False)
    box = dict(boxstyle='round,pad=0.75', facecolor='#EEF3F6', edgecolor='#DCE5EA')
    residual = comparison['unloaded_residual']['displacement_max_mm']
    dec = lambda value: f'{value:.8f}'.replace('.', ',').replace('-', '−')
    fig.text(0.087, 0.104,
             'RÉSIDU À CHARGE NULLE · t = 2\n'
             f'max |u| : {dec(residual["baseline"])} mm (16)  →  {dec(residual["refined"])} mm (32)\n'
             f'Différence : {dec(residual["difference"])} mm · aucun seuil d’acceptation défini',
             fontsize=11, linespacing=1.55, bbox=box)
    fig.text(0.64, 0.115,
             '48 états par bilan, tous représentés.\nÉchelles verticales logarithmiques.\n'
             'Points enregistrés ; traits pour guider la lecture.',
             fontsize=10, color='#506C7D', linespacing=1.55)
    fig.text(0.075, 0.029,
             'Raffinement des incréments uniquement ; aucune convergence en maillage démontrée.\n'
             'CalculiX · audits indépendants ENER et Piola · comparaison SHA-256 31a9b7a7c78c… · sources et empreintes jointes.',
             fontsize=9, color='#506C7D', linespacing=1.5)
    output.mkdir()
    stem = 'carrier-bilans-numeriques-16-32-etats'
    fig.savefig(output / (stem + '.png'), dpi=200, metadata={'Software': 'Frozen carrier energy renderer'})
    fig.savefig(output / (stem + '.svg'), metadata={'Date': None, 'Creator': 'Frozen carrier energy renderer'})
    fig.savefig(output / (stem + '.pdf'), metadata={'CreationDate': None, 'ModDate': None,
                'Creator': 'Frozen carrier energy renderer', 'Title': 'Bilans numériques carrier — 16 et 32 états'})
    plt.close(fig)
    if any(sha(p) != h for p, h in pins.items()) or any(sha(p) != h for p, h in runtime_hashes.items()):
        raise ValueError('Source, input or rendering runtime changed')
    receipt = {'schema': 'ener-increment-figure-render-1', 'status': 'rendered_all_recorded_states',
        'source_and_copied_evidence_sha256': pins, 'render_runtime_versions': versions,
        'render_runtime_files_sha256': runtime_hashes, 'inputs_runtime_unchanged': True,
        'comparison_sha256': sha(HERE / 'data/comparison.json'), 'plotted_series': plotted,
        'ENER_threshold': 0.001, 'Piola_threshold': 0.0001, 'residual_acceptance_threshold': None,
        'axis': 'logarithmic, no omitted state and no invented time-zero state',
        'worker_processes': 0, 'wall_seconds': time.monotonic() - start,
        'global_admission': False, 'mesh_convergence_claimed': False, 'physical_test_claimed': False,
        'outputs_sha256': {p.name: sha(p) for p in output.iterdir() if p.is_file()}}
    (output / 'render-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps({'status': receipt['status'], 'wall_seconds': receipt['wall_seconds'],
                      'receipt_sha256': sha(output / 'render-receipt.json')}))


if __name__ == '__main__':
    main()
