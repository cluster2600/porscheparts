"""Collect one existing verifier run without repeating ZIP decompression."""
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


pending = read('pending-verify-launch.json')
launch = read('verify-launch.json')
command = read('verify-command.json')
old_command = read('pending-verify-command.json')
assert sha(HERE / 'pending-verify-launch.json') == 'c06a0a7420a68c0545ac83213070ecbafde59013184d8c348b7cfe4c85acf8ea'
assert sha(HERE / 'pending-verify-command.json') == '564b0e31f918368cd9dd13f4df676fb8afcf65992551a5e8e02a05b33db995cd'
assert sha(ROOT / launch['root_GO']) == launch['root_GO_sha256'] == '86a8a9ba79a5a15a486825e7ffe988a6005b77ab41ab887432c27c3f050d2d7c'
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
assert command['argv_template'][6] == sha(HERE / 'verify-launch.json')
merged = {}
for field in ['inputs_sha256', 'source_sha256']:
    for name, digest in launch[field].items():
        assert name not in merged or merged[name] == digest
        merged[name] = digest
assert len(merged) == 113 and all(sha(ROOT / name) == digest for name, digest in merged.items())
supervision = read('verify-execution-001/execution-receipt.json')
assert supervision['actual_returncode'] == 0 and supervision['direct_child_reaped'] is True
assert supervision['no_non_zombie_group_members'] is True and supervision['final_group_members'] == []
assert supervision['failure'] is None and supervision['cleanup_error'] is None
assert supervision['timeout'] is False and supervision['interrupted'] is False
assert supervision['signals_to_owned_group_only'] == []
assert supervision['sources_before'] == supervision['sources_after'] == merged
assert supervision['sources_and_plan_unchanged'] is True
assert supervision['plan_sha256'] == sha(HERE / 'verify-launch.json')
assert supervision['command'] == launch['command']
assert supervision['total_wall_budget_seconds'] == 180 and supervision['cleanup_grace_seconds'] == [10, 10]
assert launch['inner_alarm_seconds'] is None and launch['inner_CPU_limit_seconds'] is None
stdout = read('verify-execution-001/stdout.log')
assert stdout == dict(status='all_archived_original_bytes_verified', archives=3,
                      files=696, inherited_C1_members=495, new_solver_run=False)
assert (HERE / 'verify-execution-001/stderr.log').read_bytes() == b''
assert not (ROOT / launch['output_directory']).exists()
assert sha(HERE / 'capsule-001/manifest.json') == launch['capsule_manifest_sha256'] == '367346c6d908fe03111f435c6c5d7f74cbf2f16c4ba6114e04aba11065da100d'
expected_paths = read('assembly-terminal-collection-001.json')['exact_capsule_pathset']
actual_paths = sorted(str(path.relative_to(HERE / 'capsule-001')) for path in (HERE / 'capsule-001').rglob('*') if path.is_file())
assert actual_paths == expected_paths and len(actual_paths) == 13
for name, digest in supervision['logs_sha256'].items():
    assert sha(HERE / 'verify-execution-001' / name) == digest
query = subprocess.run(['/bin/ps', '-g', str(supervision['pid']), '-o', 'pid=,ppid=,pgid=,stat='],
                       capture_output=True, text=True, timeout=10)
assert query.returncode == 1 and query.stdout == '' and query.stderr == ''
paths = ['verify-execution-001/' + name for name in ['started.json', 'stdout.log', 'stderr.log', 'execution-receipt.json']]
report = dict(schema='dependent-rawfine-stored-byte-verify-terminal-1',
              status='closed_actual_RC0_all696_original_member_stream_bytes_verified_without_restoration',
              actual_tool_handle=29240, actual_initial_chunk='64d793', actual_terminal_chunk='aa17aa',
              actual_tool_returncode=0, actual_child_returncode=supervision['actual_returncode'],
              owned_PID=supervision['pid'], direct_child_reaped=True, owned_group_empty=True,
              fresh_group_query=dict(returncode=query.returncode, stdout=query.stdout, stderr=query.stderr),
              elapsed_seconds=supervision['elapsed_seconds'],
              source_pins_current_and_before_after_equal=113, whole_two_pending_inverses_equal=True,
              actual_manifest_sha256=launch['capsule_manifest_sha256'],
              actual_assembly_ROOT_sha256=launch['actual_assembly_ROOT_sha256'],
              verification_stdout_entire_object=stdout, reserved_output_still_absent=True,
              all13_original_capsule_paths_and_bytes_unchanged=True,
              whole_execution_files={name: dict(bytes=(HERE / name).stat().st_size, sha256=sha(HERE / name)) for name in paths},
              restored_or_reanalysed_or_native_or_published=False,
              original_volume_law_STEP_refusals_unchanged=True,
              no_repeated_decompression_during_collection=True, collector_source_sha256=sha(Path(__file__)))
with (HERE / 'verify-terminal-collection-001.json').open('x') as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps(dict(status=report['status'], original_members=696,
                      terminal_sha256=sha(HERE / 'verify-terminal-collection-001.json')), sort_keys=True))
