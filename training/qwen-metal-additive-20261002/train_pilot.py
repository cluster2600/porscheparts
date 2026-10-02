"""Inspect the frozen pilot by default; --run explicitly starts future training."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import verify_grounded

HERE = Path(__file__).resolve().parent

def preflight(config_path):
    config = verify_grounded.load(config_path)
    export = (HERE/config['export']).resolve()
    if not export.is_relative_to(HERE.resolve()):
        raise ValueError('Export must be inside this package')
    result = verify_grounded.verify(HERE,export)
    profile = verify_grounded.load(export/'model-profile.json')
    if (config['model_id'],config['revision'])!=(profile['model_id'],profile['revision']):
        raise ValueError('Training model/tokenizer profile mismatch')
    expected_quant={'load_in_4bit':True,'type':'nf4','double_quant':True,'compute_dtype':'bfloat16'}
    if config['training_arguments']['report_to'] or config['quantization']!=expected_quant:
        raise ValueError('Pilot config changed outside its supported profile')
    return config,export,profile,result

def run(config_path,output):
    config,export,profile,_ = preflight(config_path)
    if output.exists():
        raise ValueError('Use a new adapter output directory')
    # Heavy imports, network access and model weights are confined to --run.
    import torch
    from datasets import Dataset
    from huggingface_hub import snapshot_download
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig,
                              DataCollatorForSeq2Seq,Trainer,TrainingArguments,set_seed)
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('This pilot profile requires a CUDA GPU supporting bfloat16')
    set_seed(config['training_arguments']['seed'])
    token_dir = Path(snapshot_download(config['model_id'],revision=config['revision'],
                                      allow_patterns=list(profile['tokenizer_files_sha256'])))
    for name,expected in profile['tokenizer_files_sha256'].items():
        if verify_grounded.sha(token_dir/name)!=expected:
            raise ValueError('Runtime tokenizer differs from exported token arrays')
    tokenizer = AutoTokenizer.from_pretrained(str(token_dir),trust_remote_code=False,local_files_only=True)
    tokenizer.padding_side='right'
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token=tokenizer.eos_token
    quant = BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type=config['quantization']['type'],
                              bnb_4bit_use_double_quant=config['quantization']['double_quant'],
                              bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(config['model_id'],revision=config['revision'],
                trust_remote_code=False,quantization_config=quant,device_map={'':0},torch_dtype=torch.bfloat16)
    model.config.use_cache=False
    model=prepare_model_for_kbit_training(model)
    model=get_peft_model(model,LoraConfig(**config['lora']))
    # Already tokenized once; the collator must preserve assistant-only labels.
    train=Dataset.from_list(verify_grounded.rows(export/'sft_tokens/train.jsonl'))
    valid=Dataset.from_list(verify_grounded.rows(export/'sft_tokens/valid.jsonl'))
    trainer=Trainer(model=model,args=TrainingArguments(output_dir=str(output),**config['training_arguments']),
                    train_dataset=train,eval_dataset=valid,
                    data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer,padding=True,label_pad_token_id=-100))
    trainer.train()
    trainer.save_model(str(output))
    tokenizer.save_pretrained(str(output))
    receipt={'status':'pilot_completed','model_id':config['model_id'],'revision':config['revision'],
             'config_sha256':verify_grounded.sha(config_path),'dataset_manifest_sha256':verify_grounded.sha(export/'manifest.json'),
             'trainer_state':trainer.state.to_dict() if hasattr(trainer.state,'to_dict') else vars(trainer.state),
             'libraries':{n:importlib.metadata.version(n) for n in ('torch','transformers','peft','bitsandbytes','datasets')},
             'test_used_in_training':False,'expert_validated':False,'scientific_model_improvement_claimed':False}
    (output/'training-receipt.json').write_text(json.dumps(receipt,indent=2,default=str)+'\n',encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=HERE/'lora-pilot.json')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if args.run:
        if args.output is None:
            parser.error('--run requires a fresh --output directory')
        run(args.config.resolve(),args.output.resolve())
    else:
        config,export,profile,audit=preflight(args.config.resolve())
        print(json.dumps({'status':'preflight_pass_not_trained','model_id':profile['model_id'],
                          'revision':profile['revision'],'audit':audit,'expert_review':'pending'},indent=2))
