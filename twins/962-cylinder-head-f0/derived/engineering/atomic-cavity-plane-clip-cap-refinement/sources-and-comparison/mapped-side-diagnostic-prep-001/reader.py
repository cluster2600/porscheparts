"""Read selected source preimages under saved keepers; no quotient/CDT export or native replay."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time
from collections import Counter
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[3]

def need(ok, text):
    if not ok: raise ValueError(text)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()

def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b): return sum(x*y for x,y in zip(a,b))

def measure(points, original, mapped):
    if len(set(mapped))<3:return None
    p=[points[v] for v in mapped];old=[points[v] for v in original]
    n=cross(sub(p[1],p[0]),sub(p[2],p[0]));o=cross(sub(old[1],old[0]),sub(old[2],old[0]))
    total=sum(dot(sub(p[i],p[(i+1)%3]),sub(p[i],p[(i+1)%3])) for i in range(3))
    need(total>0,'Distinct mapped IDs have coincident coordinates')
    q2=12*dot(n,n)/(total*total);normal_dot=dot(o,n)
    return q2,normal_dot

def selected_rows(path, ids, expected_vertices, expected_faces):
    need(ids==sorted(set(ids)) and all(type(i) is int and 0<=i<expected_faces for i in ids),'Selected face IDs')
    with Path(path).open('rb') as stream:
        header=stream.read(24);need(len(header)==24 and header[:8]==b'962SURF1','962SURF1 header')
        nv,nf=struct.unpack('<QQ',header[8:]);need((nv,nf)==(expected_vertices,expected_faces),'Bound source counts')
        need(Path(path).stat().st_size==24+24*(nv+nf),'Exact source byte length')
        faces={}
        for fid in ids:
            stream.seek(24+24*nv+24*fid);row=struct.unpack('<QQQ',stream.read(24))
            need(len(set(row))==3 and max(row)<nv,'Source face indices');faces[fid]=row
        vertices=sorted({v for row in faces.values() for v in row});points={};raw={}
        for vid in vertices:
            stream.seek(24+24*vid);bits=stream.read(24);xyz=struct.unpack('<ddd',bits)
            need(all(math.isfinite(v) for v in xyz),'Finite selected coordinate')
            raw[vid]=bits;points[vid]=tuple(F(v) for v in xyz)
    need(len(set(raw.values()))==len(raw),'Unique selected source coordinates')
    return faces,points,raw

def rational(value):return {'numerator':str(value.numerator),'denominator':str(value.denominator)}

def main(contract_path, output_path):
    begin=time.monotonic();contract_path=Path(contract_path);output=Path(output_path);c=json.loads(contract_path.read_text())
    need(c.get('diagnostic_launch_authorized') is True and c.get('root_and_peer_review_complete') is True,'Separate reviewed diagnostic launch required')
    need(output.resolve()==(ROOT/c['expected_output']).resolve() and not output.exists() and not output.is_symlink(),'Fresh exact report path required')
    need(sha(__file__)==c['reader_sha256'] and sha(sys.executable)==c['runtime']['python_executable_sha256'],'Reader/interpreter identity')
    pins=c['input_sha256']
    for name,digest in pins.items():need(sha(ROOT/name)==digest,'Before input drift: '+name)
    native=json.loads((ROOT/c['native_report']).read_text());retained=json.loads((ROOT/c['frozen_readback']).read_text());boundary=json.loads((ROOT/c['boundary_reference']).read_text())
    need(native['status']=='rejected_no_candidate' and native['stage']=='combined_full_quality_and_topology' and not native['exported'],'Stopped rejected native report')
    need(native['input_vertices']==869355 and native['input_faces']==1739126 and native['after_poor_faces']==1122,'Bound native case')
    ids=native['native_reference_face_ids'];need(len(ids)==9872,'Complete incident region count')
    mask=bytearray(1739126)
    for i in ids:
        need(type(i) is int and 0<=i<len(mask),'Typed incident ID');mask[i]=1
    need(hashlib.sha256(mask).hexdigest()==retained['candidate']['exact_incident_patch_mask_sha256'],'Exact frozen incident mask')
    faces,points,raw=selected_rows(ROOT/c['source_geometry'],ids,869355,1739126);need(len(points)==5938,'Selected incident vertices')
    poor=native['native_poor_face_ids'];classes=retained['candidate']['plane_classes']
    frozen_poor=sorted(v for row in classes.values() for v in row['poor_face_ids'])
    need(poor==frozen_poor and len(poor)==3112 and all(v in faces for v in poor),'Frozen complete source poor IDs')
    groups={g['component_minimum']:g['member_ids'] for g in boundary['groups']};choices=native['group_choices']
    need(len(groups)==len(choices)==510 and len({g['component_minimum'] for g in choices})==510,'All observed groups')
    mapping={};owner={};seed={v for fid in poor for v in faces[fid]}
    for g in choices:
        members=g['members'];keeper=g['selected_keeper'];key=g['component_minimum']
        need(members==groups[key] and type(keeper) is int and keeper in members,'Observed keeper/member association')
        for v in members:
            need(v in seed and v in points and points[v][2]==0 and v not in mapping,'Unique cap/seed member')
            mapping[v]=keeper;owner[v]=key
    side={i:t for i,t in faces.items() if not all(points[v][2]==0 for v in t)}
    for g in choices:
        need(g['side_star_faces']==[i for i,t in side.items() if any(owner.get(v)==g['component_minimum'] for v in t)],'Complete saved side star')
    coupled=[i for i,t in side.items() if len({owner[v] for v in t if v in owner})>1]
    need(coupled==native['coupled_side_face_ids'],'Complete coupled side-face IDs')
    dropped=[];bad=[];original_bad=[];changed=[];signs=Counter();bad_signs=Counter();by_class=Counter();minimum=None;worst_normal=None
    for fid,row in side.items():
        old_q2,_=measure(points,row,row)
        if old_q2<F(4,841):original_bad.append(fid)
        mapped=tuple(mapping.get(v,v) for v in row);metrics=measure(points,row,mapped)
        if metrics is None:dropped.append(fid);continue
        need(any(points[v][2]!=0 for v in mapped),'Noncap preimage became cap')
        q2,normal_dot=metrics;sign=(normal_dot>0)-(normal_dot<0);signs[str(sign)]+=1
        if mapped!=row:changed.append(fid)
        if minimum is None or (q2,fid)<minimum:minimum=q2,fid
        if worst_normal is None or (normal_dot,fid)<worst_normal:worst_normal=normal_dot,fid
        if q2<F(4,841):
            bad.append(fid);bad_signs[str(sign)]+=1;by_class['mixed_z0' if any(points[v][2]==0 for v in row) else 'off_plane']+=1
    need(len(dropped)==native['side_dropped_faces'],'Exact observed dropped side preimages')
    reference_noncap=set(classes['noncap_mixed_plane_vertices']['poor_face_ids'])|set(classes['noncap_no_plane_vertices']['poor_face_ids'])
    need(reference_noncap<=set(side),'All frozen original noncap poor faces covered')
    worst=None
    if minimum:
        q2,fid=minimum;row=faces[fid];mapped=tuple(mapping.get(v,v) for v in row)
        worst={'source_face_id':fid,'original_source_vertex_ids':row,'mapped_source_vertex_ids':mapped,'exact_quality_squared':rational(q2),'approximate_quality_not_native_float':math.sqrt(float(q2)),'original_point_binary64_hex':[raw[v].hex() for v in row],'mapped_point_binary64_hex':[raw[v].hex() for v in mapped]}
    for name,digest in pins.items():need(sha(ROOT/name)==digest,'After input drift: '+name)
    result={'schema':'962-saved-map-selected-noncap-diagnostic/v1','status':'completed_read_only_exact_dyadic_side_preimage_census','source_geometry_sha256':pins[c['source_geometry']],'native_report_sha256':pins[c['native_report']],'contract_sha256':sha(contract_path),'reader_sha256':sha(__file__),
      'method':'Streamed source hash; only the9872 incident face rows and their5938 point rows decoded. Saved510 keepers used once; no keeper selection, CDT, geometry export, native or scientific import.',
      'selected_source_faces':len(faces),'selected_source_vertices':len(points),'noncap_source_faces':len(side),'surviving_noncap_faces':len(side)-len(dropped),'dropped_source_face_ids':dropped,'changed_surviving_source_face_ids':changed,
      'poor_source_face_ids_exact':bad,'poor_count_exact':len(bad),'poor_plane_class_counts':dict(by_class),'original_poor_noncap_source_face_ids_exact':original_bad,'original_exact_vs_frozen_NumPy_poor_symmetric_difference':sorted(set(original_bad)^reference_noncap),
      'remaining_previously_poor_source_face_ids_exact':sorted(set(bad)&set(original_bad)),'newly_poor_source_face_ids_exact':sorted(set(bad)-set(original_bad)),
      'all_surviving_original_dot_mapped_normal_sign_counts':dict(signs),'poor_original_dot_mapped_normal_sign_counts':dict(bad_signs),'worst_quality_record':worst,'minimum_original_dot_mapped_normal':{'exact_value':rational(worst_normal[0]),'source_face_id':worst_normal[1]} if worst_normal else None,
      'native_global_poor_count_retained':native['after_poor_faces'],'native_global_minimum_retained':native['after_minimum_quality'],'native_cap_poor_count_inferred':False,'exact_dyadic_metrics_are_not_native_floating_point_replay':True,
      'fixed_chosen_map_cap_only_changes_cannot_remove_these_noncap_failures':bool(bad),'alternative_keeper_or_general_repair_infeasibility_claimed':False,
      'exterior_goodness_basis':'Attributed to frozen209a complete-array readback; exterior triangles were not decoded or reclassified by this reader.','global_topology_distance_features_or_candidate_admission':False,'head_PDE_material_LPBF_or_manufacturing_qualified':False,'geometry_files_written':False,'all_bound_inputs_unchanged':True,'wall_seconds':time.monotonic()-begin}
    with output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')

if __name__=='__main__':
    need(len(sys.argv)==3,'reader.py frozen-contract.json fresh-report.json')
    main(sys.argv[1],sys.argv[2])
