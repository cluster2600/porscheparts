"""Independent finite saved-report check; never imports/runs target or raw inputs."""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import json
import struct

E = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering')
D = E / 'native005-END181-QP-arithmetic-execution-001'
W = E / 'native005-END181-QP-arithmetic-root-execution-001'
HERE = Path(__file__).resolve().parent
CHANNELS = ('computed', 'stored_QP')
BAD = ((0, 0), (32, 1), (32, 2))
SIGN = 1 << 63
cache = {}


def strict(raw):
    def pairs(items):
        out = {}
        for k, v in items:
            assert k not in out, ('duplicate JSON key', k)
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def hexword(bits):
    return struct.unpack('>d', struct.pack('>Q', bits))[0].hex()


def binary(bits):
    exponent, mantissa = (bits >> 52) & 2047, bits & ((1 << 52) - 1)
    assert exponent != 2047
    if exponent:
        mantissa += 1 << 52
        shift = exponent - 1023 - 52
    else:
        shift = -1074
    value = F(mantissa << shift, 1) if shift >= 0 else F(mantissa, 1 << -shift)
    return -value if bits & SIGN else value


def decode(text):
    if text not in cache:
        value = float.fromhex(text)
        bits = struct.unpack('>Q', struct.pack('>d', value))[0]
        assert hexword(bits) == text, ('noncanonical word', text)
        cache[text] = (binary(bits), bits)
    return cache[text]


def quotient_even(n, d):
    a, r = divmod(n, d)
    return a + (2*r > d or (2*r == d and a & 1))


def rounded(value, zero_sign=0):
    """Integer-only nearest/ties-even conversion, including subnormal and signed zero."""
    if not value:
        return SIGN if zero_sign else 0
    sign = SIGN if value < 0 else 0
    n, d = abs(value.numerator), value.denominator
    exponent = n.bit_length() - d.bit_length()
    if (n < d << exponent) if exponent >= 0 else (n << -exponent < d):
        exponent -= 1
    if exponent < -1022:
        mantissa = quotient_even(n << 1074, d)
        assert mantissa <= 1 << 52
        return sign | mantissa
    shift = 52 - exponent
    mantissa = quotient_even(n << shift, d) if shift >= 0 else quotient_even(n, d << -shift)
    if mantissa == 1 << 53:
        mantissa >>= 1
        exponent += 1
    assert exponent <= 1023 and (1 << 52) <= mantissa < (1 << 53)
    return sign | ((exponent + 1023) << 52) | (mantissa - (1 << 52))


def multiply(a, b):
    return rounded(binary(a)*binary(b), bool((a ^ b) & SIGN))


def add(a, b):
    value = binary(a) + binary(b)
    return rounded(value, bool(a & SIGN and b & SIGN))


def rat(value):
    return [value.numerator, value.denominator]


def display(value):
    return dict(exact_ratio=rat(value), once_rounded_binary64_hex=hexword(rounded(value)))


def exact_resultants(values, geometry, constraints):
    out = {}
    limit = decode((1e-7).hex())[0]
    for group in ('constrained', 'free', 'all'):
        rows = {n: [values[n][j] if group == 'all' or ((n, j) in constraints) == (group == 'constrained')
                    else F(0) for j in range(3)] for n in sorted(geometry)}
        result = []
        for j in range(3):
            forces = [rows[n][j] for n in sorted(rows)]
            moments = [geometry[n][(j+1)%3]*rows[n][(j+2)%3] - geometry[n][(j+2)%3]*rows[n][(j+1)%3]
                       for n in sorted(rows)]
            fs, ms = sum(forces, F(0)), sum(moments, F(0))
            result.append(dict(component=j, force=display(fs), moment=display(ms),
                force_L1=rat(sum(map(abs, forces), F(0))), force_max=rat(max(map(abs, forces))),
                moment_L1=rat(sum(map(abs, moments), F(0))), moment_max=rat(max(map(abs, moments))),
                unchanged_force_limit_binary64_hex=(1e-7).hex(), unchanged_moment_limit_binary64_hex=(1e-7).hex(),
                force_exceeds_original_gate=abs(fs) > limit, moment_exceeds_original_gate=abs(ms) > limit))
        out[group] = result
    return out


def float_resultants(bits, geometry_bits, constraints):
    out = {}
    limit = decode((1e-7).hex())[0]
    for group in ('constrained', 'free', 'all'):
        rows = {n: [bits[n][j] if group == 'all' or ((n, j) in constraints) == (group == 'constrained')
                    else 0 for j in range(3)] for n in sorted(geometry_bits)}
        result = []
        for j in range(3):
            forces = [binary(rows[n][j]) for n in sorted(rows)]
            moments = [binary(add(multiply(geometry_bits[n][(j+1)%3], rows[n][(j+2)%3]),
                                   multiply(geometry_bits[n][(j+2)%3], rows[n][(j+1)%3]) ^ SIGN))
                       for n in sorted(rows)]
            fs, ms = rounded(sum(forces, F(0))), rounded(sum(moments, F(0)))
            as_float = lambda b: struct.unpack('>d', struct.pack('>Q', b))[0]
            result.append(dict(component=j, force_N=as_float(fs), force_binary64_hex=hexword(fs),
                moment_Nm=as_float(ms), moment_binary64_hex=hexword(ms),
                force_L1_N=as_float(rounded(sum(map(abs, forces), F(0)))),
                force_max_abs_term_N=as_float(rounded(max(map(abs, forces)))),
                moment_L1_Nm=as_float(rounded(sum(map(abs, moments), F(0)))),
                original_force_limit_N=1e-7, original_moment_limit_Nm=1e-7,
                force_exceeds_original_gate=abs(binary(fs)) > limit, moment_exceeds_original_gate=abs(binary(ms)) > limit))
        out[group] = result
    return out


def main():
    paths = [D/'report.json', D/'execution-receipt.json', W/'authorization.json', W/'result.json',
             W/'stdout.log', W/'stderr.log', W/'tool-return.json', W/'census.json',
             E/'native005-END181-equilibrium-execution-001/diagnostic.json']
    records = [pin(p) for p in paths]
    assert records[0]['sha256'] == 'dc1d3bae0834bfe76838cb966290f4c6b43df07e601764bef4e7afffddfcbc99'
    assert records[0]['bytes'] == 7473602
    o, receipt, auth, parent = [strict(p.read_bytes()) for p in paths[:4]]
    census, prior = strict(paths[7].read_bytes()), strict(paths[8].read_bytes())
    assert o['original36_aggregate_checks'] == prior['all36_aggregate_checks']
    assert o['original12_native_aggregate_checks'] == prior['original12_native_aggregate_checks']
    assert o['complete_original_region_order'] == prior['exact_region_assembly_iteration_order']
    assert o['complete_source_ID_coordinate_binary64_LE_hex'] == prior['complete_source_ID_coordinate_binary64_LE_hex']
    assert o['complete_ordered_HEX8_cells'] == prior['complete_ordered_HEX8_cells']
    assert o['constrained_DOFs'] == prior['constrained_DOFs']
    geometry_bits = {int(n): list(struct.unpack('<3Q', bytes.fromhex(h)))
                     for n, h in o['complete_source_ID_coordinate_binary64_LE_hex'].items()}
    geometry = {n: list(map(binary, words)) for n, words in geometry_bits.items()}
    cells = {r['source_cell_ID']: r['nodes'] for r in o['complete_ordered_HEX8_cells']}
    constraints = set(map(tuple, o['constrained_DOFs']))
    old = {(r['source_ID'], r['component']): r for r in prior['all1275_native_vs_assembled_component_observations']}
    assert len(geometry) == 425 and len(cells) == 256 and len(constraints) == 6 and len(old) == 1275
    A = {ch: {n: [0, 0, 0] for n in geometry} for ch in CHANNELS}
    B = {ch: {n: [F(0)]*3 for n in geometry} for ch in CHANNELS}
    C = {ch: {n: [F(0)]*3 for n in geometry} for ch in CHANNELS}
    witnesses = {str(n)+':'+str(j): [] for n, j in BAD}
    seed_index = merge_index = products_count = 0
    for order in o['complete_original_region_order']:
        label = order['region']
        region = {ch: {n: [0, 0, 0] for n in order['node_iteration_order']} for ch in CHANNELS}
        for cell in order['cell_iteration_order']:
            physical = set()
            for q in range(8):
                seed = o['all2048_operand_seeds'][seed_index]
                assert (seed['region'], seed['cell'], seed['native_QP'], seed['nodes']) == (label, cell, q, cells[cell])
                assert 0 <= seed['physical_rule_index'] < 8 and seed['physical_rule_index'] not in physical
                physical.add(seed['physical_rule_index'])
                ng = struct.unpack('<3Q', bytes.fromhex(seed['native_coordinate_words_LE']))
                rg = struct.unpack('<3Q', bytes.fromhex(seed['rule_coordinate_words_LE']))
                assert max(abs(binary(a)-binary(b)) for a, b in zip(ng, rg)) <= decode((2e-13).hex())[0]
                gradients = [[decode(v) for v in row] for row in seed['gradient_words']]
                wq, wb = decode(seed['weight_word'])
                assert wq == F(1, 1024) and len(gradients) == 8 and all(len(x) == 3 for x in gradients)
                for ch in CHANNELS:
                    stress = [[decode(v) for v in row] for row in seed['stress_words'][ch]]
                    assert len(stress) == 3 and all(len(x) == 3 for x in stress)
                    for local, n in enumerate(seed['nodes']):
                        grad = gradients[local]
                        for i in range(3):
                            prods = [rounded(stress[i][j][0]*grad[j][0], bool((stress[i][j][1]^grad[j][1])&SIGN)) for j in range(3)]
                            products_count += 3
                            dot = rounded(sum(map(binary, prods), F(0)))
                            contribution = multiply(wb, dot)
                            assert hexword(contribution) == seed['rounded_contribution_words'][ch][local][i]
                            before = region[ch][n][i]
                            region[ch][n][i] = add(before, contribution)
                            b = binary(contribution)
                            c = wq*sum((stress[i][j][0]*grad[j][0] for j in range(3)), F(0))
                            B[ch][n][i] += b
                            C[ch][n][i] += c
                            if (n, i) in BAD:
                                witnesses[str(n)+':'+str(i)].append(dict(channel=ch, seed_index=seed_index,
                                    region=label, cell=cell, native_QP=q, component=i, source_ID=n,
                                    product_words=list(map(hexword, prods)), fsum_word=hexword(dot),
                                    weighted_contribution_word=hexword(contribution), region_before_word=hexword(before),
                                    region_after_word=hexword(region[ch][n][i]), B_contribution=rat(b), C_contribution=rat(c)))
                seed_index += 1
            assert physical == set(range(8))
        for ch in CHANNELS:
            for n in order['node_iteration_order']:
                before = list(map(hexword, A[ch][n]))
                A[ch][n] = [add(a, b) for a, b in zip(A[ch][n], region[ch][n])]
                expected = dict(channel=ch, region=label, source_ID=n, before_words=before,
                                region_words=list(map(hexword, region[ch][n])), after_words=list(map(hexword, A[ch][n])))
                assert expected == o['complete900_region_merges'][merge_index]
                merge_index += 1
    assert seed_index == 2048 and merge_index == 900 and products_count == 294912
    assert witnesses == o['three_failed_native_DOF_contribution_witnesses']
    expected_components = []
    for n in sorted(geometry):
        for j in range(3):
            p = old[(n, j)]
            native = decode(p['native_binary64_hex'])[0]
            assert hexword(A['computed'][n][j]) == p['assembled_binary64_hex']
            channels = {}
            for ch in CHANNELS:
                a, b, c = binary(A[ch][n][j]), B[ch][n][j], C[ch][n][j]
                channels[ch] = dict(A_word=hexword(A[ch][n][j]), B=display(b), C=display(c),
                                    A_minus_B=rat(a-b), B_minus_C=rat(b-c), A_minus_C=rat(a-c), native_CSV_minus_A_word=rat(native-a))
            expected_components.append(dict(source_ID=n, component=j, constrained=(n, j) in constraints,
                native_CSV_word=p['native_binary64_hex'], prior_constitutive_word=p['assembled_binary64_hex'], channels=channels,
                computed_minus_stored_QP=dict(A=rat(binary(A['computed'][n][j])-binary(A['stored_QP'][n][j])),
                                            B=rat(B['computed'][n][j]-B['stored_QP'][n][j]), C=rat(C['computed'][n][j]-C['stored_QP'][n][j]))))
    assert expected_components == o['all1275_component_comparisons']
    aggregate, exact_a, expected_checks = {}, {}, []
    for ch in CHANNELS:
        aggregate[ch] = dict(A=float_resultants(A[ch], geometry_bits, constraints),
                             B=exact_resultants(B[ch], geometry, constraints), C=exact_resultants(C[ch], geometry, constraints))
        exact_a[ch] = exact_resultants({n: list(map(binary, A[ch][n])) for n in geometry}, geometry, constraints)
        for variant, groups in aggregate[ch].items():
            for group, rows in groups.items():
                for row in rows:
                    for quantity, unit in [('force', 'force_N'), ('moment', 'moment_Nm')]:
                        value = dict(binary64_hex=row[quantity+'_binary64_hex']) if variant == 'A' else row[quantity]
                        expected_checks.append(dict(channel=ch, variant=variant, rowset=group, component=row['component'], quantity=quantity,
                            conventional_unit_label_from_frozen_assessor=unit, value=value,
                            unchanged_limit_binary64_hex=(1e-7).hex(), exceeds_original_gate=row[quantity+'_exceeds_original_gate']))
    assert aggregate == o['variant_resultants'] and exact_a == o['exact_postprocessing_of_A_words']
    assert aggregate['computed']['A'] == prior['independently_assembled_resultants']
    assert expected_checks == o['derived_variant_checks'] and len(expected_checks) == 108
    assert receipt['report'] == records[0]
    assert receipt['fixed_input_source_runtime_records'] == o['fixed_input_source_runtime_records']
    assert receipt['source_packet_records'] == o['source_packet_records']
    assert receipt['complete_before_after_equal'] is True and receipt['known_input_and_packet_bytes'] == 2612711
    assert parent['raw_returncode'] == 0 and parent['wait_reap_completed'] is True and parent['timeout'] is False
    assert parent['parent_error'] is None and parent['parent_wall_seconds'] == 1.817782667 and parent['within_20_seconds'] is True
    assert auth['before'] == parent['after'] and len(auth['before']) == 13 and parent['alias_unchanged'] is True
    assert auth['invocations'] == 1 and auth['retry'] is False and auth['timeout_seconds'] == 20
    for name, desc in parent['outputs'].items():
        assert desc == next(r for r in records if r['path'] == str(D/name))
    assert paths[5].read_bytes() == b''
    stdout = strict(paths[4].read_bytes())
    assert stdout['derived_exceedances'] == sum(x['exceeds_original_gate'] for x in expected_checks) == 36
    assert stdout['report_sha256'] == records[0]['sha256'] and stdout['report_bytes'] == records[0]['bytes']
    tool = strict(paths[6].read_bytes());tool_summary = strict(tool['output'])
    assert tool['exit_code'] == tool_summary['raw_returncode'] == 0 and tool_summary['wait_reaped'] is True and tool_summary['timeout'] is False
    expected_census = {v['path']: v for v in auth['before'].values()}
    for d in records[:8]:
        if d['path'] != str(W/'census.json'):
            expected_census[d['path']] = d
    saved_census = {v['path']: v for v in census['records']}
    assert len(saved_census) == len(census['records']) == 20
    assert census['file_count'] == 21 and census['self_counted_without_self_hash'] is True
    for path, d in expected_census.items():
        assert saved_census[path] == d
    assert set(saved_census) == set(expected_census)
    assert sum(d['bytes'] for d in saved_census.values()) + records[7]['bytes'] == census['total_bytes'] == 10118460
    assert census['within_cap'] is True and census['total_bytes'] < census['cap_bytes'] == 33554432
    for key in ['solver_convergence_or_cause_established', 'replacement_force_field_created',
                'field_force_physics_material_LPBF_manufacturing_acceptance', 'new_solver_or_native_execution', 'retry']:
        assert o[key] is False
    summary = dict(status='PASS_ALL_SAVED_OPERAND_ARITHMETIC_AND_METADATA_CHECKS',
        reads=records, read_count=len(records), read_bytes=sum(x['bytes'] for x in records),
        QP_seeds=seed_index, rounded_scalar_products=products_count, rounded_dot_sums=98304,
        weighted_contributions=98304, regional_additions=98304, regional_merge_rows=merge_index,
        regional_scalar_merges=2700, full_component_rows=1275,
        witness_records={k: len(v) for k, v in witnesses.items()},
        original_checks=36, original_native_checks=12, derived_checks=108,
        derived_failures=36, original_failures=len(prior['aggregate_exceedances']),
        failures_by_channel_variant={ch: {v: sum(x['exceeds_original_gate'] for x in expected_checks if x['channel']==ch and x['variant']==v)
                                         for v in ('A','B','C')} for ch in CHANNELS},
        census_paths=21, census_bytes=10118460,
        rounding_method='Independent integer quotient/remainder nearest-ties-even; Fraction exact sums/products and IEEE signed-zero operation rules. No target import/kernel replay/math.fsum or raw input access.',
        limitations='Operands are saved derived seeds. No independent raw CSV/constitutive-gradient generation/native solver/installed-runtime/ABI/provenance or physical qualification is established.')
    with (HERE/'arithmetic-check.json').open('x') as stream:
        json.dump(summary, stream, indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='reads'},indent=2))


if __name__ == '__main__':
    main()
