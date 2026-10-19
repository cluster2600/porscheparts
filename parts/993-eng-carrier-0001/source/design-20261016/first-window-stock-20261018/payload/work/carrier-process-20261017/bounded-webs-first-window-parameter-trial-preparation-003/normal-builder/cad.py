"""Retained CAD body with inset window cutters and adaptive STEP-volume gate.

Original source bionic-20261011/cad.py SHA256 3c7afe3916020f715fbb6889b46b288254873367ed7a3e5da7c5b4e6953c7c4e.
The copied construction is unchanged except the two explicitly marked blocks.
"""
import hashlib
import json
import sys
from pathlib import Path

from build123d import (Edge, Wire, Face, Polygon, fillet, extrude, Cylinder,
                      Pos, export_step, export_stl, import_step, Vector)


def arm_envelope(depth, pad, start=65, end=278):
    """Smooth XZ arch, extruded across Y; its centre retains the pad datum."""
    edges = []
    for side in (-1, 1):
        for zsign in (-1, 1):
            def p(x, z):
                return (side*x, -100, zsign*z)
            edges.extend([
                Edge.make_bezier(p(start, pad/2), p(78, pad/2),
                                 p(87, depth/2), p(100, depth/2)),
                Edge.make_line(p(100, depth/2), p(240, depth/2)),
                Edge.make_bezier(p(240, depth/2), p(255, depth/2),
                                 p(end-8, pad/2), p(end, pad/2)),
            ])
        if pad:
            edges.append(Edge.make_line(p(end, -pad/2), p(end, pad/2)))
    if pad:
        edges += [Edge.make_line((-start, -100, z), (start, -100, z))
                  for z in (-pad/2, pad/2)]
        return extrude(Face(Wire(edges)), amount=200, dir=(0, 1, 0))
    # The two hollow cores taper to zero before either joint.
    return [extrude(Face(Wire(edges[i:i+6])), amount=200, dir=(0, 1, 0))
            for i in (0, 6)]


def build(config, output):
    g = config['geometry']
    t = g['thickness_mm']
    assert t > 0 and len(g['central_bolt_centres_xy_mm']) == 4
    assert len(g['end_centres_x_mm']) == 2
    assert 0 < g['end_bore_radius_mm'] < g['end_outer_radius_mm']
    output.mkdir(parents=True, exist_ok=False)
    edges = [
        Edge.make_bezier((-278, -22), (-220, -20), (-100, -36), (-65, -36)),
        Edge.make_line((-65, -36), (65, -36)),
        Edge.make_bezier((65, -36), (100, -36), (220, -20), (278, -22)),
        Edge.make_line((278, -22), (278, 22)),
        Edge.make_bezier((278, 22), (220, 20), (100, 36), (65, 36)),
        Edge.make_line((65, 36), (-65, 36)),
        Edge.make_bezier((-65, 36), (-100, 36), (-220, 20), (-278, 22)),
        Edge.make_line((-278, 22), (-278, -22)),
    ]
    shell = g.get('arm_shell')
    stock = shell['depth_mm'] if shell else t
    body = Pos(0, 0, -stock / 2) * extrude(Face(Wire(edges)), amount=stock)
    windows = [([(78, -25), (146, -20), (80, 24)], 6),
               ([(105, 24), (217, 18), (156, -22)], 7),
               ([(172, -20), (255, -14), (243, 15)], 5)]
    import os
    for side in (-1, 1):
        for window_index, (points, radius) in enumerate(windows):
            scale = g.get('window_scale', 1)
            assert 0 < scale <= 1
            cx, cy = [sum(p[i] for p in points)/len(points) for i in (0, 1)]
            points = [(cx+scale*(x-cx), cy+scale*(y-cy)) for x, y in points]
            face = Polygon(*[(side * x, y) for x, y in points], align=None)
            face = fillet(face.vertices(), radius*scale)
            # New: inset the rounded cutter before any solid Boolean.
            original_face = face.faces()[0]
            inset = 2.8 if window_index == 0 and scale == 0.9 else g['window_edge_inset_mm']
            with (output/'window-branch-ledger.jsonl').open('a') as ledger:
                ledger.write(json.dumps(dict(X_side=side, scale=scale, window_index=window_index, inset_mm=inset, rounded_radius_before_offset_mm=radius*scale, nominal_radius_after_offset_mm=radius*scale-inset, scaled_triangle_points_mm=points), allow_nan=False)+'\n')
                ledger.flush(); os.fsync(ledger.fileno())
            face = Face(original_face.outer_wire().offset_2d(-inset))
            assert 0 < face.area < original_face.area
            cut = Pos(0, 0, -stock) * extrude(face, amount=2 * stock, dir=(0, 0, 1))
            body = body - cut
    if shell:
        assert 0 < 2*shell['cap_mm'] < stock and shell['web_mm'] > 0
        body = body & arm_envelope(stock, t)
        w = shell['web_mm']
        for side, core in zip((-1, 1), arm_envelope(stock-2*shell['cap_mm'], 0, end=268)):
            inner = [Edge.make_bezier((side*65, -36+w), (side*100, -36+w),
                                     (side*220, -20+w), (side*278, -22+w)),
                     Edge.make_line((side*278, -22+w), (side*278, 22-w)),
                     Edge.make_bezier((side*278, 22-w), (side*220, 20-w),
                                      (side*100, 36-w), (side*65, 36-w)),
                     Edge.make_line((side*65, 36-w), (side*65, -36+w))]
            hollow = Pos(0, 0, -stock)*extrude(Face(Wire(inner)), amount=2*stock, dir=(0, 0, 1))
            body = body - (hollow & core)
    if g.get('central_back_ribs'):
        # Stiffen behind the assumed mating face, outside the bolt/tool columns.
        rib = g['central_back_ribs']; w = rib['width_mm']; top = rib['top_z_mm']
        for side in (-1, 1):
            rails = []
            for offset in (-w/2, w/2):
                def p(x, y):
                    return (x, side*(y+offset))
                rails.extend([
                    Edge.make_bezier(p(-105, 25), p(-90, 25), p(-80, 8), p(-65, 8)),
                    Edge.make_line(p(-65, 8), p(-35, 8)),
                    Edge.make_bezier(p(-35, 8), p(-29, 8), p(-27, 16), p(-22, 16)),
                    Edge.make_line(p(-22, 16), p(22, 16)),
                    Edge.make_bezier(p(22, 16), p(27, 16), p(29, 8), p(35, 8)),
                    Edge.make_line(p(35, 8), p(65, 8)),
                    Edge.make_bezier(p(65, 8), p(80, 8), p(90, 25), p(105, 25)),
                ])
            rails += [Edge.make_line((x, side*(25-w/2)), (x, side*(25+w/2)))
                      for x in (-105, 105)]
            raised = Pos(0, 0, t/2-.01)*extrude(Face(Wire(rails)), amount=top-t/2+.01, dir=(0, 0, 1))
            profile = [Edge.make_bezier((-105, -100, stock/2), (-90, -100, stock/2),
                                        (-80, -100, top), (-65, -100, top)),
                       Edge.make_line((-65, -100, top), (65, -100, top)),
                       Edge.make_bezier((65, -100, top), (80, -100, top),
                                        (90, -100, stock/2), (105, -100, stock/2)),
                       Edge.make_line((105, -100, stock/2), (105, -100, t/2-.01)),
                       Edge.make_line((105, -100, t/2-.01), (-105, -100, t/2-.01)),
                       Edge.make_line((-105, -100, t/2-.01), (-105, -100, stock/2))]
            body = body + (raised & extrude(Face(Wire(profile)), amount=200, dir=(0, 1, 0)))
    for x in g['end_centres_x_mm']:
        body = body + Pos(x, 0, 0) * Cylinder(g['end_outer_radius_mm'],
                                              g['end_length_mm'], rotation=(90, 0, 0))
    # Round the four long concave blade-to-eye junction edges, not the seats.
    junctions = [e for e in body.edges()
                 if 260 < abs(e.center().X) < 274
                 and (abs(e.center().Z) > t/2 if shell else abs(abs(e.center().Z) - t/2) < 1e-5)
                 and abs(e.center().Y) < 1e-5 and e.length > 25]
    assert len(junctions) == 4, [(tuple(e.center()), e.length) for e in junctions]
    body = fillet(junctions, g['boss_blend_radius_mm'])
    for x in g['end_centres_x_mm']:
        body = body - Pos(x, 0, 0) * Cylinder(g['end_bore_radius_mm'],
                                              g['end_length_mm'] + 2, rotation=(90, 0, 0))
    for x, y in g['central_bolt_centres_xy_mm']:
        body = body - Pos(x, y, 0) * Cylinder(g['central_bore_radius_mm'], t + 2)
    for x in g['central_opening_centres_x_mm']:
        body = body - Pos(x, 0, 0) * Cylinder(g['central_opening_radius_mm'], t + 2)
    for x, y in g['secondary_centres_xy_mm']:
        body = body - Pos(x, y, 0) * Cylinder(g['secondary_radius_mm'], t + 2)
    assert body.is_valid and len(body.solids()) == 1
    mass = body.volume * config['material']['density_tonne_mm3'] * 1000
    if shell:
        limits = config['design_constraints']
        assert mass <= limits['absolute_mass_ceiling_kg'], f'Overweight: {mass:.6f} kg'
        assert t == limits['reference_pad_thickness_mm']
    export_step(body, output / 'carrier.step')
    export_stl(body, output / 'carrier.stl', tolerance=0.08, angular_tolerance=0.12)
    reread = import_step(output / 'carrier.step')
    assert reread.is_valid and len(reread.solids()) == 1
    # New: the same strict gate, using adaptive integration for curved faces.
    from corrected_cad import precise_volume
    native_volume, _ = precise_volume(body)
    readback_volume, _ = precise_volume(reread)
    assert abs(readback_volume / native_volume - 1) < 1e-8
    solid = reread.solids()[0]
    # Readback checks compare the exported solid with the declared study inputs.
    for x, y in g['central_bolt_centres_xy_mm']:
        for z in (-t / 2 - 1, 0, t / 2 + 1):
            assert not solid.is_inside(Vector(x, y, z))
        assert solid.is_inside(Vector(x + g['central_bore_radius_mm'] + 1, y, 0))
    for x in g['end_centres_x_mm']:
        for y in (-g['end_length_mm'] / 2 - 1, 0, g['end_length_mm'] / 2 + 1):
            assert not solid.is_inside(Vector(x, y, 0))
        assert solid.is_inside(Vector(x, 0, g['end_bore_radius_mm'] + 1))
    report = {
        'design_id': config['design_id'], 'dimension_source': 'design_assumptions',
        'volume_mm3': body.volume,
        'dense_reference_mass_kg': mass,
        'CAD_valid': True, 'solid_count': 1, 'STEP_readback_volume_match': True,
        'six_provisional_bore_axis_checks_pass': True,
        'measured_interface_inspection': False, 'manufacturing_authorized': False,
        'geometry_sha256': {n: hashlib.sha256((output / n).read_bytes()).hexdigest()
                            for n in ['carrier.step', 'carrier.stl']},
    }
    (output / 'geometry.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'study.json').write_text(json.dumps(config, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    build(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]))
