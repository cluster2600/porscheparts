"""Frozen four-domain MLX continuation using existing native, bounded graders."""
import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys

from curriculum import calculate, cases

HERE = Path(__file__).resolve().parent
BASE_SHA = 'daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58'
PRIOR_SHA = 'a1014c6f71b46d879c09462c4a57d17d00df8f11b8178dd53bf6d5f2ac2f778a'
DOMAINS = ('python', 'openfoam', 'openusd', 'picogk')


def helpers(training):
    sys.path.insert(0, str(training / 'training/m64-qwen'))
    from dataset import digest
    from run import save, child, configure_tokenizer, exact_match
    import picogk
    spec = importlib.util.spec_from_file_location('usd_reviewed', training / 'training/m64-engineer/openusd.py')
    usd = importlib.util.module_from_spec(spec); spec.loader.exec_module(usd)
    return digest, save, child, configure_tokenizer, exact_match, picogk, usd


def choose(before, after):
    if [r['id'] for r in before] != [r['id'] for r in after]:
        raise ValueError('evaluation coverage differs')
    regressions = [b['id'] for b, a in zip(before, after) if b['passed'] and not a['passed']]
    summary = {d: {'before': sum(r['passed'] for r in before if r['domain'] == d and not r.get('retention')),
                   'after': sum(r['passed'] for r in after if r['domain'] == d and not r.get('retention')),
                   'total': sum(r['domain'] == d and not r.get('retention') for r in after)} for d in DOMAINS}
    gates = all(r['passed'] for r in after if r.get('task') == 'mesh_gate')
    eligible = not regressions and gates and all(v['after'] >= v['before'] and v['after'] >= math.ceil(0.85*v['total']) for v in summary.values()) and any(v['after'] > v['before'] for v in summary.values())
    return {'candidate_eligible_for_fresh_tests': eligible, 'regressions': regressions,
            'new_validation': summary, 'mesh_failure_gates_passed': gates}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['train', 'score'])
    for name in ('training-checkout', 'output', 'usd-python', 'sdk', 'dll'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--input', type=Path); p.add_argument('--responses', type=Path)
    a = p.parse_args()
    a.training_checkout = a.training_checkout.resolve(); a.output = a.output.absolute()
    digest, save, child, configure_tokenizer, exact_match, pico, usd = helpers(a.training_checkout)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1',
                      HF_HUB_DISABLE_TELEMETRY='1', DOTNET_CLI_TELEMETRY_OPTOUT='1', PXR_WORK_THREAD_LIMIT='1')
    if a.action == 'score':
        rows = json.loads(a.input.read_text())
        responses = {r['id']: r['response'] for r in json.loads(a.responses.read_text())}
        a.output.mkdir(exist_ok=False)
        def score(r):
            text = re.sub(r'^```(?:python|json|csharp|cs)?\s*([\s\S]*?)\s*```$', r'\1', responses[r['id']].strip())
            result = {'id': r['id'], 'domain': r['domain'], 'task': r.get('task'),
                      'retention': r.get('retention', False), 'passed': False, 'response_sha256': __import__('hashlib').sha256(text.encode()).hexdigest()}
            try:
                if r['domain'] == 'python':
                    # Parameter perturbations reject memorised literal answers.
                    checks = []
                    for factor in (1, 1.7, 0.6):
                        values = {k: v*factor if k != 'pi' else v for k, v in r['expected']['values'].items()}
                        checks.append(math.isclose(calculate(text, values), calculate('result = ' + r['expected']['expression'], values), rel_tol=1e-9, abs_tol=1e-12))
                    result['passed'] = all(checks)
                elif r['domain'] == 'openfoam':
                    result['passed'] = exact_match(text, r['expected'])
                elif r['domain'] == 'openusd':
                    stage = usd.author(text)
                    result['native'] = usd.validate(stage, a.output/r['id'])
                    result['passed'] = usd.snapshot(stage) == usd.snapshot(usd.author(r['messages'][-1]['content']))
                else:
                    _, beams = pico.parse(text)
                    semantics = pico.signature(beams) == pico.signature(r['expected'])
                    result.update(pico.witness(text, a.output/r['id'], a.sdk, a.dll))
                    result['passed'] = semantics and result['compiled'] and result['native_passed']
            except Exception as e:
                result['error'] = type(e).__name__ + ': ' + str(e)
            return result
        # USD stays serial: the existing native evaluator observed a TBB cleanup hang.
        scored = [score(r) for r in rows if r['domain'] != 'picogk']
        with ThreadPoolExecutor(max_workers=4) as pool:
            scored += list(pool.map(score, [r for r in rows if r['domain'] == 'picogk']))
        by_id = {r['id']: r for r in scored}
        save(a.output/'scores.json', [by_id[r['id']] for r in rows]); return

    if shutil.disk_usage(a.output.parent).free < 2*1024**3:
        raise ValueError('require existing 2 GiB working reserve')
    lock = (a.training_checkout/'work/m64-qwen/train.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    import importlib.metadata
    if importlib.metadata.version('mlx-lm') != '0.31.3':
        raise ValueError('use pinned MLX runtime')
    work = a.training_checkout/'work/m64-qwen'
    model = work/'model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
    prior = work/'coding-003/checkpoint-600'
    if digest(model/'model.safetensors') != BASE_SHA or digest(prior/'adapters.safetensors') != PRIOR_SHA:
        raise ValueError('base or selected adapter changed')
    native = {a.dll: '710c4e0428efbe9c1cd1db1663247b45604f96d167a6726782ab8ddca350565a',
              a.dll.parent/'picogk.26.2.dylib': '5c1cd3fc12766a85bc5c1441a95f065fb274338d1333c3ae2d3396b59d0e18e7'}
    if any(digest(f) != expected for f, expected in native.items()):
        raise ValueError('native PicoGK runtime differs')
    subprocess.run([str(a.usd_python), '-c', 'from pxr import Usd; assert Usd.GetVersion() == (0,25,5)'], check=True)
    a.output.mkdir(exist_ok=False)
    def phase(name):
        save(a.output/'status.json', {'phase': name}); print(name, flush=True)
    phase('prepare')
    new = cases(usd, pico)
    previous = work/'coding-006'
    previous_manifest = json.loads((previous/'manifest.json').read_text())
    for name in ('usd-cases.jsonl', 'picogk-cases.json'):
        if digest(previous/name) != previous_manifest['files_sha256'][name]:
            raise ValueError('previous frozen corpus changed')
    old_usd = [json.loads(x) for x in (previous/'usd-cases.jsonl').read_text().splitlines()]
    old_pico = json.loads((previous/'picogk-cases.json').read_text())
    replay = []
    rng = random.Random(42)
    for domain, rows in [('openusd', old_usd), ('picogk', old_pico)]:
        replay += [{**r, 'domain': domain, 'retention': True} for r in rows if r['split'] == 'valid']
        replay += [{**r, 'domain': domain, 'retention': True} for r in rng.sample([r for r in rows if r['split'] == 'train'], 96)]
    all_rows = new + replay
    save(a.output/'cases.json', all_rows)
    data = a.output/'data'; data.mkdir()
    for split in ('train', 'valid', 'test'):
        (data/(split+'.jsonl')).write_text(''.join(json.dumps({'messages': r['messages']})+'\n' for r in all_rows if r['split'] == split))
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    network, tokenizer = load(str(model), tokenizer_config={'trust_remote_code': False})
    maximum = max(len(tokenizer.apply_chat_template(r['messages'], tokenize=True)) for r in all_rows)
    if maximum > 1024: raise ValueError('do not truncate sequences')
    del network, tokenizer; mx.clear_cache()
    sources = [HERE/'run.py', HERE/'curriculum.py', HERE/'sources.json',
               a.training_checkout/'training/m64-qwen/run.py', a.training_checkout/'training/m64-qwen/dataset.py',
               a.training_checkout/'training/m64-qwen/picogk.py', a.training_checkout/'training/m64-engineer/openusd.py']
    frozen = {str(f): digest(f) for f in [*sources, a.output/'cases.json', *sorted(data.glob('*.jsonl'))]}
    manifest = {'registered_at_utc': datetime.now(timezone.utc).isoformat(), 'files_sha256': frozen,
                'native_sha256': {str(f): expected for f, expected in native.items()},
                'sdk_version': subprocess.check_output([str(a.sdk), '--version'], text=True).strip(),
                'training_checkout_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.training_checkout, text=True).strip(),
                'base_sha256': BASE_SHA, 'warm_start_sha256': PRIOR_SHA, 'maximum_sequence_tokens': maximum,
                'counts': {s: {d: sum(r['split'] == s and r['domain'] == d for r in all_rows) for d in DOMAINS} for s in ('train', 'valid', 'test')},
                'iterations': 480, 'learning_rate': 0.00005, 'num_layers': 16, 'rank': 8, 'scale': 20, 'seed': 42,
                'selection': 'No per-case regression on new or old validation; >=85% per new domain; at least one gain; every mesh-failure gate passes. Fresh tests open only after eligibility.',
                'limitations': 'Shared task recipes and family labels; no independent task-family or real engineering generalisation claim. OpenFOAM scores are control/mesh-gate contracts; separate native witnesses are required.',
                'default_adapter_replaced': False, 'manufacturing_authorized': False}
    save(a.output/'manifest.json', manifest)
    common = [str(Path(__file__).resolve()), 'score', '--training-checkout', str(a.training_checkout),
              '--usd-python', str(a.usd_python), '--sdk', str(a.sdk), '--dll', str(a.dll)]
    def grade(label, rows, responses):
        input_path = a.output/(label+'-cases.json'); response_path = a.output/(label+'-responses.json')
        save(input_path, rows); save(response_path, responses)
        child([str(a.usd_python), *common, '--input', str(input_path), '--responses', str(response_path),
               '--output', str(a.output/label)], a.output/(label+'-score.log'), timeout=1800)
        return json.loads((a.output/label/'scores.json').read_text())
    phase('reference_checks')
    # Check every authored Python/USD answer, and every held-out PicoGK answer.
    # ponytail: sample 24 training PicoGK native witnesses; remaining training literals are parsed.
    for r in new:
        if r['domain'] == 'picogk' and pico.signature(pico.parse(r['messages'][-1]['content'])[1]) != pico.signature(r['expected']):
            raise ValueError('reference graph differs')
    references = [r for r in new if r['domain'] != 'picogk' or r['split'] != 'train' or new.index(r)//4 < 24]
    ref = grade('reference-checks', references, [{'id': r['id'], 'response': r['messages'][-1]['content']} for r in references])
    if not all(r['passed'] for r in ref): raise ValueError('reference checker failed')
    def evaluate(label, adapter, split):
        phase(label)
        network, tokenizer = load(str(model), adapter_path=str(adapter), tokenizer_config={'trust_remote_code': False})
        configure_tokenizer(tokenizer); mx.random.seed(42)
        rows = [r for r in all_rows if r['split'] == split]
        responses = []
        for r in rows:
            prompt = tokenizer.apply_chat_template(r['messages'][:2], tokenize=False, add_generation_prompt=True)
            text = ''.join(x.text for x in stream_generate(network, tokenizer, prompt=prompt, max_tokens=1024, sampler=make_sampler(temp=0)))
            responses.append({'id': r['id'], 'response': text})
        del network, tokenizer; mx.clear_cache()
        return grade(label, rows, responses)
    before = evaluate('validation-before', prior, 'valid')
    phase('training')
    command = [sys.executable, '-m', 'mlx_lm', 'lora', '--model', str(model), '--data', str(data),
               '--train', '--iters', '480', '--batch-size', '1', '--num-layers', '16', '--learning-rate', '0.00005',
               '--max-seq-length', '1024', '--mask-prompt', '--seed', '42', '--steps-per-report', '20',
               '--steps-per-eval', '480', '--val-batches', '-1', '--save-every', '480',
               '--resume-adapter-file', str(prior/'adapters.safetensors'), '--adapter-path', str(a.output/'adapter')]
    save(a.output/'training-command.json', command)
    child(command, a.output/'training.log', timeout=3600)
    after = evaluate('validation-after', a.output/'adapter', 'valid')
    result = choose(before, after)
    result.update(candidate_sha256=digest(a.output/'adapter/adapters.safetensors'),
                  fresh_tests_opened=False, default_adapter_replaced=False, manufacturing_authorized=False)
    if result['candidate_eligible_for_fresh_tests']:
        test_before = evaluate('test-before', prior, 'test')
        test_after = evaluate('test-after', a.output/'adapter', 'test')
        result.update(fresh_tests_opened=True, fresh_test_selection=choose(test_before, test_after))
    for name, expected in frozen.items():
        if digest(Path(name)) != expected: raise ValueError('frozen input changed')
    if digest(prior/'adapters.safetensors') != PRIOR_SHA: raise ValueError('selected adapter changed')
    save(a.output/'results.json', result)
    phase('complete_candidate_only' if result['candidate_eligible_for_fresh_tests'] else 'complete_rejected')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__': main()
