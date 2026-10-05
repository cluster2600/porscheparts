"""Resume an infrastructure-interrupted frozen final evaluation without reselection."""
import argparse,json,time,shutil
from pathlib import Path
import evaluate_compact as e,run_compact,run_corrective as u,verify_grounded as v,concise_qualified_profile_v7 as helper
HERE=Path(__file__).resolve().parent

def resume(source,selection_path,output,cache):
 cfg,root,_,profile=run_compact.audit();u.audit()
 if (output/'final-receipt.json').exists():raise ValueError('Final evaluation already complete')
 selection=u.load(selection_path);receipt=u.load(source/'development-receipt.json')
 if selection!=u.load(output/'frozen-selection.json') or not selection['accepted_on_development']:raise ValueError('Frozen selection mismatch')
 if selection['development_receipt_sha256']!=v.sha(source/'development-receipt.json'):raise ValueError('Training receipt changed')
 for key,file in [('config_sha256','compact-config.json'),('runner_sha256','run_compact.py')]:
  if receipt[key]!=v.sha(HERE/file):raise ValueError('Executed training inputs changed')
 for key,file in [('inference_profile_sha256','concise-qualified-profile.json'),('inference_helper_sha256','concise_qualified_profile_v7.py')]:
  if selection[key]!=v.sha(HERE/file):raise ValueError('Selected inference inputs changed')
 if receipt['dataset_manifest_sha256']!=v.sha(root/'manifest.json'):raise ValueError('Training data changed')
 checkpoint=source/'adapter';weight_hash=v.sha(checkpoint/'adapter_model.safetensors')
 if weight_hash!=selection['checkpoint_weights_sha256'] or weight_hash!=receipt['adapter_files_sha256']['adapter_model.safetensors']:raise ValueError('Selected weights changed')
 if v.sha(checkpoint/'adapter_config.json')!=receipt['adapter_files_sha256']['adapter_config.json']:raise ValueError('Adapter config changed')
 domain=u.load(HERE/'corrective-domain-manifest.json')
 if v.sha(HERE/'corrective-domain-benchmark.jsonl')!=domain['benchmark_sha256']:raise ValueError('Domain benchmark changed')
 questions=helper.questions_with_profile(v.rows(HERE/'corrective-v4/final-test.jsonl'))
 if questions!=v.rows(output/'final-questions.jsonl'):raise ValueError('Executed questions changed')
 original=output/'base-final-test.partial.jsonl';prior=v.rows(original)
 if not 0<len(prior)<len(questions) or [p['id'] for p in prior]!=[q['id'] for q in questions[:len(prior)]]:raise ValueError('Invalid partial results')
 if (output/'interruption-receipt.json').exists():raise ValueError('Already resumed; inspect existing progress')
 shutil.copyfile(original,output/'interrupted-base-partial.jsonl')
 u.save(output/'interruption-receipt.json',{'reason':'Execution environment interruption; process lost before final base row.','preserved_predictions':len(prior),'preserved_predictions_sha256':v.sha(original),'selection_sha256':v.sha(output/'frozen-selection.json'),'resumer_sha256':v.sha(HERE/'resume_compact.py'),'evaluator_sha256':v.sha(HERE/'evaluate_compact.py'),'candidate_changed':False,'predictions_regenerated':False})
 started=time.monotonic()
 def status(stage,**detail):
  val={'stage':stage,**detail};u.save(output/'status.json',val);print(json.dumps(val),flush=True)
 model,tokenizer,snapshot=run_compact.runtime(cfg,profile,cache)
 for name,sha in receipt['base_weights_sha256'].items():
  if v.sha(snapshot/name)!=sha:raise ValueError('Runtime base weights changed')
 rest=u.predict(model,tokenizer,questions[len(prior):],cfg,output/'base-resumed-predictions.jsonl',status)
 base=prior+rest;u.dump(output/'base-final-test.jsonl',base)
 from peft import PeftModel
 model=PeftModel.from_pretrained(model,str(checkpoint),local_files_only=True).eval()
 adapter=u.predict(model,tokenizer,questions,cfg,output/'adapter-final-test.jsonl',status)
 auxiliary_questions=helper.questions_with_profile(v.rows(HERE/'corrective-domain-benchmark.jsonl'));u.dump(output/'domain-questions.jsonl',auxiliary_questions)
 auxiliary=u.predict(model,tokenizer,auxiliary_questions,cfg,output/'adapter-domain-test.jsonl',status)
 for kind,qs,preds in [('base-final',questions,base),('adapter-final',questions,adapter),('adapter-domain',auxiliary_questions,auxiliary)]:
  u.save(output/(kind+'-screen.json'),e.screen(qs,preds))
  u.dump(output/(kind+'-review.jsonl'),[{**q,'prediction':p,'assistant_assessment':None,'independent_expert_score':None,'independent_reviewer':None} for q,p in zip(qs,preds)])
 u.save(output/'final-receipt.json',{'status':'final_test_completed','selection_sha256':v.sha(output/'frozen-selection.json'),'dataset_manifest_sha256':v.sha(root/'manifest.json'),'config_sha256':v.sha(HERE/'compact-config.json'),'profile_sha256':v.sha(HERE/'concise-qualified-profile.json'),'profile_helper_sha256':v.sha(HERE/'concise_qualified_profile_v7.py'),'evaluator_sha256':v.sha(HERE/'evaluate_compact.py'),'resumer_sha256':v.sha(HERE/'resume_compact.py'),'adapter_config_sha256':v.sha(checkpoint/'adapter_config.json'),'registered_test_manifest_sha256':v.sha(HERE/'corrective-v4/manifest.json'),'base_weights_sha256':receipt['base_weights_sha256'],'checkpoint_weights_sha256':weight_hash,'seconds':time.monotonic()-started,'seconds_scope':'Resumption wall time only; original generation durations retained per prediction.','total_generation_seconds':sum(p['seconds'] for p in base+adapter+auxiliary),'preserved_base_predictions':len(prior),'auxiliary_benchmark_sha256':v.sha(HERE/'corrective-domain-benchmark.jsonl'),'test_used_in_training':False,'test_used_for_checkpoint_selection':False,'independent_expert_validated':False,'files_sha256':{p.name:v.sha(p) for p in output.iterdir() if p.is_file() and p.name!='status.json'}})
 status('final_test_completed')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for flag in ('source','selection','output','cache'):parser.add_argument('--'+flag,type=Path,required=True)
 args=parser.parse_args();resume(args.source.resolve(),args.selection.resolve(),args.output.resolve(),args.cache.resolve())
