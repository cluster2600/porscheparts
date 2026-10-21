"""HELD fixed END-only native balance localization; no FEM, solver or assessor invocation."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct
import sys

ROOT = Path('project-role://engineering-checkout')
BASE = ROOT / 'work/962-engineering'
HERE = Path(__file__).resolve().parent
HELD = HERE / 'held-preparation.json'
NATIVE = BASE / 'cp1-oneway-cooling-release-linear-001'
OUTPUT = BASE / 'cp1-oneway-cooling-release-linear-END-native-balance-diagnostic-001'
AUTHORIZATION = BASE / 'cp1-oneway-cooling-release-linear-END-native-balance-diagnostic-root-execution-001/authorization.json'
REFUSAL_ACCEPTANCE = BASE / 'cp1-oneway-cooling-release-linear-assessment-root-execution-001/result-peer-acceptance.json'
FORCE = ('rx', 'ry', 'rz')
END_HEADER = ['disp_x', 'disp_y', 'disp_z', 'id', 'rx', 'ry', 'rz', 'temperature', 'x', 'y', 'z']
def need(ok, message):
    if not ok:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024**2), b''):
            h.update(part)
    return h.hexdigest()

def number(value):
    need(type(value) in (str, float, int), 'Explicit finite numeric scalar required')
    out = float(value)
    need(math.isfinite(out), 'Nonfinite scalar refused')
    return out

def support_masks(geometry, active_nodes, step, phase):
    need(type(step) is int and 0 <= step <= 182 and phase in ('begin', 'end'), 'Fixed183-step phase required')
    point = {(0, 0), (0, 1), (0, 2), (32, 1), (32, 2), (137, 2)}
    need(geometry.get(0) == (0., 0., 0.) and geometry.get(32) == (1., 0., 0.)
         and geometry.get(137) == (0., 1., 0.), 'Exact original six support IDs/positions required')
    clamp = {(tag, component) for tag in active_nodes if geometry[tag][2] == 0. for component in range(3)}
    need(len(clamp) == (135 if step < 80 else 255) and point <= clamp,
         'Exact45/85 active z=0 plane nodes and six remaining components required')
    constrained = clamp if step < 181 else point
    universe = {(tag, component) for tag in active_nodes for component in range(3)}
    free = universe - constrained
    need(constrained <= universe and not constrained & free and constrained | free == universe,
         'One complete disjoint constrained/free mask; no simultaneous clamp/point BCs')
    released = clamp - point if step == 181 and phase == 'begin' else set()
    # BEGIN181 is inherited END180 state, before the new free rows have equilibrated.
    # Only newly released components are exempt then; every END row is checked.
    need(not released or (len(released) == 249 and released <= free), 'Only249 newly released BEGIN181 components may be unequilibrated')
    return constrained, free, released


def compact(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def regular(path):
    need(path.is_file() and not path.is_symlink() and path.resolve() == path,
         'Exact original regular file required: ' + str(path))


def read_end(step, record, geometry, words, old, shared, storage):
    name = f'thermoelastic_end_{step:04d}.csv'
    path = NATIVE / name
    regular(path)
    raw = path.read_bytes()
    need(record == dict(path=str(path.relative_to(ROOT)), sha256=digest(raw), bytes=len(raw)),
         'Literal END CSV identity mismatch')
    table = list(csv.reader(io.StringIO(raw.decode('utf-8'), newline='')))
    need(table and table[0] == END_HEADER, 'Exact complete eleven-field END header order required')
    rows = table[1:]
    active = set(geometry) if step >= 80 else old
    expected_repeated = shared if step >= 80 else set()
    groups = {}; ids = []; id_tokens = []; word_stream = bytearray()
    for line, tokens in enumerate(rows, 2):
        need(len(tokens) == 11 and all(token != '' for token in tokens), 'No omitted/padded original END tokens')
        row = dict(zip(END_HEADER, tokens)); token = row['id']
        need(token.isascii() and token.isdigit(), 'Explicit nonnegative integer source ID token required')
        tag = int(token)
        need(tag in active and all(math.isfinite(float(value)) for value in tokens), 'Exact active finite END row required')
        xyz = tuple(number(row[key]) for key in 'xyz')
        need(struct.pack('<3d', *xyz) == words[tag], 'ID/coordinate binary64 association mismatch')
        groups.setdefault(tag, []).append((line, tokens)); ids.append(tag); id_tokens.append(token)
        word_stream.extend(struct.pack('<Q', tag) + words[tag])
    need(set(groups) == active and len(set(id_tokens)) == len(groups), 'Complete active source IDs/no lexical ID alias')
    repeats = sorted(tag for tag, group in groups.items() if len(group) > 1)
    need(set(repeats) == expected_repeated and all(len(group) == (2 if tag in expected_repeated else 1)
         for tag, group in groups.items()), 'Exact shared doublets only; no missing/nonshared/triple rows')
    duplicates = []
    for tag in repeats:
        group = groups[tag]
        need(group[0][1] == group[1][1], 'All eleven original tokens must match before any representative is selected')
        duplicates.append(dict(source_ID=tag, original_CSV_lines=[line for line, _ in group],
            header_plus_row_tokens_SHA256=[digest(compact([END_HEADER, tokens])) for _, tokens in group],
            all_present_header_tokens_lexically_identical=True,
            source_coordinate_binary64_LE_hex=words[tag].hex(), source_shared25_interface_member=True))
    multiplicity = {}; lexical = {}
    for group in groups.values():
        key = str(len(group)); multiplicity[key] = multiplicity.get(key, 0) + 1
    for token in set(id_tokens):
        key = str(id_tokens.count(token)); lexical[key] = lexical.get(key, 0) + 1
    full_storage_record = dict(path=str(path.relative_to(ROOT)), sha256=digest(raw), bytes=len(raw),
        kind='nodal', phase='end', step=step, header=END_HEADER, raw_rows=len(rows), unique_IDs=len(groups),
        multiplicity_counts=multiplicity, distinct_original_ID_tokens=len(set(id_tokens)),
        raw_ordered_ID_tokens=id_tokens, lexical_ID_multiplicity_counts=lexical, raw_ordered_source_IDs=ids,
        ordered_source_ID_u64_plus_coordinate_binary64_LE_sha256=digest(word_stream),
        all_rows_source_ID_coordinate_words_exact=True, duplicate_IDs=repeats, duplicate_groups=duplicates,
        all_duplicate_groups_full_row_lexically_identical=True)
    need(full_storage_record == storage['files'][name], 'Every complete accepted END storage record must match raw rows')
    # Selection is permitted only after complete alias/provenance validation above; raw storage is never changed.
    first = {tag: dict(zip(END_HEADER, group[0][1])) for tag, group in groups.items()}
    nodal = {tag: {key: number(row[key]) for key in FORCE} for tag, row in first.items()}
    evidence = dict(source=record, step=step, phase='end', header=END_HEADER, raw_rows=len(rows),
        unique_source_IDs=len(groups), full_token_shared_doublets=len(duplicates),
        raw_ordered_ID_tokens=id_tokens, raw_ordered_source_IDs=ids,
        source_ID_coordinate_stream_sha256=digest(word_stream),
        complete_accepted_storage_record_compact_JSON_sha256=digest(compact(full_storage_record)),
        sorted_reaction_token_and_binary64_stream_sha256=digest(compact([
            [tag, [first[tag][key] for key in FORCE], [nodal[tag][key].hex() for key in FORCE]] for tag in sorted(active)])),
        duplicate_groups=duplicates, all_aliases_checked_before_first_representative=True)
    return nodal, first, groups, active, evidence


def end_balance_rows(nodal, geometry, active_nodes, constraints):
    reaction = [[nodal[n][k] if (n, j) in constraints else 0. for j, k in enumerate(FORCE)] for n in sorted(active_nodes)]
    all_forces = [[nodal[n][k] for k in FORCE] for n in sorted(active_nodes)]
    rows = []
    for rowset, force_rows in zip(('reaction', 'all_forces'), (reaction, all_forces)):
        for j in range(3):
            force_sum = math.fsum(v[j] for v in force_rows)
            moment_sum = math.fsum(geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3] for n, v in zip(sorted(active_nodes), force_rows))
            force_terms = [v[j] for v in force_rows]
            moment_terms = [geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3] for n, v in zip(sorted(active_nodes), force_rows)]
            rows.append(dict(rowset=rowset, component=j, force_N=force_sum, force_binary64_hex=force_sum.hex(),
                force_absolute_error_N=abs(force_sum - 0.), force_limit_N=1e-7,
                force_exceeds_unchanged_gate=not (abs(force_sum - 0.) <= 1e-7),
                moment_Nm=moment_sum, moment_binary64_hex=moment_sum.hex(),
                moment_absolute_error_Nm=abs(moment_sum - 0.), moment_limit_Nm=1e-7,
                moment_exceeds_unchanged_gate=not (abs(moment_sum - 0.) <= 1e-7),
                sorted_source_ID_u64_LE_sha256=digest(b''.join(struct.pack('<Q', tag) for tag in sorted(active_nodes))),
                force_terms_binary64_LE_sha256=digest(b''.join(struct.pack('<d', value) for value in force_terms)),
                moment_terms_binary64_LE_sha256=digest(b''.join(struct.pack('<d', value) for value in moment_terms))))
    return rows


def main(refusal_acceptance_sha256=None, authorization_sha256=None):
    # Both absent external hashes refuse before loading metadata or reading any raw field body.
    need(all(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value)
             for value in (refusal_acceptance_sha256, authorization_sha256)),
         'HELD: exact completed-refusal acceptance and separate root authorization digests are required')
    regular(REFUSAL_ACCEPTANCE); regular(AUTHORIZATION); regular(HELD)
    need(sha(REFUSAL_ACCEPTANCE) == refusal_acceptance_sha256 and sha(AUTHORIZATION) == authorization_sha256,
         'Exact external admission digest mismatch')
    held = json.loads(HELD.read_text()); authorization = json.loads(AUTHORIZATION.read_text())
    need(authorization.get('schema') == '962-linear-cooling-END-native-balance-diagnostic-authorization/v1'
         and authorization.get('diagnostic_execution_authorized') is True
         and authorization.get('root_and_independent_source_review_complete') is True
         and all(authorization.get(key) is False for key in ('native_execution_authorized', 'assessment_execution_authorized',
             'automatic_retry', 'head_execution_authorized', 'engineering_accepted', 'physics_qualified',
             'material_qualified', 'process_calibrated', 'manufacturing_authorized')),
         'Only separately reviewed fixed saved-END balance localization is authorized')
    need(authorization.get('source') == held['source'] and authorization.get('held') == dict(
         path=str(HELD.relative_to(ROOT)), sha256=sha(HELD), bytes=HELD.stat().st_size)
         and authorization.get('refusal_root_acceptance') == dict(path=str(REFUSAL_ACCEPTANCE.relative_to(ROOT)),
             sha256=refusal_acceptance_sha256, bytes=REFUSAL_ACCEPTANCE.stat().st_size), 'Source/held/refusal admission bindings required')
    need(authorization.get('ordinary_seconds') == 60 and authorization.get('TERM_grace_seconds') == 8
         and authorization.get('sampled_RSS_stop_bytes') == 2147483648
         and authorization.get('sampled_output_stop_bytes') == 33554432
         and authorization.get('new_owned_session') is True and authorization.get('verified_owned_KILL_wait') is True,
         'Separate ordinary60s/T8/2GiB/32MiB owned lifecycle required')
    refusal = json.loads(REFUSAL_ACCEPTANCE.read_text())
    need(refusal.get('schema') == '962-linear-cooling-root-terminal-strict-assessment-refusal-acceptance/v1'
         and refusal.get('decision') == 'ACCEPT_PRESERVATION_OF_STRICT_NATIVE_GLOBAL_FORCE_BALANCE_ASSESSMENT_REFUSAL_ONLY'
         and refusal.get('assessment_result_absent') is True
         and refusal.get('full183_366_phase_7_SI_result_not_accepted') is True,
         'Completed strict refusal preservation only; no field acceptance transfer')
    need(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'Fresh fixed diagnostic output required')
    for name, expected in held['metadata_input_sha256'].items():
        path = ROOT / name; regular(path)
        need(sha(path) == expected, 'Fixed source/control metadata changed')
    native_closed = json.loads((ROOT / held['native_root_closed']['path']).read_text())
    capture_accept = json.loads((ROOT / held['native_capture_root_acceptance']['path']).read_text())
    storage = json.loads((ROOT / held['complete_storage_result']['path']).read_text())
    storage_accept = json.loads((ROOT / held['storage_root_acceptance']['path']).read_text())
    transfer = json.loads((ROOT / held['accepted_transfer_manifest']['path']).read_text())
    policy = json.loads((ROOT / held['POLICY']['path']).read_text())['absolute_SI_limits']
    need(policy == held['unchanged_seven_absolute_SI_limits'] and policy['force_N'] == 1e-7
         and policy['moment_Nm'] == 1e-7, 'No SI criterion or limit change')
    need(capture_accept.get('schema') == held['native_capture_root_acceptance_schema']
         and storage_accept.get('schema') == '962-linear-cooling-root-complete-lexical-storage-acceptance/v1'
         and storage_accept.get('decision') == 'ACCEPT_COMPLETE_NODAL_REFERENCE_LEXICAL_STORAGE_FOR_SEPARATE_SEVEN_SI_ASSESSMENT'
         and storage.get('status') == 'PASS_OBSERVED_MULTIPLICITY_AND_LEXICAL_ASSOCIATIONS_ONLY'
         and storage.get('negatives') == [] and storage.get('scanned_CSVs') == 732,
         'Separate exact completed capture/storage proof required')
    need(set(held['end_csv_records']) == {f'thermoelastic_end_{step:04d}.csv' for step in range(183)},
         'Exactly183 fixed END identities required')
    for name, record in held['end_csv_records'].items():
        need(native_closed['outputs'].get(name) == record, 'Literal END identity must join current capture')
    geometry = {}; words = {}; old = set(); born = set(); shared = set()
    for row in transfer['node_rows']:
        tag = row['source_node_id']; xyz = tuple(row['coordinates_m'])
        need(type(tag) is int and tag >= 0 and tag not in geometry and len(xyz) == 3
             and all(type(value) is float and math.isfinite(value) for value in xyz)
             and [value.hex() for value in xyz] == row['binary64_hex'], 'Exact typed425 source map required')
        geometry[tag] = xyz; words[tag] = struct.pack('<3d', *xyz)
        if row['old2']: old.add(tag)
        if row['born3']: born.add(tag)
        if row['shared']: shared.add(tag)
    need(len(geometry) == 425 and len(old) == len(born) == 225 and len(shared) == 25
         and old | born == set(geometry) and old & born == shared, 'Fixed complete active membership required')
    need(storage['source_node_map']['ID_to_coordinate_binary64_LE_hex'] == {
         str(tag): words[tag].hex() for tag in sorted(words)}, 'Accepted storage425 source-coordinate proof required')
    balances = []; file_evidence = {}; first_failure = None; first_force = None; first_moment = None
    maxima = {}; witnesses = {}; counts = dict(files=0, raw_rows=0, unique_node_phases=0, shared_doublet_groups=0)
    for step in range(183):
        name = f'thermoelastic_end_{step:04d}.csv'
        nodal, tokens, groups, active, evidence = read_end(step, held['end_csv_records'][name], geometry, words, old, shared, storage)
        constraints, free, released = support_masks(geometry, active, step, 'end')
        need(not released, 'No END component is exempt as a newly released BEGIN row')
        file_evidence[name] = evidence
        counts['files'] += 1; counts['raw_rows'] += evidence['raw_rows']
        counts['unique_node_phases'] += evidence['unique_source_IDs']
        counts['shared_doublet_groups'] += evidence['full_token_shared_doublets']
        for row in end_balance_rows(nodal, geometry, active, constraints):
            row['step'] = step; balances.append(row)
            for unit, value, error, exceeds in [
                ('force_N', row['force_N'], row['force_absolute_error_N'], row['force_exceeds_unchanged_gate']),
                ('moment_Nm', row['moment_Nm'], row['moment_absolute_error_Nm'], row['moment_exceeds_unchanged_gate'])]:
                event = dict(step=step, rowset=row['rowset'], component=row['component'], unit=unit,
                    value=value, binary64_hex=value.hex(), absolute_error=error, unchanged_limit=policy[unit])
                if exceeds:
                    if first_failure is None: first_failure = event
                    if unit == 'force_N' and first_force is None: first_force = event
                    if unit == 'moment_Nm' and first_moment is None: first_moment = event
                if unit not in maxima or error > maxima[unit]['absolute_error']:
                    maxima[unit] = event
                    witnesses[unit] = dict(event=event, CSV=held['end_csv_records'][name],
                        sorted_source_ID_contributions=[dict(source_ID=tag,
                            original_CSV_lines=[line for line, _ in groups[tag]],
                            raw_rx_ry_rz_tokens=[tokens[tag][key] for key in FORCE],
                            native_rx_ry_rz_binary64_hex=[nodal[tag][key].hex() for key in FORCE],
                            coordinate_binary64_LE_hex=words[tag].hex(),
                            constrained_components=[component for component in range(3) if (tag, component) in constraints])
                            for tag in sorted(active)])
    need(counts == dict(files=183, raw_rows=64350, unique_node_phases=61775, shared_doublet_groups=2575)
         and len(balances) == 1098, 'Complete183 END/2rowsets/3components force and moment observations required')
    for name, record in held['end_csv_records'].items():
        need(sha(NATIVE / name) == record['sha256'], 'Original END CSV changed during diagnostic')
    for name, expected in held['metadata_input_sha256'].items():
        need(sha(ROOT / name) == expected, 'Source/control metadata changed during diagnostic')
    need(sha(REFUSAL_ACCEPTANCE) == refusal_acceptance_sha256 and sha(AUTHORIZATION) == authorization_sha256,
         'External completed admission changed')
    result = dict(schema='962-linear-cooling-END-native-balance-localization/v1',
        status='COMPLETED_FIXED_SAVED_BALANCE_LOCALIZATION_ONLY', counts=counts,
        component_sum_records=balances, force_sum_count=1098, moment_sum_count=1098,
        first_failure_in_assessor_END_balance_order=first_failure, first_force_failure=first_force,
        first_moment_failure=first_moment, maxima=maxima, maximum_witnesses=witnesses,
        all183_original_END_input_evidence=file_evidence,
        source_ID_coordinate_binary64_LE_hex={str(tag): words[tag].hex() for tag in sorted(words)},
        lexical_duplicates_verified_before_representative=True, raw_storage_rewritten_or_averaged=False,
        sum_order='step0..182; reaction then all_forces; component0..2; force before moment; sorted source IDs',
        force_and_moment_limits_unchanged=True, numerical_cause=None, solver_cause=None,
        IEEE_floor_or_feasibility_claim=None, full_assessor_reexecuted=False, FEM_QP_CDF_geometry_evaluated=False,
        seven_SI_or_fields_accepted=False, native_execution_authorized=False, engineering_accepted=False,
        physics_qualified=False, material_qualified=False, process_calibrated=False, manufacturing_authorized=False)
    encoded = (json.dumps(result, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    need(len(encoded) <= 33554432 and not OUTPUT.exists(), 'Fresh bounded diagnostic JSON only')
    OUTPUT.mkdir()
    with (OUTPUT / 'diagnostic.json').open('xb') as stream: stream.write(encoded)
    print(json.dumps(dict(status=result['status'], counts=counts, first_failure=first_failure, maxima=maxima)))


if __name__ == '__main__':
    need(len(sys.argv) in (1, 3), 'Exactly two external admission digests or held invocation required')
    main(*(sys.argv[1:] if len(sys.argv) == 3 else (None, None)))
