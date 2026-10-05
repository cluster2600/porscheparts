"""Diagnose one exposed training batch on official precisions; never update weights."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import run


def worker(args):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM,AutoTokenizer
    run.verify_snapshot(args.snapshot)
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(42)
    tokenizer=AutoTokenizer.from_pretrained(str(args.snapshot),local_files_only=True)
    record=next(r for r in run.rows(run.HERE/'data/train-records.jsonl') if r['id']==args.record)
    tokens=run.supervised_tokens(record,tokenizer)
    labels=tokens['labels'];positions=[i for i,v in enumerate(labels) if v!=-100]
    result={'status':'started','optimizer_updates':0,'record_id':record['id'],
            'record_sha256':run.object_sha(record),'device':args.device,'dtype':args.dtype,
            'adapter_sha256':run.sha(args.adapter/'adapter_model.safetensors'),
            'sequence_tokens':len(labels),'supervised_tokens':len(positions),
            'first_supervised_position':positions[0],'last_supervised_position':positions[-1],
            'supervised_eos_included':labels[positions[-1]]==tokenizer.eos_token_id,
            'truncated':False,'all_ignored':not positions,'first_bad_parameter_gradient':None,
            'normalization':'mean cross entropy over non-ignored assistant targets',
            'scientific_gain_demonstrated':False}
    result['head_fp32']=args.head_fp32
    run.save(args.output/'batch-diagnostic.json',result)
    model=AutoModelForCausalLM.from_pretrained(str(args.snapshot),local_files_only=True,
             torch_dtype=getattr(torch,args.dtype),attn_implementation='eager').to(args.device)
    if args.head_fp32:
        model.lm_head.to(dtype=torch.float32)
        model.lm_head.register_forward_pre_hook(lambda module,inputs:tuple(v.to(torch.float32) for v in inputs))
    model=PeftModel.from_pretrained(model,str(args.adapter),is_trainable=True)
    model.train();model.config.use_cache=False;model.enable_input_require_grads()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
    def hook(name):
        def observe(gradient):
            if result['first_bad_parameter_gradient'] is None and not torch.isfinite(gradient).all().item():
                result['first_bad_parameter_gradient']=name
                run.save(args.output/'batch-diagnostic.json',result)
            return gradient
        return observe
    for name,p in model.named_parameters():
        if p.requires_grad:p.register_hook(hook(name))
    batch={k:torch.tensor([v],device=args.device) for k,v in tokens.items()}
    tick=time.monotonic()
    context=torch.autograd.detect_anomaly(check_nan=True) if args.anomaly else __import__('contextlib').nullcontext()
    with context:
        loss=model(**batch).loss
        result['loss']=float(loss.detach().cpu());result['loss_finite']=bool(torch.isfinite(loss).item())
        run.save(args.output/'batch-diagnostic.json',result)
        loss.backward()
    finite=[torch.isfinite(p.grad).all() for p in model.parameters() if p.requires_grad and p.grad is not None]
    result.update(status='completed_no_optimizer_update',gradients_finite=bool(finite) and torch.stack(finite).all().item(),seconds=time.monotonic()-tick)
    run.save(args.output/'batch-diagnostic.json',result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--adapter',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--record',default='qualifier-sebm-heat-treatment-en')
    p.add_argument('--device',choices=['cpu','mps'],required=True);p.add_argument('--dtype',choices=['bfloat16','float16','float32'],required=True)
    p.add_argument('--anomaly',action='store_true');p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--head-fp32',action='store_true')
    args=p.parse_args()
    if not args.worker:
        if args.output.exists():p.error('Use a fresh output directory')
        args.output.mkdir(parents=True)
        child=subprocess.Popen([sys.executable,__file__,*sys.argv[1:],'--worker'])
        try:code=child.wait(timeout=600)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            code=124
        if code:run.save(args.output/'interruption-receipt.json',{'status':'diagnostic_interrupted_or_failed','exit_code':code,'optimizer_updates':0})
        return code
    with run.ResourceGuard(args.output):worker(args)
    return 0


if __name__=='__main__':raise SystemExit(main())
