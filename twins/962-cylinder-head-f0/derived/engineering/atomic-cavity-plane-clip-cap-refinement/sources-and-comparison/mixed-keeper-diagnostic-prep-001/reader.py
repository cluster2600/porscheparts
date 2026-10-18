"""One exact mixed-graph keeper diagnostic; no native keeper/CDT or geometry export."""
import ast
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
HELPERS={'need','sub','cross','dot','measure','selected_rows','rational'}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()

def load_helpers(path, expected):
    if digest(path)!=expected:raise ValueError('Frozen helper source changed')
    tree=ast.parse(Path(path).read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in HELPERS]
    if {n.name for n in nodes}!=HELPERS:raise ValueError('Exact helper definition set')
    namespace={'F':F,'Path':Path,'math':math,'struct':struct}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    return namespace

def components(edges):
    parent={v:v for edge in edges for v in edge}
    def find(v):
        while parent[v]!=v:parent[v]=parent[parent[v]];v=parent[v]
        return v
    for a,b in edges:
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    groups=defaultdict(list)
    for v in sorted(parent):groups[find(v)].append(v)
    return dict(sorted(groups.items()))

def build_stars(side,groups):
    owner={v:k for k,members in groups.items() for v in members};stars={k:{} for k in groups};coupled=[]
    for fid,row in side.items():
        touching=sorted({owner[v] for v in row if v in owner})
        if len(touching)>1:coupled.append(fid)
        for k in touching:stars[k][fid]=row
    return stars,coupled

def rank_group(points,star,members,measure):
    candidates=[];member_set=set(members)
    for keeper in sorted(members):
        surviving=[];dropped=[];normal_failures=[];score=None
        for fid,row in star.items():
            mapped=tuple(keeper if v in member_set else v for v in row);metric=measure(points,row,mapped)
            if metric is None:dropped.append(fid);continue
            q2,normal_dot=metric;surviving.append(fid)
            if normal_dot<=0:normal_failures.append(fid)
            score=q2 if score is None else min(score,q2)
        candidates.append({'keeper':keeper,'eligible':bool(surviving) and not normal_failures,'minimum_exact_q2':score,'surviving_face_ids':surviving,'dropped_face_ids':dropped,'nonpositive_normal_face_ids':normal_failures})
    eligible=[r for r in candidates if r['eligible']]
    best=max(eligible,key=lambda r:(r['minimum_exact_q2'],-r['keeper'])) if eligible else None
    return {'members':members,'selected_keeper':best['keeper'] if best else None,'selected_minimum_exact_q2':best['minimum_exact_q2'] if best else None,'candidates':candidates}

def map_cycles(cycles,mapping):
    result=[]
    for cycle in cycles:
        mapped=[]
        for v in cycle:
            w=mapping.get(v,v)
            if not mapped or mapped[-1]!=w:mapped.append(w)
        if len(mapped)>1 and mapped[-1]==mapped[0]:mapped.pop()
        result.append(mapped)
    return result

def classify(points,side,mapping,measure):
    bad=[];old_bad=[];dropped=[];changed=[];signs=Counter();bad_signs=Counter();minimum=None
    for fid,row in side.items():
        if measure(points,row,row)[0]<F(4,841):old_bad.append(fid)
        mapped=tuple(mapping.get(v,v) for v in row);metric=measure(points,row,mapped)
        if metric is None:dropped.append(fid);continue
        q2,dot=metric;sign='positive' if dot>0 else 'negative' if dot<0 else 'zero';signs[sign]+=1
        if mapped!=row:changed.append(fid)
        if minimum is None or (q2,fid)<minimum:minimum=q2,fid
        if q2<F(4,841):bad.append(fid);bad_signs[sign]+=1
    worst=None
    if minimum:
        q2,fid=minimum;worst={'source_face_id':fid,'original_source_vertex_ids':side[fid],'mapped_source_vertex_ids':[mapping.get(v,v) for v in side[fid]],'quality_squared':q2,'approximate_quality_not_native_float':math.sqrt(float(q2))}
    return {'source_noncap_faces':len(side),'surviving_noncap_faces':len(side)-len(dropped),'dropped_source_face_ids':dropped,'poor_source_face_ids':bad,'poor_faces':len(bad),'original_poor_source_face_ids':old_bad,'remaining_previously_poor_source_face_ids':sorted(set(bad)&set(old_bad)),'newly_poor_source_face_ids':sorted(set(bad)-set(old_bad)),'changed_surviving_source_face_ids':changed,'normal_sign_counts':{k:signs[k] for k in ('positive','zero','negative')},'poor_normal_sign_counts':{k:bad_signs[k] for k in ('positive','zero','negative')},'worst_quality_record':worst}

def encode(value):
    if isinstance(value,F):return {'numerator':str(value.numerator),'denominator':str(value.denominator)}
    if isinstance(value,dict):return {k:encode(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [encode(v) for v in value]
    return value

def main():
    begin=time.monotonic();folder=Path(__file__).resolve().parent;contract_path=folder/'frozen-contract.json';c=json.loads(contract_path.read_text());output=folder/'readback-report.json'
    if c.get('diagnostic_launch_authorized') is not True or c.get('root_and_peer_review_complete') is not True:raise ValueError('Separate reviewed diagnostic launch required')
    if output.resolve()!=(ROOT/c['expected_output']).resolve() or output.exists() or output.is_symlink():raise ValueError('Fresh exact output required')
    if digest(__file__)!=c['reader_sha256'] or digest(sys.executable)!=c['runtime']['python_executable_sha256']:raise ValueError('Reader/interpreter identity')
    for name,h in c['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Before input drift: '+name)
    h=load_helpers(ROOT/c['helper_source'],c['helper_sha256']);need=h['need'];measure=h['measure'];selected=h['selected_rows']
    retained=json.loads((ROOT/c['frozen_readback']).read_text());reference=json.loads((ROOT/c['repair_reference']).read_text());mixed=json.loads((ROOT/c['mixed_graph_record']).read_text());census=json.loads((ROOT/c['census_record']).read_text());native=json.loads((ROOT/c['source_native_report']).read_text())
    ids=native['native_reference_face_ids'];mask=bytearray(1739126)
    need(len(ids)==9872 and ids==sorted(set(ids)),'Complete incident IDs')
    for v in ids:need(type(v) is int and 0<=v<len(mask),'Typed incident IDs');mask[v]=1
    need(hashlib.sha256(mask).hexdigest()==retained['candidate']['exact_incident_patch_mask_sha256'],'Frozen complete incident mask')
    region,=census['exact_seed_incident_patch_components'];need(region['face_ids']==ids and len(region['topology']['boundary_vertices'])==2012,'Complete frozen region/fixed-in-region association')
    rows,points,raw=selected(ROOT/c['source_geometry'],ids,869355,1739126);need(len(points)==5938,'Incident vertex count')
    cycles=reference['cap']['components'][0]['topology']['oriented_boundary_cycles'];need([len(v) for v in cycles]==[1482,2026],'Frozen cap cycles')
    missing=sorted({v for cycle in cycles for v in cycle}-set(points));need(missing==c['additional_cap_cycle_point_ids'] and len(missing)==38,'Exactly declared existing loop point rows')
    with (ROOT/c['source_geometry']).open('rb') as stream:
        for vid in missing:
            stream.seek(24+24*vid);bits=stream.read(24);xyz=struct.unpack('<ddd',bits);need(all(math.isfinite(v) for v in xyz) and xyz[2]==0,'Finite original extra cap coordinate');raw[vid]=bits;points[vid]=tuple(F(v) for v in xyz)
    areas=[sum(points[a][0]*points[b][1]-points[a][1]*points[b][0] for a,b in zip(loop,loop[1:]+loop[:1]))/2 for loop in cycles]
    need(areas[0]>0 and areas[1]<0,'Exact source inner/outer signed-area association')
    mixed_ids=retained['candidate']['plane_classes']['noncap_mixed_plane_vertices']['poor_face_ids'];records={r['face_id']:r['minimum_edges'] for r in reference['shortest_edges']['ordered_exact_squared_lengths']}
    edges=sorted({tuple(e) for fid in mixed_ids for e in records[fid]});groups=components(edges);scenario=mixed['scenarios']['all_tied_minima']
    canonical=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    need(len(mixed_ids)==716 and len(edges)==716 and len(groups)==506 and sum(map(len,groups.values()))==1222,'Exact mixed graph counts')
    need(canonical(edges)==scenario['ordered_edges_canonical_json_sha256'] and canonical(list(groups.values()))==scenario['ordered_component_vertices_canonical_json_sha256'],'Complete frozen graph identities')
    need(Counter(map(len,groups.values()))==Counter({2:296,3:210}),'Only the frozen pairs/triples')
    fixed=set(region['topology']['boundary_vertices']);members={v for row in groups.values() for v in row};seed={v for fid in native['native_poor_face_ids'] for v in rows[fid]}
    need(members<=set(cycles[0]) and not members.intersection(cycles[1]) and not members.intersection(fixed) and members<=seed and all(points[v][2]==0 for v in members),'Complete cap/seed/free/outer association')
    prior={v:g for g in reference['shortest_edges']['all_tied_minima']['components'] for v in g['vertex_ids']}
    for group in groups.values():need(len({prior[v]['component_minimum'] for v in group})==1 and all(not prior[v]['fixed_conflict_ids'] for v in group),'Prior no-fixed-conflict association')
    side={fid:row for fid,row in rows.items() if not all(points[v][2]==0 for v in row)};need(len(side)==6402,'Complete selected noncap source rows')
    stars,coupled=build_stars(side,groups);choices=[];mapping={};refused=[]
    for key,group in groups.items():
        choice=rank_group(points,stars[key],group,measure);choice['component_minimum']=key;choice['complete_side_star_face_ids']=list(stars[key]);choices.append(choice)
        if choice['selected_keeper'] is None:refused.append(key)
        else:
            for v in group:mapping[v]=choice['selected_keeper']
    mapped=None;simultaneous=None;cycle_observations={'original_cycles':cycles,'mapped_cycles':None,'original_exact_signed_areas':areas,'mapped_exact_signed_areas':None,'outer_cycle_index':1,'outer_source_ID_sequence_and_coordinate_bits_unchanged':None,'simplicity_nesting_hole_or_CDT_domain_audited':False}
    if not refused:
        mapped=map_cycles(cycles,mapping);need(mapped[1]==cycles[1],'Outer loop must remain exactly unchanged')
        simultaneous=classify(points,side,mapping,measure)
        cycle_observations={'original_cycles':cycles,'mapped_cycles':mapped,'original_exact_signed_areas':areas,'mapped_exact_signed_areas':[sum(points[a][0]*points[b][1]-points[a][1]*points[b][0] for a,b in zip(loop,loop[1:]+loop[:1]))/2 for loop in mapped],'outer_cycle_index':1,'outer_source_ID_sequence_and_coordinate_bits_unchanged':True,'mapped_cycles_have_at_least3_distinct_IDs':all(len(set(v))>=3 for v in mapped),'mapped_cycle_IDs_unique_and_disjoint':len({v for row in mapped for v in row})==sum(map(len,mapped)),'simplicity_nesting_hole_or_CDT_domain_audited':False}
    for name,hsh in c['input_sha256'].items():need(digest(ROOT/name)==hsh,'After input drift: '+name)
    result={'schema':'962-exact-mixed-keeper-readonly-diagnostic/v1','status':'complete_independent_choices_and_simultaneous_side_census' if not refused else 'no_complete_keeper_map','contract_sha256':digest(contract_path),'reader_sha256':digest(__file__),'helper_sha256':c['helper_sha256'],'helper_definitions_extracted_unchanged':sorted(HELPERS),'graph_edges':edges,'groups_and_all_keeper_candidates':choices,'groups_without_eligible_nonempty_star':refused,'complete_coupled_side_face_ids':coupled,'simultaneous_side_census':simultaneous,'cap_cycle_observations':cycle_observations,
      'selection_policy':'Independent complete noncap stars; require positive exact old dot mapped normals and nonempty survivors; maximize minimum exact q²; lowest source ID resolves exact ties. No2/29 score eligibility cutoff. Other groups are unchanged while ranking one group.',
      'decoded_source_faces':9872,'incident_source_points':5938,'additional_existing_cap_cycle_point_rows':38,'total_decoded_source_points':len(points),'fixed_in_region_basis':'Exact frozen incident-boundary vertex set and209a mask; observed exterior-only fixed865429 has2012 members in this region. No new repair constraint is approved.',
      'no_complete_map_is_a_retained_diagnostic_refusal':True,'independent_choices_guarantee_simultaneous_feasibility':False,'cap_triangulated_or_full_candidate_exported':False,'geometry_files_written':False,'global_topology_domain_distance_features_or_head_admitted':False,'material_LPBF_or_manufacturing_qualified':False,'exterior_goodness_attributed_to_frozen_full_array_readback':True,'all_bound_inputs_unchanged':True,'wall_seconds':time.monotonic()-begin}
    with output.open('x') as stream:json.dump(encode(result),stream,indent=2,allow_nan=False);stream.write('\n')

if __name__=='__main__':main()
