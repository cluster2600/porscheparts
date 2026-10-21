"""One source-bound atomic candidate topology/intersection worker; no repair."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import signal
import sys
import time

CANDIDATE_SHA = '1f9dbd4cda61c7b58084479ebb165fb01280fa831752dc0da18517e548131b1a'
COUNTS = dict(vertices=901727, triangles=1803870)
SOURCE = Path('/bound/twins/962-cylinder-head-f0/source')
HELPERS = {
    'audit_quality_topology_002.py': 'd08c68348bd3cf511844c488f0165afc8814ab0851e434b4b79de48fdcf4f27f',
    'audit_envelope_surface.py': '5a4a6559702e48fc4d97bb3b71a050aa600645485443a4c1caf389456d77c0c0',
    'audit_quality_head.py': 'a298270aa00b1536314a07629b935500c68883ca0d3bd1a179d71b49a8e73991',
    'audit_quality_patch.py': '3532a172b2bce3a8ead7c8b11b712a2b55891377726fa1b6d847e84f0eed3912',
    'mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5',
    'prepare_head_analysis.py': 'cda8f7155a8c22ab66898f07d1ad452ba5384ad7f75a1f012606685cd8a12dc3',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def worker(expected):
    output = Path('/out'); contract_path = Path('/bound/contract.json')
    candidate = Path('/bound/candidate.bin')
    contract = json.loads(contract_path.read_text())
    allowed = {'frozen-execution-contract.json', 'controller-executed.py',
               'source-snapshots', 'atomic-topology.native.log'}
    if (digest(contract_path) != expected or contract['root_authorized'] is not True
            or contract['root_and_peer_review_complete'] is not True
            or {p.name for p in output.iterdir()} != allowed
            or digest(output/'frozen-execution-contract.json') != expected
            or contract['candidate_sha256'] != CANDIDATE_SHA
            or contract['expected_counts'] != COUNTS
            or contract['worker_helper_sha256'] != HELPERS
            or digest(Path(__file__)) != contract['worker_sha256']
            or any(value is not False for value in contract['qualification'].values())):
        raise ValueError('Fresh exact reviewed worker/contract/candidate required')
    def verify():
        return (digest(contract_path) == expected and digest(candidate) == CANDIDATE_SHA
                and all(digest(SOURCE/name) == sha for name, sha in HELPERS.items())
                and digest(Path(__file__)) == contract['worker_sha256'])
    if not verify():
        raise ValueError('Worker input/source drift before imports or claim')
    save(output/'worker-claimed.json', dict(source_sha256=digest(Path(__file__))))
    signal.alarm(300); start = time.monotonic()
    report = dict(status='running', gate_passed=False, topology_gate_passed=False,
        candidate_sha256=CANDIDATE_SHA, expected_counts=COUNTS,
        qualification=contract['qualification'], runtime={},
        exact_source_attribution='Unmodified 002 components/require_topology and envelope audit_intersections helpers; no retained legacy run/worker entrypoint called.')
    p = f = None; p_hash = f_hash = None
    try:
        sys.path.insert(0, str(SOURCE))
        import numpy as np
        import igl
        import igl.copyleft.cgal as cgal
        from audit_quality_topology_002 import components, require_topology
        from audit_envelope_surface import audit_intersections
        from audit_quality_head import read
        from mesh_head import array_sha
        from prepare_head_analysis import validate_surface
        runtime = dict(libigl_version=importlib.metadata.version('libigl'),
            cgal_wrapper_sha256=digest(Path(cgal.__file__)),
            igl_binary_modules={str(q.relative_to(Path(igl.__file__).parent)): digest(q)
                for q in Path(igl.__file__).parent.rglob('*.so')})
        if (runtime != contract['pinned_intersection_runtime'] or platform.machine() != 'aarch64'
                or np.__version__ != '2.2.6'
                or digest(Path(sys.executable).resolve()) != contract['python_executable_sha256']):
            raise ValueError('Pinned ARM64 Python/NumPy/libigl native runtime changed')
        report['runtime'].update(runtime, python=sys.version, numpy=np.__version__, machine=platform.machine())
        p, f = read(candidate); p, f = np.array(p, dtype=np.float64), np.array(f, dtype=np.int64)
        p_hash, f_hash = array_sha(p), array_sha(f)
        if (p_hash, f_hash) != (contract['point_array_sha256'], contract['face_array_sha256']):
            raise ValueError('Exact ordered candidate arrays changed')
        surface = validate_surface(p, f)
        if any(surface[key] != value for key, value in COUNTS.items()):
            raise ValueError('New atomic candidate counts changed')
        tetra = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)
        fixtures = [components(igl, tetra), components(igl, np.concatenate((tetra, tetra+4)))]
        if fixtures != [1, 2]:
            raise ValueError('Known component fixtures failed')
        count = components(igl, f)
        report.update(surface=surface, connected_components=count, component_fixture_results=fixtures)
        require_topology(surface, count); report['topology_gate_passed'] = True
        audit_intersections(report, p, f)
        report['status'] = 'topology_and_global_intersection_subgates_passed' if report['gate_passed'] else 'rejected_outputs_preserved'
    except Exception as exc:
        report.update(status='failed_or_rejected_outputs_preserved', error=type(exc).__name__+': '+str(exc), gate_passed=False)
    finally:
        try:
            report['bound_inputs_unchanged'] = verify()
        except Exception:
            report['bound_inputs_unchanged'] = False
        report['candidate_arrays_unchanged'] = (p_hash is not None and p_hash == array_sha(p) and f_hash == array_sha(f))
        if not report['bound_inputs_unchanged'] or not report['candidate_arrays_unchanged']:
            report.update(status='failed_bound_input_or_array_drift', gate_passed=False)
        report['wall_seconds'] = time.monotonic()-start
        save(output/'worker-report.json', report); signal.alarm(0)
    return 0 if report['gate_passed'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract-sha256', required=True)
    raise SystemExit(worker(parser.parse_args().contract_sha256))
