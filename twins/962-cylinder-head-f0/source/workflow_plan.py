"""Check mandatory phase coverage and prepare separate job records, never run solvers."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
HEAD = ROOT / 'twins/962-cylinder-head-f0'
CONTRACT = HEAD / 'workflow-contract.json'
PHASES = ('provenance', 'reconstruction', 'picogk', 'surface', 'volume',
          'coolant_cfd', 'cht', 'material_strength', 'lpbf_melt_pool',
          'lpbf_build', 'lpbf_release', 'omni_preflight', 'omni_conversion',
          'omni_assignment', 'omni_conformance', 'field_exchange', 'omni_render',
          'physicsnemo', 'delivery')
STATES = {'blocked', 'prepared', 'running', 'executed', 'accepted', 'failed', 'not_applicable'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, name):
    path = root / name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Reference escapes its declared root: ' + name)
    return path


def validate_contract(contract, root=ROOT):
    stages = contract['phases']
    if contract['schema_version'] != 1 or [s['id'] for s in stages] != list(PHASES):
        raise ValueError('Mandatory phases are missing, duplicated or reordered')
    previous = set()
    for stage in stages:
        if not set(stage['depends_on']) <= previous:
            raise ValueError('Unknown, cyclic or out-of-order dependency')
        previous.add(stage['id'])
        for field in ('software', 'required_inputs', 'expected_outputs', 'acceptance_checks', 'references'):
            if not stage[field] or any(not isinstance(v, str) or not v.strip() for v in stage[field]):
                raise ValueError('Incomplete stage ' + stage['id'] + ': ' + field)
        if not stage['command_templates'] or any(
                not argv or any(not isinstance(v, str) or not v for v in argv)
                for argv in stage['command_templates']):
            raise ValueError('Missing command preparation')
        for name in stage['references']:
            if not inside(root, name).is_file():
                raise ValueError('Missing repository recipe: ' + name)
    return stages


def proof(root, entry, kind=None, phase=None):
    if not isinstance(entry, dict) or set(entry) != {'path', 'sha256'}:
        raise ValueError('Expected a relative, hash-bound evidence reference')
    path = inside(root, entry['path'])
    if not path.is_file() or sha(path) != entry['sha256']:
        raise ValueError('Evidence missing or changed: ' + entry['path'])
    if kind:
        data = json.loads(path.read_text())
        if data.get('kind') != kind or data.get('phase') != phase:
            raise ValueError('Receipt kind or phase does not match')
        if kind == 'execution':
            if data.get('exit_code') != 0 or data.get('timed_out') is not False:
                raise ValueError('Execution did not complete successfully')
        elif data.get('passed') is not True:
            raise ValueError('Runtime/independent assessment did not pass')
    return path


def validate_plan(plan, folder, contract):
    stages = validate_contract(contract)
    if (plan['schema_version'] != 1 or plan['manufacturing_authorized'] is not False
            or plan['contract_sha256'] != sha(CONTRACT)
            or [j['phase'] for j in plan['jobs']] != list(PHASES)):
        raise ValueError('Incomplete, stale or improperly promoted campaign')
    expected = set().union(*(set(s['references']) for s in stages))
    if set(plan['source_hashes']) != expected:
        raise ValueError('Recipe source coverage changed')
    for name, digest in plan['source_hashes'].items():
        if sha(inside(ROOT, name)) != digest:
            raise ValueError('Recipe changed; preserve this plan and prepare a new one')
    states = {}
    for stage, job in zip(stages, plan['jobs']):
        state = job['state']
        if state not in STATES:
            raise ValueError('Unknown phase state')
        if state == 'not_applicable':
            if stage['id'] != 'reconstruction' or not job['reason']:
                raise ValueError('Core phase cannot be silently omitted')
        elif state in ('blocked', 'failed'):
            if not job['reason']:
                raise ValueError('Blocked/failed phase needs its actual reason')
        else:
            if (set(job['input_bindings']) != set(stage['required_inputs'])
                    or any(not isinstance(v, str) or not v.strip() for v in job['input_bindings'].values())
                    or not job['commands'] or any(not a or any(
                        not isinstance(v, str) or not v or re.search(r'\{[A-Z_]+\}', v)
                        for v in a) for a in job['commands'])):
                raise ValueError('Unbound inputs or command templates are not prepared work')
            proof(folder, job['runtime_receipt'], 'runtime_qualification', stage['id'])
            if any(states[d] not in ('accepted', 'not_applicable') for d in stage['depends_on']):
                raise ValueError('Upstream acceptance is missing')
            if state in ('executed', 'accepted'):
                proof(folder, job['execution_receipt'], 'execution', stage['id'])
                if not job['outputs']:
                    raise ValueError('Executed phase has no captured outputs')
                for entry in job['outputs']:
                    proof(folder, entry)
            if state == 'accepted':
                proof(folder, job['independent_assessment'], 'independent_assessment', stage['id'])
                if job['acceptance_scope'] not in ('software', 'study_numerical'):
                    raise ValueError('This ledger cannot grant physical qualification')
        states[stage['id']] = state
    return dict(status='workflow_structure_checked_not_physical_validation', phases=len(states),
                states=states, all_phases_accepted=all(v in ('accepted', 'not_applicable')
                for v in states.values()), manufacturing_authorized=False)


def materialize(output, contract):
    stages = validate_contract(contract)
    if output.exists():
        raise ValueError('Plan output must be fresh; preserve historical checkpoints')
    jobs = []
    for stage in stages:
        jobs.append(dict(phase=stage['id'], state='blocked',
            reason='Concrete inputs, runtime qualification and upstream acceptance must be bound',
            input_bindings={name: None for name in stage['required_inputs']},
            commands=stage['command_templates'], runtime_receipt=None, execution_receipt=None,
            independent_assessment=None, acceptance_scope=None, outputs=[]))
    names = set().union(*(set(s['references']) for s in stages))
    plan = dict(schema_version=1, contract_sha256=sha(CONTRACT),
        source_hashes={n: sha(inside(ROOT, n)) for n in sorted(names)}, jobs=jobs,
        manufacturing_authorized=False)
    validate_plan(plan, output, contract)
    output.mkdir(parents=True)
    (output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    return plan


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--output', type=Path)
    action.add_argument('--check-plan', type=Path)
    parser.add_argument('--require-ready', choices=PHASES)
    args = parser.parse_args()
    contract = json.loads(CONTRACT.read_text())
    validate_contract(contract)
    if args.output:
        materialize(args.output.resolve(), contract)
        print('Prepared 19 job records; runtime and input binding remain required')
    elif args.check_plan:
        result = validate_plan(json.loads(args.check_plan.read_text()), args.check_plan.resolve().parent, contract)
        print(json.dumps(result, indent=2))
        if args.require_ready and result['states'][args.require_ready] != 'prepared':
            raise SystemExit('Selected phase is not prepared for execution')
    elif args.require_ready:
        parser.error('--require-ready needs --check-plan')
    else:
        print('Mandatory 19-phase contract and repository recipes checked')
