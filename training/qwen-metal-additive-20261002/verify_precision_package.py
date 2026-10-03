"""Verify the complete precision package without asserting human scientific review."""
import argparse,json
from pathlib import Path
import run_precision,run_corrective as u,verify_grounded as v,evaluate_precision as e,precision_terminology_profile as helper
HERE=Path(__file__).resolve().parent

def verify(output):
 cfg,root,_,_=run_precision.audit();package=u.load(output/'package-manifest.json')
 for name,sha in package['files_sha256'].items():
  if v.sha(output/name)!=sha:raise ValueError('Packaged file changed: '+name)
 receipt=u.load(output/'development-receipt.json');final=u.load(output/'final-receipt.json');selection=u.load(output/'frozen-selection.json');assessment=u.load(output/'assistant-final-assessment.json')
 if any(x.get('independent_expert_validated',False) for x in (package,receipt,final,selection,assessment)):raise ValueError('Unsupported expert validation')
 if receipt['test_used_in_training'] or final['test_used_in_training'] or final['test_used_for_checkpoint_selection']:raise ValueError('New test isolation violated')
 if package['status']!=assessment['status'] or package['inference_profile']!='precision-v9':raise ValueError('Package status/profile mismatch')
 if receipt['dataset_manifest_sha256']!=v.sha(root/'manifest.json') or final['dataset_manifest_sha256']!=receipt['dataset_manifest_sha256'] or package['dataset_manifest_sha256']!=receipt['dataset_manifest_sha256']:raise ValueError('Data release mismatch')
 for key,name in [('config_sha256','precision-config-v7.json'),('profile_sha256','precision-terminology-profile.json'),('profile_helper_sha256','precision_terminology_profile.py')]:
  if receipt[key]!=v.sha(HERE/name) or final[key]!=receipt[key]:raise ValueError('Executed input mismatch')
 if receipt['runner_sha256']!=v.sha(HERE/'run_precision.py') or final['evaluator_sha256']!=v.sha(HERE/'evaluate_precision.py'):raise ValueError('Executed code changed')
 if selection['development_receipt_sha256']!=v.sha(output/'development-receipt.json') or final['selection_sha256']!=v.sha(output/'frozen-selection.json'):raise ValueError('Selection provenance mismatch')
 for name,sha in final['files_sha256'].items():
  if v.sha(output/name)!=sha:raise ValueError('Raw final result changed')
 weights=v.sha(output/'adapter/adapter_model.safetensors');audit=u.load(output/'adapter-audit.json')
 if weights!=selection['checkpoint_weights_sha256'] or weights!=final['checkpoint_weights_sha256'] or weights!=receipt['adapter_files_sha256']['adapter_model.safetensors'] or weights!=audit['sha256'] or not audit['all_finite'] or audit['nonzero_lora_b_tensors']!=audit['lora_b_tensors']:raise ValueError('Weights or audit changed')
 if final['adapter_config_sha256']!=v.sha(output/'source-adapter-config.json') or final['adapter_config_sha256']!=receipt['adapter_files_sha256']['adapter_config.json']:raise ValueError('Executed adapter config changed')
 expected=u.load(output/'source-adapter-config.json');expected.update(base_model_name_or_path=cfg['model_id'],revision=cfg['revision'])
 if expected!=u.load(output/'adapter/adapter_config.json'):raise ValueError('Unexpected portable config transformation')
 if final['base_weights_sha256']!=receipt['base_weights_sha256']:raise ValueError('Base weights mismatch')
 if final['registered_test_manifest_sha256']!=v.sha(HERE/'precision-test-manifest.json') or receipt['registered_new_test_manifest_sha256']!=final['registered_test_manifest_sha256'] or receipt['registered_new_domain_manifest_sha256']!=v.sha(HERE/'precision-domain-manifest.json'):raise ValueError('New benchmark registration changed')
 primary=v.rows(HERE/'precision-final-test.jsonl');domain=v.rows(HERE/'precision-domain-benchmark.jsonl')
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
 return {'status':'pass','assessment_status':assessment['status'],'scope':'Integrity, raw lexical recomputation and recorded assistant decisions; not independent expert review.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.output.resolve()),indent=2))
