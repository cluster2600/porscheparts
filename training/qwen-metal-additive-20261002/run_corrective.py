"""Train fixed corrective checkpoints and score development only; final test is separate."""
import argparse, importlib.metadata, json, re, resource, time
from datetime import datetime,timezone
from pathlib import Path
import verify_grounded
HERE=Path(__file__).resolve().parent

def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n')
def dump(path,rows):path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
def load(path):return verify_grounded.load(path)
def audit():
 cfg=load(HERE/'corrective-config.json');root=HERE/cfg['data'];manifest=load(root/'manifest.json')
 verify_grounded.verify(HERE,HERE/'grounded-v3')
 for name,sha in manifest['files_sha256'].items():
  if verify_grounded.sha(root/name)!=sha:raise ValueError('Corrective data changed: '+name)
 for name,sha in manifest['inputs_sha256'].items():
  if verify_grounded.sha(HERE/name)!=sha:raise ValueError('Corrective authoring input changed: '+name)
 if manifest['source_manifest_sha256']!=verify_grounded.sha(HERE/'grounded-v3/manifest.json'):raise ValueError('Source release changed')
 records=verify_grounded.rows(root/'train-records.jsonl');tokens=verify_grounded.rows(root/'train-tokens.jsonl')
 passages={p['passage_id']:p for p in verify_grounded.rows(HERE/'grounded-v3/passages.jsonl')}
 for record,token in zip(records,tokens):
  p=passages[record['passage_id']]
  if p['split']!='train' or record['excerpt'] not in p['text']:raise ValueError('Train/source boundary changed')
  if record['passage_id'] not in record['messages'][-1]['content']:raise ValueError('Training target lacks reference')
  start=record['assistant_start'];end=record['assistant_eos']
  if any(x!=-100 for x in token['labels'][:start]) or token['labels'][start:end+1]!=token['input_ids'][start:end+1]:raise ValueError('Assistant mask changed')
 return cfg,root,manifest

def predict(model,tokenizer,questions,cfg,path,status):
 import torch
 result=[];model.eval()
 with torch.inference_mode(),torch.autocast('cpu',dtype=torch.bfloat16):
  for q in questions:
   start=time.monotonic();inputs=tokenizer.apply_chat_template(q['messages'],tokenize=True,return_tensors='pt',return_dict=True,add_generation_prompt=True,enable_thinking=False)
   out=model.generate(**inputs,**cfg['decoding'],pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
   tokens=out[0,inputs['input_ids'].shape[-1]:];response=tokenizer.decode(tokens,skip_special_tokens=True).strip()
   result.append({'id':q['id'],'response':response,'generated_tokens':len(tokens),'seconds':time.monotonic()-start,'reached_token_budget':len(tokens)>=cfg['decoding']['max_new_tokens']})
   dump(path.with_suffix('.partial.jsonl'),result);status('prediction',evaluation=path.stem,id=q['id'],tokens=len(tokens))
 dump(path,result);return result

def development_screen(questions,predictions):
 critical={'eval-001','eval-002','eval-003','eval-004','eval-005','eval-007','eval-008'}
 result=[]
 for q,r in zip(questions,predictions):
  citations=re.findall(r'\[[\w]+:p\d+\]',q['messages'][1]['content'])
  expected=citations[-1];response=r['response'];prefix=response.lower()[:180]
  boundary=bool(re.search(r'\bnon\b|ne (?:permet|fournit|donne|précise)|pas (?:possible|de valeur)|impossible|insuffisan|manqu',prefix)) if q['id'] in critical else None
  result.append({'id':q['id'],'expected_citation':expected,'citation_present':expected in response,'critical_boundary_screen':boundary,'reached_token_budget':r['reached_token_budget']})
 return {'examples':len(result),'expected_citations':sum(r['citation_present'] for r in result),'critical_boundaries_screened':sum(r['critical_boundary_screen'] is not None for r in result),'critical_boundaries_pass':sum(r['critical_boundary_screen'] is True for r in result),'token_budget_hits':sum(r['reached_token_budget'] for r in result),'rows':result,'scope':'Lexical development screen, not semantic accuracy or expert review.'}

def runtime(cfg,cache):
 import torch
 from transformers import AutoModelForCausalLM,AutoTokenizer,set_seed
 from huggingface_hub import snapshot_download
 torch.set_num_threads(cfg['threads']);torch.set_num_interop_threads(1);set_seed(cfg['training']['seed'])
 profile=load(HERE/'corrective-v4/model-profile.json')
 snapshot=Path(snapshot_download(cfg['model_id'],revision=cfg['revision'],cache_dir=str(cache),allow_patterns=[*profile['tokenizer_files_sha256'],'*.safetensors','*.safetensors.index.json','generation_config.json']))
 for name,sha in profile['tokenizer_files_sha256'].items():
  if verify_grounded.sha(snapshot/name)!=sha:raise ValueError('Tokenizer changed')
 tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True);tokenizer.padding_side='right'
 model=AutoModelForCausalLM.from_pretrained(str(snapshot),local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa')
 return model,tokenizer,snapshot

def run(output,cache):
 cfg,root,manifest=audit()
 if output.exists():raise ValueError('Use a fresh experiment directory')
 output.mkdir(parents=True);started=time.monotonic()
 def status(stage,**detail):
  record={'stage':stage,'time':datetime.now(timezone.utc).isoformat(),**detail};save(output/'status.json',record);print(json.dumps(record),flush=True)
 status('loading');model,tokenizer,snapshot=runtime(cfg,cache)
 questions=verify_grounded.rows(root/'development.jsonl')
 base=predict(model,tokenizer,questions,cfg,output/'base-development.jsonl',status);save(output/'base-development-screen.json',development_screen(questions,base))
 from peft import LoraConfig,get_peft_model
 from datasets import Dataset
 from transformers import Trainer,TrainingArguments,DataCollatorForSeq2Seq,TrainerCallback
 model.config.use_cache=False;model=get_peft_model(model,LoraConfig(**cfg['lora']))
 class Progress(TrainerCallback):
  def on_log(self,args,state,control,logs=None,**kwargs):status('training',step=state.global_step,epoch=state.epoch,metrics=logs)
 trainer=Trainer(model=model,args=TrainingArguments(output_dir=str(output/'checkpoints'),**cfg['training']),train_dataset=Dataset.from_list(verify_grounded.rows(root/'train-tokens.jsonl')),data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer,padding=True,label_pad_token_id=-100),callbacks=[Progress()])
 status('training');train_start=time.monotonic();result=trainer.train();training_seconds=time.monotonic()-train_start
 save(output/'training-metrics.json',result.metrics);save(output/'trainer-history.json',trainer.state.log_history)
 model.config.use_cache=True
 checkpoints=sorted((output/'checkpoints').glob('checkpoint-*'),key=lambda p:int(p.name.split('-')[-1]))
 screens={}
 for checkpoint in checkpoints:
  name=checkpoint.name;model.load_adapter(str(checkpoint),adapter_name=name,is_trainable=False);model.set_adapter(name)
  result_rows=predict(model,tokenizer,questions,cfg,output/(name+'-development.jsonl'),status)
  screens[name]=development_screen(questions,result_rows);save(output/(name+'-development-screen.json'),screens[name])
 receipt={'status':'development_completed','model_id':cfg['model_id'],'revision':cfg['revision'],'dataset_manifest_sha256':verify_grounded.sha(root/'manifest.json'),'config_sha256':verify_grounded.sha(HERE/'corrective-config.json'),'runner_sha256':verify_grounded.sha(HERE/'run_corrective.py'),'training_seconds':training_seconds,'total_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'global_step':trainer.state.global_step,'training_sources':manifest['training_sources'],'train_rows':manifest['train_rows'],'test_used_in_training':False,'final_test_generated':False,'expert_validated':False,'screens':screens,'base_screen':development_screen(questions,base),'libraries':{n:importlib.metadata.version(n) for n in ('torch','transformers','peft','datasets','accelerate')},'base_weights_sha256':{p.name:verify_grounded.sha(p) for p in snapshot.glob('*.safetensors')},'checkpoint_weights_sha256':{p.name:verify_grounded.sha(p/'adapter_model.safetensors') for p in checkpoints}}
 save(output/'development-receipt.json',receipt);status('development_completed')

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true');parser.add_argument('--output',type=Path);parser.add_argument('--cache',type=Path)
 args=parser.parse_args()
 if args.run:
  if args.output is None or args.cache is None:parser.error('--run requires --output and --cache')
  run(args.output.resolve(),args.cache.resolve())
 else:
  _,_,manifest=audit();print(json.dumps({'status':'preflight_pass_not_trained','train_rows':manifest['train_rows']}))
