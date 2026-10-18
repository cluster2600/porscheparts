"""Collect exact local-I/O assembly bytes; no ZIP member access or analysis."""
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


assert sha(HERE / 'root-assembly-GO-001.json') == 'ac31ba87312e870f1ff706127cc07ef8090bf2ffa9f39a2208e332c861ba850d'
assert sha(HERE / 'root-pack-terminal-review-001.json') == 'a7fe97064b24e9c28789518486bd8966eb2ce38bc7961374f47ce0400b33a5bc'
assert (HERE / 'pack-plan.json').read_bytes() == (HERE / 'pending-pack-plan.json').read_bytes()
actual = read('assembly-execution-001/actual-child.json')
command = read('assembly-command.json')
pending = read('pending-assembly-proposal.json')
assert actual['actual_child_returncode'] == 0 and actual['direct_child_reaped'] is True
assert actual['timeout'] is False and actual['owned_signals'] == []
assert actual['argv'] == command['argv'] == pending['argv']
assert actual['command_sha256'] == sha(HERE / 'assembly-command.json')
assert actual['fresh_group_query'] == dict(returncode=1, stdout='', stderr='')
receipt = read('assembly.json')
manifest = read('capsule-001/manifest.json')
template = read('manifest-template.json')
pack = read('packaging.json')
assert receipt['status'] == 'actual_delta_archives_and_sources_copied_no_reanalysis'
assert receipt['manifest_sha256'] == sha(HERE / 'capsule-001/manifest.json')
assert receipt['packaging_sha256'] == sha(HERE / 'packaging.json')
assert receipt['inherited_taper_members'] == 495 and receipt['new_raw_refined_members'] == 201
assert receipt['new_solver_run'] is False and receipt['numerical_replay'] is False
inverse = copy.deepcopy(manifest)
for key in ['archives', 'files_sha256']:
    inverse[key] = template[key]
assert inverse == template
assert manifest['archives'] == pack['archives']
expected_paths = {*manifest['archives'], *manifest['files_sha256'], 'manifest.json'}
files = {str(path.relative_to(HERE / 'capsule-001')) for path in (HERE / 'capsule-001').rglob('*') if path.is_file()}
assert files == expected_paths and len(files) == 13
assert not any(path.is_symlink() for path in (HERE / 'capsule-001').rglob('*'))
for name, digest in manifest['files_sha256'].items():
    assert sha(HERE / 'capsule-001' / name) == digest
for name, row in manifest['archives'].items():
    original = HERE / 'archives' / name
    copied = HERE / 'capsule-001' / name
    assert original.stat().st_size == copied.stat().st_size == row['bytes'] < 100000000
    assert sha(original) == sha(copied) == row['sha256']
for name, row in template['utility_sources'].items():
    assert sha(ROOT / row['source']) == sha(HERE / 'capsule-001' / name) == row['sha256']
merged = {}
for field in ['inputs_sha256', 'source_sha256']:
    for name, digest in read('pack-launch.json')[field].items():
        assert name not in merged or merged[name] == digest
        merged[name] = digest
assert len(merged) == 219 and all(sha(ROOT / name) == digest for name, digest in merged.items())
query = subprocess.run(['/bin/ps', '-g', str(actual['owned_PID']), '-o', 'pid=,ppid=,pgid=,stat='],
                       capture_output=True, text=True, timeout=10)
assert query.returncode == 1 and query.stdout == '' and query.stderr == ''
outputs = ['assembly.json', *['capsule-001/' + name for name in sorted(files)],
           *['assembly-execution-001/' + name for name in ['started.json', 'stdout.log', 'stderr.log', 'actual-child.json']]]
report = dict(schema='rawfine-one-exact-IO-assembly-terminal-1',
              status='closed_actual_RC0_exact13_file_capsule_assembled_no_verification_or_analysis',
              actual_tool_chunk='f66112', actual_tool_returncode=0, actual_child_returncode=0,
              owned_PID=actual['owned_PID'], direct_child_reaped=True, owned_group_empty=True,
              fresh_group_query=dict(returncode=query.returncode, stdout=query.stdout, stderr=query.stderr),
              elapsed_seconds=actual['elapsed_seconds'], timeout=False,
              ROOT_GO_sha256=sha(HERE / 'root-assembly-GO-001.json'),
              ROOT_pack_terminal_review_sha256=sha(HERE / 'root-pack-terminal-review-001.json'),
              assembly_command_sha256=sha(HERE / 'assembly-command.json'),
              manifest_sha256=receipt['manifest_sha256'], packaging_sha256=sha(HERE / 'packaging.json'),
              whole_template_inverse_equal=True, exclusive_plan_copy_entire_bytes_equal=True,
              exact_capsule_pathset=sorted(files), original219_pack_inputs_and_original3ZIPs_unchanged=True,
              whole_outputs={name: dict(bytes=(HERE / name).stat().st_size, sha256=sha(HERE / name)) for name in outputs},
              decompression_stored_verification_restore_analysis_native_or_publication=False,
              original_refusals_retained=True, collector_source_sha256=sha(Path(__file__)))
with (HERE / 'assembly-terminal-collection-001.json').open('x') as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps(dict(status=report['status'], capsule_files=len(files),
                      manifest_sha256=report['manifest_sha256'],
                      terminal_sha256=sha(HERE / 'assembly-terminal-collection-001.json')), sort_keys=True))
