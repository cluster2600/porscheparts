#!/usr/bin/env python3
"""Research-only thin-wall route; reuses the same thermal and hydraulic model."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
from size_core import evaluate, geometry, STUDY


def run(output):
    if output.exists(): raise FileExistsError(output)
    card=json.loads((STUDY/'requirements.json').read_text());a=card['assumed'];rows=[];best=None
    search={'faces_mm':[[500,400],[620,450],[700,500],[800,550]],'depths_mm':[60,90,120],
            'hot_gaps_mm':[2,3],'cold_gaps_mm':[4,6],'hot_pitches_mm':[1.5,2,3],
            'cold_pitches_mm':[2,3],'fins_mm':[.15,.2],'strips_mm':[5,10,12],'walls_mm':[.4,.6],'charge_parallel_banks':[1,2]}
    for face,depth,h,c,ph,pc,t,strip,wall,banks in itertools.product(*search.values()):
        g=geometry((*face,depth,h,c,ph,pc,t),wall);g.update(fin_family='offset',strip_length_mm=strip,charge_parallel_banks=banks)
        cases=[evaluate(g,s,a,hfactor=.75,ffactor=2) for s in a['scenarios']]
        passed=all(c['assumed_constraints_pass'] for c in cases);mass=g['metal_volume_m3']*a['metal_density_kg_m3']
        rows.append({**g,'mass_kg':mass,'all_scenarios_pass':passed,'all_regimes_admissible':all(c['correlation_screen_admissible'] for c in cases),'max_outlet_c':max(c['charge_outlet_c'] for c in cases),'max_hot_dp_pa':max(c['hot']['pressure_drop_pa'] for c in cases),'max_cold_dp_pa':max(c['cold']['pressure_drop_pa'] for c in cases)})
        if passed and (best is None or mass<best['mass_kg']):best={'geometry':g,'mass_kg':mass,'stress_cases':cases}
    output.mkdir(parents=True)
    with (output/'thin-sweep.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");writer.writeheader();writer.writerows(rows)
    paths=[Path(__file__),STUDY/'source/size_core.py',STUDY/'requirements.json']
    report={'status':'advanced_process_research_only','search':search,'candidate_count':len(rows),
            'screen_pass_count':sum(r['all_scenarios_pass'] for r in rows),'best_screen_candidate':best,
            'manufacturer_recipe_selected':False,'thin_fin_printability_verified':False,'pressure_qualified':False,'manufacturing_authorized':False,
            'full_core_native_geometry_generated':False,'source_hashes':{str(p.relative_to(STUDY)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'sweep_sha256':hashlib.sha256((output/'thin-sweep.csv').read_bytes()).hexdigest()}
    if best:
        from size_core import crossflow_grid
        c=best['stress_cases'][-1]
        report['crossflow_grid_check']=[crossflow_grid(c['ua_w_k'],a['scenarios'][-1]['charge_mass_flow_kg_s']*a['hot_cp_j_kg_k'],a['cooling_mass_flow_kg_s']*a['cold_cp_j_kg_k'],c['charge_inlet_c'],a['ambient_c'],n) for n in [40,80,160]]
        import math
        ch=a['scenarios'][-1]['charge_mass_flow_kg_s']*a['hot_cp_j_kg_k']; cc=a['cooling_mass_flow_kg_s']*a['cold_cp_j_kg_k']; cr=min(ch,cc)/max(ch,cc); ntu=c['ua_w_k']/min(ch,cc)
        eps=1/(1/(-math.expm1(-ntu))+cr/(-math.expm1(-cr*ntu))-1/ntu)
        report['fully_mixed_bound_charge_outlet_c']=c['charge_inlet_c']-eps*min(ch,cc)*(c['charge_inlet_c']-a['ambient_c'])/ch
        report['cooling_flow_sensitivity']=[evaluate(best['geometry'],a['scenarios'][-1],a,cooling_mass=m,hfactor=.75,ffactor=2) for m in [1.,1.5,2.,2.5,3.]]
        report['per_bank_core_45deg_extents_mm']=[(best['geometry']['width_mm']/best['geometry']['charge_parallel_banks']+best['geometry']['depth_mm'])/2**.5,best['geometry']['span_mm'],(best['geometry']['width_mm']/best['geometry']['charge_parallel_banks']+best['geometry']['depth_mm'])/2**.5]
    (output/'thin-sizing.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'count':len(rows),'passing':report['screen_pass_count'],'best':best}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.output)
