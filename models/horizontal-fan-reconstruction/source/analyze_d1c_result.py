#!/usr/bin/env python3
"""Compare one native consistent branch against the already preserved D1 control."""
import argparse,hashlib,json,math,re,statistics
from pathlib import Path
from measurement_window import require_measurement_window
NUM=r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def admission_supported(complete,summary):
    checks={'initial_time_matches_frozen_continuation','residual_p','residual_U','residual_turbulence','mass_balance','flow_stability','torque_stability','declared_flow_direction','complete_finite_fields','finite_measurements'}
    return bool(complete and summary and summary.get('status')=='reference_pilot_admitted_numerically' and set(summary.get('criteria_checks',{}))==checks and all(summary['criteria_checks'].values()) and summary.get('contiguous_measurement_window_verified') and summary.get('native_window_sample_count')==20 and summary.get('final_field_cell_counts')=={name:453496 for name in ['U','p','k','omega','nut']})


def analyze(inputs,study,output):
    native=json.loads((inputs/'native-evidence-manifest.json').read_text())
    for name,record in native['members'].items():
        p=inputs/name
        if p.stat().st_size!=record['bytes'] or sha(p)!=record['sha256']:raise ValueError('Preserved native D1C identity differs')
    case=inputs/'cases/consistent';rows={};entered=[];incomplete=[]
    summary_path=case/'flow-summary.json';summary=json.loads(summary_path.read_text()) if summary_path.exists() else None
    log=(case/'log.foamRun').read_text()
    for block in re.split(r'(?m)^Time = ',log)[1:]:
        t=int(float(re.match(r'([0-9.]+)',block)[1]));entered.append(t)
        pressure=re.findall(r'Solving for p, Initial residual = ('+NUM+r'), Final residual = ('+NUM+r'), No Iterations (\d+)',block)
        continuity=re.search(r'time step continuity errors : sum local = ('+NUM+r'), global = ('+NUM+r')',block)
        if len(pressure)!=3 or not continuity or not re.search(r'(?m)^ExecutionTime =',block):incomplete.append(t);continue
        rows[t]={'p_initial_residual_max':max(float(v[0]) for v in pressure),'p_final_linear_residual_max':max(float(v[1]) for v in pressure),'linear_pressure_iterations_summed_three_corrections':sum(int(v[2]) for v in pressure),'continuity_global':float(continuity[2])}
    tables={};counts={}
    for name in ['inletFlow','outletFlow','rotorForces']:
        path=case/'postProcessing'/name/'900'/('forces.dat' if name=='rotorForces' else 'surfaceFieldValue.dat')
        if summary and sha(path)!=summary['file_sha256'][str(path.relative_to(case))]:raise ValueError('Telemetry differs from original native archived summary')
        values=[[float(v) for v in re.findall(NUM,l)] for l in path.read_text().splitlines() if l.strip() and not l.startswith('#')]
        if not all(math.isfinite(v) for row in values for v in row):raise ValueError('Finite native measurements required')
        iterations=[int(row[0]) for row in values]
        if len(set(iterations))!=len(iterations):raise ValueError('Duplicate telemetry timestamps')
        tables[name]={int(row[0]):row for row in values};counts[name]={'total_samples_including_initial900':len(values),'new_samples_after900':sum(t>900 for t in iterations),'iterations':iterations,'sha256':sha(path)}
    baseline=json.loads((study/'results/cfd/D1-bounded-result.json').read_text())
    proposal=json.loads((study/'parameters/D1-coupling-proposed-protocol.json').read_text())
    if proposal['baseline_report_sha256']!=sha(study/'results/cfd/D1-bounded-result.json'):raise ValueError('Frozen control identity changed')
    stats=lambda v:{'mean':statistics.mean(v),'population_std':statistics.pstdev(v),'min':min(v),'max':max(v),'relative_std_if_nonzero_mean':statistics.pstdev(v)/abs(statistics.mean(v)) if statistics.mean(v) else None}
    windows=[];differences=[]
    for first in [901,921,941]:
        expected=list(range(first,first+20));complete=all(t in rows and all(t in table for table in tables.values()) for t in expected)
        values=None;delta=None
        if complete:
            require_measurement_window(expected,*[[table[t] for t in expected] for table in tables.values()],20)
            values={key:[rows[t][key] for t in expected] for key in rows[first]}
            values.update(Qin_m3_s=[tables['inletFlow'][t][1] for t in expected],Qout_m3_s=[tables['outletFlow'][t][1] for t in expected],fluid_on_rotor_torque_Nm=[tables['rotorForces'][t][9]+tables['rotorForces'][t][12] for t in expected])
            values['input_power_W']=[-v*6000*math.pi/30 for v in values['fluid_on_rotor_torque_Nm']];values={k:stats(v) for k,v in values.items()}
            control=baseline['records']['control']['windows'][(first-901)//20]['statistics']
            delta={k:{'control':control[k],'consistent':values[k],'mean_signed_difference':values[k]['mean']-control[k]['mean'],'mean_percent_difference_relative_to_control_magnitude':100*(values[k]['mean']-control[k]['mean'])/abs(control[k]['mean']) if control[k]['mean'] else None} for k in values}
        windows.append({'range':[first,first+19],'prospectively_declared':True,'complete20_native_samples':complete,'statistics':values});differences.append(delta)
    complete=(list(rows)==list(range(901,961)) and not incomplete and bool(re.search(r'(?m)^End\s*$',log)) and all(w['complete20_native_samples'] for w in windows))
    admitted=admission_supported(complete,summary)
    reduction=None;interpretation='incomplete_or_intermediate_descriptive_only'
    if complete:
        b=baseline['records']['control']['windows'][2]['statistics']['p_initial_residual_max']['max'];v=windows[2]['statistics']['p_initial_residual_max']['max'];reduction=100*(b-v)/b
        if reduction>=30 and admitted:interpretation='supports_numerical_coupling_sensitivity_under_prospective_rule'
        elif abs(reduction)<10:interpretation='does_not_support_coupling_sensitivity_under_prospective_rule'
    partition=json.loads((case/'partition-preparation.json').read_text());config=json.loads((case/'config-verification.json').read_text());launcher=json.loads((inputs/'launcher-receipt.json').read_text());isolation=json.loads((inputs/'isolation-verification.json').read_text())
    if partition['shared_partition_sha256']!=proposal['shared_initial_MPI_partition_sha256'] or not config['all_initial_native_files_match']:raise ValueError('Native initial state or partition differs')
    result={'status':interpretation,'candidate_native_target960_complete':complete,'candidate_original_frozen_gates_passed':admitted,'control_original_frozen_gates_passed':False,'paired_numerical_admission_established':False,'new_cases':1,'entered_iterations':entered,'complete_iterations':list(rows),'incomplete_iterations_excluded':incomplete,'complete_iteration_count':len(rows),'tables':counts,'windows':windows,'matched_window_differences':differences,'last20_initial_p_max_reduction_percent':reduction,'candidate_original_frozen_checks':summary['criteria_checks'] if summary else None,'residual_trace_complete_iterations':{'iterations':list(rows),'initial_max':[r['p_initial_residual_max'] for r in rows.values()],'linear_final_max':[r['p_final_linear_residual_max'] for r in rows.values()]},'shared_initial_partition_sha256':partition['shared_partition_sha256'],'native_initial_processor_file_count':partition['native_initial_processor_file_count'],'global_elapsed_seconds':native['global_elapsed_seconds_setup_solver_reconstruction_audit_and_preservation'],'global_wall_cap_seconds':300,'resources_released':not launcher['owned_container_remaining'],'services_unchanged':launcher['services_unchanged'],'resources_released_UTC':launcher['resources_released_UTC'],'actual_isolation':isolation,'native_archive_sha256':native['archive_sha256'],'native_archive_bytes':native['archive_bytes'],'native_archive_member_count':len(native['members']),'native_archive_all_members_verified':native['all_members_verified'],'private_archive_not_published':True,'baseline_report_sha256':sha(study/'results/cfd/D1-bounded-result.json'),'proposal_sha256':sha(study/'parameters/D1-coupling-proposed-protocol.json'),'script_sha256':sha(Path(__file__)),'native_manifest_sha256':sha(inputs/'native-evidence-manifest.json'),'historical_fine_admission_restored':False,'physical_validation_established':False,'installed_cooling_improvement_established':False,'outlet_reverse_flow_remains_explicit_limit':True,'no_additional_phase_launched':True,'physical_frequency_or_statistical_confidence_established':False}
    if result['global_elapsed_seconds']>300 or not result['resources_released']:raise ValueError('Execution budget or cleanup violated')
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','complete_iteration_count','candidate_original_frozen_gates_passed','last20_initial_p_max_reduction_percent','global_elapsed_seconds']}));return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','study','output']:ap.add_argument(name,type=Path)
    a=ap.parse_args();analyze(a.inputs,a.study,a.output)
