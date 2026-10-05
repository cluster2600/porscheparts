"""Check gradients on inspected training rows without optimizer updates."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import run


def worker(snapshot, output, adapter=None, dtype='bfloat16', all_rows=False):
    import torch
    from peft import PeftModel
    started = time.monotonic()
    model, tokenizer, files = run.runtime(snapshot)
    projection_receipt = getattr(model, '_projection_receipt', None)
    run.save(output/'projection-receipt.json', projection_receipt)
    if projection_receipt and dtype != 'bfloat16':
        raise ValueError('Registered separate projection requires BF16 embedding; no whole-model dtype override')
    if dtype == 'float16':
        model.to(dtype=torch.float16)
    model = PeftModel.from_pretrained(model, str(adapter or run.PACK / 'adapter'), is_trainable=True)
    lifecycle = [run.projection_integrity(model, projection_receipt, 'after_peft')] if projection_receipt else []
    model.config.use_cache = False
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    records = run.rows(run.HERE / 'data/train-records.jsonl')
    cases = [(r,run.supervised_tokens(r,tokenizer)) for r in records]
    if not all_rows:
        cases = [cases[0], *sorted(cases[1:],key=lambda p:len(p[1]['input_ids']),reverse=True)[:3]]
    result = {'status': 'started', 'optimizer_updates': 0, 'model_files_sha256': files,
              'protocol_sha256': run.sha(run.HERE / 'protocol.json'), 'rows': [],
              'runner_sha256':run.sha(run.HERE/'run.py'),
              'projection_receipt':projection_receipt,
              'projection_lifecycle':lifecycle,
              'diagnostic_dtype':dtype,
              'adapter_sha256':run.sha(Path(adapter or run.PACK/'adapter')/'adapter_model.safetensors'),
              'scientific_gain_demonstrated': False}
    result['actual_trainable_dtypes'] = sorted({str(p.dtype) for p in model.parameters() if p.requires_grad})
    result['trainable_parameters'] = sum(p.numel() for p in model.parameters() if p.requires_grad)
    for record,tokens in cases:
        model.train()
        tick = time.monotonic()
        batch = {k:torch.tensor([v],device='mps') for k,v in tokens.items()}
        loss = model(**batch).loss
        loss.backward()
        finite = [torch.isfinite(p.grad).all() for p in model.parameters()
                  if p.requires_grad and p.grad is not None]
        ok = bool(finite) and torch.stack(finite).all().item() and torch.isfinite(loss).item()
        torch.mps.synchronize()
        result['rows'].append({'id':record['id'], 'sequence_tokens':len(tokens['input_ids']),
                              'loss':float(loss.detach().cpu()), 'gradients_finite':bool(ok),
                              'seconds':time.monotonic()-tick})
        run.save(output/'gradient-probe-receipt.json',result)
        if not ok:
            raise ValueError('Diagnostic gradient/loss non-finite')
        model.zero_grad(set_to_none=True)
        del batch,loss
        run.release_idle_mps_cache()
    result.update(status='pass_without_optimizer_updates',seconds=time.monotonic()-started)
    if projection_receipt:
        result['projection_lifecycle'].append(run.projection_integrity(model, projection_receipt, 'probe_end'))
    run.save(output/'gradient-probe-receipt.json',result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--adapter',type=Path);p.add_argument('--dtype',choices=['bfloat16','float16'],default='bfloat16')
    p.add_argument('--all-rows',action='store_true')
    p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS);args=p.parse_args()
    if not args.worker:
        if args.output.exists():p.error('Use a fresh output directory')
        args.output.mkdir(parents=True)
        child=subprocess.Popen([sys.executable,__file__,*sys.argv[1:],'--worker'])
        try:code=child.wait(timeout=300)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            code=124
        if code:run.save(args.output/'interruption-receipt.json',{'status':'diagnostic_failed','exit_code':code,'optimizer_updates':0})
        return code
    with run.ResourceGuard(args.output):worker(args.snapshot.resolve(),args.output.resolve(),args.adapter,args.dtype,args.all_rows)
    return 0


if __name__=='__main__':raise SystemExit(main())
