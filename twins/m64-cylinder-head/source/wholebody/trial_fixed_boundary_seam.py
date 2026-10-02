#!/usr/bin/env python3
"""Bounded, fixed-boundary opening of one diagnosed native air-gap face.

Coordinates and candidates remain private. A local geometry candidate is not
a mesh repair, physical 0.040 mm certificate or manufacturing approval.
"""
import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import signal
import time

import numpy as np
from trial_native_junction_blend import (
    BODY_SHA, DIAGNOSTIC_SHA, indexed, read_native, segment_kind, line_chords,
    section_edges, sha, save,
)
from trial_native_junction_chamfer import encoded


def deform_surface(surface, direction, amplitude):
    """Modify only an independent working surface; keep all four boundaries."""
    from OCP.gp import gp_Pnt
    direction = np.asarray(direction, dtype=float)
    if (direction.shape != (3,) or not np.isfinite(direction).all()
            or abs(np.linalg.norm(direction)-1) > 1e-12
            or not math.isfinite(amplitude) or not 0 < amplitude <= .035):
        raise ValueError('bounded_amplitude_and_unit_direction_required')
    if (not hasattr(surface, 'NbUPoles') or surface.IsURational() or surface.IsVRational()
            or (surface.UDegree(), surface.VDegree(), surface.NbUPoles(), surface.NbVPoles()) != (1, 1, 2, 2)):
        raise ValueError('single_nonrational_bilinear_surface_required')
    u0, u1, v0, v1 = surface.Bounds()
    surface.IncreaseDegree(4, 4)
    # Fixed exploratory support: last 8% of U and 12% of V, near measured probes.
    surface.InsertUKnot(u0+.92*(u1-u0), 4, 1e-12)
    surface.InsertVKnot(v0+.88*(v1-v0), 4, 1e-12)
    if (surface.NbUPoles(), surface.NbVPoles()) != (9, 9):
        raise ValueError('unexpected_piecewise_Bernstein_layout')
    coefficient = amplitude*4096/729
    p = np.array(surface.Pole(8, 8).Coord()) + coefficient*direction
    surface.SetPole(8, 8, gp_Pnt(*p))
    # B_3^4(t)=4*t^3*(1-t) has exact maximum 27/64, zero value at
    # both ends and zero first/second derivatives at the lower support edge.
    bound = Fraction.from_float(coefficient)*Fraction(729, 4096)
    if not (surface.RemoveUKnot(2, 2, 1e-12) and surface.RemoveVKnot(2, 2, 1e-12)):
        raise ValueError('C2_knot_reduction_failed')
    return coefficient, bound


def field(u, v, coefficient):
    x, y = (u-.92)/.08, (v-.88)/.12
    return coefficient*16*x**3*(1-x)*y**3*(1-y) if 0 <= x <= 1 and 0 <= y <= 1 else 0.


def located_surface(face):
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    location = TopLoc_Location()
    surface = BRep_Tool.Surface_s(face, location)
    transform = location.Transformation()
    if abs(abs(transform.ScaleFactor())-1) > 1e-12:
        raise ValueError('rigid_surface_placement_required')
    return surface, transform


def tolerances(shape):
    from OCP.BRep import BRep_Tool
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    return {name: [BRep_Tool.Tolerance_s(cast(s)) for s in indexed(shape, kind)]
            for name, kind, cast in [('faces', TopAbs_FACE, TopoDS.Face_s),
                                    ('edges', TopAbs_EDGE, TopoDS.Edge_s),
                                    ('vertices', TopAbs_VERTEX, TopoDS.Vertex_s)]}


def gap_width(shape, a, b):
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_OUT
    from OCP.gp import gp_Pnt
    a, b = np.array(a), np.array(b)
    centre = (a+b)/2
    direction = (b-a)/np.linalg.norm(b-a)
    hits = line_chords(shape, centre, direction, .15)['intersections']
    lo, hi = max(t for t in hits if t < 0), min(t for t in hits if t > 0)
    if not all(BRepClass3d_SolidClassifier(shape, gp_Pnt(*(centre+(lo+t*(hi-lo))*direction)),
                 1e-9).State() == TopAbs_OUT for t in (.25, .5, .75)):
        raise ValueError('diagnosed_air_interval_lost')
    return hi-lo


def render(reference, candidate, centre, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for shape, colour, style, label in ((reference, '#244e71', '-', 'Original'),
                                      (candidate, '#d05a28', '--', 'Local candidate')):
        lines = section_edges(shape, centre)
        for ax in axes:
            for i, line in enumerate(lines):
                ax.plot(line[:, 0]-centre[0], line[:, 2]-centre[2], style,
                        color=colour, linewidth=1, label=label if i == 0 else None)
    for ax, half in zip(axes, (1., .12)):
        ax.set(xlim=(-half, half), ylim=(-half, half), xlabel='X offset — scan units',
               ylabel='Z offset — scan units', aspect='equal')
        ax.grid(alpha=.2)
        ax.legend()
    fig.suptitle('Actual native CAD section | fixed-boundary seam experiment')
    fig.text(.5, .02, 'Candidate only. Not a thermal field, print simulation or physical-scale certificate.', ha='center')
    fig.tight_layout(rect=(0, .05, 1, .94))
    fig.savefig(output, dpi=160)
    plt.close(fig)


def run(args):
    import OCP
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SOLID, TopAbs_IN
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt, gp_Vec
    pins = {args.body: BODY_SHA, args.diagnostic: DIAGNOSTIC_SHA, Path(__file__): sha(__file__)}
    for name in ('trial_native_junction_blend.py', 'trial_native_junction_chamfer.py',
                 'audit_pinched_junction.py', 'render_v5_v2.py'):
        p = Path(__file__).with_name(name)
        pins[p] = sha(p)
    if (args.output.exists() or args.output.is_symlink() or OCP.__version__ != '7.9.3.1'
            or any(p.is_symlink() or sha(p) != h for p, h in pins.items())):
        raise ValueError('exact_inputs_runtime_and_fresh_private_output_required')
    os.umask(0o077)
    args.output.mkdir(mode=0o700)
    start = time.monotonic()
    report = dict(schema='m64-fixed-boundary-seam/v1', status='incomplete',
        input_sha256=BODY_SHA, diagnostic_sha256=DIAGNOSTIC_SHA,
        source_sha256=pins[Path(__file__)], helper_sha256={p.name: h for p, h in pins.items() if p.suffix == '.py'},
        OCP_version=OCP.__version__, selected_face=1154, amplitude_scan_units=args.amplitude,
        support_normalized=[.92, 1., .88, 1.], master_replaced=False,
        physical_millimetres_certified=False, functional_interfaces_certified=False,
        global_minimum_wall_certified=False, full_mesh_passed=False, manufacturing_authorized=False)
    save(args.output/'started.json', report)
    reference, original = None, None
    try:
        reference, working = read_native(args.body), read_native(args.body)
        original = encoded(reference)
        valid = lambda s: BRepCheck_Analyzer(s, True, False, True).IsValid()
        if encoded(working) != original or not valid(reference):
            raise ValueError('independent_exact_valid_native_read_required')
        faces = indexed(working, TopAbs_FACE)
        if len(faces) != 4918 or len(indexed(working, TopAbs_SOLID)) != 1:
            raise ValueError('exact_single_body_required')
        face = TopoDS.Face_s(faces[1153])
        surface, transform = located_surface(face)
        original_surface = surface.Transformed(transform)
        edges = indexed(face, TopAbs_EDGE)
        if len(edges) != 4:
            raise ValueError('four_boundary_edges_required')
        allowed = [i for i, f in enumerate(faces, 1) if any(
            e.IsSame(g) for e in edges for g in indexed(f, TopAbs_EDGE))]
        if len(allowed) > 8:
            raise ValueError('bounded_incident_representation_patch_required')
        protected = {i: encoded(f) for i, f in enumerate(faces, 1) if i not in allowed}
        before_tolerances = tolerances(working)
        u0, u1, v0, v1 = surface.Bounds()
        boundary = []
        for edge in edges:
            c2 = BRepAdaptor_Curve2d(TopoDS.Edge_s(edge), face)
            c3 = BRepAdaptor_Curve(TopoDS.Edge_s(edge))
            samples = []
            for t in np.linspace(c2.FirstParameter(), c2.LastParameter(), 121):
                uv = c2.Value(float(t))
                if min(abs(uv.X()-u0), abs(uv.X()-u1), abs(uv.Y()-v0), abs(uv.Y()-v1)) > 1e-9:
                    raise ValueError('non_isoparametric_boundary_not_supported')
                samples.append((uv.X(), uv.Y(), c3.Value(float(t))))
            boundary.extend(samples)
        groups = json.loads(args.diagnostic.read_text())['groups_private']
        probes = []
        for group in groups:
            a, b = group['nearby_native_faces_private'][:2]
            if sorted((a['face_index'], b['face_index'])) == [893, 1154]:
                a, b = sorted((a, b), key=lambda row: row['face_index'])
                if segment_kind(reference, a['point'], b['point'])[0] != 'air_gap':
                    raise ValueError('original_air_gap_required')
                probes.append((np.array(a['point']), np.array(b['point'])))
        if len(probes) != 7:
            raise ValueError('seven_bound_native_witnesses_required')
        direction = np.mean([(b-a)/np.linalg.norm(b-a) for a, b in probes], axis=0)
        direction /= np.linalg.norm(direction)
        if not all(BRepClass3d_SolidClassifier(reference, gp_Pnt(*(b+args.amplitude*direction)),
                      1e-9).State() == TopAbs_IN for a, b in probes):
            raise ValueError('opening_direction_not_inside_source_material')
        report.update(permitted_representation_faces=allowed, direction_private=direction.tolist())
        save(args.output/'preflight.json', report)
        local_direction = gp_Vec(*direction).Transformed(transform.Inverted())
        coefficient, bound = deform_surface(surface, local_direction.Coord(), args.amplitude)
        surface = surface.Transformed(transform)
        report.update(scalar_field_bound_exact=str(bound), scalar_field_bound_scan_units=float(bound),
                      native_roundoff_bound_included=False, resulting_degrees=[surface.UDegree(), surface.VDegree()])
        error = maximum = 0.
        orientation = float('inf')
        for un in np.unique(np.r_[np.linspace(0, 1, 17), np.linspace(.92, 1, 65)]):
            for vn in np.unique(np.r_[np.linspace(0, 1, 17), np.linspace(.88, 1, 65)]):
                u, v = u0+un*(u1-u0), v0+vn*(v1-v0)
                old, new, du0, dv0, du1, dv1 = gp_Pnt(), gp_Pnt(), gp_Vec(), gp_Vec(), gp_Vec(), gp_Vec()
                original_surface.D1(u, v, old, du0, dv0)
                surface.D1(u, v, new, du1, dv1)
                error = max(error, new.Distance(gp_Pnt(*(np.array(old.Coord())+field(un, vn, coefficient)*direction))))
                maximum = max(maximum, old.Distance(new))
                n0, n1 = du0.Crossed(dv0), du1.Crossed(dv1)
                orientation = min(orientation, n0.Dot(n1)/n0.SquareMagnitude())
        boundary_error = max(p.Distance(surface.Value(u, v)) for u, v, p in boundary)
        source_boundary_error = max(p.Distance(original_surface.Value(u, v)) for u, v, p in boundary)
        report.update(native_formula_error_max_sampled=error, native_displacement_max_sampled=maximum,
            orientation_ratio_min_sampled=orientation, boundary_error_max_sampled=boundary_error,
            source_boundary_error_max_sampled=source_boundary_error, native_valid=valid(working),
            all_entity_tolerances_identical=tolerances(working) == before_tolerances,
            protected_face_serializations_unchanged=all(encoded(faces[i-1]) == b for i, b in protected.items()))
        save(args.output/'native-checks.json', report)
        if (bound > Fraction('0.040') or error > 1e-9 or maximum > .040 or orientation <= 0
                or boundary_error > 1e-7 or not report['native_valid']
                or not report['all_entity_tolerances_identical'] or not report['protected_face_serializations_unchanged']):
            raise ValueError('surface_native_or_locality_guard_failed')
        report['fixed_ray_widths'] = [dict(before=gap_width(reference, a, b), after=gap_width(working, a, b)) for a, b in probes]
        if not all(r['after'] > r['before'] for r in report['fixed_ray_widths']):
            raise ValueError('not_all_diagnosed_air_rays_improve')
        path = args.output/'diagnostic-candidate.brep'
        if not BRepTools.Write_s(working, str(path)):
            raise ValueError('native_write_failed')
        path.chmod(0o600)
        reread = read_native(path)
        report.update(candidate_sha256=sha(path), readback_valid=valid(reread),
                      readback_tolerances_identical=tolerances(reread) == before_tolerances)
        if not report['readback_valid'] or not report['readback_tolerances_identical'] or len(indexed(reread, TopAbs_SOLID)) != 1:
            raise ValueError('native_readback_guard_failed')
        save(args.output/'before-bop.json', report)
        check = BOPAlgo_ArgumentAnalyzer()
        check.SetShape1(reread)
        check.SelfInterMode = True
        check.StopOnFirstFaulty = True
        check.Perform()
        report.update(BOP_has_faulty=check.HasFaulty(), BOP_has_errors=check.HasErrors())
        if check.HasFaulty() or check.HasErrors():
            raise ValueError('BOP_self_intersection_check_failed')
        volumes = []
        for s in (reference, reread):
            props = GProp_GProps()
            BRepGProp.VolumeProperties_s(s, props)
            volumes.append(props.Mass())
        if not all(math.isfinite(v) and v > 0 for v in volumes):
            raise ValueError('positive_native_volumes_required')
        report['volume_change_scan_units_cubed'] = volumes[1]-volumes[0]
        image = args.output/'native-section.png'
        render(reference, reread, np.mean([(a+b)/2 for a, b in probes], axis=0), image)
        report['image_sha256'] = sha(image)
        report['status'] = 'local_candidate_passed_pending_full_mesh_and_physics'
    except Exception as exc:
        report.update(status='rejected', error_type=type(exc).__name__, error=str(exc))
    finally:
        report.update(elapsed_seconds=time.monotonic()-start,
                      inputs_unchanged=all(sha(p) == h for p, h in pins.items()),
                      reference_in_memory_unchanged=reference is not None and original is not None and encoded(reference) == original)
        if not report['inputs_unchanged'] or not report['reference_in_memory_unchanged']:
            report['status'] = 'rejected_input_changed'
        save(args.output/'report.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'elapsed_seconds', 'inputs_unchanged')}, allow_nan=False), flush=True)
    return 0 if report['status'].startswith('local_candidate_passed') else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body', 'diagnostic', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--amplitude', type=float, choices=(.02, .035), default=.02)
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
