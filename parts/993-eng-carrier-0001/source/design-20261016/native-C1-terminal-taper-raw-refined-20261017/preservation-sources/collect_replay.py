"""Collect the closed one-restoration replay; no numerical function is rerun."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


pending = read('pending-replay-launch.json')
launch = read('replay-launch.json')
command = read('replay-command.json')
old_command = read('pending-replay-command.json')
assert sha(HERE / 'pending-replay-launch.json') == '7e608317c81744711e247b976c3e7aaa2cec52dbbeb2a597fe7ce0bf084b5616'
assert sha(HERE / 'pending-replay-command.json') == '7cdceb07f2974681527810def1f88014fa962cd1fbfe123fc2389ee7df6332dc'
assert sha(ROOT / launch['root_GO']) == launch['root_GO_sha256'] == '0f91a0a2035001bab66fccc062e461d85e7bd34129d2b1c31ad9574e6569251c'
go = read('root-replay-GO-001.json')
assert all(sha(HERE / name) == digest for name, digest in go['closed_inputs_sha256'].items())
inverse = copy.deepcopy(launch)
assert inverse['inputs_sha256'].pop(launch['root_GO']) == launch['root_GO_sha256']
for key in ['status', 'launch_ready', 'root_GO', 'root_GO_sha256']:
    inverse[key] = pending[key]
assert inverse == pending
inverse_command = copy.deepcopy(command)
for key in ['status', 'launch_ready', 'ROOT_GO']:
    inverse_command[key] = old_command[key]
inverse_command['argv_template'][6] = old_command['argv_template'][6]
assert inverse_command == old_command
assert command['argv_template'][6] == sha(HERE / 'replay-launch.json')
merged = {}
for field in ['inputs_sha256', 'source_sha256']:
    for name, digest in launch[field].items():
        assert name not in merged or merged[name] == digest
        merged[name] = digest
assert len(merged) == 613 and all(sha(ROOT / name) == digest for name, digest in merged.items())
supervision = read('analysis-execution-001/execution-receipt.json')
assert supervision['actual_returncode'] == 0 and supervision['direct_child_reaped'] is True
assert supervision['no_non_zombie_group_members'] is True and supervision['final_group_members'] == []
assert supervision['failure'] is None and supervision['cleanup_error'] is None
assert supervision['timeout'] is False and supervision['interrupted'] is False
assert supervision['signals_to_owned_group_only'] == []
assert supervision['sources_before'] == supervision['sources_after'] == merged
assert supervision['sources_and_plan_unchanged'] is True
assert supervision['plan_sha256'] == sha(HERE / 'replay-launch.json')
assert supervision['command'] == launch['command']
assert supervision['total_wall_budget_seconds'] == 180 and supervision['cleanup_grace_seconds'] == [10, 10]
assert launch['inner_alarm_seconds'] == 150 and launch['inner_CPU_limit_seconds'] == [140, 141]
receipt = read('analysis-replay-001/reanalysis-receipt.json')
assert read('analysis-execution-001/stdout.log') == receipt
assert (HERE / 'analysis-execution-001/stderr.log').read_bytes() == b''
assert receipt['status'] == 'two_actual_raw_refined_taper_cases_reanalysed_entire_results_and_bytes_equal'
assert receipt['actual_returncode'] == 0 and receipt['runtime_unchanged'] is True
assert receipt['restored_inputs_unchanged'] is True and receipt['runtime_files'] == 500
assert receipt['cwd'] == '/' and receipt['actual_workers'] == 0
assert receipt['new_solver_run'] is False and receipt['new_mesh'] is False
assert receipt['stress_convergence_established'] is False
assert receipt['inner_wall_seconds'] == 150 and receipt['CPU_limit_seconds'] == [140, 141]
manifest = read('capsule-001/manifest.json')
assert receipt['capsule_manifest_sha256'] == sha(HERE / 'capsule-001/manifest.json') == launch['capsule_manifest_sha256']
assert manifest['candidate_qualified'] is False and manifest['h2_qualified'] is False
assert manifest['strict_H2_volume_refusal_preserved'] is True and manifest['law_original_RC1_preserved'] is True
assert manifest['STEP_exchange_qualified'] is False
members = dict(manifest['dependency']['members'])
for archive in manifest['archives'].values():
    for name, row in archive['members'].items():
        assert name not in members
        members[name] = row
assert len(members) == 696
restored = HERE / 'analysis-replay-001/restored'
actual_paths = {str(path.relative_to(restored)) for path in restored.rglob('*') if path.is_file()}
assert actual_paths == set(members)
assert not any(path.is_symlink() for path in restored.rglob('*'))
for name, row in members.items():
    assert (restored / name).stat().st_size == row['bytes'] and sha(restored / name) == row['sha256']
comparisons = []
assert len(manifest['cases']) == len(receipt['cases']) == 2
for case, actual_case in zip(manifest['cases'], receipt['cases']):
    assert actual_case['case'] == case['name'] and actual_case['VM_MPa'] == case['expected_VM_MPa']
    assert actual_case['element_id'] == 89539 and actual_case['IP_one_based'] == 2
    assert actual_case['energy_result_entirely_equal'] is True and actual_case['peak_result_entirely_equal'] is True
    assert actual_case['relative_energy_error'] <= actual_case['tolerance'] == 1e-4
    for key, old in [('energy', 'energy-audit.json'), ('peak', 'global-peaks.json')]:
        current = HERE / 'analysis-replay-001' / (case['key'] + '-' + key + '.json')
        original = restored / case['root'] / old
        assert json.loads(current.read_text()) == json.loads(original.read_text())
        assert current.read_bytes() == original.read_bytes() and sha(current) == sha(original)
        comparisons.append(dict(case=case['key'], report=key, entire_object_equal=True,
                                serialized_bytes_equal=True, sha256=sha(current)))
assert len(comparisons) == 4
for name, digest in supervision['logs_sha256'].items():
    assert sha(HERE / 'analysis-execution-001' / name) == digest
query = subprocess.run(['/bin/ps', '-g', str(supervision['pid']), '-o', 'pid=,ppid=,pgid=,stat='],
                       capture_output=True, text=True, timeout=10)
assert query.returncode == 1 and query.stdout == '' and query.stderr == ''
paths = ['analysis-replay-001/restored/' + name for name in sorted(members)]
paths += ['analysis-replay-001/' + name for name in ['rigid-energy.json', 'rigid-peak.json', 'spring-energy.json', 'spring-peak.json', 'reanalysis-receipt.json']]
paths += ['analysis-execution-001/' + name for name in ['started.json', 'stdout.log', 'stderr.log', 'execution-receipt.json']]
assert len(paths) == 705
report = dict(schema='dependent-rawfine-one-analysis-replay-terminal-1',
              status='closed_actual_RC0_one696_restore_four_entire_reports_and_serialized_bytes_equal',
              actual_tool_handle=26475, actual_initial_chunk='66e287', actual_terminal_chunk='648ba0',
              actual_tool_returncode=0, actual_child_returncode=0,
              owned_PID=supervision['pid'], direct_child_reaped=True, owned_group_empty=True,
              fresh_group_query=dict(returncode=query.returncode, stdout=query.stdout, stderr=query.stderr),
              elapsed_seconds=supervision['elapsed_seconds'], reanalysis_receipt=receipt,
              actual_manifest_sha256=launch['capsule_manifest_sha256'],
              source_pins_current_and_before_after_equal=613, runtime_files_before_after=500,
              whole_two_pending_inverses_equal=True, restored_original_paths=696,
              all_restored_originals_entire_bytes_equal=True, complete_report_comparisons=comparisons,
              whole_outputs={name: dict(bytes=(HERE / name).stat().st_size, sha256=sha(HERE / name)) for name in paths},
              no_repeated_numerical_analysis_or_decompression_during_collection=True,
              original_volume_law_STEP_refusals_retained=True,
              native_solver_CAD_mesh_or_publication=False, collector_source_sha256=sha(Path(__file__)))
with (HERE / 'replay-terminal-collection-001.json').open('x') as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps(dict(status=report['status'], restored_members=696, whole_outputs=len(paths),
                      terminal_sha256=sha(HERE / 'replay-terminal-collection-001.json')), sort_keys=True))
