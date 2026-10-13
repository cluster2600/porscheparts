"""One registered radius/diameter correction; preserve the first continuation."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('robustness_course', Path(__file__).with_name('run.py'))
course = importlib.util.module_from_spec(spec); spec.loader.exec_module(course)
pilot = course.pilot


def verify(work):
    frozen = pilot.load(work/'FROZEN.json')
    # Bound each read: the first runner stalled in final verification of an SDK file.
    command = 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())'
    def check(binding):
        name, expected = binding
        try:
            result = subprocess.run([sys.executable, '-c', command, name], capture_output=True, text=True, timeout=15)
            retried = False
        except subprocess.TimeoutExpired:
            result = subprocess.run([sys.executable, '-c', command, name], capture_output=True, text=True, timeout=15)
            retried = True
        if result.returncode or result.stdout.strip() != expected:
            raise ValueError('Registered input changed or could not be read: '+name)
        return name if retried else None
    with ThreadPoolExecutor(max_workers=4) as pool:
        retries = [name for name in pool.map(check, frozen['files'].items()) if name]
    print('Frozen integrity passed:',len(frozen['files']),'files; bounded read retries:',json.dumps(retries),flush=True)
    frozen['verification_read_retries'] = retries
    return frozen


def paired(previous_rows, old):
    blocked = {(r['expected']['recipe'], tuple(r['expected']['parameters_mm'])) for r in previous_rows+old}
    original = course.random
    course.random = SimpleNamespace(Random=lambda seed: random.Random(seed+101))
    try: fresh = course.cases()
    finally: course.random = original
    counts = Counter(); rows = []
    for row in fresh:
        recipe = row['expected']['recipe']; lang = row['language']; key = (lang, recipe)
        params = row['expected']['parameters_mm']
        if row['split'] != 'train' or recipe in ('bcc', 'needs_measurement') or counts[key] == 5:
            continue
        if (recipe, tuple(params)) in blocked: continue
        counts[key] += 1; names = course.LABELS[lang]
        for radii in (True, False):
            fields = [(names[1 if recipe=='washer' else 0], params[0]),
                      (names[6 if radii else 7] if recipe=='cylinder' else names[2 if radii else 4], params[1]*(1 if radii else 2))]
            if recipe != 'cylinder':
                fields.append((names[(10 if radii else 11) if recipe=='thread' else (3 if radii else 5)], params[2]*(1 if radii else 2)))
            if recipe == 'thread': fields.append((names[12], params[3]))
            fields.reverse(); items = []
            for j, (label, value) in enumerate(fields):
                unit, divisor = [('cm',10), ('m',1000), ('mm',1)][j%3]
                items.append(f'{label} {Decimal(str(value))/Decimal(divisor)} {unit}')
            prompt = f'{course.PREFIX[lang]}. {recipe}: '+ '; '.join(items)+'.'
            rows.append({'id':f'paired-{lang}-{recipe}-{counts[key]}-{int(radii)}',
                         'expected':row['expected'], 'messages':[row['messages'][0], {'role':'user','content':prompt}, row['messages'][2]]})
    assert len(rows) == 200 and all(v == 5 for v in counts.values()) and len(counts) == 20
    assert len({r['messages'][1]['content'] for r in rows}) == 200
    assert all(pilot.matches(pilot.parse(r['messages'][-1]['content']), r['expected']) for r in rows)
    assert len({(r['expected']['recipe'],tuple(r['expected']['parameters_mm'])) for r in rows}) == 100
    return rows


def prepare(previous, work):
    frozen = verify(previous)
    if not pilot.load(previous/'completion-recovery.json')['passed']:
        raise ValueError('Previous integrity recovery failed')
    if shutil.disk_usage(work.parent).free < 3*1024**3: raise ValueError('Need 3 GiB free')
    extra = paired(pilot.load(previous/'cases.json'), pilot.load(previous/'old-plans.json'))
    replay = (course.PRIOR/'2026-10-12-r3/data/train.jsonl').read_text()
    audit = pilot.load(previous/'replay-provenance-audit.json')
    replay_path = course.PRIOR/'2026-10-12-r3/data/train.jsonl'
    if pilot.digest(replay_path) != audit['replay_original_sha256'] or len(replay.splitlines()) != 688:
        raise ValueError('Original replay changed')
    work.mkdir(); (work/'data').mkdir()
    for name in ('cases.json','old-plans.json','retention.json','runtime','host'):
        (work/name).symlink_to(previous/name, target_is_directory=name in ('runtime','host'))
    training = (previous/'data/train.jsonl').read_text()+replay+''.join(json.dumps({'messages':r['messages']},ensure_ascii=False)+'\n' for r in extra)*2
    (work/'data/train.jsonl').write_text(training)
    (work/'data/valid.jsonl').write_bytes((previous/'data/valid.jsonl').read_bytes())
    pilot.save(work/'paired.json',extra)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(frozen['base'], local_files_only=True, trust_remote_code=False)
    maximum = max(pilot.sequence_length(tok.apply_chat_template(json.loads(line)['messages'],tokenize=True)) for line in training.splitlines())
    if maximum > 1024: raise ValueError('Sequence truncation forbidden')
    parent = previous/'run-001/adapter/adapters.safetensors'
    files = [Path(__file__),previous/'FROZEN.json',parent,parent.with_name('adapter_config.json'),
             previous/'completion-recovery.json',previous/'replay-provenance-audit.json',replay_path,
             work/'paired.json',work/'data/train.jsonl',work/'data/valid.jsonl']
    frozen['files'].update({str(p):pilot.digest(p) for p in files})
    frozen.update(training_rows=len(training.splitlines()),maximum_tokens=maximum,
                  correction={'training_parent':str(parent),'training_parent_sha256':pilot.digest(parent),
                              'paired_prompts':200,'paired_geometric_intents':100,'paired_repetitions':2,
                              'old_replay_rows':1376,'new_original_rows':720,
                              'baseline':'Retained r3; same development and retention sets; final test still closed.'})
    pilot.save(work/'FROZEN.json',frozen); print('Prepared correction:',frozen['training_rows'],'rows',flush=True)


def run(work):
    original_save = pilot.save
    def register(path,value):
        if path.name == 'protocol.json':
            correction = pilot.load(work/'FROZEN.json')['correction']; command = value['command']
            for flag, text in {'--resume-adapter-file':correction['training_parent'],'--iters':'240',
                               '--save-every':'240','--steps-per-eval':'240','--learning-rate':'0.0000025'}.items():
                command[command.index(flag)+1] = text
            value.update(correction=correction,selection=value['selection'].replace('480','240'))
        original_save(path,value)
    pilot.save = register; course.verify = verify
    course.run(work)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=['self-check','prepare','run'])
    p.add_argument('--work',type=Path); p.add_argument('--previous',type=Path); a=p.parse_args()
    if a.action == 'self-check':
        rows=paired(course.cases(),[]); assert paired(course.cases(),[]) == rows
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory); file=work/'input.txt'; file.write_text('registered')
            pilot.save(work/'FROZEN.json',{'files':{str(file):pilot.digest(file)}}); verify(work)
            file.write_text('changed')
            try: verify(work)
            except ValueError: pass
            else: raise AssertionError('Changed registered input accepted')
        print('Paired correction self-check passed: 200 prompts, 100 new geometric intents, five languages')
    elif a.action == 'prepare':
        if not a.work or not a.previous: p.error('--work and --previous required')
        prepare(a.previous.resolve(),a.work.resolve())
    else:
        if not a.work: p.error('--work required')
        run(a.work.resolve())
