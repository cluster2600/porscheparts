#!/usr/bin/env python3
"""Two rejected full-width controls and two localized central-foot hypotheses."""
import argparse
import json
import math
from pathlib import Path

import g11_cad as g11

G11_CAD = g11.REPO/'twins/m64-cylinder-head/evidence/g11-support-stiffness-20260926/cad.json'


def candidates():
    rows = [dict(id=f'centre_w11_foot{w}_h{h}', component='central_diaphragm',
                 parameters=dict(base_width_mm=w, flare_height_mm=h, journal_width_mm=11.))
            for w, h in ((24, 40), (30, 50))]
    return rows+[dict(id=f'centre_w11_local{span}_foot{w}_h{h}', component='central_diaphragm',
                     parameters=dict(base_width_mm=w, flare_height_mm=h, journal_width_mm=11., local_x_span_mm=span))
                 for span, w, h in ((24, 24, 40), (28, 30, 50))]


def flare_profile(base_width, height):
    if not all(math.isfinite(v) for v in (base_width, height)) or (base_width, height) not in ((24, 40), (30, 50)):
        raise ValueError('foot flare is outside the bounded G12 design hypotheses')
    return [(-base_width/2, 0.), (base_width/2, 0.), (5.5, height), (-5.5, height)]


def candidate_shape(row, p, base):
    import cadquery as cq
    import carrier
    from cadcommon import _cyl
    if row not in candidates():
        raise ValueError('unknown G12 candidate')
    q = row['parameters']
    axes = carrier.axes(p)
    z0 = p['carrier_face_height']
    bore_bottom = min(a[0][2] for a in axes.values())-p['rocker_pivot_radius']-p['carrier_journal_radial_clearance']
    if z0+q['flare_height_mm'] >= bore_bottom:
        raise ValueError('flare would change the journal band')
    x0, x1 = axes['intake'][0][0]-9, axes['exhaust'][0][0]+9
    windows = [(x0, x1)]
    if 'local_x_span_mm' in q:
        half = q['local_x_span_mm']/2
        windows = [(x-half, x+half) for x in (-p['carrier_mount_x'], p['carrier_mount_x'])]
        if any(a < x0 or b > x1 for a, b in windows):
            raise ValueError('local buttress extends beyond the unchanged x envelope')
    shape = base
    for a, b in windows:
        points = [cq.Vector(a, y, z0+z) for y, z in flare_profile(q['base_width_mm'], q['flare_height_mm'])]
        wire = cq.Wire.makePolygon(points, close=True)
        foot = cq.Solid.extrudeLinear(wire, [], cq.Vector(b-a, 0, 0))
        shape = shape.fuse(foot)
    for x in (-p['carrier_mount_x'], p['carrier_mount_x']):
        shape = shape.cut(_cyl([x, 0, z0-1], [x, 0, max(a[0][2] for a in axes.values())+10], 3.3))
    for tool in g11.oil_paths(p, 'central_diaphragm').values():
        shape = shape.cut(tool)
    return shape.clean()


def projected_land(shape, head, p):
    """Geometric 0.05 mm land slice only; no contact, preload or bearing pressure."""
    import cadquery as cq
    b = shape.BoundingBox()
    slab = cq.Solid.makeBox(b.xlen+2, b.ylen+2, .05,
                           cq.Vector(b.xmin-1, b.ymin-1, p['carrier_face_height']))
    land = shape.intersect(slab).translate((0, 0, -.05))
    return dict(slice_thickness_mm=.05, projected_foot_area_mm2=land.Volume()/.05,
                area_over_existing_head_solid_mm2=land.intersect(head).Volume()/.05,
                unsupported_projected_area_mm2=land.cut(head).Volume()/.05,
                structural_contact_qualified=False)


def spring_envelope_bounds(p):
    """Uncompressed outer cones contain shorter compressed cones with this taper."""
    import cadquery as cq
    import g7
    import layout
    from cadcommon import _v
    if p['spring_outer_diameter'] < p['retainer_diameter']:
        raise ValueError('spring outer-cone containment requires a narrowing taper')
    result = {}
    for side, sy in layout.VALVES:
        axis = layout.axis_up(p, side)
        seat = layout.head_centre(p, side, sy)+axis*p[side+'_spring_seat_axial']
        shape = cq.Solid.makeCone(p['spring_outer_diameter']/2, p['retainer_diameter']/2,
                                 p['spring_installed_height'], _v(seat), _v(axis))
        result[side+('_p' if sy > 0 else '_m')] = g7.native_bounds(shape)
    return result


def run(output):
    import assembly
    import audit_g6 as audit
    import cadquery as cq
    import g7
    output.mkdir(parents=True, exist_ok=False)
    baseline = json.loads(g11.BASELINE.read_text())
    g11_receipt = json.loads(G11_CAD.read_text())
    if g11.sha256(Path(g11.__file__)) != g11_receipt['source_sha256']:
        raise ValueError('frozen G11 source fingerprint mismatch')
    for name, expected in baseline['source_sha256'].items():
        if g11.sha256(g11.REPO/name) != expected:
            raise ValueError('frozen G7 source fingerprint mismatch: '+name)
    p = baseline['values']
    reference, _ = g7.parts(p)
    if abs(reference['head'].Volume()-baseline['head_volume_mm3']) > .01:
        raise ValueError('rebuilt baseline head volume changed')
    base = g11.candidate_shape(next(r for r in g11.candidates() if r['id'] == 'centre_w11'), p, reference)
    prior = next(r for r in g11_receipt['variants'] if r['id'] == 'centre_w11')
    if not prior['cad_accepted'] or abs(base.Volume()-prior['volume_mm3']) > .01:
        raise ValueError('G11 central baseline replay failed')
    report = dict(classification='G12_local_foot_geometry_hypotheses_not_stiffness_results', complete=False,
                  manufacturing_authorized=False, engine_start_authorized=False, FEA_executed=False,
                  material_or_boundary_conditions_changed=False, source_sha256=g11.sha256(Path(__file__)),
                  g11_source_sha256=g11.sha256(Path(g11.__file__)), g11_receipt_sha256=g11.sha256(G11_CAD),
                  g7_baseline_sha256=g11.sha256(g11.BASELINE), values=p, variants=[],
                  head_axes_upper_journals_oil_and_fasteners_unchanged=True,
                  baseline_projected_land=projected_land(base, reference['head'], p),
                  spring_conservative_outer_bounds_mm=spring_envelope_bounds(p),
                  design_rationale='Localized buttresses are centred at the unchanged x=+/-25 mm mounts; spans 24/28 mm stop at +/-37/39 mm, inside the conservative spring x keep-outs. Geometry hypotheses only.',
                  crank_samples_deg=list(range(0, 720, 5)), collision_tolerance_mm3=g11.TOL,
                  motion_scope='Each candidate support versus 27 G7 moving components; sampled, not continuous or deformable dynamics',
                  software={'cadquery': cq.__version__})
    def checkpoint():
        (output/'receipt.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    shapes = {}
    for row in candidates():
        shape = candidate_shape(row, p, base)
        shapes[row['id']] = shape
        void = audit.closed_voids(shape)
        oil = {name: audit.overlap(shape, tool) for name, tool in g11.oil_paths(p, 'central_diaphragm').items()}
        collisions = [dict(part=name, volume_mm3=v) for name, part in reference.items()
                      if name != 'central_diaphragm' and (v := audit.overlap(shape, part)) > g11.TOL]
        failures = []
        if not assembly.brep_valid(shape) or len(shape.Solids()) != 1:
            failures.append('invalid_or_disconnected_BRep')
        if not void['no_enclosed_void_detected']:
            failures.append('closed_void_detected')
        if any(v > g11.TOL for v in oil.values()):
            failures.append('existing_oil_path_obstructed')
        if collisions:
            failures.append('static_interference')
        folder = output/row['id']
        folder.mkdir()
        step = folder/'central_diaphragm.step'
        cq.exporters.export(cq.Workplane().add(shape), str(step))
        cq.exporters.export(cq.Workplane().add(shape), str(folder/'preview.svg'), opt={
            'projectionDir': (1, -1, -.8), 'showHidden': False, 'width': 900, 'height': 600})
        section = shape.cut(cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(0, -500, -500)))
        cq.exporters.export(cq.Workplane().add(section), str(folder/'section-x0.svg'), opt={
            'projectionDir': (1, 0, 0), 'showHidden': False, 'width': 900, 'height': 600})
        row.update(journal_width_mm=11., volume_mm3=shape.Volume(), added_volume_mm3=shape.Volume()-base.Volume(),
                   BRep_valid=assembly.brep_valid(shape), solid_count=len(shape.Solids()),
                   closed_void_check=void, oil_path_residual_solid_mm3=oil,
                   static_interferences=collisions, sampled_motion_interferences=[], motion_samples_checked=0,
                   minimum_nominal_rocker_axial_gap_mm=min(p[s+'_valve_y']-p['rocker_width']/2-5.5
                       for s in ('intake', 'exhaust')), functional_clearance_qualified=False,
                   projected_land=projected_land(shape, reference['head'], p),
                   step=str(step.relative_to(output)), step_sha256=g11.sha256(step),
                   native_views={f.name: g11.sha256(f) for f in (folder/'preview.svg', folder/'section-x0.svg')},
                   rejections=failures, cad_accepted=False)
        if 'local_x_span_mm' in row['parameters']:
            edge = p['carrier_mount_x']+row['parameters']['local_x_span_mm']/2
            bounds = report['spring_conservative_outer_bounds_mm']
            row['added_buttress_spring_conservative_x_gap_mm'] = min(
                -edge-bounds['intake_p']['xmax'], bounds['exhaust_p']['xmin']-edge)
            if row['added_buttress_spring_conservative_x_gap_mm'] <= 0:
                failures.append('local_buttress_crosses_conservative_spring_x_envelope')
        report['variants'].append(row)
        checkpoint()
        print(json.dumps({'stage': 'CAD', 'id': row['id'], 'collisions': collisions}), flush=True)
    # Preserve even rejected geometry and all sampled failures; never cut away moving components to force a pass.
    for angle in report['crank_samples_deg']:
        motion = g11.moving_shapes(p, reference, angle)
        if set(motion) != set(g11.moving_names(reference)):
            raise ValueError('moving component coverage changed')
        for row in report['variants']:
            for name, part in motion.items():
                if (v := audit.overlap(shapes[row['id']], part)) > g11.TOL:
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
