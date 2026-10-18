"""One reviewed read-only audit through the frozen owned metadata/cleanup helper."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve()
PREP = HERE.parent
OUTPUT = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-topology-001'
CANDIDATE = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/candidate.bin'
IMAGE = 'sha256:3ccaf5701c7c9add59eda6e8db918106fc8d51f4c2ef5b148d8079262861c7e1'
META_SHA = 'a88477c47d406cea3761c324e1f6eb82dcb1c2b962698d7f328261c6cef2929b'
CORE_SHA = 'b214e1cece8dbf66be6071199cbdf1a8e22a2a59328888011de17492f923c86b'
LIMITS = dict(cpus=2, memory_bytes=4294967296, memory_swap_bytes=4294967296,
    swap_bytes=0, hard_wall_seconds=300, network='none', tmpfs_bytes=0)
GATES = dict(connected_components=1,
    closed_oriented_edge_manifold=True, vertex_manifold=True, positive_signed_volume=True,
    global_intersection_pairs=0, complete_pair_cap=100001, all_five_intersection_fixtures=True,
    one_two_component_fixtures=True, candidate_and_sources_unchanged=True)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def observed(pins):
    return {name: digest(ROOT/name) if (ROOT/name).is_file() and not (ROOT/name).is_symlink() else None
            for name in pins}


def validate(path, expected, output):
    if digest(path) != expected:
        raise ValueError('Exact reviewed execution child required')
    child = json.loads(path.read_text()); pins = child['input_sha256']
    if (child.get('schema') != '962-atomic-global-topology-intersection-child/v1'
            or child.get('root_authorized') is not True
            or child.get('root_and_peer_review_complete') is not True
            or child.get('image_id') != IMAGE or child.get('resources') != LIMITS
            or child.get('gates') != GATES or child.get('automatic_retry') is not False
            or child.get('expected_counts') != dict(vertices=871731, triangles=1743878)
            or child.get('candidate_sha256') != '9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4'
            or child.get('candidate') != str(CANDIDATE.relative_to(ROOT))
            or child.get('output') != str(OUTPUT.relative_to(ROOT))
            or not child.get('qualification') or any(v is not False for v in child['qualification'].values())):
        raise ValueError('Only one separately reviewed fixed audit is permitted')
    preparation = child['preparation']; prep_path = ROOT/preparation['path']
    if prep_path.resolve() != (PREP/'preparation-contract.json').resolve() or digest(prep_path) != preparation['sha256']:
        raise ValueError('Exact preparation required')
    prep = json.loads(prep_path.read_text())
    expected_pins = dict(prep['input_sha256']); expected_pins[preparation['path']] = preparation['sha256']
    for name, sha in child.get('execution_reviews', {}).items():
        if name in expected_pins:
            raise ValueError('Review pin must not replace a prepared input')
        expected_pins[name] = sha
    if pins != expected_pins:
        raise ValueError('Complete prepared source/input/review pin set required')
    for name in pins:
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or not (ROOT/p).resolve().is_relative_to(ROOT):
            raise ValueError('Only bound repository inputs permitted')
    for key in ('worker_sha256', 'worker_helper_sha256', 'pinned_intersection_runtime',
                'python_executable_sha256', 'point_array_sha256', 'face_array_sha256', 'qualification'):
        if child[key] != prep[key]:
            raise ValueError('Prepared worker/arrays/runtime changed')
    if (pins.get(str(HERE.relative_to(ROOT))) != digest(HERE)
            or pins.get(str(CANDIDATE.relative_to(ROOT))) != child['candidate_sha256']
            or observed(pins) != pins):
        raise ValueError('Bound inputs changed before output or imports')
    if output.resolve() != OUTPUT.resolve() or output.exists() or output.is_symlink():
        raise ValueError('Only the fixed fresh output is permitted')
    return child, pins


def run(path, expected, output):
    child, pins = validate(path, expected, output)
    meta_path = PREP/'run_finest_endpoint_metadata.py'; core_path = PREP/'run_finest_endpoint_preflight.py'
    if digest(meta_path) != META_SHA or digest(core_path) != CORE_SHA:
        raise ValueError('Frozen cleanup sources changed before isolated import')
    spec = importlib.util.spec_from_file_location('atomic_topology_owned_metadata', meta_path)
    metadata = importlib.util.module_from_spec(spec); spec.loader.exec_module(metadata)
    core = metadata.CORE
    if core.INSPECT != metadata.ORIGINAL_FORMAT:
        raise ValueError('Unexpected cleanup metadata state')
    output.mkdir(); (output/'frozen-execution-contract.json').write_bytes(path.read_bytes())
    (output/'controller-executed.py').write_bytes(HERE.read_bytes())
    sources = output/'source-snapshots'; sources.mkdir()
    for source in [HERE, PREP/'audit_atomic_topology.py', meta_path, core_path, *sorted((PREP/'worker-sources').glob('*.py'))]:
        (sources/source.name).write_bytes(source.read_bytes())
    owner = uuid.uuid4().hex; name = '962-atomic-topology-'+owner[:10]
    mounts = [(str(output.resolve()), '/out', True, 'bind'),
        (str(CANDIDATE.resolve()), '/bound/candidate.bin', False, 'bind'),
        (str((output/'frozen-execution-contract.json').resolve()), '/bound/contract.json', False, 'bind'),
        (str((PREP/'audit_atomic_topology.py').resolve()), '/bound/worker.py', False, 'bind'),
        (str((PREP/'worker-sources').resolve()), '/bound/twins/962-cylinder-head-f0/source', False, 'bind')]
    command = ['docker', 'create', '--name', name, '--label', 'io.962-finest.owner='+owner,
        '--network', 'none', '--read-only', '--cpus', '2', '--memory', '4294967296', '--memory-swap', '4294967296',
        '-e', 'OMP_NUM_THREADS=2', '-e', 'OPENBLAS_NUM_THREADS=2', '-e', 'MKL_NUM_THREADS=2', '-e', 'NUMEXPR_NUM_THREADS=2']
    for source, target, writable, _ in mounts:
        command += ['--mount', 'type=bind,src='+source+',dst='+target+('' if writable else ',readonly')]
    command += ['--entrypoint', '/usr/local/bin/python3', IMAGE, '-B', '/bound/worker.py', '--contract-sha256', expected]
    controls = dict(NanoCpus=2000000000, Memory=4294967296, MemorySwap=4294967296,
                    NetworkMode='none', ReadonlyRootfs=True, Tmpfs=None)
    before = observed(pins); old_image, old_inspect = core.IMAGE, core.INSPECT
    try:
        core.IMAGE, core.INSPECT = IMAGE, metadata.CORRECTED_FORMAT
        row = core.execute(command, name, owner, output, 'atomic-topology', 300, controls, mounts)
    finally:
        core.IMAGE, core.INSPECT = old_image, old_inspect
    after = observed(pins); report_path = output/'worker-report.json'
    report = json.loads(report_path.read_text()) if report_path.is_file() and not report_path.is_symlink() else None
    state = row['final_metadata']['State'] if row['final_metadata'] else {}
    unchanged = before == after == pins and digest(path) == expected
    passed = (not row['error'] and not row['cleanup_errors'] and row['attach_reaped']
        and row['owned_container_removed'] and row['attach_returncode'] == state.get('ExitCode') == 0
        and state.get('Running') is False and state.get('OOMKilled') is False and unchanged
        and report is not None and report.get('gate_passed') is True
        and report.get('topology_gate_passed') is True and report.get('bound_inputs_unchanged') is True
        and report.get('candidate_arrays_unchanged') is True)
    save(output/'receipt.json', dict(status='subgates_passed_no_admission' if passed else 'failed_or_rejected_outputs_preserved',
        original_child_sha256=expected, actual_before_sha256=before, actual_after_sha256=after,
        all_inputs_unchanged=unchanged, execution_sha256=digest(output/'atomic-topology.execution.json'),
        worker_report_sha256=digest(report_path) if report is not None else None,
        owned_helper_core_sha256=CORE_SHA, metadata_companion_sha256=META_SHA,
        isolated_image_and_optional_metadata_redirection_restored=core.IMAGE == old_image and core.INSPECT == old_inspect,
        artifact_sha256={str(p.relative_to(output)): digest(p) for p in output.rglob('*') if p.is_file()},
        qualification=child['qualification'], automatic_retry=False))
    return 0 if passed else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError('Controller terminated')))
    raise SystemExit(run(args.contract.resolve(), args.contract_sha256, args.output))
