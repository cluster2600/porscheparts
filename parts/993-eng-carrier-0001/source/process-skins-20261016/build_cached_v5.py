"""Replay each recorded constructor authority without relabeling its evidence."""
import argparse
import importlib.util
import json
from pathlib import Path

from admitted_regions import sha
from compact_json import dumps

BASE = Path(__file__).with_name('build_cached.py')
BASE_SHA256 = 'fe8c06ecd2b30d4c05383ca65bb90c1523e86278bd6cd4447b92c9d6f5120fc2'
SCHEMA = 'support-geometry-v3-combinatorial-intervals'
STRATEGY = 'continuous_domain_with_nonoverlapping_attested_edge_strips'
KEYS = ('envelopes', 'regions', 'skins', 'grids', 'contacts', 'collisions')
POLICY_FILES = (Path(__file__).resolve(), Path(__file__).with_name('admissions_v3.py'),
                Path(__file__).with_name('incremental_combinatorial_interfaces_ids.py'),
                Path(__file__).with_name('incremental_combinatorial_interfaces.py'),
                Path(__file__).with_name('indexed_combinatorial_interfaces.py'),
                Path(__file__).with_name('redundant_strip_interfaces.py'))
POLICY_SHA256 = {path: sha(path) for path in POLICY_FILES}
ADMISSION_SHA256 = 'da60b5fd390cb9213638981c85bd7b95a4500d775ec41263d92c859785f8ba9d'
INDEX_SHA256 = '81422bc8ce95beab8039e33f70a9d1274083be1ce1426c778c700a06a8b21df8'
ASSEMBLY_SHA256 = '69b32aee03445071f9d6d1705d1e153baf16d82f85a9ea7f25cb6532dfb99ad8'
LINE_INDEX_SHA256 = '0302ac46796b2dab08484873370ab1f4d5eff6319c752f966641825a34aba2bd'
OLD_CONSTRUCTION_SHA256 = '94393c465fb15c1c3129ad8e482ea19cd597d3e716714e069b4eaee38b80e2fa'
REDUNDANT_SHA256 = '5047b9393408104fe704697a1fc35a9fe18cadc0a8d98fac5f176a409ef5c646'
if any(POLICY_SHA256[path] != expected for path, expected in zip(
        POLICY_FILES[1:], (ADMISSION_SHA256, INDEX_SHA256, ASSEMBLY_SHA256, LINE_INDEX_SHA256, REDUNDANT_SHA256))):
    raise ValueError('The reviewed exact admission or interface index changed')
RUNTIME_HOOKS = dict(combinatorial_constructor_dispatch=dict(source=POLICY_FILES[0].name,
    sha256=POLICY_SHA256[POLICY_FILES[0]],
    operation='strict_recorded_source_sha256_dispatch_without_relabeling',
    authorities={
        OLD_CONSTRUCTION_SHA256: dict(source='combinatorial_interfaces.py', sha256=OLD_CONSTRUCTION_SHA256,
            implementation=POLICY_FILES[2].name, implementation_sha256=INDEX_SHA256,
            operation='byte_identical_constructor_receipt_with_lossless_incremental_assembly'),
        REDUNDANT_SHA256: dict(source=POLICY_FILES[5].name, sha256=REDUNDANT_SHA256,
            operation='omit_only_whole_attested_strip_certified_inside_source_domain',
            base_constructor_sha256=OLD_CONSTRUCTION_SHA256, incremental_constructor_sha256=INDEX_SHA256)},
    incremental_assembly_source_sha256=ASSEMBLY_SHA256, source_line_index_sha256=LINE_INDEX_SHA256))
if sha(BASE) != BASE_SHA256:
    raise ValueError('The frozen cached support builder changed')
_spec = importlib.util.spec_from_file_location('_carrier_cached_builder_v5_base', BASE)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
_prepared_regions = _base.PreparedRegions
_admission_spec = importlib.util.spec_from_file_location('_carrier_cached_v5_old_admissions', POLICY_FILES[1])
admissions_v3 = importlib.util.module_from_spec(_admission_spec)
_admission_spec.loader.exec_module(admissions_v3)
_index_spec = importlib.util.spec_from_file_location('_carrier_cached_v5_index', POLICY_FILES[2])
_index = importlib.util.module_from_spec(_index_spec)
_index_spec.loader.exec_module(_index)
admissions_v3._construction = _index
_old_continuous_admission = admissions_v3.continuous_admission
_new_spec = importlib.util.spec_from_file_location('_carrier_cached_v5_new_admissions', POLICY_FILES[1])
_new_admission = importlib.util.module_from_spec(_new_spec)
_new_spec.loader.exec_module(_new_admission)
_redundant_spec = importlib.util.spec_from_file_location('_carrier_cached_v5_redundant', POLICY_FILES[5])
_redundant = importlib.util.module_from_spec(_redundant_spec)
_redundant_spec.loader.exec_module(_redundant)
_new_admission._construction = _redundant
_new_admission.CONSTRUCTION_SHA256 = REDUNDANT_SHA256


def continuous_admission(reconstruction, contacts, penetration):
    """Use only the authority explicitly recorded by this reconstruction."""
    if not isinstance(reconstruction, dict):
        raise ValueError('Missing recorded constructor authority')
    authority = reconstruction.get('combinatorial_construction_source_sha256')
    if authority == OLD_CONSTRUCTION_SHA256:
        return _old_continuous_admission(reconstruction, contacts, penetration)
    if authority == REDUNDANT_SHA256:
        return _new_admission.continuous_admission(reconstruction, contacts, penetration)
    raise ValueError('Unrecognized recorded constructor authority')


# The historical seal uses its original gates and dispatches each interval set
# through one of two isolated admission modules. Public imports stay untouched.
admissions_v3.continuous_admission = continuous_admission


def prepared_regions(*args, **kwargs):
    prepared = _prepared_regions(*args, **kwargs)
    prepared.files.update(POLICY_SHA256)
    prepared.verify()
    return prepared


def verify_sources():
    if sha(BASE) != BASE_SHA256 or any(sha(path) != digest for path, digest in POLICY_SHA256.items()):
        raise ValueError('Cached support builder or admission policy changed')


def seal(output, checkpoint, store):
    verify_sources()
    admission, admitted = admissions_v3.seal(output, checkpoint, store)
    for item in admission.values():
        path = Path(output)/item['receipt']
        receipt = json.loads(path.read_text())
        receipt['admission_runtime_hooks'] = RUNTIME_HOOKS
        path.write_text(dumps(receipt, indent=2, allow_nan=False)+'\n')
        item['receipt_sha256'] = sha(path)
    checkpoint['admission_runtime_hooks'] = RUNTIME_HOOKS
    (Path(output)/'support-stage.json').write_text(dumps(checkpoint, indent=2, allow_nan=False)+'\n')
    verify_sources()
    return admission, admitted


# Mutations are confined to the private builder and admission instances.
_base.PreparedRegions = prepared_regions
_base.seal = seal


def verify_v3_stage(directory):
    directory = Path(directory).resolve()
    checkpoint = json.loads((directory/'support-stage.json').read_text())
    admission = checkpoint.get('admission', {})
    if checkpoint.get('manufacturing_preparation_admitted') is not True or set(admission) != set(KEYS):
        raise ValueError('A v3 stage requires six admitted receipts')
    if checkpoint.get('admission_runtime_hooks') != RUNTIME_HOOKS:
        raise ValueError('The v3 admission runtime hook differs')
    for key in KEYS:
        item = admission[key]
        name = f'admission-{key}.json'
        path = directory/name
        if (item.get('receipt') != name or item.get('status') != 'passed' or path.is_symlink()
                or not path.is_file() or sha(path) != item.get('receipt_sha256')):
            raise ValueError('The exact v3 admission receipt identity differs: '+key)
        receipt = json.loads(path.read_text())
        if (receipt.get('passed') is not True or receipt.get('status') != 'passed'
                or receipt.get('input_sha256') != checkpoint['input_sha256']
                or receipt.get('admission_schema') != SCHEMA
                or receipt.get('admission_source_sha256') != POLICY_SHA256[POLICY_FILES[1]]
                or receipt.get('admission_runtime_hooks') != RUNTIME_HOOKS):
            raise ValueError('The reusable stage does not use this exact v3 policy: '+key)
    return checkpoint


def build(input_path, output, envelopes, part_cache, expected_sha256=None, identity_receipt=None,
          solid_sheets=False, continuous_interfaces=False, region_checkpoints=None,
          supports_only=False, reuse_support_stage=None):
    verify_sources()
    if reuse_support_stage is not None:
        verify_v3_stage(reuse_support_stage)
    result = _base.build(input_path, output, envelopes, part_cache, expected_sha256, identity_receipt,
        solid_sheets, continuous_interfaces, region_checkpoints, supports_only, reuse_support_stage)
    if not supports_only:
        checkpoint_path = Path(output)/'support-stage.json'
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint['admission_runtime_hooks'] = RUNTIME_HOOKS
        checkpoint_path.write_text(dumps(checkpoint, indent=2, allow_nan=False)+'\n')
        result['outputs_sha256']['support-stage.json'] = sha(checkpoint_path)
    verify_v3_stage(output)
    result.update(support_strategy=STRATEGY, runner_adapter_source_sha256=POLICY_SHA256[POLICY_FILES[0]],
                  cached_builder_base_sha256=BASE_SHA256,
                  admission_source_sha256=POLICY_SHA256[POLICY_FILES[1]],
                  admission_runtime_hooks=RUNTIME_HOOKS)
    path = Path(output)/('support-stage.json' if supports_only else 'report.json')
    path.write_text(dumps(result, indent=2, allow_nan=False)+'\n')
    verify_sources()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument('--sha256')
    identity.add_argument('--identity-receipt', type=Path)
    parser.add_argument('--envelopes', type=Path, required=True)
    parser.add_argument('--part-cache', type=Path, required=True)
    parser.add_argument('--region-checkpoints', type=Path, required=True)
    parser.add_argument('--supports-only', action='store_true')
    parser.add_argument('--reuse-support-stage', type=Path)
    parser.add_argument('--solid-sheets', action='store_true')
    parser.add_argument('--continuous-interfaces', action='store_true')
    args = parser.parse_args()
    report = build(args.input, args.output, args.envelopes, args.part_cache, args.sha256,
        args.identity_receipt, args.solid_sheets, args.continuous_interfaces,
        args.region_checkpoints, args.supports_only, args.reuse_support_stage)
    print(json.dumps({key:report[key] for key in ('status', 'manufacturing_preparation_admitted', 'n_layers') if key in report}))
