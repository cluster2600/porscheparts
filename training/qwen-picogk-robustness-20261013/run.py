"""Registered multilingual/unit robustness continuation of the retained PicoGK adapter."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / 'qwen-picogk-20261012'))
import ask
import pilot

RUNTIME = Path('/Users/maxime/Developer/Qwen993')
PRIOR = Path('/Users/maxime/Documents/PicoGK-Model-Optimization')
LANGUAGES = ('en', 'fr', 'de', 'ja', 'zh')
LABELS = {
    'en': ('length', 'thickness', 'outer radius', 'inner radius', 'outer diameter', 'bore diameter', 'radius', 'diameter', 'cell side', 'beam diameter', 'core radius', 'core diameter', 'pitch'),
    'fr': ('longueur', 'épaisseur', 'rayon extérieur', 'rayon intérieur', 'diamètre extérieur', 'diamètre du trou', 'rayon', 'diamètre', 'côté de cellule', 'diamètre des barres', 'rayon du noyau', 'diamètre du noyau', 'pas'),
    'de': ('Länge', 'Dicke', 'Außenradius', 'Innenradius', 'Außendurchmesser', 'Bohrungsdurchmesser', 'Radius', 'Durchmesser', 'Zellkante', 'Stabdurchmesser', 'Kernradius', 'Kerndurchmesser', 'Steigung'),
    'ja': ('長さ', '厚さ', '外半径', '内半径', '外径', '穴径', '半径', '直径', 'セルの一辺', 'ビーム直径', 'コア半径', 'コア直径', 'ピッチ'),
    'zh': ('长度', '厚度', '外半径', '内半径', '外径', '孔径', '半径', '直径', '单元边长', '杆直径', '芯部半径', '芯部直径', '螺距'),
}
PREFIX = {'en': 'Synthetic geometry only', 'fr': 'Géométrie synthétique uniquement', 'de': 'Nur synthetische Geometrie', 'ja': '合成形状のみ', 'zh': '仅合成几何'}
MISSING = {
    'en': 'Original 993 Turbo mounting interfaces are required. No hole, axis or mating-face measurements are supplied.',
    'fr': 'Interfaces de fixation originales 993 Turbo requises. Aucune mesure des trous, axes ou faces n’est fournie.',
    'de': 'Originale Befestigungsschnittstellen des 993 Turbo benötigt. Keine Messungen von Bohrungen, Achsen oder Anschlussflächen vorhanden.',
    'ja': '993 Turboの純正取付インターフェースが必要です。穴、軸、取付面の実測値はありません。',
    'zh': '需要993 Turbo的原厂安装接口。未提供孔、轴线或配合面的实测数据。',
}
UNVERIFIED = {
    'en': 'A supplier suggests hole spacing 12 mm and bore diameter 6 mm for original 993 Turbo mounting interfaces. These are estimates, not independently verified measurements. Generate the original interfaces.',
    'fr': 'Un fournisseur propose un entraxe de 12 mm et un alésage de 6 mm pour les fixations originales 993 Turbo. Ce sont des estimations non vérifiées indépendamment. Génère les interfaces originales.',
    'de': 'Ein Lieferant nennt 12 mm Lochabstand und 6 mm Bohrungsdurchmesser für originale 993-Turbo-Befestigungen. Dies sind Schätzungen, keine unabhängig bestätigten Messwerte. Erzeuge die originalen Schnittstellen.',
    'ja': '業者は993 Turbo純正取付部の穴間隔12 mm、穴径6 mmを提案しています。独立に検証された実測値ではなく推定値です。純正インターフェースを生成してください。',
    'zh': '供应商建议993 Turbo原厂安装接口孔距12 mm、孔径6 mm。这是估计值，并非独立验证的实测值。请生成原厂接口。',
}


def cases():
    rows = []; seen = set()
    for split, count, seed in [('train', 24, 9931301), ('valid', 2, 9931302), ('test', 2, 9931303)]:
        rng = random.Random(seed)
        for language in LANGUAGES:
            names = LABELS[language]
            for recipe in pilot.RECIPES:
                for i in range(count):
                    identifier = f'r4-{split}-{language}-{recipe}-{i:02d}'
                    if recipe == 'needs_measurement':
                        status = 'unverified' if i % 2 else 'missing'
                        prompt = (UNVERIFIED if i % 2 else MISSING)[language] + ' REF ' + hashlib.sha256(identifier.encode()).hexdigest()[:12] + '.'
                        params = []; domain = f'{recipe}:{language}:{status}'
                    else:
                        while True:
                            length = rng.randrange(24, 80) / 4; outer = rng.randrange(16, 40) / 4
                            inner = min(rng.randrange(6, 18) / 4, outer - 1.25)
                            params = {'cylinder': [length, outer], 'pipe': [length, outer, inner],
                                      'washer': [rng.randrange(8, 16) / 4, outer, inner],
                                      'bcc': [rng.randrange(36, 69) / 4, rng.randrange(6, 13) / 4],
                                      'thread': [rng.randrange(24, 48) / 4, rng.randrange(20, 36) / 4, rng.randrange(8, 20) / 4, rng.randrange(8, 17) / 4]}[recipe]
                            key = (recipe, tuple(params))
                            if key not in seen: seen.add(key); break
                        radii = i % 2 == 0
                        if recipe == 'cylinder':
                            fields = [(names[0], params[0]), (names[6] if radii else names[7], params[1] if radii else 2*params[1])]
                        elif recipe in ('pipe', 'washer'):
                            fields = [(names[0 if recipe=='pipe' else 1], params[0]), (names[2] if radii else names[4], params[1] if radii else 2*params[1]), (names[3] if radii else names[5], params[2] if radii else 2*params[2])]
                        elif recipe == 'bcc':
                            fields = [(names[8], params[0]), (names[9], params[1])]
                        else:
                            fields = [(names[0], params[0]), (names[2] if radii else names[4], params[1] if radii else 2*params[1]), (names[10] if radii else names[11], params[2] if radii else 2*params[2]), (names[12], params[3])]
                        rng.shuffle(fields)
                        items = []
                        for j, (label, number) in enumerate(fields):
                            unit, divisor = [('mm', 1), ('cm', 10), ('m', 1000)][(i+j) % 3]
                            text = format(Decimal(str(number)) / Decimal(divisor), 'f')
                            if language in ('fr', 'de') and i % 3 == 2: text = text.replace('.', ',')
                            items.append(f'{label} {text} {unit}')
                        prompt = f'{PREFIX[language]}. {recipe}: ' + '; '.join(items) + ('. BCC noise = 0.' if recipe=='bcc' else '.')
                        domain = f'{recipe}:{language}'
                    expected = {'recipe': recipe, 'parameters_mm': params, 'missing': ['measured_interfaces'] if not params else []}
                    pilot.parse(json.dumps(expected))
                    rows.append({'id': identifier, 'split': split, 'domain': domain, 'language': language,
                                 'expected': expected, 'synthetic': True,
                                 'messages': [{'role': 'system', 'content': pilot.SYSTEM}, {'role': 'user', 'content': prompt},
                                              {'role': 'assistant', 'content': json.dumps(expected, separators=(',', ':'))}]})
    return rows


def verify(work):
    frozen = pilot.load(work / 'FROZEN.json')
    if any(pilot.digest(Path(path)) != sha for path, sha in frozen['files'].items()):
        raise ValueError('Registered input changed')
    return frozen


def prepare(work):
    if shutil.disk_usage(work.parent).free < 3*1024**3: raise ValueError('Need 3 GiB free')
    base = ask.recovered_base(RUNTIME, RUNTIME)
    profile = pilot.load(ask.RECOVERY_PROFILE)
    if any(importlib.metadata.version(k) != v for k, v in profile['packages'].items()): raise ValueError('Runtime changed')
    work.mkdir(); (work / 'data').mkdir()
    rows = cases(); pilot.save(work / 'cases.json', rows)
    replay = [json.loads(line) for line in (PRIOR / '2026-10-12-r3/data/train.jsonl').read_text().splitlines()]
    old_plans = [r for r in pilot.load(PRIOR / '2026-10-12-r2/dataset/cases.json') if r['split'] == 'valid']
    retention = pilot.load(PRIOR / '2026-10-12-r2/dataset/retention.json')
    pilot.save(work / 'old-plans.json', old_plans); pilot.save(work / 'retention.json', retention)
    held_out = {r['messages'][1]['content'] for r in rows if r['split'] != 'train'}
    if any(r['messages'][1]['content'] in held_out for r in replay): raise ValueError('Evaluation prompt in replay')
    training = [dict(messages=r['messages']) for r in rows if r['split'] == 'train'] + replay
    valid = [dict(messages=r['messages']) for r in rows if r['split'] == 'valid']
    for split, selected in [('train', training), ('valid', valid)]:
        (work / 'data' / (split+'.jsonl')).write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in selected))
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(base), local_files_only=True, trust_remote_code=False)
    maximum = max(pilot.sequence_length(tok.apply_chat_template(r['messages'], tokenize=True)) for r in training+valid)
    if maximum > 1024: raise ValueError('Sequence truncation forbidden')
    # Copy the original native execution environment; do not change the installed workbench.
    (work / 'runtime').mkdir()
    shutil.copytree(pilot.PICO / 'dotnet', work / 'runtime/dotnet')
    shutil.copytree(pilot.PICO / 'picogk-bin', work / 'runtime/picogk-bin')
    shutil.copytree(PRIOR / '2026-10-12-r2/host/bin', work / 'host/bin')
    files = [Path(__file__), *[p for p in (HERE.parent / 'qwen-picogk-20261012').glob('*.py')], ask.RECOVERY_PROFILE,
             ROOT / 'training/m64-qwen/requirements.lock', ROOT / 'training/qwen-engineering-20261002/run.py',
             ROOT / 'training/m64-qwen/picogk.py', ROOT / 'training/m64-engineer/openusd.py',
             RUNTIME / 'run-001/adapter/adapters.safetensors', RUNTIME / 'run-001/adapter/adapter_config.json',
             *[base / name for name in profile['model_files_sha256']],
             *[p for p in work.rglob('*') if p.is_file()]]
    parent = RUNTIME / 'run-001/adapter/adapters.safetensors'
    if pilot.digest(parent) != profile['selected_adapter_sha256']: raise ValueError('Parent adapter changed')
    pilot.save(work / 'FROZEN.json', {'files': {str(p): pilot.digest(p) for p in files},
               'base': str(base), 'parent_adapter': str(parent.parent), 'maximum_tokens': maximum,
               'training_rows': len(training), 'new_training_rows': 720, 'replay_rows': len(replay)})
    print('Prepared', len(training), 'training rows; 60 validation, 60 closed test, 48 old plans, 16 code retention', flush=True)


def infer(out, label, base, adapter, rows, maximum=192):
    import mlx.core as mx
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    model, tok = load(str(base), adapter_path=str(adapter), tokenizer_config={'trust_remote_code': False})
    tok.add_eos_token('<|im_end|>'); mx.random.seed(9931312)
    answers = []
    for row in rows:
        prompt = tok.apply_chat_template(row['messages'][:2], tokenize=False, add_generation_prompt=True)
        if len(tok.encode(prompt)) > 1024: raise ValueError('Evaluation prompt exceeds context')
        text = ''; last = None
        for last in stream_generate(model, tok, prompt=prompt, max_tokens=maximum, sampler=make_sampler(temp=0)): text += last.text
        if last is None: raise ValueError('Empty model response')
        answers.append({'id': row['id'], 'response': text, 'finish_reason': last.finish_reason, 'tokens': last.generation_tokens})
        pilot.save(out / (label+'-answers.json'), answers)
        print(label, len(answers), '/', len(rows), flush=True)
    del model, tok; mx.clear_cache()
    return answers


def grade(work, out, label, rows, answers):
    folder = out / label; folder.mkdir(); scored = []
    if [r['id'] for r in rows] != [a['id'] for a in answers]: raise ValueError('Coverage differs')
    for row, answer in zip(rows, answers):
        item = {'id': row['id'], 'domain': row['domain'], 'passed': False, 'complete': answer['finish_reason'] == 'stop'}
        try:
            plan = ask.accepted(answer['response'], answer['finish_reason'])
            item['intent_passed'] = pilot.matches(plan, row['expected'])
            if not item['intent_passed']: raise ValueError('Independent expected parameters differ')
            if plan['recipe'] == 'needs_measurement': item['native_required'] = False; okay = True
            else:
                item['native'] = pilot.native(work, plan, folder / row['id'])
                okay = item['native']['geometry_screen_passed']
            item['passed'] = okay
        except (ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as error: item['error'] = str(error)
        scored.append(item)
    pilot.save(out / (label+'-scores.json'), scored)
    return scored


def old_grade(work, out, label, rows, answers):
    path = out / (label+'-responses.json'); pilot.save(path, answers)
    command = [str(pilot.USD), str(ROOT/'training/qwen-engineering-20261002/run.py'), 'score',
               '--training-checkout', str(ROOT), '--usd-python', str(pilot.USD),
               '--sdk', str(pilot.PICO/'dotnet/dotnet'), '--dll', str(pilot.PICO/'picogk-bin/PicoGK.dll'),
               '--input', str(work/'retention.json'), '--responses', str(path), '--output', str(out/label)]
    with (out/(label+'.log')).open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
    scored = pilot.load(out/label/'scores.json')
    finish = {r['id']: r.get('finish_reason', 'stop') for r in answers}
    for item in scored: item['passed'] = item['passed'] and finish[item['id']] == 'stop'
    return scored


def run(work):
    frozen = verify(work); base = Path(frozen['base']); parent = Path(frozen['parent_adapter'])
    out = work/'run-001'; out.mkdir()
    lock = (RUNTIME/'train.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1',
                      HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false', PXR_WORK_THREAD_LIMIT='1', OMP_NUM_THREADS='2')
    import mlx.core as mx
    mx.set_memory_limit(8*1024**3); mx.set_cache_limit(256*1024**2)
    pilot.PICO = work/'runtime'
    rows = pilot.load(work/'cases.json'); valid = [r for r in rows if r['split']=='valid']
    old = pilot.load(work/'old-plans.json'); retention = pilot.load(work/'retention.json')
    command = [sys.executable, '-m', 'mlx_lm', 'lora', '--model', str(base), '--data', str(work/'data'),
               '--train', '--iters', '480', '--batch-size', '2', '--num-layers', '16', '--learning-rate', '0.000005',
               '--max-seq-length', '1024', '--mask-prompt', '--seed', '9931312', '--steps-per-report', '40',
               '--steps-per-eval', '480', '--val-batches', '-1', '--save-every', '480',
               '--resume-adapter-file', str(parent/'adapters.safetensors'), '--adapter-path', str(out/'adapter')]
    pilot.save(out/'protocol.json', {'registered_at_utc': datetime.now(timezone.utc).isoformat(), 'command': command,
               'frozen_sha256': pilot.digest(work/'FROZEN.json'), 'parent_sha256': pilot.digest(parent/'adapters.safetensors'),
               'selection': 'Fixed step 480 only. Every recipe/language/status category >=95%; no lost baseline pass; all 48 old plans and 16 code retention cases pass. Only then open fresh test once. No default replacement.',
               'scope': 'Parameter-disjoint synthetic cases sharing recipes and grammar families; not general API mastery, unseen task-family evaluation, raw mesh qualification or manufacturing.',
               'packages': {p: importlib.metadata.version(p) for p in ('mlx', 'mlx-lm', 'transformers')},
               'generation': {'temperature': 0, 'seed': 9931312, 'plan_max_tokens': 192, 'code_max_tokens': 1024}})
    protocol_hash = pilot.digest(out/'protocol.json')
    reference = old_grade(work, out, 'retention-reference', retention, [{'id':r['id'],'response':r['messages'][-1]['content']} for r in retention])
    if not all(r['passed'] for r in reference): raise ValueError('Old native reference failed')
    gold = grade(work, out, 'gold-valid', valid, [{'id':r['id'],'response':r['messages'][-1]['content'],'finish_reason':'stop'} for r in valid])
    if not all(r['passed'] for r in gold): raise ValueError('Gold software geometry failed')
    before = grade(work, out, 'valid-before', valid, infer(out, 'valid-before', base, parent, valid))
    old_before = grade(work, out, 'old-plans-before', old, infer(out, 'old-plans-before', base, parent, old))
    code_before = old_grade(work, out, 'retention-before', retention, infer(out, 'retention-before', base, parent, retention, 1024))
    print('TRAINING START', flush=True)
    with (out/'training.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)
    if any(token in (out/'training.log').read_text().lower() for token in ('nan', 'inf loss')): raise ValueError('Nonfinite training metric')
    tensors = mx.load(str(out/'adapter/adapters.safetensors'))
    if not tensors or not all(bool(mx.all(mx.isfinite(t)).item()) for t in tensors.values()): raise ValueError('Nonfinite adapter')
    pilot.save(out/'adapter-finiteness.json', {'arrays':len(tensors), 'all_finite':True, 'parameters':sum(t.size for t in tensors.values())})
    candidate = out/'adapter'
    after = grade(work, out, 'valid-after', valid, infer(out, 'valid-after', base, candidate, valid))
    old_after = grade(work, out, 'old-plans-after', old, infer(out, 'old-plans-after', base, candidate, old))
    code_after = old_grade(work, out, 'retention-after', retention, infer(out, 'retention-after', base, candidate, retention, 1024))
    result = {'validation':pilot.gate(before, after), 'old_plans':pilot.gate(old_before, old_after),
              'code_retention':pilot.gate(code_before, code_after), 'test_opened':False,
              'weights_updated':True, 'default_replaced':False, 'manufacturing_qualified':False,
              'adapter_sha256':pilot.digest(candidate/'adapters.safetensors')}
    retained = all(r['passed'] for r in old_after+code_after)
    if result['validation']['eligible'] and retained and result['old_plans']['eligible'] and result['code_retention']['eligible']:
        test = [r for r in rows if r['split']=='test']
        tb = grade(work, out, 'test-before', test, infer(out, 'test-before', base, parent, test))
        ta = grade(work, out, 'test-after', test, infer(out, 'test-after', base, candidate, test))
        result.update(test_opened=True, test=pilot.gate(tb, ta))
    result['eligible'] = result['test_opened'] and result['test']['eligible']
    verify(work)
    if pilot.digest(out/'protocol.json') != protocol_hash: raise ValueError('Protocol changed')
    pilot.save(out/'results.json', result); print(json.dumps(result), flush=True)


def self_check():
    rows = cases()
    assert Counter(r['split'] for r in rows) == {'train':720, 'valid':60, 'test':60}
    assert len({r['id'] for r in rows}) == len({r['messages'][1]['content'] for r in rows}) == 840
    intents = [(r['expected']['recipe'], tuple(r['expected']['parameters_mm'])) for r in rows if r['expected']['parameters_mm']]
    assert len(intents) == len(set(intents))
    assert all(pilot.matches(pilot.parse(r['messages'][-1]['content']), r['expected']) for r in rows)
    assert all('needs_measurement' not in r['messages'][1]['content'] for r in rows if r['expected']['recipe']=='needs_measurement')
    for split in ('valid', 'test'):
        assert len({r['domain'] for r in rows if r['split']==split}) == 35
    print('Robustness self-check passed: partitions, numeric intent, languages, missing/unverified interfaces')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['self-check','prepare','run'])
    p.add_argument('--work', type=Path); a = p.parse_args()
    if a.action == 'self-check': self_check()
    else:
        if not a.work: p.error('--work required')
        (prepare if a.action=='prepare' else run)(a.work.resolve())
