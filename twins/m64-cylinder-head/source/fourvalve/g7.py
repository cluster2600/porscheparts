#!/usr/bin/env python3
"""G7 local rocker supports and finite-air cooling study; no engine/build release."""
import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'cad')]
import features
import g6_screen as g6
import layout

BASELINE = layout.REPO / 'twins/m64-cylinder-head/evidence/g6-carrier-thermal-am-20260925/native-audit.json'
F39 = layout.REPO / 'twins/reference-917-engine/source/run_f39_cooling_optimization.py'
spec = importlib.util.spec_from_file_location('g7_existing_cooling', F39)
cooling = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cooling)
DESIGN = {'centre_wall_mm': 10., 'rib_width_mm': 8., 'rib_x_width_mm': 18.,
          'rocker_axial_gap_mm': 1., 'bridge_bottom_mm': 120., 'bridge_height_mm': 18.,
          'rocker_pivot_radius': 6.25,
          'fin_count': 17, 'fin_pitch': 3.8, 'fin_thickness': 2., 'fin_x_margin': 0.}
AIR = {'air_density_kg_m3': 1.127, 'air_dynamic_viscosity_pa_s': 1.9e-5,
       'air_thermal_conductivity_w_mk': .0275,
       'air_cp_J_kgK': 1007., 'inlet_C': 40., 'minor_loss_k': 2., 'fan_efficiency': .5}
AIR['air_prandtl'] = AIR['air_cp_J_kgK']*AIR['air_dynamic_viscosity_pa_s']/AIR['air_thermal_conductivity_w_mk']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def baseline():
    b = json.loads(BASELINE.read_text())
    for name, expected in b['source_sha256'].items():
        if digest(layout.REPO / name) != expected:
            raise ValueError('G6 source fingerprint mismatch: ' + name)
    return b


def support_positions(p, side):
    outer = p[side + '_valve_y'] + p['rocker_width'] / 2 + DESIGN['rocker_axial_gap_mm'] + DESIGN['rib_width_mm'] / 2
    if outer + DESIGN['rib_width_mm'] / 2 >= p['carrier_end_y'] - p['carrier_wall_thickness'] / 2:
        raise ValueError('local rib overlaps end-frame journal band')
    if p[side + '_valve_y'] - p['rocker_width'] / 2 <= DESIGN['centre_wall_mm'] / 2:
        raise ValueError('central wall intersects rocker axial envelope')
    return outer


def point_span(force, length, position, diameter, E_GPa=200.):
    """Single load on a rotationally released shaft bay. mm/N/MPa; not carrier FEA."""
    g6.positive(force, length, position, diameter, E_GPa)
    if position >= length:
        raise ValueError('load must lie strictly between supports')
    E, I, a, b = E_GPa * 1000, math.pi * diameter**4 / 64, position, length-position
    exact = force*a*a*b*b/(3*E*I*length)
    K, f = np.zeros((6, 6)), np.zeros(6)
    for i, ell in enumerate((a, b)):
        ke = E*I/ell**3*np.array([[12,6*ell,-12,6*ell], [6*ell,4*ell**2,-6*ell,2*ell**2],
                                  [-12,-6*ell,12,-6*ell], [6*ell,2*ell**2,-6*ell,4*ell**2]])
        ix = np.arange(2*i, 2*i+4); K[np.ix_(ix,ix)] += ke
    f[2] = force
    free = [1,2,3,5]; u = np.zeros(6)
    u[free] = np.linalg.solve(K[np.ix_(free,free)], f[free])
    return {'load_point_deflection_mm': exact, 'independent_FE_at_load_mm': float(u[2]),
            'maximum_bending_stress_MPa': force*a*b/length*(diameter/2)/I,
            'centre_wall_reaction_per_bay_N': force*b/length, 'outer_rib_reaction_N': force*a/length,
            'carrier_compliance_included': False, 'strength_allowable_MPa': None}


def air_capacity(UA, capacity_rate, delta_T, cells=None):
    """Isothermal solid, finite-capacity air: exact NTU or implicit upwind cells."""
    g6.positive(UA, capacity_rate, delta_T)
    if cells is None:
        return capacity_rate * delta_T * -math.expm1(-UA/capacity_rate)
    if not isinstance(cells, int) or cells < 2:
        raise ValueError('at least two air cells required')
    excess = delta_T
    q = 0.
    for _ in range(cells):
        following = excess / (1 + UA/(cells*capacity_rate))
        q += UA/cells*following
        excess = following
    if not math.isclose(q, capacity_rate*(delta_T-excess), rel_tol=1e-10):
        raise ValueError('air energy balance failed')
    return q


def channel_case(p, mass_flow, solid_k, ceiling=250.):
    """Sealed straight channels along x; no bypass, real plenum or fan curve."""
    g6.positive(mass_flow, solid_k, ceiling-AIR['inlet_C'])
    boxes = features.fin_boxes(p)
    n = len(boxes)//2
    gap = (p['fin_pitch']-p['fin_thickness'])*.001
    depth, length = p['fin_depth']*.001, boxes[0][3]*.001
    if n < 2 or gap <= 0:
        raise ValueError('at least two separated fins per side required')
    area = 2*(n-1)*gap*depth
    Dh = 2*gap*depth/(gap+depth)
    speed = mass_flow/(AIR['air_density_kg_m3']*area)
    Re = AIR['air_density_kg_m3']*speed*Dh/AIR['air_dynamic_viscosity_pa_s']
    mach = speed/math.sqrt(1.4*287.05*(AIR['inlet_C']+273.15))
    row = {'mass_flow_kg_s_per_head_hypothesis': mass_flow, 'constant_solid_k_W_mK': solid_k,
           'fin_count': len(boxes), 'flow_area_m2': area, 'channel_gap_mm': gap*1000,
           'velocity_m_s': speed, 'Re': Re, 'Mach_at_inlet': mach,
           'flow_length_over_Dh': length/Dh, 'fan_operating_point_verified': False}
    # Do not silently extrapolate the reused smooth-pipe turbulent correlation.
    if not (3000 <= Re <= 5e6 and .5 <= AIR['air_prandtl'] <= 2000 and mach < .3 and length/Dh >= 10):
        return dict(row, status='outside_selected_correlation_or_low_Mach_domain', heat_W=None)
    result = cooling.method_b({'fixed_boundaries': AIR}, {'open_area_m2': area},
                              p['fin_thickness'], gap*1000, depth*1000, length*1000,
                              {'capture_fraction': 1., 'minor_loss_k': AIR['minor_loss_k']}, mass_flow)
    h = result['nusselt'] * AIR['air_thermal_conductivity_w_mk'] / Dh
    eta = cooling.fin_efficiency(h, p['fin_thickness']*.001, depth, solid_k)
    # Only surfaces bounding internal channels, not every face of the block.
    fin_area, root_area = 4*(n-1)*length*depth, 2*(n-1)*length*gap
    UA = h * (eta*fin_area + root_area)
    C = mass_flow*AIR['air_cp_J_kgK']
    delta = ceiling-AIR['inlet_C']
    q = air_capacity(UA,C,delta)
    return dict(row, status='conditional_straight_channel_screen', heat_W=q, h_W_m2K=h,
                fin_efficiency=eta, UA_W_K=UA, fin_area_m2=fin_area, root_area_m2=root_area,
                air_outlet_C=AIR['inlet_C']+q/C, pressure_drop_Pa=result['total_pressure_drop_pa'],
                fan_shaft_power_W_per_head=result['total_pressure_drop_pa']*mass_flow/AIR['air_density_kg_m3']/AIR['fan_efficiency'],
                constant_inlet_air_overestimate_W=UA*delta-q,
                upwind_relative_errors_8_32_128=[abs(air_capacity(UA,C,delta,n)/q-1) for n in (8,32,128)])


def screens(p, c, old):
    rows = []
    for case in old['mechanics']['force_scenarios']:
        side = case['side']; length = support_positions(p, side)
        beam = point_span(case['rocker_reaction_bound_N'],length,p[side+'_valve_y'],2*p['rocker_pivot_radius'])
        journal_gap = p['carrier_journal_radial_clearance']
        axis_screen = journal_gap+beam['load_point_deflection_mm']
        rows.append({'side':side, 'rpm':case['rpm'], 'mass_kg':case['effective_mass_hypothesis_kg'],
                     'spring_factor':case['spring_force_factor'], 'gas_N':case['adverse_opening_gas_force_N'],
                     'support_span_mm':length, 'G6_midspan_bound_mm':case['shaft_beam_bound']['centre_deflection_mm'],
                     'G7_shaft_only':beam,
                     'shaft_only_below_0p04_mm':beam['load_point_deflection_mm']<c['load_sensitivity']['shaft_axis_deflection_screen_mm'],
                     'journal_geometric_radial_gap_mm':journal_gap,
                     'clearance_plus_shaft_screen_mm':axis_screen,
                     'clearance_plus_shaft_below_0p04_mm':axis_screen<c['load_sensitivity']['shaft_axis_deflection_screen_mm'],
                     'unchanged_forced_lift_contact_loss':not case['no_forced_lift_contact_loss'],
                     'assembly_stiffness_qualified':False})
    configurations = {'G6':p, 'G7':dict(p, **{k:v for k,v in DESIGN.items() if k.startswith('fin_')})}
    thermal = {name:[channel_case(q,m,k) for m,k in itertools.product((.025,.05,.075,.1), (100.,150.,187.))]
               for name,q in configurations.items()}
    duty = old['thermal']['minimum_hypothetical_demand_W']
    for cases in thermal.values():
        for r in cases:
            if r['heat_W'] is not None:
                deficit = max(0,duty-r['heat_W'])
                r['deficit_to_lowest_G6_hypothetical_duty_W']=deficit
                # Energy-only minimum, not an attainable cooling-channel design.
                r['oil_flow_energy_only_minimum_L_min_per_head']=deficit/(850*2000*30)*60000
    return {'shaft_comparison':rows, 'cooling_comparison':thermal,
            'air_properties_and_losses_all_hypotheses':AIR, 'minimum_G6_hypothetical_duty_W':duty,
            'gas_spring_mass_and_lift_inputs_changed':False,
            'material_or_cooling_system_selected':False,
            'thermal_limitations':['hydraulic-diameter smooth-pipe analogy for a rectangular fin channel',
                'uniform fin root ceiling; no head conduction or exhaust bridge map',
                'no bypass, fan map, plenum or bank-to-bank flow distribution',
                'constant assumed air properties, no hot material card',
                'oil-flow minimum excludes heat-transfer resistance and cooler capacity']}


def parts(p):
    import cadquery as cq
    import assembly
    import carrier
    from cadcommon import _cyl
    shapes = assembly.parts(p,0)
    shapes['head'] = carrier.modify_head(p,shapes['head'])
    mounts = carrier.parts(p)
    axes = carrier.axes(p)
    x0 = axes['intake'][0][0]-DESIGN['rib_x_width_mm']/2
    x1 = axes['exhaust'][0][0]+DESIGN['rib_x_width_mm']/2
    z0 = p['carrier_face_height']
    ztop = max(q[0][2] for q in axes.values())+9
    w = DESIGN['centre_wall_mm']
    centre = cq.Solid.makeBox(x1-x0,w,ztop-z0,cq.Vector(x0,-w/2,z0))
    for x in (-p['carrier_mount_x'],p['carrier_mount_x']):
        shapes['head'] = shapes['head'].cut(_cyl([x,0,z0-12],[x,0,z0+1],3))
        centre = centre.cut(_cyl([x,0,z0-1],[x,0,ztop+1],3.3))
        mounts[f'central_mount_bolt_{x:+g}'] = _cyl([x,0,z0-12],[x,0,ztop],3).fuse(_cyl([x,0,ztop],[x,0,ztop+6],5))
    for side,(pivot,cam) in axes.items():
        x,z = pivot[0],pivot[2]
        bore = p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']
        centre = centre.cut(_cyl([x,-w,z],[x,w,z],bore))
        sign = -1 if side=='intake' else 1
        # Accessible journal-feed port; no hose, pump or pressure qualification.
        centre = centre.cut(_cyl([x+sign*20,0,z],[x,0,z],1))
        outer = support_positions(p,side)
        for sy,tag in ((-1,'m'),(1,'p')):
            y = sy*outer; r = DESIGN['rib_width_mm']; bx = DESIGN['rib_x_width_mm']
            bottom = DESIGN['bridge_bottom_mm']
            rib = cq.Solid.makeBox(bx,r,z+9-bottom,cq.Vector(x-bx/2,y-r/2,bottom))
            a,b = sorted((y,sy*p['carrier_end_y']))
            bridge = cq.Solid.makeBox(bx,b-a,DESIGN['bridge_height_mm'],cq.Vector(x-bx/2,a,bottom))
            name = 'carrier_base_'+tag
            mounts[name] = mounts[name].fuse(rib,bridge).cut(_cyl([x,y-r,z],[x,y+r,z],bore))
            feed_z = cam[2]-25
            tool = _cyl([x,y,feed_z],[x,sy*p['carrier_end_y'],feed_z],1).fuse(_cyl([x,y,feed_z],[x,y,z],1))
            mounts[name] = mounts[name].cut(tool).cut(carrier.oil_tools(p,sy,side)).clean()
    mounts['central_diaphragm'] = centre.clean()
    shapes['head'] = shapes['head'].clean()
    shapes.update(mounts)
    return shapes, set(mounts)


def native_bounds(shape):
    """Underlying BRep bounds, independent of cached STL tessellation."""
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped,box,False,False)
    return dict(zip(('xmin','ymin','zmin','xmax','ymax','zmax'),box.Get()))


def run(out):
    import cadquery as cq
    import assembly
    import audit_g6
    import rocker_train
    import components
    p,c = g6.inputs(); old = baseline()
    previous_bounds = native_bounds(components.head(p))
    p['rocker_pivot_radius'] = DESIGN['rocker_pivot_radius']
    numerical = screens(p,c,old)
    p.update({k:v for k,v in DESIGN.items() if k.startswith('fin_')})
    out.mkdir(parents=True,exist_ok=False)
    shapes, added = parts(p)
    pairs = []
    names = list(shapes)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            if a not in added and b not in added: continue
            v = audit_g6.overlap(shapes[a],shapes[b])
            if v>1e-5:pairs.append({'a':a,'b':b,'volume_mm3':v})
    print(json.dumps({'stage':'CAD','interferences':pairs}),flush=True)
    dynamic = []
    supports = ['central_diaphragm','carrier_base_p','carrier_base_m']
    # ponytail: sample rigid rocker cycle; continuous deformable multibody analysis remains required.
    for phi in range(0,720,30):
        for side,sy in layout.VALVES:
            for name,part in rocker_train.moving_parts(p,side,sy,phi).items():
                for support in supports:
                    v = audit_g6.overlap(part,shapes[support])
                    if v>1e-5:dynamic.append({'crank_deg':phi,'side':side,'sy':sy,'part':name,'support':support,'volume_mm3':v})
    export = ['head','central_diaphragm','carrier_base_p']
    voids = {}
    for n in export:
        voids[n] = audit_g6.closed_voids(shapes[n])
        for ext in ('step','stl'):
            cq.exporters.export(cq.Workplane().add(shapes[n]),str(out/(n+'.'+ext)),tolerance=.05,angularTolerance=.15)
    assembly._export(list(shapes.values()),out/'assembly.step')
    half = cq.Solid.makeBox(1000,1000,1000,cq.Vector(-500,p['intake_valve_y'],-500))
    cut = cq.Compound.makeCompound([s.cut(half) for s in shapes.values()]).rotate((0,0,0),(1,0,0),-90)
    cq.exporters.export(cq.Workplane().add(cut),str(out/'section.svg'),opt={'projectionDir':(0,0,-1),'showHidden':False,'strokeWidth':.15,'width':1100,'height':None})
    from unittest.mock import patch
    with patch.object(components,'head',return_value=shapes['head']):
        compression = assembly.compression_ratio(p)
    paths = list(HERE.glob('*.py'))+list((HERE/'cad').glob('*.py'))+[F39,BASELINE,HERE/'g6-inputs.json']
    result = {'classification':'G7_geometric_candidate_and_reduced_screens_not_qualified',
              'manufacturing_authorized':False,'engine_start_authorized':False,
              'design_hypotheses_mm':DESIGN,'values':p,'baseline_sha256':digest(BASELINE),
              'CAD_interferences':pairs,'sampled_rocker_interferences':dynamic,
              'rocker_crank_samples_deg':list(range(0,720,30)),
              'BRep_valid':{n:assembly.brep_valid(s) for n,s in shapes.items()},
              'solid_counts':{n:len(s.Solids()) for n,s in shapes.items()},
              'head_volume_mm3':shapes['head'].Volume(),
              'nominal_rocker_boss_radial_ligament_mm':p['rocker_boss_radius']-p['rocker_pivot_radius']-p['rocker_radial_clearance'],
              'G6_native_head_bounds_mm':previous_bounds, 'G7_native_head_bounds_mm':native_bounds(shapes['head']),
              'head_bounds_unchanged':all(abs(native_bounds(shapes['head'])[a]-v)<1e-6 for a,v in previous_bounds.items()),
              'compression':compression,'closed_void_checks':voids,'screens':numerical,
              'limitations':['central diaphragm and rib/head compliance not solved',
                  'unselected journal gap alone consumes the 0.04 mm axis-motion screen budget',
                  'no bearing fit, journal oil-film or preload/thread qualification',
                  'central diaphragm mounting bolts are envelopes, not selected fasteners',
                  'sampled rocker poses are not a complete dynamic collision proof',
                  'denser fins need a shroud and flow distribution not present in CAD'],
              'software':{'cadquery':cq.__version__},
              'source_sha256':{str(f.relative_to(layout.REPO)):digest(f) for f in paths},
              'files_sha256':{f.name:digest(f) for f in out.iterdir()}}
    (out/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'stage':'done','components':len(shapes),'CAD_interferences':len(pairs),'sampled_rocker_interferences':len(dynamic)}),flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    run(parser.parse_args().output)
