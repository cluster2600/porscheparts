#!/usr/bin/env python3
"""Conditional blade-element/momentum and beam screening, not a calibrated fan map."""
import argparse
import copy
import json
import math
from pathlib import Path


def screen(p,shaft_power_W=6000,*,rho=1.2,lift_slope=5.7,cl_limit=1.1,cd0=.025,
           drag_quadratic=.04,gap_loss_coefficient=5,friction_torque_Nm=.63):
    R=p['diameter_mm']/2000;root=R*p['blade_root_radius_ratio'];carrier=R*p['carrier_radius_ratio']
    A=math.pi*(R*R-carrier*carrier);B=p['blade_count'];omega0=6000*math.pi/30
    bins=64;dr=(R-carrier)/bins
    leakage=(1-gap_loss_coefficient*p['tip_gap_ratio'])**2
    if not 0<leakage<=1:raise ValueError('Leakage surrogate outside validity')
    def elements(v):
        rows=[]
        for i in range(bins):
            r=carrier+(i+.5)*dr;fraction=(r-root)/(R-root)
            chord=R*(p['root_chord_ratio']+(p['tip_chord_ratio']-p['root_chord_ratio'])*fraction)
            beta=math.radians(p['root_pitch_deg']+p['tip_twist_deg']*fraction)
            phi=math.atan2(v,omega0*r);alpha=beta-phi+2*R*p['camber_ratio']/chord
            cl=max(-cl_limit,min(cl_limit,lift_slope*alpha));cd=cd0+drag_quadratic*cl*cl
            # Prandtl finite-blade factor; assumed uniform induced velocity.
            exponent=B*(R-r)/(2*r*max(math.sin(phi),1e-6))
            loss=2/math.pi*math.acos(math.exp(-min(exponent,700)))
            dynamic=.5*rho*((omega0*r)**2+v*v)*B*chord*dr*loss
            thrust=dynamic*(cl*math.cos(phi)-cd*math.sin(phi))
            torque=dynamic*(cl*math.sin(phi)+cd*math.cos(phi))*r
            rows.append({'r':r,'chord':chord,'alpha_deg':math.degrees(alpha),'thrust':thrust,'torque':torque})
        return rows
    low=0.;high=omega0*R*2
    for _ in range(44):
        v=(low+high)/2;rows=elements(v)
        residual=leakage*sum(row['thrust'] for row in rows)-2*rho*A*v*v
        if residual>0:low=v
        else:high=v
    v0=(low+high)/2;rows=elements(v0);rotor_power0=omega0*sum(row['torque'] for row in rows)
    if rotor_power0<=0:raise ValueError('No positive-power propulsive solution')
    low=0.;high=5000.
    for _ in range(48):
        omega=(low+high)/2
        power=rotor_power0*(omega/omega0)**3+friction_torque_Nm*omega
        if power<shaft_power_W:low=omega
        else:high=omega
    omega=(low+high)/2;scale=omega/omega0;v=v0*scale
    flow=A*v;pressure=2*rho*v*v
    alpha_flags=sum(abs(row['alpha_deg'])>12 for row in rows)/len(rows)
    # Per-blade cantilever estimate; no contact, hub-notch, thermal or fatigue model.
    t=R*p['blade_thickness_ratio'];croot=R*p['root_chord_ratio']
    material_rho=2700.;E=70e9;drr=(R-root)/128
    radial_force=0.;blade_mass=0.
    mean_t=t*(.55+.45*2/math.pi)
    for i in range(128):
        r=root+(i+.5)*drr;fraction=(r-root)/(R-root)
        chord=R*(p['root_chord_ratio']+(p['tip_chord_ratio']-p['root_chord_ratio'])*fraction)
        mass=material_rho*chord*mean_t*drr
        blade_mass+=mass;radial_force+=mass*omega*omega*r
    bending_moment=sum(row['thrust']*scale*scale*(row['r']-root) for row in rows)/B
    axial_stress=radial_force/(croot*mean_t)
    bending_stress=6*bending_moment/(croot*t*t)
    span=R-root;I=croot*t**3/12;cross_section=croot*t
    beam_hz=1.875104**2/(2*math.pi*span*span)*math.sqrt(E*I/(material_rho*cross_section))
    # Four illustrative downstream resistances; values are sensitivity assumptions.
    resistances=[1.,1.25,1.5,1.8];weights=[1/math.sqrt(k) for k in resistances]
    branch_fractions=[w/sum(weights) for w in weights]
    return {'configuration_id':p['configuration_id'],'diameter_mm_assumed':p['diameter_mm'],
            'shaft_power_W_assumed':shaft_power_W,'fan_rpm_screen':omega*30/math.pi,
            'flow_m3_s_screen':flow,'static_pressure_Pa_screen':pressure,
            'useful_air_power_W_screen':pressure*flow,'shaft_to_air_efficiency_screen':pressure*flow/shaft_power_W,
            'tip_speed_m_s':omega*R,'tip_mach_assuming_343_m_s':omega*R/343,
            'drag_and_gap_model':{'lift_slope_per_rad':lift_slope,'cl_limit':cl_limit,'Cd0':cd0,
                                  'drag_quadratic':drag_quadratic,'gap_loss_coefficient':gap_loss_coefficient,
                                  'friction_torque_Nm':friction_torque_Nm},
            'radial_sections_over_12deg_incidence_fraction':alpha_flags,
            'beam_stress_MPa_screen':(axial_stress+bending_stress)/1e6,
            'beam_centrifugal_stress_MPa_screen':axial_stress/1e6,'beam_aero_bending_stress_MPa_screen':bending_stress/1e6,
            'per_blade_mass_kg_screen':blade_mass,'cantilever_first_frequency_Hz_screen':beam_hz,
            'blade_passing_frequency_Hz':B*omega/(2*math.pi),
            'radial_thrust_density_not_installed_air_distribution':[
                {'radius_ratio':row['r']/R,'blade_incidence_deg':row['alpha_deg'],
                 'relative_annular_thrust':row['thrust']/sum(x['thrust'] for x in rows)} for row in rows],
            'illustrative_four_branch_flow_fractions':branch_fractions,
            'branch_resistances_assumed_relative':resistances,
            'validity_flags':{'polar_measured':False,'boundary_conditions_measured':False,'tip_mach_above_0p3':omega*R/343>.3,
                              'sections_outside_small_angle_polar':alpha_flags>0,'CFD_or_FEM_result':False,
                              'physical_validation_established':False,'manufacturing_authorized':False}}


def evaluate(reference):
    definitions=[('R0',{}),('V1_tip_unloading',{'tip_twist_deg':reference['tip_twist_deg']-7}),
                 ('V2_lower_collective_pitch',{'root_pitch_deg':reference['root_pitch_deg']-6}),
                 ('V3_tighter_clearance',{'tip_gap_ratio':reference['tip_gap_ratio']/2}),
                 ('V4_thicker_blade',{'blade_thickness_ratio':reference['blade_thickness_ratio']*1.2})]
    variants=[]
    for name,change in definitions:
        p=copy.deepcopy(reference);p.update(change);p['configuration_id']=reference['configuration_id']+'_'+name
        variants.append({'variant':name,'changes':change,'parameters':p,'result':screen(p)})
    sensitivity=[]
    for label,change,kwargs in [
        ('diameter_low',{'diameter_mm':reference['diameter_mm']*.89},{}),
        ('diameter_high',{'diameter_mm':reference['diameter_mm']*1.11},{}),
        ('polar_low_lift',{}, {'lift_slope':4.0,'cl_limit':.8,'cd0':.04}),
        ('polar_high_lift',{}, {'lift_slope':6.3,'cl_limit':1.3,'cd0':.015}),
        ('clearance_loss_low',{}, {'gap_loss_coefficient':2}),
        ('clearance_loss_high',{}, {'gap_loss_coefficient':10})]:
        p=copy.deepcopy(reference);p.update(change);sensitivity.append({'case':label,'changes':change,'result':screen(p,**kwargs)})
    for item in variants[1:]:
        base=variants[0]['result'];result=item['result']
        item['relative_to_R0_percent']={key:100*(result[key]/base[key]-1) for key in
             ['flow_m3_s_screen','static_pressure_Pa_screen','shaft_to_air_efficiency_screen','beam_stress_MPa_screen','cantilever_first_frequency_Hz_screen']}
    # Two reported EB replica points used only to expose admissible power-model choices.
    cubic_hp=(32-3*1.5)/24;linear_hp=1.5-cubic_hp
    return {'status':'first_order_conditional_screen_no_physical_qualification',
            'reference_configuration':reference['configuration_id'],'comparison_basis':'Same assumed 6000 W total shaft input, air density 1.2 kg/m3 and common polar; uniform disk induction',
            'method':'Blade elements + static actuator momentum + finite-blade loss, explicit gap-loss surrogate and linear drive friction. Beam screening separately assumes aluminium 2700kg/m3 / 70GPa.',
            'dominant_uncertainties':['absolute scale','profile and stall polar','hub/shroud blockage','inlet and downstream resistance','drive friction','blade root geometry and supports'],
            'variants':variants,'sensitivities':sensitivity,
            'reported_EB_replica_power_context':{'source_ledger_ids':['P039','P040','P041'],
                'reported_points':[[4000,1.5],[12000,32]],'units_as_reported':['fan rpm','hp, standard not resolved'],
                'two_point_power_law_exponent':math.log(32/1.5)/math.log(3),
                'cubic_plus_linear_hp_at_rpm_over_4000':{'cubic':cubic_hp,'linear':linear_hp},
                'fit_at_8000fan_rpm_hp':8*cubic_hp+2*linear_hp,
                'mechanical_hp_assumption_W':745.6998715822702,'metric_PS_W':735.49875,
                'transfer_to_factory_or_scan_geometry_calibrated':False},
            'manufacturing_scope':'Geometry access, thickness and cantilever screening only; no machine, powder, thermal history, supports, residual stress or process qualification',
            'automatic_model_admission':False,'physical_validation_established':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('parameters',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();result=evaluate(json.loads(args.parameters.read_text()));args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{'variant':v['variant'],'rpm':round(v['result']['fan_rpm_screen']),
                      'flow_m3_s':round(v['result']['flow_m3_s_screen'],3),'pressure_Pa':round(v['result']['static_pressure_Pa_screen']),
                      'efficiency':round(v['result']['shaft_to_air_efficiency_screen'],3),'beam_stress_MPa':round(v['result']['beam_stress_MPa_screen'],1)} for v in result['variants']],indent=2))
