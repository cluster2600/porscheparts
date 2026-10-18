"""One exact saved-data graph intersection; no coordinate or native geometry operation."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'prepared'
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
def uf_groups(edges):
    parent={v:v for edge in edges for v in edge}
    def find(v):
        while parent[v]!=v: parent[v]=parent[parent[v]]; v=parent[v]
        return v
    for a,b in edges:
        a,b=find(a),find(b)
        if a!=b: parent[max(a,b)]=min(a,b)
    groups=defaultdict(list)
    for v in sorted(parent): groups[find(v)].append(v)
    return dict(groups)
def cyclic_runs(loop,members):
    selected=set(members)
    assert selected and selected<=set(loop)
    return 1 if len(selected)==len(loop) else sum(v in selected and loop[i-1] not in selected for i,v in enumerate(loop))
def boundary_edges(loops):
    return {tuple(sorted((v,loop[(i+1)%len(loop)]))) for loop in loops for i,v in enumerate(loop)}

def main():
    contract_path=HERE/'frozen-contract.json'
    assert len(sys.argv)==2 and digest(contract_path)==sys.argv[1], 'Exact contract required'
    c=json.loads(contract_path.read_text())
    assert c['saved_JSON_preparation_authorized'] is True and c['native_execution_authorized'] is False
    before={name:digest(ROOT/name) for name in c['input_sha256']}
    assert before==c['input_sha256'] and digest(Path(__file__))==c['source_sha256']
    assert not OUT.exists() and not OUT.is_symlink(), 'Fresh output required'
    # Known literal cases: exact intersection, removal of a chord, cyclic wrap, and whole cycle.
    l=[0,1,2,3,4,5]; e={(0,1),(1,2),(2,3),(3,4),(4,5),(0,5)}
    assert boundary_edges([l])==e
    assert sorted(({(0,1),(1,2),(0,2),(4,5),(0,5)})&e)==[(0,1),(0,5),(1,2),(4,5)]
    assert uf_groups([(0,1),(0,5),(1,2),(4,5)])=={0:[0,1,2,4,5]}
    assert cyclic_runs(l,[4,5,0,1,2])==1 and cyclic_runs(l,[0,2])==2 and cyclic_runs(l,l)==1
    r=json.loads((ROOT/c['reference']).read_text())
    screen=json.loads((ROOT/c['rim_screen']).read_text())
    old_raw=(ROOT/c['original_targets']).read_bytes()
    old=list(struct.iter_unpack('<QQ',old_raw))
    assert old==[tuple(e) for e in r['shortest_edges']['all_tied_minima']['unique_edge_ids']]
    assert len(old)==2700 and old==sorted(set(old)) and all(a<b for a,b in old)
    original_groups=uf_groups(old)
    expected={g['component_minimum']:g for g in r['shortest_edges']['all_tied_minima']['components']}
    assert len(original_groups)==476
    assert original_groups=={k:v['vertex_ids'] for k,v in expected.items()}
    assert all(not g['fixed_conflict_ids'] for g in expected.values())
    loops=r['cap']['components'][0]['topology']['oriented_boundary_cycles']
    assert [len(l) for l in loops]==[1482,2026]
    locations={v:(k,j) for k,l in enumerate(loops) for j,v in enumerate(l)}
    assert len(locations)==3508 and len(locations)==sum(map(len,loops))
    boundary=boundary_edges(loops); assert len(boundary)==3508
    targets=sorted(set(old)&boundary)
    assert len(targets)==2212 and set(targets)<=set(old) and set(targets)<=boundary
    groups=uf_groups(targets); assert len(groups)==510
    old_owner={v:k for k,values in original_groups.items() for v in values}
    rows=[]
    for first,members in groups.items():
        loop_ids={locations[v][0] for v in members}; prior={old_owner[v] for v in members}
        assert len(loop_ids)==len(prior)==1
        k=next(iter(loop_ids)); parent=next(iter(prior)); count=cyclic_runs(loops[k],members)
        assert count==1 and set(members)<=set(expected[parent]['vertex_ids'])
        assert not expected[parent]['fixed_conflict_ids']
        rows.append(dict(component_minimum=first,member_ids=members,cap_loop=k,cyclic_runs=count,
                         prior_component_minimum=parent,prior_fixed_conflicts=[]))
    assert screen['full_query_completed'] is True and screen['all_bound_inputs_unchanged'] is True
    failed=[tuple(e) for e in screen['failed_completed_edge_ids']]
    assert len(failed)==len(set(failed))==1474
    assert all(e in boundary for e in failed) and set(failed)<=set(targets)
    after={name:digest(ROOT/name) for name in before}
    assert after==before and digest(Path(__file__))==c['source_sha256'] and digest(contract_path)==sys.argv[1]
    encoded=b''.join(struct.pack('<QQ',a,b) for a,b in targets)
    assert list(struct.iter_unpack('<QQ',encoded))==targets
    OUT.mkdir()
    with (OUT/'targets.u64').open('xb') as f:f.write(encoded)
    result=dict(schema='962-cap-aware-boundary-target-observations/v1',
        status='exact_all_matching_boundary_edge_graph_prepared_no_geometry_or_native_execution',
        original_edges=2700,original_UF_groups=476,cap_boundary_edges=3508,cap_cycle_lengths=list(map(len,loops)),
        retained_edges=len(targets),removed_nonboundary_edges=len(old)-len(targets),UF_groups=len(groups),
        target_vertices=sum(map(len,groups.values())),group_size_histogram=dict(sorted(Counter(map(len,groups.values())).items())),
        all_groups_one_cyclic_run=True,all_groups_one_cap_loop=True,all_groups_subsets_of_prior_no_fixed_conflict_groups=True,
        necessary_rim_screen_failing_edges=1474,all1474_covered=True,missing_failing_edges=[],groups=rows,
        targets_bytes=len(encoded),targets_sha256=hashlib.sha256(encoded).hexdigest(),
        source_sha256=c['source_sha256'],contract_sha256=sys.argv[1],input_sha256=before,all_bound_inputs_unchanged=True,
        selection='Every edge in the exact intersection of all2700 frozen tied-minimum existing edges and all3508 actual oriented-cap-cycle boundary edges; no length cutoff or further subset.',
        scope='This removes the demonstrated separated-run obstruction only. Independent side-star choices, simultaneous normals, cap coverage, global quality, ordinary neighbors, envelope and later independent global/distance/volume gates remain untested for this proposal.',
        keeper_selected=False,geometry_or_coordinates_modified=False,native_execution_authorized=False,
        head_surface_or_physics_or_manufacturing_admitted=False)
    with (OUT/'report.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    with (OUT/'self-check.json').open('x') as f:json.dump(dict(status='pass_four_literal_stdlib_checks_and_complete_saved_graph_association',source_sha256=c['source_sha256'],contract_sha256=sys.argv[1],targets_binary_roundtrip=True,complete_510_group_checks=True,all1474_failing_edges_covered=True,report_sha256=digest(OUT/'report.json')),f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('retained_edges','UF_groups','target_vertices','targets_bytes','targets_sha256','all_groups_one_cyclic_run','all1474_covered')}))
if __name__=='__main__':main()
