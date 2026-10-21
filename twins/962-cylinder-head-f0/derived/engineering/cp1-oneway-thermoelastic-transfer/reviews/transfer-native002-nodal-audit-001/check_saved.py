"""One saved-CSV lexical/ID/coordinate audit; no producer or assessor import."""
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / 'work/962-engineering'
OUT = E / 'cp1-oneway-thermoelastic-transfer-002'
RUN = E / 'cp1-oneway-thermoelastic-transfer-root-execution-002'
PREP = E / 'cp1-oneway-thermoelastic-transfer-prep-002'
HERE = Path(__file__).resolve().parent
sha = lambda b: hashlib.sha256(b).hexdigest()
PIN = {
    RUN / 'closed-result.json': 'd898fca841c4e3c59f6320cce1a40b003137afa9f2f815d46e11d870594165dd',
    OUT / 'native-execution.json': '728fe39456b4c4d92bb61ea1a34ca6f8915bc09c701168d03600dc1b56d8c574',
    OUT / 'actual-contract.json': '9fd012256eb321f1a7717164cd929c6f0e89a3c4d75e02f96710a45b34d9cefb',
    OUT / 'transfer-manifest.json': '86e10faa43c34156f0ec7eba1187125b487dc73433d8e7667a7f9ad2f98ba3fb',
    PREP / 'thermal-input-index.json': 'ad60a9b29ccb9f6b7114abe686402bd7bd40cb87bfdd40d540a3d38bb31e56d6',
    PREP / 'thermoelastic-birth.i': 'cbead6d0ec032a0cc1bb82dd2abc032aa3f94321340ddc06058f42c8a1ce6fdb',
    PREP / 'case-contract.json': 'cf56e131b449595ba78b0889725a3536fdda82cff67330bad8e062c93e2d18d2',
    PREP / 'run_mac.py': 'dcc8f5a26f3834dd195778536ba527a6179558a57b956a021ee3feae94f5d992',
    E / 'cp1-oneway-thermoelastic-assessor-prep-002/assess.py': '6dfb8aaa2be8575eaf99c5e49a5f28e345cd12a185e22d5aab5467b632509d03',
    E / 'cp1-oneway-thermoelastic-transfer-result-peer-002/review.json': '678318429f60b3d28f5b21e530ab8d376413093f1b02bccb6643191c9c8a2118',
}


def raw_file(p):
    if not p.is_file() or p.is_symlink() or p.resolve() != p:
        raise ValueError('Expected original regular file: ' + str(p.relative_to(ROOT)))
    return p.read_bytes()


def require(test, message):
    if not test:
        raise ValueError(message)


def main():
    pins_before = {str(p.relative_to(ROOT)): {'sha256': sha(raw_file(p)), 'bytes': p.stat().st_size} for p in PIN}
    require(all(pins_before[str(p.relative_to(ROOT))]['sha256'] == h for p, h in PIN.items()), 'Direct frozen binding mismatch')
    closed = json.loads(raw_file(RUN / 'closed-result.json'))
    receipt = json.loads(raw_file(OUT / 'native-execution.json'))
    actual = json.loads(raw_file(OUT / 'actual-contract.json'))
    transfer = json.loads(raw_file(OUT / 'transfer-manifest.json'))
    inventory = closed['complete_recursive_output_inventory']
    require(len(inventory) == closed['output_count'] == 990 and closed['output_bytes'] == 359397778, 'Full990 root inventory identity mismatch')
    require(receipt['complete_artifact_sha256'] == {n: r['sha256'] for n, r in inventory.items() if n != 'native-execution.json'}, 'Full recursive receipt/root map mismatch')
    require(receipt['artifact_sha256'] == {n: r['sha256'] for n, r in inventory.items() if n != 'native-execution.json' and Path(n).name == n}, 'Flat receipt/root map mismatch')
    require(receipt['native_execution_completed'] is True and receipt['passed'] is False
            and receipt['independent_assessment_performed'] is False and receipt['automatic_retry'] is False, 'Original native/assessment boundary mismatch')
    require(closed['native_receipt_sha256'] == PIN[OUT / 'native-execution.json']
            and closed['actual_sha256'] == receipt['actual_contract_sha256'] == PIN[OUT / 'actual-contract.json'], 'Actual/receipt/root join mismatch')
    require(actual['source_sha256'] == PIN[PREP / 'run_mac.py'] and actual['deck_sha256'] == PIN[PREP / 'thermoelastic-birth.i']
            and actual['source_physics_contract_sha256'] == PIN[PREP / 'case-contract.json'], 'Exact source002/deck/physics association mismatch')
    for name, source in [('thermoelastic-birth.i', PREP / 'thermoelastic-birth.i'), ('frozen-contract.json', PREP / 'case-contract.json')]:
        require(raw_file(OUT / name) == raw_file(source), 'Native source snapshot drift: ' + name)
    require(receipt['transfer_manifest_sha256'] == PIN[OUT / 'transfer-manifest.json'], 'Native transfer association mismatch')
    geometry = {r['source_node_id']: r for r in transfer['node_rows']}
    require(len(geometry) == len(transfer['node_rows']) == 425, 'Exact source425 unique node map required')
    old = {t for t, r in geometry.items() if r['old2']}
    born = {t for t, r in geometry.items() if r['born3']}
    shared = {t for t, r in geometry.items() if r['shared']}
    require((len(old), len(born), len(shared)) == (225, 225, 25) and shared == old & born, 'Fixed source old/born/shared association mismatch')
    words = {}
    for tag, row in geometry.items():
        xyz = row['coordinates_m']
        require([float(v).hex() for v in xyz] == row['binary64_hex'], 'Source map hex mismatch')
        words[tag] = struct.pack('<3d', *xyz)
        require((xyz[0] == 1.) == (tag in shared), 'Source shared interface map mismatch')
    names = [(f'thermoelastic_{phase}_{step:04d}.csv', 'nodal', phase, step) for step in range(161) for phase in ('begin', 'end')]
    names += [(f'thermoelastic_reference_{phase}_{step:04d}.csv', 'reference', phase, step) for step in range(161) for phase in ('begin', 'end')]
    declared = {n for n in inventory if re.fullmatch(r'thermoelastic_(?:reference_)?(?:begin|end)_\d{4}\.csv', n)}
    require(declared == {n for n, _, _, _ in names} and len(names) == 644, 'Complete322+322 CSV family mismatch')
    current_files = {str(p.relative_to(OUT)): p.stat().st_size for p in OUT.rglob('*') if p.is_file()}
    require(not any(p.is_symlink() for p in OUT.rglob('*')) and current_files == {n: r['bytes'] for n, r in inventory.items()}, 'Full990 current file-name/size metadata mismatch')
    results = {}; negatives = []; raw_hashes = {}; current_name = None
    try:
        for name, kind, phase, step in names:
            current_name = name; p = OUT / name; raw = raw_file(p); raw_hashes[name] = sha(raw)
            require({'sha256': sha(raw), 'bytes': len(raw)} == inventory[name], 'CSV byte identity differs from root inventory')
            reader = csv.reader(io.StringIO(raw.decode(), newline='')); header = next(reader); data = list(reader)
            common = {'id', 'x', 'y', 'z', 'disp_x', 'disp_y', 'disp_z', 'temperature'}
            expected_fields = {'id', 'x', 'y', 'z', 'born_reference_temperature'} if kind == 'reference' else common | ({'rx', 'ry', 'rz'} if phase == 'end' else set())
            require(len(header) == len(set(header)) and set(header) == expected_fields, 'Exact full header field set mismatch')
            active = (born if step >= 80 else set()) if kind == 'reference' else (set(geometry) if step >= 80 else old)
            grouped = defaultdict(list); ordered_ids = []; raw_ID_tokens = []; word_stream = bytearray()
            for number, tokens in enumerate(data, 2):
                require(len(tokens) == len(header) and all(t != '' for t in tokens), 'Malformed original CSV row')
                row = dict(zip(header, tokens)); token = row['id']
                require(token.isascii() and token.isdigit(), 'Original ID token is not explicit nonnegative integer text')
                tag = int(token); require(tag in active, 'Observed ID outside exact source active-node set')
                xyz = tuple(float(row[k]) for k in 'xyz')
                require(all(math.isfinite(float(t)) for t in tokens), 'Nonfinite original CSV token')
                require(struct.pack('<3d', *xyz) == words[tag], 'Source ID/coordinate binary64-word association mismatch')
                grouped[tag].append((number, tokens)); ordered_ids.append(tag)
                raw_ID_tokens.append(token)
                word_stream.extend(struct.pack('<Q', tag)); word_stream.extend(words[tag])
            counts = Counter({t: len(v) for t, v in grouped.items()}); repeated = {t: rows for t, rows in grouped.items() if len(rows) > 1}
            record = dict(path=str(p.relative_to(ROOT)), sha256=sha(raw), bytes=len(raw), kind=kind, phase=phase, step=step,
                          header=header, raw_rows=len(data), unique_IDs=len(grouped), multiplicity_counts=dict(Counter(counts.values())),
                          distinct_original_ID_tokens=len(set(raw_ID_tokens)), raw_ordered_ID_tokens=raw_ID_tokens,
                          lexical_ID_multiplicity_counts=dict(Counter(Counter(raw_ID_tokens).values())),
                          raw_ordered_source_IDs=ordered_ids, ordered_source_ID_u64_plus_coordinate_binary64_LE_sha256=sha(word_stream),
                          all_rows_source_ID_coordinate_words_exact=True, duplicate_IDs=sorted(repeated), duplicate_groups=[])
            results[name] = record
            require(len(set(raw_ID_tokens)) == len(grouped), 'Different lexical ID strings collapse to one source ID')
            require(set(grouped) == active, 'Incomplete exact source active-node set')
            if kind == 'nodal' and step >= 80:
                require(len(data) == 450 and len(grouped) == 425 and set(repeated) == shared
                        and dict(Counter(counts.values())) == {1: 400, 2: 25}, 'Postbirth nodal450/425/exact25shared multiplicity mismatch')
            else:
                require(len(data) == len(active) and not repeated, 'Unique prebirth nodal/reference sample count mismatch')
            for tag, rows in sorted(repeated.items()):
                exact = all(tokens == rows[0][1] for _, tokens in rows)
                record['duplicate_groups'].append(dict(source_ID=tag, original_CSV_lines=[line for line, _ in rows],
                    header_plus_row_tokens_SHA256=[sha(json.dumps([header, tokens], separators=(',', ':'), ensure_ascii=False).encode()) for _, tokens in rows],
                    all_present_header_tokens_lexically_identical=exact, source_coordinate_binary64_LE_hex=words[tag].hex(),
                    source_shared25_interface_member=tag in shared))
                require(exact, 'Repeated source ID has unequal original lexical tokens in one or more header fields, including END reactions')
            record['all_duplicate_groups_full_row_lexically_identical'] = True
    except (ValueError, KeyError, StopIteration) as error:
        negatives.append(dict(file=current_name, error=type(error).__name__ + ': ' + str(error)))
    for name, digest in raw_hashes.items():
        require(sha(raw_file(OUT / name)) == digest, 'Scanned CSV changed during saved audit')
    require(all(sha(raw_file(p)) == expected for p, expected in PIN.items()), 'Frozen source/root binding changed during audit')
    totals = {kind: {'files': sum(r['kind'] == kind for r in results.values()),
                     'raw_rows': sum(r['raw_rows'] for r in results.values() if r['kind'] == kind),
                     'postbirth_doublet_groups': sum(len(r['duplicate_groups']) for r in results.values() if r['kind'] == kind)} for kind in ('nodal', 'reference')}
    result = dict(schema='962-native002-complete-nodal-lexical-duplicate-audit/v1', status='REFUSED_SAVED_DATA_MISMATCH' if negatives else 'PASS_OBSERVED_MULTIPLICITY_AND_LEXICAL_ASSOCIATIONS_ONLY',
                  direct_bindings=pins_before, full_native_inventory_count=990, full_native_inventory_bytes=359397778,
                  full990_name_size_and_receipt_metadata_joined=True, outside_requested_CSV_body_hashes_root_attributed=True,
                  scanned_CSVs=len(results), expected_CSVs=644, totals=totals, negatives=negatives,
                  source_node_map=dict(nodes=425, old225_IDs=sorted(old), born225_IDs=sorted(born), shared25_IDs=sorted(shared),
                                       ID_to_coordinate_binary64_LE_hex={str(t): words[t].hex() for t in sorted(words)}),
                  files=results, all_scanned_CSV_and_binding_bytes_before_after_unchanged=True,
                  original_thermal_source_CSVs_read_normalized_or_deduplicated=False, native_CSVs_rewritten_or_deduplicated=False,
                  assessor_or_source_helper_import_execution=False, scientific_or_native_execution=False,
                  native_receipt_original_passed=False, independent_mechanical_assessment_performed=False,
                  native_Exodus_ID_connectivity_bijection_or_reference_tensor_physics_acceptance=False)
    with (HERE / 'complete-saved-audit.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: result[k] for k in ['status', 'scanned_CSVs', 'totals', 'negatives']}, indent=2))
    return 2 if negatives else 0


if __name__ == '__main__':
    raise SystemExit(main())
