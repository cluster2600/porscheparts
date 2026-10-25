"""Plot complete-cell diagnostics; mesh quality is not mechanical convergence."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    reports = [json.loads(path.read_text()) for path in [a.reference, a.candidate]]
    assert all(row['status'] == 'all_cell_quality_diagnostics_completed' for row in reports)
    assert not a.output.exists()
    a.output.mkdir(parents=True)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    for ax, (key, extreme, title) in zip(axes, [
        ('mean_ratio', 'minimum', 'Minimum mean ratio · higher is better'),
        ('Jacobian_condition_2norm', 'maximum', 'Maximum local condition · lower is better'),
        ('minimum_altitude_mm', 'minimum', 'Minimum element altitude [mm]')]):
        values = [row['metrics'][key][extreme] for row in reports]
        ax.bar(['Original T4', 'Extracted Netgen'], values, color=['#819991', '#0783aa'])
        ax.set_title(title, fontsize=10)
        ax.bar_label(ax.containers[0], labels=[f'{x:.5g}' for x in values], padding=4)
        ax.set_ylim(0, max(values)*1.2)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('993 R2 / BOUNDARY-PRESERVING VOLUME REMESH', fontweight='bold')
    fig.supxlabel('343,283 → 381,564 cells · complete exact orientation/connectivity pass\nOriginal exterior retained. No new FEA result; element altitude is not wall thickness.', fontsize=10)
    target = a.output/'carrier-volume-remesh-quality.png'
    fig.savefig(target, dpi=160)
    plt.close(fig)
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    (a.output/'figure-provenance.json').write_text(json.dumps(dict(
        source_sha256={str(path):sha(path) for path in [a.reference, a.candidate, Path(__file__)]},
        figure_sha256=sha(target)), indent=2)+'\n')


if __name__ == '__main__':
    main()
