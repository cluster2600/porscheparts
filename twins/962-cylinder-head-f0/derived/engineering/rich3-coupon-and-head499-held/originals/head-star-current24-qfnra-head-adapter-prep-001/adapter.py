"""HELD fixed HEAD499 adapter; no execution or admission is created on import."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import types

ROOT = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
OUTPUT = ROOT / 'work/962-engineering/head-star-current24-qfnra-head-execution-001'
CAP = 32 * 1024**2
COMPONENTS = (2, 7, 8, 9, 10, 21, 28, 30, 31, 39, 45)
INPUT_MAP_SHA256 = '61a9482457279b33b43ae53aae18c5a7ebc6717e21a72ede8bab0e22e8cdc0e5'
EDGE_HELD = dict(path='work/962-engineering/head-star-current24-edge-removal-prep-001/held-preparation.json',
    sha256='eec69197200e1d1c1651b2ae172f0ddca379262997d35d8e5461f30d49eda4b7', bytes=20559)
SOURCES = {
    'emitter': dict(path='work/962-engineering/head-star-current24-coupled-qfnra-prep-001/qfnra_emitter.py',
        sha256='5d76ef8218843ef92c83d64db3e5d9b0d8d1f6523d95aecdfa53b99dc569cd7b', bytes=36312),
    'protocol': dict(path='work/962-engineering/head-star-current24-coupled-qfnra-prep-001/qfnra_protocol.py',
        sha256='9b5885a35bfbc681c0354e937b9f57621b3d8137adc25b4e2ba455e86ce59785', bytes=12459),
    'transport': dict(path='work/962-engineering/head-star-current24-qfnra-toy-transport-prep-003/check_toy_sessions.py',
        sha256='3619b5316cf23398ed479ebf724a1159bb816ce3bafb85ad93c40b67b7df4990', bytes=22291),
    'validator': dict(path='work/962-engineering/head-star-current24-qfnra-word-validator-prep-001/validate_binary64_words.py',
        sha256='20b702017e8da8db3786d3423fe60c6c42289e5cab9cc5012a0991f9eb2540b2', bytes=31381),
}
PACKET_NAMES = ('adapter.py', 'METHOD.md', 'manifest.json')


def need(value, message):
    if not value:
        raise ValueError(message)


def checked_bytes(pin):
    path = ROOT / pin['path']
    need(path.is_file() and not path.is_symlink() and path.resolve() == path,
         'Fixed canonical regular file required: ' + pin['path'])
    raw = path.read_bytes()
    need(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'],
         'Fixed source/input identity changed: ' + pin['path'])
    return raw


def fresh_module(role, raw):
    module = types.ModuleType('fixed_head499_' + role)
    module.__file__ = str(ROOT / SOURCES[role]['path'])
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def full_model(protocol, text, symbols, aliases):
    """T003's definition schema generalized to the exact3/6 Real names.

    The generic symbolic parser and scalar-value grammar are unchanged imports.
    Bool bodies are retained, not treated as proven by their printed value.
    """
    need(type(symbols) is list and len(symbols) in (3, 6)
         and len(set(symbols)) == len(symbols)
         and type(aliases) is list and len(set(aliases)) == len(aliases)
         and not set(symbols).intersection(aliases), 'Exact disjoint model name sets required')
    expected = {name: 'Real' for name in symbols}
    expected.update({name: 'Bool' for name in aliases})
    tree = protocol.parse_sexpr(text)
    if type(tree) is list and tree and tree[0] == 'model':
        tree = tree[1:]
    need(type(tree) is list and len(tree) == len(expected), 'Complete exact HEAD model definition count required')
    definitions = {}
    for row in tree:
        need(type(row) is list and len(row) == 5 and row[0] == 'define-fun'
             and type(row[1]) is str and row[2] == [] and row[1] in expected
             and row[1] not in definitions and row[3] == expected[row[1]],
             'Exact unique zero-argument model name/sort/arity required')
        definitions[row[1]] = row[4]
    need(set(definitions) == set(expected), 'Missing or extra model definition')
    return dict(real_values={name: protocol.model_value(definitions[name]) for name in symbols},
                definitions=definitions)


def file_record(path):
    need(path.is_file() and not path.is_symlink(), 'Complete captured stream/report required')
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def preserved(sources_before, edge_before, payloads, input_records, packet_before):
    errors = []
    for role, pin in SOURCES.items():
        try:
            need(checked_bytes(pin) == sources_before[role], 'Source changed: ' + role)
        except BaseException as exc:
            errors.append(dict(role=role, error=repr(exc)))
    try:
        need(checked_bytes(EDGE_HELD) == edge_before, 'Edge-held contract changed')
    except BaseException as exc:
        errors.append(dict(role='edge_held', error=repr(exc)))
    for name, pin in input_records.items():
        try:
            need(checked_bytes(pin) == payloads[name], 'Saved input changed')
        except BaseException as exc:
            errors.append(dict(role=name, error=repr(exc)))
    for name, raw in packet_before.items():
        try:
            need((Path(__file__).resolve().parent / name).read_bytes() == raw, 'Adapter packet changed')
        except BaseException as exc:
            errors.append(dict(role=name, error=repr(exc)))
    return errors


def run_head499():
    """Exactly one fixed future root-admitted operation; no arbitrary paths/CLI."""
    started = time.monotonic()
    need(sys.version_info[:3] == (3, 10, 11) and sys.flags.isolated == 1
         and sys.flags.no_site == 1 and sys.dont_write_bytecode,
         'Separately current-selected CPython3.10.11 -B -I -S required')
    need(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'Fixed fresh output directory must be absent')
    packet_before = {name: (Path(__file__).resolve().parent / name).read_bytes() for name in PACKET_NAMES}
    sources_before = {role: checked_bytes(pin) for role, pin in SOURCES.items()}
    protocol = fresh_module('protocol', sources_before['protocol'])
    emitter = fresh_module('emitter', sources_before['emitter'])
    transport = fresh_module('transport', sources_before['transport'])
    validator = fresh_module('validator', sources_before['validator'])
    need(emitter.SMT_PROLOGUE == transport.PROLOGUE and emitter.SMT_CHECK == transport.CHECK,
         'Exact previously tested prologue/check identity required')
    deadline = started + transport.GLOBAL_SECONDS
    expected_group = os.getpgrp()
    capture = transport.Capture(OUTPUT)
    results = [dict(component_ID=cid, status='UNATTEMPTED') for cid in COMPONENTS]
    payloads, input_records, all_mappings, blocks = {}, {}, [], []
    edge_before = None
    failure = None
    validation = None
    candidate_record = None
    validation_record = None
    preservation_errors = []
    static_bytes = sum(map(len, sources_before.values())) + sum(map(len, packet_before.values()))

    def budget():
        need(time.monotonic() < deadline, 'Existing helper60s deadline expired')
        need(capture.total + static_bytes <= CAP, 'Known inclusive32MiB scope exceeded; no truncation')

    try:
        edge_before = checked_bytes(EDGE_HELD)
        input_records = emitter.strict_json(edge_before)['input_records']
        need(len(input_records) == 23 and hashlib.sha256(emitter.canonical(input_records).encode()).hexdigest() == INPUT_MAP_SHA256,
             'Exact complete23 descriptor map required')
        payloads = {name: checked_bytes(pin) for name, pin in input_records.items()}
        static_bytes += len(edge_before) + sum(map(len, payloads.values()))
        budget()
        admitted = emitter.admit_current(payloads, edge_before)
        emission = emitter.emit_all(admitted)
        blocks = emission['blocks']
        need(tuple(b['component_ID'] for b in blocks) == COMPONENTS
             and sum(len(b['cell_rows']) for b in blocks) == 499
             and sum(len(b['variables']) for b in blocks) == 48, 'Complete fixed11/499/48 emission required')
        budget()
        for block, result in zip(blocks, results):
            result.update(variables=block['variables'], cell_rows=block['cell_rows'],
                predicates=block['predicates'], exact_oriented_boundary=block['exact_oriented_boundary'],
                baseline_scaled_six_volume=block['baseline_scaled_six_volume'], normalization=block['normalization'],
                integer_coefficient_DAG_sha256=block['integer_coefficient_DAG_sha256'], mappings=[])
        for block, result in zip(blocks, results):
            session = None
            stop_remaining = False
            result['status'] = 'INCOMPLETE'
            try:
                budget()
                # This exact retained Session is stored before its start can spawn Z3.
                session = transport.Session(dict(ID='head_c%03d' % block['component_ID']), capture, deadline, protocol)
                session.start(expected_group)
                symbols = [v['symbol'] for v in block['variables']]
                aliases = [p['name'] for p in block['predicates']]
                bootstrap = emitter.smt_block(block)
                result['SMT_sha256'] = hashlib.sha256(bootstrap.encode('ascii')).hexdigest()
                result['SMT_bytes'] = len(bootstrap.encode('ascii'))
                result['SMT_complete_body_location'] = session.session_id + '.jsonl bootstrap request wire'
                status = protocol.parse_status(session.exchange('bootstrap', bootstrap))
                result['solver_status'] = status
                budget()
                if status != 'sat':
                    session.phase = status
                    session.close(normal=True)
                    need(not session.cleanup and session.proc.returncode == 0 and session.check_count == 1
                         and session.eof == {'stdout', 'stderr'} and session.stderr_bytes == 0,
                         'Non-SAT result still requires complete normal captured/reaped session')
                    result['status'] = 'INCOMPLETE_' + status.upper()
                    result['UNSAT_scope'] = 'Solver-attributed only; no checked proof or global mesh infeasibility'
                    failure = result['status']
                else:
                    session.phase = 'sat'
                    result['initial_full_model'] = session.exchange('model', '(get-model)')
                    initial_model = full_model(protocol, result['initial_full_model'], symbols, aliases)
                    projection_command = '(get-value (' + ' '.join(symbols) + '))'
                    result['initial_projection'] = session.exchange('projection', projection_command)
                    projection = protocol.parse_projection(result['initial_projection'], symbols, 'sat')
                    need(initial_model['real_values'] == {r['symbol']: r['value'] for r in projection},
                         'Initial full model and projection disagree')
                    model_id = protocol.snapshot_id(projection)
                    result['model_id'] = model_id
                    result['initial_original_predicates'] = []
                    for alias in aliases:
                        answer = session.exchange('predicate', '(get-value (' + alias + '))')
                        value = protocol.parse_boolean(answer, alias, 'sat')
                        result['initial_original_predicates'].append(dict(alias=alias, response=answer, value=value))
                        need(value is True, 'Initial original asserted predicate is false')
                        budget()

                    def oracle(request):
                        need(request['model_id'] == model_id and session.phase == 'sat' and session.check_count == 1
                             and request['command'] == '(get-value (' + request['term'] + '))',
                             'Same retained model/request association required')
                        answer = session.exchange('oracle', request['command'])
                        value = protocol.parse_boolean(answer, request['term'], 'sat')
                        budget()
                        return value

                    for coordinate in block['variables']:
                        mapped = protocol.nearest_binary64(coordinate, int(block['normalization']['scale_integer']), model_id, oracle)
                        result['mappings'].append(mapped)
                        all_mappings.append(mapped)
                    result['final_full_model'] = session.exchange('model', '(get-model)')
                    final_model = full_model(protocol, result['final_full_model'], symbols, aliases)
                    result['final_projection'] = session.exchange('projection', projection_command)
                    final_projection = protocol.parse_projection(result['final_projection'], symbols, 'sat')
                    need(final_model == initial_model and final_projection == projection
                         and final_model['real_values'] == {r['symbol']: r['value'] for r in final_projection},
                         'Full model/projection changed during read-only mapping')
                    result['final_original_predicates'] = []
                    for alias in aliases:
                        answer = session.exchange('predicate', '(get-value (' + alias + '))')
                        value = protocol.parse_boolean(answer, alias, 'sat')
                        result['final_original_predicates'].append(dict(alias=alias, response=answer, value=value))
                        need(value is True, 'Final original asserted predicate is false')
                        budget()
                    session.close(normal=True)
                    need(not session.cleanup and session.proc.returncode == 0 and session.check_count == 1
                         and session.eof == {'stdout', 'stderr'} and session.stderr_bytes == 0,
                         'Complete normal0/reaped one-check session required')
                    budget()
                    result['status'] = 'COMPLETE_SAT_MAPPING_ONLY'
            except BaseException as exc:
                stop_remaining = True
                failure = repr(exc)
                result.update(status='INCOMPLETE', error=repr(exc), traceback=traceback.format_exc())
                if hasattr(exc, 'events'):
                    result['partial_mapping_events'] = exc.events
                if session is not None:
                    try:
                        session.close(normal=False)
                    except BaseException as cleanup_error:
                        result['cleanup_call_error'] = dict(error=repr(cleanup_error), traceback=traceback.format_exc())
            finally:
                if session is not None:
                    result.update(session_id=session.session_id,
                        pid=session.proc.pid if session.proc is not None else None,
                        solver_returncode=session.proc.returncode if session.proc is not None else None,
                        check_count=session.check_count, cleanup=session.cleanup,
                        direct_child_reaped=session.proc is not None and session.proc.returncode is not None,
                        stdout_bytes=session.stdout_bytes, stderr_bytes=session.stderr_bytes,
                        observed_EOF_names=sorted(session.eof))
                    try:
                        session.finish()
                    except BaseException as finish_error:
                        stop_remaining = True
                        result['finish_error'] = dict(error=repr(finish_error), traceback=traceback.format_exc())
                        failure = repr(finish_error)
                        result['status'] = 'INCOMPLETE'
                    result['captured_files'] = []
                    for suffix in ('.stdout', '.stderr', '.jsonl'):
                        try:
                            result['captured_files'].append(file_record(capture.root / (session.session_id + suffix)))
                        except BaseException as capture_error:
                            stop_remaining = True
                            result.setdefault('capture_record_errors', []).append(repr(capture_error))
                            failure = repr(capture_error)
                            result['status'] = 'INCOMPLETE'
            if stop_remaining:
                break
        preservation_errors = preserved(sources_before, edge_before, payloads, input_records, packet_before)
        need(not preservation_errors, 'Complete source/input/packet preservation required')
        if failure is None:
            need(len(all_mappings) == 48 and all(r['status'] == 'COMPLETE_SAT_MAPPING_ONLY' for r in results),
                 'All11 retained SAT models/all48 mappings required; no partial proposal')
            candidate = emitter.word_proposal(admitted, all_mappings)
            with (capture.root / 'word-candidate.json').open('xb') as handle:
                capture.record(handle, candidate)
            candidate_record = file_record(capture.root / 'word-candidate.json')
            budget()
            validation = validator.validate_proposal(candidate, payloads, admitted['input_records'])
            with (capture.root / 'word-validation.json').open('xb') as handle:
                capture.record(handle, validation)
            validation_record = file_record(capture.root / 'word-validation.json')
            need(validation.get('complete11_blocks') is True and validation.get('complete499_cells') is True
                 and validation.get('complete48_mappings') is True
                 and validation.get('actual_binary64_word_quality_vector_accepted') is True,
                 'Independent complete499 actual-word validation refused; preserve candidate without acceptance')
            budget()
    except BaseException as exc:
        failure = repr(exc)
        results.append(dict(status='INCOMPLETE_INTAKE_EMISSION_OR_VALIDATION', error=repr(exc), traceback=traceback.format_exc()))
    if edge_before is not None:
        preservation_errors = preserved(sources_before, edge_before, payloads, input_records, packet_before)
        if preservation_errors:
            failure = 'Final source/input/packet preservation failed'
    complete = (failure is None and len(all_mappings) == 48 and validation is not None
                and validation.get('actual_binary64_word_quality_vector_accepted') is True
                and not preservation_errors and len(results) == 11
                and all(r['status'] == 'COMPLETE_SAT_MAPPING_ONLY' for r in results))
    report = dict(schema='962-current24-fixed-HEAD499-QFNRA-adapter/v1', complete_candidate=complete,
        component_results=results, all11_component_IDs=list(COMPONENTS),
        unattempted_component_IDs=[r['component_ID'] for r in results if r.get('status') == 'UNATTEMPTED'],
        failure=failure, preservation_errors=preservation_errors, mapped_coordinate_count=len(all_mappings),
        complete_word_candidate=candidate_record, independent_word_validation=validation_record,
        source_records=SOURCES, edge_held=EDGE_HELD, input_records=input_records,
        input_map_canonical_sha256=INPUT_MAP_SHA256, static_source_input_packet_bytes=static_bytes,
        elapsed_before_report_seconds=time.monotonic()-started, captured_bytes_before_report=capture.total,
        cap_bytes=CAP, recorded_check_counts=[dict(component_ID=r['component_ID'], count=r.get('check_count'))
            for r in results if 'component_ID' in r and r['status'] != 'UNATTEMPTED'], no_retries=True,
        same_inherited_external_group_required=True, expected_external_group=expected_group,
        full_SMT_and_raw_session_streams_in_capture=True,
        old_external60s_gap_transferred_as_pass=False, full_external_startup_through_final_census_attested=False,
        report_candidate_requires_raw0_and_external_final_clock_identity_and_inclusive_census=True,
        installed_source_or_full_ABI_equivalence=False, complete_application_eligibility=None,
        geometry_application_authorized=False, global_embedding_accepted=False,
        physical_strength_material_LPBF_manufacturing_accepted=False)
    with (capture.root / 'report.json').open('xb') as handle:
        capture.record(handle, report, enforce=False)
    need(capture.total + static_bytes <= CAP and time.monotonic() < deadline,
         'Post-report known inclusive32MiB/helper60s gate failed; report is not acceptance')
    need(not preserved(sources_before, edge_before, payloads, input_records, packet_before),
         'Post-report source/input/packet preservation failed')
    need(complete, 'Incomplete HEAD499 operation; all available evidence retained')
    return report


def main():
    need(len(sys.argv) == 1, 'Fixed no-argument HEAD499 adapter only')
    result = run_head499()
    print(json.dumps(dict(complete_candidate=result['complete_candidate'], components=11,
                         mappings=48, original_cells=499, application_authorized=False), allow_nan=False))


if __name__ == '__main__':
    main()
