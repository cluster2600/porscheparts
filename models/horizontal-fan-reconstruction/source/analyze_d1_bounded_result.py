#!/usr/bin/env python3
"""Report a bounded incomplete D1 honestly using only prospective complete windows."""
import argparse,hashlib,json,math,re,statistics
from pathlib import Path
from measurement_window import require_measurement_window
NUM=r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(inputs,archive_manifest,output):
    native=json.loads(archive_manifest.read_text());index=json.loads((inputs/'input-manifest.json').read_text())['files']
    for name,record in index.items():
        p=inputs/name
        if native['members'][name]!=record or p.stat().st_size!=record['bytes'] or sha(p)!=record['sha256']:raise ValueError('Native diagnostic input identity differs')
    prefix='D1-runtime-symlink-repair/';root=inputs/prefix;records={}
    stats=lambda values:{'mean':statistics.mean(values),'population_std':statistics.pstdev(values),'min':min(values),'max':max(values),'relative_std_if_nonzero_mean':statistics.pstdev(values)/abs(statistics.mean(values)) if statistics.mean(values) else None}
    for label in ['control','absolute']:
        case=root/'cases'/label;rows={};entered=[]
        text=(case/'log.foamRun').read_text()
        for block in re.split(r'(?m)^Time = ',text)[1:]:
            t=int(float(re.match(r'([0-9.]+)',block)[1]));entered.append(t)
            solves=re.findall(r'Solving for p, Initial residual = ('+NUM+r'), Final residual = ('+NUM+r'), No Iterations (\d+)',block)
            continuity=re.search(r'time step continuity errors : sum local = ('+NUM+r'), global = ('+NUM+r')',block)
            if len(solves)==3 and continuity and re.search(r'(?m)^ExecutionTime =',block):rows[t]={'p_initial_residual_max':max(float(v[0]) for v in solves),'p_final_linear_residual_max':max(float(v[1]) for v in solves),'linear_pressure_iterations_summed_three_corrections':sum(int(v[2]) for v in solves),'continuity_global':float(continuity[2])}
        tables=[];table_records={}
        for name in ['inletFlow','outletFlow','rotorForces']:
            p=case/'postProcessing'/name/'900'/('forces.dat' if name=='rotorForces' else 'surfaceFieldValue.dat')
            values=[[float(v) for v in re.findall(NUM,line)] for line in p.read_text().splitlines() if line.strip() and not line.startswith('#')]
            if not all(math.isfinite(v) for row in values for v in row):raise ValueError('Native finite telemetry required')
            table_records[name]={'total_samples_including_initial900':len(values),'new_samples_after900':sum(row[0]>900 for row in values),'iterations':[row[0] for row in values],'sha256':sha(p)}
            tables.append({int(row[0]):row for row in values})
        windows=[]
        for first in [901,921,941]:
            expected=list(range(first,first+20));available=all(t in rows and all(t in table for table in tables) for t in expected)
            window={'range':[first,first+19],'prospectively_declared':True,'complete20_native_samples':available,'statistics':None}
            if available:
                require_measurement_window(expected,*[[table[t] for t in expected] for table in tables],20)
                values={key:[rows[t][key] for t in expected] for key in rows[expected[0]]}
                values.update(Qin_m3_s=[tables[0][t][1] for t in expected],Qout_m3_s=[tables[1][t][1] for t in expected],fluid_on_rotor_torque_Nm=[tables[2][t][9]+tables[2][t][12] for t in expected])
                values['input_power_W']=[-v*6000*math.pi/30 for v in values['fluid_on_rotor_torque_Nm']]
                window['statistics']={key:stats(v) for key,v in values.items()}
            windows.append(window)
        flow=case/'flow-summary.json'
        summary=json.loads(flow.read_text()) if flow.exists() else None
        records[label]={'iterations_entered':entered,'iterations_completed_and_reported':list(rows),'complete_iteration_count':len(rows),'tables':table_records,'windows':windows,'admission_window_941_960_verified':windows[-1]['complete20_native_samples'],'frozen_admission_status':summary['status'] if summary else 'not_evaluated_incomplete_target960','frozen_criteria_checks':summary['criteria_checks'] if summary else None,'final_field_cell_counts_at960':summary['final_field_cell_counts'] if summary else None,'residual_trace_complete_iterations':{'iterations':list(rows),'initial_max':[r['p_initial_residual_max'] for r in rows.values()],'linear_final_max':[r['p_final_linear_residual_max'] for r in rows.values()]}}
    changes={}
    c=records['control']['windows'][0]['statistics'];a=records['absolute']['windows'][0]['statistics']
    if c is not None and a is not None:
        for name in c:changes[name]={'control':c[name],'absolute':a[name],'mean_signed_difference':a[name]['mean']-c[name]['mean'],'mean_percent_difference_relative_to_control_mean_magnitude':100*(a[name]['mean']-c[name]['mean'])/abs(c[name]['mean']) if c[name]['mean'] else None}
    partition=[json.loads((root/'cases'/label/'partition-preparation.json').read_text()) for label in ['control','absolute']]
    if partition[0]!=partition[1] or not partition[0]['all_initial_processor_files_hashes_match']:raise ValueError('Initial native partition identity required')
    budget=json.loads((inputs/'D1-original-global-budget-receipt.json').read_text());release=json.loads((root/'completion-and-release-verification.json').read_text());isolation=json.loads((root/'host-isolation-verification.json').read_text())
    result={'status':'D1_control60_not_admitted_pressure_absolute29_incomplete_global_budget_stopped','records':records,'paired_first_prospective_window_901_920_descriptive_difference':changes,'complete_paired_target960_comparison_established':False,'historical_fine_admission_restored':False,'pressure_linear_final_max_reduction_factor_first20':c['p_final_linear_residual_max']['max']/a['p_final_linear_residual_max']['max'],'pressure_initial_max_ratio_absolute_over_control_first20':a['p_initial_residual_max']['max']/c['p_initial_residual_max']['max'],'pressure_linear_iterations_ratio_first20':a['linear_pressure_iterations_summed_three_corrections']['mean']/c['linear_pressure_iterations_summed_three_corrections']['mean'],'shared_initial_partition_sha256':partition[0]['shared_partition_sha256'],'global_budget':budget,'actual_container_limits':{k:v for k,v in isolation.items() if k not in ['owned_container_name']},'resources_released_UTC':release['observed_UTC'],'resources_released':release['resources_released'],'no_owned_D1_container_remaining':not release['owned_D1_containers_active'],'remaining_services_match_preflight':release['services']==['ops-control-plane-1 qwen38-control-plane:local','openbao-openbao-1 ghcr.io/openbao/openbao:2.3.1'],'native_archive_sha256':native['archive_sha256'],'native_archive_bytes':native['archive_bytes'],'native_archive_members':len(native['members']),'native_archive_all_members_verified':native['all_members_verified'],'private_archive_not_published':True,'input_manifest_sha256':sha(inputs/'input-manifest.json'),'script_sha256':sha(Path(__file__)),'physical_validation_established':False,'performance_improvement_established':False,'physical_frequency_or_statistical_confidence_established':False,'interpretation':'Only the predeclared first20 window is paired and complete. Tighter linear pressure solves strongly reduce their final residual but leave the initial residual peaks similar in that window. This weakens the sole-linear-stopping explanation; nonlinear, mesh/wake and outlet effects remain unresolved. The incomplete absolute branch cannot establish target960 admission or a complete matched comparison.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k in ['status','pressure_linear_final_max_reduction_factor_first20','pressure_initial_max_ratio_absolute_over_control_first20','pressure_linear_iterations_ratio_first20','resources_released']}));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','archive_manifest','output']:p.add_argument(name,type=Path)
    a=p.parse_args();analyze(a.inputs,a.archive_manifest,a.output)
