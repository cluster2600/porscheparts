"""Saved-reference/target checks only; no head geometry or native library is loaded."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT/'work/962-engineering'
PATHS = {
    'held': ('atomic-cavity-plane-clip-cap-aware-head-prep-001/held-preparation.json', '20d675b3e29be3ad14f4b1fded16fa7aae08c64b9a49d4a6fe519f8af7e94ccb'),
    'preparation': ('atomic-cavity-plane-clip-cap-aware-head-prep-001/preparation.json', None),
    'targets': ('atomic-cavity-plane-clip-cap-aware-head-prep-001/targets.u64', 'bfa804a820e3a98fc82f0fa19d547a4963a275be36ec60ff768fdd1712b9db4a'),
    'reference': ('atomic-cavity-plane-clip-repair-reference-001/readback-report.json', 'ebf9dd540d32ff6dd2d47267a94d8500b498b30e783288a91eba5c556d21b108'),
    'source': ('atomic-cavity-plane-clip-cap-aware-repair-prep-002/cap_aware_002.cpp', 'ac5a70abb560b1868188ca78d69e26cfabeedafe47ae5302b6bb2fa4654dfc3f'),
    'policy': ('atomic-cavity-plane-clip-cap-aware-repair-prep-002/atomic_policy.hpp', '7ffb32ad2923f2e7ddbe2e78f56655aa0b80e40e01e237e331ffccf6395af825'),
    'head_binding': ('atomic-cavity-plane-clip-cap-aware-repair-prep-002/head_binding.hpp', 'c7c26e411ba1aab85cc360133926fed766b170d88c54455a5a3e71ea822d2c57'),
    'binary': ('atomic-cavity-plane-clip-cap-aware-compile-001/cap-aware', '1cd441fa6f071a79c7cd6736dfb86e40759819d63a91a6b33b341f18661e54fc'),
    'compile_summary': ('atomic-cavity-plane-clip-cap-aware-compile-001/phase-summary.json', None),
    'fixture_summary': ('atomic-cavity-plane-clip-cap-aware-fixtures-001/phase-summary.json', '5e91e1125fdae1f6007e9465d057c332233311948a2c8b9410d5b6bb6ef86400'),
    'fixture_assessment': ('atomic-cavity-plane-clip-cap-aware-fixture-assessment-001/receipt.json', None),
    'controller': ('atomic-cavity-plane-clip-cap-aware-phase-prep-001/run_finest_patch_phase.py', 'c2191896dba65d38cf41222f51dcab29c7896624481d1beb4b1b097c0546a440'),
    'metadata': ('atomic-cavity-plane-clip-cap-aware-phase-prep-001/run_finest_endpoint_metadata.py', 'a88477c47d406cea3761c324e1f6eb82dcb1c2b962698d7f328261c6cef2929b'),
    'cleanup': ('atomic-cavity-plane-clip-cap-aware-phase-prep-001/run_finest_endpoint_preflight.py', 'b214e1cece8dbf66be6071199cbdf1a8e22a2a59328888011de17492f923c86b'),
}
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()
def snapshot():
    values={role:digest(BASE/name) for role,(name,_) in PATHS.items()}
    for role,(_,expected) in PATHS.items():
        if expected is not None: assert values[role]==expected, role
    return values

def run_count(loop, members):
    members=set(members)
    assert members and members <= set(loop)
    starts=[i for i,v in enumerate(loop) if v in members and loop[i-1] not in members]
    return (1 if len(members)==len(loop) else len(starts)), starts

assert run_count([0,1,2,3], [3,0])[0]==1
assert run_count([0,1,2,3], [0,2])[0]==2
assert run_count([0,1,2,3], [0,1,2,3])[0]==1
before=snapshot()
held=json.loads((BASE/PATHS['held'][0]).read_text())
r=json.loads((BASE/PATHS['reference'][0]).read_text())
raw=(BASE/PATHS['targets'][0]).read_bytes()
edges=list(struct.iter_unpack('<QQ',raw))
assert len(raw)==43200 and len(edges)==2700
assert edges==sorted(set(edges)) and all(a<b for a,b in edges)
assert edges==[tuple(e) for e in r['shortest_edges']['all_tied_minima']['unique_edge_ids']]
parent={v:v for edge in edges for v in edge}
def find(v):
    while parent[v]!=v: parent[v]=parent[parent[v]]; v=parent[v]
    return v
for a,b in edges:
    a,b=find(a),find(b)
    if a!=b: parent[max(a,b)]=min(a,b)
groups=defaultdict(list)
for v in sorted(parent): groups[find(v)].append(v)
expected={g['component_minimum']:g['vertex_ids'] for g in r['shortest_edges']['all_tied_minima']['components']}
assert dict(groups)==expected and len(groups)==476
loops=r['cap']['components'][0]['topology']['oriented_boundary_cycles']
assert [len(x) for x in loops]==[1482,2026]
locations={v:(k,i) for k,loop in enumerate(loops) for i,v in enumerate(loop)}
assert len(locations)==sum(map(len,loops))==3508
rows=[]
for first,members in sorted(groups.items()):
    loop_ids={locations[v][0] for v in members}; assert len(loop_ids)==1
    k=next(iter(loop_ids)); n,starts=run_count(loops[k],members)
    rows.append(dict(component_minimum=first,member_count=len(members),cap_loop=k,
                     cyclic_runs=n,run_start_positions=starts,
                     run_start_vertex_ids=[loops[k][i] for i in starts]))
fail=[row for row in rows if row['cyclic_runs']!=1]
assert len(fail)==48
for role in ('source','binary','targets'): assert held[role+'_sha256']==before[role]
assert held['native_launch_authorized'] is False
assert held['controls']==dict(cpus=2,memory_bytes=4294967296,swap_bytes=0,hard_wall_seconds=300,tmpfs_bytes=0,network='none',automatic_retry=False)
phase_checks={}
for label,role in [('compile','compile_summary'),('fixtures','fixture_summary')]:
    phase=json.loads((BASE/PATHS[role][0]).read_text())
    assert phase['procedural_phase_finished'] and phase['all_inputs_unchanged']
    assert phase['actual_before_sha256']==phase['actual_after_sha256']
    pins=phase['actual_before_sha256']; observed={name:digest(ROOT/name) for name in pins}
    assert observed==pins
    phase_checks[label]=dict(input_count=len(pins),all_current=True)
fixture=json.loads((BASE/PATHS['fixture_assessment'][0]).read_text())
assert fixture['expected_native_returncodes']==[0,0,3,3]
assert fixture['status']=='pass_four_native_synthetic_cases_and_complete_saved_array_oracle'
after=snapshot(); assert after==before
result=dict(status='necessary_cyclic_contiguity_failure_no_head_execution',
    source_sha256=digest(Path(__file__)),input_sha256=before,all_inputs_unchanged=True,
    targets_exact_reference_rows=True,UF_memberships_exact_reference=True,target_edges=len(edges),UF_groups=len(groups),
    boundary_cycle_lengths=list(map(len,loops)),same_single_loop_all_groups=True,
    cyclic_run_histogram=dict(sorted(Counter(x['cyclic_runs'] for x in rows).items())),
    contiguous_groups=len(rows)-len(fail),noncontiguous_groups=len(fail),groups=rows,
    compile_and_fixture_saved_record_current_pin_checks=phase_checks,
    proof='For any single keeper per disjoint UF group, each maximal cyclic membership run maps to that same keeper ID. Other groups use disjoint member IDs, so a nonempty intervening run cannot map to that keeper. Consecutive and wrap-end duplicate removal cannot erase separated occurrences; source rejects the second occurrence before CDT. Other earlier refusals remain possible.',
    native_or_geometry_operation_performed=False,head_acceptance_or_physics_established=False)
with (HERE/'cyclic-run-check.json').open('x') as f: json.dump(result,f,indent=2); f.write('\n')
print(json.dumps({k:result[k] for k in ('status','UF_groups','contiguous_groups','noncontiguous_groups','cyclic_run_histogram')}))
