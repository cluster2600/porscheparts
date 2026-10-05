#!/usr/bin/env python3
"""Audit complete fixed60 D2 pair; distinguish numerical gates and domain effect."""
import hashlib,json,math,re
from pathlib import Path
import numpy as np
from analyze_flow_balance import field_values,patch_block
from measurement_window import require_measurement_window


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def symmetric(a,b):
    denominator=max(abs(a),abs(b));return abs(a-b)/denominator if denominator>0 else None


def stats(x):return {'mean':float(x.mean()),'std':float(x.std()),'minimum':float(x.min()),'maximum':float(x.max()),'CV':float(x.std()/abs(x.mean())) if abs(x.mean())>0 else None}


def difference(v,a,b):
    dp=1.2*(b['p']-a['p']);du=np.linalg.norm(b['U']-a['U'],axis=1)
    return {'pressure_volume_RMS_Pa':float(np.sqrt(np.dot(v,dp*dp)/v.sum())),'pressure_abs_cell_p99_Pa':float(np.quantile(np.abs(dp),.99)),'pressure_max_abs_Pa':float(np.abs(dp).max()),'velocity_volume_RMS_m_s':float(np.sqrt(np.dot(v,du*du)/v.sum())),'velocity_abs_cell_p99_m_s':float(np.quantile(du,.99)),'velocity_max_m_s':float(du.max())}


def analyze(root,protocol_file,output):
    started=__import__('time').monotonic();p=json.loads(protocol_file.read_text());selections=np.load(root/'common-selections-private.npz',allow_pickle=False);v=selections['cellVolumes'];nc=len(v);reports={};fields={};used={}
    def table(case,name):
        files=list((case/'postProcessing'/name).glob('*/*.dat'))
        if len(files)!=1:raise ValueError('Exactly one native table required '+name)
        t=np.loadtxt(files[0],comments='#',ndmin=2)
        if not np.isfinite(t).all():raise ValueError('Finite native telemetry required')
        used[str(files[0].relative_to(root))]=sha(files[0]);return t
    for label in ['current','extended']:
        case=root/label;summary=json.loads((case/'flow-summary.json').read_text());used[label+'/flow-summary.json']=sha(case/'flow-summary.json');Q=table(case,'commonOutletFlux');P=table(case,'commonPressureBandMean');T=table(case,'rotorForces')
        all_expected=list(range(961,1021));require_measurement_window(all_expected,Q[Q[:,0]>=961],P[P[:,0]>=961],T[T[:,0]>=961],60)
        windows=[]
        for lo,hi in p['execution']['windows']:
            q=Q[(Q[:,0]>=lo)&(Q[:,0]<=hi)];pr=P[(P[:,0]>=lo)&(P[:,0]<=hi)];t=T[(T[:,0]>=lo)&(T[:,0]<=hi)];require_measurement_window(list(range(lo,hi+1)),q,pr,t,20)
            torque=t[:,9]+t[:,12];windows.append({'range':[lo,hi],'samples':len(q),'Q_m3_s':stats(q[:,1]),'pressure_Pa':stats(pr[:,1]*1.2),'torque_Nm':stats(torque),'power_W':stats(-torque*p['unchanged_physics']['rpm_assumed']*math.pi/30)})
        fields[label]={};actualnc=nc if label=='current' else 680596
        for iteration in [1000,1020]:
            checkpoint={}
            for name,components in [('p',1),('U',3)]:
                file=case/str(iteration)/name;values=field_values(file.read_text(),'internalField',actualnc,components)
                if not np.isfinite(values).all():raise ValueError('Finite complete checkpoint required')
                checkpoint[name]=values[:nc];used[str(file.relative_to(root))]=sha(file)
            fields[label][iteration]=checkpoint
        delta=difference(v,fields[label][1000],fields[label][1020]);last=windows[-1];prev=windows[-2];s=p['additional_stationarity_screen']
        relativeQ=symmetric(last['Q_m3_s']['mean'],prev['Q_m3_s']['mean']);relativeT=symmetric(last['torque_Nm']['mean'],prev['torque_Nm']['mean']);dp=abs(last['pressure_Pa']['mean']-prev['pressure_Pa']['mean'])
        checks={'common_flow_CV':last['Q_m3_s']['CV'] is not None and last['Q_m3_s']['CV']<=s['last_window_common_flow_CV_max'],'common_pressure_std':last['pressure_Pa']['std']<=s['last_window_common_pressure_std_Pa_max'],'between_windows_common_flow':relativeQ is not None and relativeQ<=s['between_last_two_window_mean_common_flow_relative_max'],'between_windows_torque':relativeT is not None and relativeT<=s['between_last_two_window_mean_torque_relative_max'],'between_windows_pressure':dp<=s['between_last_two_window_mean_pressure_difference_Pa_max'],'core_pressure_checkpoint_RMS':delta['pressure_volume_RMS_Pa']<=s['checkpoint1000_to1020_core_pressure_volume_RMS_Pa_max'],'core_velocity_checkpoint_RMS':delta['velocity_volume_RMS_m_s']<=s['checkpoint1000_to1020_core_velocity_volume_RMS_m_s_max']}
        # Evaluate core-plane reverse flux and far-boundary flux independently.
        text=(case/'1020/phi').read_text();far=field_values(patch_block(text,'outlet'),'value',4542,1)
        if label=='current':common=far
        else:
            mapping=np.load(case/'private-maps.npz',allow_pickle=False)['old_to_new_faces'];internalcount=int(re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)',text)[1]);allphi=field_values(text,'internalField',internalcount,1);common=allphi[mapping[selections['commonOutletFaceIds']]]
        flux_stats=lambda f:{'net_m3_s':float(f.sum()),'gross_forward_m3_s':float(f[f>0].sum()),'gross_reverse_m3_s':float(-f[f<0].sum()),'reverse_over_net':float(-f[f<0].sum()/abs(f.sum())) if f.sum()!=0 else None,'reversed_faces':int((f<0).sum())}
        roi={name:difference(v[selections[name]],{k:a[selections[name]] for k,a in fields[label][1000].items()},{k:a[selections[name]] for k,a in fields[label][1020].items()}) for name in ['commonPressureBand','commonOutletOwners','commonTipWake']}
        reports[label]={'original_numerical_checks':summary['criteria_checks'],'original_numerical_admission_supported':all(summary['criteria_checks'].values()) and summary['native_window_sample_count']==20 and summary['iterations_completed']==1020 and all(n==actualnc for n in summary['final_field_cell_counts'].values()),'original_max_initial_residuals':summary['maximum_initial_residual_last_window'],'windows':windows,'between_last_two_window_relative_Q':relativeQ,'between_last_two_window_relative_torque':relativeT,'between_last_two_window_abs_pressure_Pa':dp,'stationarity_checks':checks,'all_additional_stationarity_checks_pass':all(checks.values()),'core_checkpoint1000_to1020':delta,'fixed_zone_checkpoint_changes':roi,'final_common_plane_flux':flux_stats(common),'final_far_outlet_flux':flux_stats(far)}
        used[label+'/1020/phi']=sha(case/'1020/phi')
    A=reports['current']['windows'][-1];B=reports['extended']['windows'][-1];g=p['domain_comparison_screen'];q=symmetric(A['Q_m3_s']['mean'],B['Q_m3_s']['mean']);t=symmetric(A['torque_Nm']['mean'],B['torque_Nm']['mean']);power=symmetric(A['power_W']['mean'],B['power_W']['mean']);dp=abs(A['pressure_Pa']['mean']-B['pressure_Pa']['mean']);plimit=max(g['common_pressure_last20_difference_Pa_floor'],g['common_pressure_last20_relative_difference_max']*max(abs(A['pressure_Pa']['mean']),abs(B['pressure_Pa']['mean'])))
    comparable=all(r['original_numerical_admission_supported'] and r['all_additional_stationarity_checks_pass'] for r in reports.values());comparison_checks={'common_flow':q is not None and q<=g['common_flow_last20_relative_difference_max'],'rotor_torque':t is not None and t<=g['rotor_torque_and_input_power_last20_relative_difference_max'],'rotor_input_power':power is not None and power<=g['rotor_torque_and_input_power_last20_relative_difference_max'],'common_pressure':dp<=plimit}
    paired=difference(v,fields['current'][1020],fields['extended'][1020]);zones={name:difference(v[selections[name]],{k:a[selections[name]] for k,a in fields['current'][1020].items()},{k:a[selections[name]] for k,a in fields['extended'][1020].items()}) for name in ['commonPressureBand','commonOutletOwners','commonTipWake']}
    result={'status':'inconclusive_domain_comparison' if not comparable else 'bulk_observables_within_declared_single_extension_bands' if all(comparison_checks.values()) else 'domain_dependent_model_operating_point','both_cases_completed_exact60':True,'both_cases_numerical_and_stationarity_admitted':comparable,'reports':reports,'last20_comparison':{'relative_common_Q_difference':q,'relative_rotor_torque_difference':t,'relative_rotor_power_difference':power,'abs_common_pressure_difference_Pa':dp,'common_pressure_limit_Pa':plimit,'domain_checks_descriptive_even_when_inconclusive':comparison_checks},'core_paired1020_field_differences':paired,'fixed_zone_paired1020_differences':zones,'source_sha256':used,'protocol_sha256':sha(protocol_file),'analysis_script_sha256':sha(Path(__file__)),'analysis_wall_seconds':__import__('time').monotonic()-started,'domain_independence_established':False,'physical_validation_established':False,'local_fields_qualified':False,'airflow_improvement_proven':False,'native_iteration_variability_is_not_physical_time_or_experimental_uncertainty':True,'pressure_statistic_is_not_fan_port_pressure_rise':True}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'last20_comparison':result['last20_comparison']}));return result


if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser(description=__doc__)
    for name in ['root','protocol','output']:a.add_argument(name,type=Path)
    x=a.parse_args();analyze(x.root,x.protocol,x.output)
