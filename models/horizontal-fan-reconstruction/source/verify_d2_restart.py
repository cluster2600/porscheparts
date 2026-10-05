#!/usr/bin/env python3
"""Verify the native checkpoint proof and unlaunched fixed20 completion plan."""
import json
from pathlib import Path
from prepare_d2_restart1000 import identity, validate_checkpoint


def verify(root):
    read = lambda name: json.loads((root/name).read_text())
    audit = read('results/runtime/D2-restart-checkpoint-audit.json')
    plan = read('parameters/D2-restart1000-protocol.json')
    receipt = read('results/runtime/D2-restart-preparation-receipt.json')
    original = read('parameters/D2-executed-configurations/protocol.json')
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    validate_checkpoint(audit, plan)
    require(audit['status'] == 'native_checkpoint_audit_only_no_solver' and not audit['solver_or_reconstruction_launched'], 'Read-only native checkpoint audit')
    require(set(audit['checkpoints']) == {'980', '1000'} and audit['serial_numeric_directories'] == ['960'], 'Actual native parallel-only checkpoints')
    require(plan['status'] == 'prepared_not_launched' and not plan['new_solver_launched'] and not plan['current_control_replayed'] and plan['no_further_continuation_if_rejected'], 'Fixed20 completion scope, no control replay or endless continuation')
    for key in ['original_numerical_acceptance_all_required', 'additional_stationarity_screen', 'domain_comparison_screen']:
        require(plan[key] == original[key], 'All original pressure/numerical/stationarity thresholds frozen')
    for field, name in [('checkpoint_audit_sha256', 'results/runtime/D2-restart-checkpoint-audit.json'),
                        ('original_protocol_sha256', 'parameters/D2-executed-configurations/protocol.json'),
                        ('controlDict_sha256', 'parameters/D2-restart1000-controlDict')]:
        require(plan[field] == identity(root/name)['sha256'], 'Frozen preparation identity ' + name)
    control = (root/'parameters/D2-restart1000-controlDict').read_text()
    previous = control.replace('startFrom startTime; startTime 1000;', 'startFrom latestTime; startTime 0;')
    import hashlib
    require(hashlib.sha256(previous.encode()).hexdigest() == audit['files']['system/controlDict']['sha256'], 'Only startFrom/startTime changed from actual native control')
    require(receipt['status'] == 'private_restart_prepared_no_solver' and not receipt['solver_or_reconstruction_launched'] and not receipt['reconstructed_from_integrals'], 'Actual private preparation, no numerical state invented')
    require(receipt['script_sha256'] == identity(root/'source/prepare_d2_restart1000.py')['sha256'] and receipt['plan_sha256'] == identity(root/'parameters/D2-restart1000-protocol.json')['sha256'], 'Actual preparer and plan identities')
    seeds = {n:r for n,r in audit['files'].items() if '/1000/' in n}
    require(len(seeds) == 32 and receipt['native_MPI_seed_files'] == seeds and sum(r['bytes'] for r in seeds.values()) == plan['checkpoint1000_native_files_bytes'], 'All native1000 restart field and time files preserved')
    require(receipt['checkpoint_audit_sha256'] == plan['checkpoint_audit_sha256'] and receipt['controlDict_sha256'] == plan['controlDict_sha256'], 'Actual preparation inputs')
    for name, record in receipt['source_mesh_config_identity'].items():
        require(record == audit['files'][name], 'Unchanged actual mesh/config ' + name)
    timing = {r['iteration']:r for r in audit['complete_iteration_timing']}
    require(list(timing) == list(range(961,1001)), 'Forty complete original timings, no partial1001')
    observed = timing[1000]['execution_seconds']-timing[980]['execution_seconds']
    require(abs(observed-audit['observed_981_1000_execution_seconds']) < 1e-9, 'Measured last20 restart cost')
    budget = plan['budget_proposed_not_authorized_or_started']
    require(budget['aggregate_wall_cap_seconds'] == 240 and budget['solver_wall_cap_seconds'] == 110 and budget['CPU_max'] == 4 and budget['memory_and_swap_GiB'] == 5 and budget['new_deadline_required_do_not_reuse_expired_D2_deadline'], 'Fresh proposed bounded lot, no execution or reservation')
    require(not any(plan[k] for k in ['physical_validation_established','domain_independence_established','airflow_improvement_proven','raw_scan_or_native_fields_published']), 'No unsupported qualification/publication')
    print('D2 native980/1000 checkpoint proof and private fixed20 unlaunched preparation checked')


if __name__ == '__main__':
    verify(Path(__file__).resolve().parents[1])
