"""Run one registered local research LoRA pilot; retain the existing adapters."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

from prepare import compact, digest, save, verify
from train import BASE, RUNTIME, gate, score

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING = Path(os.environ.get('QWEN_RESEARCH_ENGINEERING_ROOT', str(ROOT)))
PARENT = ENGINEERING / 'work/qwen-engineering-005/checkpoint-1200'
PRIVATE = ENGINEERING / 'work/qwen-engineering-002/helpers'
USD_PYTHON = Path(os.environ.get('QWEN_RESEARCH_USD_PYTHON', str(ENGINEERING / 'work/cad-recode-tools-venv/bin/python')))
PICO = Path(os.environ.get('QWEN_RESEARCH_PICOGK_ROOT', str(ENGINEERING / 'work/picogk-runtime')))
PARENT_SHA = '70142a4583f5c95a74b3a5dd6661d8243e85e7846dc7aba6e8b4ab3c6a3f29d4'
BASE_SHA = 'daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58'


def checked_score(cases, answers):
    if len(cases) != len(answers) or len({r['id'] for r in cases}) != len(cases):
        raise ValueError('Evaluation coverage differs or duplicate case IDs')
    return score(cases, answers)


def run(dataset, output):
    integrity = verify(dataset)
    if output.exists():
        raise ValueError('Use a new run directory; preserve interrupted runs')
    if shutil.disk_usage(output.parent).free < 3 * 1024**3:
        raise ValueError('Require 3 GiB working reserve')
    if importlib.metadata.version('mlx-lm') != '0.31.3':
        raise ValueError('Use the existing pinned MLX-LM 0.31.3 runtime')
    if digest(BASE / 'model.safetensors') != BASE_SHA or digest(PARENT / 'adapters.safetensors') != PARENT_SHA:
        raise ValueError('Base or parent adapter changed')
    lock = (RUNTIME / 'train.lock').open('a')
    # ponytail: one host-wide lock; per-device locks only if concurrent accelerators exist.
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1',
                      HF_HUB_DISABLE_TELEMETRY='1', DOTNET_CLI_TELEMETRY_OPTOUT='1', PXR_WORK_THREAD_LIMIT='1')
    subprocess.run([str(USD_PYTHON), '-c', 'from pxr import Usd; assert Usd.GetVersion() == (0,25,5)'], check=True)
    sdk = PICO / 'dotnet/dotnet'; dll = PICO / 'picogk-bin/PicoGK.dll'
    native = {dll: '710c4e0428efbe9c1cd1db1663247b45604f96d167a6726782ab8ddca350565a',
              dll.parent / 'picogk.26.2.dylib': '5c1cd3fc12766a85bc5c1441a95f065fb274338d1333c3ae2d3396b59d0e18e7'}
    if any(digest(p) != h for p, h in native.items()):
        raise ValueError('Native PicoGK runtime changed')
    old_cases = ENGINEERING / 'work/qwen-engineering-003/cases.json'
    development = json.loads(old_cases.read_text())
    rng = random.Random(1042)
    retention = []
    for domain in ('openusd', 'picogk'):
        pool = sorted((r for r in development if r['split'] == 'valid' and r['domain'] == domain), key=lambda r: r['id'])
        retention += sorted(rng.sample(pool, 8), key=lambda r: r['id'])
    output.mkdir()
    (output / 'data').mkdir()
    for split in ('train', 'valid'):
        shutil.copy2(dataset / 'data' / (split + '.jsonl'), output / 'data' / (split + '.jsonl'))
    valid = json.loads((dataset / 'evaluation/valid-cases.json').read_text())
    save(output / 'validation-cases.json', valid)
    save(output / 'retention-cases.json', retention)
    sources = [Path(__file__), Path(__file__).with_name('prepare.py'), Path(__file__).with_name('curriculum.py'),
               ROOT / 'training/qwen-porsche-corpus/train.py', ROOT / 'training/qwen-porsche-corpus/corpus.py',
               ROOT / 'training/qwen-engineering-20261002/run.py', ROOT / 'training/qwen-engineering-20261002/curriculum.py',
               PRIVATE / 'training/m64-qwen/run.py', PRIVATE / 'training/m64-qwen/dataset.py',
               PRIVATE / 'training/m64-qwen/picogk.py', PRIVATE / 'training/m64-engineer/openusd.py']
    frozen = {str(p): digest(p) for p in [*sources, old_cases, PARENT / 'adapters.safetensors', PARENT / 'adapter_config.json',
              BASE / 'model.safetensors', BASE / 'config.json',
              *(BASE / n for n in json.loads((dataset / 'manifest.json').read_text())['tokenizer_files']),
              dataset / 'FROZEN.json', dataset / 'evaluation/test-cases.json',
              output / 'validation-cases.json', output / 'retention-cases.json', *sorted((output / 'data').glob('*.jsonl'))]}
    for i, source in enumerate(sources):
        dest = output / 'tools' / str(i) / source.name
        dest.parent.mkdir(parents=True); shutil.copy2(source, dest)
    command = [sys.executable, '-m', 'mlx_lm', 'lora', '--model', str(BASE), '--data', str(output / 'data'),
               '--train', '--iters', '320', '--batch-size', '2', '--num-layers', '16', '--learning-rate', '0.000005',
               '--max-seq-length', '1024', '--mask-prompt', '--seed', '1042', '--steps-per-report', '20',
               '--steps-per-eval', '320', '--val-batches', '-1', '--save-every', '320',
               '--resume-adapter-file', str(PARENT / 'adapters.safetensors'), '--adapter-path', str(output / 'adapter')]
    protocol = {'registered_at_utc': datetime.now(timezone.utc).isoformat(), 'frozen': frozen,
                'native_sha256': {str(p): h for p, h in native.items()}, 'training_command': command,
                'dataset_integrity': integrity, 'dataset': str(dataset), 'base': str(BASE), 'parent': str(PARENT),
                'mlx_lm': importlib.metadata.version('mlx-lm'),
                'sdk_version': subprocess.check_output([str(sdk), '--version'], text=True).strip(),
                'registered_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'validation_counts': dict(Counter(r['kind'] for r in valid)), 'retention_counts': dict(Counter(r['domain'] for r in retention)),
                'selection': 'Fixed final step 320. Exact JSON >=95% per validation kind, no lost baseline pass; open the final 8 tests only if eligible. Retention separately reports >=95% per domain and no regression. No automatic promotion.',
                'generation': {'temperature': 0, 'seed': 1042, 'research_max_tokens': 256, 'retention_max_tokens': 1024},
                'limits': 'Small source-conditioned pilot with shared response recipes. Exact paraphrases can fail. No held-out fatigue category, semantic science benchmark, independent engineering-family or physical qualification. Sixteen previously used development cases are a retention smoke test, not a fresh coding benchmark.'}
    save(output / 'protocol.json', protocol)
    save(output / 'protocol.sha256.json', {'sha256': digest(output / 'protocol.json')})
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    def phase(label):
        save(output / 'status.json', {'phase': label}); print(label, flush=True)
    def infer(label, adapter, rows, maximum=256):
        phase(label)
        model, tokenizer = load(str(BASE), adapter_path=str(adapter), tokenizer_config={'trust_remote_code': False})
        tokenizer.add_eos_token('<|im_end|>'); mx.random.seed(1042)
        answers = []
        for row in rows:
            prompt = tokenizer.apply_chat_template(row['messages'][:2], tokenize=False, add_generation_prompt=True)
            answers.append(''.join(r.text for r in stream_generate(model, tokenizer, prompt=prompt, max_tokens=maximum, sampler=make_sampler(temp=0))))
            save(output / (label + '-answers.json'), answers)
            print(label, len(answers), '/', len(rows), flush=True)
        del model, tokenizer; mx.clear_cache()
        return answers
    def native_grade(label, answers):
        response = output / (label + '-responses.json')
        save(response, [{'id': r['id'], 'response': a} for r, a in zip(retention, answers)])
        if len(answers) != len(retention): raise ValueError('Incomplete retention responses')
        command = [str(USD_PYTHON), str(ROOT / 'training/qwen-engineering-20261002/run.py'), 'score',
                   '--training-checkout', str(PRIVATE), '--usd-python', str(USD_PYTHON), '--sdk', str(sdk), '--dll', str(dll),
                   '--input', str(output / 'retention-cases.json'), '--responses', str(response), '--output', str(output / label)]
        with (output / (label + '-native.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1800)
        rows = json.loads((output / label / 'scores.json').read_text())
        if [r['id'] for r in rows] != [r['id'] for r in retention]: raise ValueError('Native grader coverage differs')
        return [{'id': r['id'], 'kind': r['domain'], 'passed': r['passed']} for r in rows]
    phase('native-reference-checks')
    reference = native_grade('retention-reference', [r['messages'][-1]['content'] for r in retention])
    if not all(r['passed'] for r in reference): raise ValueError('Native reference checker failed')
    before = checked_score(valid, infer('validation-before', PARENT, valid))
    save(output / 'validation-before-scores.json', before)
    retained_before = native_grade('retention-before', infer('retention-before', PARENT, retention, 1024))
    phase('training'); save(output / 'training-command.json', command)
    with (output / 'training.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)
    after = checked_score(valid, infer('validation-after', output / 'adapter', valid))
    save(output / 'validation-after-scores.json', after)
    result = {'validation': gate(before, after), 'weights_updated': True, 'default_replaced': False,
              'qualified': False, 'test_opened': False, 'adapter_sha256': digest(output / 'adapter/adapters.safetensors')}
    save(output / 'results.json', result)
    if result['validation']['eligible']:
        tests = json.loads((dataset / 'evaluation/test-cases.json').read_text())
        b = checked_score(tests, infer('test-before', PARENT, tests))
        a = checked_score(tests, infer('test-after', output / 'adapter', tests))
        save(output / 'test-before-scores.json', b); save(output / 'test-after-scores.json', a)
        result.update(test_opened=True, test=gate(b, a))
    retained_after = native_grade('retention-after', infer('retention-after', output / 'adapter', retention, 1024))
    result['retention'] = gate(retained_before, retained_after)
    result['validation_before_passed'] = sum(r['passed'] for r in before)
    result['validation_after_passed'] = sum(r['passed'] for r in after)
    result['retention_before_passed'] = sum(r['passed'] for r in retained_before)
    result['retention_after_passed'] = sum(r['passed'] for r in retained_after)
    if any(digest(p) != h for p, h in {**frozen, **protocol['native_sha256']}.items()):
        raise ValueError('Registered input changed during the run')
    if digest(output / 'protocol.json') != json.loads((output / 'protocol.sha256.json').read_text())['sha256']:
        raise ValueError('Protocol changed during the run')
    result['dataset_integrity_after'] = verify(dataset)
    save(output / 'results.json', result); phase('complete_experimental')
    print(compact(result), flush=True)


def self_check():
    rows = [{'id': 'a', 'kind': 'evidence', 'expected': {'claims': [], 'missing_information': ['missing']}},
            {'id': 'b', 'kind': 'summary', 'expected': {'claims': [], 'missing_information': []}}]
    correct = [compact(r['expected']) for r in rows]
    before = checked_score(rows, correct)
    assert gate(before, before)['eligible']
    wrong = checked_score(rows, [correct[0], '{"claims":[{"text":"unsupported","record_id":"unknown"}],"missing_information":[]}'])
    assert gate(before, wrong)['regressions'] == ['b'] and not gate(before, wrong)['eligible']
    try: checked_score(rows, correct[:1])
    except ValueError: pass
    else: raise AssertionError('Incomplete answers accepted')
    print('run self-check passed')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=('self-check', 'run'))
    p.add_argument('--dataset', type=Path); p.add_argument('--output', type=Path); a = p.parse_args()
    if a.action == 'self-check': self_check()
    else:
        if not a.dataset or not a.output: p.error('--dataset and --output required')
        run(a.dataset.resolve(), a.output.resolve())
