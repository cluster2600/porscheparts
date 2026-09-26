#!/usr/bin/env python3
"""Bounded G11 support variants and sampled assembly checks, not a build release."""
import argparse
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path[:0] = [str(HERE), str(HERE / 'cad')]
BASELINE = REPO / 'twins/m64-cylinder-head/evidence/g7-local-supports-cooling-20260925/native-audit.json'
TOL = 1e-5


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidates():
    outer = [dict(id=f'outer_d{d}_w{w}', component='carrier_base_p',
                  parameters=dict(bridge_depth_mm=d, bridge_x_width_mm=w, centre_wall_mm=10),
                  journal_width_mm=8.) for d, w in itertools.product((18, 24, 30), repeat=2)]
    return outer + [dict(id=f'centre_w{w}', component='central_diaphragm',
                        parameters=dict(bridge_depth_mm=18, bridge_x_width_mm=18, centre_wall_mm=w),
                        journal_width_mm=float(w)) for w in (10, 11, 12)]


def dimensions(row):
    """Only the approved twelve designs; prevents accidental parameter coupling."""
    if row not in candidates():
        raise ValueError('candidate is outside the approved G11 grid')
    q = row['parameters']
    return dict(outer_width=q['bridge_x_width_mm'], bottom=138-q['bridge_depth_mm'],
                depth=q['bridge_depth_mm'], centre_width=q['centre_wall_mm'],
                centre_x_margin=9., outer_journal_width=8.)


def oil_paths(p, component):
    import carrier
    import g7
    from cadcommon import _cyl
    out = {}
    for side, (pivot, cam) in carrier.axes(p).items():
        x, z = pivot[0], pivot[2]
        if component == 'central_diaphragm':
            sign = -1 if side == 'intake' else 1
            out[side] = _cyl([x+sign*20, 0, z], [x, 0, z], 1)
        else:
            y, feed = g7.support_positions(p, side), cam[2]-25
            out[side] = _cyl([x, y, feed], [x, p['carrier_end_y'], feed], 1).fuse(
                _cyl([x, y, feed], [x, y, z], 1), carrier.oil_tools(p, 1, side)).clean()
    if component == 'carrier_base_p':
        out['return'] = carrier.returns(p, 1)
    return out


def candidate_shape(row, p, reference):
    import cadquery as cq
    import carrier
    import g7
    from cadcommon import _cyl
    d = dimensions(row)
    axes = carrier.axes(p)
    component = row['component']
    if component == 'central_diaphragm':
        x0 = axes['intake'][0][0]-d['centre_x_margin']
        x1 = axes['exhaust'][0][0]+d['centre_x_margin']
        z0, top, w = p['carrier_face_height'], max(a[0][2] for a in axes.values())+9, d['centre_width']
        shape = cq.Solid.makeBox(x1-x0, w, top-z0, cq.Vector(x0, -w/2, z0))
        for x in (-p['carrier_mount_x'], p['carrier_mount_x']):
            shape = shape.cut(_cyl([x, 0, z0-1], [x, 0, top+1], 3.3))
    else:
        shape = reference[component]
        w = d['outer_journal_width']
        for side, (pivot, _) in axes.items():
            x, z = pivot[0], pivot[2]
            y, bx, bottom = g7.support_positions(p, side), d['outer_width'], d['bottom']
            rib = cq.Solid.makeBox(bx, w, z+9-bottom, cq.Vector(x-bx/2, y-w/2, bottom))
            bridge = cq.Solid.makeBox(bx, p['carrier_end_y']-y, d['depth'], cq.Vector(x-bx/2, y, bottom))
            shape = shape.fuse(rib, bridge)
    for side, (pivot, _) in axes.items():
        x, z = pivot[0], pivot[2]
        y = 0 if component == 'central_diaphragm' else g7.support_positions(p, side)
        shape = shape.cut(_cyl([x, y-w, z], [x, y+w, z],
                               p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']))
    for tool in oil_paths(p, component).values():
        shape = shape.cut(tool)
    return shape.clean()


def moving_names(reference):
    return [n for n in reference if n == 'piston' or n.startswith(
        ('camshaft_', 'rocker_intake_', 'rocker_exhaust_', 'roller_', 'valve_', 'retainer_', 'spring_'))]


def moving_shapes(p, reference, angle):
    """Exact rigid transforms of the existing cam/rockers; fresh spring envelope."""
    import components
    import kinematics as kin
    import layout
    import numpy as np
    import rocker_geometry as rg
    out = {}
    crown = kin.piston_crown_z(p, np.array([angle, 0.]))
    out['piston'] = reference['piston'].translate((0, 0, float(crown[0]-crown[1])))
    for side in layout.SIDES:
        pivot, cam, _, _ = rg.frame(p, side, 1)
        sign = -1 if side == 'intake' else 1
        origin = (float(cam[0]), 0., float(cam[2]))
        out['camshaft_'+side] = reference['camshaft_'+side].rotate(origin,
            (origin[0], -sign, origin[2]), angle/2)
        state, zero = rg.state(p, side, angle), rg.state(p, side, 0)
        delta = math.degrees(float(state['beta'][0]-zero['beta'][0]))
        lift, lift0 = float(state['valve_lift_mm'][0]), float(zero['valve_lift_mm'][0])
        for sy in (-1, 1):
            tag = side + ('_p' if sy > 0 else '_m')
            point = tuple(rg.frame(p, side, sy)[0])
            end = (point[0], point[1]+sign, point[2])
            for name in ('rocker', 'roller', 'roller_pin'):
                key = name+'_'+tag
                out[key] = reference[key].rotate(point, end, delta)
            movement = tuple(-layout.axis_up(p, side)*(lift-lift0))
            for name in ('valve', 'retainer'):
                key = name+'_'+tag
                out[key] = reference[key].translate(movement)
            out['spring_'+tag] = components.spring(p, side, sy, lift)
    return out


def run(output):
    import assembly
    import audit_g6 as audit
    import cadquery as cq
    import g7
    output.mkdir(parents=True, exist_ok=False)
    baseline = json.loads(BASELINE.read_text())
    for name, expected in baseline['source_sha256'].items():
        if sha256(REPO/name) != expected:
            raise ValueError('G7 source fingerprint mismatch: '+name)
    p = baseline['values']
    reference, _ = g7.parts(p)
    # Rebuilding the unchanged G7 head provides an independent input drift check.
    if abs(reference['head'].Volume()-baseline['head_volume_mm3']) > .01:
        raise ValueError('rebuilt baseline head volume changed')
    report = dict(classification='G11_geometric_support_candidates_not_qualified',
                  manufacturing_authorized=False, engine_start_authorized=False, complete=False,
                  baseline_sha256=sha256(BASELINE), source_sha256=sha256(Path(__file__)),
                  values=p, variants=[], head_unchanged=True, bores_axes_and_mount_positions_unchanged=True,
                  functional_clearance_qualified=False,
                  motion_scope='sampled rigid kinematics and spring envelopes; not continuous or deformable dynamics',
                  crank_samples_deg=list(range(0, 720, 5)), collision_tolerance_mm3=TOL,
                  software={'cadquery': cq.__version__})
    def checkpoint():
        (output/'receipt.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    shapes = {}
    envelope = g7.native_bounds(cq.Compound.makeCompound(list(reference.values())))
    for row in candidates():
        component = row['component']
        shape = candidate_shape(row, p, reference)
        shapes[row['id']] = shape
        b = g7.native_bounds(shape)
        void = audit.closed_voids(shape)
        oil = {n: {'tool_connected_solids': len(t.Solids()), 'residual_solid_mm3': audit.overlap(t, shape)}
               for n, t in oil_paths(p, component).items()}
        collisions = [{'part': n, 'volume_mm3': v} for n, part in reference.items()
                      if n != component and (v := audit.overlap(shape, part)) > TOL]
        failures = []
        if not assembly.brep_valid(shape) or len(shape.Solids()) != 1:
            failures.append('invalid_or_disconnected_BRep')
        if not void['no_enclosed_void_detected']:
            failures.append('closed_void_detected')
        if any(r['residual_solid_mm3'] > TOL or r['tool_connected_solids'] != 1 for r in oil.values()):
            failures.append('oil_path_obstructed_or_disconnected')
        if any(b[a] < envelope[a]-1e-6 for a in ('xmin', 'ymin', 'zmin')) or any(
                b[a] > envelope[a]+1e-6 for a in ('xmax', 'ymax', 'zmax')):
            failures.append('outside_reference_assembly_envelope')
        if collisions:
            failures.append('static_interference')
        folder = output/row['id']
        folder.mkdir()
        step = folder/(component+'.step')
        cq.exporters.export(cq.Workplane().add(shape), str(step))
        # Native BRep line drawings, not generated product pictures or simulated fields.
        cq.exporters.export(cq.Workplane().add(shape), str(folder/'preview.svg'), opt={
            'projectionDir': (1, -1, -.8), 'showHidden': False, 'width': 900, 'height': 600})
        plane_y = 0. if component == 'central_diaphragm' else g7.support_positions(p, 'intake')
        section = shape.cut(cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, plane_y, -500)))
        cq.exporters.export(cq.Workplane().add(section), str(folder/'section.svg'), opt={
            'projectionDir': (0, 1, 0), 'showHidden': False, 'width': 900, 'height': 600})
        row.update(step=str(step.relative_to(output)), step_sha256=sha256(step), volume_mm3=shape.Volume(),
                   added_volume_mm3=shape.Volume()-reference[component].Volume(), BRep_valid=assembly.brep_valid(shape),
                   solid_count=len(shape.Solids()), bounds_mm=b, closed_void_check=void, oil_paths=oil,
                   static_interferences=collisions, sampled_motion_interferences=[], motion_samples_checked=0,
                   minimum_nominal_rocker_axial_gap_mm=min(p[s+'_valve_y']-p['rocker_width']/2-row['journal_width_mm']/2
                       for s in ('intake', 'exhaust')) if component == 'central_diaphragm' else 1.,
                   journal_gap_mm=p['carrier_journal_radial_clearance'], rejections=failures, cad_accepted=False)
        row['native_views'] = {f.name: sha256(f) for f in (folder/'preview.svg', folder/'section.svg')}
        report['variants'].append(row)
        checkpoint()
        print(json.dumps({'stage': 'CAD', 'id': row['id'], 'rejections': failures}), flush=True)
    # ponytail: reuse each complete pose across the twelve supports; 5-degree sampling is not swept-volume proof.
    for angle in report['crank_samples_deg']:
        motion = moving_shapes(p, reference, angle)
        if set(motion) != set(moving_names(reference)):
            raise ValueError('moving component coverage changed')
        for row in report['variants']:
            for name, part in motion.items():
                v = audit.overlap(shapes[row['id']], part)
                if v > TOL:
                    row['sampled_motion_interferences'].append(dict(crank_deg=angle, part=name, volume_mm3=v))
            row['motion_samples_checked'] += 1
        if angle % 60 == 0:
            checkpoint()
            print(json.dumps({'stage': 'motion', 'crank_deg': angle}), flush=True)
    for row in report['variants']:
        if row['sampled_motion_interferences']:
            row['rejections'].append('sampled_motion_interference')
        row['cad_accepted'] = not row['rejections'] and row['motion_samples_checked'] == 144
    report['complete'] = True
    checkpoint()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
