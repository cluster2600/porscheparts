"""Collect this one owned trial after its actual tool handle has reached terminal."""
import copy
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import time
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[2]
GO = '49ee7a6240c6cebbbca274e38a23dd44bf755c4bef556542636ca5b58caab90e'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''): digest.update(block)
    return digest.hexdigest()

def read(path): return json.loads(path.read_bytes())
def encoded(value): return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
def rel(path): return str(path.relative_to(R))

def inverses():
    pp, pl, pc = (H / n for n in ('pending-plan.json', 'pending-launch-plan.json', 'pending-command.json'))
    ap, al, ac = (H / n for n in ('plan.json', 'launch-plan.json', 'command.json'))
    p, launch, command = read(ap), read(al), read(ac)
    go_name = rel(H / 'root-GO-001.json')
    assert sha(R / go_name) == p['root_GO_sha256'] == launch['root_GO_sha256'] == command['root_GO_sha256'] == GO
    assert p['root_GO'] == launch['root_GO'] == command['root_GO'] == go_name
    assert p['launch_ready'] is launch['launch_ready'] is command['launch_ready'] is True
    back = copy.deepcopy(p); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None); del back['files_sha256'][go_name]
    assert back == read(pp) and encoded(back) == pp.read_bytes()
    back = copy.deepcopy(launch); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None)
    back['command'][5:7] = [str(pp), sha(pp)]; del back['inputs_sha256'][go_name]
    back['inputs_sha256'] = {rel(pp) if key == rel(ap) else key: sha(pp) if key == rel(ap) else value for key, value in back['inputs_sha256'].items()}
    assert back == read(pl) and encoded(back) == pl.read_bytes()
    back = copy.deepcopy(command); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None)
    back['argv'][4], back['argv'][6] = str(pl), sha(pl)
    assert back == read(pc) and encoded(back) == pc.read_bytes()
    assert launch['command'][5:7] == [str(ap), sha(ap)] and command['argv'][4] == str(al) and command['argv'][6] == sha(al)
    return p, launch, command

def absent(flag, pid):
    result = subprocess.run(['/bin/ps', flag, str(pid), '-o', 'pid=,ppid=,pgid=,stat='], capture_output=True, text=True, timeout=2)
    assert result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip()
    return True

def whole_outputs(output, execution):
    rows = {}
    for directory in (output, execution):
        for path in sorted(directory.rglob('*')):
            assert not path.is_symlink()
            if not path.is_file(): continue
            before = path.stat(); digest = sha(path); after = path.stat()
            assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            rows[rel(path)] = dict(sha256=digest, bytes=after.st_size)
    return rows

def collect():
    began = time.monotonic()
    p, launch, command = inverses()
    tool = read(H / 'actual-tool-terminal.json')
    assert tool['session_id'] == 77258 and tool['initial_chunk'] == '946f72' and type(tool['actual_tool_returncode']) is int
    execution, output = R / p['execution_directory'], R / p['output_directory']
    supervision = read(execution / 'execution-receipt.json'); started = read(execution / 'started.json')
    pins = {**launch['source_sha256'], **launch['inputs_sha256']}
    assert {name: sha(R / name) for name in pins} == pins == supervision['sources_before'] == supervision['sources_after']
    assert supervision['sources_and_plan_unchanged'] and supervision['plan_sha256'] == started['plan_sha256'] == sha(H / 'launch-plan.json')
    assert supervision['command'] == launch['command'] and supervision['cwd'] == command['cwd'] == str(R)
    assert supervision['pid'] == started['pid'] == started['pgid'] == 8333
    assert supervision['direct_child_reaped'] and supervision['no_non_zombie_group_members'] and supervision['final_group_members'] == [] and supervision['cleanup_error'] is None
    assert absent('-p', started['pid']) and absent('-g', started['pgid'])
    assert supervision['actual_returncode'] is not None
    assert tool['actual_tool_returncode'] == (0 if supervision['status'] == 'executed' else 1)
    for name, digest in supervision['logs_sha256'].items(): assert sha(execution / name) == digest
    events = [json.loads(line) for line in (output / 'events.jsonl').read_text().splitlines()] if (output / 'events.jsonl').exists() else []
    assert [row['seconds'] for row in events] == sorted(row['seconds'] for row in events)
    spec = importlib.util.spec_from_file_location('_closed_trial_stdlib', H / 'trial.py')
    trial = importlib.util.module_from_spec(spec); spec.loader.exec_module(trial)
    assessment_path = output / 'assessment.json'
    assessment = read(assessment_path) if assessment_path.is_file() else None
    evidence = dict(native_assessment_present=assessment is not None, events=events)
    if assessment is not None:
        assert assessment['sources_before'] == assessment['sources_after'] == p['files_sha256'] and assessment['sources_unchanged']
        assert assessment['candidate_qualified'] is False and assessment['master_replaced'] is False and assessment['FEA_executed'] is False and assessment['old_complete7_law_proof_not_transferred_to_union'] is True
        assert assessment['downstream_checks'] == {key: 'PENDING' for key in trial.GATE.PENDING}
        actual_partial = {str(path.relative_to(output)): sha(path) for path in sorted(output.rglob('*')) if path.is_file() and path.name not in ('assessment.json', 'events.jsonl')}
        assert assessment['all_partial_outputs_before_assessment_sha256'] == actual_partial
        printed = []
        for line in (execution / 'stdout.log').read_text().splitlines():
            try: row = json.loads(line)
            except json.JSONDecodeError: continue
            if isinstance(row, dict) and row.get('assessment_sha256') == sha(assessment_path): printed.append(row)
        assert len(printed) == 1 and printed[0]['status'] == assessment['status']
        for file, digest in assessment.get('outputs_sha256', {}).items(): assert sha(output / file) == digest
        for role, ledger in assessment.get('actual_window_branch_ledgers', {}).items():
            ledger_path = output / ledger['path']; assert sha(ledger_path) == ledger['sha256']
            rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
            assert rows == ledger['rows']; trial.check_branch_ledger(rows, .9 if role == 'base-without-ribs' else .4)
        for name, preservation in assessment.get('raw_Cut_preservation', {}).items():
            assert read(output / (name + '-raw-preservation.json')) == preservation
            if preservation['path'] is None: assert preservation['sha256'] is None and preservation['reason'] == 'completed_native_Cut_returned_a_null_shape'
            else: assert preservation['reason'] is None and sha(output / preservation['path']) == preservation['sha256']
        summaries = assessment.get('native_Cut_summaries', {})
        for name, summary in summaries.items(): assert read(output / (name + '.json')) == summary
        measurements_path = output / 'local-measurements-before-gates.json'
        if measurements_path.is_file():
            measured = read(measurements_path); assert all(assessment[key] == value for key, value in measured.items())
            study = read(R / p['baseline_study'])
            assert measured['mass_kg'] == measured['native_volume_mm3'] * study['material']['density_tonne_mm3'] * 1000
            assert measured['delta_from_current07b_volume_mm3'] == measured['native_volume_mm3'] - measured['current07b_volume_mm3']
            evidence['complete_measurements_before_gates'] = measured
        if supervision['actual_returncode'] == 0:
            assert assessment['status'] == 'single_first_window_trial_local_gates_complete_downstream_PENDING' and 'failure' not in assessment
            assert list(summaries) == ['baseline-minus-candidate', 'current07b-minus-candidate', 'candidate-minus-current07b']
            trial.strict_empty(summaries['baseline-minus-candidate']); trial.strict_empty(summaries['current07b-minus-candidate'])
            added = summaries['candidate-minus-current07b']
            assert not added['native_topologically_empty'] and added['native_valid'] and added['material_solid_volume_mm3'] > 0
            measured = evidence['complete_measurements_before_gates']; assert measured['native_volume_mm3'] > measured['current07b_volume_mm3']
            trial.GATE.local_gate_flags(summaries['baseline-minus-candidate'], measured['candidate_native_valid'], measured['candidate_native_solid_count'], measured['mass_kg'], measured['bounds_mm'], p)
            assert set(assessment['actual_window_branch_ledgers']) == {'base-without-ribs', 'outer-window-stock'}
        evidence.update(assessment_sha256=sha(assessment_path), actual_status=assessment['status'], failure=assessment.get('failure'), raw_candidate_sha256=assessment.get('outputs_sha256', {}).get('candidate-native.brep'), complete_native_Cut_summaries=summaries, raw_Cut_preservation=assessment.get('raw_Cut_preservation', {}), actual_window_branch_ledgers=assessment.get('actual_window_branch_ledgers', {}))
    for predecessor in ('001', '002'):
        old = H.with_name('bounded-webs-first-window-parameter-trial-preparation-' + predecessor)
        record = read(H / ('from-' + predecessor + '.json'))
        assert all(sha(old / name) == digest for name, digest in record['old_pending_controls_preserved'].items())
    outputs = whole_outputs(output, execution)
    return dict(schema='owned-first-window-trial003-terminal-1', status='closed_actual_window_trial_local_PASS_only' if supervision['actual_returncode'] == 0 else 'closed_actual_window_trial_refusal_preserved',
        actual_tool=tool, actual_child_returncode=supervision['actual_returncode'], pid=started['pid'], pgid=started['pgid'], direct_child_reaped=True, owned_group_empty=True, fresh_PID_and_PGID_absent=True,
        root_GO_sha256=GO, supervision_sha256=sha(execution / 'execution-receipt.json'), sources_before_after_equal=True, merged_pins=len(pins), three_whole_object_and_stored_byte_inverses=True,
        all_outputs=outputs, output_count=len(outputs), total_output_bytes=sum(row['bytes'] for row in outputs.values()), evidence=evidence, timeout=supervision['timeout'], signals=supervision['signals_to_owned_group_only'], cleanup_error=supervision['cleanup_error'],
        supervised_elapsed_seconds=supervision['elapsed_seconds'], candidate_qualified=False, master_replaced=False, old_complete7_law_proof_transferred=False, no_downstream_scientific_run=True, collection_elapsed_seconds=time.monotonic()-began)

if __name__ == '__main__':
    result = collect()
    target = H / 'terminal-collection.json'
    with target.open('xb') as stream: stream.write(encoded(result)); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(dict(status=result['status'], actual_child_returncode=result['actual_child_returncode'], terminal_sha256=sha(target), outputs=result['output_count'], merged_pins=result['merged_pins'], evidence=result['evidence'].get('complete_measurements_before_gates'), failure=result['evidence'].get('failure'))))
