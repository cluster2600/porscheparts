#!/usr/bin/env python3
"""Independent rectangular-face flux vs adaptive native whole-solid volume.

This audit is specific to the pinned seam experiment. Integration of an arbitrary
trimmed face over its rectangular bounds would be wrong; it is not supported.
"""
import argparse
import json
import math
from pathlib import Path
import signal
import time

import numpy as np
from trial_native_junction_blend import BODY_SHA, indexed, read_native, sha, save

CANDIDATE_SHA = '30514eb86701dcced4c6f043ac4e492a21464d616357635dfa8bfdf9e2452150'


def rectangular_flux(face, order):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepTools import BRepTools
    from OCP.GeomAbs import GeomAbs_BSplineSurface, GeomAbs_Plane
    from OCP.TopAbs import TopAbs_FORWARD, TopAbs_REVERSED
    from OCP.gp import gp_Pnt, gp_Vec
    if face.Orientation() not in (TopAbs_FORWARD, TopAbs_REVERSED) or order not in (8, 16, 32):
        raise ValueError('supported_orientation_and_Gauss_order_required')
    surface = BRepAdaptor_Surface(face, False)
    u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
    us, vs = [u0, u1], [v0, v1]
    if surface.GetType() == GeomAbs_BSplineSurface:
        s = surface.BSpline()
        us += [s.UKnot(i) for i in range(1, s.NbUKnots()+1) if u0 < s.UKnot(i) < u1]
        vs += [s.VKnot(i) for i in range(1, s.NbVKnots()+1) if v0 < s.VKnot(i) < v1]
    elif surface.GetType() != GeomAbs_Plane:
        raise ValueError('only_pinned_rectangular_spline_or_analytic_plane_witness')
    us, vs = sorted(set(us)), sorted(set(vs))
    nodes, weights = np.polynomial.legendre.leggauss(order)
    terms = []
    for a, b in zip(us, us[1:]):
        for c, d in zip(vs, vs[1:]):
            for i, x in enumerate(nodes):
                for j, y in enumerate(nodes):
                    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
                    surface.D1((a+b)/2+(b-a)/2*x, (c+d)/2+(d-c)/2*y, p, du, dv)
                    terms.append(weights[i]*weights[j]*(b-a)*(d-c)/12 *
                                 np.dot(p.Coord(), du.Crossed(dv).Coord()))
    return math.fsum(terms)*(1 if face.Orientation() == TopAbs_FORWARD else -1)


def run(args):
    import OCP
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    pins = {args.body: BODY_SHA, args.candidate: CANDIDATE_SHA, args.receipt: sha(args.receipt),
            Path(__file__): sha(__file__)}
    receipt = json.loads(args.receipt.read_text())
    if (args.output.exists() or args.output.is_symlink() or OCP.__version__ != '7.9.3.1'
            or any(p.is_symlink() or sha(p) != h for p, h in pins.items())
            or receipt.get('candidate_sha256') != CANDIDATE_SHA or receipt.get('input_sha256') != BODY_SHA
            or receipt.get('status') != 'local_candidate_passed_pending_full_mesh_and_physics'
            or receipt.get('inputs_unchanged') is not True or receipt.get('BOP_has_faulty') is not False
            or receipt.get('BOP_has_errors') is not False):
        raise ValueError('exact_completed_native_trial_and_fresh_output_required')
    start = time.monotonic()
    shapes = [read_native(p) for p in (args.body, args.candidate)]
    faces = [TopoDS.Face_s(indexed(s, TopAbs_FACE)[1153]) for s in shapes]
    report = dict(schema='m64-fixed-boundary-volume-audit/v1', source_sha256=pins[Path(__file__)],
        body_sha256=BODY_SHA, candidate_sha256=CANDIDATE_SHA, trial_receipt_sha256=pins[args.receipt],
        OCP_version=OCP.__version__, original_default_volume_change=receipt['volume_change_scan_units_cubed'],
        scope='pinned_rectangular_face_1154_only; other_surfaces_unchanged',
        manufacturing_authorized=False, rigorous_interval_bound=False, Gauss=[], adaptive_native=[])
    for order in (8, 16, 32):
        fluxes = [rectangular_flux(f, order) for f in faces]
        report['Gauss'].append(dict(order=order, delta_scan_units_cubed=fluxes[1]-fluxes[0]))
    for eps in (1e-6, 1e-9, 1e-12):
        masses, estimates = [], []
        for shape in shapes:
            props = GProp_GProps()
            estimates.append(BRepGProp.VolumeProperties_s(shape, props, eps, True, False))
            masses.append(props.Mass())
        report['adaptive_native'].append(dict(requested_relative_eps=eps,
            native_error_estimates=estimates, delta_scan_units_cubed=masses[1]-masses[0]))
    values = [row['delta_scan_units_cubed'] for row in report['Gauss']]
    final = report['adaptive_native'][-1]['delta_scan_units_cubed']
    report['agreement_absolute_scan_units_cubed'] = abs(final-values[-1])
    report['inputs_unchanged'] = all(sha(p) == h for p, h in pins.items())
    passed = (all(math.isfinite(v) and v < 0 for v in values+[final]) and max(values)-min(values) < 1e-9
              and report['agreement_absolute_scan_units_cubed'] < 1e-8 and report['inputs_unchanged'])
    report.update(status='local_volume_crosscheck_passed' if passed else 'rejected_volume_disagreement',
                  elapsed_seconds=time.monotonic()-start)
    save(args.output, report)
    print(json.dumps(report), flush=True)
    return 0 if passed else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body', 'candidate', 'receipt', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    signal.alarm(120)
    raise SystemExit(run(parser.parse_args()))
