"""Read-only END181 vector diagnostic; no solver or acceptance-limit changes."""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import struct
import sys

REPO = Path(__file__).resolve().parents[4]
ROOT = None
PARSER = REPO / 'twins/962-cylinder-head-f0/derived/engineering/native005-displacement-storage-diagnostic/originals/cp1-oneway-cooling-release-richardson2-observer004-saved-measurement-parser-prep-003/parse_saved_measurement.py'
spec = importlib.util.spec_from_file_location('saved_parser', PARSER)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def inspect(name):
    root = ROOT / name
    receipt_raw = (root / 'native-execution.json').read_bytes()
    receipt = json.loads(receipt_raw)
    pins = receipt['inputs_and_outputs']['artifact_sha256']
    inputs = {}
    def read(name):
        raw = (root / name).read_bytes()
        assert sha(raw) == pins[name], 'Native artifact changed: ' + name
        inputs[name] = dict(sha256=sha(raw), bytes=len(raw))
        return raw
    mapping = p.strict_json(read('rich2-END181-dof-map.json'))
    trace = p.parse_monitor_trace(read('native.log').decode())
    streams = {s: read('physical-' + s + '.petsc') for s in 'XFY'}
    scans = {s: p.scan_vectors(streams[s], mapping['PetscInt_bytes'], read('physical-' + s + '.petsc.info')) for s in streams}
    p.bind_stream_headers(scans, trace, mapping['global_DOF_count'], mapping['PetscInt_bytes'])
    rows = [r for r in mapping['rows'] if r['variable_slot'] < 3]
    assert len(rows) == 1275 and {r['global_DOF'] for r in rows} == set(range(1275))
    assert sum(r['constrained'] for r in rows) == 6
    csv_rows = {}
    duplicates = 0
    for row in csv.DictReader(io.StringIO(read('thermoelastic_end_0181.csv').decode())):
        key = int(row['id'])
        if key in csv_rows:
            assert csv_rows[key] == row, 'Unequal duplicate CSV node'
            duplicates += 1
        csv_rows[key] = row
    assert len(csv_rows) == 425 and duplicates == 25
    for row in rows:
        node = csv_rows[row['source_node_ID']]
        assert [struct.pack('<d', float(node[k])).hex() for k in ('x','y','z')] == row['coordinate_binary64_LE_hex']
        assert row['constrained'] == ((row['source_node_ID'], row['variable_slot']) in {(0,0),(0,1),(0,2),(32,1),(32,2),(137,2)})
    events = [e for e in trace['events'] if e['step'] == 181]
    assert [e['object_ordinal'] for e in events] == [360,361]
    vectors = {}
    norms = {}
    for s, raw in streams.items():
        for e in events:
            obj = scans[s]['objects'][e['object_ordinal']]
            values = struct.unpack_from('>' + str(obj['N']) + 'd', raw, obj['payload_offset'])
            assert all(math.isfinite(v) for v in values)
            key = s + str(e['monitor_iteration']); vectors[key] = values
            norms[key] = dict(l2=math.sqrt(math.fsum(v*v for v in values)), max_abs=max(map(abs,values)))
    for i, event in enumerate(events):
        monitor = next(b for b in trace['blocks'] if b['step']==181)['monitors'][i]
        assert math.isclose(norms['F'+str(i)]['l2'], float(monitor['norm_token']), rel_tol=1e-11)
    detail=[]
    for row in rows:
        node=csv_rows[row['source_node_ID']]; slot=row['variable_slot']; index=row['global_DOF']
        x=float(node[('disp_x','disp_y','disp_z')[slot]])
        assert struct.pack('>d',x)==struct.pack('>d',vectors['X1'][index])
        reaction=float(node[('rx','ry','rz')[slot]])
        detail.append(dict(node=row['source_node_ID'],slot=slot,constrained=row['constrained'],
            residual=vectors['F1'][index],nodal_force=reaction,
            residual_minus_nodal_force=vectors['F1'][index]-reaction,
            update_identity_error=(vectors['X0'][index]-vectors['Y1'][index])-vectors['X1'][index]))
    def subset(constrained):
        selected=[r for r in detail if r['constrained']==constrained]
        return dict(count=len(selected),max_residual=max(abs(r['residual']) for r in selected),
            max_nodal_force=max(abs(r['nodal_force']) for r in selected),
            max_residual_force_difference=max(abs(r['residual_minus_nodal_force']) for r in selected),
            residual_sums=[math.fsum(r['residual'] for r in selected if r['slot']==s) for s in range(3)],
            force_sums=[math.fsum(r['nodal_force'] for r in selected if r['slot']==s) for s in range(3)])
    return dict(source_directory=str(root),native_receipt_sha256=sha(receipt_raw),inputs=inputs,
        vectors=norms,free=subset(False),constrained=subset(True),
        update_identity_max_error=max(abs(r['update_identity_error']) for r in detail),
        exact_X1_CSV_matches=len(detail),trace_objects=364,rows=detail)

def project_forces(nodes):
    """Exact arithmetic on decoded binary64 inputs; these are native saved forces."""
    groups = {g: [Fraction(0) for _ in range(6)] for g in ('free', 'constrained')}
    for n, row in nodes.items():
        xyz = [Fraction(float(row[k])) for k in ('x', 'y', 'z')]
        for slot, k in enumerate(('rx', 'ry', 'rz')):
            fixed = (n, slot) in {(0,0),(0,1),(0,2),(32,1),(32,2),(137,2)}
            force = [Fraction(0)] * 3
            force[slot] = Fraction(float(row[k]))
            moment = [xyz[1]*force[2]-xyz[2]*force[1],
                      xyz[2]*force[0]-xyz[0]*force[2],
                      xyz[0]*force[1]-xyz[1]*force[0]]
            out = groups['constrained' if fixed else 'free']
            for j, v in enumerate(force + moment):
                out[j] += v
    return {k: [float(v) for v in values] for k, values in groups.items()}


def hold_projection(root):
    pins = json.loads((root/'native-execution.json').read_text())['inputs_and_outputs']['artifact_sha256']
    result = {}
    for step in (181,182):
        name = f'thermoelastic_end_{step:04}.csv'
        raw = (root/name).read_bytes()
        assert sha(raw) == pins[name]
        rows = {}
        for row in csv.DictReader(io.StringIO(raw.decode())):
            n = int(row['id'])
            assert n not in rows or rows[n] == row
            rows[n] = row
        assert set(rows) == set(range(425))
        assert all(float(row['temperature']) == 300 for row in rows.values())
        result[str(step)] = dict(sha256=sha(raw), native_force_and_moment=project_forces(rows))
    return result


if __name__ == '__main__':
    ROOT = Path(sys.argv[1]).resolve(strict=True)
    out = Path(sys.argv[2])
    assert not out.exists()
    result = dict(scope='saved_END181_diagnostic_only', phase_ids=['lpbf_build','lpbf_release'],
        parser_sha256=sha(PARSER.read_bytes()), script_sha256=sha(Path(__file__).read_bytes()),
        python=sys.version, python_executable_sha256=sha(Path(sys.executable).read_bytes()),
        argv=sys.argv, physical_qualification=False, root_cause_established=False,
        engineering_phase_promotion=False, cases={})
    for label, name in [
        ('two_updates','cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004'),
        ('three_updates','cp1-oneway-cooling-release-richardson3-observer004-native-measurement-001')]:
        result['cases'][label] = inspect(name)
        result['cases'][label]['hold_projection'] = hold_projection(ROOT/name)
    with out.open('x') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print('Inspected two saved captures; no solver execution or engineering acceptance')
