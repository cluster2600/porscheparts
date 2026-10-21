"""Independent literal-fixture event checks; no CGAL/controller import or native call."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def squared_cross(a, b, c):
    u = [Fraction(b[i])-Fraction(a[i]) for i in range(3)]
    v = [Fraction(c[i])-Fraction(a[i]) for i in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    return sum(x*x for x in n)


def literal_setup(case):
    p, faces = case['points'], case['faces']; seeds = set(); count = 0
    for f in faces:
        a,b,c = [p[i] for i in f]
        lengths = sum(sum((u[i]-v[i])**2 for i in range(3)) for u,v in ((a,b),(b,c),(c,a)))
        q = 2*math.sqrt(3)*math.sqrt(float(squared_cross(a,b,c)))/lengths
        if q < 2/29:
            count += 1; seeds.update(f)
    fixed = {i for f in faces if not seeds.intersection(f) for i in f}
    fixed.update(i for i,x in enumerate(p) if x[0] in (-76,76))
    return dict(original_seed_faces=count, reference_faces=sum(bool(seeds.intersection(f)) for f in faces),
                fixed_source_vertices=len(fixed), budget_mm=0.0625)


def assess(rows, case):
    assert rows and all(isinstance(r,dict) for r in rows)
    assert rows[0]['event']=='setup' and rows[-1]['event']=='complete'
    assert sum(r['event']=='setup' for r in rows)==sum(r['event']=='complete' for r in rows)==1
    assert literal_setup(case)==case['setup']
    for k,v in case['setup'].items(): assert rows[0][k]==v
    target=[8,9]; names=[r['event'] for r in rows]
    for index,row in enumerate(rows):
        assert isinstance(row['event'],str) and row['event'] in case['allowed_events']
        assert row['edge_current_ids']==([0,0] if index==0 else target)
        origin=row['endpoint_original_id']; assert origin is None or type(origin) is int and origin in (8,9)
        if row['event'].startswith('topology.'): assert row['phase']=='final_topology'
        if row['event'].startswith('placement.'): assert row['phase']=='independent_final_placement'
        if row['event'].startswith('ordinary.'): assert row['phase']=='final_ordinary_geometry'
    final=[r for r in rows if r['event']=='final_profile_result']; assert len(final)==1
    final=final[0]
    assert type(final['topology']) is bool and final['topology'] is case['topology']
    assert type(final['choice_present']) is bool and final['choice_present'] is (case['choice_origin'] is not None)
    assert final['ordinary_geometry'] is case['ordinary_geometry']
    assert final['endpoint_original_id']==case['choice_origin'] and final['phase']=='final_result'
    assert names.index('final_profile_result')==len(rows)-2
    assert case['required_event'] in names
    choices=[r for r in rows if r['event']=='placement.choice_present']
    if case['choice_origin'] is None:
        assert not choices and case['all_fixed_required_placement_event'] in names
        assert 'ordinary.not_evaluated_no_choice_or_topology' in names
    else:
        assert len(choices)==1 and choices[0]['endpoint_original_id']==case['choice_origin']
        assert [r['endpoint_original_id'] for r in rows if r['event']=='placement.endpoint_begin']==[8,9]
        quality=[r for r in rows if r['event']=='placement.quality_values']
        assert [r['endpoint_original_id'] for r in quality]==[8,9]
        for q in quality:
            assert type(q['before_bad']) is int and q['before_bad']==case['setup']['original_seed_faces']
            assert type(q['after_bad']) is int and q['after_bad']==q['before_bad']-2
            for key in ('before_minimum','after_minimum'):
                assert type(q[key]) in (int,float) and math.isfinite(q[key]) and 0<q[key]<=1
            assert q['after_minimum']>=q['before_minimum']
        assert quality[0]['after_minimum']>quality[1]['after_minimum']
    points={tuple(p) for p in case['points']}; pairs=0; obstruction=False
    for row in rows:
        if 'ordered_points_mm' not in row: continue
        assert row['event'] in ('ordinary.dihedral','ordinary.area_ratio') and type(row['passed']) is bool
        pp=row['ordered_points_mm']; assert len(pp)==4 and all(tuple(p) in points for p in pp)
        values=[squared_cross(pp[0],pp[1],pp[2]),squared_cross(pp[0],pp[2],pp[3])]
        larger,smaller=max(values),min(values); assert smaller>0
        for key,value in [('larger_squared_cross_norm',larger),('smaller_squared_cross_norm',smaller)]:
            assert type(row[key]) in (int,float) and math.isfinite(row[key]) and row[key]==float(value)
        ratio_pass=larger<100000000*smaller
        assert (row['event']=='ordinary.dihedral') is ratio_pass
        if not ratio_pass:
            assert row['passed'] is False
            if case['exact_obstruction_ratio'] is not None:
                obstruction |= larger/smaller==Fraction(case['exact_obstruction_ratio'])
        if case['ordinary_geometry'] is True: assert row['passed'] is True
        pairs+=1
    if case['ordinary_geometry'] is not None: assert pairs>0
    if case['exact_obstruction_ratio'] is not None: assert obstruction
    complete=rows[-1]; assert complete['phase']=='complete' and complete['endpoint_original_id'] is None and complete['target_count']==1
    for k in ('SMS_run_called','mesh_exported','historical_veto_identified','solver_admission','engineering_accepted'):
        assert complete[k] is False
    return dict(passed=True,events=len(rows),ordinary_pairs_independently_checked=pairs,
                native_history_inferred=False,head_or_solver_admission=False)


def reject_constant(value):
    raise ValueError('Nonfinite JSON constant refused: '+value)


if __name__=='__main__':
    if len(sys.argv)!=5: raise ValueError('case events.jsonl expectations-SHA256 fresh-result.json required')
    case,path,expected,output=sys.argv[1:]; raw=(HERE/'expectations.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected
    expected_case=json.loads(raw)['cases'][case]
    rows=[json.loads(line,parse_constant=reject_constant) for line in Path(path).read_text().splitlines()]
    result=assess(rows,expected_case)
    result.update(case=case,events_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                  checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),native_executed_by_checker=False)
    with Path(output).open('x') as f: json.dump(result,f,indent=2);f.write('\n')
