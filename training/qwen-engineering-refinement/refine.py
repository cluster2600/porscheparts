"""Continue the measured candidate; private graders and unchanged held-out prompts."""
import argparse
import ast
import fcntl
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TRAIN = Path('/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993')
FIRST = ROOT/'work/qwen-engineering-001'
RUNTIME = TRAIN/'work/m64-qwen'
PICO = Path('/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK')
USD_PYTHON = Path('/Users/maxime/projects/3dprinting993/work/cad-recode-tools-venv/bin/python')
HERE = Path(__file__).resolve().parent
FORMULAS = (
    ('axial_stress', 'force / area', {'force': 1200, 'area': 0.0002}, 'Axial stress in Pa; force N, area m^2.'),
    ('bearing_stress', 'force / (thickness * diameter)', {'force': 1200, 'thickness': 0.008, 'diameter': 0.01}, 'Nominal bearing stress in Pa; force N, thickness/diameter m. This is not a joint-capacity check.'),
    ('solid_shaft_torsion', '16 * torque / (pi * diameter * diameter * diameter)', {'torque': 25, 'pi': math.pi, 'diameter': 0.04}, 'Maximum shear stress in Pa for a solid circular shaft under Saint-Venant elastic torsion. torque N m; diameter m.'),
    ('cantilever_deflection', 'force * length * length * length / (3 * modulus * inertia)', {'force': 50, 'length': 0.2, 'modulus': 70e9, 'inertia': 1e-8}, 'Free-end deflection in m of a prismatic Euler-Bernoulli cantilever with a transverse end load; small deflection. force N, length m, modulus Pa, inertia m^4.'),
    ('cantilever_root_moment', 'force * length', {'force': 50, 'length': 0.2}, 'Root bending moment in N m of a cantilever under a transverse end load. force N; length m.'),
    ('euler_buckling', 'pi * pi * modulus * inertia / (factor * length * factor * length)', {'pi': math.pi, 'modulus': 70e9, 'inertia': 1e-8, 'factor': 1.0, 'length': 0.2}, 'Euler critical load in N of an ideal slender elastic column. End factor is supplied, not inferred. modulus Pa, inertia m^4, length m. No imperfection or plasticity allowance.'),
    ('axial_extension', 'force * length / (modulus * area)', {'force': 1200, 'length': 0.2, 'modulus': 70e9, 'area': 0.0002}, 'Axial extension in m of a uniform linear-elastic bar. force N, length m, modulus Pa, area m^2.'),
    ('thermal_extension', 'alpha * length * temperature_change', {'alpha': 23e-6, 'length': 0.2, 'temperature_change': 80}, 'Unconstrained linear thermal extension in m. alpha 1/K, length m, temperature_change K. No thermal stress is implied.'),
    ('conduction_rate', 'conductivity * area * temperature_difference / length', {'conductivity': 170, 'area': 0.002, 'temperature_difference': 80, 'length': 0.01}, 'Steady one-dimensional heat rate in W through a uniform slab with constant conductivity. conductivity W/(m K), area m^2, temperature_difference K, length m.'),
    ('convection_rate', 'coefficient * area * temperature_difference', {'coefficient': 80, 'area': 0.002, 'temperature_difference': 80}, 'Heat rate in W from a supplied convection coefficient. coefficient W/(m^2 K), area m^2, temperature_difference K; coefficient is not predicted.'),
    ('goodman_inverse_factor', 'alternating / endurance + mean / ultimate', {'alternating': 40e6, 'endurance': 160e6, 'mean': 60e6, 'ultimate': 300e6}, 'Inverse safety factor for the ideal linear Goodman relation. Positive tensile mean stress and all strengths in Pa are supplied. No fatigue-life or material-qualification claim.'),
    ('empirical_bolt_preload', 'torque / (nut_factor * diameter)', {'torque': 15, 'nut_factor': 0.2, 'diameter': 0.008}, 'Estimated bolt preload in N from the empirical nut-factor equation. torque N m, diameter m, nut_factor supplied. Friction scatter and proof strength are not resolved.'),
)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def additions(usd, pico, variant_generator):
    rows = [r for r in usd.candidates(composition=True) if r['split'] == 'train']
    rows += [r for r in variant_generator.variant_selection_candidates() if r['split'] == 'train']
    rows = [{**r, 'domain': 'openusd', 'retention': False} for r in rows]
    rng = random.Random(260024)
    points = list(itertools.product(range(-24, 25, 6), repeat=3))
    for i in range(256):
        n = 2 + i % 3; xyz = [list(p) for p in rng.sample(points, n)]
        radii = [rng.choice([1, 1.5, 2, 2.5, 3]) for _ in range(n)]
        edges = rng.sample(list(itertools.combinations(range(n), 2)), rng.randint(1, n*(n-1)//2))
        for permutation in range(2):
            names = rng.sample(range(10, 90), n) if permutation else list(range(n))
            ordered = edges[:] if not permutation else edges[::-1]
            nodes = list(range(n)); rng.shuffle(nodes)
            graph = {'nodes': {str(names[k]): {'xyz_mm': xyz[k], 'radius_mm': radii[k]} for k in nodes},
                     'edges': [[names[a], names[b]] for a, b in ordered], 'rounded_caps': bool(i % 2)}
            beams = [xyz[a]+[radii[a]]+xyz[b]+[radii[b]]+[bool(i % 2)] for a, b in ordered]
            prompt = ('PicoGK contract: AddBeam takes endpoint radii, not diameters. Given this dependency graph, '
                      'emit one AddBeam statement per edge, preserving the radius attached to each node. '
                      f'Synthetic fixture invariant_train_{i}_{permutation}.\n'+json.dumps(graph))
            rows.append({'id': f'invariant-train-{i}-{permutation}', 'domain': 'picogk', 'split': 'train', 'expected': beams,
                         'messages': [{'role': 'system', 'content': pico.SYSTEM}, {'role': 'user', 'content': prompt},
                                      {'role': 'assistant', 'content': pico.code(beams)}]})
    for split, repeats, seed in [('train', 8, 260025), ('valid', 2, 260026), ('test', 2, 260027)]:
        rng = random.Random(seed)
        for i, (task, expression, supplied, description) in enumerate(FORMULAS):
            for j in range(repeats):
                values = {k: v*rng.uniform(0.7, 1.4) if k not in ('pi', 'factor') else v for k, v in supplied.items()}
                prompt = description+' All inputs are synthetic, supplied in the stated SI units. Inputs: '+json.dumps(values)+'. Return only result = <expression> using the supplied variable names; no numeric substitution.'
                rows.append({'id': f'mechanics-{split}-{task}-{j}', 'domain': 'python', 'split': split, 'task': task,
                             'expected': {'values': values, 'expression': expression},
                             'messages': [{'role': 'system', 'content': 'Return only requested Python arithmetic. Never infer material properties, engine loads or physical validation.'},
                                          {'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': 'result = '+expression}]})
    return rows


def qualified(before, after, choose):
    result = choose(before, after)
    result['per_domain'] = {d: {'passed': sum(r['passed'] for r in after if r['domain'] == d),
                              'total': sum(r['domain'] == d for r in after)} for d in ('python', 'openfoam', 'openusd', 'picogk')}
    result['near_perfect_bounded_validation'] = not result['regressions'] and result['mesh_failure_gates_passed'] and all(v['passed'] >= math.ceil(0.95*v['total']) for v in result['per_domain'].values())
    return result


def parameterized(answer, expected, calculate):
    source = re.sub(r'^```(?:python)?\s*([\s\S]*?)\s*```$', r'\1', answer.strip())
    names = {n.id for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Name) and n.id != 'result'}
    values = expected['values']
    if names != set(values): return False
    for name in values:
        if name == 'pi': continue
        for factor in (0.4, 1.9):
            changed = {**values, name: values[name]*factor}
            if not math.isclose(calculate(source, changed), calculate('result = '+expected['expression'], changed), rel_tol=1e-9, abs_tol=1e-12): return False
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    output = a.output.resolve(); output.mkdir(exist_ok=False)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1', HF_HUB_DISABLE_TELEMETRY='1', PXR_WORK_THREAD_LIMIT='1')
    lock = (RUNTIME/'train.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    private = output/'helpers'; shutil.copytree(FIRST/'frozen-helpers', private, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(TRAIN/'training/m64-engineer/openusd.py', output/'variant-generator.py')
    sys.path.insert(0, str(ROOT/'training/qwen-engineering-20261002'))
    old = module('registered_runner', ROOT/'training/qwen-engineering-20261002/run.py')
    digest, save, child, configure, exact, pico, usd = old.helpers(private)
    def phase(name): save(output/'status.json', {'phase': name}); print(name, flush=True)
    phase('prepare')
    previous_manifest = json.loads((FIRST/'manifest.json').read_text())
    assert all(digest(Path(f)) == h for f, h in previous_manifest['native_sha256'].items())
    subprocess.run([str(USD_PYTHON), '-c', 'from pxr import Usd; assert Usd.GetVersion() == (0,25,5)'], check=True)
    if shutil.disk_usage(output).free < 3*1024**3: raise ValueError('require 3 GiB working reserve')
    for f in private.rglob('*.py'):
        original = TRAIN/f.relative_to(private)
        if str(original) in previous_manifest['files_sha256']:
            assert digest(f) == previous_manifest['files_sha256'][str(original)]
    model = RUNTIME/'model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
    warm = FIRST/'adapter'; selected = RUNTIME/'coding-003/checkpoint-600'
    assert digest(model/'model.safetensors') == old.BASE_SHA and digest(selected/'adapters.safetensors') == old.PRIOR_SHA
    assert digest(warm/'adapters.safetensors') == 'eee6ac87e5f9b3f65a61238e5c54ab23cac419b31d94ccaaad056bb033dcdfd1'
    initial = json.loads((FIRST/'cases.json').read_text())
    assert digest(FIRST/'cases.json') == previous_manifest['files_sha256'][str(FIRST/'cases.json')]
    more = additions(usd, pico, module('paired_generator', output/'variant-generator.py'))
    old_usd = [json.loads(x) for x in (RUNTIME/'coding-006/usd-cases.jsonl').read_text().splitlines()]
    existing = {r['id'] for r in initial}
    rows = initial+more+[{**r, 'domain': 'openusd', 'retention': True} for r in old_usd if r['split'] == 'train' and r['id'] not in existing]
    assert len({r['id'] for r in rows}) == len(rows)
    save(output/'cases.json', rows); data = output/'data'; data.mkdir()
    for split in ('train', 'valid', 'test'):
        (data/(split+'.jsonl')).write_text(''.join(json.dumps({'messages': r['messages']})+'\n' for r in rows if r['split'] == split))
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    import importlib.metadata
    assert importlib.metadata.version('mlx-lm') == '0.31.3'
    network, tokenizer = load(str(model), tokenizer_config={'trust_remote_code': False})
    maximum = max(len(tokenizer.apply_chat_template(r['messages'], tokenize=True)) for r in rows)
    if maximum > 1024: raise ValueError('sequence would be truncated')
    del network, tokenizer; mx.clear_cache()
    frozen_files = [Path(__file__), ROOT/'training/qwen-engineering-20261002/run.py', ROOT/'training/qwen-engineering-20261002/curriculum.py',
                    output/'variant-generator.py', output/'cases.json', *private.rglob('*.py'), *data.glob('*.jsonl')]
    frozen = {str(f.resolve()): digest(f) for f in frozen_files}
    save(output/'manifest.json', {'files_sha256': frozen, 'maximum_sequence_tokens': maximum, 'seed': 42, 'iterations': 600, 'batch_size': 2,
         'learning_rate': 0.00002, 'num_layers': 16, 'warm_sha256': digest(warm/'adapters.safetensors'),
         'native_sha256': previous_manifest['native_sha256'], 'registered_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'counts': {s: {d: sum(r['split'] == s and r['domain'] == d for r in rows) for d in old.DOMAINS} for s in ('train', 'valid', 'test')},
         'selection': '>=95% in every combined domain; no previously passing retained-adapter case lost. Tests open only after eligibility.',
         'limitations': 'Shared task recipes; arithmetic mechanics only; no generic automotive qualification. No paid compute or manufacturing authorization.'})
    common = [str(ROOT/'training/qwen-engineering-20261002/run.py'), 'score', '--training-checkout', str(private), '--usd-python', str(USD_PYTHON),
              '--sdk', str(PICO/'dotnet/dotnet'), '--dll', str(PICO/'picogk-bin/PicoGK.dll')]
    def grade(label, subset, responses):
        inp = output/(label+'-cases.json'); resp = output/(label+'-responses.json')
        save(inp, subset); save(resp, responses)
        child([str(USD_PYTHON), *common, '--input', str(inp), '--responses', str(resp), '--output', str(output/label)], output/(label+'.log'), timeout=1800)
        scores = json.loads((output/label/'scores.json').read_text())
        answers = {r['id']: r['response'] for r in responses}
        by_id = {r['id']: r for r in subset}
        for result in scores:
            if result['domain'] == 'python' and result['passed']:
                try: result['passed'] = parameterized(answers[result['id']], by_id[result['id']]['expected'], old.calculate)
                except (ValueError, SyntaxError, ZeroDivisionError): result['passed'] = False
                result['independent_parameter_audit_passed'] = result['passed']
        save(output/label/'scores-with-parameter-audit.json', scores)
        return scores
    phase('reference_checks')
    # ponytail: native-witness 24 new training graphs; parse every remaining literal against its independent graph.
    for r in more:
        if r['domain'] == 'picogk': assert pico.signature(pico.parse(r['messages'][-1]['content'])[1]) == pico.signature(r['expected'])
    references = [r for r in more if r['domain'] != 'picogk' or int(r['id'].split('-')[2]) < 12]
    assert all(r['passed'] for r in grade('references', references, [{'id': r['id'], 'response': r['messages'][-1]['content']} for r in references]))
    def infer(label, adapter, subset):
        phase(label); network, tokenizer = load(str(model), adapter_path=str(adapter), tokenizer_config={'trust_remote_code': False})
        configure(tokenizer); mx.random.seed(42); responses = []
        for r in subset:
            prompt = tokenizer.apply_chat_template(r['messages'][:2], tokenize=False, add_generation_prompt=True)
            text = ''.join(x.text for x in stream_generate(network, tokenizer, prompt=prompt, max_tokens=1024, sampler=make_sampler(temp=0)))
            responses.append({'id': r['id'], 'response': text})
        del network, tokenizer; mx.clear_cache()
        return responses
    validation = [r for r in rows if r['split'] == 'valid']
    retained = {r['id']: r for r in json.loads((FIRST/'validation-before-frozen/scores.json').read_text())}
    mechanics = [r for r in validation if r['id'] not in retained]
    mechanics_before = grade('mechanics-before', mechanics, infer('mechanics-before-infer', selected, mechanics))
    retained.update({r['id']: r for r in mechanics_before}); before = [retained[r['id']] for r in validation]
    save(output/'validation-before.json', before)
    phase('training')
    command = [sys.executable, '-m', 'mlx_lm', 'lora', '--model', str(model), '--data', str(data), '--train', '--iters', '600', '--batch-size', '2',
        '--num-layers', '16', '--learning-rate', '0.00002', '--max-seq-length', '1024', '--mask-prompt', '--seed', '42', '--steps-per-report', '20',
        '--steps-per-eval', '600', '--val-batches', '-1', '--save-every', '200', '--resume-adapter-file', str(warm/'adapters.safetensors'), '--adapter-path', str(output/'adapter')]
    save(output/'training-command.json', command); child(command, output/'training.log', timeout=7200)
    screen = [r for r in validation if (r['domain'] == 'picogk' and not r.get('retention')) or r['id'] in ('usd-valid-004', 'usd2-valid-017')]
    trials = {}; chosen = None
    for step in (200, 400, 600):
        adapter = output/f'checkpoint-{step}'; adapter.mkdir()
        shutil.copy2(output/'adapter'/f'{step:07d}_adapters.safetensors', adapter/'adapters.safetensors')
        shutil.copy2(output/'adapter/adapter_config.json', adapter/'adapter_config.json')
        responses = infer(f'screen-{step}-infer', adapter, screen)
        scores = grade(f'screen-{step}', screen, responses)
        trials[str(step)] = {'screen_passed': sum(r['passed'] for r in scores), 'screen_total': len(scores), 'adapter_sha256': digest(adapter/'adapters.safetensors')}
        if not all(r['passed'] for r in scores): continue
        rest = [r for r in validation if r['id'] not in {s['id'] for s in screen}]
        responses += infer(f'validation-{step}-infer', adapter, rest)
        after = grade(f'validation-{step}', validation, responses)
        trials[str(step)].update(qualified(before, after, old.choose))
        save(output/'trials.json', trials)
        if trials[str(step)]['near_perfect_bounded_validation']: chosen = step; break
    result = {'selected_step': chosen, 'trials': trials, 'default_adapter_replaced': False, 'fresh_tests_opened': False, 'manufacturing_authorized': False}
    if chosen is not None:
        tests = [r for r in rows if r['split'] == 'test' and (not r.get('retention'))]
        test_before = grade('fresh-before', tests, infer('fresh-before-infer', selected, tests))
        test_after = grade('fresh-after', tests, infer('fresh-after-infer', output/f'checkpoint-{chosen}', tests))
        result.update(fresh_tests_opened=True, fresh_result=qualified(test_before, test_after, old.choose))
    assert all(digest(Path(f)) == h for f, h in frozen.items())
    assert all(digest(Path(f)) == h for f, h in previous_manifest['native_sha256'].items())
    assert digest(selected/'adapters.safetensors') == old.PRIOR_SHA
    save(output/'results.json', result); phase('complete_candidate_only' if chosen is not None else 'complete_rejected')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__': main()
