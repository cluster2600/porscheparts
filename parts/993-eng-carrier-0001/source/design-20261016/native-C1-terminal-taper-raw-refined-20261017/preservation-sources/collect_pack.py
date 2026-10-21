"""Collect the one closed pack; whole bytes only, no ZIP member decompression."""
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


plan = read('pending-pack-plan.json')
launch = read('pack-launch.json')
pending = read('pending-pack-launch.json')
command = read('pack-command.json')
old_command = read('pending-pack-command.json')
assert sha(HERE / 'pending-pack-plan.json') == '8d29dac989a4cf273497c99321d41cf18ac1f6478e189f31de4a0e3ef4ed4bc8'
assert sha(HERE / 'pending-pack-launch.json') == '003afa5dc18ba455a244b3f2339dbefb5790a2b50634f369f94e1fb859a7aef0'
assert sha(HERE / 'pending-pack-command.json') == '3f20ebf79ca494e49cbc89adba70dad6f4b4786588997155f994eacdc7e65e58'
inverse = copy.deepcopy(launch)
assert inverse['inputs_sha256'].pop(launch['root_GO']) == launch['root_GO_sha256']
for key in ['status', 'launch_ready', 'root_GO', 'root_GO_sha256']:
    inverse[key] = pending[key]
assert inverse == pending
inverse_command = copy.deepcopy(command)
for key in ['status', 'launch_ready']:
    inverse_command[key] = old_command[key]
inverse_command['argv_template'][6] = old_command['argv_template'][6]
assert inverse_command == old_command
assert command['argv_template'][6] == sha(HERE / 'pack-launch.json')
assert command['argv_template'][4] == str(HERE / 'pack-launch.json')
assert launch['command'][-1] == sha(HERE / 'pending-pack-plan.json')
merged = {}
for name in ['inputs_sha256', 'source_sha256']:
    for path, digest in launch[name].items():
        assert path not in merged or merged[path] == digest
        merged[path] = digest
assert len(merged) == 219
assert all(sha(ROOT / path) == digest for path, digest in merged.items())
supervision = read('pack-execution-001/execution-receipt.json')
assert supervision['actual_returncode'] == 0
assert supervision['direct_child_reaped'] is True
assert supervision['no_non_zombie_group_members'] is True
assert supervision['final_group_members'] == []
assert supervision['timeout'] is False and supervision['interrupted'] is False
assert supervision['failure'] is None and supervision['cleanup_error'] is None
assert supervision['sources_before'] == supervision['sources_after'] == merged
assert supervision['sources_and_plan_unchanged'] is True
assert supervision['plan_sha256'] == sha(HERE / 'pack-launch.json')
assert supervision['command'] == launch['command']
assert supervision['total_wall_budget_seconds'] == 200
assert supervision['cleanup_grace_seconds'] == [10, 10]
assert supervision['signals_to_owned_group_only'] == []
pack = read('packaging.json')
assert pack['status'] == 'three_deterministic_archives_created_no_solver'
assert pack['originals_unchanged'] is True and pack['original_bytes'] == 361205127
assert pack['plan_sha256'] == sha(HERE / 'pending-pack-plan.json')
assert pack['source_sha256'] == '697277ea5c4ccc10cec323f6815409e4d948726f55b52045c17d1be99bfa1a9a'
assert pack['new_solver_run'] is False and pack['actual_workers'] == 0
assert set(pack['archives']) == set(plan['archives'])
assert {p.name for p in (HERE / 'archives').iterdir()} == set(pack['archives'])
archives = {}
for name, row in pack['archives'].items():
    path = HERE / 'archives' / name
    assert not path.is_symlink() and path.is_file()
    assert row['members'] == plan['archives'][name]
    assert row['bytes'] == path.stat().st_size < 100000000
    assert row['sha256'] == sha(path)
    archives[name] = dict(bytes=row['bytes'], sha256=row['sha256'], members=len(row['members']))
assert sum(row['members'] for row in archives.values()) == 201
assert all(sha(ROOT / path) == row['sha256'] for rows in plan['archives'].values() for path, row in rows.items())
for name, digest in supervision['logs_sha256'].items():
    assert sha(HERE / 'pack-execution-001' / name) == digest
query = subprocess.run(['/bin/ps', '-g', str(supervision['pid']), '-o', 'pid=,ppid=,pgid=,stat='],
                       capture_output=True, text=True, timeout=10)
assert query.returncode == 1 and query.stdout == '' and query.stderr == ''
paths = ['packaging.json', *['archives/' + name for name in sorted(archives)],
         *['pack-execution-001/' + name for name in ['started.json', 'stdout.log', 'stderr.log', 'execution-receipt.json']]]
report = dict(schema='raw-refined-taper-one-PACK-terminal-1',
              status='closed_actual_RC0_three_fixed_archives_created_only',
              actual_tool_handle=81033, actual_initial_chunk='b064a1', actual_terminal_chunk='8647e6',
              actual_tool_returncode=0, actual_child_returncode=supervision['actual_returncode'],
              direct_child_reaped=True, owned_group_empty=True,
              fresh_owned_group_query=dict(returncode=query.returncode, stdout=query.stdout, stderr=query.stderr),
              elapsed_seconds=supervision['elapsed_seconds'],
              pack_wall_seconds=pack['wall_seconds'], pack_CPU_seconds=pack['CPU_seconds'],
              pack_maxRSS_bytes=pack['maxRSS_bytes'],
              all219_source_inputs_before_after_and_current_equal=True,
              whole_two_pending_object_inverses=True, fixed_pack_plan_sha256=sha(HERE / 'pending-pack-plan.json'),
              archives=archives, original_members=201, original_raw_bytes=361205127,
              whole_outputs={name: dict(bytes=(HERE / name).stat().st_size, sha256=sha(HERE / name)) for name in paths},
              supervision_sha256=sha(HERE / 'pack-execution-001/execution-receipt.json'),
              packaging_sha256=sha(HERE / 'packaging.json'),
              original_refusals_preserved=True, child_nice10_once=True, parent_nice_modified=False,
              decompression_or_assembly_or_restore_or_replay_or_publication=False,
              collector_source_sha256=sha(Path(__file__)))
with (HERE / 'pack-terminal-collection-001.json').open('x') as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps(dict(status=report['status'], archives=archives,
                      terminal_sha256=sha(HERE / 'pack-terminal-collection-001.json')), sort_keys=True))
