"""Run a fact-rich CPU LoRA cycle on the pinned Qwen3 4B Instruct base."""
import argparse,importlib.metadata,json,resource,time
from datetime import datetime,timezone
from pathlib import Path
import evidence_profile,run_corrective,verify_grounded
HERE=Path(__file__).resolve().parent

def audit():
 cfg=run_corrective.load(HERE/'compact-config.json');root=HERE/cfg['data'];manifest=run_corrective.load(root/'manifest.json');profile=run_corrective.load(root/'model-profile.json')
 verify_grounded.verify(HERE,HERE/'grounded-v3')
 for name,sha in manifest['files_sha256'].items():
  if verify_grounded.sha(root/name)!=sha:raise ValueError('Compact release changed: '+name)
 if manifest['producer_sha256']!=verify_grounded.sha(HERE/'prepare_compact.py') or manifest['evidence_profile_sha256']!=verify_grounded.sha(HERE/'evidence-profile.json'):raise ValueError('Producer or inference profile changed')
 if (cfg['model_id'],cfg['revision'])!=(profile['model_id'],profile['revision']):raise ValueError('Compact base/profile mismatch')
 if manifest['parent_manifest_sha256']!=verify_grounded.sha(HERE/'grounded-v3/manifest.json'):raise ValueError('Parent release changed')
 passages={p['passage_id']:p for p in verify_grounded.rows(HERE/'grounded-v3/passages.jsonl')}
 records=verify_grounded.rows(root/'train-records.jsonl');tokens=verify_grounded.rows(root/'train-tokens.jsonl')
 if len(records)!=24 or len(tokens)!=len(records):raise ValueError('Curriculum incomplete')
 for r,t in zip(records,tokens):
  if passages[r['passage_id']]['split']!='train':raise ValueError('Held-out text in training')
  start,end=r['assistant_start'],r['assistant_eos']
  if any(i!=-100 for i in t['labels'][:start]) or t['labels'][start:end+1]!=t['input_ids'][start:end+1]:raise ValueError('Assistant mask changed')
 return cfg,root,manifest,profile

def runtime(cfg,profile,cache):
 import torch
 from huggingface_hub import snapshot_download
 from transformers import AutoModelForCausalLM,AutoTokenizer,set_seed
 torch.set_num_threads(cfg['threads']);torch.set_num_interop_threads(1);set_seed(cfg['training']['seed'])
 snapshot=Path(snapshot_download(cfg['model_id'],revision=cfg['revision'],cache_dir=str(cache),allow_patterns=[*profile['tokenizer_files_sha256'],'*.safetensors','*.safetensors.index.json','generation_config.json']))
 for name,sha in profile['tokenizer_files_sha256'].items():
  if verify_grounded.sha(snapshot/name)!=sha:raise ValueError('Runtime tokenizer changed')
 tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True);tokenizer.padding_side='right'
 model=AutoModelForCausalLM.from_pretrained(str(snapshot),local_files_only=True,torch_dtype=torch.bfloat16,attn_implementation='sdpa')
 return model,tokenizer,snapshot

def run(output,cache):
 cfg,root,manifest,profile=audit()
 if output.exists():raise ValueError('Use a fresh run directory')
 output.mkdir(parents=True);started=time.monotonic()
 def status(stage,**detail):
  r={'stage':stage,'time':datetime.now(timezone.utc).isoformat(),**detail};run_corrective.save(output/'status.json',r);print(json.dumps(r),flush=True)
 status('loading');model,tokenizer,snapshot=runtime(cfg,profile,cache)
 original=verify_grounded.rows(HERE/'corrective-v4/development.jsonl');questions=evidence_profile.questions_with_profile(original)
 run_corrective.dump(output/'development-questions.jsonl',questions)
 baseline=run_corrective.predict(model,tokenizer,questions,cfg,output/'base-development.jsonl',status)
 run_corrective.save(output/'base-development-screen.json',run_corrective.development_screen(original,baseline))
 from datasets import Dataset
 from peft import LoraConfig,get_peft_model
 from transformers import Trainer,TrainingArguments,DataCollatorForSeq2Seq,TrainerCallback
 model.config.use_cache=False;model=get_peft_model(model,LoraConfig(**cfg['lora']));model.enable_input_require_grads()
 class Progress(TrainerCallback):
  def on_log(self,args,state,control,logs=None,**kwargs):status('training',step=state.global_step,epoch=state.epoch,metrics=logs)
 trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)
 trainer=Trainer(model=model,args=TrainingArguments(output_dir=str(output/'adapter'),**cfg['training']),train_dataset=Dataset.from_list(verify_grounded.rows(root/'train-tokens.jsonl')),data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer,padding=True,label_pad_token_id=-100),callbacks=[Progress()])
 status('training');begin=time.monotonic();trained=trainer.train();training_seconds=time.monotonic()-begin
 trainer.save_model(str(output/'adapter'));tokenizer.save_pretrained(str(output/'adapter'))
 run_corrective.save(output/'training-metrics.json',trained.metrics);run_corrective.save(output/'trainer-history.json',trainer.state.log_history)
 model.gradient_checkpointing_disable();model.config.use_cache=True
 predictions=run_corrective.predict(model,tokenizer,questions,cfg,output/'adapter-development.jsonl',status)
 run_corrective.save(output/'adapter-development-screen.json',run_corrective.development_screen(original,predictions))
 receipt={'status':'development_completed','model_id':cfg['model_id'],'revision':cfg['revision'],'dataset_manifest_sha256':verify_grounded.sha(root/'manifest.json'),'config_sha256':verify_grounded.sha(HERE/'compact-config.json'),'runner_sha256':verify_grounded.sha(HERE/'run_compact.py'),'profile_sha256':verify_grounded.sha(HERE/'evidence-profile.json'),'profile_helper_sha256':verify_grounded.sha(HERE/'evidence_profile.py'),'training_seconds':training_seconds,'total_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'global_step':trainer.state.global_step,'train_rows':manifest['train_rows'],'trainable_parameters':trainable,'test_used_in_training':False,'final_test_generated':False,'independent_expert_validated':False,'base_weights_sha256':{p.name:verify_grounded.sha(p) for p in snapshot.glob('*.safetensors')},'adapter_files_sha256':{p.name:verify_grounded.sha(p) for p in (output/'adapter').iterdir() if p.is_file()},'libraries':{n:importlib.metadata.version(n) for n in ('torch','transformers','tokenizers','peft','accelerate','datasets','huggingface-hub')}}
 run_corrective.save(output/'development-receipt.json',receipt);status('development_completed')

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true');parser.add_argument('--output',type=Path);parser.add_argument('--cache',type=Path);args=parser.parse_args()
 if args.run:
  if args.output is None or args.cache is None:parser.error('--run needs --output and --cache')
  run(args.output.resolve(),args.cache.resolve())
 else:
  _,_,manifest,_=audit();print(json.dumps({'status':'compact_preflight_pass_not_trained','train_rows':manifest['train_rows']}))
