"""Render audited native residuals, static pressure history and saved cell-centre speed."""
import argparse
import json
from pathlib import Path
import re

from analyze_restart import flow, history
from prepare_restart import sha, verify


def render(case, audit, output):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    if output.exists():
        raise ValueError('Figure output must be new')
    report = json.loads((audit / 'flow-report.json').read_text())
    saved = case / str(int(report['saved_iteration']))
    verify(saved, report['final_field_hashes'])
    verify(case, report['history_hashes'])
    if sha(audit / 'residual-history.json') != report['residual_history_sha256']:
        raise ValueError('Residual history changed')
    traces = json.loads((audit / 'residual-history.json').read_text())
    # Native writeCellCentres supplies the same cell order as the reconstructed U.
    if not re.search(r'dimensions\s*\[0\s+1\s+0\s+0\s+0\s+0\s+0\]', (saved / 'C').read_text()):
        raise ValueError('Expected native cell centres in metres')
    centres = np.asarray(flow.benchmark.read_vector_field(saved / 'C', report['cells'])) * 1000
    u = np.asarray(flow.benchmark.read_vector_field(saved / 'U', report['cells']))
    if centres.shape != (report['cells'], 3) or u.shape != centres.shape or not np.isfinite(centres).all():
        raise ValueError('Invalid native cell-centre frame')
    pin = history(case, 'inletPressure')[1]; pout = history(case, 'outletPressure')[1]
    times = sorted(pin)
    dp = [(pin[t] - pout[t]) * report['density_kg_m3'] / 1000 for t in times]
    fig = plt.figure(figsize=(17, 6), layout='constrained')
    residual = fig.add_subplot(131)
    for name in ('Ux', 'Uy', 'Uz', 'p', 'omega', 'k'):
        residual.semilogy([r['iteration'] for r in traces],
                         [r['initial_residuals'][name] for r in traces], label=name)
    residual.axhline(report['residual_target'], color='black', linestyle='--', label='Target')
    residual.set(xlabel='SIMPLE iteration (not seconds)', ylabel='First-solve initial residual',
                 title='Global convergence'); residual.legend(fontsize=8); residual.grid(alpha=.2)
    pressure = fig.add_subplot(132); pressure.plot(times, dp, color='#2679a9')
    pressure.axvline(report['saved_iteration'], color='black', linestyle='--', label='Saved fields')
    pressure.set(xlabel='SIMPLE iteration (not seconds)', ylabel='Static pressure difference (kPa)',
                 title='Native area-average inlet minus outlet'); pressure.grid(alpha=.2)
    pressure.legend(fontsize=8)
    spatial = fig.add_subplot(133, projection='3d')
    selected = np.arange(0, len(u), max(1, int(np.ceil(len(u) / 20000))))
    speed = np.linalg.norm(u, axis=1)
    cloud = spatial.scatter(*centres[selected].T, c=speed[selected], cmap='viridis', s=1,
                            vmin=0, vmax=float(speed.max()), rasterized=True)
    spatial.set(xlabel='X (mm)', ylabel='Y (mm)', zlabel='Z (mm)',
                title=f"Water-domain cell centres — saved iteration {report['saved_iteration']:g}")
    spatial.set_box_aspect(np.ptp(centres, axis=0)); spatial.view_init(elev=30, azim=-60)
    fig.colorbar(cloud, ax=spatial, shrink=.6, label='Speed (m/s)')
    state = 'Numerical screen passed' if report['numerical_flow_screen_passed'] else 'Unconverged / screen rejected'
    fig.suptitle(f'4 L head water study — {state}\nFirst-order isothermal RANS; no thermal or physical qualification', fontsize=14)
    fig.savefig(output, dpi=150); plt.close(fig)
    with Image.open(output) as picture: picture.verify()
    return dict(image_sha256=sha(output), source_sha256=sha(Path(__file__)),
        flow_report_sha256=sha(audit / 'flow-report.json'),
        residual_history_sha256=sha(audit / 'residual-history.json'),
        native_centres_sha256=sha(saved / 'C'), sampled_cells=len(selected),
        total_cells=report['cells'], manufacturing_authorized=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('case', 'audit', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(render(*(p.resolve() for p in (args.case, args.audit, args.output))), indent=2))
