"""Retain v5 guide gates and link the v6 exact-admission execution evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from build_part_workflow_guide import build, digest

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).with_name('build_carrier_workshop_guide_v5.py')
BASE_SHA256 = '6d5a3bebe7f38545a737ee5c2bf8de7cb269feb89d3bc0c3f2fa4bcd4c807a45'
CONSUMER = ROOT/'parts/993-eng-carrier-0001/source/process-skins-20261016/build_cached_v6.py'
CONSUMER_SHA256 = '6a6d3720e4a9c98c05393ea6446b33f6596ba3addcd73184ccaec5c8b64b9343'
SOURCE_SHA256 = digest(Path(__file__))
OLD_RECIPE = 'manufacturing/workflows/993-carrier-lpbf-v5.json'
NEW_RECIPE = 'manufacturing/workflows/993-carrier-lpbf-v6.json'
OLD_RUNNER = 'scripts/run_part_workflow.py'
NEW_RUNNER = 'scripts/run_part_workflow_v2.py'
KEYS = ('envelopes', 'regions', 'skins', 'grids', 'contacts', 'collisions')
REPLAY = 'exact-admission-replays.json'
PROOFS = ('exact-unit-proof-assessment.json', 'exact-unit-proof-plan.json', 'exact-unit-proof-runtime.json')


def verify_sources():
    if (digest(BASE) != BASE_SHA256 or digest(Path(__file__)) != SOURCE_SHA256 or
            digest(CONSUMER) != CONSUMER_SHA256):
        raise ValueError('Carrier guide or exact-admission consumer source changed')


verify_sources()
_spec = importlib.util.spec_from_file_location('_carrier_workshop_v6_base', BASE)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def exact_replay_reference(run):
    """Verify linked metadata only; no AM import, geometry proof or runtime comparison."""
    verify_sources()
    directory = run/'process'
    def read(name):
        path = directory/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('An exact-admission guide input is absent or a symlink')
        return json.loads(path.read_text())
    stage, report = read('support-stage.json'), read('report.json')
    if (stage.get('manufacturing_preparation_admitted') is not True or
            report.get('manufacturing_preparation_admitted') is not True or
            stage.get('admission') != report.get('admission') or set(stage.get('admission', {})) != set(KEYS) or
            stage.get('input_sha256') != report.get('input_sha256') or
            report.get('outputs_sha256', {}).get('support-stage.json') != digest(directory/'support-stage.json')):
        raise ValueError('The exact-admission stage is not bound to the final process report')
    binding = stage.get('exact_unit_replays', {})
    files = binding.get('files_sha256', {})
    if (binding.get('receipt') != REPLAY or binding.get('receipt_sha256') != files.get(REPLAY) or
            set(files) not in ({REPLAY}, {REPLAY, *PROOFS})):
        raise ValueError('The exact-admission replay binding differs')
    for name, expected in files.items():
        read(name)
        if (digest(directory/name) != expected or stage.get('outputs_sha256', {}).get(name) != expected or
                report.get('outputs_sha256', {}).get(name) != expected):
            raise ValueError('The exact-admission evidence SHA differs')
    execution = read(REPLAY)
    hook = stage.get('admission_runtime_hooks', {}).get('parallel_exact_unit_admissions', {})
    runtime = execution.get('runtime_before_sha256')
    if (execution.get('schema') != 'bounded-exact-unit-replays-1' or execution.get('status') != 'completed' or
            execution.get('workers') != 4 or execution.get('maximum_pending_futures') != 8 or
            execution.get('worker_group_closed') is not True or
            execution.get('worker_runtime_identity_verified_at_initialisation') is not True or
            not isinstance(runtime, str) or len(runtime) != 64 or any(c not in '0123456789abcdef' for c in runtime) or
            runtime != execution.get('runtime_after_sha256') or execution.get('source_indices') != [0, 1, 2, 3, 8, 9, 10] or
            execution.get('policy_sha256', {}).get(CONSUMER.name) != CONSUMER_SHA256 or
            hook.get('source') != CONSUMER.name or hook.get('sha256') != CONSUMER_SHA256 or
            execution.get('reviewed_proof_files_sha256') != {n:h for n,h in files.items() if n != REPLAY}):
        raise ValueError('The recorded exact-admission execution is incomplete or unbound')
    indices, rows = execution['source_indices'], execution.get('units', [])
    expected = [(r['source_index'], r['unit'], r['result_sha256']) for r in rows]
    if not expected or len({(r[0], r[1]) for r in expected}) != len(expected):
        raise ValueError('Exact-admission unit identities are empty or duplicated')
    receipts = {}
    for key in KEYS:
        item = stage['admission'][key]
        if item.get('receipt') != 'admission-'+key+'.json' or item.get('status') != 'passed':
            raise ValueError('A historical support admission is absent or refused')
        receipt = read(item['receipt'])
        if digest(directory/item['receipt']) != item.get('receipt_sha256') or receipt.get('exact_unit_replays') != binding:
            raise ValueError('One of the six admissions has another replay binding or SHA')
        receipts[item['receipt']] = item['receipt_sha256']
        if key in ('skins', 'grids', 'contacts', 'collisions'):
            actual = []
            for row in receipt.get('continuous_interval_exact_admissions', []):
                region = row['region']
                if type(region) is not int or not 0 <= region < len(indices):
                    raise ValueError('An exact-admission result has an invalid region index')
                value = json.dumps(row['receipt'], sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
                actual.append((indices[region], row['unit'], hashlib.sha256(value).hexdigest()))
            if actual != expected:
                raise ValueError('A support gate changes the recorded exact-unit result hashes')
    return dict(schema='carrier-guide-exact-admission-reference-1', consumer_source_sha256=CONSUMER_SHA256,
        support_stage_sha256=digest(directory/'support-stage.json'), process_report_sha256=digest(directory/'report.json'),
        evidence_files_sha256=files, admission_receipts_sha256=receipts, unit_result_count=len(rows),
        recorded_AM_runtime_sha256=runtime, exact_units_recomputed_in_PDF=False, PDF_runtime_compared_to_AM=False,
        scope='Receipt/file identities and matching recorded unit results only; mathematical replay remains the pinned consumer6 responsibility.')


def render(description, output):
    verify_sources()
    data = json.loads(description.read_text())
    if data['stages'][3]['id'] != 'supports' or data['stages'][5]['id'] != 'delivery':
        raise ValueError('The six-stage carrier guide layout changed')
    command = data['stages'][5]['commands'][0]
    if command.split().count(OLD_RECIPE) != 1:
        raise ValueError('The v5 carrier reproduction command changed')
    if command.split().count(OLD_RUNNER) != 1:
        raise ValueError('The v5 carrier workflow runner token changed')
    run = description.resolve().parent
    reference = exact_replay_reference(run)
    data['stages'][5]['commands'][0] = command.replace(OLD_RECIPE, NEW_RECIPE).replace(OLD_RUNNER, NEW_RUNNER)
    data['stages'][3]['files'] += [dict(source=str((run/'process'/name).relative_to(ROOT)), label=label)
        for name, label in [('support-stage.json', 'Scellement des supports et liaisons SHA des six admissions'),
                            (REPLAY, 'Rejeux exacts des intervalles : exécution et résultats liés')]]
    data['stages'][3]['files'] += [dict(source=str((run/'process'/name).relative_to(ROOT)), label='Preuve conservée : '+name)
        for name in PROOFS if name in reference['evidence_files_sha256']]
    data['exact_admission_reference'] = reference
    data['workshop_adapter'] = dict(source='scripts/build_carrier_workshop_guide_v6.py', sha256=SOURCE_SHA256,
        base_sha256=BASE_SHA256, retained_adapter=data.get('workshop_adapter'))
    description.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    result = build(description, output)
    if exact_replay_reference(run) != reference:
        raise ValueError('Exact-admission evidence changed during guide publication')
    verify_sources()
    return result


# Change only the renderer of this private v5 instance; all old guards stay active.
_base.build = render


def package(run):
    verify_sources()
    reference = exact_replay_reference(run.resolve())
    result = _base.package(run)
    if exact_replay_reference(run.resolve()) != reference:
        raise ValueError('Exact-admission evidence changed during guide packaging')
    verify_sources()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    package(parser.parse_args().run)
