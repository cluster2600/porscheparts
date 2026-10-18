"""Pure exact saved-fixture oracle; no native or scientific imports."""
import ast
from collections import Counter,defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXPECT='edd3f258e3374371b3467b68e254d70033545ba35a920cd2e0c16694f23c5365'
HELPER=ROOT/'work/962-engineering/atomic-cavity-plane-clip-assessment-prep-001/assess_clip.py'
HELPER_SHA='5194356616d0eb2f44b8fd72180364248acf268d8d7ea9b5cfd577367084dacc'
MAX=(1<<64)-1
GUARDS={'cap_domain_coverage_plane_winding_fixed_faces_no_new_points','combined_global_quality',
 'combined_topology_fixed_exterior_oriented_patch_boundary','exact_mapped_two_loop_annulus',
 'final_affected_neighbor_policy','immutable_local_full_triangle_envelope',
 'one_deterministic_independent_keeper_map','reference_and_exact_target_association',
 'exact_frozen_head_poor_IDs_or_nonhead_fixture'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def functions():
    if sha(HELPER)!=HELPER_SHA:raise ValueError('Frozen exact helper changed')
    names={'need','canonical','sub','cross','dot','read','connected','topology','area','side','intersection','rectangle','cover'}
    definitions=[n for n in ast.parse(HELPER.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names]
    if len(definitions)!=len(names):raise ValueError('Complete exact retained functions required')
    namespace=dict(Counter=Counter,defaultdict=defaultdict,F=F,Path=Path,math=math,struct=struct)
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(HELPER),'exec'),namespace)
    return namespace


def chain(faces):
    result=Counter()
    for t in faces:
        for a,b in zip(t,t[1:]+t[:1]):result[tuple(sorted((a,b)))]+=1 if a<b else -1
    return {e:n for e,n in result.items() if n}


def canonical_cycles(cycles):
    if not isinstance(cycles,list) or len(cycles)!=2:
        raise ValueError('Exactly two observed cap cycles required')
    seen=set();result=[]
    for cycle in cycles:
        if (not isinstance(cycle,list) or len(cycle)<3 or any(type(v) is not int or v<0 for v in cycle)
                or len(set(cycle))!=len(cycle) or seen&set(cycle)):
            raise ValueError('Complete disjoint integer cap-cycle IDs required')
        seen.update(cycle);t=tuple(cycle);start=t.index(min(t));result.append(t[start:]+t[:start])
    return sorted(result)


def cap_cycles(faces):
    boundary=chain(faces)
    if any(abs(n)!=1 for n in boundary.values()):raise ValueError('Oriented cap rim required')
    remaining={e if n>0 else e[::-1] for e,n in boundary.items()};following=dict(remaining)
    if len(following)!=len(remaining) or Counter(b for a,b in remaining)!=Counter(following.keys()):
        raise ValueError('Disjoint directed cap rims required')
    loops=[]
    while remaining:
        a,b=min(remaining);start=a;loop=[a];remaining.remove((a,b))
        while b!=start:
            loop.append(b);a=b;b=following[a];remaining.remove((a,b))
        loops.append(loop)
    return canonical_cycles(loops)


def assess(name,directory):
    if sha(HERE/'expectations.json')!=EXPECT:raise ValueError('Frozen fixture expectations changed')
    refs=json.loads((HERE/'expectations.json').read_text());case=refs['cases'][name];m=functions()
    need=m['need'];canonical=m['canonical'];sub=m['sub'];cross=m['cross'];dot=m['dot']
    input_path=HERE/case['input_file'];targets_path=HERE/case['targets_file']
    need(sha(input_path)==case['input_sha256'] and sha(targets_path)==case['targets_sha256'],'Frozen literal input/targets changed')
    rows,p,faces=m['read'](input_path);directory=Path(directory)
    need(directory.is_dir() and not directory.is_symlink(),'Regular saved-result directory required')
    need(not any(x.is_symlink() for x in directory.iterdir()),'No saved-output symlink')
    report=json.loads((directory/'report.json').read_text())
    need(report['manufacturing_authorized'] is False and report['head_surface_or_solver_admitted'] is False,'No qualification')
    need(report['before_poor_faces']==len(case['input_observations']['poor_face_ids']),'Actual poor literal associated')
    for key,expected in [('native_poor_face_ids',case['input_observations']['poor_face_ids']),
                         ('native_reference_face_ids',case['input_observations']['incident_face_ids'])]:
        need(isinstance(report[key],list) and all(type(i) is int for i in report[key]) and report[key]==expected,'Complete exact native input-ID partition')
    need(report['input_vertices']==len(p) and report['input_faces']==len(faces) and report['target_edges']==len(case['targets']),'Native literal counts/targets associated')
    old_cycles=cap_cycles([t for t in faces if all(p[v][2]==0 for v in t)])
    need(canonical_cycles(report['original_cap_cycles'])==old_cycles,'Complete original oriented cap cycles')
    if case['expected_returncode']==3:
        need(report['mapped_cap_cycles']==[],'Rejected eligibility does not credit a mapped cap')
        need({x.name for x in directory.iterdir()}=={'report.json'} and report['exported'] is False and report['candidate_file_present'] is False,'Refusal exports absent')
        need(report['status']=='rejected_no_candidate','Declared local rejection required')
        return dict(case=name,status='checked_declared_refusal_no_exports',expected_native_returncode=3)
    need({x.name for x in directory.iterdir()}=={'report.json','candidate.bin','vertex-coordinate-origins.u64','face-source-ids.u64'},'Complete saved-output closure')
    need(report['status']=='local_candidate_only' and report['exported'] is True and report['candidate_file_present'] is True,'Local candidate only')
    need(set(report['guards'])==GUARDS and all(v is True for v in report['guards'].values()),'Every declared local guard required')
    outrows,q,outfaces=m['read'](directory/'candidate.bin')
    origins_raw=(directory/'vertex-coordinate-origins.u64').read_bytes();source_raw=(directory/'face-source-ids.u64').read_bytes()
    need(len(origins_raw)==8*len(q) and len(source_raw)==8*len(outfaces),'Complete provenance arrays')
    origins=[x[0] for x in struct.iter_unpack('<Q',origins_raw)];sources=[x[0] for x in struct.iter_unpack('<Q',source_raw)]
    need(origins==case['expected_output_origins'],'Exact complete local coordinate origins/order')
    need(outrows==[rows[v] for v in origins],'Every output coordinate byte is an input byte')
    need(len(q)==17 and len(outfaces)==34 and report['output_vertices']==17 and report['output_faces']==34,'Exact output counts')
    topology=m['topology'](q,outfaces,0);need(topology['exact_signed_volume_mm3']=='12','Exact known volume')
    members=set(case['group_members']);keeper=case['expected_keeper'];mapped=lambda t:tuple(keeper if v in members else v for v in t)
    noncap={i:canonical(mapped(t)) for i,t in enumerate(faces) if any(p[v][2]!=0 for v in t) and len(set(mapped(t)))==3}
    fixed_cap=set(case['input_observations']['fixed_cap_face_ids']);got_noncap=set();got_fixed=set();captri=[];all_keys=[]
    for t,sid in zip(outfaces,sources):
        ids=tuple(origins[v] for v in t);key=canonical(ids);all_keys.append(key)
        a,b,c=[q[v] for v in t];u=sub(b,a);v=sub(c,a);normal=cross(u,v);total=dot(u,u)+dot(v,v)+dot(sub(v,u),sub(v,u))
        need(2523*dot(normal,normal)>=total*total,'Frozen exact 2/29 quality criterion')
        if all(q[v][2]==0 for v in t):
            need(normal[2]<0,'Exact negative cap winding');captri.append([q[v][:2] for v in t])
            if sid!=MAX:
                need(sid in fixed_cap and sid not in got_fixed and key==canonical(faces[sid]),'Exact fixed-cap provenance');got_fixed.add(sid)
        else:
            need(sid in noncap and sid not in got_noncap and key==noncap[sid],'Exact noncap preimage');got_noncap.add(sid)
            old=faces[sid];oldn=cross(sub(p[old[1]],p[old[0]]),sub(p[old[2]],p[old[0]]));need(dot(oldn,normal)>0,'Retained mixed normal preimage')
    need(got_noncap==set(noncap) and got_fixed==fixed_cap,'Every noncap and fixed-cap face accounted for')
    mapped_cycles=[]
    for cycle in old_cycles:
        row=[]
        for vertex in cycle:
            value=keeper if vertex in members else vertex
            if not row or row[-1]!=value:row.append(value)
        if len(row)>1 and row[0]==row[-1]:row.pop()
        mapped_cycles.append(row)
    expected_cycles=canonical_cycles(mapped_cycles)
    need(canonical_cycles(report['mapped_cap_cycles'])==expected_cycles,'Complete mapped source cap cycles')
    output_cap=[tuple(origins[v] for v in t) for t in outfaces if all(q[v][2]==0 for v in t)]
    need(cap_cycles(output_cap)==expected_cycles,'Actual output cap cycles equal mapped source cycles')
    m['cover'](captri,[-2,-2],[2,2],F(12),hole=([-1,-1],[1,1]))
    exterior={canonical(faces[i]) for i in case['input_observations']['exterior_face_ids']}
    need(exterior<=set(all_keys),'Every exterior oriented face retained')
    need(set(case['input_observations']['exterior_fixed_vertex_ids'])<=set(origins),'Every fixed coordinate retained')
    need(chain([faces[i] for i in case['input_observations']['incident_face_ids']])==chain([tuple(origins[v] for v in t) for t in outfaces if canonical(tuple(origins[v] for v in t)) not in exterior]),'Exact oriented incident-region boundary')
    choice=report['group_choices'];need(len(choice)==1,'One synthetic group')
    choice=choice[0];need(choice['component_minimum']==min(members) and choice['members']==sorted(members) and choice['selected_keeper']==keeper,'Exact predicted unique keeper')
    score=case['native_score_six_order_bounds'][str(keeper)]
    need(math.isfinite(choice['side_star_minimum_quality']) and score['score_lower']<=choice['side_star_minimum_quality']<=score['score_upper'],'Reserved six-order native-formula score range')
    star=[i for i,t in enumerate(faces) if set(t)&members and any(p[v][2]!=0 for v in t)]
    need(choice['side_star_faces']==star and report['coupled_side_face_ids']==[],'All side-star source IDs and no coupling')
    need(report['after_poor_faces']==0 and report['global_Euler_before']==report['global_Euler_after']==0,'Reported unchanged quality/Euler gate')
    need(report['fixed_cap_face_ids']==sorted(fixed_cap) and report['fixed_cap_faces']==len(fixed_cap),'Fixed-cap report association')
    need(F(report['original_cap_exact_area'])==F(report['mapped_cap_exact_area'])==12,'Exact reported cap areas')
    return dict(case=name,status='complete_synthetic_geometry_checked_no_head_admission',expected_native_returncode=0,vertices=17,faces=34,keeper=keeper,exact_volume_mm3='12',exact_cap_area_mm2='12',fixed_cap_faces=len(fixed_cap),all_coordinate_bytes_and_face_preimages_checked=True,nonoverlapping_annulus_hole_coverage_checked=True)


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: assess.py case saved-output-directory')
    print(json.dumps(assess(sys.argv[1],Path(sys.argv[2])),indent=2,allow_nan=False))
