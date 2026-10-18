"""Retain all six v5 gates; replay their exact units in four bounded workers."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

from admitted_regions import sha
from compact_json import dumps
import parallel_exact_admissions as parallel

SOURCE = Path(__file__).resolve().parent
BASE = SOURCE/'build_cached_v5.py'
BASE_SHA256 = parallel.ENGINE_SHA256
PARALLEL_PATH = SOURCE/'parallel_exact_admissions.py'
PARALLEL_SHA256 = 'c21938ed27aa973596dc603f758ab3c6bc6796ee8c92dfd48ffe83c8ba2fe5bf'
if Path(parallel.__file__).resolve() != PARALLEL_PATH or sha(BASE) != BASE_SHA256:
    raise ValueError('The private v5 builder or parallel module path differs')
_spec = importlib.util.spec_from_file_location('_carrier_cached_builder_v6_base', BASE)
_v5 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_v5)
POLICY_FILES = (*_v5.POLICY_FILES, Path(__file__).resolve(), PARALLEL_PATH, parallel.AREA)
POLICY_SHA256 = {**_v5.POLICY_SHA256, POLICY_FILES[-3]:sha(__file__),
    PARALLEL_PATH:PARALLEL_SHA256, parallel.AREA:parallel.AREA_SHA256}
KEYS, SCHEMA, STRATEGY = _v5.KEYS, _v5.SCHEMA, _v5.STRATEGY
RUNTIME_HOOKS = copy.deepcopy(_v5.RUNTIME_HOOKS)
RUNTIME_HOOKS['parallel_exact_unit_admissions'] = dict(source=Path(__file__).name,
    sha256=sha(__file__), helper_sha256=PARALLEL_SHA256, workers=4, maximum_pending_futures=8,
    parent_seal_source_sha256=_v5.ADMISSION_SHA256, exact_dispatch_source_sha256=BASE_SHA256,
    replay_assembly_source_sha256=parallel.AREA_SHA256,
    assembly_operation='Reuse the same exact cycle areas after boundary reordering',
    optional_reviewed_four_unit_receipt_sha256=parallel.PROOF_SHA256,
    reviewed_results_assembly_source_sha256=_v5.INDEX_SHA256)
_v5.POLICY_SHA256.update(POLICY_SHA256)
_v5.RUNTIME_HOOKS = RUNTIME_HOOKS
_prepared = _v5._prepared_regions
_seal = _v5.seal
ACTIVE = None
REPLAY_NAME = 'exact-admission-replays.json'
PROOF_NAMES = ('exact-unit-proof-assessment.json', 'exact-unit-proof-plan.json', 'exact-unit-proof-runtime.json')


def verify_sources():
    _v5.verify_sources()
    if any(sha(path) != digest for path,digest in POLICY_SHA256.items()):
        raise ValueError('The private parallel admission policy changed')


def prepared_regions(*args, **kwargs):
    prepared = _prepared(*args, **kwargs)
    if ACTIVE is None:
        raise ValueError('No private v6 build is active')
    ACTIVE['prepared'] = prepared
    return prepared


def _proven(prepared, path):
    if path is None:
        return None
    producers = {}
    for row in prepared.rows:
        if row['source_index'] in (3, 9):
            checkpoint = json.loads((row['_directory']/'region-checkpoint.json').read_text())
            producers[row['source_index']] = dict(checkpoint_sha256=row['checkpoint_sha256'],
                metadata_sha256=checkpoint['files_sha256']['geometry-assessment.json'],
                surface_sha256=checkpoint['files_sha256']['support.npz'])
    proven = parallel.FourProvenResults(path, producers, _v5)
    prepared.files.update(proven.files); prepared.verify()
    return proven


def _write(path, value):
    Path(path).write_text(dumps(value, indent=2, allow_nan=False)+'\n')


def seal(output, checkpoint, store):
    verify_sources()
    output = Path(output)
    prepared = ACTIVE['prepared']
    proven = _proven(prepared, ACTIVE['proven'])
    indices = [r['source_index'] for r in store.report['regions']]
    workers = parallel.ParallelExactAdmissions(indices, POLICY_SHA256, proven)
    original = _v5.admissions_v3._exact_support_units
    try:
        with workers:
            _v5.admissions_v3._exact_support_units = workers
            admission, admitted = _seal(output, checkpoint, store)
    except BaseException as error:
        _write(output/REPLAY_NAME, dict(workers.receipt(), status='failed',
            failure=type(error).__name__, message=str(error)))
        raise
    finally:
        _v5.admissions_v3._exact_support_units = original
    execution = dict(workers.receipt(), status='completed', source_indices=indices)
    execution['policy_sha256'] = {p.name:h for p,h in POLICY_SHA256.items()}
    files = {}
    if proven is not None:
        for name, (source, digest) in zip(PROOF_NAMES, proven.files.items()):
            target = output/name
            with target.open('xb') as stream: stream.write(source.read_bytes())
            if sha(target) != digest:
                raise ValueError('A copied reviewed exact-unit proof differs')
            files[name] = digest
    execution['reviewed_proof_files_sha256'] = files
    _write(output/REPLAY_NAME, execution)
    files[REPLAY_NAME] = sha(output/REPLAY_NAME)
    binding = dict(receipt=REPLAY_NAME, receipt_sha256=files[REPLAY_NAME], files_sha256=files)
    for item in admission.values():
        path = output/item['receipt']; receipt = json.loads(path.read_text())
        receipt['exact_unit_replays'] = binding
        _write(path, receipt); item['receipt_sha256'] = sha(path)
    checkpoint['exact_unit_replays'] = binding
    checkpoint['outputs_sha256'].update(files)
    _write(output/'support-stage.json', checkpoint)
    return admission, admitted


_v5._prepared_regions = prepared_regions
_v5._base.seal = seal


def verify_v6_stage(directory):
    """Check v5's six gates, plus every unit/result and the replay execution."""
    verify_sources()
    directory = Path(directory).resolve()
    checkpoint = _v5.verify_v3_stage(directory)
    binding = checkpoint.get('exact_unit_replays', {})
    files = binding.get('files_sha256', {})
    if (binding.get('receipt') != REPLAY_NAME or files.get(REPLAY_NAME) != binding.get('receipt_sha256') or
            set(files) not in ({REPLAY_NAME}, {REPLAY_NAME, *PROOF_NAMES})):
        raise ValueError('The v6 stage omits the exact-unit execution binding')
    for name, digest in files.items():
        path = directory/name
        if (path.is_symlink() or not path.is_file() or sha(path) != digest or
                checkpoint['outputs_sha256'].get(name) != digest):
            raise ValueError('The v6 exact-unit evidence identity differs')
    execution = json.loads((directory/REPLAY_NAME).read_text())
    runtime_sha256 = parallel.identity(parallel.runtime_identity())
    if (execution.get('schema') != 'bounded-exact-unit-replays-1' or execution.get('status') != 'completed' or
            execution.get('workers') != 4 or execution.get('maximum_pending_futures') != 8 or
            execution.get('worker_group_closed') is not True or
            execution.get('engine_source_sha256') != BASE_SHA256 or
            execution.get('replay_assembly_sha256') != parallel.AREA_SHA256 or
            execution.get('runtime_before_sha256') != runtime_sha256 or
            execution.get('runtime_after_sha256') != runtime_sha256 or
            execution.get('worker_runtime_identity_verified_at_initialisation') is not True or
            execution.get('policy_sha256') != {p.name:h for p,h in POLICY_SHA256.items()} or
            execution.get('reviewed_proof_files_sha256') != {n:h for n,h in files.items() if n != REPLAY_NAME}):
        raise ValueError('The v6 exact-unit execution contract differs')
    indices = execution['source_indices']
    if indices != [0,1,2,3,8,9,10] or [s['index'] for s in checkpoint['supports']] != list(range(7)):
        raise ValueError('The exact-unit execution omits required regions')
    expected, results = [], {}
    for support in checkpoint['supports']:
        for name, reconstruction, contacts in parallel.units(support):
            expected.append((indices[support['index']], name, parallel.identity(reconstruction),
                parallel.identity(contacts), reconstruction['vertical_contact_penetration_mm']))
    rows = execution['units']
    if [(r['source_index'],r['unit'],r['reconstruction_sha256'],r['contacts_sha256'],r['penetration_mm'])
            for r in rows] != expected:
        raise ValueError('The exact-unit execution omits or changes unit payloads')
    reviewed = {}
    if set(files) != {REPLAY_NAME}:
        for name, digest in zip(PROOF_NAMES, (parallel.PROOF_SHA256, parallel.PLAN_SHA256,
                '57f4ee2a89b15c65d46bfc034f3433e651320e05505518d593aaacb2ed63d119')):
            if files[name] != digest:
                raise ValueError('The four reviewed proof identities differ')
        reviewed = {r['id']:r for r in json.loads((directory/PROOF_NAMES[0]).read_text())['cases']}
        if parallel.identity(json.loads((directory/PROOF_NAMES[2]).read_text())) != runtime_sha256:
            raise ValueError('The reviewed results and current runtime differ')
    for row in rows:
        if row['origin'] not in {'exact_function_with_reused_exact_cycle_areas', 'reviewed_real_result_reused'}:
            raise ValueError('Unknown exact-unit execution origin')
        if row['origin'] == 'reviewed_real_result_reused' and (
                (row['source_index'], row['unit']) not in parallel.FIXED_UNITS or set(files) == {REPLAY_NAME}):
            raise ValueError('An unreviewed result cannot be reused')
        if row['origin'] == 'reviewed_real_result_reused':
            proof = reviewed[parallel.FIXED_UNITS[row['source_index'],row['unit']]]
            if (row['result_sha256'] != parallel.identity(proof['result']) or
                    row['reconstruction_sha256'] != proof['reconstruction_sha256'] or
                    row['contacts_sha256'] != proof['contacts_sha256'] or row['penetration_mm'] != .2):
                raise ValueError('A reused result differs from its reviewed exact proof')
        results[(row['source_index'],row['unit'])] = row['result_sha256']
    for key, item in checkpoint['admission'].items():
        receipt = json.loads((directory/item['receipt']).read_text())
        if receipt.get('exact_unit_replays') != binding:
            raise ValueError('A gate omits its exact-unit execution binding')
        if key in ('skins','grids','contacts','collisions'):
            actual = receipt.get('continuous_interval_exact_admissions', [])
            if [(indices[r['region']],r['unit'],parallel.identity(r['receipt'])) for r in actual] != [
                    (r['source_index'],r['unit'],r['result_sha256']) for r in rows]:
                raise ValueError('A gate changes an exact-unit replay result')
    return checkpoint


def _restore_execution(source, output, result, supports_only):
    """The immutable CORE copies files but rebuilds and shortens its checkpoint."""
    source, output = Path(source), Path(output)
    checkpoint = json.loads((source/'support-stage.json').read_text())
    binding = checkpoint['exact_unit_replays']
    target = json.loads((output/'support-stage.json').read_text())
    target['exact_unit_replays'] = binding
    target['outputs_sha256'].update(binding['files_sha256'])
    _write(output/'support-stage.json', target)
    if supports_only:
        result.update(target)
    else:
        result['outputs_sha256'].update(binding['files_sha256'])
        result['outputs_sha256']['support-stage.json'] = sha(output/'support-stage.json')
    return result


def build(input_path, output, envelopes, part_cache, expected_sha256=None, identity_receipt=None,
          solid_sheets=False, continuous_interfaces=False, region_checkpoints=None,
          supports_only=False, reuse_support_stage=None, proven_unit_replays=None):
    global ACTIVE
    verify_sources()
    if ACTIVE is not None:
        raise ValueError('A private v6 build is already active')
    if reuse_support_stage is not None:
        verify_v6_stage(reuse_support_stage)
        if proven_unit_replays is not None:
            raise ValueError('A reusable stage already binds its exact-unit results')
    ACTIVE = dict(proven=proven_unit_replays)
    try:
        result = _v5.build(input_path, output, envelopes, part_cache, expected_sha256, identity_receipt,
            solid_sheets, continuous_interfaces, region_checkpoints, supports_only, reuse_support_stage)
        source = reuse_support_stage if reuse_support_stage is not None else output if supports_only else Path(output).with_name(Path(output).name+'-supports')
        result = _restore_execution(source, output, result, supports_only)
        verify_v6_stage(output)
        result.update(runner_adapter_source_sha256=sha(__file__), parallel_admission_base_sha256=BASE_SHA256)
        _write(Path(output)/('support-stage.json' if supports_only else 'report.json'), result)
        verify_sources()
        return result
    finally:
        ACTIVE = None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path); parser.add_argument('output', type=Path)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument('--sha256'); identity.add_argument('--identity-receipt', type=Path)
    for name in ('envelopes', 'part-cache', 'region-checkpoints'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--supports-only', action='store_true')
    parser.add_argument('--reuse-support-stage', type=Path)
    parser.add_argument('--proven-unit-replays', type=Path)
    parser.add_argument('--solid-sheets', action='store_true'); parser.add_argument('--continuous-interfaces', action='store_true')
    args = parser.parse_args()
    report = build(args.input, args.output, args.envelopes, args.part_cache, args.sha256, args.identity_receipt,
        args.solid_sheets, args.continuous_interfaces, args.region_checkpoints, args.supports_only,
        args.reuse_support_stage, args.proven_unit_replays)
    print(json.dumps({k:report[k] for k in ('status','manufacturing_preparation_admitted','n_layers') if k in report}))
