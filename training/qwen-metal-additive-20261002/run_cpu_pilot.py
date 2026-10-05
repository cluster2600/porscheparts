"""Run the fixed CPU LoRA pilot and base/adapter comparison without editing v3."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import resource
import time
import evaluate_grounded
import train_pilot
import verify_grounded

HERE=Path(__file__).resolve().parent

def now():
    return datetime.now(timezone.utc).isoformat()

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')

def save_rows(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in value),encoding='utf-8')

def run(output,cache):
    if output.exists():
        raise ValueError('Use a fresh run output directory')
    config,export,profile,audit=train_pilot.preflight(HERE/'lora-pilot.json')
    cpu=verify_grounded.load(HERE/'cpu-pilot.json')
    if cpu['device']!='cpu' or cpu['dtype']!='bfloat16' or cpu['quantization'] is not None:
        raise ValueError('Unsupported CPU experiment profile')
    import torch
    from datasets import Dataset
    from huggingface_hub import snapshot_download
    from peft import LoraConfig,get_peft_model
    from transformers import AutoModelForCausalLM,AutoTokenizer,DataCollatorForSeq2Seq,Trainer,TrainingArguments,set_seed
    torch.set_num_threads(cpu['threads'])
    torch.set_num_interop_threads(1)
    set_seed(config['training_arguments']['seed'])
    output.mkdir(parents=True)
    started=now();begin=time.monotonic()
    def status(stage,**detail):
        value={'stage':stage,'time':now(),**detail}
        save(output/'status.json',value)
        print(json.dumps(value),flush=True)
    status('downloading_pinned_model')
    snapshot=Path(snapshot_download(profile['model_id'],revision=profile['revision'],cache_dir=str(cache),
        allow_patterns=[*profile['tokenizer_files_sha256'],'*.safetensors','*.safetensors.index.json','generation_config.json']))
    for name,expected in profile['tokenizer_files_sha256'].items():
        if verify_grounded.sha(snapshot/name)!=expected:
            raise ValueError('Runtime tokenizer differs from frozen arrays')
    tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False)
    tokenizer.padding_side='right'
    model=AutoModelForCausalLM.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False,
            torch_dtype=torch.bfloat16,attn_implementation='sdpa')
    collator=DataCollatorForSeq2Seq(tokenizer=tokenizer,padding=True,label_pad_token_id=-100)
    validation=verify_grounded.rows(export/'sft_tokens/valid.jsonl')
    questions=verify_grounded.rows(export/'evaluation/questions.jsonl')
    def loss(model):
        model.eval();values=[]
        with torch.inference_mode(),torch.autocast('cpu',dtype=torch.bfloat16):
            for row in validation:
                batch=collator([row])
                values.append(float(model(**batch).loss))
        return {'mean_example_loss':sum(values)/len(values),'example_losses':values,'examples':len(values),
                'scope':'Mean per-example assistant-token cross-entropy on validation; not scientific accuracy.'}
    def predict(model,name):
        model.eval();predictions=[];timings=[]
        with torch.inference_mode(),torch.autocast('cpu',dtype=torch.bfloat16):
            for row in questions:
                start=time.monotonic()
                inputs=tokenizer.apply_chat_template(row['messages'],add_generation_prompt=True,
                    tokenize=True,return_tensors='pt',return_dict=True,enable_thinking=False)
                tokens=model.generate(**inputs,**cpu['decoding'],pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
                generated=tokens[0,inputs['input_ids'].shape[-1]:]
                response=tokenizer.decode(generated,skip_special_tokens=True).strip()
                predictions.append({'id':row['id'],'response':response})
                timings.append({'id':row['id'],'generated_tokens':len(generated),'seconds':time.monotonic()-start,
                                'reached_token_budget':len(generated)>=cpu['decoding']['max_new_tokens']})
                save_rows(output/(name+'-predictions.partial.jsonl'),predictions)
                status(name+'_prediction',id=row['id'],generated_tokens=len(generated))
        save_rows(output/(name+'-predictions.jsonl'),predictions)
        save(output/(name+'-timings.json'),timings)
        report,worksheet=evaluate_grounded.evaluate(export,predictions)
        save(output/(name+'-evaluation.json'),report)
        save_rows(output/(name+'-review.jsonl'),worksheet)
        return report
    status('base_validation')
    base_loss=loss(model);save(output/'base-validation.json',base_loss)
    status('base_predictions',mean_example_loss=base_loss['mean_example_loss'])
    base_report=predict(model,'base')
    status('training')
    model.config.use_cache=False
    model=get_peft_model(model,LoraConfig(**config['lora']))
    model.enable_input_require_grads()
    model.print_trainable_parameters()
    arguments={**config['training_arguments'],'use_cpu':True,'dataloader_pin_memory':False,'disable_tqdm':True}
    trainer=Trainer(model=model,args=TrainingArguments(output_dir=str(output/'adapter'),**arguments),
        train_dataset=Dataset.from_list(verify_grounded.rows(export/'sft_tokens/train.jsonl')),
        eval_dataset=Dataset.from_list(validation),data_collator=collator)
    train_start=time.monotonic()
    result=trainer.train()
    trainer.save_model(str(output/'adapter'));tokenizer.save_pretrained(str(output/'adapter'))
    save(output/'training-metrics.json',result.metrics)
    save(output/'trainer-history.json',trainer.state.log_history)
    save(output/'adapter/training-receipt.json',{'status':'cpu_lora_pilot_completed','model_id':profile['model_id'],
        'revision':profile['revision'],'dataset_manifest_sha256':verify_grounded.sha(export/'manifest.json'),
        'device':'cpu','dtype':'bfloat16','quantization':None,'global_step':trainer.state.global_step,
        'train_rows':len(trainer.train_dataset),'validation_rows':len(validation),'test_used_in_training':False})
    training_seconds=time.monotonic()-train_start
    model.gradient_checkpointing_disable();model.config.use_cache=True
    status('adapter_validation')
    adapter_loss=loss(model);save(output/'adapter-validation.json',adapter_loss)
    status('adapter_predictions',mean_example_loss=adapter_loss['mean_example_loss'])
    adapter_report=predict(model,'adapter')
    receipt={'status':'completed','started_at':started,'completed_at':now(),
        'model_id':profile['model_id'],'revision':profile['revision'],
        'dataset_manifest_sha256':verify_grounded.sha(export/'manifest.json'),
        'cpu_config_sha256':verify_grounded.sha(HERE/'cpu-pilot.json'),
        'source_config_sha256':verify_grounded.sha(HERE/'lora-pilot.json'),
        'runner_sha256':verify_grounded.sha(HERE/'run_cpu_pilot.py'),
        'device':'cpu','dtype':'bfloat16','quantization':None,'threads':cpu['threads'],
        'training_seconds':training_seconds,'total_seconds':time.monotonic()-begin,
        'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'training_metrics':result.metrics,'base_validation':base_loss,'adapter_validation':adapter_loss,
        'base_evaluation':base_report,'adapter_evaluation':adapter_report,
        'decoding':cpu['decoding'],'test_used_in_training':False,'expert_validated':False,
        'libraries':{n:importlib.metadata.version(n) for n in ('torch','transformers','tokenizers','peft','accelerate','datasets','huggingface-hub')},
        'weight_files_sha256':{p.name:verify_grounded.sha(p) for p in snapshot.glob('*.safetensors')},
        'adapter_files_sha256':{p.name:verify_grounded.sha(p) for p in (output/'adapter').iterdir() if p.is_file()},
        'limitations':['One small fixed run; no independent expert review or statistical significance.',
                      'Validation loss/citation presence do not establish scientific correctness.',
                      'CPU unquantized BF16 results do not measure the prepared GPU NF4 profile.']}
    save(output/'run-receipt.json',receipt)
    status('completed',training_seconds=training_seconds)
    return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--cache',type=Path)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if args.run:
        if args.output is None or args.cache is None:
            parser.error('--run requires --output and --cache')
        run(args.output.resolve(),args.cache.resolve())
    else:
        _,_,profile,audit=train_pilot.preflight(HERE/'lora-pilot.json')
        print(json.dumps({'status':'cpu_preflight_pass_not_trained','model_id':profile['model_id'],'audit':audit},indent=2))
