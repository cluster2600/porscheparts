"""Retain the failed first trial; add joint interface states and fresh families."""
import argparse
import itertools
import json
import os
from pathlib import Path
import shutil
import sys

from interfaces import HERE, SYSTEM, assess
from train_interfaces import BASE_SHA, PRIOR_SHA, cases as original_cases

FAMILIES = {'train': ('air_duct', 'seat_bracket', 'oil-port', 'fan_mount', 'gear-case', 'sensor_housing'),
            'valid': ('cold_plenum', 'filter-bracket'),
            'test': ('breather_casing', 'pump-support', 'timing_cover')}
WARM_SHA = 'ba6f1ad63bc0bc14a3bfe822025c1481d1b9ba3e67c7a508f9b35c750e24af51'


def cases():
    old = original_cases()
    rows = [r for r in old if r['split'] in ('train', 'valid')]
    for split, families in FAMILIES.items():
        for family in families:
            for number, states in enumerate(itertools.product(('ready', 'absent', 'unknown'), repeat=3)):
                requirements, observations = {}, {}
                for role, count, state in zip(('central', 'left', 'right'), (4, 1, 1), states):
                    name = family + '_' + role
                    requirements[name] = {'attachment_sites': count,
                                          'reference': 'unknown' if state == 'unknown' else 'measured'}
                    if state != 'absent':
                        observations[name] = {'attachment_sites': count,
                            'inspection': 'not_checked' if state == 'unknown' else 'matched_reference'}
                expected = assess(requirements, observations)
                prompt = ('Audit the synthetic ' + family + '; inspect every role independently. ' +
                          'No material certificate or release evidence.\n' +
                          json.dumps({'requirements': requirements, 'observations': observations}, sort_keys=True))
                rows.append({'id': f'v2-{split}-{family}-{number}', 'split': split, 'family': family,
                    'states': states, 'requirements': requirements, 'observations': observations,
                    'expected': expected, 'messages': [{'role': 'system', 'content': SYSTEM},
                        {'role': 'user', 'content': prompt},
                        {'role': 'assistant', 'content': json.dumps(expected, sort_keys=True)}]})
    # Previously opened tests are regressions, never new tests or training rows.
    rows += [{**r, 'split': 'regression'} for r in old if r['split'] in ('test', 'incident')]
    for row in rows:
        row['task'] = 'attachments'
    # Remove documentary prose from the incident's model input, retaining exactly the same facts and oracle.
    incident = rows[-1]
    contract = json.loads((HERE / 'interface-contract.json').read_text())
    incident['messages'][1]['content'] = 'Audit 993 115 021 53. Watertight mesh, no central bracket holes.\n' + json.dumps({
        'requirements': {r: {k: v[k] for k in ('attachment_sites', 'reference')} for r, v in contract['requirements'].items()},
        'observations': {r: {k: v[k] for k in ('attachment_sites', 'inspection')} for r, v in contract['observations'].items()}}, sort_keys=True)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-checkout', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--first-run', required=True, type=Path)
    args = parser.parse_args()
    training, output, first = (p.resolve() for p in (args.training_checkout, args.output, args.first_run))
    sys.path.insert(0, str(training / 'training/m64-qwen'))
    from dataset import digest
    from run import child, save, evaluate
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1', HF_HUB_DISABLE_TELEMETRY='1')
    if shutil.disk_usage(output.parent).free < 2 * 1024**3:
        raise ValueError('Need the existing 2 GiB working reserve')
    model = training / 'work/m64-qwen/model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
    prior = training / 'work/m64-qwen/coding-003/checkpoint-600'
    warm = first / 'adapter'
    if digest(model / 'model.safetensors') != BASE_SHA or digest(prior / 'adapters.safetensors') != PRIOR_SHA or digest(warm / 'adapters.safetensors') != WARM_SHA:
        raise ValueError('Pinned base, selected adapter or first candidate changed')
    import importlib.metadata
    if importlib.metadata.version('mlx-lm') != '0.31.3':
        raise ValueError('Use the pinned runtime')
    rows = cases()
    if len({r['id'] for r in rows}) != len(rows) or len({r['messages'][1]['content'] for r in rows}) != len(rows):
        raise ValueError('Duplicate case or prompt')
    output.mkdir(exist_ok=False)
    data = output / 'data'; data.mkdir()
    save(output / 'cases.json', rows)
    for split in ('train', 'valid', 'test'):
        (data / (split + '.jsonl')).write_text(''.join(json.dumps({'messages': r['messages']}) + '\n' for r in rows if r['split'] == split))
    import mlx.core as mx
    from mlx_lm import load
    network, tokenizer = load(str(model), tokenizer_config={'trust_remote_code': False})
    maximum = max(len(tokenizer.apply_chat_template(r['messages'], tokenize=True)) for r in rows)
    if maximum > 512:
        raise ValueError('A sequence exceeds the reused evaluator limit; do not truncate it')
    del network, tokenizer
    mx.clear_cache()
    sources = [Path(__file__).resolve(), HERE / 'train_interfaces.py', HERE / 'interfaces.py', HERE / 'interface-contract.json',
               training / 'training/m64-qwen/run.py', training / 'training/m64-qwen/dataset.py']
    manifest = {'counts': {s: sum(r['split'] == s for r in rows) for s in ('train', 'valid', 'test', 'regression')},
        'source_sha256': {str(p): digest(p) for p in sources},
        'data_sha256': {str(p.relative_to(output)): digest(p) for p in [output / 'cases.json', *sorted(data.glob('*.jsonl'))]},
        'base_sha256': BASE_SHA, 'coding_adapter_sha256': PRIOR_SHA, 'warm_start_sha256': WARM_SHA,
        'maximum_sequence_tokens': maximum, 'iterations': 360, 'learning_rate': 0.0001, 'num_layers': 4,
        'rank': 8, 'scale': 20, 'batch_size': 1, 'seed': 42,
        'selection': 'All 70 validation cases must pass before fresh tests open; then all tests and regressions must pass.',
        'limitation': 'Shared templates/rules, family-disjoint fresh tests; not general engineering qualification.',
        'provenance': 'Owner-authorized synthetic fixtures; original tests retained as regressions, never added to training.'}
    save(output / 'manifest.json', manifest)

    def score(label, adapter, splits):
        save(output / 'status.json', {'phase': label})
        folder = output / label; (folder / 'data').mkdir(parents=True)
        # The reused evaluator calls its input partition test; the frozen IDs and actual splits stay in cases.json.
        save(folder / 'data/cases.json', [{**r, 'split': 'test'} for r in rows if r['split'] in splits])
        evaluate(folder, model, adapter)
        mx.clear_cache()
        return json.loads((folder / 'adapter-evaluation.json').read_text())

    before = score('validation-before', warm, {'valid'})
    save(output / 'status.json', {'phase': 'training'})
    command = [sys.executable, '-m', 'mlx_lm', 'lora', '--model', str(model), '--data', str(data), '--train',
        '--iters', '360', '--batch-size', '1', '--num-layers', '4', '--learning-rate', '0.0001', '--max-seq-length', '512',
        '--mask-prompt', '--seed', '42', '--steps-per-report', '30', '--steps-per-eval', '360', '--val-batches', '-1',
        '--save-every', '360', '--resume-adapter-file', str(warm / 'adapters.safetensors'), '--adapter-path', str(output / 'adapter')]
    save(output / 'training-command.json', command)
    child(command, output / 'training.log', timeout=1800)
    after = score('validation-after', output / 'adapter', {'valid'})
    selected = after['passed'] == after['total'] == 70
    result = {'validation_before': before['passed'], 'validation_after': after['passed'], 'validation_total': after['total'],
        'candidate_selected_for_attachment_review': selected, 'coding_adapter_replaced': False, 'manufacturing_authorized': False,
        'candidate_sha256': digest(output / 'adapter/adapters.safetensors')}
    if selected:
        test = score('test-after', output / 'adapter', {'test', 'regression'})
        result.update(test_after=test['passed'], test_total=test['total'],
            fresh_test_passed=sum(r['passed'] for r in test['cases'] if r['id'].startswith('v2-test-')),
            regression_passed=sum(r['passed'] for r in test['cases'] if not r['id'].startswith('v2-test-')),
            incident_passed=test['cases'][-1]['passed'])
        result['candidate_selected_for_attachment_review'] = test['passed'] == test['total'] == 106
    for name, expected in manifest['data_sha256'].items():
        if digest(output / name) != expected:
            raise ValueError('Frozen data changed')
    if digest(prior / 'adapters.safetensors') != PRIOR_SHA:
        raise ValueError('Selected coding adapter changed')
    save(output / 'results.json', result)
    save(output / 'status.json', {'phase': 'complete', **result})
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
