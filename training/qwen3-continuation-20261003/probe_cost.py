"""Bounded CPU/MPS cost probe on an already inspected training example; no optimizer update."""
import argparse
import gc
import json
from pathlib import Path
import subprocess
import sys
import time
import run


def worker(snapshot, output):
    import torch
    import psutil
    from peft import PeftModel
    cfg = run.load(run.HERE / 'protocol.json')
    available = psutil.virtual_memory().available
    if available < 16 * 1024**3:
        raise ValueError('Probe requires at least 16 GiB available memory')
    model, tokenizer, files = run.runtime(snapshot)
    model = PeftModel.from_pretrained(model, str(run.PACK / 'adapter'), is_trainable=True)
    record = run.rows(run.HERE / 'data/train-records.jsonl')[0]
    result = {'status': 'probing_not_trained', 'model_files_sha256': files,
              'protocol_sha256': run.sha(run.HERE / 'protocol.json'),
              'adapter_sha256': cfg['initial_adapter_sha256'], 'runtime': run.inventory(),
              'available_memory_bytes': available, 'backends': {},
              'optimizer_updates': 0, 'data_row_id': record['id'],
              'scientific_gain_demonstrated': False}
    run.save(output / 'probe-receipt.json', result)
    devices = ['mps', 'cpu'] if torch.backends.mps.is_available() else ['cpu']
    for device in devices:
        metrics = {'device': device, 'dtype': 'bfloat16', 'status': 'started'}
        try:
            model.to(device)
            model.eval()
            model.config.use_cache = True
            encoded = tokenizer.apply_chat_template(record['messages'][:-1], tokenize=True,
                return_tensors='pt', return_dict=True, add_generation_prompt=True,
                enable_thinking=False).to(device)
            def sync():
                if device == 'mps':
                    torch.mps.synchronize()
            sync()
            tick = time.monotonic()
            with torch.inference_mode():
                generated = model.generate(**encoded, do_sample=False, max_new_tokens=16,
                    pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
            sync()
            new = generated[0, encoded['input_ids'].shape[-1]:]
            metrics.update(inference_seconds=time.monotonic() - tick,
                generated_tokens=len(new), token_ids=new.cpu().tolist(),
                response=tokenizer.decode(new, skip_special_tokens=True),
                scope='16-token cost/parity probe on training data; not an accuracy result')
            del encoded, generated, new
            model.train()
            model.config.use_cache = False
            model.enable_input_require_grads()
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
            tokenized = run.supervised_tokens(record, tokenizer)
            batch = {name: torch.tensor([values], device=device) for name, values in tokenized.items()}
            sync()
            tick = time.monotonic()
            loss = model(**batch).loss
            loss.backward()
            sync()
            metrics.update(forward_backward_seconds=time.monotonic() - tick,
                           loss=float(loss.detach().cpu()),
                           sequence_tokens=len(tokenized['input_ids']))
            if not torch.isfinite(loss):
                raise ValueError('Probe loss non-finite')
            model.zero_grad(set_to_none=True)
            model.gradient_checkpointing_disable()
            del batch, loss
            metrics['status'] = 'completed_without_optimizer_update'
            metrics['peak_rss_bytes'] = run.rss_bytes()
            if run.rss_bytes() > cfg['training']['max_rss_gib'] * 1024**3:
                raise ValueError('Probe memory ceiling exceeded')
        except Exception as exc:
            metrics.update(status='failed', error=type(exc).__name__ + ': ' + str(exc))
        result['backends'][device] = metrics
        run.save(output / 'probe-receipt.json', result)
        model.to('cpu')
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    completed = result['backends']
    result['status'] = 'cost_probe_completed_not_trained'
    if all(d in completed and 'token_ids' in completed[d] for d in ('mps', 'cpu')):
        result['probe_tokens_equal_cpu_mps'] = completed['mps']['token_ids'] == completed['cpu']['token_ids']
    run.save(output / 'probe-receipt.json', result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker:
        if args.output.exists():
            parser.error('Use a fresh output directory')
        args.output.mkdir(parents=True)
        child = subprocess.Popen([sys.executable, __file__, *sys.argv[1:], '--worker'])
        try:
            code = child.wait(timeout=600)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            code = 124
        if code:
            run.save(args.output / 'interruption-receipt.json',
                     {'status': 'probe_failed_or_interrupted', 'exit_code': code,
                      'optimizer_updates': 0, 'scientific_gain_demonstrated': False})
        return code
    worker(args.snapshot.resolve(), args.output.resolve())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
