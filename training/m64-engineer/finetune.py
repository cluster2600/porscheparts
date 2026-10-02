#!/usr/bin/env python3
"""Single NVIDIA GPU QLoRA training, and a separate unquantized CPU merge."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re


def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def read_data(folder, tokenizer, max_length):
    from dataset import check
    from datasets import Dataset
    result, families, seen = {}, {}, set()
    for name in ('train','valid','test'):
        path=folder/(name+'.jsonl')
        records=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if not records: raise ValueError(f'empty {name}')
        check(records)
        examples=[]
        for row in records:
            group=row['family_id']
            if group in families and families[group]!=name: raise ValueError('family leakage')
            families[group]=name
            key=' '.join(row['messages'][1]['content'].split())
            if key in seen: raise ValueError('cross-split prompt duplicate')
            seen.add(key)
            messages=row['messages']
            tokens=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=False)
            if len(tokens)>max_length: raise ValueError(f'{row["id"]}: {len(tokens)} tokens; split the task instead of truncating')
            examples.append({'prompt':messages[:-1],'completion':messages[-1:]})
        # Test answers are validated for integrity but never supplied to SFTTrainer.
        if name!='test': result[name]=Dataset.from_list(examples)
    return result


def train(a):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, set_seed
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTConfig, SFTTrainer
    if not torch.cuda.is_available(): raise RuntimeError('This recipe requires a local CUDA GPU; use the existing MLX runner on Mac.')
    if int(os.environ.get('WORLD_SIZE','1'))!=1: raise RuntimeError('Single GPU recipe: distributed training requires a separately validated configuration.')
    if not re.fullmatch(r'[0-9a-f]{40}',a.revision): raise ValueError('pin a full model commit SHA')
    if a.output.exists(): raise ValueError('choose a new output directory')
    if a.rank<=0 or a.max_length<128 or a.learning_rate<=0 or a.epochs<=0: raise ValueError('invalid training parameters')
    set_seed(a.seed)
    bf16=torch.cuda.is_bf16_supported()
    dtype=torch.bfloat16 if bf16 else torch.float16
    tokenizer=AutoTokenizer.from_pretrained(a.model,revision=a.revision,token=False,trust_remote_code=False)
    tokenizer.eos_token='<|im_end|>'
    tokenizer.pad_token='<|endoftext|>'
    tokenizer.padding_side='right'
    data=read_data(a.data,tokenizer,a.max_length)
    model=AutoModelForCausalLM.from_pretrained(a.model,revision=a.revision,token=False,trust_remote_code=False,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=dtype),
        torch_dtype=dtype,device_map={'':0},attn_implementation='sdpa')
    model.config.use_cache=False
    model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True,
                                          gradient_checkpointing_kwargs={'use_reentrant':False})
    model=get_peft_model(model,LoraConfig(task_type='CAUSAL_LM',r=a.rank,lora_alpha=2*a.rank,
        lora_dropout=0.05,bias='none',target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj']))
    model.print_trainable_parameters()
    config=SFTConfig(output_dir=str(a.output),num_train_epochs=a.epochs,max_steps=a.max_steps,
        per_device_train_batch_size=1,per_device_eval_batch_size=1,gradient_accumulation_steps=16,
        learning_rate=a.learning_rate,lr_scheduler_type='cosine',warmup_ratio=0.03,max_grad_norm=1.0,
        optim='paged_adamw_8bit',weight_decay=0.01,bf16=bf16,fp16=not bf16,
        gradient_checkpointing=True,gradient_checkpointing_kwargs={'use_reentrant':False},
        max_length=a.max_length,packing=False,completion_only_loss=True,assistant_only_loss=False,
        eos_token='<|im_end|>',eval_strategy='steps',eval_steps=50,save_strategy='steps',save_steps=50,
        save_total_limit=2,logging_steps=10,report_to='none',push_to_hub=False,
        seed=a.seed,data_seed=a.seed,dataloader_num_workers=0)
    trainer=SFTTrainer(model=model,args=config,processing_class=tokenizer,
                       train_dataset=data['train'],eval_dataset=data['valid'])
    # Verify the actual TRL collator masks the prompt and trains the response/EOS.
    for index in range(len(trainer.train_dataset)):
        sample=trainer.train_dataset[index]
        batch=trainer.data_collator([sample])
        labels=batch['labels'][0]
        if not (labels==-100).any() or not (labels!=-100).any(): raise RuntimeError('invalid loss mask')
        mask=sample['completion_mask']
        if any(int(labels[i])!=-100 for i,value in enumerate(mask) if not value): raise RuntimeError('prompt leak into loss')
        eos=tokenizer.eos_token_id
        if eos not in labels[labels!=-100].tolist(): raise RuntimeError('assistant EOS missing from loss')
    a.output.mkdir(parents=True,exist_ok=True)
    provenance={'model':a.model,'revision':a.revision,'arguments':{k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
        'script_sha256':digest(Path(__file__)),'dataset_hashes':{n:digest(a.data/(n+'.jsonl')) for n in ('train','valid','test')},
        'versions':{p:importlib.metadata.version(p) for p in ('torch','transformers','trl','peft','accelerate','datasets','bitsandbytes')},
        'gpu':torch.cuda.get_device_name(0),'cuda':torch.version.cuda,'chat_template_sha256':hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()}
    (a.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    torch.cuda.reset_peak_memory_stats()
    result=trainer.train()
    adapter=a.output/'adapter'
    model.save_pretrained(adapter,safe_serialization=True)
    tokenizer.save_pretrained(adapter)
    metrics=dict(result.metrics,peak_allocated_gib=torch.cuda.max_memory_allocated()/1024**3,
                 validation=trainer.evaluate())
    (a.output/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n')
    (adapter/'training-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(f'Saved experimental adapter: {adapter}')


def merge(a):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    if a.output.exists(): raise ValueError('choose a new merge output directory')
    meta=json.loads((a.adapter/'training-provenance.json').read_text())
    # Reload original BF16 weights. Never merge into an already quantized checkpoint.
    base=AutoModelForCausalLM.from_pretrained(meta['model'],revision=meta['revision'],token=False,
        trust_remote_code=False,torch_dtype=torch.bfloat16,device_map={'':'cpu'},low_cpu_mem_usage=True)
    model=PeftModel.from_pretrained(base,str(a.adapter),is_trainable=False).merge_and_unload(safe_merge=True)
    tokenizer=AutoTokenizer.from_pretrained(str(a.adapter),local_files_only=True,trust_remote_code=False)
    model.config.use_cache=True
    model.config.eos_token_id=tokenizer.eos_token_id
    model.generation_config.eos_token_id=tokenizer.eos_token_id
    model.generation_config.pad_token_id=tokenizer.pad_token_id
    model.save_pretrained(a.output,safe_serialization=True,max_shard_size='4GB')
    tokenizer.save_pretrained(a.output)
    (a.output/'training-provenance.json').write_text(json.dumps(meta,indent=2)+'\n')


def main():
    os.environ.update(HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false',WANDB_DISABLED='true')
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    t=sub.add_parser('train'); t.add_argument('--model',default='Qwen/Qwen2.5-Coder-7B-Instruct')
    t.add_argument('--revision',required=True); t.add_argument('--data',type=Path,required=True)
    t.add_argument('--output',type=Path,required=True); t.add_argument('--rank',type=int,default=32)
    t.add_argument('--epochs',type=float,default=1); t.add_argument('--max-steps',type=int,default=-1)
    t.add_argument('--max-length',type=int,default=4096); t.add_argument('--learning-rate',type=float,default=1e-4)
    t.add_argument('--seed',type=int,default=42)
    m=sub.add_parser('merge'); m.add_argument('--adapter',type=Path,required=True); m.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.action=='train': train(a)
    else: merge(a)

if __name__=='__main__': main()
