#!/usr/bin/env python3
"""Train and evaluate one bounded local QLoRA pilot; never rent, publish or execute model code."""
from __future__ import annotations

import argparse
import fcntl
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

from dataset import ROOT, digest, dumps, write_dataset

HERE = Path(__file__).resolve().parent
WORK = ROOT / 'work' / 'm64-qwen'


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def configure_tokenizer(tokenizer):
    # The pinned conversion has model EOS 151643 but chat EOS 151645.
    # Stop at the actual chat boundary as well as the model end-of-text token.
    tokenizer.add_eos_token('<|im_end|>')


def exact_match(text, expected):
    """Strict JSON types matter: false must not accidentally compare equal to zero."""
    try:
        actual = json.loads(text, object_pairs_hook=unique_object)
        return dumps(actual) == dumps(expected)
    except (ValueError, TypeError):
        return False


def comparison(base, adapter, base_loss, adapter_loss):
    before = {r['id']: r for r in base['cases']}
    after = {r['id']: r for r in adapter['cases']}
    if len(before) != 20 or before.keys() != after.keys():
        raise ValueError('evaluation coverage differs')
    regressions = [key for key, row in before.items()
                   if row['task'] in ('material', 'rental') and row['content_match_ignoring_fence'] and not after[key]['content_match_ignoring_fence']]
    safety_failures = [key for key, row in after.items()
                       if row['task'] in ('material', 'rental') and not row['content_match_ignoring_fence']]
    content_regressions = [key for key, row in before.items()
                           if row['content_match_ignoring_fence'] and not after[key]['content_match_ignoring_fence']]
    base_passed = sum(row['passed'] for row in before.values())
    adapter_passed = sum(row['passed'] for row in after.values())
    accuracy_improved = adapter_passed > base_passed
    loss_ok = all(math.isfinite(v) for v in (base_loss, adapter_loss)) and adapter_loss <= base_loss
    latency_ok = adapter['mean_seconds'] <= 2 * base['mean_seconds']
    return {
        'decision': 'candidate_adapter' if accuracy_improved and not regressions and not safety_failures and not content_regressions and loss_ok and latency_ok else 'keep_base',
        'accuracy_improved': accuracy_improved, 'safety_regressions': regressions,
        'safety_failures': safety_failures, 'content_regressions': content_regressions,
        'base_content_passed': sum(r['content_match_ignoring_fence'] for r in before.values()),
        'adapter_content_passed': sum(r['content_match_ignoring_fence'] for r in after.values()),
        'loss_acceptable': loss_ok, 'latency_acceptable': latency_ok,
        'base_passed': base_passed, 'adapter_passed': adapter_passed, 'total': 20,
        'base_test_loss': base_loss, 'adapter_test_loss': adapter_loss,
        'manufacturing_authorized': False, 'rental_authorized': False,
    }


def evaluate(output, model, adapter=None):
    import mlx.core as mx
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler

    mx.random.seed(42)
    network, tokenizer = load(str(model), adapter_path=str(adapter) if adapter else None,
                              tokenizer_config={'trust_remote_code': False})
    configure_tokenizer(tokenizer)
    cases = json.loads((output / 'data' / 'cases.json').read_text())
    if any(len(tokenizer.apply_chat_template(row['messages'], tokenize=True)) > 512 for row in cases):
        raise ValueError('example exceeds the fixed training sequence length')
    results = []
    for row in cases:
        if row['split'] != 'test':
            continue
        prompt = tokenizer.apply_chat_template(row['messages'][:2], tokenize=False, add_generation_prompt=True)
        started = time.perf_counter()
        text = ''
        last = None
        for response in stream_generate(network, tokenizer, prompt=prompt, max_tokens=192,
                                        sampler=make_sampler(temp=0)):
            text += response.text
            last = response
        if last is None:
            raise RuntimeError('model produced no response')
        content = re.sub(r'^```(?:json)?\s*([\s\S]*?)\s*```$', r'\1', text.strip())
        results.append({
            'id': row['id'], 'task': row['task'], 'response': text,
            'passed': exact_match(text, row['expected']),
            'content_match_ignoring_fence': exact_match(content, row['expected']),
            'seconds': time.perf_counter() - started,
            'generation_tokens': last.generation_tokens,
            'generation_tps': last.generation_tps,
            'peak_memory_gb': last.peak_memory,
        })
        print(f"{row['id']}: {'passed' if results[-1]['passed'] else 'failed'}", flush=True)
    report = {
        'cases': results, 'passed': sum(r['passed'] for r in results), 'total': len(results),
        'content_matches_ignoring_fence': sum(r['content_match_ignoring_fence'] for r in results),
        'mean_seconds': sum(r['seconds'] for r in results) / len(results),
        'peak_memory_gb': max(r['peak_memory_gb'] for r in results),
        'decoding': {'temperature': 0, 'max_tokens': 192, 'seed': 42},
    }
    save(output / ('adapter-evaluation.json' if adapter else 'base-evaluation.json'), report)


def child(command, log, timeout=1800):
    with log.open('x') as handle:
        subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def test_loss(command, log):
    child(command, log)
    match = re.search(r'Test loss ([0-9.eE+-]+), Test ppl ([0-9.eE+-]+)', log.read_text())
    if not match:
        raise RuntimeError(f'missing finite test loss: {log.name}')
    value = float(match[1])
    if not math.isfinite(value):
        raise RuntimeError('non-finite test loss')
    return value


def train(output):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('this pilot requires Apple Silicon macOS')
    if shutil.disk_usage(ROOT).free < 3 * 1024**3:
        raise RuntimeError('need at least 3 GiB free for download and 2 GiB working reserve')
    import mlx.core as mx
    if not mx.metal.is_available():
        raise RuntimeError('Metal is unavailable')
    config = json.loads((HERE / 'model.json').read_text())
    if importlib.metadata.version('mlx-lm') != config['mlx_lm_version']:
        raise RuntimeError('mlx-lm differs from the pinned runtime')
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    phase = 'prepare'
    try:
        save(output / 'status.json', {'status': 'running', 'phase': phase})
        data_manifest = write_dataset(output / 'data')
        save(output / 'configuration.json', config)
        save(output / 'runtime.json', {
            'python': platform.python_version(), 'platform': platform.platform(),
            'device': mx.device_info()['device_name'],
            'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'source_hashes': {p.name: digest(p) for p in HERE.iterdir() if p.suffix in ('.py', '.json', '.lock')},
            'packages': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
        })
        phase = 'download'
        save(output / 'status.json', {'status': 'running', 'phase': phase})
        print('Downloading pinned public model without authentication.', flush=True)
        from huggingface_hub import snapshot_download, hf_hub_download
        model = Path(snapshot_download(
            config['repository'], revision=config['revision'], token=False,
            cache_dir=str(WORK / 'model-cache'),
            allow_patterns=['*.json', '*.safetensors', '*.txt', 'README.md'],
        ))
        if digest(model / 'model.safetensors') != config['weights_sha256']:
            raise RuntimeError('model weight hash mismatch')
        license_path = Path(hf_hub_download(
            config['upstream_repository'], 'LICENSE', revision=config['upstream_revision'],
            token=False, cache_dir=str(WORK / 'model-cache'),
        ))
        shutil.copyfile(license_path, output / 'MODEL-LICENSE.txt')
        save(output / 'model-files.json', {p.name: digest(p) for p in model.iterdir() if p.is_file()})
        if shutil.disk_usage(ROOT).free < 2 * 1024**3:
            raise RuntimeError('less than 2 GiB free after download')
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        base = [sys.executable, str(HERE / 'run.py'), '--evaluate', '--output', str(output), '--model', str(model)]
        common = [sys.executable, '-m', 'mlx_lm', 'lora', '--model', str(model),
                  '--data', str(output / 'data'), '--batch-size', '1', '--max-seq-length', '512',
                  '--seed', '42', '--mask-prompt']
        phase = 'base_evaluation'
        save(output / 'status.json', {'status': 'running', 'phase': phase})
        print('Evaluating base model on 20 frozen cases.', flush=True)
        child(base, output / 'base-evaluation.log')
        base_loss = test_loss(common + ['--test', '--test-batches', '-1', '--adapter-path', ''], output / 'base-loss.log')
        phase = 'training'
        save(output / 'status.json', {'status': 'running', 'phase': phase})
        adapter = output / 'adapter'
        training = config['training']
        command = common + ['--train', '--adapter-path', str(adapter), '--val-batches', '-1',
                            '--steps-per-report', '10', '--steps-per-eval', '30', '--save-every', '60']
        for key in ('iters', 'num_layers', 'learning_rate', 'fine_tune_type'):
            command.extend(['--' + key.replace('_', '-'), str(training[key])])
        print('Training 60 QLoRA iterations locally; see training.log.', flush=True)
        child(command, output / 'training.log')
        if not (adapter / 'adapters.safetensors').is_file():
            raise RuntimeError('training produced no adapter')
        phase = 'adapter_evaluation'
        save(output / 'status.json', {'status': 'running', 'phase': phase})
        print('Evaluating adapter against the same frozen cases.', flush=True)
        child(base + ['--adapter', str(adapter)], output / 'adapter-evaluation.log')
        adapter_loss = test_loss(common + ['--test', '--test-batches', '-1', '--adapter-path', str(adapter)], output / 'adapter-loss.log')
        for name, expected in data_manifest['data_hashes'].items():
            if digest(output / 'data' / name) != expected:
                raise RuntimeError('dataset changed during the run')
        result = comparison(json.loads((output / 'base-evaluation.json').read_text()),
                            json.loads((output / 'adapter-evaluation.json').read_text()), base_loss, adapter_loss)
        result['elapsed_seconds'] = time.time() - started
        result['adapter_sha256'] = digest(adapter / 'adapters.safetensors')
        save(output / 'comparison.json', result)
        save(output / 'status.json', {'status': 'completed', 'decision': result['decision']})
        print(json.dumps(result, indent=2), flush=True)
    except BaseException as exc:
        save(output / 'status.json', {'status': 'failed', 'phase': phase, 'error_type': type(exc).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--evaluate', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--model', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--adapter', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(WORK.resolve()) or output == WORK.resolve():
        parser.error('output must be a new run directory below work/m64-qwen')
    # No implicit hub credentials or reporting integrations in this local pilot.
    os.environ.update({'HF_HUB_DISABLE_IMPLICIT_TOKEN': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
                       'DO_NOT_TRACK': '1', 'WANDB_DISABLED': 'true', 'TOKENIZERS_PARALLELISM': 'false'})
    if args.evaluate:
        if args.model is None:
            parser.error('evaluation requires a local model')
        evaluate(output, args.model, args.adapter)
    else:
        WORK.mkdir(parents=True, exist_ok=True)
        # ponytail: one training job per Mac; revisit only for a measured concurrency need.
        with (WORK / 'train.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            train(output)


if __name__ == '__main__':
    main()
