"""Eight exact retained opening points on two full surfaces; no interface map."""
import argparse
import hashlib
import importlib
import json
import math
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve(); PREP = HERE.parent
SOURCE = ROOT/'twins/962-cylinder-head-f0/source'
OLD = ROOT/'twins/962-cylinder-head-f0/engineering/analysis-quality-features-contract.json'
ORIGINAL = 'work/962-engineering/analysis-envelope-025-003/exact-input.bin'
CANDIDATE = 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/candidate.bin'
OUTPUT = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-openings-001'
RESOURCES = dict(rss_stop_bytes=4294967296, rss_poll_seconds=.1,
    process_group_deadline_seconds=120, thread_environment_limit=2,
    hard_address_space_quota=False, OS_CPU_quota=False)
QUALIFICATION = dict(complete_semantic_feature_map=False, feature_channel_BCC_review_complete=False,
    candidate_metal_wall_clearance_qualified=False, conformal_metal_fluid_interface_validated=False,
    solver_admission_established=False, engineering_accepted=False, manufacturing_authorized=False)
ORDERED_ARRAY_SHA256 = {'original': ['f6aee40320646d34212929551866b111093ab25d81d78d68e48b95e1f8f78ad7', '9318ffffd6b46c1daa3f35169071eb3ad815171848fc3d48778b8373a2ea5341'], 'candidate': ['e0009dc6c5481cb77383b91a6e72ee4f223f207917b345e74f0b5b8e65ca6786', '152dc93bc9d5ea98aa2ec88271b0385471c466a29259c0f874ccfcf81c5ea9bd']}
FIXED = {
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/manifest.json': '53f94089eea095020ff9c9692a2a530b43ba37a96b2a6e30e2e23ee21d690a84',
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-result-peer-001/review.json': '4498c149823907ddd46830f7dc582dc65b935d39f25b2b5053393eb34770c0ca',
    'work/962-engineering/atomic-cavity-plane-clip-cap-census-001/readback-report.json': 'f246f1ef38a7657bd9eefc2349391cb31ab4a2147656743bb99c790c12d52a7d',
    'work/962-engineering/atomic-cavity-plane-clip-cap-census-result-peer-001/review.json': 'fa5b363375236fb24ba8c9382bcf61da44ca39b63549a96ab0bd7b559a1b57c3',
    'work/962-engineering/atomic-cavity-plane-clip-readback-prep-001/run_readback.py': 'e0e63b01708584d0296757df8aaea89c5238bc352109a716a7abed49defa3d97',
    ORIGINAL: '894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95',
    CANDIDATE: '9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4',
    str(OLD.relative_to(ROOT)): '692daf068bf96c8236cab96c8959b33858f6cbf8319f31083daac713164dae29',
    'work/962-engineering/quality-patch-features-001/worker-report.json': 'bb99c186083869fa792228ad2095066abcca60c652112118999edb3c9265e72d',
    'twins/962-cylinder-head-f0/derived/family/bore-95-report.json': '5dc2c44ec6978cee9ea9bbd80c392227b68c3e13c0915e7f20e562cb489c7efb',
    'twins/962-cylinder-head-f0/source/audit_quality_features.py': '4e6eb1358c1687fabe78ca95958fb9e4c1724537abe2718414bfe46834f4ceb4',
    'twins/962-cylinder-head-f0/source/audit_quality_head.py': 'a298270aa00b1536314a07629b935500c68883ca0d3bd1a179d71b49a8e73991',
    'twins/962-cylinder-head-f0/source/audit_quality_patch.py': '3532a172b2bce3a8ead7c8b11b712a2b55891377726fa1b6d847e84f0eed3912',
    'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5',
    'twins/962-cylinder-head-f0/source/prepare_head_analysis.py': 'cda8f7155a8c22ab66898f07d1ad452ba5384ad7f75a1f012606685cd8a12dc3',
    'twins/962-cylinder-head-f0/source/run_quality_distance_002.py': '6aeb8be558054b6cb4e8d1b7904adfe17d57b0c11d17a134cbe574a8cafa085c',
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


def load_contract(path, expected):
    if digest(path) != expected:
        raise ValueError('Exact reviewed opening-probe child required')
    c = json.loads(path.read_text()); required = dict(FIXED)
    for p in (HERE, PREP/'run_openings.py', PREP/'METHOD.md', PREP/'source-reuse.json',
              PREP/'array-byte-bindings.json', PREP/'preparation-checks.json'):
        required[str(p.relative_to(ROOT))] = digest(p)
    for name, sha in c.get('execution_reviews', {}).items():
        if name in required:
            raise ValueError('Review must not replace prepared input')
        required[name] = sha
    if (c.get('schema') != '962-atomic-eight-openings-child/v1'
            or c.get('root_authorized') is not True or c.get('root_and_peer_review_complete') is not True
            or c.get('resources') != RESOURCES or c.get('qualification') != QUALIFICATION
            or c.get('input_hashes') != required or c.get('original') != ORIGINAL
            or c.get('candidate') != CANDIDATE or c.get('output') != str(OUTPUT.relative_to(ROOT))
            or c.get('expected_counts') != {'original': [902145, 1804706], 'candidate': [871731, 1743878]}
            or c.get('ordered_array_sha256') != ORDERED_ARRAY_SHA256
            or c.get('automatic_retry') is not False):
        raise ValueError('Frozen exact full surfaces, source, scope and controls required')
    for name, sha in required.items():
        p = Path(name)
        if (p.is_absolute() or '..' in p.parts or not (ROOT/p).resolve().is_relative_to(ROOT)
                or not (ROOT/p).is_file() or (ROOT/p).is_symlink() or digest(ROOT/p) != sha):
            raise ValueError('Bound opening-probe input changed: '+name)
    old = json.loads(OLD.read_text())
    prior = json.loads((ROOT/'work/962-engineering/quality-patch-features-001/worker-report.json').read_text())
    if (c['interpreter'] != old['interpreter'] or c['interpreter_sha256'] != old['interpreter_sha256']
            or digest(Path(c['interpreter']).resolve()) != old['interpreter_sha256']
            or c['runtime'] != old['runtime'] or c['opening_points_mm'] != old['opening_points_mm']
            or len(c['opening_points_mm']) != 8 or c['fixture_absolute_bound_mm'] != 1e-12
            or c['retained_unit_tetra_fixture'] != prior['known_tetrahedron_distance_fixture']):
        raise ValueError('Exact old approved interpreter/VTK/points/fixture bound required')
    return c


def worker(path, expected, output):
    c = load_contract(path, expected)
    allowed = {'frozen-contract.json', 'controller-executed.py', 'worker-executed.py',
               'source-snapshots', 'running-receipt.json', 'native.log'}
    if (output.resolve() != OUTPUT.resolve() or {p.name for p in output.iterdir()} != allowed
            or digest(output/'frozen-contract.json') != expected
            or digest(output/'worker-executed.py') != digest(HERE)):
        raise ValueError('Fresh exact controller-owned opening audit required')
    save(output/'worker-claimed.json', dict(source_sha256=digest(HERE), contract_sha256=expected))
    signal.alarm(120); started = time.monotonic()
    report = dict(status='running', opening_subgate_passed=False, qualification=QUALIFICATION,
                  source_sha256=digest(HERE), contract_sha256=expected)
    try:
        sys.path.insert(0, str(SOURCE))
        import numpy as np
        from audit_quality_features import distance
        from prepare_head_analysis import polydata
        from audit_quality_head import read
        from mesh_head import array_sha
        from vtkmodules.vtkCommonCore import vtkVersion, vtkMultiThreader, vtkSMPTools
        from vtkmodules.util.numpy_support import vtk_to_numpy
        vtkMultiThreader.SetGlobalMaximumNumberOfThreads(2); vtkSMPTools.Initialize(2)
        runtime = dict(vtk_version=vtkVersion.GetVTKVersion(), module_hashes={
            n: digest(Path(importlib.import_module(n).__file__)) for n in c['runtime']['module_hashes']})
        if (runtime != c['runtime'] or digest(Path(sys.executable).resolve()) != c['interpreter_sha256']
                or vtkMultiThreader.GetGlobalMaximumNumberOfThreads() > 2
                or vtkSMPTools.GetEstimatedNumberOfThreads() > 2):
            raise ValueError('Pinned approved VTK/interpreter or thread cap changed')
        retained = json.loads((ROOT/'twins/962-cylinder-head-f0/derived/family/bore-95-report.json').read_text())
        if retained['dry_opening_probes_mm'] != c['opening_points_mm']:
            raise ValueError('All eight actual retained probe points required')
        tetra = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        tf = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)
        fn = distance(polydata(tetra, tf)); values = [float(fn.EvaluateFunction(x)) for x in ((.25, .25, .25), (2., 2., 2.))]
        oracle = [-.25/math.sqrt(3), 5/math.sqrt(3)]
        if any(not math.isfinite(a) or abs(a-b) > 1e-12 for a, b in zip(values, oracle)):
            raise ValueError('Unchanged known unit-tetra fixture failed')
        rows = []
        for label, name in [('original', ORIGINAL), ('candidate', CANDIDATE)]:
            p, f = read(ROOT/name); hashes = [array_sha(p), array_sha(f)]
            if hashes != c['ordered_array_sha256'][label]:
                raise ValueError('Complete ordered surface arrays changed')
            if [len(p), len(f)] != c['expected_counts'][label]:
                raise ValueError('Full surface count changed')
            poly = polydata(p, f); xyz = vtk_to_numpy(poly.GetPoints().GetData())
            faces = vtk_to_numpy(poly.GetPolys().GetConnectivityArray()).reshape(-1, 3)
            if (xyz.dtype != np.float64 or xyz.tobytes() != p.tobytes()
                    or not np.array_equal(faces, f) or faces.dtype.itemsize != 8):
                raise ValueError('Exact full indexed float64 VTK roundtrip failed')
            fn = distance(poly); signed = [float(fn.EvaluateFunction(point)) for point in c['opening_points_mm']]
            if not all(math.isfinite(v) and v > 0 for v in signed):
                raise ValueError('Retained opening point blocked or ambiguous: '+label)
            if hashes != [array_sha(p), array_sha(f)]:
                raise ValueError('Full input arrays changed during VTK query')
            rows.append(dict(surface=label, vertices=len(p), triangles=len(f), signed_distances_mm=signed,
                all_eight_strictly_outside_metal=True, exact_indexed_float64_roundtrip=True,
                array_sha256=hashes, source_sha256=digest(ROOT/name)))
            del fn, poly, xyz, faces, p, f
        report.update(status='eight_retained_opening_subgate_passed_only', opening_subgate_passed=True,
            runtime=runtime, opening_points_mm=c['opening_points_mm'], surfaces=rows,
            tetra_fixture=dict(observed=values, expected=oracle, absolute_error_bound_mm=1e-12),
            prior_retained_unit_tetra_fixture=c['retained_unit_tetra_fixture'],
            vtk_thread_controls=dict(global_maximum=vtkMultiThreader.GetGlobalMaximumNumberOfThreads(),
                SMP_estimate=vtkSMPTools.GetEstimatedNumberOfThreads(), hard_CPU_quota=False),
            no_equal_surface_count_assumption=True, candidate_metal_fluid_wall_clearance_proved=False)
    except Exception as exc:
        report.update(status='failed_or_rejected_opening_subgate', error=type(exc).__name__+': '+str(exc), opening_subgate_passed=False)
    finally:
        try:
            load_contract(path, expected)
            if report['opening_subgate_passed'] and any(
                    digest(Path(importlib.import_module(n).__file__)) != sha
                    for n, sha in c['runtime']['module_hashes'].items()):
                raise ValueError('Pinned VTK modules changed after probes')
            report['bound_inputs_unchanged'] = True
        except Exception:
            report.update(bound_inputs_unchanged=False, opening_subgate_passed=False)
        report['worker_wall_seconds'] = time.monotonic()-started
        save(output/'worker-report.json', report); signal.alarm(0)
    return 0 if report['opening_subgate_passed'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True); parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True); a = parser.parse_args()
    raise SystemExit(worker(a.contract.resolve(), a.contract_sha256, a.output))
