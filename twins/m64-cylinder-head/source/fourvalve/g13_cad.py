#!/usr/bin/env python3
"""Three upper central-spine hypotheses on the unchanged G11 bottom land."""
import argparse
import json
from pathlib import Path

import g11_cad as g11
import g12_cad as g12

G12_CAD = g11.REPO/'twins/m64-cylinder-head/evidence/g12-local-buttresses-20260926/cad.json'


def candidates():
    return [dict(id=f'centre_w11_spine60_t{w}', component='central_diaphragm',
                 journal_width_mm=11., parameters=dict(spine_x_span_mm=60., spine_width_mm=w,
                 unchanged_foot_height_mm=1., transition_height_mm=9., journal_width_mm=11.))
            for w in (18, 24, 30)]


def spine_profile(row, height):
    if row not in candidates() or height <= 10:
        raise ValueError('outside the bounded G13 central-spine hypotheses')
    q = row['parameters']
    w = q['spine_width_mm']/2
    z0 = q['unchanged_foot_height_mm']
    z1 = z0+q['transition_height_mm']
    return [(-5.5, z0), (5.5, z0), (w, z1), (w, height), (-w, height), (-w, z1)]


def candidate_shape(row, p, base):
    import cadquery as cq
    import carrier
    from cadcommon import _cyl
    axes = carrier.axes(p)
    z0 = p['carrier_face_height']
    top = max(a[0][2] for a in axes.values())+9
    profile = spine_profile(row, top-z0)
    half = row['parameters']['spine_x_span_mm']/2
    bore_r = p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']
    if half >= min(abs(a[0][0])-bore_r-1 for a in axes.values()):
        raise ValueError('spine enters the preserved journal neighbourhood')
    wire = cq.Wire.makePolygon([cq.Vector(-half, y, z0+z) for y, z in profile], close=True)
    shape = base.fuse(cq.Solid.extrudeLinear(wire, [], cq.Vector(2*half, 0, 0)))
    # Preserve the actual existing bolt/tool definitions, never carve moving-part envelopes.
    for x in (-p['carrier_mount_x'], p['carrier_mount_x']):
        shape = shape.cut(_cyl([x, 0, z0-1], [x, 0, top+1], 3.3))
    for tool in g11.oil_paths(p, 'central_diaphragm').values():
        shape = shape.cut(tool)
    return shape.clean()


def difference(a, b):
    return dict(added_volume_mm3=abs(a.cut(b).Volume()), removed_volume_mm3=abs(b.cut(a).Volume()))


def support_land(shape, p):
    """Exact bottom planar faces plus the same 0.05 mm section used by G12."""
    import cadquery as cq
    import g7
    z0 = p['carrier_face_height']
    slab = cq.Solid.makeBox(200, 100, .05, cq.Vector(-100, -50, z0))
    faces = [f for f in shape.Faces() if f.geomType() == 'PLANE'
             and abs(f.BoundingBox().zmin-z0) < 1e-6 and abs(f.BoundingBox().zmax-z0) < 1e-6]
    return shape.intersect(slab), dict(z_mm=z0, bottom_planar_area_mm2=sum(f.Area() for f in faces),
        bottom_faces=[dict(area_mm2=f.Area(), bounds_mm=g7.native_bounds(f)) for f in faces],
        selection='All bottom-plane faces at carrier_face_height; inherited whole-land XYZ clamp is not physical contact validation')


def journal_neighbourhoods(shape, base, p):
    import cadquery as cq
    import carrier
    r = p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']+1
    result = {}
    for side, (pivot, _) in carrier.axes(p).items():
        box = cq.Solid.makeBox(2*r, 60, 2*r, cq.Vector(pivot[0]-r, -30, pivot[2]-r))
        result[side] = difference(shape.intersect(box), base.intersect(box))
    return result


def outer_mirror_shapes(p, reference):
    """Build -y independently from its G7 body; do not define it by mirroring +y."""
    import cadquery as cq
    import carrier
    import g7
    from cadcommon import _cyl
    row = next(r for r in g11.candidates() if r['id'] == 'outer_d30_w30')
    positive = g11.candidate_shape(row, p, reference)
    negative = reference['carrier_base_m']
    for side, (pivot, cam) in carrier.axes(p).items():
        x, z, y = pivot[0], pivot[2], -g7.support_positions(p, side)
        rib = cq.Solid.makeBox(30, 8, z+9-108, cq.Vector(x-15, y-4, 108))
        bridge = cq.Solid.makeBox(30, y+p['carrier_end_y'], 30,
                                 cq.Vector(x-15, -p['carrier_end_y'], 108))
        negative = negative.fuse(rib, bridge).cut(_cyl([x, y-8, z], [x, y+8, z],
            p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']))
        feed = cam[2]-25
        negative = negative.cut(_cyl([x, y, feed], [x, -p['carrier_end_y'], feed], 1))
        negative = negative.cut(_cyl([x, y, feed], [x, y, z], 1)).cut(carrier.oil_tools(p, -1, side))
    return positive, negative.cut(carrier.returns(p, -1)).clean()


def outer_mirror_proof(p, reference, output, prior):
    import assembly
    import audit_g6 as audit
    import cadquery as cq
    import carrier
    import g7
    positive, negative = outer_mirror_shapes(p, reference)
    mirror = positive.mirror('XZ')
    delta = difference(negative, mirror)
    pos_land, pos_metadata = support_land(positive, p)
    neg_land, neg_metadata = support_land(negative, p)
    base_pos_land, _ = support_land(reference['carrier_base_p'], p)
    base_neg_land, _ = support_land(reference['carrier_base_m'], p)
    masks = dict(mirrored_fixed_land=difference(neg_land, pos_land.mirror('XZ')),
                 positive_land_vs_G7=difference(pos_land, base_pos_land),
                 negative_land_vs_G7=difference(neg_land, base_neg_land))
    bands = {}
    r = p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']+1
    for side, (pivot, _) in carrier.axes(p).items():
        y = g7.support_positions(p, side)
        box = cq.Solid.makeBox(2*r, 8, 2*r, cq.Vector(pivot[0]-r, y-4, pivot[2]-r))
        bands[side] = difference(negative.intersect(box.mirror('XZ')), positive.intersect(box).mirror('XZ'))
    folder = output/'outer_d30_w30_mirror'
    folder.mkdir()
    paths = {}
    for tag, shape in (('p', positive), ('m', negative)):
        step = folder/('carrier_base_'+tag+'.step')
        cq.exporters.export(cq.Workplane().add(shape), str(step))
        paths[tag] = dict(step=str(step.relative_to(output)), step_sha256=g11.sha256(step),
                          BRep_valid=assembly.brep_valid(shape), solid_count=len(shape.Solids()), volume_mm3=shape.Volume())
    collisions = [dict(part=name, volume_mm3=v) for name, part in reference.items()
                  if name != 'carrier_base_m' and (v := audit.overlap(negative, part)) > g11.TOL]
    result = dict(id='outer_d30_w30', classification='native_y_reflection_equivalence_not_new_FEA',
        transformation_matrix=[ [1, 0, 0], [0, -1, 0], [0, 0, 1] ],
        vector_cases={'+x': [1, 0, 0], '-z': [0, 0, -1]},
        load_and_fixed_XYZ_invariance='Applicable only to identical isotropic material, mirrored meshes/traction masks and the unchanged ideal whole-foot XYZ constraint; not a physical assembly or asymmetric hot-condition equivalence',
        native_difference_mm3=delta, foot_mask_comparison_mm3=masks,
        journal_mask_comparison_mm3=bands, positive_support_land=pos_metadata, negative_support_land=neg_metadata,
        source_prior_step_sha256=prior['step_sha256'], prior_volume_difference_mm3=positive.Volume()-prior['volume_mm3'],
        files=paths, negative_static_interferences=collisions, sampled_motion_interferences=[],
        motion_samples_checked=0, symmetry_accepted=False)
    result['symmetry_accepted'] = not collisions and all(row['BRep_valid'] and row['solid_count'] == 1 for row in paths.values()) and abs(result['prior_volume_difference_mm3']) < .01 and all(
        v <= g11.TOL for record in (delta, *masks.values(), *bands.values()) for v in record.values())
    return result, negative


def run(output):
    import assembly
    import audit_g6 as audit
    import cadquery as cq
    import g7
    output.mkdir(parents=True, exist_ok=False)
    baseline = json.loads(g11.BASELINE.read_text())
    g11_receipt = json.loads(g12.G11_CAD.read_text())
    g12_receipt = json.loads(G12_CAD.read_text())
    for module, expected in ((g11, g11_receipt['source_sha256']), (g12, g12_receipt['source_sha256'])):
        if g11.sha256(Path(module.__file__)) != expected:
            raise ValueError('frozen source fingerprint mismatch: '+module.__name__)
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
    land, land_metadata = support_land(base, p)
    g12a = next(r for r in g12_receipt['variants'] if r['id'] == 'centre_w11_local24_foot24_h40')
    outer = next(r for r in g11_receipt['variants'] if r['id'] == 'outer_d30_w30')
    report = dict(classification='G13_upper_central_spine_geometry_hypotheses_not_stiffness_results',
        complete=False, manufacturing_authorized=False, engine_start_authorized=False, FEA_executed=False,
        source_sha256=g11.sha256(Path(__file__)), g11_source_sha256=g11.sha256(Path(g11.__file__)),
        g12_source_sha256=g11.sha256(Path(g12.__file__)), g7_baseline_sha256=g11.sha256(g11.BASELINE),
        g11_receipt_sha256=g11.sha256(g12.G11_CAD), g12_receipt_sha256=g11.sha256(G12_CAD),
        values=p, variants=[], head_axes_journals_oil_and_fasteners_unchanged=True,
        baseline_volume_mm3=base.Volume(), baseline_support_land=land_metadata,
        baseline_projected_land=g12.projected_land(base, reference['head'], p),
        prior_g12a_projected_land=g12a['projected_land'],
        outer_reference=dict(id=outer['id'], journal_width_mm=outer['journal_width_mm'],
            step_sha256=outer['step_sha256'], parameters=outer['parameters'],
            cad_accepted_in_prior_receipt=outer['cad_accepted'], recomputed_in_this_campaign=False),
        spring_conservative_outer_bounds_mm=g12.spring_envelope_bounds(p),
        design_rationale='Upper material inside x +/-30 mm transfers journal loads through the inner wall. The bottom 1 mm remains the G11 11 mm section; a 9 mm shoulder transition changes no ideal-clamp surface. Its local stress/compliance needs FEA. No predicted 0.040 mm achievement.',
        crank_samples_deg=list(range(0, 720, 5)), collision_tolerance_mm3=g11.TOL,
        motion_scope='Each candidate versus 27 G7 moving components; sampled rigid kinematics, not continuous or deformable dynamics',
        software={'cadquery': cq.__version__})
    report['outer_mirror_audit'], outer_negative = outer_mirror_proof(p, reference, output, outer)
    def checkpoint():
        (output/'receipt.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    shapes = {}
    envelope = g7.native_bounds(cq.Compound.makeCompound(list(reference.values())))
    for row in candidates():
        shape = candidate_shape(row, p, base)
        shapes[row['id']] = shape
        bounds = g7.native_bounds(shape)
        void = audit.closed_voids(shape)
        oil = {name: dict(residual_solid_mm3=audit.overlap(shape, tool), tool_connected_solids=len(tool.Solids()))
               for name, tool in g11.oil_paths(p, 'central_diaphragm').items()}
        collisions = [dict(part=name, volume_mm3=v) for name, part in reference.items()
                      if name != 'central_diaphragm' and (v := audit.overlap(shape, part)) > g11.TOL]
        candidate_land, metadata = support_land(shape, p)
        land_diff = difference(candidate_land, land)
        bands = journal_neighbourhoods(shape, base, p)
        failures = []
        valid = assembly.brep_valid(shape)
        if not valid or len(shape.Solids()) != 1:
            failures.append('invalid_or_disconnected_BRep')
        if not void['no_enclosed_void_detected']:
            failures.append('closed_void_detected')
        if any(r['residual_solid_mm3'] > g11.TOL or r['tool_connected_solids'] != 1 for r in oil.values()):
            failures.append('existing_oil_path_obstructed_or_disconnected')
        if any(v > g11.TOL for v in land_diff.values()) or abs(metadata['bottom_planar_area_mm2']-land_metadata['bottom_planar_area_mm2']) > g11.TOL:
            failures.append('bottom_fixed_land_changed')
        if any(v > g11.TOL for r in bands.values() for v in r.values()):
            failures.append('journal_neighbourhood_changed')
        if base.cut(shape).Volume() > g11.TOL:
            failures.append('baseline_material_removed')
        if any(bounds[a] < envelope[a]-1e-6 for a in ('xmin', 'ymin', 'zmin')) or any(
                bounds[a] > envelope[a]+1e-6 for a in ('xmax', 'ymax', 'zmax')):
            failures.append('outside_reference_assembly_envelope')
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
        row.update(volume_mm3=shape.Volume(), added_volume_mm3=shape.Volume()-base.Volume(),
            BRep_valid=valid, solid_count=len(shape.Solids()), bounds_mm=bounds, closed_void_check=void,
            oil_paths=oil, journal_neighbourhood_difference=bands, support_land=metadata,
            bottom_land_difference=land_diff, projected_land=g12.projected_land(shape, reference['head'], p),
            static_interferences=collisions, sampled_motion_interferences=[], motion_samples_checked=0,
            minimum_nominal_rocker_axial_gap_mm=min(p[s+'_valve_y']-p['rocker_width']/2-5.5 for s in ('intake', 'exhaust')),
            functional_clearance_qualified=False, step=str(step.relative_to(output)), step_sha256=g11.sha256(step),
            native_views={f.name: g11.sha256(f) for f in (folder/'preview.svg', folder/'section-x0.svg')},
            rejections=failures, cad_accepted=False)
        edge = row['parameters']['spine_x_span_mm']/2
        spring_bounds = report['spring_conservative_outer_bounds_mm']
        row['spine_spring_conservative_x_gap_mm'] = min(-edge-spring_bounds['intake_p']['xmax'], spring_bounds['exhaust_p']['xmin']-edge)
        report['variants'].append(row)
        checkpoint()
        print(json.dumps({'stage': 'CAD', 'id': row['id'], 'rejections': failures, 'collisions': collisions}), flush=True)
    for angle in report['crank_samples_deg']:
        motion = g11.moving_shapes(p, reference, angle)
        if set(motion) != set(g11.moving_names(reference)):
            raise ValueError('moving component coverage changed')
        for row in report['variants']:
            for name, part in motion.items():
                if (v := audit.overlap(shapes[row['id']], part)) > g11.TOL:
                    row['sampled_motion_interferences'].append(dict(crank_deg=angle, part=name, volume_mm3=v))
            row['motion_samples_checked'] += 1
        for name, part in motion.items():
            if (v := audit.overlap(outer_negative, part)) > g11.TOL:
                report['outer_mirror_audit']['sampled_motion_interferences'].append(dict(crank_deg=angle, part=name, volume_mm3=v))
        report['outer_mirror_audit']['motion_samples_checked'] += 1
        if angle % 60 == 0:
            checkpoint()
            print(json.dumps({'stage': 'motion', 'crank_deg': angle}), flush=True)
    for row in report['variants']:
        if row['sampled_motion_interferences']:
            row['rejections'].append('sampled_motion_interference')
        row['cad_accepted'] = not row['rejections'] and row['motion_samples_checked'] == 144
    report['outer_mirror_audit']['symmetry_accepted'] &= not report['outer_mirror_audit']['sampled_motion_interferences'] and report['outer_mirror_audit']['motion_samples_checked'] == 144
    report['complete'] = True
    checkpoint()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
