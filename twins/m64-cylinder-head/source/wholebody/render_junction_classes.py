#!/usr/bin/env python3
"""Real native sections of the five diagnosed coincident-point families."""
import argparse
import json
from pathlib import Path
import signal

import numpy as np
from audit_pinched_junction import BODY_SHA, section_edges
from trial_native_junction_blend import DIAGNOSTIC_SHA, PAIRS, segment_kind, read_native
from render_v5_v2 import sha, save


def run(args):
    import OCP
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pins = {args.body: BODY_SHA, args.diagnostic: DIAGNOSTIC_SHA, Path(__file__): sha(__file__)}
    for name in ('audit_pinched_junction.py', 'trial_native_junction_blend.py', 'render_v5_v2.py'):
        p = Path(__file__).with_name(name); pins[p] = sha(p)
    if (args.output.exists() or OCP.__version__ != '7.9.3.1'
            or any(p.is_symlink() or sha(p) != h for p, h in pins.items())):
        raise ValueError('fresh_private_output_and_exact_inputs_required')
    args.output.mkdir(mode=0o700)
    body = read_native(args.body)
    groups = json.loads(args.diagnostic.read_text())['groups_private']
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    summaries = []
    for ax, pair in zip(axes.flat, PAIRS):
        selected = [g for g in groups if sorted(r['face_index'] for r in
                    g['nearby_native_faces_private'][:2]) == list(pair)]
        if not selected: raise ValueError('missing_diagnosed_family')
        centre = np.asarray(selected[0]['point_private'])
        classes = [segment_kind(body, *(r['point'] for r in g['nearby_native_faces_private'][:2]))
                   for g in selected]
        if len({r[0] for r in classes}) != 1: raise ValueError('mixed_family_classification')
        kind = classes[0][0]; widths = [r[1] for r in classes]
        for line in section_edges(body, centre): ax.plot(line[:, 0], line[:, 2], color='#294858', lw=1)
        ax.scatter(centre[0], centre[2], color='#d45529' if kind == 'material_lip' else '#1a96ac', s=24)
        ax.set_xlim(centre[0]-.15, centre[0]+.15); ax.set_ylim(centre[2]-.15, centre[2]+.15)
        ax.set_aspect('equal'); ax.grid(alpha=.2)
        ax.set_xlabel('X — provisional scan units'); ax.set_ylabel('Z — provisional scan units')
        ax.ticklabel_format(useOffset=False)
        ax.set_title(f"Faces {pair[0]}/{pair[1]}: {kind.replace('_', ' ')}\n"
                     f"{len(selected)} pairs | local 3D segments {min(widths):.5f}–{max(widths):.5f}", fontsize=10)
        summaries.append(dict(face_pair=list(pair), kind=kind, pairs=len(selected),
                              minimum_segment=min(widths), maximum_segment=max(widths)))
    axes.flat[-1].axis('off')
    axes.flat[-1].text(.04, .9,
        '14 coincident vertex pairs\n5 native edge families\n\n8 near air gaps\n6 near material lips\n\n'
        'Each plot: exact CAD intersection at fixed Y.\nDot: first mesh-defect point in that family.\n'
        'Reported lengths are separate 3D ray tests,\nnot thickness measured from this picture.\n\n'
        'Original geometry unchanged.\nNo minimum-wall, 0.040 mm,\nCAE or manufacturing certificate.',
        va='top', fontsize=11, linespacing=1.45)
    fig.suptitle('M64 | Air gaps and material lips require different corrections', fontsize=17)
    fig.tight_layout(rect=(0,.03,1,.95))
    image = args.output/'junction-classes.png'; fig.savefig(image, dpi=170); plt.close(fig)
    save(args.output/'report.json', dict(schema='m64-native-junction-class-render/v1',
        OCP_version=OCP.__version__, numpy_version=np.__version__, matplotlib_version=matplotlib.__version__,
        source_sha256=pins[Path(__file__)], native_BRep_sha256=BODY_SHA,
        diagnostic_sha256=DIAGNOSTIC_SHA, image_sha256=sha(image), families=summaries,
        display_curve_deflection=.0002, geometry_modified=False, manufacturing_authorized=False,
        helper_sha256={p.name: h for p, h in pins.items() if p.name.endswith('.py')},
        inputs_unchanged=all(sha(p) == h for p, h in pins.items())))
    if any(sha(p) != h for p, h in pins.items()): raise ValueError('inputs_changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body', 'diagnostic', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    signal.alarm(180)
    run(parser.parse_args())
