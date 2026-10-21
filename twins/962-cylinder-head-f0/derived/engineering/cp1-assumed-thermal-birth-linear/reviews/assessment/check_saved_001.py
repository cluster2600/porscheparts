"""Review saved assessment arithmetic/closure; no assessor import or physics replay."""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
E='work/962-engineering/'
ACTUAL=E+'cp1-assumed-thermal-birth-linear-assessment-prep-001/actual-contract.json'
CHILD=E+'cp1-assumed-thermal-birth-linear-assessment-child-peer-001/review.json'
OUT=E+'cp1-assumed-thermal-birth-linear-assessment-001/'
RUN=E+'cp1-assumed-thermal-birth-linear-assessment-root-execution-001/'
NATIVE=E+'cp1-assumed-thermal-birth-linear-001/'
EXPECTED={ACTUAL:'5128445ee07da6844bc79c476a3e488a442e22ef3fb756073a9d306916087404',
 CHILD:'e68cd22c470f127dddc465af485764724669534cc2775b4d5c9a97679488de37',
 OUT+'assessment.json':'198ae20f6baa27a726b17f3924659b8c1e0613e9a5b1e161ad8f6ef3b5107dbf',
 RUN+'closed-result.json':'7b28e1d6374a1b26e710a95da20330eb3366e0e5f3b2dd290b8a89d4546112dd',
 RUN+'result-review.json':'f664c6fd639fac07a84f7ef45ed0970d7a74951bd83bec246d1796680f536d48'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads((ROOT/p).read_text())
def need(v,label):
    if not v:raise AssertionError(label)
def bits(v):return struct.pack('>d',v)

def main():
    actual=load(ACTUAL);closed=load(RUN+'closed-result.json');launch=load(RUN+'launch.json');assessment=load(OUT+'assessment.json')
    pins=dict(actual['input_sha256']);need(len(pins)==614,'614 saved inputs')
    pins.update(EXPECTED)
    for name in ['launch.json','stdout.log','stderr.log']:pins[RUN+name]=sha(ROOT/RUN/name)
    pins[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    before={}
    for name,digest in pins.items():
        p=ROOT/name;need(p.is_file() and not p.is_symlink() and p.suffix not in ['.msh','.bin','.so','.dylib'],'explicit saved file')
        before[name]=sha(p);need(before[name]==digest,'digest '+name)
    need(set(p.name for p in (ROOT/OUT).iterdir())=={'assessment.json'},'one output file')
    need((ROOT/OUT/'assessment.json').stat().st_size==112952 and closed['assessment_output_files']=={'assessment.json':{'sha256':EXPECTED[OUT+'assessment.json'],'bytes':112952}},'result inventory')
    native_inventory=actual['native_output_inventory'];need(len(native_inventory)==502 and sum(r['bytes'] for r in native_inventory.values())==5881859,'native closure')
    for name,row in native_inventory.items():need(before[NATIVE+name]==row['sha256'] and (ROOT/NATIVE/name).stat().st_size==row['bytes'],'native immutable inventory')
    need(closed['actual_sha256']==EXPECTED[ACTUAL] and closed['child_peer_sha256']==EXPECTED[CHILD] and closed['root_launch_sha256']==sha(ROOT/RUN/'launch.json'),'root joins')
    need(launch['actual_sha256']==EXPECTED[ACTUAL] and launch['child_peer_sha256']==EXPECTED[CHILD] and launch['argv']==actual['argv'],'launch argv')
    need(launch['new_owned_session'] is True and launch['assessment_pid']==launch['assessment_pgid']==closed['assessment_pid'],'owned process association')
    need(closed['returncode']==0 and closed['assessment_reaped'] is True and closed['observed_leader_absent'] is True and closed['stop_reason'] is None and closed['error'] is None,'root lifecycle')
    need(closed['universal_descendant_absence_claimed'] is False and closed['all614_inputs_actual_peer_python_before_after_unchanged'] is True and closed['all502_original_native_output_files_unchanged'] is True,'root limited observations')
    for stream in ['stdout','stderr']:need(closed[stream+'_sha256']==sha(ROOT/RUN/(stream+'.log')),'stream hash')
    need(closed['output_plus_logs_bytes']==112952+sum((ROOT/RUN/n).stat().st_size for n in ['stdout.log','stderr.log'])==113104,'output/log count')
    samples=closed['RSS_samples'];need(len(samples)==33 and max(r['RSS_bytes'] for r in samples)==closed['maximum_sampled_owned_leader_RSS_bytes']==44990464 and closed['true_peak'] is False,'sampled RSS')
    need(all(closed[k] is False for k in ['automatic_retry','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized']),'closed authority limits')
    card=load(NATIVE+'card.json');contract=load(NATIVE+'frozen-contract.json');native=load(NATIVE+'native-execution.json')
    need(assessment['native_receipt_sha256']==sha(ROOT/NATIVE/'native-execution.json')=='a210f0ef6d41686ce795b76d7d43fc17aa320038cfabd601d0250ae8feb2b673','receipt identity')
    need(assessment['frozen_contract_sha256']==actual['numerical_reference_sha256']==sha(ROOT/NATIVE/'frozen-contract.json')=='13a12dc586cf773a0a4b0a2777276d062d60d2e7c67aa7357e6581fd83f4fddd','reference')
    need(assessment['assessor_sha256']==actual['assessor_sha256']==contract['assessor_sha256']=='0548fcbf6eba737aaaf816abbfbfd0511b5b8fb266aa10c34a1f5817eef0e338','assessor')
    need(contract['card']==card and assessment['classification']==card['classification']=='HYPOTHETICAL_SOFTWARE_VERIFICATION_ONLY','hypothetical card')
    need(native['passed'] is False and native['independent_assessment_performed'] is False,'old native receipt unchanged')
    need(assessment['passed'] is True and assessment['failed_checks']==[] and assessment['level']==2 and assessment['dt_s']==.0025 and assessment['native_steps']==160,'saved passed level2')
    traces=assessment['traces'];need(len(traces)==160 and [r['step'] for r in traces]==list(range(1,161)),'complete ordered traces')
    expected_fields={'step','time_s','active_volume_m3','enthalpy_J','birth_enthalpy_J','centered_step_enthalpy_increment_J','cumulative_centered_heat_response_J','continuous_source_energy_J','continuous_energy_error_J','relative_continuous_energy_error','finite_box_power_W','quadrature_power_W','BE_capacity_correction_J','temperature_min_K','temperature_max_K'}
    increments=[];trace_rows=[];continuous=[];energy_errors=[];box_errors=[]
    for i,row in enumerate(traces,1):
        need(set(row)==expected_fields and all(type(v) in (float,int) and math.isfinite(v) for v in row.values()),'trace finite field closure')
        need(bits(row['time_s'])==bits(i*.0025) and row['active_volume_m3']==(1 if i<80 else 2),'time/declared active volume')
        need(row['BE_capacity_correction_J']==0 and row['continuous_source_energy_J']>0 and row['finite_box_power_W']>0 and row['quadrature_power_W']>0,'saved finite source fields')
        need(card['predeclared_tolerances']['temperature_lower_K']<=row['temperature_min_K']<=row['temperature_max_K']<=card['predeclared_tolerances']['temperature_upper_K'],'recorded temperature bounds')
        increments.append(row['centered_step_enthalpy_increment_J']);need(bits(math.fsum(increments))==bits(row['cumulative_centered_heat_response_J']),'saved cumulative arithmetic')
        defect=row['cumulative_centered_heat_response_J']-row['continuous_source_energy_J'];relative=defect/max(abs(row['continuous_source_energy_J']),1e-12)
        need(bits(defect)==bits(row['continuous_energy_error_J']) and bits(relative)==bits(row['relative_continuous_energy_error']),'saved defect/normalization arithmetic')
        energy=row['centered_step_enthalpy_increment_J']-.0025*row['quadrature_power_W']+row['BE_capacity_correction_J'];box=(row['quadrature_power_W']-row['finite_box_power_W'])/row['finite_box_power_W']
        continuous.append(abs(relative));energy_errors.append(abs(energy));box_errors.append(abs(box))
        need(row['birth_enthalpy_J']==(0 if i<80 else traces[79]['birth_enthalpy_J']),'stored birth accounting transition')
        trace_rows.append(dict(step=i,continuous_relative_abs=abs(relative),saved_step_energy_abs_J=abs(energy),saved_finite_box_relative_abs=abs(box)))
    maximums=assessment['max_error_by_check'];tol=card['predeclared_tolerances']
    thresholds={'initial_temperature':tol['node_history_K'],'active_node_count':0,'existing_nodal_history':tol['node_history_K'],'new_node_count':0,'new_node_birth_temperature':tol['node_history_K'],'k_T_element_average':tol['material_property_absolute'],'cp_T_element_average':tol['material_property_absolute'],'moving_source_element_average':tol['source_cell_average_relative'],'finite_box_gaussian_power':tol['finite_box_power_relative'],'nonlinear_BE_enthalpy_identity':tol['corrected_step_energy_absolute_J'],'nonuniform_final_temperature':0,'finest_continuous_energy_error':tol['finest_continuous_energy_relative']}
    need(set(maximums)==set(thresholds) and all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=thresholds[k] for k,v in maximums.items()),'all12 reported maxima within exact card thresholds')
    need(bits(max(continuous))==bits(assessment['max_continuous_relative_energy_error'])==bits(maximums['finest_continuous_energy_error']),'saved continuous maximum')
    need(bits(max(energy_errors))==bits(maximums['nonlinear_BE_enthalpy_identity']) and bits(max(box_errors))==bits(maximums['finite_box_gaussian_power']),'saved per-step/box maxima')
    property_rows=79*128+81*256
    check_count=1+160*4+property_rows*3+2+2
    need(check_count==assessment['checks_count']==93189,'source-derived93,189 count')
    printed=load(RUN+'stdout.log');need(printed=={k:assessment[k] for k in ['passed','level','dt_s','checks_count','failed_checks','max_continuous_relative_energy_error']},'stdout summary exact')
    root_review=load(RUN+'result-review.json');need(root_review['assessment_sha256']==EXPECTED[OUT+'assessment.json'] and root_review['closure_sha256']==EXPECTED[RUN+'closed-result.json'] and root_review['max_error_by_check']==maximums,'root result association')
    after={name:sha(ROOT/name) for name in pins};need(before==after,'all saved pins stable')
    result=dict(schema='962-cp1-LINEAR-assessment-independent-saved-result-check/v1',status='PASS_SAVED_ASSESSMENT_BINDINGS_AND_TRACE_ARITHMETIC',input_sha256=before,input_sha256_after=after,all_saved_inputs_unchanged=True,
      assessment_output_inventory=closed['assessment_output_files'],native_files_unchanged=502,native_bytes_unchanged=5881859,actual614_map_verified=True,trace_count=160,reported_check_count=93189,derived_count_formula='1 initial +160*4 base step checks +3*(79*128+81*256) material/source samples +2 birth +2 final checks',
      exact_card_thresholds=thresholds,reported_maxima=maximums,all_reported_maxima_within_unchanged_thresholds=True,all160_saved_trace_arithmetic=trace_rows,
      independently_checked='Full byte/source/actual/receipt/root/CLI/lifecycle associations; complete trace shape/time/volume/finite values; saved cumulative/defect/relative/per-step energy/box-power arithmetic; reported12 maxima against unchanged card thresholds and count formula. No raw-field Gaussian/HEX/enthalpy integration or continuous-source quadrature recomputation.',
      assessor_attribution='The93189 individual checks and raw-field source/energy computations are outputs of the bound unchanged0548 assessor, not independently repeated here. This checker checks complete saved summaries/traces and provenance only.',
      root_lifecycle_attribution=dict(returncode=0,reaped=True,observed_leader_absent=True,universal_descendant_absence=False,wall_seconds=closed['wall_seconds'],RSS_sample_count=33,maximum_sampled_owned_leader_RSS_bytes=44990464,true_peak=False),
      one_level_only_no_temporal_convergence=True,original_Newton_nonlinear_criterion_not_checked=True,assessor_imported_or_rerun=False,native_or_PDE_replay=False,engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False)
    output=HERE/'independent-saved-check.json';need(not output.exists(),'fresh checker output');output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'],saved_pins=len(pins),traces=160,reported_checks=93189,failed_checks=0,assessor_rerun=False)))

if __name__=='__main__':main()
