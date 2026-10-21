"""One separately reviewed CGAL distance phase, using preserved owned cleanup."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import signal
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve()
META = HERE.with_name('run_finest_endpoint_metadata.py')
META_SHA = 'bb1d006e6146918df8b566aea4d244c0c00b143587d30dc41dfb1da361a5e215'
if hashlib.sha256(META.read_bytes()).hexdigest() != META_SHA:
    raise ValueError('Frozen metadata source changed')
SPEC = importlib.util.spec_from_file_location('endpoint003_frozen_metadata', META)
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)
B = M.CORE
TEST = 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-controller-prep-001/test_cgal_controller.py'
PHASES = {'compile': (4294967296, 300, 1073741824, 1),
          'fixtures': (536870912, 60, 0, 4), 'head': (4294967296, 300, 0, 1)}


def snapshot(pins):
    observed = {}
    for name in pins:
        path = ROOT/name
        observed[name] = B.digest(path) if path.is_file() and not path.is_symlink() else None
    return observed


def validated_child(path, expected):
    if B.digest(path) != expected:
        raise ValueError('Exact separate execution child required')
    child = json.loads(path.read_text()); pins = child['input_sha256']
    if (child.get('root_authorized') is not True or child.get('root_and_peer_review_complete') is not True
            or child.get('phase') not in PHASES or child.get('image_id') != B.IMAGE
            or child.get('automatic_retry') is not False):
        raise ValueError('Reviewed fixed phase and immutable image required')
    memory, wall, tmpfs, count = PHASES[child['phase']]
    if child.get('limits') != dict(cpus=2, memory_bytes=memory, swap_bytes=0,
                                   hard_wall_seconds_each=wall, tmpfs_bytes=tmpfs, network='none'):
        raise ValueError('Declared phase controls changed')
    required = [str(HERE.relative_to(ROOT)), str(META.relative_to(ROOT)),
                str(M.BASE.relative_to(ROOT)), TEST, child['preparation']['path']]
    if (any(name not in pins for name in required)
            or pins[child['preparation']['path']] != child['preparation']['sha256']
            or len(child['jobs']) != count):
        raise ValueError('Complete source, test, preparation and fixed job count required')
    for name in pins:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or not (ROOT/path).resolve().is_relative_to(ROOT):
            raise ValueError('Only task repository inputs are permitted')
    labels = set()
    for job in child['jobs']:
        if not re.fullmatch('[a-z0-9-]+', job['label']) or job['label'] in labels:
            raise ValueError('Unique fixed job labels required')
        labels.add(job['label'])
        allowed = ['/usr/bin/c++'] if child['phase'] == 'compile' else ['/bounded-distance']
        if job['entrypoint'] not in allowed or any(not isinstance(x, str) for x in job['arguments']):
            raise ValueError('Reviewed direct native entrypoint/arguments required')
        if not job['expected_returncodes'] or any(type(rc) is not int or rc not in (0, 2) for rc in job['expected_returncodes']):
            raise ValueError('Only declared success or stagnation codes are permitted')
        for name, target in job['read_only_mounts'].items():
            if name not in pins or not target.startswith('/') or target.startswith('/out'):
                raise ValueError('Every immutable native mount must be hash-bound')
    return child, pins


def run(path, expected, output):
    child, pins = validated_child(path, expected)
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to(ROOT/'work/962-engineering'):
        raise ValueError('Fresh owned phase output required')
    before = snapshot(pins)
    if before != pins or B.digest(path) != expected or B.INSPECT != M.ORIGINAL_FORMAT:
        raise ValueError('Input drift refused before outputs or native launch')
    output.mkdir(parents=True); output = output.resolve()
    (output/'frozen-execution-contract.json').write_bytes(path.read_bytes())
    for source in [HERE, META, M.BASE]:
        (output/source.name).write_bytes(source.read_bytes())
    memory, wall, tmpfs, _ = PHASES[child['phase']]
    controls = dict(NanoCpus=2000000000, Memory=memory, MemorySwap=memory,
                    NetworkMode='none', ReadonlyRootfs=True,
                    Tmpfs={'/tmp': 'rw,size='+str(tmpfs)} if tmpfs else None)
    results = []; error = None
    B.INSPECT = M.CORRECTED_FORMAT
    try:
        for job in child['jobs']:
            if snapshot(pins) != pins or B.digest(path) != expected:
                raise ValueError('Input drift between phase jobs')
            previous = B.file_hashes(output); owner = uuid.uuid4().hex
            name = '962-patch-'+job['label']+'-'+owner[:10]
            mounts = [(str(output), '/out', True, 'bind')]+[
                (str((ROOT/n).resolve()), target, False, 'bind') for n, target in job['read_only_mounts'].items()]
            argv = ['docker', 'create', '--name', name, '--label', 'io.962-finest.owner='+owner,
                    '--network', 'none', '--read-only', '--cpus', '2', '--memory', str(memory), '--memory-swap', str(memory)]
            if tmpfs:
                argv += ['--tmpfs', '/tmp:rw,size='+str(tmpfs)]
            for source, target, writable, _ in mounts:
                argv += ['--mount', 'type=bind,src='+source+',dst='+target+('' if writable else ',readonly')]
            argv += ['--entrypoint', job['entrypoint'], B.IMAGE]+job['arguments']
            row = B.execute(argv, name, owner, output, job['label'], wall, controls, mounts)
            state = row['final_metadata']['State'] if row['final_metadata'] else {}
            preserved = all((output/n).is_file() and B.digest(output/n) == value for n, value in previous.items())
            good = (not row['error'] and not row['cleanup_errors'] and row['attach_reaped']
                    and row['owned_container_removed'] and row['attach_returncode'] in job['expected_returncodes']
                    and state.get('ExitCode') == row['attach_returncode'] and state.get('Running') is False
                    and state.get('OOMKilled') is False and preserved and snapshot(pins) == pins)
            results.append(dict(label=job['label'], execution_passed=good,
                                previous_artifacts_unchanged=preserved, returncode=row['attach_returncode']))
            if not good:
                break
            print(json.dumps(results[-1]), flush=True)
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
    finally:
        B.INSPECT = M.ORIGINAL_FORMAT
    after = snapshot(pins); unchanged = after == pins and B.digest(path) == expected
    finished = not error and unchanged and len(results) == len(child['jobs']) and all(r['execution_passed'] for r in results)
    B.save(output/'phase-summary.json', dict(schema='962-endpoint003-bounded-phase/v1', phase=child['phase'],
        procedural_phase_finished=finished, error=error, jobs=results, execution_contract_sha256=expected,
        actual_before_sha256=before, actual_after_sha256=after, all_inputs_unchanged=unchanged,
        artifact_sha256=B.file_hashes(output), metadata_source_sha256=META_SHA,
        cleanup_source_sha256=M.BASE_SHA, controller_sha256=B.digest(HERE),
        automatic_retry=False, numerical_fixture_acceptance_established=False,
        head_surface_admitted=False, solver_admission_established=False, manufacturing_authorized=False))
    return 0 if finished else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    def interrupt(signum, _frame):
        raise InterruptedError('Controller signal '+str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(run(args.contract.resolve(), args.contract_sha256, args.output))
