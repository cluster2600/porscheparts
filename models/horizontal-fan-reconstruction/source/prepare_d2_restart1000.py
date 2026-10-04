#!/usr/bin/env python3
"""Prepare one private, hash-checked native MPI restart; never launch a solver."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time


def identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def validate_checkpoint(audit, plan):
    if (plan['restart_iteration'], plan['first_iteration'], plan['target_iteration'],
            plan['new_iterations'], plan['new_cases'], plan['current_control_replayed']) != (
            1000, 1001, 1020, 20, ['extended'], False):
        raise ValueError('Only the frozen extended1000-to1020 completion is allowed')
    checkpoint = audit['checkpoints']['1000']
    if not checkpoint['native_processor_checkpoint_complete'] or not checkpoint['uniform_directories_resolve']:
        raise ValueError('A complete native processor checkpoint is required')
    if checkpoint['total_cells'] != 680596 or len(checkpoint['processors']) != 4:
        raise ValueError('Frozen mesh and four native partitions required')
    for rank, row in enumerate(checkpoint['processors']):
        if row['rank'] != rank or row['expected_cells'] != plan['rank_cells'][rank]:
            raise ValueError('Original native partition cardinality differs')
        if row['uniform_time'] != {'value': '1000', 'name': '1000', 'index': '1000', 'deltaT': '1', 'deltaT0': '1'}:
            raise ValueError('Saved native time and index must be exactly1000')
        if set(row['fields']) != {'p', 'U', 'k', 'omega', 'nut', 'phi', 'Uf'}:
            raise ValueError('Missing native volume or surface restart field')
        for name, field in row['fields'].items():
            count = row['expected_internal_faces'] if name in ('phi', 'Uf') else row['expected_cells']
            components = 3 if name in ('U', 'Uf') else 1
            key = f'processor{rank}/1000/{name}'
            if not field['finite'] or field['count'] != count or field['components'] != components or field['identity'] != audit['files'][key]:
                raise ValueError('Incomplete/nonfinite/inconsistent native restart field')
        if row['uniform_time_identity'] != audit['files'][f'processor{rank}/1000/uniform/time']:
            raise ValueError('Native time identity differs')


def changed_control(text):
    replacement = text
    for key, old, new in [('startFrom', 'latestTime', 'startTime'), ('startTime', '0', '1000')]:
        replacement, count = re.subn(r'\b' + key + r'\s+' + old + r'\s*;', key + ' ' + new + ';', replacement)
        if count != 1:
            raise ValueError('Unexpected actual native start control')
    if not re.search(r'\bendTime\s+1020\s*;', replacement):
        raise ValueError('The original fixed target must remain1020')
    return replacement


def prepare(source, audit_file, plan_file, control_file, output):
    started = time.monotonic()
    audit = json.loads(audit_file.read_text())
    plan = json.loads(plan_file.read_text())
    if identity(audit_file)['sha256'] != plan['checkpoint_audit_sha256']:
        raise ValueError('Frozen checkpoint audit identity differs')
    validate_checkpoint(audit, plan)
    source, output = source.resolve(strict=True), output.resolve()
    if output == source or source in output.parents or output in source.parents or output.exists():
        raise ValueError('A new separate private output directory is required')
    # Verify original files before making a copy. The original runtime stays intact.
    selected = {name: record for name, record in audit['files'].items()
                if name.startswith(('constant/', 'system/'))
                or re.match(r'^processor[0-3]/(?:constant/|1000/)', name)
                or name in ('reference-protocol.json', 'private-maps.npz',
                            'partition-verification.json', 'independent-mesh-gate.json')}
    actual_names = {str(p.relative_to(source)) for base in [source/'constant', source/'system',
                    *[source/f'processor{i}'/d for i in range(4) for d in ('constant', '1000')]]
                    for p in base.rglob('*') if p.is_file()}
    required_names = {n for n in selected if n.startswith(('constant/', 'system/', 'processor'))}
    if actual_names != required_names:
        raise ValueError('Unrecorded or missing mesh/config/checkpoint file')
    for name, record in selected.items():
        if identity(source/name) != record:
            raise ValueError('Frozen source changed: ' + name)
    if changed_control((source/'system/controlDict').read_text()) != control_file.read_text() or identity(control_file)['sha256'] != plan['controlDict_sha256']:
        raise ValueError('Only explicit startFrom/startTime changes are allowed')
    output.mkdir(parents=True, exist_ok=False)
    for name, record in selected.items():
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/name, target)
        if identity(target) != record:
            raise ValueError('Private copied checkpoint identity differs: ' + name)
    shutil.copyfile(control_file, output/'system/controlDict')
    protocol = json.loads((output/'reference-protocol.json').read_text())
    if protocol['acceptance_all_required'] != plan['original_numerical_acceptance_all_required']:
        raise ValueError('Frozen original acceptance thresholds differ')
    original_protocol_identity = identity(output/'reference-protocol.json')
    if original_protocol_identity['sha256'] != plan['original_case_runtime_protocol_sha256']:
        raise ValueError('Original runtime protocol changed')
    shutil.copyfile(output/'reference-protocol.json', output/'original-reference-protocol.json')
    protocol = {key: protocol[key] for key in ['reference_configuration', 'rpm_assumed', 'fluid',
                'boundary_conditions', 'model', 'acceptance_all_required']}
    protocol['protocol_id'] = plan['protocol_id']
    protocol['expected_actual_solver_iterations'] = list(range(1001, 1021))
    protocol['required_admission_sample_iterations'] = list(range(1001, 1021))
    protocol['expected_cell_count'] = 680596
    protocol['iterations'] = 1020
    protocol['new_iterations'] = 20
    protocol['wall_timeout_seconds'] = 110
    protocol['aggregate_wall_cap_seconds'] = 240
    protocol['frozen_system_file_sha256'] = {name: identity(output/'system'/name)['sha256']
                                            for name in ('controlDict', 'fvSchemes', 'fvSolution')}
    protocol['physical_validation_established'] = False
    protocol['manufacturing_authorized'] = False
    protocol['initial_fields_sha256'] = {'1000/uniform/time': audit['files']['processor0/1000/uniform/time']['sha256']}
    protocol['initial_fields_scope'] = 'Time marker only; all32 native MPI seed identities are recorded separately'
    protocol['native_MPI_seed_files'] = {n: r for n, r in selected.items() if '/1000/' in n}
    protocol['original_runtime_protocol_sha256'] = original_protocol_identity['sha256']
    (output/'reference-protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    # This root marker is bookkeeping for the existing summary helper, not serial fields.
    marker = output/'1000/uniform/time'
    marker.parent.mkdir(parents=True)
    shutil.copyfile(output/'processor0/1000/uniform/time', marker)
    receipt = {'status': 'private_restart_prepared_no_solver', 'solver_or_reconstruction_launched': False,
               'restart_iteration': 1000, 'target_iteration': 1020, 'new_iterations': 20,
               'current_control_replayed': False, 'reconstructed_from_integrals': False,
               'native_MPI_seed_files': protocol['native_MPI_seed_files'],
               'source_mesh_config_identity': {n:r for n,r in selected.items() if '/1000/' not in n},
               'root1000_contains_only_time_marker_not_serial_fields': True,
               'controlDict_sha256': identity(control_file)['sha256'],
               'plan_sha256': identity(plan_file)['sha256'], 'checkpoint_audit_sha256': identity(audit_file)['sha256'],
               'script_sha256': identity(Path(__file__))['sha256'],
               'wall_seconds': time.monotonic()-started, 'native_fields_and_meshes_private': True}
    (output/'restart-preparation-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ['status','solver_or_reconstruction_launched','wall_seconds']}))
    return receipt


if __name__ == '__main__':
    os.nice(10)
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'audit', 'plan', 'control', 'output'):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    prepare(args.source, args.audit, args.plan, args.control, args.output)
