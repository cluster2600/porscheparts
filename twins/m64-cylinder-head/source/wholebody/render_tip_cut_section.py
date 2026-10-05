#!/usr/bin/env python3
"""Actual native-CAD section of the first bounded cut; not a product render."""
import argparse
import json
from pathlib import Path
import signal

import numpy as np
from audit_pinched_junction import section_edges
from trial_bounded_tip_cut import read_native, BODY_SHA, native


def run(args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    record = args.candidate/'report.json'; candidate = args.candidate/'candidate-private.brep'
    receipt = json.loads(record.read_text())
    if (args.output.exists() or args.output.is_symlink() or native.sha256(args.body) != BODY_SHA
            or receipt.get('source_face') != 1648 or receipt.get('radius_scan_units') != .02
            or receipt.get('candidate_sha256') != native.sha256(candidate)
            or receipt.get('inputs_unchanged') is not True):
        raise ValueError('fresh_image_and_first_cut_evidence_required')
    pins = {p: native.sha256(p) for p in (args.body, candidate, record, Path(__file__))}
    centre = np.asarray(receipt['centre_private'])
    curves = [(section_edges(read_native(p), centre), color, label)
              for p, color, label in ((args.body, '#176b91', 'Original CAD'),
                                      (candidate, '#cb582d', 'Experimental cut'))]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor='#f7f9fb')
    for ax, span in zip(axes, (.15, .025)):
        for lines, color, label in curves:
            for i, line in enumerate(lines):
                xy = line[:, [0, 2]]-centre[[0, 2]]
                ax.plot(xy[:, 0], xy[:, 1], color=color, lw=1.5,
                        linestyle='-' if label == 'Original CAD' else '--', label=label if i == 0 else None)
        ax.set(xlim=(-span, span), ylim=(-span, span), aspect='equal',
               xlabel='Relative X — scan units', ylabel='Relative Z — scan units')
        ax.grid(alpha=.2); ax.legend(loc='lower right', fontsize=9)
    axes[0].set_title('Native section through the diagnosed tip')
    axes[1].set_title('Cut radius 0.020 — equal axis scale')
    fig.suptitle('M64 meshing research | local CAD experiment, NOT an accepted head', fontsize=13)
    fig.text(.5, .015, 'Native section curves, sampled at 0.0002 scan units. Scale, fitment, mesh and printing are not validated.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .055, 1, .94))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160); plt.close(fig)
    if any(native.sha256(p) != h for p, h in pins.items()): raise ValueError('source_changed')
    native.save(args.output.with_suffix('.json'), dict(schema='m64-tip-cut-section/v1',
        source_hashes={p.name: h for p, h in pins.items()}, image_sha256=native.sha256(args.output),
        inputs_unchanged=True, manufacturing_authorized=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('body', 'candidate', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    signal.alarm(120); run(parser.parse_args())
