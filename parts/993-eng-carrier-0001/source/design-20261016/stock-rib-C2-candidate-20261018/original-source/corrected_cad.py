"""Redistribute V5 material and match the frozen, unmeasured F0 bracket.

The original builder and its outputs remain unchanged. This revision uses its
parametric arms, then adds rear ribs outside the new provisional tool columns.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

SOURCE = Path('/Users/maxime/.codex/worktrees/993-carrier-revalidation/3dprinting993/parts/993-eng-carrier-0001/source/bionic-20261011/correction-20261013')
BASE = SOURCE.parent
ROOT = SOURCE.parents[4]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def precise_volume(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    props=GProp_GProps()
    error=BRepGProp.VolumeProperties_s(shape.wrapped,props,1e-10,True,False)
    return props.Mass(),error


def contract():
    c = json.loads((SOURCE/'interface-study.json').read_text())
    for name, expected in c['sources_sha256'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Frozen input changed: '+name)
    return c


def config(depth, skin, web, window, rib_width, rib_top):
    c = contract()
    result = json.loads((BASE/'study-v5.json').read_text())
    result['design_id'] = 'carrier-correction-20261013'
    result['revision_reason'] = ('Redistribute material into deeper arms and rear ribs; '
                                 'match the independently frozen F0 study bracket')
    g = result['geometry']
    g['central_bolt_centres_xy_mm'] = c['study_central_centres_xy_mm']
    g['arm_shell'] = {'depth_mm': depth, 'cap_mm': skin, 'web_mm': web}
    g['window_scale'] = window
    g['central_back_ribs'] = {'width_mm': rib_width, 'top_z_mm': rib_top, 'inboard_y_mm': 5}
    result['design_constraints']['baseline_interface_comparator'] = (
        'Frozen F0 study bracket in correction-20261013/interface-study.json; not OEM evidence')
    result['design_constraints']['protected_regions'] = (
        '8 mm central pad and 25 mm tool columns at F0 study centres; V5 end bores/seats')
    result['design_constraints']['secondary_access'] = 'Full-depth cutters; retained 12 mm axial gauge'
    result['load_cases']['reverse_torque_combined'] = {
        'force_N': [0, 0, -4000], 'moment_Nmm': [0, -850000, 0]}
    for axis, name in enumerate(('roll', 'pitch', 'yaw')):
        moment = [0, 0, 0]
        moment[axis] = 850000
        result['load_cases'][name] = {'force_N': [0, 0, 0], 'moment_Nmm': moment}
    return result


def build(settings, output):
    from build123d import Edge, Wire, Face, Polygon, Cylinder, Pos, extrude, export_step, export_stl, export_brep, import_step
    c = contract()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    settings = copy.deepcopy(settings)
    settings['design_id'] += '-'+output.name
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    (output/'requested-study.json').write_text(json.dumps(settings, indent=2)+'\n')
    spec = importlib.util.spec_from_file_location('frozen_carrier_cad', BASE/'cad.py')
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base_settings = copy.deepcopy(settings)
    base_settings['geometry'].pop('central_back_ribs')
    base.build(base_settings, output/'base-without-ribs')
    body = import_step(output/'base-without-ribs/carrier.step')
    g = settings['geometry']
    t, stock = g['thickness_mm'], g['arm_shell']['depth_mm']
    if 'end_window_scale' in g:
        reinforced = copy.deepcopy(base_settings)
        reinforced['geometry']['window_scale'] = g['end_window_scale']
        base.build(reinforced, output/'outer-window-stock')
        stock_body = import_step(output/'outer-window-stock/carrier.step')
        for side in (-1, 1):
            mask = Polygon(*[(side*x,y) for x,y in ((172,-20),(255,-14),(243,15))], align=None)
            mask = Pos(0,0,-stock)*extrude(mask,amount=2*stock,dir=(0,0,1))
            body = body+(stock_body&mask)
    if g.get('root_gusset_radius_mm',0)>0:
        envelope=base.arm_envelope(stock,t)
        for sx in (-1,1):
            for sy in (-1,1):
                gusset=Pos(sx*76,sy*29,0)*Cylinder(g['root_gusset_radius_mm'],2*stock)
                body=body+(gusset&envelope)
    rib = g['central_back_ribs']
    w, top, inner = rib['width_mm'], rib['top_z_mm'], rib['inboard_y_mm']
    from fractions import Fraction as Q
    assert (w, top, inner) == (2.8, 30, 5)
    # Exact cubic-to-degree6 elevation; only the central outward-Y pole gains 64/20*w.
    outer_Q = [(Q(22), Q(87,5)), (Q(49,2), Q(87,5)), (Q(132,5), Q(76,5)),
               (Q(561,20), Q(1043,50)), (Q(149,5), Q(43,5)), (Q(32), Q(32,5)), (Q(35), Q(32,5))]
    def transition(side, offset, X_side):
        if offset != w/2:
            xy = [(22,16+offset),(27,16+offset),(29,inner+offset),(35,inner+offset)]
        else:
            xy = [(float(x),float(y)) for x,y in outer_Q]
        if X_side < 0:
            xy = [(-x,y) for x,y in reversed(xy)]
        points = [(x,side*y) for x,y in xy]
        edge = Edge.make_bezier(*points)
        if offset == w/2:
            rational = outer_Q if X_side > 0 else [(-x,y) for x,y in reversed(outer_Q)]
            row = dict(X_side=X_side,Y_side=side,role='outward_Y_rail',degree=6,
                amplitude_mm=w,law='64*t^3*(1-t)^3',nominal_Y_width_mm=w,maximum_Y_width_mm=2*w,
                source_cubic_inner_y_mm=inner,source_inner_rail_unchanged=True,
                control_points_Q=[[str(x),str(side*y)] for x,y in rational],
                actual_float_control_points_mm=[list(point) for point in points],
                C2_delta_zero_at_both_endpoints=True)
            with (output/'rib-width-branch-ledger.jsonl').open('a') as stream:
                stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        return edge
    for side in (-1, 1):
        rails = []
        for offset in (-w/2, w/2):
            def p(x, y):
                return (x, side*(y+offset))
            rails.extend([
                Edge.make_bezier(p(-105, 25), p(-90, 25), p(-80, inner), p(-65, inner)),
                Edge.make_line(p(-65, inner), p(-35, inner)),
                transition(side, offset, -1),
                Edge.make_line(p(-22, 16), p(22, 16)),
                transition(side, offset, 1),
                Edge.make_line(p(35, inner), p(65, inner)),
                Edge.make_bezier(p(65, inner), p(80, inner), p(90, 25), p(105, 25)),
            ])
        rails += [Edge.make_line((x, side*(25-w/2)), (x, side*(25+w/2))) for x in (-105, 105)]
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
    # Remove material through the whole local depth, including sloping hollow arms.
    # The old 10 mm drill left partial secondary bores beyond Z=+/-5 mm.
    for x, y in g['secondary_centres_xy_mm']:
        body = body - Pos(x, y, 0)*Cylinder(g['secondary_radius_mm'], 2*(top+stock))
    # Preserve the declared study tool paths after adding reinforcement.
    tool_removed = 0.0
    for x, y in c['study_central_centres_xy_mm']:
        cutter = Pos(x, y, 4+(top+10)/2)*Cylinder(c['study_tool_radius_mm'], top+10)
        before = body.volume
        body = body-cutter
        tool_removed += before-body.volume
    export_brep(body, output/'native-before-original-gates.brep')
    assert body.is_valid and len(body.solids()) == 1
    export_step(body, output/'carrier.step')
    export_stl(body, output/'carrier.stl', tolerance=.06, angular_tolerance=.10)
    reread = import_step(output/'carrier.step')
    assert reread.is_valid and len(reread.solids()) == 1
    volume,integration_error=precise_volume(body)
    read_volume,read_error=precise_volume(reread)
    comparison={'original_default_mm3':body.volume,'readback_default_mm3':reread.volume,
                'adaptive_original_mm3':volume,'adaptive_readback_mm3':read_volume,
                'estimated_relative_integration_errors':[integration_error,read_error],
                'adaptive_relative_difference':read_volume/volume-1}
    (output/'volume-integration.json').write_text(json.dumps(comparison,indent=2)+'\n')
    assert abs(read_volume/volume-1) < 1e-8
    mass = volume*settings['material']['density_tonne_mm3']*1000
    (output/'study.json').write_text(json.dumps(settings, indent=2)+'\n')
    report = {'design_id': settings['design_id'], 'volume_mm3': volume,
              'dense_reference_mass_kg': mass, 'mass_ceiling_pass': mass <= c['mass_ceiling_kg'],
              'CAD_valid': True, 'solid_count': 1, 'STEP_readback_volume_match': True,
              'tool_clearance_removed_mm3': tool_removed,
              'geometry_sha256': {n: sha(output/n) for n in ('carrier.step', 'carrier.stl')},
              'interface_contract_sha256': sha(SOURCE/'interface-study.json'),
              'generator_sha256': sha(Path(__file__)),
              'dimension_source': 'provisional_study_contract_not_OEM',
              'fitment_validated': False, 'manufacturing_authorized': False}
    (output/'geometry.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
    return report


if __name__ == '__main__':
    if len(sys.argv) not in (8, 9, 10):
        raise SystemExit('Usage: corrected_cad.py OUT DEPTH SKIN WEB WINDOW RIB_WIDTH RIB_TOP [END_WINDOW [ROOT_RADIUS]]')
    settings=config(*map(float, sys.argv[2:8]))
    if len(sys.argv)>=9: settings['geometry']['end_window_scale']=float(sys.argv[8])
    if len(sys.argv)==10: settings['geometry']['root_gusset_radius_mm']=float(sys.argv[9])
    build(settings, sys.argv[1])
