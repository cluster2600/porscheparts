"""Compare the explicit-tail profile on old development prompts only."""
import argparse,json,time
from pathlib import Path
from peft import PeftModel
import run_compact,run_corrective,quote_first_fidelity_profile,verify_grounded
HERE=Path(__file__).resolve().parent

def run(source,output,cache):
 cfg,root,_,model_profile=run_compact.audit()
 if output.exists():raise ValueError('Use a fresh comparison directory')
 receipt=run_corrective.load(source/'development-receipt.json')
 if receipt['dataset_manifest_sha256']!=verify_grounded.sha(root/'manifest.json'):raise ValueError('Dataset differs')
 adapter=source/'adapter'
 if verify_grounded.sha(adapter/'adapter_model.safetensors')!=receipt['adapter_files_sha256']['adapter_model.safetensors']:raise ValueError('Adapter changed')
 output.mkdir(parents=True);started=time.monotonic()
 def status(stage,**detail):
  record={'stage':stage,**detail};run_corrective.save(output/'status.json',record);print(json.dumps(record),flush=True)
 original=verify_grounded.rows(HERE/'corrective-v4/development.jsonl')
 original+=[q for q in verify_grounded.rows(HERE/'corrective-v4/final-test.jsonl') if q['id'] in ('fresh-03','fresh-05')]
 original+=[q for q in verify_grounded.rows(HERE/'corrective-domain-benchmark.jsonl') if q['id'] in ('heat-07','heat-08')]
 original+=[q for q in verify_grounded.rows(HERE/'precision-final-test.jsonl') if q['id'] in ('precision-01','precision-02','precision-03')]
 import audit_fidelity
 audit_fidelity.audit()
 priority=['eval-002','precision-01','precision-02','precision-03']
 original.sort(key=lambda q:priority.index(q['id']) if q['id'] in priority else len(priority))
 questions=quote_first_fidelity_profile.questions_with_profile(original)
 run_corrective.dump(output/'questions.jsonl',questions)
 model,tokenizer,snapshot=run_compact.runtime(cfg,model_profile,cache)
 for name,sha in receipt['base_weights_sha256'].items():
  if verify_grounded.sha(snapshot/name)!=sha:raise ValueError('Base weights changed')
 screens={}
 for name in ('adapter',):
  if name=='adapter':model=PeftModel.from_pretrained(model,str(adapter),local_files_only=True).eval()
  predictions=run_corrective.predict(model,tokenizer,questions,cfg,output/(name+'-development.jsonl'),status)
  import run_precision
  screens[name]=run_precision.development_screen(original,predictions);run_corrective.save(output/(name+'-development-screen.json'),screens[name])
 run_corrective.save(output/'profile-receipt.json',{'status':'development_completed','profile_sha256':verify_grounded.sha(HERE/'quote-first-fidelity-profile.json'),'profile_helper_sha256':verify_grounded.sha(HERE/'quote_first_fidelity_profile.py'),'comparator_sha256':verify_grounded.sha(HERE/'compare_quote_first_fidelity_profile.py'),'development_receipt_sha256':verify_grounded.sha(source/'development-receipt.json'),'seconds':time.monotonic()-started,'registered_new_test_manifest_sha256':verify_grounded.sha(HERE/'fidelity-test-manifest.json'),'registered_new_domain_manifest_sha256':verify_grounded.sha(HERE/'fidelity-domain-manifest.json'),'screens':screens,'development_scope':'Fifteen retired questions only; adapter-only development screening, paired control reserved for final evaluation.','final_test_generated':False,'independent_expert_validated':False,'files_sha256':{p.name:verify_grounded.sha(p) for p in output.iterdir() if p.is_file() and p.name!='status.json'}})
 status('development_completed')

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('source','output','cache'):parser.add_argument('--'+name,type=Path,required=True)
 args=parser.parse_args();run(args.source.resolve(),args.output.resolve(),args.cache.resolve())
