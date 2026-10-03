"""Verify the complete fidelity package without asserting human scientific review."""
import argparse,json
from pathlib import Path
import run_compact,run_corrective as u,verify_grounded as v,evaluate_fidelity as e,task_routed_profile as helper
HERE=Path(__file__).resolve().parent

def verify(output):
 import run_precision
 run_precision.audit()
 import audit_fidelity
 audit_fidelity.audit()
 cfg,root,_,_=run_compact.audit();package=u.load(output/'package-manifest.json')
 domain_manifest=u.load(HERE/'fidelity-domain-manifest.json')
 if v.sha(HERE/'fidelity-domain-benchmark.jsonl')!=domain_manifest['benchmark_sha256']:raise ValueError('Registered domain benchmark changed')
 for name,sha in package['files_sha256'].items():
  if v.sha(output/name)!=sha:raise ValueError('Packaged file changed: '+name)
 receipt=u.load(output/'development-receipt.json');final=u.load(output/'final-receipt.json');selection=u.load(output/'frozen-selection.json');assessment=u.load(output/'assistant-final-assessment.json')
 if any(x.get('independent_expert_validated',False) for x in (package,receipt,final,selection,assessment)):raise ValueError('Unsupported expert validation')
 if receipt['test_used_in_training'] or final['test_used_in_training'] or final['test_used_for_checkpoint_selection']:raise ValueError('New test isolation violated')
 if package['status']!=assessment['status'] or package['inference_profile']!='task-v14':raise ValueError('Package status/profile mismatch')
 if receipt['dataset_manifest_sha256']!=v.sha(root/'manifest.json') or final['dataset_manifest_sha256']!=receipt['dataset_manifest_sha256'] or package['dataset_manifest_sha256']!=receipt['dataset_manifest_sha256']:raise ValueError('Data release mismatch')
 if receipt['config_sha256']!=v.sha(HERE/'compact-config.json') or final['config_sha256']!=receipt['config_sha256']:raise ValueError('Configuration mismatch')
 if receipt['profile_sha256']!=v.sha(HERE/'evidence-profile.json') or receipt['profile_helper_sha256']!=v.sha(HERE/'evidence_profile.py'):raise ValueError('Executed training profile mismatch')
 for key,name in [('profile_sha256','task-routed-profile.json'),('profile_helper_sha256','task_routed_profile.py')]:
  if final[key]!=v.sha(HERE/name):raise ValueError('Selected inference input mismatch')
 if final['training_profile_sha256']!=receipt['profile_sha256'] or final['training_profile_helper_sha256']!=receipt['profile_helper_sha256']:raise ValueError('Training/inference profile receipt mismatch')
 comparison_path=output/'selected-profile-development/profile-receipt.json';comparison=u.load(comparison_path)
 if v.sha(comparison_path)!=selection['comparison_receipt_sha256'] or final['comparison_receipt_sha256']!=selection['comparison_receipt_sha256']:raise ValueError('Selection comparison provenance mismatch')
 for name,sha in comparison['files_sha256'].items():
  if v.sha(comparison_path.parent/name)!=sha:raise ValueError('Development comparison changed')
 if comparison['profile_sha256']!=final['profile_sha256'] or comparison['profile_helper_sha256']!=final['profile_helper_sha256'] or comparison['development_receipt_sha256']!=v.sha(output/'development-receipt.json'):raise ValueError('Comparison input provenance mismatch')
 origins=u.load(comparison_path.parent/'prediction-origins.json');cq={q['id']:q for q in v.rows(comparison_path.parent/'questions.jsonl')};cp={r['id']:r for r in v.rows(comparison_path.parent/'adapter-development.jsonl')}
 if len(origins)!=15 or len({r['id'] for r in origins})!=15 or comparison['comparator_sha256']!=v.sha(HERE/'compare_task_routed_profile.py'):raise ValueError('Development binding provenance mismatch')
 if comparison['config_sha256']!=receipt['config_sha256'] or comparison['checkpoint_weights_sha256']!=receipt['adapter_files_sha256']['adapter_model.safetensors'] or comparison['base_weights_sha256']!=receipt['base_weights_sha256']:raise ValueError('Reused runtime pins mismatch')
 new={r['id']:r for r in v.rows(comparison_path.parent/'new-development-predictions.jsonl')}
 for origin in origins:
  identifier=origin['id']
  if origin['origin']=='reused_identical_expanded_input':
   folder=comparison_path.parent/'reuse-evidence';qfile=folder/(origin['source']+'-questions.jsonl');pfile=folder/(origin['source']+'-predictions.jsonl');oldq={q['id']:q for q in v.rows(qfile)};oldp={r['id']:r for r in v.rows(pfile)}
   if origin['questions_sha256']!=v.sha(qfile) or origin['predictions_sha256']!=v.sha(pfile) or cq[identifier]['messages']!=oldq[identifier]['messages'] or cp[identifier]!=oldp[identifier]:raise ValueError('Reused prediction is not an identical input/output')
  elif origin['origin']=='newly_generated':
   if cp[identifier]!=new[identifier]:raise ValueError('Generated development prediction changed')
  else:raise ValueError('Unknown development prediction origin')
 if receipt['runner_sha256']!=v.sha(HERE/'run_compact.py') or final['evaluator_sha256']!=v.sha(HERE/'evaluate_fidelity.py'):raise ValueError('Executed code changed')
 if selection['development_receipt_sha256']!=v.sha(output/'development-receipt.json') or final['selection_sha256']!=v.sha(output/'frozen-selection.json'):raise ValueError('Selection provenance mismatch')
 for name,sha in final['files_sha256'].items():
  if v.sha(output/name)!=sha:raise ValueError('Raw final result changed')
 weights=v.sha(output/'adapter/adapter_model.safetensors');audit=u.load(output/'adapter-audit.json')
 if weights!=selection['checkpoint_weights_sha256'] or weights!=final['checkpoint_weights_sha256'] or weights!=receipt['adapter_files_sha256']['adapter_model.safetensors'] or weights!=audit['sha256'] or not audit['all_finite'] or audit['nonzero_lora_b_tensors']!=audit['lora_b_tensors']:raise ValueError('Weights or audit changed')
 if final['adapter_config_sha256']!=v.sha(output/'source-adapter-config.json') or final['adapter_config_sha256']!=receipt['adapter_files_sha256']['adapter_config.json']:raise ValueError('Executed adapter config changed')
 expected=u.load(output/'source-adapter-config.json');expected.update(base_model_name_or_path=cfg['model_id'],revision=cfg['revision'])
 if expected!=u.load(output/'adapter/adapter_config.json'):raise ValueError('Unexpected portable config transformation')
 if final['base_weights_sha256']!=receipt['base_weights_sha256']:raise ValueError('Base weights mismatch')
 if final['registered_test_manifest_sha256']!=v.sha(HERE/'fidelity-test-manifest.json') or comparison['registered_new_test_manifest_sha256']!=final['registered_test_manifest_sha256'] or comparison['registered_new_domain_manifest_sha256']!=v.sha(HERE/'fidelity-domain-manifest.json'):raise ValueError('New benchmark registration changed')
 primary=v.rows(HERE/'fidelity-final-test.jsonl');domain=v.rows(HERE/'fidelity-domain-benchmark.jsonl')
 if v.rows(output/'final-questions.jsonl')!=helper.questions_with_profile(primary) or v.rows(output/'domain-questions.jsonl')!=helper.questions_with_profile(domain):raise ValueError('Executed questions differ from registration')
 for kind,questions,file in [('base-final',primary,'base-final-test.jsonl'),('adapter-final',primary,'adapter-final-test.jsonl'),('adapter-domain',domain,'adapter-domain-test.jsonl')]:
  if e.screen(questions,v.rows(output/file))!=u.load(output/(kind+'-screen.json')):raise ValueError('Screen disagrees with raw results')
 if assessment['predictions_sha256']!=v.sha(output/'adapter-final-test.jsonl') or assessment['domain_predictions_sha256']!=v.sha(output/'adapter-domain-test.jsonl'):raise ValueError('Assessment refers to other predictions')
 pr=assessment['primary_rows'];dr=assessment['domain_rows']
 if [x['id'] for x in pr]!=[q['id'] for q in primary] or [x['id'] for x in dr]!=[q['id'] for q in domain] or any(not isinstance(x['pass'],bool) or not x['reason'] for x in pr+dr):raise ValueError('Incomplete or invalid assistant assessment')
 ps=u.load(output/'adapter-final-screen.json');ds=u.load(output/'adapter-domain-screen.json')
 accepted=ps['expected_citations']==12 and sum(x['pass'] for x in pr)>=11 and all(x['pass'] for q,x in zip(primary,pr) if q['critical_boundary']) and ds['expected_citations']==8 and sum(x['pass'] for x in dr)>=7 and all(x['pass'] for q,x in zip(domain,dr) if q['critical_boundary'])
 if accepted!=(assessment['status']=='accepted_on_registered_benchmark'):raise ValueError('Acceptance claim disagrees with actual decisions')
 if package['previous_failed_trial_manifest_sha256']!=v.sha(HERE/'runs/qwen3-compact-001/package-manifest.json'):raise ValueError('Previous failed trial changed')
 if package['rejected_precision_development_manifest_sha256']!=v.sha(HERE/'runs/qwen3-precision-development-001/package-manifest.json'):raise ValueError('Rejected precision trial changed')
 if package['rejected_source_profile_manifest_sha256']!=v.sha(HERE/'runs/qwen3-source-profile-001/package-manifest.json'):raise ValueError('Rejected source profile changed')
 if package['rejected_fidelity_development_manifest_sha256']!=v.sha(HERE/'runs/qwen3-fidelity-development-001/package-manifest.json'):raise ValueError('Rejected fidelity development changed')
 for field,name in [('rejected_condition_development_manifest_sha256','qwen3-condition-development-001'),('rejected_quote_development_manifest_sha256','qwen3-quote-development-001')]:
  if package[field]!=v.sha(HERE/'runs'/name/'package-manifest.json'):raise ValueError('Rejected development archive changed')
 if package['review_errata_sha256']!=v.sha(HERE/'development-review-errata.json'):raise ValueError('Review errata changed')
 for name,sha in u.load(HERE/'task-routed-profile.json')['backend_inputs_sha256'].items():
  if v.sha(output/name)!=sha:raise ValueError('Packaged backend changed: '+name)
 return {'status':'pass','assessment_status':assessment['status'],'scope':'Integrity, raw lexical recomputation and recorded assistant decisions; not independent expert review.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.output.resolve()),indent=2))
