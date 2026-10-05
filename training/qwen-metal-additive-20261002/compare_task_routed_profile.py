"""Bind identical retired development inputs; generate only genuinely changed ones."""
import argparse,json,shutil,time
from pathlib import Path
import run_compact,run_corrective as u,verify_grounded as v,task_routed_profile,audit_fidelity
HERE=Path(__file__).resolve().parent

def run(source,comparison,condition_archive,output,cache):
 cfg,root,_,model_profile=audit_fidelity.audit()
 if output.exists():raise ValueError('Use a fresh development directory')
 training=u.load(source/'development-receipt.json');old=u.load(comparison/'profile-receipt.json');partial=u.load(condition_archive/'package-manifest.json')
 if old['development_receipt_sha256']!=v.sha(source/'development-receipt.json') or partial['training_receipt_sha256']!=v.sha(source/'development-receipt.json'):raise ValueError('Reused work has a different training run')
 if training['config_sha256']!=v.sha(HERE/'compact-config.json') or partial['checkpoint_weights_sha256']!=v.sha(source/'adapter/adapter_model.safetensors') or training['adapter_files_sha256']['adapter_model.safetensors']!=partial['checkpoint_weights_sha256']:raise ValueError('Reused weights/config differ')
 for folder,manifest in ((comparison,old),(condition_archive,partial)):
  for name,sha in manifest['files_sha256'].items():
   if v.sha(folder/name)!=sha:raise ValueError('Reused evidence changed: '+name)
 for receipt,profile,helper,comparator in ((old,'source-precision-profile.json','source_precision_profile.py','compare_source_precision_profile.py'),(partial,'condition-fidelity-profile.json','condition_fidelity_profile.py','compare_condition_fidelity_profile.py')):
  if receipt['profile_sha256']!=v.sha(HERE/profile) or receipt['profile_helper_sha256']!=v.sha(HERE/helper) or receipt['comparator_sha256']!=v.sha(HERE/comparator):raise ValueError('Reused executed profile/code changed')
 original=v.rows(HERE/'corrective-v4/development.jsonl')
 original+=[q for q in v.rows(HERE/'corrective-v4/final-test.jsonl') if q['id'] in ('fresh-03','fresh-05')]
 original+=[q for q in v.rows(HERE/'corrective-domain-benchmark.jsonl') if q['id'] in ('heat-07','heat-08')]
 original+=[q for q in v.rows(HERE/'precision-final-test.jsonl') if q['id'] in ('precision-01','precision-02','precision-03')]
 priority=['eval-002','precision-01','precision-02','precision-03'];original.sort(key=lambda q:priority.index(q['id']) if q['id'] in priority else len(priority))
 questions=task_routed_profile.questions_with_profile(original);output.mkdir(parents=True);started=time.monotonic()
 def status(stage,**details):
  record={'stage':stage,**details};u.save(output/'status.json',record);print(json.dumps(record),flush=True)
 u.dump(output/'questions.jsonl',questions)
 reuse_sources=[(comparison,'questions.jsonl','adapter-development.jsonl','source-comparison'),(condition_archive/'raw-partial-development','questions.jsonl','adapter-development.partial.jsonl','condition-development')]
 predictions={};origins=[];pending=[]
 for q in questions:
  found=False
  for folder,qfile,pfile,label in reuse_sources:
   oq={r['id']:r for r in v.rows(folder/qfile)};op={r['id']:r for r in v.rows(folder/pfile)}
   if q['id'] in op and q['id'] in oq and q['messages']==oq[q['id']]['messages']:
    predictions[q['id']]=op[q['id']];origins.append({'id':q['id'],'origin':'reused_identical_expanded_input','source':label,'questions_sha256':v.sha(folder/qfile),'predictions_sha256':v.sha(folder/pfile),'model_input_equal':True});found=True;break
  if not found:pending.append(q)
 (output/'reuse-evidence').mkdir()
 for folder,qfile,pfile,label in reuse_sources:
  shutil.copyfile(folder/qfile,output/'reuse-evidence'/(label+'-questions.jsonl'));shutil.copyfile(folder/pfile,output/'reuse-evidence'/(label+'-predictions.jsonl'))
 shutil.copyfile(comparison/'profile-receipt.json',output/'reuse-evidence/source-comparison-receipt.json');shutil.copyfile(condition_archive/'package-manifest.json',output/'reuse-evidence/condition-archive-manifest.json')
 status('binding_complete',reused=len(predictions),new_predictions_required=len(pending))
 if pending:
  model,tokenizer,snapshot=run_compact.runtime(cfg,model_profile,cache)
  for name,sha in training['base_weights_sha256'].items():
   if v.sha(snapshot/name)!=sha:raise ValueError('Base snapshot changed')
  from peft import PeftModel
  model=PeftModel.from_pretrained(model,str(source/'adapter'),local_files_only=True).eval()
  fresh=u.predict(model,tokenizer,pending,cfg,output/'new-development-predictions.jsonl',status)
  for r in fresh:predictions[r['id']]=r;origins.append({'id':r['id'],'origin':'newly_generated','model_input_equal':None})
 merged=[predictions[q['id']] for q in questions];u.dump(output/'adapter-development.jsonl',merged);u.save(output/'prediction-origins.json',origins)
 import run_precision
 screens={'adapter':run_precision.development_screen(original,merged)};u.save(output/'adapter-development-screen.json',screens['adapter'])
 u.save(output/'profile-receipt.json',{'status':'development_completed','profile_sha256':v.sha(HERE/'task-routed-profile.json'),'profile_helper_sha256':v.sha(HERE/'task_routed_profile.py'),'comparator_sha256':v.sha(HERE/'compare_task_routed_profile.py'),'development_receipt_sha256':v.sha(source/'development-receipt.json'),'config_sha256':training['config_sha256'],'checkpoint_weights_sha256':partial['checkpoint_weights_sha256'],'base_weights_sha256':training['base_weights_sha256'],'seconds':time.monotonic()-started,'seconds_scope':'Binding and newly generated development predictions only; original timings remain in reused rows.','reused_predictions':len(merged)-len(pending),'new_predictions':len(pending),'reuse_scope':'Retired development only; exact expanded messages, unchanged pinned base/adapter/config, frozen source-code and raw evidence. No unseen score claimed.','registered_new_test_manifest_sha256':v.sha(HERE/'fidelity-test-manifest.json'),'registered_new_domain_manifest_sha256':v.sha(HERE/'fidelity-domain-manifest.json'),'screens':screens,'final_test_generated':False,'independent_expert_validated':False,'files_sha256':{str(p.relative_to(output)):v.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='status.json'}})
 status('development_completed')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source','comparison','condition-archive','output','cache'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();run(**{k:v.resolve() for k,v in vars(a).items()})
