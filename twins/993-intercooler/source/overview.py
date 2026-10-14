#!/usr/bin/env python3
"""Overview figure of the 750 hp core routes; plots retained screen results only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HUB = Path(__file__).resolve().parents[1]
STUDY = HUB/'750-hp'


def run(output):
    if output.exists(): raise FileExistsError(output)
    a = json.loads((STUDY/'requirements.json').read_text())['assumed']
    screen = json.loads((STUDY/'core-comparison/results/screen.json').read_text())
    passes = json.loads((STUDY/'counterflow-passes/results/passes.json').read_text())
    with (STUDY/'core-comparison/results/screen-sweep.csv').open() as stream:
        gyroid = [r for r in csv.DictReader(stream) if r['family'] == 'gyroid' and float(r['max_hot_dp_pa']) <= a['charge_pressure_loss_budget_pa'] and float(r['max_cold_dp_pa']) <= a['ambient_pressure_loss_budget_pa']]
    g = min(gyroid, key=lambda r: float(r['max_charge_outlet_c'])); helix = screen['helical_closest_in_domain'][0]
    witness = screen['witness_offset_strip']; ext = passes['extended_search']['lightest_by_passes']; light = screen['gyroid_break_even_lighter_than_witness']
    points = [
        ('Offset strip, retained witness', witness['mass_kg'], max(c['charge_outlet_c'] for c in witness['replayed_stress_cases']), 'D', '#222222', 'screen pass'),
        ('Offset strip, wider charge gap', ext['1']['mass_kg'], ext['1']['max_charge_outlet_c'], 'o', '#4c72b0', 'screen pass, thin margin'),
        ('Offset strip, 2 counterflow passes', ext['2']['mass_kg'], ext['2']['max_charge_outlet_c'], 's', '#dd8452', 'screen pass, heavier'),
        ('HelixHeatX helical tube bank', helix['mass_kg'], helix['max_charge_outlet_c'], '^', '#c44e52', 'rejected'),
        ('Gyroid, plain-duct analogue', float(g['mass_kg']), float(g['max_charge_outlet_c']), 'v', '#55a868', 'analogue only'),
    ]
    fig, ax = plt.subplots(figsize=(10, 6))
    for label, mass, outlet, marker, color, verdict in points:
        ax.scatter(mass, outlet, s=110, marker=marker, color=color, edgecolor='k', zorder=4, label=f'{label}: {mass:.1f} kg, {outlet:.1f} °C ({verdict})')
    ax.axvline(light['mass_kg'], color='#55a868', ls='--', lw=1)
    ax.annotate(f"gyroid {light['mass_kg']:.1f} kg would pass\nonly if bench Nu ≥ {light['required_equal_nusselt']:.1f}, f·Re ≤ 64",
                (light['mass_kg'], 75), xytext=(10, 0), textcoords='offset points', fontsize=8, color='#2e6b3d')
    ax.axhline(a['charge_outlet_target_c'], color='k', ls=':', lw=1); ax.text(1, a['charge_outlet_target_c']+1.5, 'charge outlet target', fontsize=8)
    ax.set(xlabel='core metal mass, headers excluded (kg)', ylabel='worst charge outlet over the three stress cases (°C)', xlim=(0, 40), ylim=(40, 145),
           title='750 hp intercooler: best candidate of each route within both pressure budgets')
    ax.legend(loc='upper right', fontsize=8); ax.grid(alpha=.3)
    output.mkdir(parents=True); fig.tight_layout(); fig.savefig(output/'overview.png', dpi=130); plt.close(fig)
    sources = [Path(__file__), STUDY/'core-comparison/results/screen.json', STUDY/'core-comparison/results/screen-sweep.csv', STUDY/'counterflow-passes/results/passes.json']
    (output/'overview.json').write_text(json.dumps({'status': 'review_figure_not_evidence', 'points': [p[:3] for p in points],
                                                     'source_sha256': {str(p.relative_to(HUB)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}, indent=2)+'\n', newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True, type=Path); run(p.parse_args().output)
