"""Verify the stored 17384-event evidence using only the Python standard library."""
import ast
from collections import Counter
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda name: json.loads((HERE/name).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = read('manifest.json')
    require(manifest['schema'] == 'carrier-closed-encoded-point-evidence-1', 'Wrong capsule schema')
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    require(actual == set(manifest['files_sha256']), 'Capsule payloads missing or extra')
    for name, expected in manifest['files_sha256'].items():
        path = HERE/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and not path.is_symlink()
            and path.resolve().is_relative_to(HERE) and sha(path) == expected, 'Payload differs: '+name)
    provenance = read('provenance.json')
    require(sha(HERE/'reference/closed_encoded_point_coverage_v1_original.py') == provenance['source_helper_sha256'],
        'The original helper differs')
    def algorithm(name):
        tree = ast.parse((HERE/name).read_text())
        return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'encode_from_owned_cuts'))
    require(algorithm('closed_encoded_point_coverage_v1.py') == algorithm('reference/closed_encoded_point_coverage_v1_original.py'),
        'Authority relocation changed the algorithm')
    spec = importlib.util.spec_from_file_location('_portable_closed_points', HERE/'closed_encoded_point_coverage_v1.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    assessment = read('evidence/assessment.json')
    execution = read('evidence/execution-receipt.json')
    review = read('evidence/root-terminal-review.json')
    require(assessment['status'] == 'all_original17384_ledger_collapsed_points_covered_no_admission'
        and assessment['inputs_unchanged'] and assessment['stdlib_runtime_unchanged']
        and not assessment['global_admission'], 'Diagnostic incomplete or changed')
    require(execution['actual_returncode'] == 0 and execution['direct_child_reaped']
        and execution['no_non_zombie_group_members'] and execution['sources_and_plan_unchanged'], 'Execution incomplete')
    require(review['files_sha256']['output-001/assessment.json'] == sha(HERE/'evidence/assessment.json')
        and review['files_sha256']['execution-001/execution-receipt.json'] == sha(HERE/'evidence/execution-receipt.json'),
        'Root review refers to other results')
    owner_index = read('evidence/owners.json')
    owners = {g['id']: g for g in owner_index['groups']}
    ranges = sorted(g['face_range'] for g in owners.values())
    require(len(owners) == len(owner_index['groups']) == 337
        and owner_index['surface_sha256'] == assessment['source_npz_sha256']
        == 'c351989c2191382d51aec2d8941d08ec1ccaaba30197bdc6121dd92e351bba6b'
        and ranges[0][0] == 0 and ranges[-1][1] == 171694
        and all(a[0] < a[1] == b[0] for a, b in zip(ranges, ranges[1:])), 'Owner index differs')
    digest, counts, number, layers = hashlib.sha256(), Counter(), 0, 0
    with gzip.open(HERE/'evidence/layers.jsonl.gz', 'rb') as stream:
        for line in stream:
            digest.update(line)
            row = json.loads(line)
            require(layers < 1034 and row['layer'] == layers and row['passed']
                and Q(row['z_exact']) == Q((layers+.5)*.06), 'Layer calendar differs')
            layers += 1
            for proof in row['proofs']:
                first, last = owners[proof['owner']]['face_range']
                witness = proof['nonzero_same_owner_witness']
                cut = tuple(tuple(Q(v) for v in p) for p in proof['original_rational_cut'])
                require(first <= proof['face_id'] < last and first <= witness['face_id'] < last
                    and proof['layer'] == row['layer'] and proof['entire_encoded_point_covered'], 'Owner/face binding differs')
                require(helper.cell_proof(cut) == proof['rounding_cell'], 'Nearest-even rounding cell differs')
                require(witness['section_identity'] == dict(source_npz_sha256=assessment['source_npz_sha256'],
                    owner_id=proof['owner'], layer=row['layer'], z_exact=row['z_exact']), 'Witness belongs to another section')
                a, b = [tuple(Q(v) for v in p) for p in witness['encoded_vector_exact']]
                point = tuple(Q(v) for v in proof['rounding_cell']['point'])
                require(a != b and helper._exact['contains_point']((a, b), point), 'Missing nonzero exact witness')
                require(tuple(tuple(Q(float(Q(v))) for v in p) for p in witness['original_rational_cut']) == (a, b),
                    'Witness encoding differs from its retained Q cut')
                number += 1
                counts[proof['face_id']] += 1
    require(layers == 1034 and number == 17384 and len(counts) == 198, 'Event totals differ')
    require(dict(counts) == {int(k): v for k, v in assessment['collapsed_events_by_face'].items()}, 'Face totals differ')
    require(digest.hexdigest() == provenance['raw_ledger_sha256'] == assessment['output_files_sha256']['layers.jsonl'],
        'Decompressed ledger differs')
    print(json.dumps(dict(status='stored_point_coverage_evidence_verified', layers=layers, covered_events=number,
        original_faces=len(counts), raw_noncollapsed_cuts_recomputed=False, contacts_or_graph_recomputed=False,
        factory_integrated=False, global_admission=False)))


if __name__ == '__main__':
    main()
