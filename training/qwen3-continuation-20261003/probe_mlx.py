"""Bounded native MLX feasibility only; original Qwen3 weights, zero updates."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time
import run


def worker(args):
    import mlx.core as mx
    import mlx.nn as nn
    import numpy as np
    from mlx.utils import tree_flatten, tree_unflatten
    from mlx_lm import load
    from mlx_lm.tuner.utils import linear_to_lora_layers
    from mlx_lm.tuner.trainer import grad_checkpoint
    mx.set_cache_limit(512 * 1024**2)
    mx.set_memory_limit(20 * 1024**3)
    mx.random.seed(42)
    files = run.verify_snapshot(args.snapshot)
    started = time.monotonic()
    receipt = {'status': 'loading', 'optimizer_updates': 0,
        'scientific_gain_demonstrated': False, 'reserved_opened': False,
        'model_files_sha256': files, 'runner_sha256': run.sha(Path(__file__)),
        'initial_adapter_sha256': run.sha(run.PACK/'adapter/adapter_model.safetensors'),
        'libraries': {n: importlib.metadata.version(n) for n in ('mlx','mlx-lm','transformers','tokenizers')},
        'base_conversion': 'none; exact local HF safetensors loaded directly; no quantization',
        'precision_policy': 'Native MLX BF16 tied base with FP32 LoRA; official delta cast before addition differs from PEFT; no cross-runtime parity claimed',
        'rows': []}
    run.save(args.output/'mlx-probe-receipt.json', receipt)
    model, tokenizer = load(str(args.snapshot), tokenizer_config={'trust_remote_code': False})
    template = hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()
    if template != run.load(run.OLD/'compact-qwen3-v5/model-profile.json')['chat_template_sha256']:
        raise ValueError('Tokenizer template mismatch')
    parameters = tree_flatten(model.parameters())
    if not all(v.dtype == mx.bfloat16 for _, v in parameters):
        raise ValueError('Native base must preserve BF16 tensors')
    receipt['base_parameters'] = sum(v.size for _,v in parameters)
    receipt['base_tensor_count'] = len(parameters)
    receipt['tied_embeddings'] = model.args.tie_word_embeddings
    model.freeze()
    linear_to_lora_layers(model, 36, {'rank': 8, 'scale': 2.0, 'dropout': .05,
                                    'keys': ['self_attn.q_proj','self_attn.v_proj']})
    original = mx.load(str(run.PACK/'adapter/adapter_model.safetensors'))
    converted = {}
    proof = []
    for key,value in original.items():
        name = key.removeprefix('base_model.model.')
        name = name.replace('.lora_A.weight','.lora_a').replace('.lora_B.weight','.lora_b')
        target = value.T
        if not np.array_equal(np.asarray(target).T, np.asarray(value)):
            raise ValueError('LoRA transpose failed')
        converted[name] = target
        proof.append({'original_name': key, 'mlx_name': name, 'original_shape': list(value.shape),
                      'mlx_shape': list(target.shape), 'exact_transpose': True, 'dtype':str(value.dtype)})
    trainable = dict(tree_flatten(model.trainable_parameters()))
    if set(trainable) != set(converted) or len(converted) != 144:
        raise ValueError('Trainable conversion key mismatch')
    model.update(tree_unflatten(list(converted.items())))
    receipt.update(adapter_conversion=proof, lora_scale=2.0, lora_dropout=.05,
                   trainable_parameters=sum(v.size for v in converted.values()),
                   trainable_tensor_count=len(converted), actual_trainable_dtypes=sorted({str(v.dtype) for v in converted.values()}))
    mx.eval(model.parameters())
    grad_checkpoint(model.layers[0])

    def loss_fn(model, tokens, labels):
        logits = model(tokens).astype(mx.float32)
        mask = labels >= 0
        targets = mx.where(mask, labels, 0)
        loss = nn.losses.cross_entropy(logits, targets, reduction='none')
        return mx.sum(loss * mask) / mx.sum(mask)

    value_and_grad = nn.value_and_grad(model, loss_fn)
    records = run.rows(run.HERE/'data/train-records.jsonl')
    cases = [(r,run.supervised_tokens(r,tokenizer)) for r in records]
    if not args.all_rows:
        cases = [next(x for x in cases if x[0]['id']=='qualifier-sebm-heat-treatment-en'),
                 max(cases, key=lambda x:len(x[1]['input_ids']))]
    for record,tokens in cases:
        model.train()
        tick = time.monotonic()
        x=mx.array([tokens['input_ids'][:-1]],dtype=mx.int32)
        y=mx.array([tokens['labels'][1:]],dtype=mx.int32)
        value,grad=value_and_grad(model,x,y)
        mx.eval(value,grad)
        flat = dict(tree_flatten(grad))
        if set(flat) != set(converted):
            raise ValueError('Absent trainable gradients')
        checks = mx.stack([mx.all(mx.isfinite(g)) for g in flat.values()])
        mx.eval(checks)
        finite = bool(mx.all(checks).item()) and bool(mx.isfinite(value).item())
        receipt['rows'].append({'id':record['id'],'sequence_tokens':len(tokens['input_ids']),
            'loss':value.item(),'all_144_gradients_finite':finite,'seconds':time.monotonic()-tick,
            'active_memory_bytes':mx.get_active_memory(),'cache_memory_bytes':mx.get_cache_memory(),
            'peak_mlx_memory_bytes':mx.get_peak_memory()})
        receipt['status']='probing_without_optimizer_updates'
        run.save(args.output/'mlx-probe-receipt.json',receipt)
        if not finite:raise ValueError('MLX loss/gradient nonfinite')
        del value,grad,flat,checks,x,y
        mx.clear_cache()
    receipt.update(status='pass_without_optimizer_updates',seconds=time.monotonic()-started)
    run.save(args.output/'mlx-probe-receipt.json',receipt)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mlx-python',type=Path,required=True)
    p.add_argument('--all-rows',action='store_true')
    p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.worker:
        worker(args);return 0
    import psutil
    if args.output.exists():p.error('Use a new output directory')
    if psutil.virtual_memory().available < 16*1024**3:p.error('Available memory below16GiB')
    args.output.mkdir(parents=True)
    swap_start=psutil.swap_memory().used
    log=args.output/'worker.log';started=time.monotonic();peak=0;reason=None;last={};peak_cpu=0
    with log.open('w') as stream:
        child=subprocess.Popen([str(args.mlx_python),__file__,*sys.argv[1:],'--worker'],stdout=stream,stderr=stream)
        proc=psutil.Process(child.pid)
        proc.cpu_percent()
        while child.poll() is None:
            time.sleep(.5)
            try:current=proc.memory_info().rss
            except psutil.NoSuchProcess:continue
            peak=max(peak,current)
            available=psutil.virtual_memory().available;swap=psutil.swap_memory().used
            peak_cpu=max(peak_cpu,proc.cpu_percent())
            last={'worker_rss_bytes':current,'system_available_bytes':available,'system_swap_growth_bytes':swap-swap_start,
                  'elapsed_seconds':time.monotonic()-started}
            run.save(args.output/'resource-monitor.json',last)
            if current>24*1024**3 or available<16*1024**3 or swap-swap_start>256*1024**2 or time.monotonic()-started>300:
                reason=('worker_rss' if current>24*1024**3 else 'minimum_system_availability' if available<16*1024**3
                        else 'swap_growth' if swap-swap_start>256*1024**2 else 'deadline')
                child.terminate()
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=10)
                break
    code=child.wait()
    gpu_error='command buffer exited with error status' in log.read_text().lower()
    run.save(args.output/'supervisor-receipt.json',{'status':'completed' if code==0 and not gpu_error else 'failed',
        'exit_code':code,'gpu_error_observed':gpu_error,'resource_stop':reason,'peak_worker_rss_bytes':peak,
        'last_resource_sample':last,'peak_worker_cpu_percent':peak_cpu,
        'seconds':time.monotonic()-started,'optimizer_updates':0,'log_sha256':run.sha(log)})
    return code if code else int(gpu_error)


if __name__=='__main__':raise SystemExit(main())
