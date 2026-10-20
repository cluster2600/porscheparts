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
OUT = E / 'cp1-oneway-cooling-release-linear-001'
RUN = E / 'cp1-oneway-cooling-release-linear-native-root-execution-001'
PREP = E / 'cp1-oneway-cooling-release-linear-prep-001'
HERE = Path(__file__).resolve().parent
sha = lambda b: hashlib.sha256(b).hexdigest()
PIN = {
    RUN / 'closed-result.json': '6d7d6c867bd5d7e289536d5ce25eb0c0288a59dcbb6e878e54b36e0ec8e0e8df',
    OUT / 'native-execution.json': 'cefbae13f5898e7640d6bde0c0d32d1bd617fc38c506ab8f2cc5b02bea8ecc9a',
    OUT / 'actual-contract.json': 'e43a9637e4279a255f7ca36d6244dbe11ff6590a2ecadebe05018966e7aa2a74',
    E / 'cp1-oneway-cooling-release-linear-native-result-peer-001/review.json': 'f85fef66bcf840375d842b1bd4ac9cc786a5be178339b0c69505fd0780b7526b',
    RUN / 'result-peer-acceptance.json': '82dc754ccd7491279e56d99977855820f00ea5a2fbd1d1386b3647e929c42504',
    OUT / 'transfer-manifest.json': 'c774e62c67e16c29dc024b8cc8e6641570e316265960e58cd7170827f8cecd06',
    PREP / 'thermal-input-index.json': '9e4da9faf9a6ccb9a55c66b2c0d9eef44b88d99e09afff69bb4f504b0cfb7aec',
    PREP / 'thermoelastic-birth.i': 'de5c9ea62050645fb546fc650c01023913478c230011faa5172b76ffb36a4f7c',
    PREP / 'case-contract.json': '294f5bf97c6ca3e9fe052e90fc4fc611e740395d1bca24595988d57b4a85758e',
    PREP / 'run_mac.py': '5ec0fe4684dd51dd7934ca3069e75497a481a08db5a9ee8a78646d81e3813f6c',
    PREP / 'held-preparation.json': '438c32f9bd03d4932d331b5b34bfd21b14d64377afdc78f61e41c88fdc6d78da',
    E / 'cp1-oneway-cooling-release-linear-assessor-prep-001/assess.py': 'b7c5c7c82c5a7fee11aa63032f9a136d46517b8163c3c880b8b39a06d083930f',
    E / 'cp1-oneway-cooling-release-contract-clarification-001/case-contract.corrected.json': '1dc7eefae6f6666a91fdb0adde2261aa9efc7f3424a713d21b6f60e6091dfb66',
    E / 'cp1-oneway-cooling-release-contract-clarification-001/correction.json': '3971d0f27293a04f051206a2b2afef3304c56aa3814b12e586c4f5fe0229ed46',
    E / 'cp1-oneway-cooling-release-linear-assessor-prep-001/LATE-BINDING-ACKNOWLEDGEMENT-001.json': '3c2cbab689212aafd2c5def017e9626126c5003723f60831fee757f734f127ce',
    PREP / 'FUNCTION-COUNT-CLARIFICATION-001.json': '8419d1fbbf3638736ac5cfd3d1287342bd787e3c560b95dc9eb9ecb3e930eaf4',
    PREP / 'GRID-ROLE-AND-READ-SCOPE-CLARIFICATION-001.json': 'b505f5320760ddca2525f3db514948dbdec18c8e5a6396310b5e9b57d1ae4ce9',
}
EXPECTED_CAPTURE_OUTPUT_COUNT = 1122
EXPECTED_CAPTURE_OUTPUT_BYTES = 423178297


def raw_file(p):
    if not p.is_file() or p.is_symlink() or p.resolve() != p:
        raise ValueError('Expected original regular file: ' + str(p.relative_to(ROOT)))
    return p.read_bytes()


def require(test, message):
    if not test:
        raise ValueError(message)


def main():
    require(all(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) for value in PIN.values())
            and type(EXPECTED_CAPTURE_OUTPUT_COUNT) is int and EXPECTED_CAPTURE_OUTPUT_COUNT > 0
            and type(EXPECTED_CAPTURE_OUTPUT_BYTES) is int and EXPECTED_CAPTURE_OUTPUT_BYTES > 0,
            'Held only: exact stopped capture/peer/root acceptance and complete inventory bindings remain unknown')
    pins_before = {str(p.relative_to(ROOT)): {'sha256': sha(raw_file(p)), 'bytes': p.stat().st_size} for p in PIN}
    require(all(pins_before[str(p.relative_to(ROOT))]['sha256'] == h for p, h in PIN.items()), 'Direct frozen binding mismatch')
    closed = json.loads(raw_file(RUN / 'closed-result.json'))
    receipt = json.loads(raw_file(OUT / 'native-execution.json'))
    actual = json.loads(raw_file(OUT / 'actual-contract.json'))
    transfer = json.loads(raw_file(OUT / 'transfer-manifest.json'))
    require(closed.get('schema') == '962-cooling-release-linear-native-root-once-closed/v1'
            and closed.get('returncode') == 0 and closed.get('stop_reason') is None
            and closed.get('signals') == [] and closed.get('error') is None
            and closed.get('native_capture_completed') is True, 'Exact naturally stopped cooling capture required')
    root_inventory = closed['outputs']
    require(all(set(row) == {'path', 'sha256', 'bytes'} and row['path'] == str((OUT / name).relative_to(ROOT))
                for name, row in root_inventory.items()), 'Exact current root path/size/hash descriptor shape required')
    inventory = {name: {key: row[key] for key in ('sha256', 'bytes')} for name, row in root_inventory.items()}
    require(len(inventory) == EXPECTED_CAPTURE_OUTPUT_COUNT
            and sum(row['bytes'] for row in inventory.values()) == EXPECTED_CAPTURE_OUTPUT_BYTES,
            'Full current root inventory identity mismatch')
    require(receipt['complete_artifact_sha256'] == {n: r['sha256'] for n, r in inventory.items() if n != 'native-execution.json'}, 'Full recursive receipt/root map mismatch')
    require(receipt['artifact_sha256'] == {n: r['sha256'] for n, r in inventory.items() if n != 'native-execution.json' and Path(n).name == n}, 'Flat receipt/root map mismatch')
    require(receipt['native_execution_completed'] is True and receipt['passed'] is False
            and receipt['independent_assessment_performed'] is False and receipt['automatic_retry'] is False, 'Original native/assessment boundary mismatch')
    require(inventory['native-execution.json']['sha256'] == PIN[OUT / 'native-execution.json']
            and inventory['actual-contract.json']['sha256'] == receipt['actual_contract_sha256'] == PIN[OUT / 'actual-contract.json'], 'Actual/receipt/root join mismatch')
    require(actual['schema'] == '962-macos-oneway-cooling-release-linear-case-actual/v1'
            and actual['source']['path'] == str((PREP / 'run_mac.py').relative_to(ROOT))
            and actual['source']['sha256'] == PIN[PREP / 'run_mac.py']
            and actual['input_sha256'][str((PREP / 'thermoelastic-birth.i').relative_to(ROOT))] == PIN[PREP / 'thermoelastic-birth.i']
            and actual['physics_contract']['sha256'] == PIN[PREP / 'case-contract.json']
            and actual.get('documentary_correction_acknowledged') is True,
            'Exact cooling source/deck/original physics and documentary correction required')
    for name in ('cp1-oneway-cooling-release-contract-clarification-001/case-contract.corrected.json',
                 'cp1-oneway-cooling-release-contract-clarification-001/correction.json',
                 'cp1-oneway-cooling-release-linear-assessor-prep-001/LATE-BINDING-ACKNOWLEDGEMENT-001.json'):
        require(actual['input_sha256'].get(str((E/name).relative_to(ROOT))) == PIN[E/name], 'Late correction/acknowledgement must be direct native pins')
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
    names = [(f'thermoelastic_{phase}_{step:04d}.csv', 'nodal', phase, step) for step in range(183) for phase in ('begin', 'end')]
    names += [(f'thermoelastic_reference_{phase}_{step:04d}.csv', 'reference', phase, step) for step in range(183) for phase in ('begin', 'end')]
    declared = {n for n in inventory if re.fullmatch(r'thermoelastic_(?:reference_)?(?:begin|end)_\d{4}\.csv', n)}
    require(declared == {n for n, _, _, _ in names} and len(names) == 732, 'Complete366+366 CSV family mismatch')
    current_files = {str(p.relative_to(OUT)): p.stat().st_size for p in OUT.rglob('*') if p.is_file()}
    require(not any(p.is_symlink() for p in OUT.rglob('*')) and current_files == {n: r['bytes'] for n, r in inventory.items()}, 'Full current file-name/size metadata mismatch')
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
    result = dict(schema='962-cooling-release-linear-complete-nodal-lexical-storage-audit/v1', status='REFUSED_SAVED_DATA_MISMATCH' if negatives else 'PASS_OBSERVED_MULTIPLICITY_AND_LEXICAL_ASSOCIATIONS_ONLY',
                  direct_bindings=pins_before, full_native_inventory_count=len(inventory), full_native_inventory_bytes=sum(row['bytes'] for row in inventory.values()),
                  full_native_name_size_and_receipt_metadata_joined=True, outside_requested_CSV_body_hashes_root_attributed=True,
                  scanned_CSVs=len(results), expected_CSVs=732, totals=totals, negatives=negatives,
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
