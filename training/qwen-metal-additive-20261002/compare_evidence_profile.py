"""Compare quote-first development answers without generating final-test data."""
import argparse,json,time
from pathlib import Path
from peft import PeftModel
import evidence_profile,run_corrective,verify_grounded
HERE=Path(__file__).resolve().parent

def run(source,output,cache):
 cfg,root,_=run_corrective.audit()
 if output.exists():raise ValueError('Use a fresh profile comparison directory')
 receipt=run_corrective.load(source/'development-receipt.json')
 if receipt['dataset_manifest_sha256']!=verify_grounded.sha(root/'manifest.json'):raise ValueError('Wrong dataset')
 output.mkdir(parents=True);started=time.monotonic()
 def status(stage,**detail):
  r={'stage':stage,**detail};run_corrective.save(output/'status.json',r);print(json.dumps(r),flush=True)
 original_questions=verify_grounded.rows(root/'development.jsonl')
 questions=evidence_profile.questions_with_profile(original_questions)
 run_corrective.dump(output/'questions.jsonl',questions)
 model,tokenizer,_=run_corrective.runtime(cfg,cache)
 predictions=run_corrective.predict(model,tokenizer,questions,cfg,output/'base-development.jsonl',status)
 screens={'base':run_corrective.development_screen(original_questions,predictions)}
 run_corrective.save(output/'base-development-screen.json',screens['base'])
 for name,weight_sha in receipt['checkpoint_weights_sha256'].items():
  path=source/'checkpoints'/name
  if verify_grounded.sha(path/'adapter_model.safetensors')!=weight_sha:raise ValueError('Checkpoint changed')
  if not isinstance(model,PeftModel):model=PeftModel.from_pretrained(model,str(path),adapter_name=name,local_files_only=True)
  else:model.load_adapter(str(path),adapter_name=name,is_trainable=False);model.set_adapter(name)
  predictions=run_corrective.predict(model,tokenizer,questions,cfg,output/(name+'-development.jsonl'),status)
  screens[name]=run_corrective.development_screen(original_questions,predictions);run_corrective.save(output/(name+'-development-screen.json'),screens[name])
 run_corrective.save(output/'profile-receipt.json',{'status':'development_completed','profile_sha256':verify_grounded.sha(HERE/'evidence-profile.json'),'profile_helper_sha256':verify_grounded.sha(HERE/'evidence_profile.py'),'comparator_sha256':verify_grounded.sha(HERE/'compare_evidence_profile.py'),'development_receipt_sha256':verify_grounded.sha(source/'development-receipt.json'),'seconds':time.monotonic()-started,'screens':screens,'final_test_generated':False,'independent_expert_validated':False,'files_sha256':{p.name:verify_grounded.sha(p) for p in output.iterdir() if p.is_file() and p.name!='status.json'}})
 status('development_completed')

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for flag in ('source','output','cache'):parser.add_argument('--'+flag,type=Path,required=True)
 args=parser.parse_args();run(args.source.resolve(),args.output.resolve(),args.cache.resolve())
