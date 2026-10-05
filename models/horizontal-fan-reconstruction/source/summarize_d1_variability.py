#!/usr/bin/env python3
"""Audit prospective D1 telemetry and deterministic iteration variability."""
import argparse,hashlib,json,math,re,statistics
from pathlib import Path
from measurement_window import require_measurement_window
NUM=r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_case(case,admission_summary):
    protocol=json.loads((case/'reference-protocol.json').read_text())
    expected=protocol['expected_actual_solver_iterations']
    if expected!=list(range(901,961)):raise ValueError('Exact prospective D1 bounds required')
    log=case/'log.foamRun';text=log.read_text();rows=[]
    for block in re.split(r'(?m)^Time = ',text)[1:]:
        iteration=float(re.match(r'([\d.eE+-]+)',block)[1])
        solves=re.findall(r'Solving for p, Initial residual = ('+NUM+r'), Final residual = ('+NUM+r'), No Iterations (\d+)',block)
        continuity=re.search(r'time step continuity errors : sum local = ('+NUM+r'), global = ('+NUM+r')',block)
        if len(solves)!=3 or not continuity:raise ValueError('Native pressure/continuity coverage required')
        rows.append([iteration,max(float(s[0]) for s in solves),max(float(s[1]) for s in solves),float(continuity[2])])
    if [r[0] for r in rows]!=expected or 'End' not in text or 'FOAM FATAL' in text:raise ValueError('Exactly60 completed native D1 iterations required')
    files=[log,case/'reference-protocol.json'];tables=[]
    for name in ['inletFlow','outletFlow','rotorForces']:
        pp=case/'postProcessing'/name
        start=max(pp.iterdir(),key=lambda p:float(p.name))
        path=start/('forces.dat' if name=='rotorForces' else 'surfaceFieldValue.dat');files.append(path)
        values=[[float(v) for v in re.findall(NUM,line)] for line in path.read_text().splitlines() if line.strip() and not line.startswith('#')]
        values=[r for r in values if r[0] in expected]
        tables.append(values)
    require_measurement_window(expected,*tables,60)
    inlet,outlet,force=tables
    quantities={'Qin_m3_s':[r[1] for r in inlet],'Qout_m3_s':[r[1] for r in outlet],'total_fluid_on_rotor_torque_Nm':[r[9]+r[12] for r in force],'p_initial_residual_max':[r[1] for r in rows],'p_final_linear_residual_max':[r[2] for r in rows],'continuity_global':[r[3] for r in rows]}
    if not all(math.isfinite(v) for values in quantities.values() for v in values):raise ValueError('Finite prospective telemetry required')
    windows=[]
    for start in [0,20,40]:
        metrics={}
        for name,values in quantities.items():
            v=values[start:start+20];mean=statistics.mean(v);std=statistics.pstdev(v)
            metrics[name]={'mean':mean,'population_standard_deviation':std,'minimum':min(v),'maximum':max(v),'relative_std_if_nonzero_mean':std/abs(mean) if mean else None}
        windows.append({'iteration_range':[expected[start],expected[start+19]],'samples':20,'statistics':metrics})
    flow=json.loads(admission_summary.read_text())
    required_checks={'initial_time_matches_frozen_continuation','residual_p','residual_U','residual_turbulence','mass_balance','flow_stability','torque_stability','declared_flow_direction','complete_finite_fields','finite_measurements'}
    complete=flow.get('status')=='reference_pilot_admitted_numerically' and set(flow['criteria_checks'])==required_checks and set(flow.get('final_field_cell_counts',{}))=={'U','p','k','omega','nut'} and all(n==protocol['expected_cell_count'] for n in flow['final_field_cell_counts'].values())
    supported=complete and flow.get('contiguous_measurement_window_verified') is True and flow.get('native_window_sample_count')==20 and flow['iterations_completed']==960 and flow['file_sha256']['reference-protocol.json']==sha(case/'reference-protocol.json') and all(flow['criteria_checks'].values())
    for name,digest in flow['file_sha256'].items():
        if sha(case/name)!=digest:raise ValueError('Frozen admission input changed')
    return {'windows':windows,'current_original_frozen_gates_passed':supported,'admission_summary_sha256':sha(admission_summary),'native_input_sha256':{str(f.relative_to(case)):sha(f) for f in files},'all60_native_telemetry_samples_verified':True}


def compare(control,absolute,control_summary,absolute_summary,output):
    c=json.loads((control/'reference-protocol.json').read_text());a=json.loads((absolute/'reference-protocol.json').read_text())
    if c['initial_fields_sha256']!=a['initial_fields_sha256'] or c['acceptance_all_required']!=a['acceptance_all_required'] or c['numerical_pressure_relTol']!=.01 or a['numerical_pressure_relTol']!=0:raise ValueError('Frozen matched pair differs from declared test')
    for key in ['model','fluid','rpm_assumed','boundary_conditions','reference_configuration','pressure_absolute_tolerance','numerical_pressure_relaxation_after','source_mesh_gate_sha256','expected_cell_count']:
        if c[key]!=a[key]:raise ValueError('Paired physical/protocol hypothesis differs')
    for name in c['frozen_system_file_sha256']:
        if name!='system/fvSolution' and sha(control/name)!=sha(absolute/name):raise ValueError('Paired discretization/control differs')
    normalized=re.sub(r'(\bp\s*\{[^{}]*?\brelTol\s+)0\.01;',r'\g<1>0;',(control/'system/fvSolution').read_text())
    if normalized!=(absolute/'system/fvSolution').read_text():raise ValueError('Only pressure relTol may differ')
    partitions=[json.loads((case/'partition-preparation.json').read_text()) for case in [control,absolute]]
    if partitions[0]!=partitions[1] or not partitions[0]['all_initial_processor_files_hashes_match']:raise ValueError('Identical native initial MPI partition required')
    records={'control':audit_case(control,control_summary),'absolute':audit_case(absolute,absolute_summary)}
    supported=all(r['current_original_frozen_gates_passed'] for r in records.values());changes={}
    for key,old in records['control']['windows'][-1]['statistics'].items():
        new=records['absolute']['windows'][-1]['statistics'][key];difference=new['mean']-old['mean']
        changes[key]={'signed_mean_difference':difference,'percent_difference_relative_to_control_mean_magnitude':100*difference/abs(old['mean']) if old['mean'] else None,'control_iteration_CV':old['relative_std_if_nonzero_mean'],'absolute_iteration_CV':new['relative_std_if_nonzero_mean']}
    result={'status':'actual_D1_telemetry_audited','records':records,'both_original_frozen_flow_gates_passed':supported,'last20_descriptive_difference':changes,'performance_ranking_allowed':False,'physical_frequency_or_statistical_confidence_established':False,'historical_fine_admission_restored':False,'interpretation':'Deterministic steady-iteration variability and one linear-solver sensitivity only; no physical noise, independent-sample uncertainty, efficiency or installed-cooling conclusion. An admitted new diagnostic phase never retroactively supplies missing historical fine samples.','script_sha256':sha(Path(__file__))}
    output.write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['control','absolute','control_summary','absolute_summary','output']:p.add_argument(name,type=Path)
    a=p.parse_args();compare(a.control,a.absolute,a.control_summary,a.absolute_summary,a.output)
