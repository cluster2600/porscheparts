"""Plot archived numerical histories; never interpret convergence as validation."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1] / 'results/organic'
fig, axes = plt.subplots(2, 2, figsize=(13, 9), layout='constrained')
for ax, cases, title in [
    (axes[0, 0], ['reference-fine', 'a-fine'], 'Level 4 surface refinement'),
    (axes[0, 1], ['reference-coarse', 'c-coarse', 'd-coarse', 'e-coarse'], 'Level 3 surface refinement'),
]:
    for case in cases:
        data = np.loadtxt(root/'flow'/case/'outlet.dat')
        assert data.ndim == 2 and len(data) >= 200 and np.isfinite(data).all()
        ax.plot(data[:, 0], data[:, 1], label=case.replace('-fine', '').replace('-coarse', ''))
    ax.set(title=title, xlabel='Solver iteration (not physical time)', ylabel='Outlet flow (m³/s)')
    ax.legend(); ax.grid(alpha=.2)

names = ['a', 'b', 'c', 'd', 'e']
volumes = [json.loads((root/v/'print/flat-slicing.json').read_text())['support_proxy_volume_cm3'] for v in names]
axes[1, 0].bar([v.upper() for v in names], volumes, color='#376c9e')
reference = json.loads((root.parent/'print-release/flat-slicing.json').read_text())
axes[1, 0].axhline(reference['support_proxy_volume_cm3'], color='black', linestyle='--', label='Reference')
axes[1, 0].set(title='Flat build support proxy — 50 µm layers', ylabel='Vertical-column proxy (cm³)', xlabel='Organic candidate')
axes[1, 0].legend()
for v in ['a', 'c', 'e']:
    data = json.loads((root/v/'thermal-15/history.json').read_text())
    axes[1, 1].plot([r['elapsed_s']/3600 for r in data],
                    [r['max_active_temperature_k']-273.15 for r in data], label=v.upper())
axes[1, 1].set(title='Homogenised thermal screen — 1.5 mm grid', xlabel='Assumed build schedule (hours)', ylabel='Maximum active bulk temperature (°C)')
axes[1, 1].legend(); axes[1, 1].grid(alpha=.2)
fig.suptitle('Organic fan trials — unvalidated numerical experiments\nNo installed airflow, material qualification or print authorization', fontsize=15)
fig.savefig(root/'study-results.png', dpi=160)
