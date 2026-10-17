"""Stopped cap-only byte/Fraction assessor; no native calls or extractor import."""
import ast
from collections import Counter,defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[3]
HELPERS={
 'work/962-engineering/atomic-cavity-plane-clip-assessment-prep-001/assess_clip.py':('5194356616d0eb2f44b8fd72180364248acf268d8d7ea9b5cfd577367084dacc',{'need','canonical','sub','cross','dot','read','connected'}),
 'work/962-engineering/cap-aware-repair-fixtures-prep-001/assess_003.py':('5df03915cf8b1cbfb89c5e58b547e3a8e834795a28d6a868d011a9066fe715c5',{'chain','canonical_cycles','cap_cycles'})}
MAX=(1<<64)-1
GUARDS=['original_cap_and_fixed_map_association','mapped_simple_two_loop_annulus',
 'explicit_annulus_minus_fixed_marks_and_exact_constraints','no_constrained_edge_split_or_fixed_cell_drift',
 'rounded_embedding_domain_topology_and_quality']
STAGES=['original_annular_cap','mapped_annulus','fixed_cell_CDT','interior_no_edge_refinement','rounded_embedding','complete']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def functions():
    ns=dict(Counter=Counter,defaultdict=defaultdict,F=F,Path=Path,math=math,struct=struct)
    for name,(digest,names)in HELPERS.items():
        path=ROOT/name
        if sha(path)!=digest:raise ValueError('Frozen pure helper drift')
        nodes=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)and n.name in names]
        if len(nodes)!=len(names):raise ValueError('Complete selected pure helper definitions required')
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    return ns

def planar(faces,nv,m):
    need=m['need'];edges=defaultdict(list);links=defaultdict(list);graph=defaultdict(set)
    for t in faces:
        for a,b,c in zip(t,t[1:]+t[:1],t[2:]+t[:2]):
            edges[tuple(sorted((a,b)))].append(1 if a<b else-1);links[a].append(tuple(sorted((b,c))))
            graph[a].add(b);graph[b].add(a)
    need(m['connected'](graph)==1 and nv-len(edges)+len(faces)==0,'One component/Euler0 required')
    boundary={e:v[0]for e,v in edges.items()if len(v)==1}
    need(all(len(v)==1 or len(v)==2 and sum(v)==0 for v in edges.values()),'Full oriented edge incidence')
    boundary_vertices={v for e in boundary for v in e}
    for vertex,pairs in links.items():
        need(len(pairs)==len(set(pairs)),'Duplicate vertex-link edge');link=defaultdict(set)
        for a,b in pairs:link[a].add(b);link[b].add(a)
        ends=sum(len(v)==1 for v in link.values())
        need(m['connected'](link)==1 and all(len(v)in(1,2)for v in link.values())and ends==(2 if vertex in boundary_vertices else 0),'Complete path/cycle vertex link')
    cycles=m['cap_cycles'](faces)
    return boundary,cycles,{'vertices':nv,'faces':len(faces),'edges':len(edges),'components':1,'Euler':0,'boundary_cycles':2}

def exact_faces(points,faces,need,require_quality):
    area=F(0);minimum=None;poor=0
    for t in faces:
        a,b,c=[points[v]for v in t];need(a[2]==b[2]==c[2]==0,'Exact plane z0')
        det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);need(det<0,'Exact negative-Z winding')
        total=sum(sum((x[k]-y[k])**2 for k in(0,1))for x,y in[(a,b),(b,c),(c,a)])
        q2=12*det*det/(total*total);poor+=2523*det*det<total*total
        minimum=q2 if minimum is None else min(minimum,q2);area-=det/2
    need(not require_quality or poor==0,'Exact stored-coordinate quality below2/29')
    return area,minimum,poor

def assess(cap_path,map_path,fixed_path,directory,returncode,expected_sha256):
    m=functions();need=m['need'];cap_path,map_path,fixed_path,directory=map(Path,[cap_path,map_path,fixed_path,directory])
    need(type(returncode)is int and returncode in(0,3),'Actual external RC0 or RC3 required')
    need(directory.is_dir()and not directory.is_symlink()and not any(x.is_symlink()for x in directory.iterdir()),'Regular stopped result required')
    files={'report.json'}if returncode==3 else{'report.json','cap-candidate.bin','vertex-coordinate-origins.u64','face-source-ids.u64'}
    need({x.name for x in directory.iterdir()}==files,'Complete stopped output closure')
    consumed=[cap_path,map_path,fixed_path]+[directory/n for n in sorted(files)]
    need(all(p.is_file()and not p.is_symlink()for p in consumed),'Regular consumed files required')
    before={str(p):sha(p)for p in consumed}
    need(all(k in expected_sha256 and expected_sha256[k]==v for k,v in before.items()),'Every consumed input/output must match external frozen hashes')
    r=json.loads((directory/'report.json').read_text(),parse_constant=lambda x:(_ for _ in()).throw(ValueError('Nonfinite JSON')))
    def finite(value):return all(finite(v)for v in value.values())if isinstance(value,dict)else all(finite(v)for v in value)if isinstance(value,list)else not isinstance(value,float)or math.isfinite(value)
    need(finite(r),'Finite complete JSON report')
    rows,p,faces=m['read'](cap_path);old_area,old_q2,old_poor=exact_faces(p,faces,need,False)
    _,old_cycles,_=planar(faces,len(p),m)
    need({v for loop in old_cycles for v in loop}==set(range(len(p))),'Original cap vertices all boundary IDs')
    need(r['input_vertices']==len(p)and r['input_faces']==len(faces),'Reported input counts')
    need(r['head_surface_or_solver_admitted']is False and r['manufacturing_authorized']is False,'No full-head/physical admission')
    need(r['interior_Steiner_hypothesis']is True and r['policy_old_coordinate_bits_required']is True and r['original_vs_mapped_domain_equality_claimed']is False and r['new_point_and_nonfixed_face_provenance_sentinel']==MAX and r['no_insertion_causes_separately_instrumented']is False,'Scoped provenance/native attribution policy')
    for key in ['map_rows','identity_map_rows','nonidentity_map_rows','fixed_faces','constrained_edges','refinement_attempts','requests_with_one_insertion','requests_without_insertion','active_shape_bad_before','active_shape_bad_after','output_vertices','output_faces','new_interior_points','final_exact_faces_below_2_over_29']:
        need(type(r[key])is int and r[key]>=0,'Nonnegative integer report counter '+key)
    for quality in[r['before_quality'],r['after_quality']]:
        need(all(type(quality[k])is int and quality[k]>=0 for k in['triangles','below_necessary_bound'])and quality['below_necessary_bound']<=quality['triangles']and type(quality['minimum_triangle_SICN'])in(int,float)and math.isfinite(quality['minimum_triangle_SICN']),'Typed finite native quality observations')
    need(type(r['CGAL_CDT_active_shape_criteria_satisfied'])is bool,'Typed native active-shape observation')
    need(r['stage']in STAGES,'Known completed/refusal stage')
    stage=STAGES.index(r['stage']);needed=GUARDS if returncode==0 else GUARDS[:min(stage,4)]
    need(set(r['guards'])==set(needed)and all(x is True for x in r['guards'].values()),'Stage-aware observed guard prefix')
    if returncode==3:
        need(r['status']=='rejected_no_candidate'and r['stage']!='complete'and r['exported']is False and r['candidate_file_present']is False,'Report-only refusal')
        need(r['CGAL_CDT_active_shape_criteria_satisfied']is False,'No credited final shape success on refusal')
        need({str(p):sha(p)for p in consumed}==before,'After consumed-file drift')
        return {'status':'checked_report_only_refusal','native_stage':r['stage'],'native_reason':r['reason'],'later_guards_and_initialized_zero_counters_unobserved':True,'full_head_admitted':False,'file_sha256':before}
    need(r['status']=='cap_only_local_candidate'and r['stage']=='complete'and r['exported']is True and r['candidate_file_present']is True,'Completed cap-only native result required')
    raw=map_path.read_bytes();need(len(raw)%16==0,'Map row bytes');pairs=list(struct.iter_unpack('<QQ',raw))
    need([a for a,b in pairs]==sorted({a for a,b in pairs})and all(a<len(p)and b<len(p)for a,b in pairs),'Sorted unique bounded map sources')
    mapping=dict(pairs);image=lambda v:mapping.get(v,v)
    need(all(image(image(v))==image(v)for v in range(len(p))),'Final idempotent map')
    loop_of={v:k for k,loop in enumerate(old_cycles)for v in loop};need(all(loop_of[a]==loop_of[b]for a,b in pairs),'Map remains within each original loop')
    def ids(path):
        data=path.read_bytes();need(len(data)%8==0,'u64 provenance bytes');return [t[0]for t in struct.iter_unpack('<Q',data)]
    fixed=ids(fixed_path);need(fixed==sorted(set(fixed))and all(x<len(faces)for x in fixed),'Sorted associated fixed face IDs')
    need(all(image(v)==v for i in fixed for v in faces[i]),'Fixed-cell input vertices preserved')
    mapped=[]
    for loop in old_cycles:
        q=[]
        for v in loop:
            if not q or q[-1]!=image(v):q.append(image(v))
        if len(q)>1 and q[0]==q[-1]:q.pop()
        mapped.append(q)
    mapped=m['canonical_cycles'](mapped);retained={v for loop in mapped for v in loop}
    need(m['canonical_cycles'](r['original_cap_cycles'])==old_cycles and m['canonical_cycles'](r['mapped_cap_cycles'])==mapped,'Complete reported original/mapped oriented cycles')
    outrows,q,outfaces=m['read'](directory/'cap-candidate.bin');origins=ids(directory/'vertex-coordinate-origins.u64');sources=ids(directory/'face-source-ids.u64')
    need(len(origins)==len(q)and len(sources)==len(outfaces),'Complete provenance counts')
    old=[v for v in origins if v!=MAX];need(len(old)==len(set(old))and set(old)==retained,'Every retained original ID once and all new IDs sentinel')
    need(all(v==MAX or outrows[i]==rows[v]for i,v in enumerate(origins)),'Every old coordinate row exact original bits')
    boundary,_,topology=planar(outfaces,len(q),m);observed=set()
    for (a,b),sign in boundary.items():
        if sign<0:a,b=b,a
        need(origins[a]!=MAX and origins[b]!=MAX,'No new boundary point');observed.add((origins[a],origins[b]))
    expected={(loop[i],loop[(i+1)%len(loop)])for loop in mapped for i in range(len(loop))}
    need(observed==expected,'Every mapped boundary segment and direction exact')
    frozen={m['canonical'](faces[i]):i for i in fixed};found=set()
    for t,sid in zip(outfaces,sources):
        key=m['canonical'](tuple(origins[v]for v in t))
        if key in frozen:need(sid==frozen[key],'Fixed cell cannot be relabelled new')
        if sid!=MAX:need(sid in fixed and sid not in found and key==m['canonical'](faces[sid]),'Exact fixed-cell face ID/provenance');found.add(sid)
    need(found==set(fixed),'All fixed cells retained once')
    area,min_q2,poor=exact_faces(q,outfaces,need,True)
    mapped_area=-sum(sum(p[a][0]*p[b][1]-p[a][1]*p[b][0]for a,b in zip(loop,loop[1:]+loop[:1]))for loop in mapped)/2
    need(area==mapped_area==F(r['mapped_cap_area'])==F(r['embedded_cap_area'])and old_area==F(r['original_cap_area']),'Exact original/mapped/embedded areas')
    need((r['output_vertices'],r['output_faces'],r['new_interior_points'])==(len(q),len(outfaces),origins.count(MAX)),'Binary/report output counts')
    need((r['map_rows'],r['identity_map_rows'],r['nonidentity_map_rows'],r['fixed_faces'])==(len(pairs),sum(a==b for a,b in pairs),sum(a!=b for a,b in pairs),len(fixed)),'Map/fixed report counters')
    constraints={tuple(sorted(e))for e in expected}|{tuple(sorted((t[j],t[(j+1)%3])))for t in[faces[i]for i in fixed]for j in range(3)};need(r['constrained_edges']==len(constraints),'Complete exact constrained-edge count')
    need(r['refinement_attempts']==r['requests_with_one_insertion']+r['requests_without_insertion']and r['requests_with_one_insertion']==origins.count(MAX),'Complete refinement request/insertion accounting')
    need(r['final_exact_faces_below_2_over_29']==poor==r['after_quality']['below_necessary_bound']==0 and r['after_quality']['triangles']==len(outfaces)and r['before_quality']['triangles']==len(faces),'Quality/report face counts')
    need(math.isfinite(r['after_quality']['minimum_triangle_SICN'])and r['after_quality']['minimum_triangle_SICN']>=2/29,'Finite reported native minimum, separately attributed')
    need(r['shape_aspect_bound']==0.125 and r['size_bound']==0 and r['CGAL_CDT_active_shape_criteria_satisfied']==(r['active_shape_bad_after']==0),'Default native shape criterion attribution')
    need({str(p):sha(p)for p in consumed}==before,'After consumed-file drift')
    return {'status':'independent_cap_bytes_Fraction_quality_topology_checked','topology':topology,'retained_old_points':len(old),'new_interior_points':origins.count(MAX),'fixed_faces':len(fixed),'exact_cap_area_mm2':str(area),'exact_minimum_triangle_quality_squared':str(min_q2),'exact_faces_below_2_over_29':poor,'native_minimum_triangle_SICN_observation':r['after_quality']['minimum_triangle_SICN'],'native_self_intersection_domain_and_no_edge_refinement_observations_not_independently_replayed':True,'no_independent_polygon_coverage_or_self_intersection_algorithm':True,'full_head_admitted':False,'file_sha256':before}

if __name__=='__main__':
    if len(sys.argv)!=8:raise SystemExit('Usage: assess.py cap.bin map.u64 fixed.u64 stopped-output RC bindings.json bindings-sha256')
    if sha(sys.argv[6])!=sys.argv[7]:raise SystemExit('Frozen external bindings required')
    print(json.dumps(assess(*sys.argv[1:5],int(sys.argv[5]),json.loads(Path(sys.argv[6]).read_text())),indent=2,allow_nan=False))
