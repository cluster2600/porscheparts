"""Prospective raw-model qualification; historical scorers and gates stay frozen."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import request_contract as contract
course, pilot = contract.course, contract.pilot
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNTIME = Path('/Users/maxime/Developer/Qwen993')
PRIOR = Path('/Users/maxime/Documents/PicoGK-Model-Optimization/2026-10-13-robustness-r3')
LANGUAGES = contract.LANGUAGES
GATES = {'minimum_raw_passes': 50, 'language_minimum': 8, 'refusals': 10, 'old_plans': 48, 'old_code': 16}
LABELS = {
    'en': ('axial length', 'axial thickness', 'outer radius', 'inner radius', 'bore radius', 'core radius', 'radius', 'outer diameter', 'inner diameter', 'bore diameter', 'core diameter', 'diameter', 'cell edge', 'beam diameter', 'pitch'),
    'fr': ('longueur axiale', 'épaisseur axiale', 'rayon extérieur', 'rayon intérieur', "rayon de l’alésage", 'rayon du noyau', 'rayon', 'diamètre extérieur', 'diamètre intérieur', "diamètre de l’alésage", 'diamètre du noyau', 'diamètre', 'arête de cellule', 'diamètre de barre', 'pas'),
    'de': ('axiale Länge', 'axiale Dicke', 'Außenradius', 'Innenradius', 'Bohrungsradius', 'Kernradius', 'Radius', 'Außendurchmesser', 'Innendurchmesser', 'Bohrungsdurchmesser', 'Kerndurchmesser', 'Durchmesser', 'Zellkante', 'Stabdurchmesser', 'Steigung'),
    'ja': ('軸方向の長さ', '軸方向の厚み', '外半径', '内半径', '穴の半径', 'コア半径', '半径', '外径', '内径', '穴の直径', 'コア直径', '直径', 'セル辺長', '梁の直径', 'ピッチ'),
    'zh': ('轴向长度', '轴向厚度', '外半径', '内半径', '孔半径', '芯部半径', '半径', '外直径', '内直径', '孔直径', '芯部直径', '直径', '晶胞边长', '梁直径', '螺距'),
}
FORMS = {
    'train': ('Synthetic exercise: {recipe}. Explicit input fields: {fields}.', 'Exercice synthétique : {recipe}. Champs explicites : {fields}.', 'Synthetische Übung: {recipe}. Explizite Eingaben: {fields}.', '合成演習：{recipe}。明示的入力：{fields}。', '合成练习：{recipe}。明确输入：{fields}。'),
    'valid': ('Build only synthetic {recipe} geometry from this specification: {fields}. Respect each quantity type and unit.', 'Construis la géométrie synthétique {recipe} suivant ces données : {fields}. Respecte chaque grandeur et unité.', 'Erzeuge die synthetische Geometrie {recipe} aus diesen Angaben: {fields}. Beachte Größenart und Einheit.', '次の指定から合成形状 {recipe} を作成してください。{fields}。各寸法の種類と単位を維持してください。', '请根据以下规格构建合成 {recipe} 几何体：{fields}。保留每个尺寸的类型和单位。'),
    'test': ('A synthetic {recipe} is defined by the following dimensional notes: {fields}. Return its parameter plan.', 'Les notes dimensionnelles suivantes définissent un objet synthétique {recipe} : {fields}. Donne son plan de paramètres.', 'Folgende Maßangaben definieren ein synthetisches {recipe}: {fields}. Gib den Parameterplan aus.', '合成 {recipe} の寸法メモは次のとおりです：{fields}。パラメータ計画を返してください。', '合成 {recipe} 的尺寸说明如下：{fields}。请返回参数方案。'),
}
REFUSALS = {
    'en': 'An original Porsche 993 Turbo attachment is requested. {detail} Do not invent mounting dimensions.',
    'fr': 'Une fixation originale de Porsche 993 Turbo est demandée. {detail} N’invente pas de cotes de fixation.',
    'de': 'Eine originale Porsche-993-Turbo-Befestigung wird benötigt. {detail} Erfinde keine Anschlussmaße.',
    'ja': '純正ポルシェ993ターボの取付部が必要です。{detail}。取付寸法を推測しないでください。',
    'zh': '需要原厂保时捷993 Turbo的安装接口。{detail}。请勿猜测安装尺寸。',
}
DETAILS = {
    'en': ('No measured hole pattern, axes or mating faces are available.', 'A fictional supplier estimate gives 13.125 mm spacing and a 6.375 mm bore, without inspection evidence.'),
    'fr': ('Aucune mesure des perçages, axes ou faces de contact n’est disponible.', 'Un devis fictif propose un entraxe de 13,125 mm et un alésage de 6,375 mm sans contrôle indépendant.'),
    'de': ('Es liegen keine Messungen von Lochbild, Achsen oder Kontaktflächen vor.', 'Eine fiktive Lieferantenschätzung nennt 13,125 mm Abstand und 6,375 mm Bohrung ohne unabhängige Prüfung.'),
    'ja': ('穴配置、軸、接触面の測定値はありません', '架空の業者見積では間隔13.125 mmと穴径6.375 mmですが、独立した検査証拠はありません'),
    'zh': ('没有孔位、轴线或接触面的测量数据', '虚构供应商估计间距13.125 mm、孔径6.375 mm，但没有独立检验依据'),
}


def rows(excluded, broader=False):
    seen, output = set(excluded), []
    for split, count, seed in [('train', 24, 9931411), ('valid', 2, 9931412), ('test', 2, 9931413)]:
        rng = random.Random(seed+(100 if broader else 0))
        for li, language in enumerate(LANGUAGES):
            for recipe in pilot.RECIPES:
                pair = None
                for i in range(count):
                    identifier = split+'-'+hashlib.sha256(f'{language}:{recipe}:{i}'.encode()).hexdigest()[:16]
                    if recipe == 'needs_measurement':
                        status = 'unverified' if i % 2 else 'missing'
                        request = dict(recipe=recipe, language=language, interface_status=status, fields={})
                        expected = {'recipe': recipe, 'parameters_mm': [], 'missing': ['measured_interfaces']}
                        prompt = REFUSALS[language].format(detail=DETAILS[language][i % 2]) + ' REF '+identifier.split('-', 1)[1]+'.'
                    else:
                        if split != 'train' or i % 2 == 0:
                            while True:
                                length, outer, inner = rng.randrange(64, 144)/8, rng.randrange(40, 80)/8, rng.randrange(12, 28)/8
                                pair = {'cylinder': [length, outer], 'pipe': [length, outer, inner],
                                        'washer': [rng.randrange(24, 40)/8, outer, inner],
                                        'bcc': [rng.randrange(72, 128)/8, rng.randrange(12, 23)/8],
                                        'thread': [rng.randrange(64, 104)/8, outer, inner, rng.randrange(17, 32)/8]}[recipe]
                                key = (recipe, tuple(pair))
                                try: pilot.parse(json.dumps(dict(recipe=recipe, parameters_mm=pair, missing=[])))
                                except ValueError: continue
                                if key not in seen: seen.add(key); break
                        expected = dict(recipe=recipe, parameters_mm=pair, missing=[])
                        fields, texts = {}, []
                        for j, ((name, target), number) in enumerate(zip(contract.FIELDS[recipe], pair)):
                            quantity = 'diameter' if target == 'radius' and i % 2 else target
                            number = Decimal(str(number)) * (2 if target == 'radius' and quantity == 'diameter' else 1)
                            unit = ('mm', 'cm', 'm')[(i+j+li) % 3]
                            value = format(number/contract.UNITS[unit], 'f')
                            if language in ('fr', 'de') and i % 2 == 0: value = value.replace('.', ',')
                            fields[name] = dict(value=value, unit=unit, quantity=quantity)
                            index = {'length': 0, 'thickness': 1, 'outer': 6 if recipe == 'cylinder' else 2, 'inner': 3, 'bore': 4, 'core': 5, 'cell_side': 12, 'beam': 13, 'pitch': 14}[name]
                            if quantity == 'diameter' and target == 'radius': index += 5
                            label = LABELS[language][index]
                            style = (i+j+li) % 3 if broader else {'train':0,'valid':1,'test':2}[split]
                            texts.append((f'{label} = {value} {unit}', f'{label}: {value} {unit}', f'{value} {unit} ({label})')[style])
                        rng.shuffle(texts)
                        request = dict(recipe=recipe, language=language, interface_status='synthetic', fields=fields)
                        prompt = FORMS[split][li].format(recipe=recipe, fields='; '.join(texts))
                        if broader:
                            prefixes = {'train':('Dimensional exercise','Exercice dimensionnel','Maßübung','寸法演習','尺寸练习'),
                                        'valid':('Prototype requirement','Exigence de prototype','Prototypanforderung','試作要件','原型要求'),
                                        'test':('Engineering input note','Note d’entrée technique','Technische Eingabenotiz','技術入力メモ','工程输入说明')}
                            prompt = prefixes[split][li]+'. '+prompt
                        if recipe == 'bcc': prompt += ' BCC noise = 0.'
                    if not pilot.matches(contract.normalize(request), expected): raise ValueError('Independent authored intent differs from converted request')
                    if broader: identifier=split+'-'+hashlib.sha256(('broader:'+prompt).encode()).hexdigest()[:16]
                    system = pilot.SYSTEM + (' Read field names both before values and after values in parentheses. Field order is irrelevant. Read each quantity independently. A stated radius stays a radius; only stated diameters become radii. Multiply centimeters by 10 and meters by 1000. Do not round to familiar increments.' if broader else '')
                    output.append(dict(id=identifier, split=split, language=language, domain=f'{recipe}:{language}'+(':'+status if recipe == 'needs_measurement' else ''),
                                       request=request, expected=expected, phrase_family=split,
                                       messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': json.dumps(expected, separators=(',', ':'))}]))
    return output


def summary(before, after, cases):
    if [r['id'] for r in before] != [r['id'] for r in after] or [r['id'] for r in cases] != [r['id'] for r in after]:
        raise ValueError('Evaluation coverage differs')
    languages = {language: sum(r['passed'] for r, c in zip(after, cases) if c['language'] == language) for language in LANGUAGES}
    refusals = sum(r['passed'] for r, c in zip(after, cases) if c['expected']['recipe'] == 'needs_measurement')
    regressions = [b['id'] for b, a in zip(before, after) if b['passed'] and not a['passed']]
    passed = sum(r['passed'] for r in after)
    return dict(passed=passed, total=len(after), by_language=languages, refusal_passes=refusals, regressions=regressions,
                eligible=len(after) == 60 and passed >= 50 and min(languages.values()) >= 8 and refusals == 10 and not regressions)


def verify(work):
    spec = importlib.util.spec_from_file_location('qualified_integrity', HERE.parent/'qwen-picogk-robustness-20261013/correction.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.verify(work)


def verify_prior():
    frozen = pilot.load(PRIOR/'FROZEN.json')
    archived_sdk = (PRIOR/'runtime/dotnet').resolve()
    bindings, relocated = {}, {}
    for name, expected in frozen['files'].items():
        source = Path(name)
        # iCloud can evict old Documents SDK resources; admit only identical SDK bytes.
        if source.resolve().is_relative_to(archived_sdk) and getattr(source.stat(), 'st_flags', 0) & getattr(stat, 'SF_DATALESS', 0x40000000):
            alternate = pilot.PICO/'dotnet'/source.resolve().relative_to(archived_sdk)
            relocated[name] = str(alternate)
            source = alternate
        key = str(source)
        if key in bindings and bindings[key] != expected: raise ValueError('Conflicting relocated input hashes')
        bindings[key] = expected
    with tempfile.TemporaryDirectory(prefix='qualified-prior-', dir=RUNTIME) as folder:
        path = Path(folder)
        pilot.save(path/'FROZEN.json', dict(files=bindings))
        verified = verify(path)
    return dict(original_binding_count=len(frozen['files']), relocated_dataless_sdk_files=relocated,
                payloads_verified=True, fallback_reads=len(verified['verification_read_retries']))


def published_trial(continuation):
    """Trust a predecessor only through the committed publication of its rejected trial, never its own mutable output."""
    raw = (continuation/'run-001/results.json').read_bytes(); digest = hashlib.sha256(raw).hexdigest()
    records = [r for r in map(pilot.load, sorted(HERE.glob('results-*.json')))
               if r.get('status') == 'completed_rejected_final' and r.get('private_receipt_sha256', {}).get('results.json') == digest]
    if len(records) != 1: raise ValueError('Continuation results are not a published rejected trial')
    old_result = json.loads(raw)
    if old_result.get('adapter_sha256') != records[0]['adapter_sha256'] or old_result.get('final', {}).get('passed') != records[0]['final']['passed']:
        raise ValueError('Continuation differs from its publication')
    return old_result, digest


def prepare(work, continuation=None):
    work = work.absolute()
    if work.exists() or shutil.disk_usage(work.parent).free < 3*1024**3: raise ValueError('Use a new directory with 3 GiB free')
    report = pilot.load(ROOT/'training/qwen-picogk-robustness-20261013/results.json')
    if pilot.digest(PRIOR/'FROZEN.json') != report['corrective_continuation']['frozen_inputs_sha256']: raise ValueError('Prior manifest changed')
    prior_verification = verify_prior()
    base = course.ask.recovered_base(RUNTIME, RUNTIME)
    recovery = pilot.load(course.ask.RECOVERY_PROFILE)
    packages = {name: importlib.metadata.version(name) for name in recovery['packages']}
    if packages != recovery['packages']: raise ValueError('Pinned MLX runtime changed')
    previous = pilot.load(PRIOR/'cases.json') + pilot.load(PRIOR/'paired.json') + pilot.cases()
    parent_source = PRIOR/'run-001/adapter'
    parent_sha = report['corrective_continuation']['adapter_sha256']
    predecessor = None
    if continuation is not None:
        continuation = continuation.resolve()
        old_result, results_sha = published_trial(continuation)
        if not old_result.get('test_opened') or old_result.get('eligible') or not old_result.get('frozen_inputs_verified'):
            raise ValueError('Continuation requires a completed rejected final trial')
        if pilot.digest(continuation/'FROZEN.json') != old_result['frozen_sha256']: raise ValueError('Continuation manifest changed')
        verify(continuation)
        parent_source = Path(old_result['adapter_path']).resolve(); parent_sha = old_result['adapter_sha256']
        if not parent_source.is_relative_to(continuation): raise ValueError('Parent adapter escaped its trial')
        if pilot.digest(parent_source/'adapter_config.json') != old_result['receipt_sha256'][str((parent_source/'adapter_config.json').relative_to(continuation/'run-001'))]:
            raise ValueError('Parent adapter configuration changed')
        previous += pilot.load(continuation/'cases.json')
        predecessor = dict(results_sha256=results_sha, final_passed=old_result['final']['passed'],
                           parent_adapter_sha256=parent_sha, reserved_final_reused=False)
    excluded = {(r['expected']['recipe'], tuple(r['expected']['parameters_mm'])) for r in previous if r['expected']['parameters_mm']}
    data = rows(excluded, broader=continuation is not None)
    replay_path = course.PRIOR/'2026-10-12-r3/data/train.jsonl'
    prior_bindings = pilot.load(PRIOR/'FROZEN.json')['files']
    if pilot.digest(replay_path) != prior_bindings[str(replay_path)]: raise ValueError('Replay changed')
    replay = [json.loads(line) for line in replay_path.read_text().splitlines()]
    evaluation_prompts = {r['messages'][1]['content'] for r in data if r['split'] != 'train'}
    if any(r['messages'][1]['content'] in evaluation_prompts for r in replay): raise ValueError('Evaluation prompt in replay')
    work.mkdir(); (work/'data').mkdir(); (work/'source/training').mkdir(parents=True)
    folders = ('qwen-picogk-qualified-20261014', 'qwen-picogk-robustness-20261013', 'qwen-picogk-20261012', 'qwen-research-corpus', 'qwen-porsche-corpus', 'qwen-engineering-20261002', 'm64-qwen', 'm64-engineer')
    for folder in folders:
        for path in (ROOT/'training'/folder).rglob('*'):
            if path.is_file() and path.suffix in ('.py', '.json', '.cs', '.lock'):
                destination = work/'source'/path.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, destination)
    subprocess.run([sys.executable, str(work/'source/training/qwen-picogk-qualified-20261014/qualify.py'), '--help'], capture_output=True, check=True, timeout=30)
    (work/'runtime').mkdir()
    for source, destination in [(pilot.PICO/'dotnet', work/'runtime/dotnet'), (pilot.PICO/'picogk-bin', work/'runtime/picogk-bin'), ((PRIOR/'host').resolve(), work/'host')]:
        if sys.platform == 'darwin': subprocess.run(['cp', '-cR', str(source), str(destination)], check=True)
        else: shutil.copytree(source, destination)
    for name in ('old-plans.json', 'retention.json'): shutil.copyfile(PRIOR/name, work/name)
    historical = [r for r in pilot.load(PRIOR/'cases.json') if r['split'] == 'valid']
    pilot.save(work/'historical.json', historical)
    for label, source, expected in [('baseline', RUNTIME/'run-001/adapter', report['baseline_adapter_sha256']), ('paired', parent_source, parent_sha)]:
        if pilot.digest(source/'adapters.safetensors') != expected: raise ValueError('Adapter changed')
        shutil.copytree(source, work/'adapters'/label)
    pilot.save(work/'cases.json', data)
    training = [dict(messages=r['messages']) for r in data if r['split'] == 'train'] + replay*2
    validation = [dict(messages=r['messages']) for r in data if r['split'] == 'valid']
    for name, selected in [('train', training), ('valid', validation)]:
        (work/'data'/f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in selected))
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(base), local_files_only=True, trust_remote_code=False)
    maximum = max(pilot.sequence_length(tokenizer.apply_chat_template(r['messages'], tokenize=True)) for r in training+validation)
    if maximum > 1024: raise ValueError('Sequence truncation forbidden')
    protocol = dict(schema='qwen.picogk.qualification-protocol@1', registered_at_utc=datetime.now(timezone.utc).isoformat(), gates=GATES,
                    selection='Paired candidate first; at most one fixed 240-step correction if raw development or retention fails. Select by raw development only; open fresh final once. Preserve historical gates.',
                    training=dict(steps=240, learning_rate=0.0000025, batch_size=2, replay_repetitions=2),
                    decoding=dict(temperature=0, seed=9931312, plan_max_tokens=192, code_max_tokens=1024), packages=packages,
                    source_revision=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                    prior_frozen_sha256=pilot.digest(PRIOR/'FROZEN.json'), prior_report_sha256=pilot.digest(ROOT/'training/qwen-picogk-robustness-20261013/results.json'),
                    dataset=dict(train_new=720, replay_rows=len(replay)*2, valid=60, reserved_final=60, excluded_numeric_intents=len(excluded), maximum_tokens=maximum,
                                 phrase_families_disjoint=True, shared_field_syntax_families=continuation is not None, original_reserved_final_inferred=False, synthetic_only=True),
                    predecessor=predecessor, system_prompt=data[0]['messages'][0]['content'])
    pilot.save(work/'protocol.json', protocol)
    pilot.save(work/'prior-verification.json', prior_verification)
    files = [p for p in work.rglob('*') if p.is_file()] + [base/name for name in recovery['model_files_sha256']]
    pilot.save(work/'FROZEN.json', dict(files={str(p): pilot.digest(p) for p in files}, base=str(base), packages=packages,
                                      protocol_sha256=pilot.digest(work/'protocol.json')))
    print('Registered fresh 60/60 partitions, independent contracts and one conditional training budget', flush=True)


def compare(work, out, label, adapter, cases, canonical=False, code=False):
    selected = cases
    if canonical:
        selected = [dict(r, messages=[r['messages'][0], {'role': 'user', 'content': contract.canonical(r['request'])}, r['messages'][-1]]) for r in cases]
    answers = course.infer(out, label, Path(pilot.load(work/'FROZEN.json')['base']), adapter, selected, 1024 if code else 192)
    return course.old_grade(work, out, label, selected, answers) if code else course.grade(work, out, label, selected, answers)


def train(work, out):
    base = pilot.load(work/'FROZEN.json')['base']
    command = [sys.executable, '-m', 'mlx_lm', 'lora', '--model', base, '--data', str(work/'data'), '--train', '--iters', '240',
               '--batch-size', '2', '--num-layers', '16', '--learning-rate', '0.0000025', '--max-seq-length', '1024', '--mask-prompt',
               '--seed', '9931312', '--steps-per-report', '40', '--steps-per-eval', '240', '--val-batches', '-1', '--save-every', '240',
               '--resume-adapter-file', str(work/'adapters/paired/adapters.safetensors'), '--adapter-path', str(out/'trained-adapter')]
    with (out/'training.log').open('w') as log: subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)
    import mlx.core as mx
    tensors = mx.load(str(out/'trained-adapter/adapters.safetensors'))
    if not tensors or not all(bool(mx.all(mx.isfinite(t)).item()) for t in tensors.values()): raise ValueError('Nonfinite adapter')
    pilot.save(out/'training-receipt.json', dict(command=command, all_tensors_finite=True, arrays=len(tensors), fixed_checkpoint=240))
    return out/'trained-adapter'


def run(work):
    frozen = verify(work)
    if pilot.digest(work/'protocol.json') != frozen['protocol_sha256'] or pilot.load(work/'protocol.json')['gates'] != GATES: raise ValueError('Protocol changed')
    if {p: importlib.metadata.version(p) for p in frozen['packages']} != frozen['packages']: raise ValueError('Packages changed')
    lock = (RUNTIME/'train.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1', HF_HUB_DISABLE_TELEMETRY='1',
                      TOKENIZERS_PARALLELISM='false', PXR_WORK_THREAD_LIMIT='1', OMP_NUM_THREADS='2')
    import mlx.core as mx
    mx.set_memory_limit(8*1024**3); mx.set_cache_limit(256*1024**2)
    pilot.PICO = work/'runtime'; course.ROOT = work/'source'
    cases = pilot.load(work/'cases.json'); valid = [r for r in cases if r['split'] == 'valid']
    old, code, historical = (pilot.load(work/name) for name in ('old-plans.json', 'retention.json', 'historical.json'))
    out = work/'run-001'; out.mkdir()
    gold = course.grade(work, out, 'reference-valid', valid, [dict(id=r['id'], response=r['messages'][-1]['content'], finish_reason='stop') for r in valid])
    reference_code = course.old_grade(work, out, 'reference-code', code, [dict(id=r['id'], response=r['messages'][-1]['content'], finish_reason='stop') for r in code])
    if not all(r['passed'] for r in gold+reference_code): raise ValueError('Native reference failed before model comparison')
    results = {}
    for label in ('paired', 'baseline'):
        adapter = work/'adapters'/label
        results[label] = dict(raw=compare(work, out, label+'-raw', adapter, valid), canonical=compare(work, out, label+'-canonical', adapter, valid, canonical=True),
                              old=compare(work, out, label+'-old', adapter, old), code=compare(work, out, label+'-code', adapter, code, code=True),
                              historical=compare(work, out, label+'-historical', adapter, historical))
    baseline = results['baseline']
    def eligible(candidate):
        return summary(baseline['raw'], candidate['raw'], valid)['eligible'] and all(r['passed'] for r in candidate['old']+candidate['code']) and not any(b['passed'] and not a['passed'] for b,a in zip(baseline['historical'], candidate['historical']))
    selected, adapter, trained = 'paired', work/'adapters/paired', False
    if not eligible(results[selected]):
        adapter = train(work, out); selected, trained = 'trained', True
        results[selected] = dict(raw=compare(work, out, 'trained-raw', adapter, valid), canonical=compare(work, out, 'trained-canonical', adapter, valid, canonical=True),
                                 old=compare(work, out, 'trained-old', adapter, old), code=compare(work, out, 'trained-code', adapter, code, code=True),
                                 historical=compare(work, out, 'trained-historical', adapter, historical))
    candidate = results[selected]
    report = dict(schema='qwen.picogk.qualification-results@1', selected=selected, adapter_path=str(adapter), adapter_sha256=pilot.digest(adapter/'adapters.safetensors'),
                  development=summary(baseline['raw'], candidate['raw'], valid), assisted={label: summary(baseline['canonical'], value['canonical'], valid) for label,value in results.items()},
                  old_plans_passed=sum(r['passed'] for r in candidate['old']), old_code_passed=sum(r['passed'] for r in candidate['code']),
                  historical_regressions=[b['id'] for b,a in zip(baseline['historical'], candidate['historical']) if b['passed'] and not a['passed']],
                  training_performed=trained, test_opened=False, eligible=False, default_replaced=False, manufacturing_qualified=False,
                  comparisons={label: summary(baseline['raw'], value['raw'], valid) for label,value in results.items()})
    if eligible(candidate):
        verify(work)
        test = [r for r in cases if r['split'] == 'test']
        pilot.save(out/'FINAL-OPENED.json', dict(opened_at_utc=datetime.now(timezone.utc).isoformat(), selected=selected, adapter_sha256=report['adapter_sha256']))
        tb = compare(work, out, 'final-baseline', work/'adapters/baseline', test)
        ta = compare(work, out, 'final-selected', adapter, test)
        report.update(test_opened=True, final=summary(tb, ta, test))
        report['eligible'] = report['final']['eligible']
    verify(work)
    report.update(frozen_inputs_verified=True, protocol_sha256=pilot.digest(work/'protocol.json'), frozen_sha256=pilot.digest(work/'FROZEN.json'))
    report['receipt_sha256'] = {str(p.relative_to(out)): pilot.digest(p) for p in out.rglob('*.json')}
    pilot.save(out/'results.json', report)
    if report['eligible']:
        profile = dict(schema='qwen.picogk.qualified-profile@1', work_root=str(work), results_sha256=pilot.digest(out/'results.json'),
                       frozen_sha256=report['frozen_sha256'], adapter_sha256=report['adapter_sha256'], packages=frozen['packages'])
        pilot.save(work/'qualified-profile.json', profile)
    print(json.dumps({key:value for key,value in report.items() if key not in ('receipt_sha256',)}, ensure_ascii=False), flush=True)


def install(work):
    path = work/'qualified-profile.json'
    expected = pilot.digest(path)
    spec = importlib.util.spec_from_file_location('qualified_loader', HERE/'ask.py')
    loader = importlib.util.module_from_spec(spec); spec.loader.exec_module(loader)
    loader.profile(path, expected)
    destination = Path.home()/'.local/bin/qwen-picogk-qualified'
    if destination.exists(): raise ValueError('Qualified command already exists; preserve it and review its recorded installation')
    source = work/'source/training/qwen-picogk-qualified-20261014/ask.py'
    launcher = '#!/bin/sh\nexec '+shlex.quote(str(RUNTIME/'venv/bin/python'))+' '+shlex.quote(str(source))+' --profile '+shlex.quote(str(path))+' --profile-sha256 '+expected+' "$@"\n'
    destination.write_text(launcher); destination.chmod(0o755)
    pilot.save(work/'installation.json', dict(command=str(destination), launcher_sha256=pilot.digest(destination), profile_sha256=expected,
               legacy_command_sha256=pilot.digest(Path.home()/'.local/bin/qwen-picogk'), legacy_default_changed=False))
    print('Installed qwen-picogk-qualified; legacy qwen-picogk remains the rollback command', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'install'))
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--continuation-from', type=Path, help='Register new disjoint partitions after a completed rejected final trial')
    args = parser.parse_args()
    if args.action=='prepare':prepare(args.work.absolute(),args.continuation_from)
    else:{'run':run,'install':install}[args.action](args.work.absolute())
