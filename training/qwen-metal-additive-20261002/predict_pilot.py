"""Prepare future base/adapter comparison; --run explicitly downloads weights."""
import argparse
import json
from pathlib import Path
import train_pilot
import verify_grounded

HERE=Path(__file__).resolve().parent
DECODING={'do_sample':False,'max_new_tokens':256}

def run(output,adapter=None):
    config,export,profile,_=train_pilot.preflight(HERE/'lora-pilot.json')
    if output.exists() or output.with_suffix('.receipt.json').exists():
        raise ValueError('Use fresh prediction and receipt paths')
    if adapter is not None:
        receipt=verify_grounded.load(adapter/'training-receipt.json')
        if (receipt['model_id'],receipt['revision'])!=(profile['model_id'],profile['revision']):
            raise ValueError('Adapter model profile mismatch')
        if receipt['dataset_manifest_sha256']!=verify_grounded.sha(export/'manifest.json'):
            raise ValueError('Adapter was trained on a different dataset release')
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig,set_seed
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('This comparison profile requires a CUDA GPU supporting bfloat16')
    set_seed(profile['seed'])
    token_dir=Path(snapshot_download(profile['model_id'],revision=profile['revision'],
                                    allow_patterns=list(profile['tokenizer_files_sha256'])))
    for name,expected in profile['tokenizer_files_sha256'].items():
        if verify_grounded.sha(token_dir/name)!=expected:
            raise ValueError('Tokenizer profile mismatch')
    tokenizer=AutoTokenizer.from_pretrained(str(token_dir),local_files_only=True,trust_remote_code=False)
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)
    model=AutoModelForCausalLM.from_pretrained(profile['model_id'],revision=profile['revision'],
                trust_remote_code=False,quantization_config=quant,device_map={'':0},torch_dtype=torch.bfloat16)
    if adapter is not None:
        from peft import PeftModel
        model=PeftModel.from_pretrained(model,str(adapter),is_trainable=False)
    model.eval()
    predictions=[]
    for row in verify_grounded.rows(export/'evaluation/questions.jsonl'):
        inputs=tokenizer.apply_chat_template(row['messages'],add_generation_prompt=True,
                    return_tensors='pt',return_dict=True,enable_thinking=False).to(model.device)
        with torch.inference_mode():
            tokens=model.generate(**inputs,**DECODING,pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
        response=tokenizer.decode(tokens[0,inputs['input_ids'].shape[-1]:],skip_special_tokens=True).strip()
        predictions.append({'id':row['id'],'response':response})
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in predictions),encoding='utf-8')
    receipt={'model_id':profile['model_id'],'revision':profile['revision'],'adapter':str(adapter) if adapter else None,
             'adapter_sha256':verify_grounded.sha(adapter/'adapter_model.safetensors') if adapter else None,
             'dataset_manifest_sha256':verify_grounded.sha(export/'manifest.json'),'decoding':DECODING,
             'quantization':config['quantization'],'prediction_sha256':verify_grounded.sha(output),
             'scope':'Grounded reading pilot; expert review is still required to score scientific correctness.'}
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--adapter',type=Path)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if args.run:
        if args.output is None:
            parser.error('--run requires --output')
        run(args.output.resolve(),args.adapter.resolve() if args.adapter else None)
    else:
        _,_,profile,audit=train_pilot.preflight(HERE/'lora-pilot.json')
        print(json.dumps({'status':'preflight_pass_no_weights_loaded','model_id':profile['model_id'],
                          'decoding':DECODING,'evaluation_count':audit['evaluation_count']},indent=2))
