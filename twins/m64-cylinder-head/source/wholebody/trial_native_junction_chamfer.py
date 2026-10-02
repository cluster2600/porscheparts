#!/usr/bin/env python3
"""One guarded chamfer experiment, not a repair or manufacturing approval.

Reuse the native junction classifier and topology metrics. Frozen fillet
sources are not edited. Coordinates, receipts and candidates stay private.
"""
import argparse
import io
import json
import math
import os
from pathlib import Path
import signal
import time

from trial_native_junction_blend import (
    BODY_SHA, DIAGNOSTIC_SHA, PAIRS, indexed, read_native, segment_kind,
    topology, ports, sha, save,
)


def encoded(shape):
    from OCP.BRepTools import BRepTools
    stream = io.BytesIO()
    BRepTools.Write_s(shape, stream)
    return stream.getvalue()


def prepare_chamfer(shape, edge, distance):
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
    from OCP.TopoDS import TopoDS
    if not math.isfinite(distance) or not 0 < distance <= .02:
        raise ValueError('finite_positive_distance_at_most_0p02_scan_units_required')
    maker = BRepFilletAPI_MakeChamfer(shape)
    maker.Add(distance, TopoDS.Edge_s(edge))
    if (maker.NbContours() != 1 or maker.NbEdges(1) != 1
            or not maker.Edge(1, 1).IsSame(edge)):
        raise ValueError('chamfer_must_not_propagate_to_another_edge')
    return maker


def tolerances_not_increased(before, after):
    return all(math.isfinite(after[k]['tolerance_max'])
               and math.isfinite(before[k]['tolerance_max'])
               and after[k]['tolerance_max'] <= before[k]['tolerance_max']
               for k in ('faces', 'edges', 'vertices'))


def run(args):
    import OCP
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID, TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    pins = {args.body: BODY_SHA, args.diagnostic: DIAGNOSTIC_SHA,
            Path(__file__): sha(__file__)}
    for name in ('trial_native_junction_blend.py', 'audit_pinched_junction.py', 'render_v5_v2.py'):
        path = Path(__file__).with_name(name)
        pins[path] = sha(path)
    for name in ('build_local_port_junction_fillet.py', 'build_scan_seeded_ports.py',
                 'build_bounded_c1_trunk.py', 'build_four_valve_distribution.py'):
        path = Path(__file__).resolve().parents[1] / name
        pins[path] = sha(path)
    if (args.pair not in PAIRS or args.distance not in (.005, .01, .02)
            or args.output.exists() or args.output.is_symlink()
            or OCP.__version__ != '7.9.3.1'
            or any(p.is_symlink() or sha(p) != h for p, h in pins.items())):
        raise ValueError('fresh_private_output_exact_inputs_runtime_and_bounded_parameters_required')
    os.umask(0o077)
    args.output.mkdir(mode=0o700)
    start = time.monotonic()
    receipt = dict(schema='m64-native-junction-chamfer/v1', status='incomplete',
        source_sha256=pins[Path(__file__)], native_BRep_sha256=BODY_SHA,
        diagnostic_sha256=DIAGNOSTIC_SHA, OCP_version=OCP.__version__,
        helper_sha256={p.name: h for p, h in pins.items() if p.name.endswith('.py')},
        selected_faces=list(args.pair), distance_scan_units=args.distance,
        master_replaced=False, physical_millimetres_certified=False,
        surface_deviation_certified=False, functional_interfaces_certified=False,
        CAE_authorized=False, manufacturing_authorized=False)
    save(args.output/'started.json', receipt)
    reference = None
    try:
        reference, working = read_native(args.body), read_native(args.body)
        original = encoded(reference)
        if encoded(working) != original:
            raise ValueError('independent_native_read_mismatch')
        faces = indexed(working, TopAbs_FACE)
        if (len(faces) != 4918 or len(indexed(reference, TopAbs_SOLID)) != 1
                or not BRepCheck_Analyzer(reference, True, False, True).IsValid()):
            raise ValueError('exact_valid_single_body_required')
        fa, fb = (faces[i-1] for i in args.pair)
        shared = [e for e in indexed(fa, TopAbs_EDGE)
                  if any(e.IsSame(f) for f in indexed(fb, TopAbs_EDGE))]
        if len(shared) != 1:
            raise ValueError('one_shared_edge_required')
        endpoints = indexed(shared[0], TopAbs_VERTEX)
        allowed = [i for i, face in enumerate(faces, 1) if any(
            v.IsSame(e) for v in indexed(face, TopAbs_VERTEX) for e in endpoints)]
        if not set(args.pair) <= set(allowed) or len(allowed) > 8:
            raise ValueError('bounded_endpoint_patch_required')
        protected = {i: encoded(f) for i, f in enumerate(faces, 1) if i not in allowed}
        all_edges = indexed(working, TopAbs_EDGE)
        receipt['edge_endpoint_valences'] = [sum(any(v.IsSame(p) for p in indexed(e, TopAbs_VERTEX))
                                                    for e in all_edges) for v in endpoints]
        receipt['source_surface_types'] = [str(BRepAdaptor_Surface(TopoDS.Face_s(f), False).GetType())
                                           for f in (fa, fb)]
        receipt['shared_curve_type'] = str(BRepAdaptor_Curve(TopoDS.Edge_s(shared[0])).GetType())
        witnesses = []
        for group in json.loads(args.diagnostic.read_text())['groups_private']:
            a, b = group['nearby_native_faces_private'][:2]
            pair = tuple(sorted((a['face_index'], b['face_index'])))
            if pair == args.pair:
                kind, width = segment_kind(reference, a['point'], b['point'])
                witnesses.append(dict(kind=kind, local_segment=width))
        if not witnesses:
            raise ValueError('diagnosed_native_witness_required')
        cad = ports.design.CAD()
        before = topology(cad, reference)
        receipt.update(permitted_source_faces=allowed, before_topology=before,
                       native_witnesses=witnesses)
        save(args.output/'preflight.json', receipt)
        maker = prepare_chamfer(working, shared[0], args.distance)
        save(args.output/'building.json', receipt)
        maker.Build()
        receipt['build_done'] = maker.IsDone()
        if not maker.IsDone():
            raise ValueError('native_chamfer_construction_failed')
        result = maker.Shape()
        after_faces = indexed(result, TopAbs_FACE)
        changed = [i for i, f in enumerate(faces, 1) if not any(f.IsSame(g) for g in after_faces)]
        after = topology(cad, result)
        receipt.update(after_topology=after, changed_source_faces=changed,
            native_valid=BRepCheck_Analyzer(result, True, False, True).IsValid(),
            protected_face_serializations_unchanged=all(
                encoded(faces[i-1]) == value for i, value in protected.items()),
            maximum_topological_tolerances_not_increased=tolerances_not_increased(before, after))
        volumes = []
        for shape in (reference, result):
            props = GProp_GProps()
            BRepGProp.VolumeProperties_s(shape, props)
            volumes.append(props.Mass())
        receipt['volume_change_scan_units_cubed'] = volumes[1]-volumes[0]
        if (not set(args.pair) <= set(changed) <= set(allowed)
                or not receipt['native_valid'] or after['solids'] != 1
                or not receipt['protected_face_serializations_unchanged']
                or not receipt['maximum_topological_tolerances_not_increased']
                or encoded(reference) != original
                or not all(math.isfinite(v) and v > 0 for v in volumes)):
            raise ValueError('locality_validity_or_tolerance_guard_failed')
        # ponytail: diagnostic only; add export only with BOP, deviation and domain checks.
        receipt['status'] = 'native_checks_passed_pending_BOP_deviation_domains_and_mesh'
    except Exception as exc:
        receipt.update(status='rejected', error_type=type(exc).__name__, error=str(exc))
    finally:
        receipt.update(elapsed_seconds=time.monotonic()-start,
                       inputs_unchanged=all(sha(p) == h for p, h in pins.items()))
        if reference is not None:
            receipt['source_in_memory_unchanged'] = encoded(reference) == original
        if not receipt['inputs_unchanged'] or receipt.get('source_in_memory_unchanged') is False:
            receipt['status'] = 'rejected_input_changed'
        save(args.output/'report.json', receipt)
    print(json.dumps(receipt, allow_nan=False), flush=True)
    return 0 if receipt['status'].startswith('native_checks_passed') else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body', 'diagnostic', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--pair', type=int, nargs=2, required=True)
    parser.add_argument('--distance', type=float, choices=(.005, .01, .02), required=True)
    args = parser.parse_args()
    args.pair = tuple(sorted(args.pair))
    signal.alarm(300)
    raise SystemExit(run(args))
