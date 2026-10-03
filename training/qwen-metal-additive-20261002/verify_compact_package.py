"""Check corrective package provenance and recompute lexical evaluation screens."""
import argparse,json
from pathlib import Path
import evaluate_compact as evaluate_corrective
import run_compact
import concise_qualified_profile_v7
import run_corrective
import verify_grounded
HERE=Path(__file__).resolve().parent

def verify(output):
 cfg,root,manifest,_=run_compact.audit()
 run_corrective.audit()
 package=run_corrective.load(output/'package-manifest.json')
 for name,sha in package['files_sha256'].items():
  if verify_grounded.sha(output/name)!=sha:raise ValueError('Packaged file changed: '+name)
 receipt=run_corrective.load(output/'development-receipt.json');final=run_corrective.load(output/'final-receipt.json');selection=run_corrective.load(output/'frozen-selection.json');assessment=run_corrective.load(output/'assistant-final-assessment.json')
 if any(r['test_used_in_training'] for r in (receipt,final)) or final['test_used_for_checkpoint_selection']:raise ValueError('Test isolation violated')
 if any(r.get('independent_expert_validated',False) or r.get('expert_validated',False) for r in (receipt,final,selection,assessment,package)):raise ValueError('Unsupported expert claim')
 if receipt['dataset_manifest_sha256']!=verify_grounded.sha(root/'manifest.json') or package['dataset_manifest_sha256']!=receipt['dataset_manifest_sha256']:raise ValueError('Data release mismatch')
 if verify_grounded.sha(output/'development-receipt.json')!=selection['development_receipt_sha256']:raise ValueError('Selection receipt mismatch')
 if verify_grounded.sha(output/'frozen-selection.json')!=final['selection_sha256']:raise ValueError('Selection changed after final test')
 for name,sha in final['files_sha256'].items():
  if verify_grounded.sha(output/name)!=sha:raise ValueError('Raw final result changed')
 if package['status']!=assessment['status']:raise ValueError('Package status disagrees with assessment')
 if final['registered_test_manifest_sha256']!=verify_grounded.sha(HERE/'corrective-v4/manifest.json'):raise ValueError('Registered benchmark manifest changed')
 if final['base_weights_sha256']!=receipt['base_weights_sha256']:raise ValueError('Base weight provenance mismatch')
 if verify_grounded.sha(output/'source-adapter-config.json')!=final['adapter_config_sha256'] or final['adapter_config_sha256']!=receipt['adapter_files_sha256']['adapter_config.json']:raise ValueError('Executed adapter config mismatch')
 weight_hash=verify_grounded.sha(output/'adapter/adapter_model.safetensors')
 if weight_hash!=final['checkpoint_weights_sha256'] or weight_hash!=selection['checkpoint_weights_sha256']:raise ValueError('Selected tensors changed')
 audit=run_corrective.load(output/'adapter-audit.json')
 if not audit['all_finite'] or audit['sha256']!=weight_hash or audit['nonzero_lora_b_tensors']!=audit['lora_b_tensors']:raise ValueError('Tensor audit mismatch')
 config=run_corrective.load(output/'adapter/adapter_config.json')
 if (config['base_model_name_or_path'],config['revision'])!=(cfg['model_id'],cfg['revision']):raise ValueError('Base pin mismatch')
 original=run_corrective.load(output/'source-adapter-config.json');original.update(base_model_name_or_path=cfg['model_id'],revision=cfg['revision'])
 if config!=original:raise ValueError('Unexpected adapter config transformation')
 if final['profile_sha256']!=verify_grounded.sha(HERE/'concise-qualified-profile.json') or final['profile_helper_sha256']!=verify_grounded.sha(HERE/'concise_qualified_profile_v7.py'):raise ValueError('Inference profile mismatch')
 if selection['inference_profile_sha256']!=final['profile_sha256'] or selection['inference_helper_sha256']!=final['profile_helper_sha256']:raise ValueError('Inference selection mismatch')
 comparison_path=output/'selected-profile-development/profile-receipt.json'
 if verify_grounded.sha(comparison_path)!=selection['comparison_receipt_sha256']:raise ValueError('Development comparison mismatch')
 comparison=run_corrective.load(comparison_path)
 if comparison['profile_sha256']!=final['profile_sha256'] or comparison['development_receipt_sha256']!=verify_grounded.sha(output/'development-receipt.json'):raise ValueError('Profile comparison provenance mismatch')
 if final.get('resumer_sha256') and final['resumer_sha256']!=verify_grounded.sha(HERE/'resume_compact.py'):raise ValueError('Executed resumption code changed')
 if receipt['runner_sha256']!=verify_grounded.sha(HERE/'run_compact.py') or receipt['config_sha256']!=verify_grounded.sha(HERE/'compact-config.json') or final['config_sha256']!=receipt['config_sha256'] or final['evaluator_sha256']!=verify_grounded.sha(HERE/'evaluate_compact.py'):raise ValueError('Executed code/config mismatch')
 if not comparison['exact_development_input_equivalence'] or not comparison['predictions_reused']:raise ValueError('Missing routing equivalence evidence')
 if comparison['profile_helper_sha256']!=final['profile_helper_sha256']:raise ValueError('Selected inference helper mismatch')
 if verify_grounded.sha(comparison_path.parent/'executed-v6-profile-receipt.json')!=comparison['executed_receipt_sha256']:raise ValueError('Original generation receipt changed')
 if verify_grounded.rows(comparison_path.parent/'questions.jsonl')!=concise_qualified_profile_v7.questions_with_profile(verify_grounded.rows(HERE/'corrective-v4/development.jsonl')):raise ValueError('Development input equivalence no longer holds')
 for name,sha in comparison['files_sha256'].items():
  if verify_grounded.sha(comparison_path.parent/name)!=sha:raise ValueError('Development evidence changed')
 questions=verify_grounded.rows(HERE/'corrective-v4/final-test.jsonl')
 if verify_grounded.rows(output/'final-questions.jsonl')!=concise_qualified_profile_v7.questions_with_profile(questions):raise ValueError('Executed final questions differ from registration')
 for kind in ('base','adapter'):
  predictions=verify_grounded.rows(output/(kind+'-final-test.jsonl'))
  if len(predictions)!=12 or [r['id'] for r in predictions]!=[r['id'] for r in questions]:raise ValueError('Final predictions incomplete')
  if evaluate_corrective.screen(questions,predictions)!=run_corrective.load(output/(kind+'-final-screen.json')):raise ValueError('Final screen changed')
 auxiliary=verify_grounded.rows(HERE/'corrective-domain-benchmark.jsonl')
 if verify_grounded.rows(output/'domain-questions.jsonl')!=concise_qualified_profile_v7.questions_with_profile(auxiliary):raise ValueError('Executed domain questions differ from registration')
 if verify_grounded.sha(HERE/'corrective-domain-benchmark.jsonl')!=final['auxiliary_benchmark_sha256']:raise ValueError('Domain benchmark changed')
 if evaluate_corrective.screen(auxiliary,verify_grounded.rows(output/'adapter-domain-test.jsonl'))!=run_corrective.load(output/'adapter-domain-screen.json'):raise ValueError('Domain screen changed')
 if assessment['domain_predictions_sha256']!=verify_grounded.sha(output/'adapter-domain-test.jsonl'):raise ValueError('Domain assessment belongs to other predictions')
 primary_rows=assessment['primary_rows'];domain_rows=assessment['domain_rows']
 if [r['id'] for r in primary_rows]!=[q['id'] for q in questions] or [r['id'] for r in domain_rows]!=[q['id'] for q in auxiliary]:raise ValueError('Assistant assessment incomplete or out of order')
 if any(not isinstance(r['pass'],bool) or not r['reason'] for r in primary_rows+domain_rows):raise ValueError('Assistant assessment lacks decisions or reasons')
 primary=run_corrective.load(output/'adapter-final-screen.json');domain=run_corrective.load(output/'adapter-domain-screen.json')
 accepted=(primary['expected_citations']==12 and sum(r['pass'] for r in primary_rows)>=11 and all(r['pass'] for q,r in zip(questions,primary_rows) if q['critical_boundary']) and domain['expected_citations']==8 and sum(r['pass'] for r in domain_rows)>=7 and all(r['pass'] for q,r in zip(auxiliary,domain_rows) if q['critical_boundary']))
 if accepted!=(assessment['status']=='accepted_on_registered_benchmark'):raise ValueError('Acceptance claim disagrees with recorded decisions')
 if assessment['predictions_sha256']!=verify_grounded.sha(output/'adapter-final-test.jsonl'):raise ValueError('Assessment prediction mismatch')
 return {'status':'pass','assessment_status':assessment['status'],'scope':'Integrity and recomputed lexical screens; assistant assessment is not independent expert review.'}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(json.dumps(verify(args.output.resolve()),indent=2))
