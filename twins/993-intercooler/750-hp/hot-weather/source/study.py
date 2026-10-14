#!/usr/bin/env python3
"""Inverse fan sizing and idealized pressure-wall screen; no engineering release."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];STUDY=ROOT.parent
sys.path.insert(0,str(STUDY/'architecture/source'))
from compare import mixed_case, root, fan_pressure, geometry


def validate(a):
    if any(a['acceptance'].values()):raise ValueError('Research cannot grant acceptance')
    def walk(x):
        if isinstance(x,dict):
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
        elif isinstance(x,(int,float)) and not isinstance(x,bool):
            if not math.isfinite(x) or x<0:raise ValueError('Invalid numeric input')
    walk(a)
    if a['charge_target_c']<=a['ambient_c'] or min(a['duct_areas_m2'])<=0:raise ValueError('Impossible target or duct')
    p=a['pressure']
    if min(p.values())<=0 or p['exploratory_proof_gauge_pa']<p['service_gauge_pa'] or p['rib_pitch_mm']<=p['rib_thickness_mm']:raise ValueError('Invalid pressure geometry')


def state(g,m,area,position,ambient,b,a,scenario,recirculation=0):
    if m<=0 or area<=0 or position not in ('upstream','downstream') or not 0<=recirculation<.5:raise ValueError('Invalid operating input')
    b=dict(b,compressor_inlet_c=ambient+a['compressor_inlet_rise_k'])
    rho0=b['ambient_pressure_pa']/(b['gas_constant_j_kg_k']*(ambient+273.15));tin=ambient
    for _ in range(40):
        # The historical helper's required-UA diagnostic rejects Tin >= its target; only its heat-transfer solution is used here.
        local=dict(b,charge_outlet_target_c=max(b['charge_outlet_target_c'],tin+1))
        c=mixed_case(g,scenario,local,m,tin)
        hotrho=b['ambient_pressure_pa']/(b['gas_constant_j_kg_k']*(c['cold_outlet_c']+273.15))
        rhofan=rho0 if position=='upstream' else hotrho
        # shortcut: K=3 is referred to ambient-volume velocity; replace with measured inlet/outlet duct losses.
        dp=c['cold']['pressure_drop_pa']+a['duct_loss_k']*m*m/(2*rho0*area*area)
        power=dp*m/rhofan/a['cooler_fan']['efficiency'];heat=power/(m*b['cold_cp_j_kg_k'])
        exhaust=c['cold_outlet_c']+(heat if position=='downstream' else 0)
        new=ambient+recirculation*(exhaust-ambient)+(heat if position=='upstream' else 0)
        if abs(new-tin)<1e-6:break
        tin=new
    else:raise ArithmeticError('Thermal recirculation iteration failed')
    fan=a['cooler_fan'];q=m/rhofan
    speed=math.sqrt(dp/(fan['shutoff_pa']*rhofan/a['fan_density_reference_kg_m3'])+(q/fan['free_flow_m3_s'])**2)
    ef=a['engine_fan'];k=a['engine_reference_loss_pa']/a['engine_reference_flow_kg_s']**2*a['fan_density_reference_kg_m3']/rho0
    em=root(lambda em:fan_pressure(em,rho0,ef,a)-k*em*em,.01,rho0*ef['free_flow_m3_s'])
    ep=k*em**3/rho0/ef['efficiency']
    port_area=math.pi*(a['charge_pipe_id_mm']/1000)**2/4
    pressure=b['ambient_pressure_pa']*scenario['compressor_pressure_ratio'];mh=scenario['charge_mass_flow_kg_s']
    rho_in=pressure/(b['gas_constant_j_kg_k']*(c['charge_inlet_c']+273.15));rho_out=pressure/(b['gas_constant_j_kg_k']*(c['charge_outlet_c']+273.15))
    port_loss=.5*a['charge_port_loss_k_each']*((mh/2)**2/(rho_in*port_area**2)+mh**2/(rho_out*(2*port_area)**2))
    return {'ambient_c':ambient,'compressor_inlet_c':ambient+a['compressor_inlet_rise_k'],'compressor_outlet_c':c['charge_inlet_c'],'fan_position':position,'duct_area_m2':area,'cooling_flow_kg_s':m,'cooler_speed_ratio':speed,
            'charge_outlet_c':c['charge_outlet_c'],'cooler_inlet_c':tin,'cooler_exhaust_c':exhaust,'recirculation_fraction':recirculation,
            'cooler_shaft_power_w':power,'engine_shaft_power_w':ep,'total_shaft_power_w':power+ep,'engine_flow_kg_s':em,'engine_inlet_c':ambient+ep/(em*b['cold_cp_j_kg_k']),
            'fan_total_pressure_pa':dp,'fan_volume_flow_m3_s':q,'fan_density_kg_m3':rhofan,'core_pressure_loss_pa':c['cold']['pressure_drop_pa'],'charge_pressure_loss_pa':c['hot']['pressure_drop_pa']+port_loss,'charge_port_loss_pa':port_loss,
            'heat_rejection_w':c['heat_rejection_w'],'energy_residual_w':c['energy_residual_w'],'correlation_admissible':c['correlation_screen_admissible'],'physical_performance_accepted':False}


def required(g,area,position,ambient,b,a,s,target):
    previous=None
    for m in [1+i*.25 for i in range(25)]:
        c=state(g,m,area,position,ambient,b,a,s)
        if c['charge_outlet_c']<=target:
            if previous is None:return c
            lo,hi=previous,m
            for _ in range(25):
                mid=(lo+hi)/2
                if state(g,mid,area,position,ambient,b,a,s)['charge_outlet_c']>target:lo=mid
                else:hi=mid
            return state(g,hi,area,position,ambient,b,a,s)
        previous=m
    return None


def fixed_speed(g,selected,ambient,b,a,s,recirculation=0):
    n=selected['cooler_speed_ratio'];area=selected['duct_area_m2'];pos=selected['fan_position']
    m=root(lambda m:n-state(g,m,area,pos,ambient,b,a,s,recirculation)['cooler_speed_ratio'],.5,8)
    return state(g,m,area,pos,ambient,b,a,s,recirculation)


def wall_screen(p,depth,span,header_depth):
    rows=[];t=p['wall_mm']/1000;young=p['hot_elastic_modulus_pa']
    for pressure in [p['service_gauge_pa'],p['exploratory_proof_gauge_pa']]:
        for name,l in [('old_flat_reference',p['comparison_flat_span_mm']/1000),('ribbed_panel',p['rib_pitch_mm']/1000)]:
            stress=.75*pressure*(l/t)**2;deflection=5*pressure*l**4/(32*young*t**3)
            rows.append({'case':name,'pressure_pa':pressure,'stress_pa':stress,'deflection_mm':deflection*1000,'small_deflection_admissible':deflection/t<.5,'assumed_allowable_pass':stress<=p['assumed_allowable_pa'] and deflection/t<.5})
    return {'method':'simply supported unit-width strip, continuous ideal supports; not a header finite-element analysis','cases':rows,
            'per_bank_interface_force_at_proof_n':p['exploratory_proof_gauge_pa']*depth*span/1e6,
            'rib_tributary_force_at_proof_n':p['exploratory_proof_gauge_pa']*depth*p['rib_pitch_mm']/1e6,
            'rib_open_area_fraction':max(0,(header_depth-2*p['wall_mm']-2*p['rib_edge_mm'])*(depth-2*p['wall_mm']-2*p['rib_edge_mm'])/((header_depth-2*p['wall_mm'])*(depth-2*p['wall_mm']))),
            'pressure_qualified':False,'support_and_rib_stresses_resolved':False}


def run(output):
    if output.exists():raise FileExistsError(output)
    config=json.loads((ROOT/'assumptions.json').read_text());validate(config)
    a=json.loads((STUDY/'architecture/assumptions.json').read_text());a.update({k:config[k] for k in ['compressor_inlet_rise_k','charge_port_loss_k_each']});b=json.loads((STUDY/'requirements.json').read_text())['assumed'];s=b['scenarios'][-1]
    rows=[];best=None
    for face,depth,cp,t in itertools.product(config['faces_mm'],config['depths_mm'],config['cold_pitches_mm'],config['fin_mm']):
        g=geometry((*face,depth,3,6,1.5,cp,t),.4);g.update(fin_family='offset',strip_length_mm=10,charge_parallel_banks=2)
        mass=g['metal_volume_m3']*b['metal_density_kg_m3']
        for area,pos in itertools.product(config['duct_areas_m2'],config['fan_positions']):
            c=required(g,area,pos,config['ambient_c'],b,a,s,config['charge_target_c'])
            passed=c is not None and c['correlation_admissible'] and c['total_shaft_power_w']<=config['total_shaft_budget_w'] and c['cooler_speed_ratio']<=config['max_cooler_speed_ratio'] and c['charge_pressure_loss_pa']<=b['charge_pressure_loss_budget_pa'] and c['engine_flow_kg_s']>=a['engine_minimum_flow_kg_s'] and c['engine_inlet_c']<=a['engine_inlet_limit_c']
            rows.append({**g,'core_mass_kg':mass,'duct_area_m2':area,'fan_position':pos,'target_reachable':c is not None,'passes':passed,'required_power_w':c['total_shaft_power_w'] if c else None,'speed_ratio':c['cooler_speed_ratio'] if c else None})
            if passed and (best is None or (mass,c['total_shaft_power_w'])<(best['core_mass_kg'],best['design_point']['total_shaft_power_w'])):best={'geometry':g,'core_mass_kg':mass,'design_point':c}
    result={'status':'uncalibrated_hot_weather_inverse_fan_screen','case_count':len(rows),'passing_count':sum(x['passes'] for x in rows),'selected':best,'assumptions':config,'acceptance':config['acceptance']}
    if best:
        g=best['geometry'];selected=best['design_point']
        result['sensitivity']=[fixed_speed(g,selected,temp,b,a,s,recirc) for temp,recirc in itertools.product([35,45,50],config['recirculation_sensitivity'])]
        result['duty_cases']=[fixed_speed(g,selected,45,b,a,scenario) for scenario in b['scenarios']]
        result['wall_screen']=wall_screen(config['pressure'],g['depth_mm'],g['span_mm'],a['header_depth_mm'])
        result['controlled_schedule']=[{'ambient_c':temp,'point':required(g,selected['duct_area_m2'],selected['fan_position'],temp,b,a,s,config['charge_target_c'])} for temp in [35,45,50]]
        p=config['pressure'];pitch=p['rib_pitch_mm'];edge=p['rib_edge_mm'];wall=p['wall_mm']
        ai=(a['header_depth_mm']-2*wall-2*edge)*(g['depth_mm']-2*wall-2*edge)/1e6
        ao=(a['bank_gap_mm']-2*wall-2*edge)*(g['depth_mm']-2*wall-2*edge)/1e6
        ni=math.ceil(g['span_mm']/2/pitch);no=math.ceil(g['span_mm']/pitch);mh=s['charge_mass_flow_kg_s']
        pressure=b['ambient_pressure_pa']*s['compressor_pressure_ratio']
        rhoi=pressure/(b['gas_constant_j_kg_k']*(selected['compressor_outlet_c']+273.15));rhoo=pressure/(b['gas_constant_j_kg_k']*(selected['charge_outlet_c']+273.15))
        rib_loss=sum((mh/4*(1-i/ni))**2 for i in range(1,ni))/(2*rhoi*ai**2)+sum((mh*(1-i/no))**2 for i in range(1,no))/(2*rhoo*ao**2)
        result['rib_loss_sensitivity']=[{'assumed_k_per_web':k,'additional_loss_pa':k*rib_loss,'total_charge_loss_pa':selected['charge_pressure_loss_pa']+k*rib_loss,'within_10kpa_budget':selected['charge_pressure_loss_pa']+k*rib_loss<=b['charge_pressure_loss_budget_pa']} for k in [.5,1,2]]
        result['rib_loss_method']='Uniform distributed core takeoff; inlet splits into two longitudinal half-manifolds; common outlet collects both banks. K per web assumed, no CFD calibration.'

        result['layout_input']={'selected':best,'assumptions':a,'pressure':config['pressure'],'acceptance':config['acceptance']}
    output.mkdir(parents=True)
    with (output/'sweep.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    paths=[Path(__file__),ROOT/'assumptions.json',STUDY/'architecture/source/compare.py',STUDY/'architecture/assumptions.json',STUDY/'source/size_core.py',STUDY/'requirements.json']
    result['source_hashes']={str(p.relative_to(STUDY)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};result['sweep_sha256']=hashlib.sha256((output/'sweep.csv').read_bytes()).hexdigest()
    (output/'study.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'cases':len(rows),'passed':result['passing_count'],'selected':best}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
