#!/usr/bin/env python3
"""Crossflow plain-fin sizing screen; no calibrated or manufacturing acceptance."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]


def validate(card):
    def walk(value):
        if isinstance(value, dict):
            for v in value.values(): walk(v)
        elif isinstance(value, list):
            for v in value: walk(v)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value) or value <= 0: raise ValueError('Expected finite positive input')
    walk(card)
    if any(card['acceptance'].values()): raise ValueError('Uncalibrated study cannot grant acceptance')
    a = card['assumed']
    if not a['ambient_c'] < a['charge_outlet_target_c'] < 150: raise ValueError('Invalid temperature target')
    if not 0 < a['heat_transfer_multiplier_stress'] <= 1 or a['friction_multiplier_stress'] < 1: raise ValueError('Invalid stress bounds')
    for search in [card['search'],card['offset_search']]:
        if min(search['fin_mm']) < 4*a['coupon_voxel_mm'] or min(search['hot_pitch_mm']+search['cold_pitch_mm']) <= max(search['fin_mm']): raise ValueError('Unresolved or blocked fin geometry')
    for s in a['scenarios']:
        if s['compressor_pressure_ratio'] <= 1 or not 0 < s['compressor_efficiency'] <= 1: raise ValueError('Invalid compressor state')
    if a['wall_mm'] < 4*a['coupon_voxel_mm'] or min(card['search']['fin_mm']) < 4*a['coupon_voxel_mm']: raise ValueError('Unresolved walls')
    if min(card['search']['hot_pitch_mm'] + card['search']['cold_pitch_mm']) <= max(card['search']['fin_mm']): raise ValueError('Blocked passage')


def effectiveness(ntu, ratio):
    if not math.isfinite(ntu) or not math.isfinite(ratio) or ntu < 0 or not 0 <= ratio <= 1: raise ValueError('Invalid NTU or capacity ratio')
    if ntu == 0: return 0.0
    if ratio < 1e-8: return -math.expm1(-ntu)
    return -math.expm1(ntu**0.22 / ratio * math.expm1(-ratio*ntu**0.78))


def required_ua(ch, cc, hot, cold, target):
    if min(ch, cc) <= 0 or not cold < target < hot: raise ValueError('Impossible duty')
    required = ch*(hot-target)/(min(ch,cc)*(hot-cold))
    if required >= 1: return None
    lo, hi = 0., 10000.
    ratio = min(ch,cc)/max(ch,cc)
    for _ in range(70):
        mid=(lo+hi)/2
        if effectiveness(mid,ratio) < required: lo=mid
        else: hi=mid
    return (lo+hi)/2*min(ch,cc)


def crossflow_grid(ua, ch, cc, th, tc, n):
    """Independent conservative cell balance; uniform UA, unmixed streams."""
    hot=[th]*n; cold_out=[]; conductance=ua/(n*n)
    for _ in range(n):
        cold=tc
        for j in range(n):
            q=(hot[j]-cold)/(1/conductance+n/(2*ch)+n/(2*cc))
            hot[j]-=q*n/ch; cold+=q*n/cc
        cold_out.append(cold)
    return {'cells_per_direction':n,'charge_outlet_c':sum(hot)/n,
            'cold_outlet_c':sum(cold_out)/n,'heat_hot_w':ch*(th-sum(hot)/n),
            'energy_residual_w':ch*(th-sum(hot)/n)-cc*(sum(cold_out)/n-tc)}


def properties(temp, pressure, cp, gas):
    # shortcut: ideal dry air with Sutherland viscosity and Pr=0.71; replace with measured humid charge properties.
    mu=1.716e-5*(temp/273.15)**1.5*(273.15+111)/(temp+111)
    return pressure/(gas*temp), mu, mu*cp/0.71


def duct(gap, clear, length, channels, mass, temp, pressure, cp, a, hfactor, ffactor, entry_k, fin=0., strip=0.):
    area=gap*clear*channels; dh=2*gap*clear/(gap+clear)
    if strip: dh=4*clear*gap*strip/(2*(clear*strip+gap*strip+fin*gap)+fin*clear)
    rho,mu,k=properties(temp,pressure,cp,a['gas_constant_j_kg_k'])
    velocity=mass/(rho*area); re=mass*dh/(area*mu); alpha=min(gap,clear)/max(gap,clear)
    pol=lambda coefficients: sum(c*alpha**i for i,c in enumerate(coefficients))
    nu_lam=7.541*pol([1,-2.610,4.970,-5.119,2.702,-0.548])
    f_lam=96/re*pol([1,-1.3553,1.9467,-1.7012,0.9564,-0.2537])
    if strip:
        alpha,delta,gamma=clear/gap,fin/strip,fin/clear
        j=0.6522*re**-0.5403*alpha**-0.1541*delta**0.1499*gamma**-0.0678*(1+5.269e-5*re**1.340*alpha**0.504*delta**0.456*gamma**-1.055)**0.1
        f=4*9.6243*re**-0.7422*alpha**-0.1856*delta**0.3053*gamma**-0.2659*(1+7.669e-8*re**4.429*alpha**0.920*delta**3.767*gamma**0.236)**0.1
        nu=j*re*0.71**(1/3)
        regime='offset' if 300<=re<=5000 and 0.134<=alpha<=0.997 and 0.012<=delta<=0.048 and 0.041<=gamma<=0.121 else 'offset_out_of_range'
    elif re < 2300: nu,f,regime=nu_lam,f_lam,'laminar'
    else:
        f=(0.79*math.log(max(re,3000))-1.64)**-2
        nu=(f/8)*(max(re,3000)-1000)*0.71/(1+12.7*math.sqrt(f/8)*(0.71**(2/3)-1))
        regime='turbulent' if re >= 3000 else 'transition_excluded'
        if re < 3000:
            blend=(re-2300)/700
            nu=nu_lam*(1-blend)+nu*blend; f=f_lam*(1-blend)+f*blend
    return {'re':re,'regime':regime,'h_w_m2_k':hfactor*nu*k/dh,
            'pressure_drop_pa':(ffactor*f*length/dh+entry_k)*rho*velocity**2/2,
            'velocity_m_s':velocity,'mach':velocity/math.sqrt(a['gamma']*a['gas_constant_j_kg_k']*temp),
            'dh_m':dh,'open_area_m2':area,'length_over_dh':length/dh,
            'laminar_thermal_entry_length_over_length':0.05*re*0.71*dh/length if regime=='laminar' else None}


def geometry(values, wall_mm):
    width,span,depth,hgap,cgap,hpitch,cpitch,fin=values
    w,d,z,h,c,ph,pc,t,wall=[v/1000 for v in (*values,wall_mm)]
    tubes=math.floor((d+c)/(h+2*wall+c)); cold_rows=tubes-1
    hot_channels=math.floor((z-2*wall+t)/ph); cold_channels=math.floor((w-2*wall+t)/pc)
    if min(tubes-1,hot_channels,cold_channels)<1: raise ValueError('No channels')
    hot_clear=ph-t; cold_clear=pc-t
    actual_span=tubes*(h+2*wall)+(tubes-1)*c
    metal_volume=w*actual_span*z-w*tubes*hot_channels*h*hot_clear-z*cold_rows*cold_channels*c*cold_clear
    return {'width_mm':width,'span_mm':actual_span*1000,'depth_mm':depth,'hot_gap_mm':hgap,'cold_gap_mm':cgap,
            'hot_pitch_mm':hpitch,'cold_pitch_mm':cpitch,'fin_mm':fin,'wall_mm':wall_mm,
            'tubes':tubes,'hot_channels_per_tube':hot_channels,'cold_channels_per_gap':cold_channels,
            'hot_clear_m':hot_clear,'cold_clear_m':cold_clear,'metal_volume_m3':metal_volume,
            'core_volume_l':w*actual_span*z*1000,'search_span_limit_mm':span,'fin_family':'plain','strip_length_mm':0}


def evaluate(g, scenario, a, cooling_mass=None, hfactor=1., ffactor=1., metal_k=None):
    mc=a['cooling_mass_flow_kg_s'] if cooling_mass is None else cooling_mass;
    if mc <= 0 or not math.isfinite(mc) or hfactor <= 0 or ffactor <= 0: raise ValueError('Invalid flow or multiplier')
    mh=scenario['charge_mass_flow_kg_s']
    tc=a['ambient_c']+273.15; target=a['charge_outlet_target_c']+273.15
    th=(a['compressor_inlet_c']+273.15)*(1+(scenario['compressor_pressure_ratio']**((a['gamma']-1)/a['gamma'])-1)/scenario['compressor_efficiency'])
    pressure=a['ambient_pressure_pa']*scenario['compressor_pressure_ratio']; ch=mh*a['hot_cp_j_kg_k']; cc=mc*a['cold_cp_j_kg_k']
    w,z,h,c,t,wall=[g[k]/1000 for k in ('width_mm','depth_mm','hot_gap_mm','cold_gap_mm','fin_mm','wall_mm')]
    strip=g['strip_length_mm']/1000
    banks=g.get('charge_parallel_banks',1)
    if banks not in (1,2): raise ValueError('Unsupported charge bank count')
    nt,nh,nc=g['tubes'],g['hot_channels_per_tube'],g['cold_channels_per_gap']; km=a['metal_k_w_m_k'] if metal_k is None else metal_k
    if not math.isfinite(km) or km<=0: raise ValueError('Invalid conductivity')
    tout=target; cout=tc
    for _ in range(80):
        hot=duct(h,g['hot_clear_m'],w/banks,nt*nh*banks,mh,(th+tout)/2,pressure,a['hot_cp_j_kg_k'],a,hfactor,ffactor,a['header_loss_k'],t,strip)
        cold=duct(c,g['cold_clear_m'],z,(nt-1)*nc,mc,(tc+cout)/2,a['ambient_pressure_pa'],a['cold_cp_j_kg_k'],a,hfactor,ffactor,a['ambient_entry_exit_k'],t,strip)
        eta=lambda hh,length: math.tanh(x:=math.sqrt(2*hh/(km*t))*length/2)/x
        eh=eta(hot['h_w_m2_k'],h); ec=eta(cold['h_w_m2_k'],c)
        # Outer tube faces lack cooling neighbours: omit their heat transfer conservatively.
        hot_area=2*(nt-1)*nh*w*g['hot_clear_m']+eh*2*(nt-1)*(nh-1)*w*h
        cold_area=2*(nt-1)*nc*z*g['cold_clear_m']+ec*2*(nt-1)*(nc-1)*z*c
        separating_area=2*(nt-1)*w*z
        ua=1/(1/(hot['h_w_m2_k']*hot_area)+wall/(km*separating_area)+1/(cold['h_w_m2_k']*cold_area))
        eps=effectiveness(ua/min(ch,cc),min(ch,cc)/max(ch,cc))
        q=eps*min(ch,cc)*(th-tc); new_t=th-q/ch; new_c=tc+q/cc
        if max(abs(new_t-tout),abs(new_c-cout))<1e-7: break
        tout=(tout+new_t)/2; cout=(cout+new_c)/2
    else: raise ArithmeticError('Property iteration did not converge')
    admissible=(hot['regime'] not in ('transition_excluded','offset_out_of_range') and cold['regime'] not in ('transition_excluded','offset_out_of_range') and max(hot['re'],cold['re'])<5e6 and max(hot['mach'],cold['mach'])<a['max_mach'] and hot['pressure_drop_pa']/pressure<a['max_pressure_fraction'])
    passed=admissible and new_t<=target and hot['pressure_drop_pa']<=a['charge_pressure_loss_budget_pa'] and cold['pressure_drop_pa']<=a['ambient_pressure_loss_budget_pa']
    return {'scenario':scenario['id'],'charge_inlet_c':th-273.15,'charge_outlet_c':new_t-273.15,
            'cooling_inlet_c':tc-273.15,'engine_inlet_c':new_c-273.15,'heat_rejection_w':q,
            'required_heat_rejection_w':ch*(th-target),'required_ua_w_k':required_ua(ch,cc,th,tc,target),
            'ua_w_k':ua,'effectiveness':eps,'hot_fin_efficiency':eh,'cold_fin_efficiency':ec,
            'hot':hot,'cold':cold,'cooling_mass_flow_kg_s':mc,'cold_fluid_power_w':cold['pressure_drop_pa']*mc/properties((tc+new_c)/2,a['ambient_pressure_pa'],a['cold_cp_j_kg_k'],a['gas_constant_j_kg_k'])[0],
            'energy_residual_w':ch*(th-new_t)-cc*(new_c-tc),'correlation_screen_admissible':admissible,
            'assumed_constraints_pass':passed,'physical_performance_accepted':False}


def run(card, output):
    validate(card)
    if output.exists(): raise FileExistsError(output)
    a=card['assumed']; rows=[]; best=None; feasible=0; scenario_best={}
    candidates=[]
    for family,search in [('plain',card['search']),('offset',card['offset_search'])]:
        for face,depth,h,c,ph,pc,t,strip in itertools.product(search['face_mm'],search['air_depth_mm'],search['hot_gap_mm'],search['cold_gap_mm'],search['hot_pitch_mm'],search['cold_pitch_mm'],search['fin_mm'],search.get('strip_length_mm',[0])):
            g=geometry((*face,depth,h,c,ph,pc,t),a['wall_mm'])
            g.update(fin_family=family,strip_length_mm=strip)
            candidates.append(g)
    for g in candidates:
        cases=[evaluate(g,s,a,hfactor=a['heat_transfer_multiplier_stress'],ffactor=a['friction_multiplier_stress']) for s in a['scenarios']]
        mass=g['metal_volume_m3']*a['metal_density_kg_m3']; passed=all(c['assumed_constraints_pass'] for c in cases)
        row={**{k:v for k,v in g.items() if not k.endswith('_m')},'mass_kg':mass,'stress_all_scenarios_pass':passed,
             'max_charge_outlet_c':max(c['charge_outlet_c'] for c in cases),'max_hot_dp_pa':max(c['hot']['pressure_drop_pa'] for c in cases),
             'max_cold_dp_pa':max(c['cold']['pressure_drop_pa'] for c in cases),'all_regimes_admissible':all(c['correlation_screen_admissible'] for c in cases)}
        rows.append(row)
        for case in cases:
            prior=scenario_best.get(case['scenario'])
            if case['assumed_constraints_pass'] and (prior is None or mass<prior['core_mass_kg']):
                scenario_best[case['scenario']]={'geometry':g,'core_mass_kg':mass,'case':case}
        if passed:
            feasible+=1
            if best is None or (mass,g['core_volume_l']) < best[0]: best=((mass,g['core_volume_l']),g)
    output.mkdir(parents=True)
    with (output/'sweep.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n");writer.writeheader();writer.writerows(rows)
    selected=best[1] if best else None
    report={'status':'uncalibrated_thermal_hydraulic_sizing','candidate_count':len(rows),'family_counts':{f:sum(r['fin_family']==f for r in rows) for f in ['plain','offset']},'stress_feasible_count':feasible,
            'objective':'minimum modeled core mass satisfying all three assumed scenarios under stress factors; plain and offset strip-fin families within correlation bounds',
            'selected_geometry':selected,'minimum_mass_by_assumed_scenario':scenario_best,'acceptance':card['acceptance'],
            'basis':card,'source_hashes':{str(p.relative_to(STUDY)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [STUDY/'requirements.json',Path(__file__)]}}
    if selected:
        report['selected_nominal']=[evaluate(selected,s,a) for s in a['scenarios']]
        report['selected_stress']=[evaluate(selected,s,a,hfactor=a['heat_transfer_multiplier_stress'],ffactor=a['friction_multiplier_stress']) for s in a['scenarios']]
        report['cooling_flow_sensitivity']=[evaluate(selected,a['scenarios'][-1],a,cooling_mass=m) for m in [1.,1.5,2.,2.5,3.]]
        report['conductivity_sensitivity']=[{'metal_k_w_m_k':k,'case':evaluate(selected,a['scenarios'][-1],a,metal_k=k)} for k in [100,120,160,300]]
        old=geometry((620,450,60,*[selected[k] for k in ['hot_gap_mm','cold_gap_mm','hot_pitch_mm','cold_pitch_mm','fin_mm']]),a['wall_mm'])
        old.update(fin_family=selected['fin_family'],strip_length_mm=selected['strip_length_mm'])
        report['original_620x450x60_same_fins']=evaluate(old,a['scenarios'][-1],a)
        g=selected; span=g['hot_clear_m']; pressure=(max(s['compressor_pressure_ratio'] for s in a['scenarios'])-1)*a['ambient_pressure_pa']
        report['wall_strip_stress_mpa']=0.75*pressure*(span/(g['wall_mm']/1000))**2/1e6
        report['wall_stress_status']='simply supported strip at scenario pressure only; not proof pressure, fatigue, header, joint or hot strength qualification'
        report['core_build_45deg_extents_mm']=[(g['width_mm']+g['depth_mm'])/math.sqrt(2),g['span_mm'],(g['width_mm']+g['depth_mm'])/math.sqrt(2)]
    bhp=card['confirmed']['engine_power_metric_hp']*735.49875/745.6998716
    report['power_basis']={'metric_hp':card['confirmed']['engine_power_metric_hp'],'kw':card['confirmed']['engine_power_metric_hp']*0.73549875,'mechanical_hp':bhp,'garrett_first_approximation_kg_s':[bhp/10.5*0.45359237/60,bhp/9.5*0.45359237/60],'upper_flow_scenario_is_extra_margin':True}
    if selected:
        report['core_mass_kg']=selected['metal_volume_m3']*a['metal_density_kg_m3']
        report['required_cooling_flow_for_15k_engine_air_rise_kg_s']=[c['required_heat_rejection_w']/(a['cold_cp_j_kg_k']*15) for c in report['selected_nominal']]
        last=report['selected_stress'][-1]
        report['crossflow_grid_check']=[crossflow_grid(last['ua_w_k'],a['scenarios'][-1]['charge_mass_flow_kg_s']*a['hot_cp_j_kg_k'],a['cooling_mass_flow_kg_s']*a['cold_cp_j_kg_k'],last['charge_inlet_c'],a['ambient_c'],n) for n in [40,80,160]]
        report['mixedness_sensitivity']=[]
        for c,s in zip(report['selected_stress'],a['scenarios']):
            ch=s['charge_mass_flow_kg_s']*a['hot_cp_j_kg_k'];cc=a['cooling_mass_flow_kg_s']*a['cold_cp_j_kg_k'];cr=min(ch,cc)/max(ch,cc);ntu=c['ua_w_k']/min(ch,cc)
            eps=1/(1/(-math.expm1(-ntu))+cr/(-math.expm1(-cr*ntu))-1/ntu)
            q=eps*min(ch,cc)*(c['charge_inlet_c']-a['ambient_c'])
            report['mixedness_sensitivity'].append({'scenario':s['id'],'both_fully_mixed_effectiveness':eps,'charge_outlet_c':c['charge_inlet_c']-q/ch,'status':'topology bound at unchanged UA, not a calibrated offset-fin mixing prediction'})
    report['sweep_sha256']=hashlib.sha256((output/'sweep.csv').read_bytes()).hexdigest()
    (output/'sizing.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'cases':len(rows),'feasible':feasible,'selected':selected}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    run(json.loads((STUDY/'requirements.json').read_text()),args.output)
