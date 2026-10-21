"""Read completed audit receipts and compare matched phase/time states; never solve."""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ENER_TOL=0.001
PIOLA_TOL=0.0001
METRICS=('displacement_max_mm','VM_max_MPa','PEEQ_max','plastic_quadrature_volume_mm3',
         'spring_energy_Nmm','CCX_solid_internal_energy_Nmm','external_incremental_trapezoid_work_Nmm',
         'work_relative_to_gross_error')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def check_frames(frames,count,denominator):
    if not isinstance(frames,list) or len(frames)!=count:raise ValueError('Actual state count differs from the fixed comparison schedule')
    for i,row in enumerate(frames,1):
        t=Fraction(str(row['total_time']));expected=Fraction(i,denominator)
        factor=t if t<=1 else 2-t
        if t!=expected or Fraction(str(row['load_factor']))!=factor:raise ValueError('A phase/time/load-factor identity differs')
    return {Fraction(str(row['total_time'])):row for row in frames}


def check_audits(analysis,work,count,denominator):
    a=check_frames(analysis['frames'],count,denominator);w=check_frames(work['frames'],count,denominator)
    if analysis['work_relative_tolerance']!=ENER_TOL or work['relative_work_tolerance']!=PIOLA_TOL:
        raise ValueError('An energy admission threshold changed')
    if not all(analysis.get(k) is True for k in ['target_load_factor_reached','planned_path_complete','unloading_complete']):
        raise ValueError('The load/unload path is incomplete')
    ener=[];piola=[];positive=[]
    for t,row in a.items():
        if not all(math.isfinite(row[k]) for k in METRICS):raise ValueError('A reported mechanical scalar is nonfinite')
        if row['PEEQ_max']<0 or row['work_relative_to_gross_error']<0:raise ValueError('Negative PEEQ or energy error')
        p=w[t]
        if not math.isfinite(p['relative_to_gross_work']) or p['relative_to_gross_work']<0 or not math.isfinite(p['minimum_detF_at_Gauss']):raise ValueError('Invalid independent work scalar')
        ep=row['work_relative_to_gross_error']<=ENER_TOL;pp=p['relative_to_gross_work']<=PIOLA_TOL
        if p['work_pass'] is not pp:raise ValueError('Frame work flag contradicts its scalar')
        ener.append(ep);piola.append(pp);positive.append(p['minimum_detF_at_Gauss']>0)
    if analysis['all_frames_ENER_diagnostic_pass'] is not all(ener) or work['all_frames_pass'] is not all(piola):
        raise ValueError('An aggregate work flag contradicts its states')
    if analysis['incremental_work_diagnostic_pass'] is not ener[-1]:raise ValueError('Final-only ENER flag differs')
    if analysis['maximum_ENER_relative_to_gross_error']!=max(row['work_relative_to_gross_error'] for row in a.values()):
        raise ValueError('Maximum ENER summary contradicts states')
    limit=analysis['measured_plastic_domain_max']
    if not math.isfinite(limit) or limit<=0:raise ValueError('Invalid measured plastic domain')
    domain=max(row['PEEQ_max'] for row in a.values())<=limit
    if analysis['within_measured_pre_necking_domain'] is not domain:raise ValueError('Material-domain flag contradicts states')
    residual=analysis['unloaded_residual']
    if residual!=analysis['frames'][-1]:raise ValueError('Residual is not the actual final unloaded state')
    return a,w,dict(ENER_all_states_pass=all(ener),Piola_all_states_pass=all(piola),positive_detF_all_states=all(positive),within_measured_domain=domain,
        ENER_failing_times=[str(t) for t,ok in zip(a,ener) if not ok],Piola_failing_times=[str(t) for t,ok in zip(a,piola) if not ok])


def delta(old,new):
    return dict(baseline=old,refined=new,difference=new-old,relative_difference=(new-old)/old if old!=0 else None)


def compare_reports(old_a,old_p,new_a,new_p):
    oa,op,old_gates=check_audits(old_a,old_p,16,8)
    na,np,new_gates=check_audits(new_a,new_p,32,16)
    if old_a['constitutive_model']!=new_a['constitutive_model'] or old_a['measured_plastic_domain_max']!=new_a['measured_plastic_domain_max']:
        raise ValueError('The material model/domain differs')
    matched=[]
    for t,old in oa.items():
        new=na[t]
        matched.append(dict(total_time=str(t),phase='loading' if t<=1 else 'unloading',load_factor=str(Fraction(str(new['load_factor']))),
            metrics={k:delta(old[k],new[k]) for k in METRICS},Piola_relative_to_gross_work=delta(op[t]['relative_to_gross_work'],np[t]['relative_to_gross_work'])))
    final_old=old_a['unloaded_residual'];final_new=new_a['unloaded_residual']
    numeric_pass=all(new_gates[k] for k in ['ENER_all_states_pass','Piola_all_states_pass','positive_detF_all_states','within_measured_domain'])
    return dict(status='comparison_completed_all_refined_numeric_checks_pass' if numeric_pass else 'comparison_completed_refined_numeric_checks_refused',
        global_admission=False,mesh_convergence_claimed=False,baseline_states=16,refined_states=32,matched_phase_time_states=len(matched),
        baseline_checks=old_gates,refined_checks=new_gates,thresholds=dict(ENER=ENER_TOL,Piola=PIOLA_TOL),matched_states=matched,
        worst_ENER_relative_to_gross=delta(max(r['work_relative_to_gross_error'] for r in oa.values()),max(r['work_relative_to_gross_error'] for r in na.values())),
        worst_Piola_relative_to_gross=delta(max(r['relative_to_gross_work'] for r in op.values()),max(r['relative_to_gross_work'] for r in np.values())),
        unloaded_residual={**{k:delta(final_old[k],final_new[k]) for k in ['displacement_max_mm','VM_max_MPa','PEEQ_max','plastic_quadrature_volume_mm3']},
            'baseline_peak_node':final_old.get('displacement_peak_node'),'refined_peak_node':final_new.get('displacement_peak_node'),
            'acceptance_threshold':None,'interpretation':'Measured difference only; no residual-displacement acceptance or convergence tolerance was invented.'},
        numerical_interpretation='One step halving supplies a sensitivity comparison, not a mesh-convergence proof, asymptotic order or material qualification.')


def load_plan():
    path=HERE/'plan.json';digest=sha(path);plan=json.loads(path.read_text())
    if sha(__file__)!=plan['comparison_source_sha256']:raise ValueError('Comparison source changed')
    for p,value in plan['files_sha256'].items():
        if sha(p)!=value:raise ValueError('A frozen preparation/audit/reference source changed')
    return path,digest,plan


def preflight(plan):
    case=Path(plan['case_directory']);execution_path=Path(plan['execution_receipt']);execution=json.loads(execution_path.read_text())
    if (execution.get('status')!='solver_executed_no_numeric_admission' or execution.get('actual_container_exit_code')!=0 or
        execution.get('container_removed') is not True or execution.get('input_hashes_unchanged') is not True or
        execution.get('plan_unchanged') is not True or execution.get('within_global_budget') is not True or execution['wall_seconds']>3600 or
        execution.get('plan_sha256')!=plan['supervision_plan_sha256']):raise ValueError('No successful completed owned solve is bound to this preparation')
    runtime_path=case/'runtime.json';runtime=json.loads(runtime_path.read_text())
    if (sha(runtime_path)!=execution.get('runtime_json_sha256') or runtime['name']!=plan['case_name'] or runtime.get('status')!='executed' or
        runtime['image']!=plan['image'] or runtime['ccx_binary_sha256']!=plan['binary_sha256'] or
        runtime['supervision_plan_sha256']!=plan['supervision_plan_sha256'] or runtime['plan_sha256']!=sha(case/'plan.json')):
        raise ValueError('Native runtime binding differs')
    actual={str(execution_path):sha(execution_path),str(runtime_path):sha(runtime_path)}
    if set(execution['outputs'])!={plan['case_name']+'.'+suffix for suffix in ['dat','frd','sta','cvg','log']}:
        raise ValueError('Completed native output set differs')
    for name,metadata in execution['outputs'].items():
        if Path(name).name!=name:raise ValueError('Native output reference escapes the case')
        p=case/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size!=metadata['bytes'] or not metadata['bytes'] or sha(p)!=metadata['sha256']:raise ValueError('A completed native output changed')
        actual[str(p)]=metadata['sha256']
    if runtime['mesh_sha256']!=sha(case/'mesh.inp') or runtime['input_sha256']!=sha(case/(plan['case_name']+'.inp')):
        raise ValueError('Native runtime inputs changed')
    spec=importlib.util.spec_from_file_location('private_refined_sta_checker',plan['sta_checker']);checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    schedule=checker.check_sta(case/(plan['case_name']+'.sta'))
    check_frames(schedule['states'],32,16)
    return actual,runtime,schedule


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--preflight',action='store_true');args=parser.parse_args()
    output=HERE/('preflight.json' if args.preflight else 'comparison.json')
    if output.exists() or output.is_symlink():raise FileExistsError('Use a fresh audit receipt path')
    plan_path,plan_hash,plan=load_plan();report=None;bound={}
    try:
        bound,runtime,schedule=preflight(plan)
        if args.preflight:
            for key in ['refined_analysis','refined_work']:
                p=Path(plan[key])
                if p.exists() or p.is_symlink():raise FileExistsError('Separate audit output is not fresh')
            report=dict(status='completed_native_solve_verified_for_separate_audits',global_admission=False,native_schedule=schedule)
        else:
            paths={k:Path(plan[k]) for k in ['baseline_analysis','baseline_work','refined_analysis','refined_work']}
            for p in paths.values():bound[str(p)]=sha(p)
            data={k:json.loads(p.read_text()) for k,p in paths.items()}
            case=Path(plan['case_directory']);raw_hash=bound[str(case/(plan['case_name']+'.dat'))]
            new_a=data['refined_analysis'];new_p=data['refined_work']
            if (new_a['runtime_sha256']!=bound[str(case/'runtime.json')] or new_p['runtime_sha256']!=bound[str(case/'runtime.json')] or
                new_p['solver_dat_sha256']!=raw_hash or new_a['inputs_sha256'][plan['case_name']+'.dat']!=raw_hash or
                new_a['constitutive_model']!=runtime['constitutive_model']):raise ValueError('New audits do not bind the actual refined solve')
            if (new_a['source_sha256']!=plan['files_sha256'][plan['analysis_source']] or
                new_p['source_sha256']!=plan['files_sha256'][plan['work_source']] or
                new_p['field_parser_sha256']!=new_a['source_sha256'] or
                new_p['mesh_sha256']!=sha(case/'mesh.inp') or new_p['material_curve_sha256']!=sha(case/'material-curve.inp') or
                any(new_a['inputs_sha256'][n]!=sha(case/n) for n in ['mesh.inp',plan['case_name']+'.inp',plan['case_name']+'.sta'])):
                raise ValueError('Audit sources, mesh, deck, schedule or material bindings differ')
            report=compare_reports(data['baseline_analysis'],data['baseline_work'],new_a,new_p)
            report['native_schedule']=schedule
    except BaseException as error:
        report=dict(status='postprocess_refused_no_admission',global_admission=False,error_type=type(error).__name__,error=str(error))
    try:
        if sha(plan_path)!=plan_hash or any(sha(p)!=digest for p,digest in {**plan['files_sha256'],**bound}.items()):
            raise ValueError('Evidence changed during postprocessing')
        report['bound_files_unchanged']=True
    except BaseException as error:
        report=dict(status='postprocess_refused_no_admission',global_admission=False,error_type=type(error).__name__,error=str(error),bound_files_unchanged=False)
    report.update(plan_sha256=plan_hash,source_sha256=sha(__file__),evidence_sha256=bound)
    with output.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':report['status'],'output':str(output),'sha256':sha(output)}))
    return 0 if report['status'] in ['completed_native_solve_verified_for_separate_audits','comparison_completed_all_refined_numeric_checks_pass'] else 1


if __name__=='__main__':raise SystemExit(main())
