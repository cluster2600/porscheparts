"""Check this retained evidence capsule only; no compiler/native/runtime import."""
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import struct


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def norm2(a, b, c):
    u = [Fraction(b[i])-Fraction(a[i]) for i in range(3)]
    v = [Fraction(c[i])-Fraction(a[i]) for i in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    return sum(x*x for x in n)


def events(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def pair_checks(rows):
    pairs = 0
    failures = 0
    for row in rows:
        if 'ordered_points_mm' not in row:
            continue
        p = row['ordered_points_mm']
        assert len(p) == 4
        a, b = norm2(*p[:3]), norm2(p[0], p[2], p[3])
        assert min(a, b) > 0
        passed = max(a, b) < 100000000 * min(a, b)
        assert (row['event'] == 'ordinary.dihedral') is passed
        if not passed:
            assert row['passed'] is False
            failures += 1
        pairs += 1
    return pairs, failures


def verify(directory):
    root = Path(directory)
    assert root.is_dir() and not root.is_symlink()
    receipt = read_json(root/'receipt.json')
    expected = receipt['payloads']
    actual = set()
    for path in root.rglob('*'):
        assert not path.is_symlink(), 'Symlink refused'
        if path.is_file():
            actual.add(str(path.relative_to(root)))
    assert actual == set(expected) | {'receipt.json'}, 'Payload closure changed'
    for name, record in expected.items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        path = root/name
        assert path.is_file() and path.stat().st_size == record['bytes']
        assert digest(path) == record['sha256'], 'Payload changed: '+name
    copies = read_json(root/'exact-copy-provenance.json')['exact_copies']
    for name, record in copies.items():
        assert digest(root/name) == record['sha256'] and (root/name).stat().st_size == record['bytes']
    projection = read_json(root/'projections.json')
    for phase, count, artifacts in [('compile',70,8),('fixtures',46,14),('head',93,8)]:
        p = projection['phases'][phase]
        assert len(p['input_sha256_by_logical_id']) == count
        assert len(p['original_complete_artifact_inventory']) == artifacts
        assert p['before_after_and_current_inputs_verified'] is True
        for key, value in p['input_sha256_by_logical_id'].items():
            assert projection['input_catalog'][key]['sha256'] == value
        for e in p['executions']:
            assert e['attach_returncode'] == 0 and e['attach_reaped'] is True
            assert e['owned_container_removed'] is True and e['terminal_state']['Running'] is False
            assert e['terminal_state']['OOMKilled'] is False
    fixture_counts = {}
    for name, count, pairs, failures, topology, choice, ordinary in [
        ('known-collapse',28,12,0,True,True,True),
        ('all-fixed',6,0,0,False,False,None),
        ('ratio-obstruction',18,1,1,True,True,False)]:
        rows = events(root/'fixtures'/f'{name}.events.jsonl')
        assert len(rows) == count and pair_checks(rows) == (pairs, failures)
        final = [r for r in rows if r['event']=='final_profile_result']
        assert len(final)==1 and final[0]['topology'] is topology
        assert final[0]['choice_present'] is choice and final[0]['ordinary_geometry'] is ordinary
        fixture_counts[name] = count
    h = events(root/'head/events.jsonl')
    assert len(h)==2190 and pair_checks(h)==(169,135)
    counts = Counter(r['event'] for r in h)
    assert counts == read_json(root/'reviews/head-peer.json')['event_counts']
    final = [r for r in h if r['event']=='final_profile_result']
    assert len(final)==135 and all(r['topology'] is True and r['choice_present'] is True and r['ordinary_geometry'] is False for r in final)
    for name in ['known-collapse','all-fixed','ratio-obstruction']:
        raw = (root/'fixtures'/f'{name}.bin').read_bytes()
        assert raw[:8] == b'962SURF1'
        nv,nf = struct.unpack_from('<QQ',raw,8)
        assert (nv,nf)==((11,18) if name=='ratio-obstruction' else (10,16))
        assert len(raw)==24+24*(nv+nf)
    for p in root.rglob('*'):
        if p.is_file() and p.suffix not in ('.bin','.u64'):
            text = p.read_text()
            assert not re.search(('/'+'Users'+'/|/'+'home'+'/|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'),text)
    return {'passed':True,'payload_files':len(expected),'payload_bytes':sum(x['bytes'] for x in expected.values()),'fixture_events':fixture_counts,'head_events':len(h),'head_final_profiles':len(final),'exact_reported_pair_ratio_checks':182,'native_replay':False,'geometry_or_solver_admission':False}


if __name__=='__main__':
    print(json.dumps(verify(Path(__file__).resolve().parent),indent=2))
