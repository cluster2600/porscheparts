#!/usr/bin/env python3
"""Classify a native junction and try one bounded fillet on a separate body.

No tolerance escalation, contour propagation, master replacement or CAE release.
The output is a geometry experiment, not a proof of surface deviation or fit.
"""
import argparse
import io
import json
from pathlib import Path
import signal
import sys
import time

import numpy as np
from audit_pinched_junction import BODY_SHA, indexed, line_chords, section_edges
from render_v5_v2 import sha, save

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_local_port_junction_fillet import read_native, topology, build_fillet, STRICT_PARAMETERS
import build_scan_seeded_ports as ports

DIAGNOSTIC_SHA = '14e6d154a84c1170b11b72fb63e2b1c3454fe706455391c5cee8fc726b9a41cf'
PAIRS = ((679, 888), (679, 897), (712, 952), (893, 1154), (1177, 1427))


def segment_kind(shape, a, b):
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN, TopAbs_OUT
    from OCP.gp import gp_Pnt
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    length = float(np.linalg.norm(b-a))
    if a.shape != (3,) or b.shape != (3,) or not np.isfinite(length) or not 1e-6 < length < .1:
        raise ValueError('finite_local_segment_required')
    ray = line_chords(shape, (a+b)/2, b-a, length*.6)
    if len(ray['intersections']) != 2 or not np.allclose(
            ray['intersections'], [-length/2, length/2], rtol=0, atol=1e-8):
        raise ValueError('segment_must_have_only_its_two_native_boundary_intersections')
    states = [BRepClass3d_SolidClassifier(shape, gp_Pnt(*map(float, a+t*(b-a))), 1e-9).State()
              for t in (.25, .5, .75)]
    if all(s == TopAbs_IN for s in states): return 'material_lip', length
    if all(s == TopAbs_OUT for s in states): return 'air_gap', length
    raise ValueError('ambiguous_native_segment')


def run(args):
    import OCP
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID, TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    pins = {args.body: BODY_SHA, args.diagnostic: DIAGNOSTIC_SHA,
            Path(__file__): sha(__file__)}
    for name in ('audit_pinched_junction.py', 'render_v5_v2.py'):
        p = Path(__file__).with_name(name); pins[p] = sha(p)
    for name in ('build_local_port_junction_fillet.py', 'build_scan_seeded_ports.py',
                 'build_bounded_c1_trunk.py', 'build_four_valve_distribution.py'):
        p = Path(__file__).resolve().parents[1]/name; pins[p] = sha(p)
    if (args.output.exists() or OCP.__version__ != '7.9.3.1'
            or any(p.is_symlink() or sha(p) != h for p, h in pins.items())):
        raise ValueError('fresh_private_output_and_exact_inputs_runtime_required')
    args.output.mkdir(mode=0o700)
    started = time.monotonic()
    receipt = dict(schema='m64-native-junction-blend/v1', status='incomplete',
        source_sha256=pins[Path(__file__)], native_BRep_sha256=BODY_SHA,
        diagnostic_sha256=DIAGNOSTIC_SHA, OCP_version=OCP.__version__,
        helper_sha256={p.name: h for p, h in pins.items() if p.name.endswith('.py')},
        selected_faces=list(args.pair), radius_scan_units=args.radius,
        construction_mode='strict-approximation-v1', independent_native_read=True,
        permitted_patch='selected_edge_and_its_endpoint_incident_faces',
        master_replaced=False, physical_millimetres_certified=False,
        surface_deviation_certified=False, CAE_authorized=False, manufacturing_authorized=False)
    save(args.output/'started.json', receipt)
    try:
        body = read_native(args.body)
        def encoded(shape):
            stream = io.BytesIO(); BRepTools.Write_s(shape, stream); return stream.getvalue()
        original = encoded(body)
        working = read_native(args.body)
        if encoded(working) != original: raise ValueError('working_copy_serialization_changed')
        faces = indexed(working, TopAbs_FACE)
        if len(faces) != 4918 or not BRepCheck_Analyzer(body, True, False, True).IsValid():
            raise ValueError('exact_valid_body_required')
        groups = json.loads(args.diagnostic.read_text())['groups_private']
        classification = []
        for group in groups:
            a, b = group['nearby_native_faces_private'][:2]
            pair = sorted([a['face_index'], b['face_index']])
            if tuple(pair) not in PAIRS: raise ValueError('unexpected_native_pair')
            kind, width = segment_kind(body, a['point'], b['point'])
            classification.append(dict(face_pair=pair, kind=kind, local_segment=width,
                                       point_private=group['point_private']))
        receipt['native_segments_private'] = classification
        save(args.output/'classification.json', receipt)
        fa, fb = (faces[i-1] for i in args.pair)
        edges_a, edges_b = indexed(fa, TopAbs_EDGE), indexed(fb, TopAbs_EDGE)
        shared = [e for e in edges_a if any(e.IsSame(f) for f in edges_b)]
        if len(shared) != 1: raise ValueError('one_shared_edge_required')
        endpoints = indexed(shared[0], TopAbs_VERTEX)
        allowed = [i for i, f in enumerate(faces, 1) if any(
            v.IsSame(e) for v in indexed(f, TopAbs_VERTEX) for e in endpoints)]
        if not set(args.pair) <= set(allowed) or len(allowed) > 8:
            raise ValueError('bounded_endpoint_patch_required')
        receipt['permitted_source_faces'] = allowed
        protected = {i: encoded(f) for i, f in enumerate(faces, 1) if i not in allowed}
        cad = ports.design.CAD()
        before_topology = topology(cad, body)
        receipt['before_topology'] = before_topology
        save(args.output/'patch-before-build.json', receipt)
        # The frozen port helper builds before inspecting contour propagation.
        # Here reject propagation first, before the costly whole-body operation.
        operation = BRepFilletAPI_MakeFillet(working)
        operation.SetParams(*STRICT_PARAMETERS)
        operation.Add(args.radius, TopoDS.Edge_s(shared[0]))
        if (operation.NbContours() != 1 or operation.NbEdges(1) != 1
                or not operation.Edge(1, 1).IsSame(shared[0])):
            raise ValueError('fillet_must_not_propagate_to_another_edge')
        operation, build = build_fillet(working, [TopoDS.Edge_s(shared[0])], args.radius,
                                        'strict-approximation-v1')
        receipt['build'] = build
        receipt['fillet_done'] = operation.IsDone()
        if not operation.IsDone(): raise ValueError('native_fillet_failed')
        result = operation.Shape()
        after = indexed(result, TopAbs_FACE)
        changed = [i for i, f in enumerate(faces, 1) if not any(f.IsSame(g) for g in after)]
        receipt.update(changed_source_faces=changed, result_faces=len(after),
                       result_solids=len(indexed(result, TopAbs_SOLID)),
                       native_valid=BRepCheck_Analyzer(result, True, False, True).IsValid(),
                       source_in_memory_unchanged=encoded(body) == original)
        receipt['protected_face_serializations_unchanged'] = all(
            encoded(faces[i-1]) == value for i, value in protected.items())
        after_topology = topology(cad, result)
        receipt['after_topology'] = after_topology
        tolerance_ok = all(after_topology[k]['tolerance_max'] <= before_topology[k]['tolerance_max']
                           for k in ('faces', 'edges', 'vertices'))
        receipt['maximum_topological_tolerances_not_increased'] = tolerance_ok
        if (not set(args.pair) <= set(changed) <= set(allowed) or not receipt['native_valid']
                or not tolerance_ok
                or not receipt['protected_face_serializations_unchanged']
                or receipt['result_solids'] != 1 or not receipt['source_in_memory_unchanged']):
            raise ValueError('locality_or_validity_guard_failed')
        output = args.output/'candidate-private.brep'
        if not BRepTools.Write_s(result, str(output)): raise ValueError('native_write_failed')
        output.chmod(0o600)
        reread = read_native(output)
        if (not BRepCheck_Analyzer(reread, True, False, True).IsValid()
                or len(indexed(reread, TopAbs_SOLID)) != 1):
            raise ValueError('native_readback_failed')
        receipt['candidate_sha256'] = sha(output)
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        centre = np.mean([r['point_private'] for r in classification if tuple(r['face_pair']) == args.pair], axis=0)
        before_lines, after_lines = section_edges(body, centre), section_edges(reread, centre)
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        for ax, half in zip(axes, (2., .15)):
            for lines, color, style in ((before_lines, '#235477', '-'), (after_lines, '#db6539', '--')):
                for line in lines: ax.plot(line[:, 0], line[:, 2], style, color=color, lw=1)
            ax.set_xlim(centre[0]-half, centre[0]+half); ax.set_ylim(centre[2]-half, centre[2]+half)
            ax.set_aspect('equal'); ax.grid(alpha=.2)
            ax.set_xlabel('X — provisional scan units'); ax.set_ylabel('Z — provisional scan units')
        fig.suptitle('Native junction trial | blue: original, orange: fillet candidate')
        fig.text(.5, .015, 'Real CAD section. Local geometry change; no mesh, physical-scale or manufacturing approval.', ha='center')
        fig.tight_layout(rect=(0,.045,1,.93))
        image = args.output/'native-section.png'; fig.savefig(image, dpi=160); plt.close(fig)
        receipt['image_sha256'] = sha(image)
        receipt['status'] = 'candidate_only_pending_BOP_deviation_and_remesh'
    except Exception as exc:
        receipt.update(status='rejected', error_type=type(exc).__name__, error=str(exc))
    finally:
        receipt.update(elapsed_seconds=time.monotonic()-started,
                       inputs_unchanged=all(sha(p) == h for p, h in pins.items()))
        save(args.output/'report.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'native_segments_private'}), flush=True)
    return 0 if receipt['status'].startswith('candidate_only') and receipt['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body', 'diagnostic', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--pair', type=int, nargs=2, required=True)
    parser.add_argument('--radius', type=float, choices=(.02, .05, .1), required=True)
    args = parser.parse_args(); args.pair = tuple(sorted(args.pair))
    if args.pair not in PAIRS: parser.error('diagnosed_face_pair_required')
    signal.alarm(300)
    raise SystemExit(run(args))
