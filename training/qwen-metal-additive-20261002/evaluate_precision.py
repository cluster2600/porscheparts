"""Evaluate the pinned Qwen3 development-selected adapter on the registered fresh test."""
import argparse,json,re,time
from pathlib import Path
import run_corrective
import run_precision
import precision_terminology_profile
import verify_grounded
HERE=Path(__file__).resolve().parent

def screen(questions,predictions):
 if len(questions)!=len(predictions) or [q['id'] for q in questions]!=[r['id'] for r in predictions]:raise ValueError('Predictions missing or out of order')
 result=[]
 for q,r in zip(questions,predictions):
  response=r['response'].casefold()
  groups=[any(term.casefold() in response for term in alternatives) for alternatives in q['required_groups']]
  citation=q['passage_id'] in r['response']
  # Missing-value cases must not supply any guessed numeric temperature.
  temperatures=re.findall(r'(?<![\w:])(\d+(?:[.,]\d+)?)\s*(?:°|degr|℃)',r['response'])
  provided_numbers=set(re.findall(r'\d+(?:[.,]\d+)?',q.get('question','')))
  unexpected_number=any(value not in provided_numbers for value in temperatures) if q['critical_boundary'] else False
  result.append({'id':q['id'],'citation_present':citation,'keyword_groups':groups,'unexpected_temperature':unexpected_number,'critical_boundary':q['critical_boundary'],'automated_screen_pass':citation and all(groups) and not unexpected_number,'token_budget_hit':r['reached_token_budget']})
 return {'examples':len(result),'expected_citations':sum(r['citation_present'] for r in result),'automated_screen_passes':sum(r['automated_screen_pass'] for r in result),'critical_boundary_screen_failures':sum(r['critical_boundary'] and not r['automated_screen_pass'] for r in result),'token_budget_hits':sum(r['token_budget_hit'] for r in result),'rows':result,'scope':'Necessary lexical/reference checks only; not semantic accuracy. Assistant passage-by-passage assessment and independent expert review are separate.'}

def run(source,selection_path,output,cache):
 cfg,root,manifest,profile=run_precision.audit()
 run_corrective.audit()
 auxiliary_manifest=run_corrective.load(HERE/'precision-domain-manifest.json')
 if verify_grounded.sha(HERE/'precision-domain-benchmark.jsonl')!=auxiliary_manifest['benchmark_sha256']:raise ValueError('Registered domain benchmark changed')
 if output.exists():raise ValueError('Use a fresh final-test directory')
 selection=run_corrective.load(selection_path)
 receipt=run_corrective.load(source/'development-receipt.json')
 if receipt['status']!='development_completed' or selection.get('checkpoint')!='adapter' or (selection.get('model_id'),selection.get('revision'))!=(cfg['model_id'],cfg['revision']):raise ValueError('Selection model or run status mismatch')
 if receipt['registered_new_test_manifest_sha256']!=verify_grounded.sha(HERE/'precision-test-manifest.json') or receipt['registered_new_domain_manifest_sha256']!=verify_grounded.sha(HERE/'precision-domain-manifest.json'):raise ValueError('Benchmark changed after training registration')
 if not selection['accepted_on_development'] or selection['independent_expert_validated']:raise ValueError('Invalid selection status')
 if selection['development_receipt_sha256']!=verify_grounded.sha(source/'development-receipt.json'):raise ValueError('Selection belongs to a different run')
 if receipt['config_sha256']!=verify_grounded.sha(HERE/'precision-config-v7.json') or receipt['dataset_manifest_sha256']!=verify_grounded.sha(root/'manifest.json'):raise ValueError('Experiment inputs changed')
 if selection['inference_profile_sha256']!=verify_grounded.sha(HERE/'precision-terminology-profile.json') or selection['inference_helper_sha256']!=verify_grounded.sha(HERE/'precision_terminology_profile.py'):raise ValueError('Selected inference profile changed')
 checkpoint=source/'adapter'
 weight_hash=verify_grounded.sha(checkpoint/'adapter_model.safetensors')
 if weight_hash!=selection['checkpoint_weights_sha256'] or weight_hash!=receipt['adapter_files_sha256']['adapter_model.safetensors']:raise ValueError('Selected checkpoint changed')
 if verify_grounded.sha(checkpoint/'adapter_config.json')!=receipt['adapter_files_sha256']['adapter_config.json']:raise ValueError('Selected adapter configuration changed')
 if receipt['test_used_in_training'] or receipt['final_test_generated']:raise ValueError('Test isolation violated')
 output.mkdir(parents=True)
 run_corrective.save(output/'frozen-selection.json',selection)
 started=time.monotonic()
 def status(stage,**detail):
  value={'stage':stage,**detail};run_corrective.save(output/'status.json',value);print(json.dumps(value),flush=True)
 status('loading');model,tokenizer,snapshot=run_precision.runtime(cfg,profile,cache)
 for name,sha in receipt['base_weights_sha256'].items():
  if verify_grounded.sha(snapshot/name)!=sha:raise ValueError('Runtime base weights differ from trained base')
 questions=precision_terminology_profile.questions_with_profile(verify_grounded.rows(HERE/'precision-final-test.jsonl'))
 run_corrective.dump(output/'final-questions.jsonl',questions)
 base=run_corrective.predict(model,tokenizer,questions,cfg,output/'base-final-test.jsonl',status)
 from peft import PeftModel
 model=PeftModel.from_pretrained(model,str(checkpoint),local_files_only=True).eval()
 adapter=run_corrective.predict(model,tokenizer,questions,cfg,output/'adapter-final-test.jsonl',status)
 auxiliary_questions=precision_terminology_profile.questions_with_profile(verify_grounded.rows(HERE/'precision-domain-benchmark.jsonl'))
 run_corrective.dump(output/'domain-questions.jsonl',auxiliary_questions)
 auxiliary=run_corrective.predict(model,tokenizer,auxiliary_questions,cfg,output/'adapter-domain-test.jsonl',status)
 run_corrective.save(output/'adapter-domain-screen.json',screen(auxiliary_questions,auxiliary))
 run_corrective.dump(output/'adapter-domain-review.jsonl',[{**q,'prediction':p,'assistant_assessment':None,'independent_expert_score':None,'independent_reviewer':None} for q,p in zip(auxiliary_questions,auxiliary)])
 for kind,predictions in [('base',base),('adapter',adapter)]:
  run_corrective.save(output/(kind+'-final-screen.json'),screen(questions,predictions))
  worksheet=[{**q,'prediction':p,'assistant_assessment':None,'independent_expert_score':None,'independent_reviewer':None} for q,p in zip(questions,predictions)]
  run_corrective.dump(output/(kind+'-final-review.jsonl'),worksheet)
 run_corrective.save(output/'final-receipt.json',{'status':'final_test_completed','selection_sha256':verify_grounded.sha(output/'frozen-selection.json'),'dataset_manifest_sha256':verify_grounded.sha(root/'manifest.json'),'config_sha256':verify_grounded.sha(HERE/'precision-config-v7.json'),'profile_sha256':verify_grounded.sha(HERE/'precision-terminology-profile.json'),'profile_helper_sha256':verify_grounded.sha(HERE/'precision_terminology_profile.py'),'evaluator_sha256':verify_grounded.sha(HERE/'evaluate_precision.py'),'adapter_config_sha256':verify_grounded.sha(checkpoint/'adapter_config.json'),'registered_test_manifest_sha256':verify_grounded.sha(HERE/'precision-test-manifest.json'),'base_weights_sha256':receipt['base_weights_sha256'],'checkpoint_weights_sha256':weight_hash,'seconds':time.monotonic()-started,'auxiliary_benchmark_sha256':verify_grounded.sha(HERE/'precision-domain-benchmark.jsonl'),'test_used_in_training':False,'test_used_for_checkpoint_selection':False,'independent_expert_validated':False,'files_sha256':{p.name:verify_grounded.sha(p) for p in output.iterdir() if p.is_file() and p.name!='status.json'}})
 status('final_test_completed')

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for flag in ('source','selection','output','cache'):parser.add_argument('--'+flag,type=Path,required=True)
 args=parser.parse_args();run(args.source.resolve(),args.selection.resolve(),args.output.resolve(),args.cache.resolve())
