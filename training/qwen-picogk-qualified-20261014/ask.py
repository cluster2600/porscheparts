"""Use an explicitly pinned qualified profile and verify its request contract."""
import argparse
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path

import request_contract as contract
import qualify
pilot = contract.pilot


def profile(path, expected_sha256):
    if pilot.digest(path) != expected_sha256: raise ValueError('Profile differs from its trusted installation hash')
    config = pilot.load(path)
    if config.get('schema') != 'qwen.picogk.qualified-profile@1': raise ValueError('Profile schema')
    work = Path(config['work_root']).resolve()
    result_path = work/'run-001/results.json'
    if pilot.digest(result_path) != config['results_sha256'] or pilot.digest(work/'FROZEN.json') != config['frozen_sha256']:
        raise ValueError('Qualification results or frozen manifest changed')
    result = pilot.load(result_path)
    if (result.get('schema') != 'qwen.picogk.qualification-results@1' or not result.get('eligible') or not result.get('test_opened')
            or not result.get('frozen_inputs_verified') or result.get('historical_regressions')
            or result.get('old_plans_passed') != 48 or result.get('old_code_passed') != 16):
        raise ValueError('Profile lacks complete raw and retention qualification')
    for stage in ('development', 'final'):
        score = result.get(stage, {})
        if (score.get('total') != 60 or score.get('passed', 0) < 50 or score.get('refusal_passes') != 10 or score.get('regressions')
                or set(score.get('by_language', {})) != set(contract.LANGUAGES) or min(score['by_language'].values()) < 8):
            raise ValueError('Raw-model qualification gate failed')
    adapter = Path(result['adapter_path']).resolve()
    if not adapter.is_relative_to(work): raise ValueError('Selected adapter escaped its experiment')
    if pilot.digest(adapter/'adapters.safetensors') != config['adapter_sha256'] or result['adapter_sha256'] != config['adapter_sha256']:
        raise ValueError('Selected adapter changed')
    for name, expected in result['receipt_sha256'].items():
        receipt = (work/'run-001'/name).resolve()
        if not receipt.is_relative_to(work/'run-001') or pilot.digest(receipt) != expected:
            raise ValueError('Score receipt changed or escaped the run')
    frozen = qualify.verify(work)
    if result['protocol_sha256'] != frozen['protocol_sha256'] or pilot.digest(work/'protocol.json') != frozen['protocol_sha256']:
        raise ValueError('Registered protocol changed')
    if frozen['packages'] != config['packages'] or {name: importlib.metadata.version(name) for name in config['packages']} != config['packages']:
        raise ValueError('Qualified runtime packages changed')
    return work, Path(frozen['base']), adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--profile-sha256', required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir(): parser.error('Use a new output file in an existing directory')
    if args.request.stat().st_size > 65536: parser.error('Request exceeds 64 KiB')
    request = json.loads(args.request.read_text(), object_pairs_hook=pilot.unique)
    expected = contract.normalize(request)
    lock = (qualify.RUNTIME/'train.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    work, base, adapter = profile(args.profile, args.profile_sha256)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1', HF_HUB_DISABLE_TELEMETRY='1')
    receipt = dict(profile_sha256=args.profile_sha256, adapter_sha256=pilot.digest(adapter/'adapters.safetensors'),
                   request_sha256=pilot.digest(args.request), geometry_executed=False, manufacturing_qualified=False)
    if expected['recipe'] == 'needs_measurement':
        receipt.update(plan=expected, model_called=False, semantic_intent_verified=True)
    else:
        import mlx.core as mx
        from mlx_lm import load, stream_generate
        from mlx_lm.sample_utils import make_sampler
        mx.set_memory_limit(8*1024**3); mx.set_cache_limit(256*1024**2); mx.random.seed(9931312)
        model, tokenizer = load(str(base), adapter_path=str(adapter), tokenizer_config={'trust_remote_code': False})
        tokenizer.add_eos_token('<|im_end|>')
        prompt = tokenizer.apply_chat_template([{'role': 'system', 'content': pilot.SYSTEM}, {'role': 'user', 'content': contract.canonical(request)}], tokenize=False, add_generation_prompt=True)
        if len(tokenizer.encode(prompt)) > 1024: parser.error('Prompt exceeds the registered context')
        text, last = '', None
        for last in stream_generate(model, tokenizer, prompt=prompt, max_tokens=192, sampler=make_sampler(temp=0)): text += last.text
        try:
            receipt.update(plan=contract.accepted(text, last.finish_reason if last else None, request), model_called=True, semantic_intent_verified=True)
        except (ValueError, TypeError) as error:
            receipt.update(plan=None, model_called=True, semantic_intent_verified=False, error=str(error), raw_response=text)
    pilot.save(args.output, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    if not receipt['semantic_intent_verified']: raise SystemExit(2)


if __name__ == '__main__': main()
