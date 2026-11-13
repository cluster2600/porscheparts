"""Independently verify recovered bytes and distinguish native completion from admission."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'receipt', 'preparation', 'input-manifest', 'collector-source', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--instance-id', type=int, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    preparation = json.loads(args.preparation.read_text())
    assert receipt['stage'] == 'complete' and sha(args.archive) == receipt['archive_sha256']
    assert sha(args.collector_source) == receipt['source_sha256']
    assert sha(args.input_manifest) == preparation['input_manifest_sha256']
    expected = {row['path']: row for row in json.loads(args.input_manifest.read_text())['files']}
    expected['input-manifest.json'] = {'sha256': sha(args.input_manifest), 'bytes': args.input_manifest.stat().st_size}
    expected['inputs.tar.gz'] = {'sha256': preparation['archive_sha256'], 'bytes': preparation['archive_bytes']}
    args.output.mkdir(mode=0o700, exist_ok=False)
    with tarfile.open(args.archive) as source:
        members = source.getmembers()
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        assert len({m.name for m in members}) == len(members), 'Duplicate archive member refused'
        assert sum(m.size for m in members) < shutil.disk_usage(args.output).free-4*1024**3
        source.extractall(args.output, filter='data')
    manifest = json.loads((args.output/'recovery-manifest.json').read_text())
    assert manifest['instance_id'] == args.instance_id
    assert manifest['source_sha256'] == sha(args.collector_source)
    assert manifest['worker_confirmed_terminal'] and manifest['native_check_processes_confirmed_absent']
    declared = {row['path']: row for row in manifest['files']}
    actual = {str(p.relative_to(args.output)) for p in args.output.rglob('*') if p.is_file()}
    assert actual == set(declared)|{'recovery-manifest.json'}
    for name, row in declared.items():
        path = args.output/name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    omitted = {row['path']: row for row in manifest['omitted_verified_inputs']}
    assert not (set(omitted)&set(declared)) and set(omitted) <= set(expected)
    for name, row in omitted.items():
        assert row['sha256'] == expected[name]['sha256'] and row['bytes'] == expected[name]['bytes']
    missing = set(expected)-set(omitted)-set(declared)
    changed = [name for name in expected if name in declared and declared[name]['sha256'] != expected[name]['sha256']]
    inputs_unchanged = not missing and not changed
    terminal_path = args.output/'terminal.json'
    terminal = json.loads(terminal_path.read_text()) if terminal_path.exists() else None
    if terminal:
        assert terminal['source_sha256'] == preparation['worker_source_sha256']
        assert terminal['input_manifest_sha256'] == preparation['input_manifest_sha256']
        assert not terminal['field_solve_executed'] and not terminal['physics_admitted']
    execution_path = args.output/'head-check-execution.json'
    execution = json.loads(execution_path.read_text()) if execution_path.exists() else None
    text = (args.output/'head-check.log').read_text() if (args.output/'head-check.log').exists() else ''
    if execution:
        assert execution['log_sha256'] == sha(args.output/'head-check.log')
    counts = {name: bool(re.search(r'^\s*'+name+r':\s*'+str(number)+r'\s*$', text, re.MULTILINE))
              for name, number in [('points', 4181299), ('faces', 30072005), ('cells', 12981388)]}
    completed = bool(execution and not execution['timeout'] and execution['exit_code'] in (0, 1)
                     and re.search(r'^\s*End\s*$', text, re.MULTILINE) and all(counts.values()))
    reported_pass = bool(completed and execution['exit_code'] == 0 and 'Mesh OK.' in text)
    passed = reported_pass and inputs_unchanged
    if terminal:
        assert terminal['native_head_check_completed'] == completed and terminal['native_head_check_passed'] == reported_pass
    report = dict(source_sha256=sha(__file__), archive_sha256=sha(args.archive), instance_id=args.instance_id,
                  recovered_files_verified=len(declared), omitted_original_files_verified=len(omitted),
                  all_recovered_bytes_match=True, all_original_inputs_unchanged=inputs_unchanged,
                  changed_input_files=len(changed), missing_input_files=len(missing),
                  native_head_counts_match=all(counts.values()), native_head_check_completed=completed,
                  native_head_check_passed=passed, native_execution=execution,
                  worker_terminal_receipt=terminal, upstream_shape_quality_passed=False,
                  case_specific_operator_admission=False, field_solve_executed=False,
                  physics_admitted=False, manufacturing_qualified=False, engine_qualified=False)
    result = args.output.with_name(args.output.name+'-verification.json')
    with result.open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
