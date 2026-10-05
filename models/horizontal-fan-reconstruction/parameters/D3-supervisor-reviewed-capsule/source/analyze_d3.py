#!/usr/bin/env python3
"""Native20-window relaxation contrast; failed prerequisites cannot qualify flow."""
import argparse,hashlib,json,math,re,time
from pathlib import Path
import numpy as np
from analyze_d2_result import native_table,stats,symmetric,difference
from analyze_flow_balance import field_values,patch_block
from summarize_reference_flow import summarize
from measurement_window import require_measurement_window
from audit_d3_checkpoint import audit
from d3_guards import LABELS,validate_plan,check_complete20


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prerequisites(reports):
    numerical={'initial_time_matches_frozen_continuation','residual_p','residual_U','residual_turbulence','mass_balance',
               'flow_stability','torque_stability','declared_flow_direction','complete_finite_fields','finite_measurements'}
    stationarity={'common_flow_CV','common_pressure_std','between_windows_common_flow','between_windows_torque',
                  'between_windows_pressure','core_pressure_checkpoint_RMS','core_velocity_checkpoint_RMS'}
    if set(reports)!=set(LABELS):raise ValueError('Both native diagnostic arms required')
    for report in reports.values():
        if set(report['original_numerical_checks'])!=numerical or set(report['stationarity_checks'])!=stationarity:raise ValueError('All original prerequisites required')
    return all(all(r['original_numerical_checks'].values()) and all(r['stationarity_checks'].values()) for r in reports.values())


def compare(output,previous,selections,plan_file):
    started=time.monotonic();plan=json.loads(plan_file.read_text());validate_plan(plan);selected=np.load(selections,allow_pickle=False);v=selected['cellVolumes'];used={};states={};reports={}
    def table(case,name,lo,hi):
        candidates=list((case/'postProcessing'/name).glob('*/*.dat'))
        if len(candidates)!=1:raise ValueError('One separate raw native table per stage required')
        f=candidates[0];t=native_table(f);rows=t[(t[:,0]>=lo)&(t[:,0]<=hi)]
        require_measurement_window(list(range(lo,hi+1)),rows,rows,rows,20)
        used[str(case.name)+'/'+name]=sha(f);return rows
    def window(case,lo,hi):
        q=table(case,'commonOutletFlux',lo,hi);p=table(case,'commonPressureBandMean',lo,hi);t=table(case,'rotorForces',lo,hi)
        require_measurement_window(list(range(lo,hi+1)),q,p,t,20)
        return {'iterations':[lo,hi],'samples':20,'Q_m3_s':stats(q[:,1]),'pressure_Pa':stats(p[:,1]*1.2),'torque_Nm':stats(t[:,9]+t[:,12])}
    def fields(directory):
        state={}
        for name,c in [('p',1),('U',3)]:
            f=directory/name;values=field_values(f.read_text(),'internalField',680596,c)
            if not np.isfinite(values).all():raise ValueError('Finite complete serial checkpoint required')
            state[name]=values[:453496];used[str(directory.parent.name)+'/'+directory.name+'/'+name]=sha(f)
        return state
    def fluxes(case):
        f=case/'1040/phi';text=f.read_text();n=re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)',text)
        if not n:raise ValueError('Native surface flux required')
        internal=field_values(text,'internalField',int(n[1]),1);mapping=np.load(previous/'private-maps.npz',allow_pickle=False)['old_to_new_faces']
        common=internal[mapping[selected['commonOutletFaceIds']]];far=field_values(patch_block(text,'outlet'),'value',4542,1)
        def record(a):
            if not np.isfinite(a).all() or a.sum()==0:raise ValueError('Finite nonzero net native flux required')
            return {'net_m3_s':float(a.sum()),'gross_reverse_m3_s':float(-a[a<0].sum()),'reverse_over_net':float(-a[a<0].sum()/abs(a.sum())),'reversed_faces':int((a<0).sum())}
        used[case.name+'/1040/phi']=sha(f);return {'common_plane':record(common),'far_outlet':record(far)}
    baseline=window(previous,1001,1020);initial=fields(previous/'1020');screen=plan['additional_stationarity_screen']
    for label in LABELS:
        case=output/label;checkpoint=audit(case);complete=check_complete20((case/'log.foamRun').read_text())
        summary=summarize(case,case/'flow-summary.json');last=window(case,1021,1040);states[label]=fields(case/'1040');change=difference(v,initial,states[label])
        dq=symmetric(last['Q_m3_s']['mean'],baseline['Q_m3_s']['mean']);dt=symmetric(last['torque_Nm']['mean'],baseline['torque_Nm']['mean']);dp=abs(last['pressure_Pa']['mean']-baseline['pressure_Pa']['mean'])
        checks={'common_flow_CV':last['Q_m3_s']['CV'] is not None and last['Q_m3_s']['CV']<=screen['last_window_common_flow_CV_max'],
                'common_pressure_std':last['pressure_Pa']['std']<=screen['last_window_common_pressure_std_Pa_max'],
                'between_windows_common_flow':dq is not None and dq<=screen['between_last_two_window_mean_common_flow_relative_max'],
                'between_windows_torque':dt is not None and dt<=screen['between_last_two_window_mean_torque_relative_max'],
                'between_windows_pressure':dp<=screen['between_last_two_window_mean_pressure_difference_Pa_max'],
                'core_pressure_checkpoint_RMS':change['pressure_volume_RMS_Pa']<=screen['checkpoint1020_to1040_core_pressure_volume_RMS_Pa_max'],
                'core_velocity_checkpoint_RMS':change['velocity_volume_RMS_m_s']<=screen['checkpoint1020_to1040_core_velocity_volume_RMS_m_s_max']}
        first=[]
        for block in re.split(r'(?m)^Time = ',(case/'log.foamRun').read_text())[1:]:
            m=re.search(r'Solving for p, Initial residual = ([0-9.eE+-]+)',block)
            if not m:raise ValueError('Native pressure residual required at every completed iteration')
            first.append(float(m[1]))
        if first[0]<=0:raise ValueError('Defined residual decay ratio required')
        roi={name:difference(v[selected[name]],{k:a[selected[name]] for k,a in initial.items()},{k:a[selected[name]] for k,a in states[label].items()}) for name in ['commonPressureBand','commonOutletOwners','commonTipWake']}
        reports[label]={'pressure_relaxation':plan['cases'][label]['pressure_relaxation'],'complete_native_iterations':complete,
                        'native1040_checkpoint':checkpoint,'original_numerical_checks':summary['criteria_checks'],
                        'all_original_numerical_checks_pass':all(summary['criteria_checks'].values()),
                        'stationarity_checks':checks,'all_additional_stationarity_checks_pass':all(checks.values()),
                        'native_last20':last,'initial1020_to_final1040_core_changes':change,'fixed_zone_changes':roi,
                        'between_windows_relative_Q':dq,'between_windows_relative_torque':dt,'between_windows_absolute_pressure_Pa':dp,
                        'first_pressure_initial_residual_by_iteration':[{'iteration':n,'residual':r} for n,r in zip(complete,first)],
                        'last_over_first_pressure_initial_residual':first[-1]/first[0],
                        'maximum_initial_residual_last20':summary['maximum_initial_residual_last_window'],
                        'final_flux':fluxes(case),'summary_sha256':sha(case/'flow-summary.json')}
    control,candidate=[reports[label] for label in LABELS]
    lower_variance=candidate['native_last20']['pressure_Pa']['std']<control['native_last20']['pressure_Pa']['std']
    slower=candidate['last_over_first_pressure_initial_residual']>control['last_over_first_pressure_initial_residual']
    result={'status':'completed_equal_work_relaxation_diagnostic_only','reports':reports,'baseline_native20':baseline,
            'both_numerical_and_stationarity_prerequisites_pass':prerequisites(reports),
            'descriptive_contrast':{'candidate_pressure_std_lower':lower_variance,'candidate_fractional_residual_decay_slower':slower,
                'variance_lower_but_residual_decay_slower_is_not_admission':lower_variance and slower,
                'paired1040_core_field_difference':difference(v,states[LABELS[0]],states[LABELS[1]])},
            'source_sha256':used,'plan_sha256':sha(plan_file),'selections_sha256':sha(selections),'script_sha256':sha(Path(__file__)),
            'wall_seconds':time.monotonic()-started,'physical_unsteadiness_demonstrated':False,'domain_independence_established':False,
            'physical_validation_established':False,'airflow_improvement_proven':False,'numeric_iteration_variability_is_not_physical_time':True,
            'no_further_continuation_or_retry':True}
    (output/'D3-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print('Native D3 diagnostic archived; no physical or airflow qualification');return result


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ['output','previous','selections','plan']:cli.add_argument(name,type=Path)
    a=cli.parse_args();compare(a.output,a.previous,a.selections,a.plan)
