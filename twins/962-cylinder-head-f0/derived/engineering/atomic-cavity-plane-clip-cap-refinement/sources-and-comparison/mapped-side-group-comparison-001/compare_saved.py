"""Saved JSON graph/star join only; no mesh reads or quality calculations."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/962-engineering'
OUT=Path(__file__).parent
INPUTS={
 'atomic-cavity-plane-clip-cap-aware-mapped-side-diagnostic-001/readback-report.json':'067f0c15ac193607b624cece45a08cac358d64db153961a59c108f02a9be4a53',
 'atomic-cavity-plane-clip-cap-aware-boundary-head-001/head-boundary/report.json':'19e0e6b26b23e3e657bcaaa4e00c4ab3289fbce54c6b442f5e763cf3c39f1b81',
 'atomic-cavity-plane-clip-repair-reference-001/readback-report.json':'ebf9dd540d32ff6dd2d47267a94d8500b498b30e783288a91eba5c556d21b108',
 'atomic-cavity-plane-clip-readback-001/readback-report.json':'209a4a35033c036ee4f0dc66c6285e49db4c85f1039d89feb52b45899562db80',
 'atomic-cavity-plane-clip-repair-reference-result-peer-001/mixed-poor-exploratory-query.json':'ceb6769c7ab98cd666a1d73fefa8e56e999440abd0d6a7ba41eeb675d6cbaff5',
 'atomic-cavity-plane-clip-cap-aware-boundary-targets-prep-001/prepared/report.json':'2c9d636eca55a6aabc9418bfb0f5b4b9ff9a410ca6a7aa7a09ee71817b6b71eb'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def graph(edges):
    parent={v:v for e in edges for v in e}
    def find(v):
        while parent[v]!=v:parent[v]=parent[parent[v]];v=parent[v]
        return v
    for a,b in edges:
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    groups=defaultdict(list)
    for v in sorted(parent):groups[find(v)].append(v)
    return dict(sorted(groups.items()))

def main():
    for p,h in INPUTS.items():assert sha(BASE/p)==h
    data={p:json.loads((BASE/p).read_text()) for p in INPUTS}
    query,native,reference,retained,mixed,boundary=[data[p] for p in INPUTS]
    assert query['native_report_sha256']==INPUTS['atomic-cavity-plane-clip-cap-aware-boundary-head-001/head-boundary/report.json']
    assert query['poor_count_exact']==728 and query['poor_source_face_ids_exact']==query['newly_poor_source_face_ids_exact'] and query['remaining_previously_poor_source_face_ids_exact']==[]
    bad=set(query['poor_source_face_ids_exact']);assert len(bad)==728 and bad<=set(query['changed_surviving_source_face_ids'])
    records={r['face_id']:r['minimum_edges'] for r in reference['shortest_edges']['ordered_exact_squared_lengths']}
    classes=retained['candidate']['plane_classes'];mixed_faces=set(classes['noncap_mixed_plane_vertices']['poor_face_ids']);cap_faces=set(classes['cap_all_z0']['poor_face_ids'])
    assert len(mixed_faces)==716 and not classes['noncap_no_plane_vertices']['poor_face_ids']
    all_edges=sorted({tuple(e) for row in records.values() for e in row});mixed_edges=sorted({tuple(e) for f in mixed_faces for e in records[f]})
    assert all_edges==[tuple(e) for e in reference['shortest_edges']['all_tied_minima']['unique_edge_ids']]
    caploops=reference['cap']['components'][0]['topology']['oriented_boundary_cycles']
    loop_edges={tuple(sorted((a,b))) for row in caploops for a,b in zip(row,row[1:]+row[:1])}
    boundary_edges=sorted(set(all_edges)&loop_edges);boundary_groups=graph(boundary_edges);mixed_groups=graph(mixed_edges)
    assert len(boundary_edges)==2212 and len(boundary_groups)==510 and len(mixed_edges)==716 and len(mixed_groups)==506
    serialized=b''.join(struct.pack('<QQ',*e) for e in boundary_edges)
    assert hashlib.sha256(serialized).hexdigest()==boundary['targets_sha256']=='bfc9d79d0d5373f0b8c93ce58377fa99056a9be6486a5beda9e85a89858c9d28'
    assert boundary_groups=={g['component_minimum']:g['member_ids'] for g in boundary['groups']}
    scenario=mixed['scenarios']['all_tied_minima'];assert canonical_sha(mixed_edges)==scenario['ordered_edges_canonical_json_sha256']
    assert canonical_sha(list(mixed_groups.values()))==scenario['ordered_component_vertices_canonical_json_sha256']
    assert Counter(len(v) for v in mixed_groups.values())==Counter({2:296,3:210})
    choices={g['component_minimum']:g for g in native['group_choices']};assert len(choices)==510
    for k,g in choices.items():assert g['members']==boundary_groups[k] and g['selected_keeper'] in g['members']
    owner={v:k for k,vertices in boundary_groups.items() for v in vertices};mixed_vertices={v for vertices in mixed_groups.values() for v in vertices}
    mixed_component_rows=[]
    for k,members in mixed_groups.items():
        parents=sorted({owner[v] for v in members});assert len(parents)==1
        mixed_component_rows.append({'component_minimum':k,'member_ids':members,'containing_current_boundary_group':parents[0]})
    face_groups={fid:sorted(k for k,g in choices.items() if fid in g['side_star_faces']) for fid in sorted(bad)}
    assert all(face_groups.values())
    touched=sorted({k for ids in face_groups.values() for k in ids});rows=[];cap_only=set()
    for k in touched:
        g=choices[k];members=set(g['members']);edges=[e for e in boundary_edges if set(e)<=members]
        mixed_overlap=sorted(members&mixed_vertices);edge_overlap=sorted(set(edges)&set(mixed_edges))
        contributors=sorted(f for f,minimum in records.items() if any(tuple(e) in set(edges) for e in minimum))
        contributor_classes={'cap':sorted(set(contributors)&cap_faces),'mixed':sorted(set(contributors)&mixed_faces)}
        is_cap_only=not mixed_overlap and not edge_overlap and set(contributors)<=cap_faces
        if is_cap_only:cap_only.add(k)
        rows.append({'component_minimum':k,'member_ids':g['members'],'size':len(members),'selected_keeper':g['selected_keeper'],'reported_side_star_minimum_quality':g['side_star_minimum_quality'],
          'complete_side_star_face_ids':g['side_star_faces'],'poor_source_face_ids_in_star':sorted(bad&set(g['side_star_faces'])),
          'current_boundary_target_edges':edges,'minimum_edge_contributing_original_poor_face_ids_by_class':contributor_classes,
          'mixed_graph_member_intersection':mixed_overlap,'mixed_graph_edge_intersection':edge_overlap,
          'mixed_graph_components_with_member_intersection':[i for i,v in mixed_groups.items() if members.intersection(v)],
          'cap_loop':next(r['cap_loop'] for r in boundary['groups'] if r['component_minimum']==k),'cap_only_by_frozen_target_provenance':is_cap_only})
    entirely=all(set(ids)<=cap_only for ids in face_groups.values())
    touched_vertices={v for k in touched for v in choices[k]['members']};disjoint=not mixed_vertices.intersection(touched_vertices)
    result={'schema':'962-saved-poor-side-group-comparison/v1','status':'completed_saved_JSON_only_association','scope':'No coordinates/BIN/VTK/NPZ read, quality calculation, keeper choice, CDT, geometry output or native execution. Source-face membership associations use the already checked complete saved side-star lists.',
      'poor_source_faces':728,'poor_face_touching_groups':[{'source_face_id':f,'group_component_minima':v} for f,v in face_groups.items()],
      'touching_group_count':len(touched),'touching_groups':rows,'face_group_incidence_histogram':dict(Counter(len(v) for v in face_groups.values())),
      'all728_associated_only_with_cap_only_groups':entirely,'all_touching_group_sizes_are_329_or410':all(r['size'] in (329,410) for r in rows),
      'exact_mixed_graph':{'edge_ids':mixed_edges,'groups':mixed_component_rows,'edges':len(mixed_edges),'UF_groups':len(mixed_groups),'vertices':len(mixed_vertices),'all_edges_subset_of_current_boundary_targets':set(mixed_edges)<=set(boundary_edges),'ordered_edges_canonical_json_sha256':canonical_sha(mixed_edges),'ordered_component_vertices_canonical_json_sha256':canonical_sha(list(mixed_groups.values()))},
      'exact_mixed_graph_has_no_member_of_poor_touching_groups':disjoint,'mixed_edge_endpoint_intersections_with_poor_touching_groups':sorted({v for e in mixed_edges for v in e}&touched_vertices),
      'interpretation':'If the Boolean association/disjointness checks are true, retaining the exact mixed-only graph avoids contracting these observed cap-only groups. This is membership evidence, not a quality result for any new keeper map or cap triangulation.',
      'new_keeper_or_graph_proposal_selected':False,'quality_for_mixed_only_graph_calculated':False,'cap_poor_count_inferred':False,'geometry_or_gate_changed':False,'head_solver_physical_or_manufacturing_admitted':False,
      'source_geometry_SHA_is_attributed_not_rehashed':query['source_geometry_sha256'],'input_sha256':{'work/962-engineering/'+p:h for p,h in INPUTS.items()},'source_sha256':sha(Path(__file__)),'all_JSON_inputs_unchanged':True}
    for p,h in INPUTS.items():assert sha(BASE/p)==h
    q=OUT/'result.json'
    with q.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'result_sha256':sha(q),'bytes':q.stat().st_size,'groups':[{'id':r['component_minimum'],'size':r['size'],'keeper':r['selected_keeper'],'score':r['reported_side_star_minimum_quality'],'poor_faces':len(r['poor_source_face_ids_in_star']),'loop':r['cap_loop'],'cap_only':r['cap_only_by_frozen_target_provenance']} for r in rows],'all728_cap_only':entirely,'mixed_graph_disjoint':disjoint}))

if __name__=='__main__':main()
