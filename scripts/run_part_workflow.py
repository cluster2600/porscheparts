"""Run a registered part recipe and preserve its inputs, logs and outputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def output_digest(path):
    if path.is_file():
        return 'file', sha(path)
    if not path.is_dir():
        raise ValueError('Declared output is missing: ' + str(path))
    files = {}
    for item in sorted(path.rglob('*')):
        if item.is_symlink():
            raise ValueError('Output directories cannot contain symbolic links')
        if item.is_file():
            files[item.relative_to(path).as_posix()] = sha(item)
    return 'directory', hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def inside(base, name):
    path = (base / name).resolve()
    if path == base.resolve() or not path.is_relative_to(base.resolve()):
        raise ValueError('Path must remain inside its declared directory: ' + name)
    return path


def validate(recipe):
    if recipe.get('schema') != 'porscheparts.part-workflow@1':
        raise ValueError('Unsupported workflow schema')
    if recipe.get('source', {}).get('kind') not in ('image', 'scan', 'measurements', 'editable_cad'):
        raise ValueError('Source kind must be image, scan, measurements or editable_cad')
    if recipe['source'].get('units') != 'mm':
        raise ValueError('A millimetre scale must be declared before CAD execution')
    stages = recipe.get('stages', [])
    ids = [stage.get('id', '') for stage in stages]
    if not stages or len(set(ids)) != len(ids) or any(not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', name) for name in ids):
        raise ValueError('Stage IDs must be unique short identifiers')
    for stage in stages:
        if not isinstance(stage.get('argv'), list) or not stage['argv'] or any(not isinstance(v, str) for v in stage['argv']):
            raise ValueError('Each stage needs an argv array; shell commands are not accepted')
        if not isinstance(stage.get('timeout_seconds'), int) or not 1 <= stage['timeout_seconds'] <= 3600:
            raise ValueError('Stage timeout must be 1..3600 seconds')
        for name in stage.get('outputs', []):
            inside(Path('/workflow-output'), name)
    for name, expected in recipe.get('inputs_sha256', {}).items():
        if not re.fullmatch(r'[0-9a-f]{64}', expected) or sha(inside(ROOT, name)) != expected:
            raise ValueError('Input identity mismatch: ' + name)


def verify(run):
    receipt = json.loads((run / 'workflow.json').read_text())
    if sha(inside(ROOT, receipt['recipe'])) != receipt['recipe_sha256']:
        raise ValueError('Recipe changed since execution')
    for name, expected in receipt['inputs_sha256'].items():
        if sha(inside(ROOT, name)) != expected:
            raise ValueError('Source changed since execution: ' + name)
    for stage in receipt['stages']:
        for name, expected in stage['outputs_sha256'].items():
            kind, actual = output_digest(inside(run, name))
            if actual != expected or kind != stage.get('output_types', {}).get(name, 'file'):
                raise ValueError('Output changed since execution: ' + name)
    return receipt


def execute(recipe_path, runtime_path, output):
    recipe_path = recipe_path.resolve()
    if not recipe_path.is_relative_to((ROOT / 'manufacturing/workflows').resolve()):
        raise ValueError('Only reviewed repository recipes may execute commands')
    recipe = json.loads(recipe_path.read_text())
    validate(recipe)
    runtime = json.loads(runtime_path.read_text())
    if not isinstance(runtime, dict) or any(not isinstance(v, str) for v in runtime.values()):
        raise ValueError('Runtime must map tool names to executable paths')
    for name, path in runtime.items():
        if not re.fullmatch(r'[a-z][a-z0-9_]*', name) or not Path(path).is_file() or not os.access(path, os.X_OK):
            raise ValueError('Runtime executable unavailable: ' + name)
    output = output.resolve()
    context = {**runtime, 'repo': str(ROOT), 'run': str(output)}
    commands = [[word.format_map(context) for word in stage['argv']] for stage in recipe['stages']]
    output.mkdir(parents=True, exist_ok=False)
    (output / 'logs').mkdir()
    receipt = {'schema': recipe['schema'], 'part_id': recipe['part_id'],
               'recipe': str(recipe_path.relative_to(ROOT.resolve())),
               'recipe_sha256': sha(recipe_path), 'runner_sha256': sha(__file__),
               'runtime_sha256': sha(runtime_path), 'source': recipe['source'],
               'inputs_sha256': recipe['inputs_sha256'], 'stages': [], 'status': 'running'}
    write(output / 'workflow.json', receipt)
    for stage, argv in zip(recipe['stages'], commands):
        observed = {'id': stage['id'], 'status': 'running', 'outputs_sha256': {}, 'output_types': {}}
        receipt['stages'].append(observed)
        write(output / 'workflow.json', receipt)
        started = time.monotonic()
        try:
            validate(recipe)
            with (output / 'logs' / (stage['id'] + '.stdout.log')).open('wb') as stdout, \
                 (output / 'logs' / (stage['id'] + '.stderr.log')).open('wb') as stderr:
                process = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr,
                                           start_new_session=True)
                try:
                    returncode = process.wait(timeout=stage['timeout_seconds'])
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=35)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    raise TimeoutError('Stage exceeded its declared deadline')
            observed['returncode'] = returncode
            if returncode:
                raise ValueError('Stage command failed; inspect its preserved logs')
            validate(recipe)
            for name in stage['outputs']:
                kind, digest = output_digest(inside(output, name))
                observed['outputs_sha256'][name] = digest
                observed['output_types'][name] = kind
            observed['status'] = 'executed'
        except Exception as error:
            observed.update(status='failed', error=str(error))
            receipt['status'] = 'failed'
            raise
        finally:
            observed['seconds'] = time.monotonic() - started
            for stream in ('stdout', 'stderr'):
                name = 'logs/' + stage['id'] + '.' + stream + '.log'
                if (output / name).is_file():
                    observed['outputs_sha256'][name] = sha(output / name)
            write(output / 'workflow.json', receipt)
    receipt['status'] = 'executed'
    receipt['meaning'] = 'Declared software stages executed; their numerical assessments remain authoritative'
    write(output / 'workflow.json', receipt)
    return verify(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    run = commands.add_parser('run')
    run.add_argument('recipe', type=Path)
    run.add_argument('--runtime', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('output', type=Path)
    args = parser.parse_args()
    result = execute(args.recipe, args.runtime, args.output) if args.action == 'run' else verify(args.output.resolve())
    print(json.dumps({'part_id': result['part_id'], 'status': result['status'],
                      'stages': [{k: stage[k] for k in ('id', 'status')} for stage in result['stages']]}))


if __name__ == '__main__':
    main()
