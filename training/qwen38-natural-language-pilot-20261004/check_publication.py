"""Regrade published exposed responses offline; no model/baseline/runtime rerun."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
VERIFIER_SHA = '347de31ed978be6569e42eceb3ea75d2c7fe038454fa86bb39fbb852d09a0fde'
verifier_path = HERE / 'parameter_verifier.py'
if hashlib.sha256(verifier_path.read_bytes()).hexdigest() != VERIFIER_SHA:
    raise ValueError('Published pure verifier bytes changed')
spec = importlib.util.spec_from_file_location('published_spacer_parameter_verifier', verifier_path)
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

EXPECTED_CASES = [('nl-next-01', 'en', 'explicit_control', 'inner diameter=20 mm; thickness=3 mm; outer diameter=45 mm', False, True), ('nl-next-02', 'fr', 'explicit_control', 'épaisseur=3 mm; diamètre intérieur=20 mm; diamètre extérieur=40 mm', False, True), ('nl-next-03', 'en', 'relative_reduction', 'The current synthetic spacer is 45 mm outside, 20 mm at the bore and 3 mm thick. Reduce only its outside diameter by 5 mm and retain the other two dimensions.', False, False), ('nl-next-04', 'fr', 'change_bore', 'Dans cet exemple synthétique, le diamètre extérieur actuel est 45 mm, le diamètre d’alésage 18 mm et l’épaisseur 3 mm. Remplace seulement le diamètre d’alésage par 20 mm.', False, False), ('nl-next-05', 'en', 'undecided_alternatives', 'For one final synthetic spacer, the outside diameter could be 40 mm or 45 mm, with a 20 mm bore and 3 mm thickness. Neither outside-diameter option has been selected.', True, True), ('nl-next-06', 'fr', 'missing_bore', 'Pour cet exemple synthétique, le diamètre extérieur est 40 mm et l’épaisseur 3 mm. Le diamètre intérieur reste inconnu ; aucune mesure ni valeur par défaut ne peut lui être attribuée.', True, True), ('nl-next-07', 'en', 'invalid_larger_bore', 'outer diameter=40 mm; inner diameter=45 mm; thickness=3 mm', True, True), ('nl-next-08', 'fr', 'unsupported_unit', 'diamètre extérieur=40 pouces; diamètre intérieur=20 pouces; épaisseur=3 pouces', True, True)]
PROPOSAL_OD = (45, 40, 40, 45)
NONPROPOSALS = (('needs_clarification','conflicting_request'), ('needs_clarification','missing_dimension'),
               ('rejected','out_of_scope'), ('rejected','unsupported_unit'))
TOKEN_COUNTS = (77,77,77,77,41,40,38,37)
REQUESTS_SHA = '138cffa4456312328dd79c364ba6d64b454c8932c0062bf9edf0f13165b0bc42'
SYSTEM_SHA = '5d1dfa8a4db3ad196003bdc5b15bd3b10ae0fda624b29db43d0d95def2cda47a'
FORBIDDEN_KEYS = {'password','api_key','secret','access_token','refresh_token','session_id','thread_id','user_id','email'}
LEAK = re.compile(r'/Users/|/private/|/tmp/|/var/folders/|/home/|file://|ssh://|'
                  r'AKIA[0-9A-Z]{16}|hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|'
                  r'-----BEGIN [A-Z ]*PRIVATE KEY-----|(?i:authorization\s*:\s*bearer\s+\S+)')


def require(condition, message):
    if not condition: raise ValueError(message)


def exact(actual, expected, message):
    require(type(actual) is type(expected) and actual == expected, message)


def clean(value):
    if isinstance(value,dict):
        require(not FORBIDDEN_KEYS.intersection(k.lower() for k in value), 'Private identifier or credential key')
        for k,v in value.items():
            if k == 'sha256' or k.endswith('_sha256'):
                require(type(v) is str and re.fullmatch(r'[0-9a-f]{64}',v), 'Malformed provenance hash')
            clean(k);clean(v)
    elif isinstance(value,list):
        for v in value: clean(v)
    elif isinstance(value,str): require(not LEAK.search(value), 'Private path or credential material')
    elif isinstance(value,float): require(math.isfinite(value), 'Nonfinite publication value')


def strict_document(path):
    data = path.read_bytes()
    require(len(data) <= 131072 and not data.startswith(b'\xef\xbb\xbf'), 'Oversized document or BOM')
    def pairs(entries):
        result={}
        for key,value in entries:
            require(key not in result, 'Duplicate publication key');result[key]=value
        return result
    def invalid(value): raise ValueError('Nonfinite publication JSON')
    value=json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid)
    require(type(value) is dict, 'Publication object required');clean(value)
    return value


def expected_intent(index):
    if index < 4:
        return {'schema_version':1,'status':'proposal','parameters':{'outer_diameter_mm':PROPOSAL_OD[index],
            'inner_diameter_mm':20,'thickness_mm':3,'unit':'mm'},'reason':None}
    status,reason=NONPROPOSALS[index-4]
    return {'schema_version':1,'status':status,'parameters':None,'reason':reason}


def check(directory=HERE):
    directory=Path(directory)
    cases=strict_document(directory/'cases.json');results=strict_document(directory/'results.json')
    clean((directory/'README.md').read_text(encoding='utf-8'))
    exact(cases['independent_holdout'],False,'Exposed fixture required')
    exact(cases['cases_are_independent_samples'],False,'Independent-sample claim forbidden')
    exact(cases['observed_vehicle_measurements'],False,'No measured part evidence')
    exact(cases['fabrication_use_authorized'],False,'No fabrication permission')
    exact(cases['language_counts'],{'en':4,'fr':4},'Language totals differ')
    exact(cases['source_requests_sha256'],REQUESTS_SHA,'Frozen request source changed')
    exact(cases['system_prompt_sha256'],SYSTEM_SHA,'Frozen system source changed')
    require(hashlib.sha256(cases['system_prompt'].encode('utf-8')).hexdigest()==SYSTEM_SHA,'System bytes changed')
    rows=cases['cases'];require(type(rows) is list and len(rows)==8,'Exactly eight rows')
    correct=baseline=proposals=baseline_proposals=critical=baseline_critical=wins=losses=tokens=0
    families={};winning_ids=[]
    for index,(row,fixture) in enumerate(zip(rows,EXPECTED_CASES)):
        for key,value in zip(('id','language','family','request','critical','baseline_correct'),fixture):
            exact(row[key],value,'Frozen fixture or baseline metadata differs: '+key)
        raw=row['raw_response'];require(type(raw) is str,'Raw response string required')
        data=raw.encode('utf-8')
        require(hashlib.sha256(data).hexdigest()==row['raw_response_sha256'],'Raw response hash differs')
        exact(row['raw_response_utf8_bytes'],len(data),'Raw byte count differs')
        candidate=V.validate_json(raw)  # No strip, fence removal, replacement or repair.
        grade=V.compare_expected_intent(candidate,expected_intent(index))
        require(grade['semantic_match'],'Allowable parameters/status do not match this request')
        exact(row['model_correct'],True,'Model grade differs');exact(row['strict_schema_and_constraints_pass'],True,'Strict grade differs')
        exact(row['actual_eos'],True,'Eight reported EOS required')
        exact(row['generated_tokens_including_eos'],TOKEN_COUNTS[index],'Frozen token count differs')
        exact(row['response_corrections_applied'],0,'Response correction forbidden')
        exact(row['geometry_runtime'],'NOT_EVALUATED','No native geometry proof')
        elapsed=row['case_elapsed_seconds'];require(type(elapsed) in (int,float) and math.isfinite(elapsed)
            and 0 <= elapsed <= 45,'Case time invalid')
        b=row['baseline_correct'];is_critical=row['critical'];is_proposal=index<4
        outcome='tie' if b else 'win';exact(row['paired_outcome'],outcome,'Paired metadata differs')
        correct+=1;baseline+=b;proposals+=is_proposal;baseline_proposals+=b and is_proposal
        critical+=is_critical;baseline_critical+=b and is_critical;wins+=not b;tokens+=TOKEN_COUNTS[index]
        if not b:winning_ids.append(row['id'])
        family=families.setdefault(row['family'],{'requests':0,'correct':0,'wins':0,'losses':0})
        family['requests']+=1;family['correct']+=1;family['wins']+=not b
    exact(winning_ids,['nl-next-03','nl-next-04'],'Frozen paired gain cases differ')
    scores=results['scores']
    expected={'baseline_correct':baseline,'model_correct':correct,'requests':8,'baseline_complete_proposals_correct':baseline_proposals,
        'model_complete_proposals_correct':proposals,'complete_proposal_requests':4,'baseline_critical_correct':baseline_critical,
        'model_critical_correct':critical,'critical_requests':4,'paired_wins':wins,'paired_losses':losses,
        'net_additional_complete_correct_proposals':2,'format_semantic_unit_or_quantity_errors':0,
        'unsupported_or_invented_quantities':0,'critical_regressions':0,'response_corrections_required':0,
        'descriptive_exact_two_sided_discordance_p':0.5,'reliable_broad_superiority_demonstrated':False}
    for key,value in expected.items():exact(scores[key],value,'Aggregate score differs: '+key)
    exact(scores['family_results'],families,'Family totals differ')
    exact(scores['gain_families'],['relative_reduction','change_bore'],'Gain families differ')
    exact(results['model']['upstream_numerical_or_conversion_parity'],'UNKNOWN','Numerical parity unproved')
    exact(results['provenance']['published_parameter_verifier_sha256'],VERIFIER_SHA,'Pure verifier provenance differs')
    method=results['method']
    exact(method['language_counts'],{'en':4,'fr':4},'Method language totals differ')
    for key,value in {'request_count':8,'complete_proposal_requests':4,'critical_requests':4,'model_generation_calls':8,
        'calls_per_request':1,'retry_or_repair':False,'few_shot_examples':False,'thinking_enabled':False,
        'seed_per_request':0,'fresh_kv_cache_per_request':True,'maximum_input_tokens':2048,
        'maximum_output_tokens_including_terminal':512,'native_eos_token_id':248046,'pad_token_id_nonterminal':248044,
        'per_case_wall_seconds':45,'global_wall_seconds':480,'independent_holdout':False,'blind_assessment':False,
        'geometry_runtime':'NOT_EVALUATED'}.items():exact(method[key],value,'Method metadata differs: '+key)
    resources=results['resources']
    for key,value in {'cpu_target_core_equivalents':2,'authorized_rolling_cpu_ceiling_core_equivalents':4,
        'cpu_window_minimum_seconds':1,'observed_max_rolling_cpu_core_equivalents':2.468044586622185,
        'cpu_target_exceeded':True,'os_hard_cpu_cap_enforced':False,'max_sampled_owned_threads':14,
        'owned_thread_observation_ceiling':16,'own_nice':10,'conservative_combined_memory_ceiling_bytes':38654705664,
        'observed_max_conservative_combined_memory_bytes':32244814228,'mlx_active_peak_ceiling_bytes':21474836480,
        'observed_max_mlx_peak_bytes':16155905556,'cache_retention_target_bytes':536870912,
        'observed_max_cache_bytes':444072832,'minimum_available_system_memory_required_bytes':17179869184,
        'observed_minimum_available_memory_proxy_bytes':17870143488,'resource_guard_failures':0,
        'gpu_errors_detected':False,'actual_eos_count':8,'generated_tokens_including_eos':tokens}.items():
        exact(resources[key],value,'Resource metadata differs: '+key)
    cost=results['operational_cost']
    require(cost['receipt_elapsed_seconds']==213.3271155829716 and cost['receipt_elapsed_seconds']<480,'Owner elapsed differs')
    require(cost['generation_min_seconds']==min(r['case_elapsed_seconds'] for r in rows) and
        cost['generation_max_seconds']==max(r['case_elapsed_seconds'] for r in rows),'Per-case time range differs')
    exact(cost['generated_tokens_including_eos'],464,'Token total differs')
    exact(cost['actual_human_correction_seconds'],None,'Human correction time was not measured')
    exact(cost['human_correction_duration_measured'],False,'Measured human time claim forbidden')
    exact(cost['required_response_corrections_on_frozen_cases'],0,'Correction metadata differs')
    require(cost['automatic_validation_wall_seconds']==0.1950459170038812,'Validation elapsed differs')
    scope=results['permissions_and_scope']
    for key,value in {'optimizer_updates':0,'adapters_loaded':False,'fine_tuning_gain_demonstrated':False,
        'reserves_opened':False,'generated_code_executed':False,'cad_or_native_geometry_executed':False,
        'manufacturing_validity_established':False,'automatic_adoption_authorized':False,'baseline_retained':True,
        'readiness_established':False}.items():exact(scope[key],value,'Permission/readiness claim differs: '+key)
    return {'status':'PASS_PUBLISHED_RESPONSE_REGRADING_ONLY','model_correct':correct,'baseline_metadata_correct':baseline,
        'paired_wins':wins,'paired_losses':losses,'actual_eos_reported':8,'reported_tokens':tokens,
        'model_or_baseline_rerun':False,'historical_runtime_execution_proved_by_this_check':False,
        'independent_samples':False,'builder_execution_authorized':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,default=HERE)
    print(json.dumps(check(parser.parse_args().directory),sort_keys=True))
