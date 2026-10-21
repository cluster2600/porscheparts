"""Recheck every stored cell/witness, without repeating the triangle diagnostic."""
from pathlib import Path
from fractions import Fraction as Q
from collections import Counter
import datetime
import hashlib
import importlib.util
import json
import signal

signal.alarm(45)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan = json.loads((HERE/'plan.json').read_text())
assessment = json.loads((HERE/'output-001/assessment.json').read_text())
supervision = json.loads((HERE/'execution-001/execution-receipt.json').read_text())
assert sha(HERE/'plan.json') == '42ffe43f0f77f1ab04f8c524755eacd1c0b19c083c3e55b6980db88390432e6d'
assert all(sha(ROOT/k) == v for k, v in plan['files_sha256'].items())
spec = importlib.util.spec_from_file_location('_root_point_cells', ROOT/plan['base_three_height_diagnostic'])
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
owners = {g['id']: g for g in json.loads((ROOT/plan['owner_index']).read_text())['groups']}
counts, number, layers = Counter(), 0, 0
with (HERE/'output-001/layers.jsonl').open() as stream:
    for text in stream:
        row = json.loads(text)
        assert row['layer'] == layers and row['passed'] and Q(row['z_exact']) == Q((layers+.5)*.06)
        layers += 1
        for proof in row['proofs']:
            first, last = owners[proof['owner']]['face_range']
            witness = proof['nonzero_same_owner_witness']
            cut = tuple(tuple(Q(v) for v in p) for p in proof['original_rational_cut'])
            assert first <= proof['face_id'] < last and first <= witness['face_id'] < last
            assert proof['layer'] == row['layer'] and proof['entire_encoded_point_covered']
            assert base.cell_proof(cut) == proof['rounding_cell']
            assert witness['section_identity'] == dict(source_npz_sha256=assessment['source_npz_sha256'],
                owner_id=proof['owner'], layer=row['layer'], z_exact=row['z_exact'])
            a, b = [tuple(Q(v) for v in p) for p in witness['encoded_vector_exact']]
            point = tuple(Q(v) for v in proof['rounding_cell']['point'])
            assert a != b
            assert (b[0]-a[0])*(point[1]-a[1]) == (b[1]-a[1])*(point[0]-a[0])
            assert all(min(x, y) <= z <= max(x, y) for x, y, z in zip(a, b, point))
            encoded = tuple(tuple(Q(float(Q(v))) for v in p) for p in witness['original_rational_cut'])
            assert encoded == (a, b)
            number += 1
            counts[proof['face_id']] += 1
assert layers == 1034 and number == 17384 and len(counts) == 198
assert dict(counts) == {int(k): v for k, v in assessment['collapsed_events_by_face'].items()}
assert assessment['all_ledger_collapsed_points_covered'] and assessment['inputs_unchanged']
assert assessment['stdlib_runtime_unchanged'] and not assessment['global_admission']
assert supervision['actual_returncode'] == 0 and supervision['direct_child_reaped']
assert supervision['no_non_zombie_group_members'] and supervision['sources_and_plan_unchanged']
assert all(sha(ROOT/k) == v for k, v in plan['files_sha256'].items())
names = ['output-001/assessment.json', 'output-001/layers.jsonl', 'execution-001/execution-receipt.json']
review = dict(at_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), root_session_collected=56097,
    actual_supervisor_exit_code=0, all1034_layers_contiguous=True,
    all17384_cells_recomputed_and_nonzero_exact_witnesses_rechecked=True,
    all198_face_event_totals_match=True, all24_pins_rehashed_unchanged=True,
    files_sha256={name: sha(HERE/name) for name in names}, verifier_sha256=sha(Path(__file__)),
    scope='Original000 collapsed-event coverage only. No contacts, graph, consumer or global admission.')
with (HERE/'root-terminal-review.json').open('x') as stream:
    json.dump(review, stream, indent=2)
    stream.write('\n')
print(json.dumps(review))
signal.alarm(0)
