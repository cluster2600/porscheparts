#!/usr/bin/env python3
"""Actual local mesh comparison; no smoothing, generative image or CAD release."""
import argparse
import json
from pathlib import Path
import signal

import numpy as np
from run_parallel_cad_trials import BODY_SHA, native


def run(args):
    import gmsh
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    paths = [args.rejected_mesh, args.rejected_receipt, args.candidate_mesh, args.candidate_receipt, Path(__file__)]
    pins = {p: native.sha256(p) for p in paths}
    if args.output.exists() or any(p.is_symlink() for p in paths): raise ValueError('fresh_output_and_regular_inputs_required')
    for mesh, receipt in ((args.rejected_mesh, args.rejected_receipt), (args.candidate_mesh, args.candidate_receipt)):
        r = json.loads(receipt.read_text())
        if (r.get('surface_sha256') != pins[mesh] or r.get('input_sha256') != BODY_SHA
                or r.get('status') != 'completed_diagnostic_only' or r.get('inputs_unchanged') is not True):
            raise ValueError('bound_diagnostic_surface_required')
    views = []; focus = basis = chosen = None
    gmsh.initialize(['boundary-comparison', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    try:
        for path in (args.rejected_mesh, args.candidate_mesh):
            gmsh.clear(); gmsh.open(str(path))
            nt, xyz, _ = gmsh.model.mesh.getNodes(); order = np.argsort(nt)
            nt, xyz = nt[order], np.asarray(xyz).reshape(-1, 3)[order]
            if chosen is None:
                worst = 1.
                for _, tag in gmsh.model.getEntities(2):
                    t, e, _ = gmsh.model.mesh.getElements(2, tag)
                    if not len(t): continue
                    q = np.asarray(gmsh.model.mesh.getElementQualities(e[0], 'minSICN'))
                    if q.min() < worst: worst, chosen = float(q.min()), tag
                if worst >= 2*.1/(3-.1): raise ValueError('rejected_surface_witness_required')
            t, e, n = gmsh.model.mesh.getElements(2, chosen)
            if list(t) != [2]: raise ValueError('same_linear_face_required')
            indices = np.searchsorted(nt, n[0])
            if indices.max() >= len(nt) or not np.array_equal(nt[indices], n[0]): raise ValueError('node_binding_required')
            tri = xyz[indices.reshape(-1, 3)]
            q = np.asarray(gmsh.model.mesh.getElementQualities(e[0], 'minSICN'))
            if focus is None:
                first = tri[int(np.argmin(q))]; focus = first.mean(0)
                _, _, basis = np.linalg.svd(first-focus); basis = basis[:2]
            selected = np.any(np.linalg.norm(tri-focus, axis=2) <= .8, axis=1)
            views.append(((tri[selected]-focus)@basis.T, q[selected]))
    finally: gmsh.finalize()
    args.output.mkdir(mode=0o700)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True, sharey=True)
    for ax, (tri, q), title in zip(axes, views, ('Rejected: every boundary split', 'Candidate: exact straight boundary retained')):
        bad = q < 2*.1/(3-.1)
        colours = np.where(bad, '#e26049', '#cedce2')
        ax.add_collection(PolyCollection(tri, facecolors=colours, edgecolors='#294858', linewidths=.8))
        ax.set(xlim=(-.8, .8), ylim=(-.5, .5), aspect='equal', xlabel='Local coordinate — scan units',
               title=f'{title}\nLocal minimum q2: {q.min():.6f}; rejected: {bad.sum()}')
        ax.grid(alpha=.2)
    axes[0].set_ylabel('Local coordinate — scan units')
    fig.suptitle('M64 research mesh | shared-boundary subdivision control')
    fig.text(.5, .025, 'Actual same-face triangles; original CAD unchanged. Not millimetres, CFD or manufacturing approval.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0,.055,1,.93))
    image = args.output/'comparison.png'; fig.savefig(image, dpi=160); plt.close(fig)
    if any(native.sha256(p) != h for p, h in pins.items()): raise ValueError('input_changed')
    native.save(args.output/'report.json', dict(schema='m64-boundary-refinement-render/v1',
        input_hashes={str(p): h for p, h in pins.items()}, selected_face_private=int(chosen),
        image_sha256=native.sha256(image), inputs_unchanged=True, generative_image=False,
        geometry_modified=False, manufacturing_authorized=False))
    print(image)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('rejected-mesh', 'rejected-receipt', 'candidate-mesh', 'candidate-receipt', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    signal.alarm(120); run(parser.parse_args())
