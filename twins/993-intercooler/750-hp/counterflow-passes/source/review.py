#!/usr/bin/env python3
"""Review figures of the multi-pass screen; plots retained results only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[1]
STUDY = HERE.parent
COLORS = {1: '#4c72b0', 2: '#dd8452', 3: '#55a868', 4: '#c44e52'}


def run(output):
    if (output/'figures.json').exists(): raise FileExistsError(output/'figures.json')
    output.mkdir(parents=True, exist_ok=True)
    card = json.loads((STUDY/'requirements.json').read_text())['assumed']
    r = json.loads((HERE/'results/passes.json').read_text()); split = r['witness_fins_split_into_passes']
    passes = [s['geometry']['charge_passes'] for s in split]

    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6))
    left.plot(passes, [s['high_case']['charge_outlet_c'] for s in split], 'o-', label='pass formula')
    left.plot(passes, [s['high_grid']['charge_outlet_c'] for s in split], 's--', label='grid, air unmixed')
    left.axhline(card['charge_outlet_target_c'], color='k', lw=1, ls=':', label='target')
    left.set(xlabel='charge passes against the cooling air', ylabel='charge outlet, high stress case (°C)', xticks=passes,
             title='Witness fins: counterflow lowers the outlet')
    left.legend(); left.grid(alpha=.3)
    right.semilogy(passes, [s['max_hot_dp_pa']/1000 for s in split], 'o-', color='#c44e52')
    right.axhline(card['charge_pressure_loss_budget_pa']/1000, color='k', lw=1, ls=':', label='charge budget')
    right.set(xlabel='charge passes against the cooling air', ylabel='charge pressure loss, worst case (kPa)', xticks=passes,
              title='...but the charge loss grows as about N^2.6 to N^2.7')
    right.legend(); right.grid(alpha=.3, which='both')
    fig.suptitle('Same 17.3 kg offset-strip core, charge split into N passes (stress factors applied)')
    fig.tight_layout(); fig.savefig(output/'witness-passes.png', dpi=130); plt.close(fig)

    with (HERE/'results/passes-sweep.csv').open() as stream: rows = list(csv.DictReader(stream))
    ok = [x for x in rows if x['all_regimes_admissible'] == 'True' and float(x['max_hot_dp_pa']) <= card['charge_pressure_loss_budget_pa']
          and float(x['max_cold_dp_pa']) <= card['ambient_pressure_loss_budget_pa'] and float(x['max_charge_outlet_c']) <= 90]
    fig, ax = plt.subplots(figsize=(10, 6))
    for p in sorted({int(x['charge_passes']) for x in ok}):
        sub = [x for x in ok if int(x['charge_passes']) == p]
        ax.scatter([float(x['mass_kg']) for x in sub], [float(x['max_charge_outlet_c']) for x in sub], s=9, alpha=.55, color=COLORS[p], label=f'{p} pass{"es" if p > 1 else ""} ({len(sub)})')
    for p, best in r['extended_search']['lightest_by_passes'].items():
        ax.scatter(best['mass_kg'], best['max_charge_outlet_c'], s=140, marker='*', color=COLORS[int(p)], edgecolor='k', zorder=5)
        ax.annotate(f"{p}-pass lightest\n{best['mass_kg']:.2f} kg", (best['mass_kg'], best['max_charge_outlet_c']), textcoords='offset points', xytext=(-100, 14) if p == '1' else (14, 6), fontsize=8, arrowprops={'arrowstyle': '-', 'lw': .6})
    ax.scatter(r['witness_mass_kg'], split[0]['max_charge_outlet_c'], s=120, marker='D', facecolor='none', edgecolor='k', zorder=6, label='retained witness')
    ax.axhline(card['charge_outlet_target_c'], color='k', lw=1, ls=':')
    ax.set(xlabel='core metal mass, headers excluded (kg)', ylabel='worst charge outlet over the three stress cases (°C)', xlim=(8, 33),
           title='In-domain candidates within both pressure budgets (extended search)')
    ax.legend(loc='upper right'); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(output/'mass-outlet.png', dpi=130); plt.close(fig)

    sources = [Path(__file__), HERE/'results/passes.json', HERE/'results/passes-sweep.csv']
    (output/'figures.json').write_text(json.dumps({'status': 'review_figures_not_evidence', 'figures': ['witness-passes.png', 'mass-outlet.png'],
                                                    'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}, indent=2)+'\n', newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True, type=Path); run(p.parse_args().output)
