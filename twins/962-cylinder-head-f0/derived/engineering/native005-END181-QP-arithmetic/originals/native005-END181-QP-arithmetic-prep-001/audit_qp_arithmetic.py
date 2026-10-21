"""HELD fixed END181 arithmetic diagnosis; execution requires separate root review."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import types
from fractions import Fraction

ROOT = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
OUTPUT = ROOT / 'work/962-engineering/native005-END181-QP-arithmetic-execution-001'
REPORT = {'path': 'work/962-engineering/native005-END181-equilibrium-execution-001/diagnostic.json', 'sha256': 'c50b2079da852028a65526577fa00011a82bfa1f61845b612e1b4d80d0a713c9', 'bytes': 1024623}
ASSESSOR = {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-assessor-prep-001/assess.py', 'sha256': 'aa7ee403a0a3078df58410815f2b613aaeb9634bd14bc9c90517ce00cec7f2d5', 'bytes': 46645}
POLICY = {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-assessor-prep-001/POLICY.json', 'sha256': 'a87df89f84706b36c0b665c0e9eac928e3c9b2b45f5a2921442b2d6403f4a638', 'bytes': 5013}
QP = {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/thermoelastic_end_fields_0181.csv', 'sha256': '807e97378f87b5e94c1b20539abe6859eab2a053f91598d9f9010a01d3395e8a', 'bytes': 1370249}
NODAL = {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/thermoelastic_end_0181.csv', 'sha256': '9970cbfd2e3d11f584e5b38615f9d92e02e00ce240b1c3f88c59716bed899f8e', 'bytes': 71995}
PYTHON = {'path': '/Users/maxime/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12', 'sha256': '1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60', 'bytes': 49968}
SELECTED_PYTHON = '/Users/maxime/.codex/worktrees/962-watercooled-head/3dprinting993/work/962-head/check-venv/bin/python'
PINS = {'derived_report': REPORT, 'assessor': ASSESSOR, 'POLICY': POLICY,
        'QP_CSV': QP, 'nodal_CSV': NODAL, 'selected_Python_body': PYTHON}
LIMITS = {'temperature_K': 1e-10, 'displacement_m': 1e-12, 'QP_coordinate_m': 2e-13,
          'strain': 1e-10, 'stress_Pa': .1, 'force_N': 1e-7, 'moment_Nm': 1e-7}
CHANNELS = ('computed', 'stored_QP')
BAD_DOFS = ((0, 0), (32, 1), (32, 2))
CAP = 32 * 1024**2
PACKET_NAMES = ('audit_qp_arithmetic.py', 'input-manifest.json', 'METHOD.md', 'source-reuse.json', 'index.json')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def checked_bytes(pin):
    path = ROOT / pin['path']
    need(path.is_file() and not path.is_symlink() and path.resolve() == path, 'Fixed regular canonical input required')
    need(path.stat().st_size == pin['bytes'], 'Fixed input byte count changed')
    raw = path.read_bytes()
    need(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'], 'Fixed input identity changed')
    return raw


def descriptor(path, raw):
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def word(value):
    need(type(value) is float and math.isfinite(value), 'Finite binary64 operand required')
    return value.hex()


def exact(value):
    need(type(value) is float and math.isfinite(value), 'Finite binary64 rational conversion required')
    return Fraction.from_float(value)


def ratio(value):
    return [value.numerator, value.denominator]


def display(value):
    rounded = float(value)
    need(math.isfinite(rounded), 'Finite diagnostic display required')
    return dict(exact_ratio=ratio(value), once_rounded_binary64_hex=rounded.hex())


def vector_rows(values, active, constraints, rowset):
    return [[values[tag][j] if rowset == 'all' or ((tag, j) in constraints) == (rowset == 'constrained') else 0.
             for j in range(3)] for tag in sorted(active)]


def resultants(values, geometry, active, constraints):
    out = {}
    for rowset in ('constrained', 'free', 'all'):
        force_rows = vector_rows(values, active, constraints, rowset)
        components = []
        for j in range(3):
            force_sum = math.fsum(v[j] for v in force_rows)
            moment_sum = math.fsum(geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3] for n, v in zip(sorted(active), force_rows))
            components.append(dict(component=j, force_N=force_sum, force_binary64_hex=force_sum.hex(),
                moment_Nm=moment_sum, moment_binary64_hex=moment_sum.hex(),
                force_L1_N=math.fsum(abs(v[j]) for v in force_rows),
                force_max_abs_term_N=max(abs(v[j]) for v in force_rows),
                moment_L1_Nm=math.fsum(abs(geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3]) for n, v in zip(sorted(active), force_rows)),
                original_force_limit_N=1e-7, original_moment_limit_Nm=1e-7,
                force_exceeds_original_gate=not (abs(force_sum - 0.) <= 1e-7),
                moment_exceeds_original_gate=not (abs(moment_sum - 0.) <= 1e-7)))
        out[rowset] = components
    return out


def exact_resultants(values, geometry, constraints):
    """Exact postprocessing of the supplied rational force values; no rounding first."""
    out = {}
    for rowset in ('constrained', 'free', 'all'):
        selected = {n: [values[n][j] if rowset == 'all' or ((n, j) in constraints) == (rowset == 'constrained')
                        else Fraction(0) for j in range(3)] for n in sorted(geometry)}
        components = []
        for j in range(3):
            forces = [selected[n][j] for n in sorted(geometry)]
            moments = [exact(geometry[n][(j+1)%3])*selected[n][(j+2)%3]
                       - exact(geometry[n][(j+2)%3])*selected[n][(j+1)%3] for n in sorted(geometry)]
            force_sum, moment_sum = sum(forces, Fraction(0)), sum(moments, Fraction(0))
            components.append(dict(component=j, force=display(force_sum), moment=display(moment_sum),
                force_L1=ratio(sum(map(abs, forces), Fraction(0))), force_max=ratio(max(map(abs, forces))),
                moment_L1=ratio(sum(map(abs, moments), Fraction(0))), moment_max=ratio(max(map(abs, moments))),
                unchanged_force_limit_binary64_hex=LIMITS['force_N'].hex(),
                unchanged_moment_limit_binary64_hex=LIMITS['moment_Nm'].hex(),
                force_exceeds_original_gate=abs(force_sum) > exact(LIMITS['force_N']),
                moment_exceeds_original_gate=abs(moment_sum) > exact(LIMITS['moment_Nm'])))
        out[rowset] = components
    return out


def fixed_context(report, assessor, nodal_path):
    need(report['schema'] == '962-native005-END181-unchanged-kernel-equilibrium-diagnostic/v1'
         and report['status'] == 'COMPLETE_SINGLE_PHASE_DIAGNOSTIC_ONLY'
         and report['step'] == 181 and report['phase'] == 'end', 'Exact completed END181 report required')
    need(report['unchanged_seven_absolute_SI_limits'] == LIMITS and report['unchanged_POLICY'] == POLICY
         and report['assessor_source'] == ASSESSOR, 'Original source/POLICY associations changed')
    need(report['raw_inputs']['thermoelastic_end_0181.csv'] == NODAL
         and report['raw_inputs']['thermoelastic_end_fields_0181.csv'] == QP, 'Same-run raw descriptor join required')
    geometry = {int(n): struct.unpack('<3d', bytes.fromhex(h))
                for n, h in report['complete_source_ID_coordinate_binary64_LE_hex'].items()}
    need(set(geometry) == set(range(425)) and all(all(math.isfinite(x) for x in p) for p in geometry.values()),
         'Complete425 finite saved coordinate words required')
    rows = report['complete_ordered_HEX8_cells']
    cells = {r['source_cell_ID']: r['nodes'] for r in rows}
    need(len(rows) == len(cells) == 256 and all(type(n) is int for n in cells)
         and all(len(c) == len(set(c)) == 8 and set(c) <= set(geometry) for c in cells.values()),
         'Complete256 tagged ordered HEX8 cells required')
    orders = report['exact_region_assembly_iteration_order']
    need([r['region'] for r in orders] == ['old2', 'born3'], 'Original region order required')
    memberships = []
    for order, block in zip(orders, (2, 3)):
        tags, nodes = order['cell_iteration_order'], order['node_iteration_order']
        need(len(tags) == len(set(tags)) == 128 and set(tags) <= set(cells)
             and set(tags) == {r['source_cell_ID'] for r in rows if r['block'] == block}
             and len(nodes) == len(set(nodes)) == 225 and set(nodes) == {n for t in tags for n in cells[t]},
             'Exact original regional cell/node iteration membership required')
        memberships.append(set(nodes))
    need(set(orders[0]['cell_iteration_order']).isdisjoint(orders[1]['cell_iteration_order'])
         and set(orders[0]['cell_iteration_order']) | set(orders[1]['cell_iteration_order']) == set(cells)
         and memberships[0] | memberships[1] == set(geometry) and len(memberships[0] & memberships[1]) == 25,
         'Complete disjoint cell and shared25 node cover required')
    shared = memberships[0] & memberships[1]
    nodal, storage = assessor.node_sample(nodal_path, geometry, set(geometry),
                                         (*assessor.DISP, 'temperature', *assessor.FORCE), shared)
    need(storage == report['END181_nodal_storage'], 'Complete native nodal storage/lexical-doublet join required')
    refs = report['own_BEGIN80_reference']['born_u_and_Tref']
    need(len(refs) == 225 and {r['source_ID'] for r in refs} == memberships[1], 'Complete own BEGIN80 born references required')
    born_u = {r['source_ID']: [float.fromhex(x) for x in r['u_hex']] for r in refs}
    born_T = {r['source_ID']: float.fromhex(r['Tref_hex']) for r in refs}
    for r in refs:
        need([word(x) for x in r['u']] == [word(x) for x in born_u[r['source_ID']]]
             and word(r['Tref_K']) == word(born_T[r['source_ID']]), 'Saved reference values and words disagree')
    constraints = {tuple(r) for r in report['constrained_DOFs']}
    expected, free, released = assessor.support_masks(geometry, set(geometry), 181, 'end')
    need(constraints == expected and len(constraints) == 6 and len(free) == 1269 and not released,
         'Original expected six-DOF partition required; no live-BC claim')
    observations = report['all1275_native_vs_assembled_component_observations']
    old = {(r['source_ID'], r['component']): r for r in observations}
    need(len(old) == len(observations) == 1275 and set(old) == {(n, j) for n in geometry for j in range(3)},
         'Complete original1275 component associations required')
    for (n, j), r in old.items():
        need(word(nodal[n][assessor.FORCE[j]]) == r['native_binary64_hex']
             and word(r['native_force_N']) == r['native_binary64_hex']
             and word(r['assembled_force_N']) == r['assembled_binary64_hex']
             and r['constrained'] is ((n, j) in constraints)
             and r['coordinate_binary64_LE_hex'] == struct.pack('<3d', *geometry[n]).hex(),
             'Exact same-run native/constitutive force/coordinate/partition join failed')
    return geometry, cells, orders, nodal, born_u, born_T, constraints, old


def arithmetic(report, assessor):
    geometry, cells, orders, nodal, born_u, born_T, constraints, old = fixed_context(report, assessor, ROOT / NODAL['path'])
    qcoords = {}
    qp = assessor.quadrature_sample(ROOT / QP['path'], geometry, cells, set(cells), qcoords, LIMITS['QP_coordinate_m'])
    need(len(qp) == len(qcoords) == 2048, 'Complete2048 native-to-physical QP associations required')
    A = {ch: {n: [0.] * 3 for n in geometry} for ch in CHANNELS}
    kernel_A = {ch: {n: [0.] * 3 for n in geometry} for ch in CHANNELS}
    B = {ch: {n: [Fraction(0)] * 3 for n in geometry} for ch in CHANNELS}
    C = {ch: {n: [Fraction(0)] * 3 for n in geometry} for ch in CHANNELS}
    seeds, merge_trace = [], []
    witnesses = {str(n) + ':' + str(j): [] for n, j in BAD_DOFS}
    for order in orders:
        label, node_order = order['region'], order['node_iteration_order']
        region = {ch: {n: [0.] * 3 for n in node_order} for ch in CHANNELS}
        kernel_region = {ch: {n: [0.] * 3 for n in node_order} for ch in CHANNELS}
        for cell in order['cell_iteration_order']:
            conn = cells[cell]
            points = [geometry[n] for n in conn]
            ru = [assessor.ZERO[0] for n in conn] if label == 'old2' else [born_u[n] for n in conn]
            rt = [400. for n in conn] if label == 'old2' else [born_T[n] for n in conn]
            state = assessor.mechanical_state(points, [[nodal[n][k] for k in assessor.DISP] for n in conn],
                                               [nodal[n]['temperature'] for n in conn], ru, rt)
            rule = assessor.hex_rule(points)
            for q in range(8):
                index, stored = qp[(cell, q)]
                xyz, gradients, weight, fields = state[index]
                need(rule[index][2] == gradients and word(rule[index][3]) == word(weight), 'Original gradient/weight generation changed')
                stress_channels = {'computed': fields['stress'], 'stored_QP': stored['stress']}
                seed = dict(region=label, cell=cell, native_QP=q, physical_rule_index=index, nodes=conn,
                    native_coordinate_words_LE=struct.pack('<3d', *qcoords[(cell, q)]).hex(),
                    rule_coordinate_words_LE=struct.pack('<3d', *xyz).hex(),
                    gradient_words=[[word(x) for x in grad] for grad in gradients], weight_word=word(weight),
                    stress_words={ch: [[word(x) for x in row] for row in stress] for ch, stress in stress_channels.items()},
                    rounded_contribution_words={})
                for ch, stress in stress_channels.items():
                    assessor.accumulate(kernel_region[ch], conn, gradients, weight, stress)
                    contributions = []
                    for n, grad in zip(conn, gradients):
                        node_contributions = []
                        for i in range(3):
                            products = [stress[i][j] * grad[j] for j in range(3)]
                            dot = math.fsum(products)
                            contribution = weight * dot
                            before = region[ch][n][i]
                            region[ch][n][i] += contribution
                            b = exact(contribution)
                            c = exact(weight) * sum((exact(stress[i][j]) * exact(grad[j]) for j in range(3)), Fraction(0))
                            B[ch][n][i] += b
                            C[ch][n][i] += c
                            node_contributions.append(word(contribution))
                            if (n, i) in BAD_DOFS:
                                witnesses[str(n) + ':' + str(i)].append(dict(channel=ch, seed_index=len(seeds),
                                    region=label, cell=cell, native_QP=q, component=i, source_ID=n,
                                    product_words=[word(x) for x in products], fsum_word=word(dot),
                                    weighted_contribution_word=word(contribution), region_before_word=word(before),
                                    region_after_word=word(region[ch][n][i]), B_contribution=ratio(b), C_contribution=ratio(c)))
                        contributions.append(node_contributions)
                    seed['rounded_contribution_words'][ch] = contributions
                seeds.append(seed)
        for ch in CHANNELS:
            for n in node_order:
                need([word(x) for x in region[ch][n]] == [word(x) for x in kernel_region[ch][n]],
                     'Manual A regional trace must exactly match unchanged accumulate')
                before = [word(x) for x in A[ch][n]]
                for j in range(3):
                    A[ch][n][j] += region[ch][n][j]
                    kernel_A[ch][n][j] += kernel_region[ch][n][j]
                merge_trace.append(dict(channel=ch, region=label, source_ID=n, before_words=before,
                    region_words=[word(x) for x in region[ch][n]], after_words=[word(x) for x in A[ch][n]]))
    need(len(seeds) == 2048 and len(merge_trace) == 900, 'Full QP/region-merge trace required')
    components = []
    for n in sorted(geometry):
        for j in range(3):
            prior = old[(n, j)]
            need(word(A['computed'][n][j]) == prior['assembled_binary64_hex'],
                 'A_computed must exactly reproduce every prior constitutively assembled word')
            channels = {}
            for ch in CHANNELS:
                need(word(A[ch][n][j]) == word(kernel_A[ch][n][j]), 'A source-kernel/global trace mismatch')
                a, b, c = exact(A[ch][n][j]), B[ch][n][j], C[ch][n][j]
                channels[ch] = dict(A_word=word(A[ch][n][j]), B=display(b), C=display(c),
                                    A_minus_B=ratio(a-b), B_minus_C=ratio(b-c), A_minus_C=ratio(a-c),
                                    native_CSV_minus_A_word=ratio(exact(prior['native_force_N'])-a))
            components.append(dict(source_ID=n, component=j, constrained=(n, j) in constraints,
                native_CSV_word=prior['native_binary64_hex'], prior_constitutive_word=prior['assembled_binary64_hex'], channels=channels,
                computed_minus_stored_QP=dict(A=ratio(exact(A['computed'][n][j])-exact(A['stored_QP'][n][j])),
                    B=ratio(B['computed'][n][j]-B['stored_QP'][n][j]), C=ratio(C['computed'][n][j]-C['stored_QP'][n][j]))))
    aggregates, exact_A, checks = {}, {}, []
    for ch in CHANNELS:
        aggregates[ch] = {'A': resultants(A[ch], geometry, set(geometry), constraints),
                          'B': exact_resultants(B[ch], geometry, constraints), 'C': exact_resultants(C[ch], geometry, constraints)}
        exact_A[ch] = exact_resultants({n: list(map(exact, A[ch][n])) for n in geometry}, geometry, constraints)
        for variant, sums in aggregates[ch].items():
            for rowset, rows in sums.items():
                for row in rows:
                    for quantity, unit in (('force', 'force_N'), ('moment', 'moment_Nm')):
                        value = dict(binary64_hex=row[quantity + '_binary64_hex']) if variant == 'A' else row[quantity]
                        checks.append(dict(channel=ch, variant=variant, rowset=rowset, component=row['component'],
                            quantity=quantity, conventional_unit_label_from_frozen_assessor=unit, value=value,
                            unchanged_limit_binary64_hex=LIMITS[unit].hex(),
                            exceeds_original_gate=row[quantity + '_exceeds_original_gate']))
    need(all(rows and {r['channel'] for r in rows} == set(CHANNELS) for rows in witnesses.values()),
         'Both complete stress-channel contribution lists required for all three failed native DOFs')
    need(len(components) == 1275 and len(checks) == 108 and len(report['all36_aggregate_checks']) == 36
         and len(report['original12_native_aggregate_checks']) == 12, 'Complete separate original/variant accounting required')
    return dict(schema='962-native005-END181-QP-arithmetic-diagnostic/v1', status='COMPLETE_ARITHMETIC_DIAGNOSTIC_ONLY',
        original36_aggregate_checks=report['all36_aggregate_checks'], original12_native_aggregate_checks=report['original12_native_aggregate_checks'],
        original36_count=36, derived_variant_aggregate_count=108, derived_variant_checks=checks,
        variant_resultants=aggregates, exact_postprocessing_of_A_words=exact_A,
        all1275_component_comparisons=components, all2048_operand_seeds=seeds,
        complete_original_region_order=orders, complete900_region_merges=merge_trace,
        three_failed_native_DOF_contribution_witnesses=witnesses,
        complete_source_ID_coordinate_binary64_LE_hex=report['complete_source_ID_coordinate_binary64_LE_hex'],
        complete_ordered_HEX8_cells=report['complete_ordered_HEX8_cells'], constrained_DOFs=report['constrained_DOFs'],
        A_computed_matches_all1275_prior_constitutive_words=True, both_A_channels_match_frozen_accumulate=True,
        B_definition='Exact global sum of identical already-rounded weight*fsum contributions; no regional or global merge rounding.',
        C_definition='Exact products and sums of the frozen binary64 stress/gradient/weight operands; no exact geometry/quadrature/constitutive or solver claim.',
        A_definition='Original per-region product/fsum/weight/in-place accumulation then original old2/born3 node-order merges.',
        exact_moment_definition='Exact cross products and sums of unrounded rational forces with saved coordinate words; A separately retains original rounded node terms/fsum.',
        ratio_encoding='[signed numerator, positive denominator]; from exact binary64 words, never decimal displays. Rational zero has no sign; once-rounded display is +0.',
        stored_QP_and_computed_stress_provenance_separate=True, native_CSV_is_separate_third_provenance=True,
        old36_failures_preserved_without_reclassification=True, unchanged_POLICY=POLICY,
        solver_convergence_or_cause_established=False, replacement_force_field_created=False,
        field_force_physics_material_LPBF_manufacturing_acceptance=False, full_assessor_executed=False,
        new_solver_or_native_execution=False, retry=False)


def main():
    need(len(sys.argv) == 1 and sys.version_info[:3] == (3, 12, 11)
         and sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode,
         'Fixed no-argument selected Python3.12.11 -B -I -S required')
    need(str(Path(sys.executable).resolve()) == PYTHON['path'], 'Selected Python body path changed')
    need(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'Fixed output must be absent, including dangling symlink')
    source_path = Path(__file__).resolve()
    packet = {}
    for name in PACKET_NAMES:
        path = source_path.parent / name
        need(path.is_file() and not path.is_symlink() and path.resolve() == path, 'Fixed regular source-packet file required')
        packet[name] = path.read_bytes()
    before = {name: checked_bytes(pin) for name, pin in PINS.items()}
    need(json.loads(before['POLICY'])['absolute_SI_limits'] == LIMITS, 'All seven unchanged absolute thresholds required')
    assessor = types.ModuleType('fixed_native005_QP_arithmetic_assessor')
    assessor.__file__ = str(ROOT / ASSESSOR['path'])
    exec(compile(before['assessor'], assessor.__file__, 'exec'), assessor.__dict__)
    result = arithmetic(json.loads(before['derived_report']), assessor)
    need(all(checked_bytes(pin) == before[name] for name, pin in PINS.items()), 'Final scientific/source/runtime identity changed')
    need(all((source_path.parent / name).read_bytes() == raw for name, raw in packet.items()), 'Source packet changed')
    result['fixed_input_source_runtime_records'] = PINS
    result['source_packet_records'] = {name: descriptor(source_path.parent / name, raw) for name, raw in packet.items()}
    result['observed_Python'] = dict(version=list(sys.version_info[:3]), executable=sys.executable,
        selected_alias=SELECTED_PYTHON, expected_body=PYTHON, isolated=sys.flags.isolated, no_site=sys.flags.no_site,
        bytecode_disabled=sys.dont_write_bytecode, stdlib_only=True, full_ABI_or_transitive_stdlib_closure=False)
    result['before_and_after_pins_equal_before_report_write'] = True
    raw = json.dumps(result, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode() + b'\n'
    known_input_bytes = sum(pin['bytes'] for pin in PINS.values()) + sum(map(len, packet.values()))
    need(known_input_bytes + len(raw) <= CAP, 'Complete report exceeds scoped32MiB; refuse without truncation')
    OUTPUT.mkdir()
    with (OUTPUT / 'report.json').open('xb') as stream:
        stream.write(raw)
    need(all(checked_bytes(pin) == before[name] for name, pin in PINS.items())
         and all((source_path.parent / name).read_bytes() == saved for name, saved in packet.items()),
         'Post-write input/source/runtime preservation failed')
    receipt = dict(schema='962-native005-END181-QP-arithmetic-execution-receipt/v1',
        status='COMPLETE_DIAGNOSTIC_PENDING_RAW_PARENT_STATUS_AND_REVIEW', report=descriptor(OUTPUT / 'report.json', raw),
        fixed_input_source_runtime_records=PINS, source_packet_records=result['source_packet_records'],
        complete_before_after_equal=True, known_input_and_packet_bytes=known_input_bytes,
        outer_timeout_seconds=20, thread_environment_expected=1, child_RSS_sampled=None,
        cap_bytes=CAP, full_parent_stream_control_census_required=True,
        full_ABI_or_transitive_stdlib_closure=False, scientific_qualification=False)
    receipt_raw = json.dumps(receipt, indent=2, allow_nan=False).encode() + b'\n'
    need(known_input_bytes + len(raw) + len(receipt_raw) <= CAP, 'Complete receipt exceeds scoped32MiB; refuse without truncation')
    with (OUTPUT / 'execution-receipt.json').open('xb') as stream:
        stream.write(receipt_raw)
    need(all(checked_bytes(pin) == before[name] for name, pin in PINS.items())
         and all((source_path.parent / name).read_bytes() == saved for name, saved in packet.items()),
         'Final post-receipt input/source/runtime preservation failed')
    print(json.dumps(dict(status=result['status'], components=1275, QP_seeds=2048, original_checks=36,
        derived_checks=108, derived_exceedances=sum(r['exceeds_original_gate'] for r in result['derived_variant_checks']),
        report_sha256=hashlib.sha256(raw).hexdigest(), report_bytes=len(raw)), allow_nan=False))


if __name__ == '__main__':
    main()
