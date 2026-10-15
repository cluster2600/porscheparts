#!/usr/bin/env python3
"""Assumed fan/system intersections, with retained historical core correlations."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parent
sys.path.insert(0,str(STUDY/'source'))
from size_core import evaluate, geometry


def validate(a):
    def walk(v):
        if isinstance(v,dict):
            for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
        elif isinstance(v,(int,float)) and not isinstance(v,bool):
            if not math.isfinite(v) or v<=0:raise ValueError('Expected positive finite assumption')
    walk(a)
    if any(a['acceptance'].values()):raise ValueError('Assumptions cannot grant acceptance')
    for key in ['cooler_fan','engine_fan']:
        if a[key]['efficiency']>1:raise ValueError('Invalid efficiency')
    if a['header_wall_mm']<4*a['voxel_mm'] or a['header_depth_mm']<=2*a['header_wall_mm']:raise ValueError('Unresolved header')


def root(fn,lo,hi):
    if fn(lo)<0 or fn(hi)>0:raise ValueError('Unbracketed operating point')
    for _ in range(32):
        mid=(lo+hi)/2
        if fn(mid)>0:lo=mid
        else:hi=mid
    return (lo+hi)/2


def fan_pressure(mass,rho,fan,a,speed=1):
    q=mass/rho
    return fan['shutoff_pa']*(rho/a['fan_density_reference_kg_m3'])*speed**2*(1-(q/(fan['free_flow_m3_s']*speed))**2)


def mixed_case(g,s,b,mass,ambient):
    b=dict(b,ambient_c=ambient)
    c=evaluate(g,s,b,cooling_mass=mass,hfactor=.75,ffactor=2)
    ch=s['charge_mass_flow_kg_s']*b['hot_cp_j_kg_k'];cc=mass*b['cold_cp_j_kg_k']
    cr=min(ch,cc)/max(ch,cc);ntu=c['ua_w_k']/min(ch,cc)
    eps=1/(1/(-math.expm1(-ntu))+cr/(-math.expm1(-cr*ntu))-1/ntu)
    q=eps*min(ch,cc)*(c['charge_inlet_c']-ambient)
    # shortcut: the mixedness bound retains UA and pressure losses from the unmixed property iteration; replace with calibrated CHT.
    return {**c,'unmixed_outlet_c':c['charge_outlet_c'],'charge_outlet_c':c['charge_inlet_c']-q/ch,
            'cold_outlet_c':ambient+q/cc,'heat_rejection_w':q,'energy_residual_w':q-cc*((ambient+q/cc)-ambient)}


def operating(g,s,b,a,architecture,ambient=None,speed=1):
    ambient=a['ambient_design_c'] if ambient is None else ambient
    rho=b['ambient_pressure_pa']/(b['gas_constant_j_kg_k']*(ambient+273.15))
    fan=a['cooler_fan'] if architecture=='separate' else a['engine_fan']
    maxmass=rho*fan['free_flow_m3_s']*speed
    def engine_dp(m):return a['engine_reference_loss_pa']*(m/a['engine_reference_flow_kg_s'])**2*a['fan_density_reference_kg_m3']/rho
    def state(m):
        preheat=0
        for _ in range(20):
            c=mixed_case(g,s,b,m,ambient+preheat)
            dp=c['cold']['pressure_drop_pa']+a['duct_loss_k']*(m/rho/a['cooler_duct_area_m2'])**2*rho/2
            if architecture=='serial':
                engine=m;pressure=dp+engine_dp(m)*(c['cold_outlet_c']+273.15)/(ambient+273.15);total=m
            elif architecture=='shared_bypass':
                engine=a['engine_reference_flow_kg_s']*math.sqrt(dp/a['engine_reference_loss_pa']*rho/a['fan_density_reference_kg_m3']*(ambient+273.15)/(ambient+preheat+273.15));pressure=dp;total=m+engine
            elif architecture=='separate':engine=0;pressure=dp;total=m
            else:raise ValueError('Unknown architecture')
            new=pressure/(rho*fan['efficiency']*b['cold_cp_j_kg_k'])
            if abs(new-preheat)<1e-6:break
            preheat=new
        else:raise ArithmeticError('Fan preheat iteration failed')
        return c,pressure,engine,total,new
    def residual(m):
        c,dp,engine,total,preheat=state(m)
        return fan_pressure(total,rho,fan,a,speed)-dp
    m=root(residual,.1,maxmass)
    c,dp,engine,total,preheat=state(m)
    engine_power=0
    if architecture=='separate':
        ef=a['engine_fan'];emax=rho*ef['free_flow_m3_s']*speed
        engine=root(lambda m:fan_pressure(m,rho,ef,a,speed)-engine_dp(m),.01,emax)
        engine_power=engine_dp(engine)*engine/rho/ef['efficiency']
    power=dp*total/rho/fan['efficiency']+engine_power
    engine_temp=c['cold_outlet_c'] if architecture=='serial' else ambient+(engine_power/(engine*b['cold_cp_j_kg_k']) if architecture=='separate' else preheat)
    passed=c['correlation_screen_admissible'] and c['charge_outlet_c']<=a['charge_target_c']-a['design_margin_k'] and c['hot']['pressure_drop_pa']<=b['charge_pressure_loss_budget_pa'] and engine>=a['engine_minimum_flow_kg_s'] and engine_temp<=a['engine_inlet_limit_c'] and power<=a['total_shaft_power_budget_w']
    return {'architecture':architecture,'scenario':s['id'],'ambient_c':ambient,'speed_ratio':speed,'cooling_flow_kg_s':m,'engine_flow_kg_s':engine,'engine_inlet_c':engine_temp,
            'fan_preheat_k':preheat,'total_shaft_power_w':power,'fan_total_pressure_pa':dp,'fan_pressure_residual_pa':fan_pressure(total,rho,fan,a,speed)-dp,
            'charge_outlet_c':c['charge_outlet_c'],'unmixed_outlet_c':c['unmixed_outlet_c'],'heat_rejection_w':c['heat_rejection_w'],
            'hot_pressure_loss_pa':c['hot']['pressure_drop_pa'],'core_cold_pressure_loss_pa':c['cold']['pressure_drop_pa'],
            'correlation_admissible':c['correlation_screen_admissible'],'energy_residual_w':c['energy_residual_w'],
            'assumed_constraints_pass':passed,'physical_performance_accepted':False}


def run(output):
    if output.exists():raise FileExistsError(output)
    a=json.loads((ROOT/'assumptions.json').read_text());validate(a)
    b=json.loads((STUDY/'requirements.json').read_text())['assumed'];rows=[];best=None
    for face,depth,hp,cp,t,wall in itertools.product(*a['search'].values()):
        g=geometry((*face,depth,3,6,hp,cp,t),wall);g.update(fin_family='offset',strip_length_mm=10,charge_parallel_banks=2)
        bounds=[g['width_mm']+a['bank_gap_mm']+2*a['header_depth_mm'],g['span_mm'],g['depth_mm']]
        if any(x>limit for x,limit in zip(bounds,a['available_envelope_mm'])):continue
        cases=[operating(g,s,b,a,'separate') for s in b['scenarios']]
        mass=g['metal_volume_m3']*b['metal_density_kg_m3'];passed=all(c['assumed_constraints_pass'] for c in cases)
        rows.append({**g,'core_mass_kg':mass,'passes':passed,'max_charge_c':max(c['charge_outlet_c'] for c in cases),'max_power_w':max(c['total_shaft_power_w'] for c in cases)})
        if passed and (best is None or mass<best['core_mass_kg']):best={'geometry':g,'core_mass_kg':mass,'packaging_bounds_mm':bounds,'design_cases':cases}
    if best is None:raise ValueError('No candidate satisfies assumed architecture requirements')
    g=best['geometry'];comparisons=[operating(g,s,b,a,arch) for arch in ['serial','shared_bypass','separate'] for s in b['scenarios']]
    sensitivities=[operating(g,b['scenarios'][-1],b,a,'separate',ambient=temp,speed=speed) for temp,speed in itertools.product(a['ambient_sensitivity_c'],a['fan_speed_ratios'])]
    output.mkdir(parents=True)
    with (output/'sweep.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    paths=[ROOT/'assumptions.json',Path(__file__),STUDY/'requirements.json',STUDY/'source/size_core.py']
    result={'status':'hypothetical_fan_coupled_architecture_screen','candidate_count':len(rows),'passing_count':sum(r['passes'] for r in rows),'selected':best,'architecture_comparison':comparisons,'sensitivity':sensitivities,'assumptions':a,
            'limitations':['Assumed upstream pusher fan curves; no ram pressure credited; full shaft work conservatively added as inlet-air heat.','Both-mixed bound retains UA and hydraulic properties from the historical unmixed iteration.','Equal charge-bank sharing, inlet losses and no exhaust recirculation assumed.','Shaft power excludes motor/drive inefficiency; electrical rating is not determined.','Headers and core envelopes are packaging studies, not sealed full-core geometry.'],
            'acceptance':a['acceptance'],'source_hashes':{str(p.relative_to(STUDY)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'sweep_sha256':hashlib.sha256((output/'sweep.csv').read_bytes()).hexdigest()}
    (output/'comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'cases':len(rows),'passes':result['passing_count'],'selected':best}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();run(args.output)
