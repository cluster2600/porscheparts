"""One source-bound full-head byte/index assembly only; no scientific/native import."""
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[3]
MAX=(1<<64)-1

def need(value,message):
    if not value:raise ValueError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def read(path):
    raw=path.read_bytes();need(raw[:8]==b'962SURF1'and len(raw)>=24,'SURF1 codec')
    nv,nf=struct.unpack_from('<QQ',raw,8);need(0<nv<=2000000 and 0<nf<=2000000 and len(raw)==24+24*(nv+nf),'Exact bounded SURF1 byte counts')
    return raw,nv,nf
def rows(raw,nv):return struct.iter_unpack('<QQQ',memoryview(raw)[24+24*nv:])
def point(raw,i):return raw[24+24*i:48+24*i]
def ids(path):
    raw=path.read_bytes();need(len(raw)%8==0,'u64 byte count');return [v[0]for v in struct.iter_unpack('<Q',raw)]
def encoded(values):
    result=array('Q',values)
    if sys.byteorder!='little':result.byteswap()
    need(result.itemsize==8,'u64 storage');return result.tobytes()
def canonical(t):return min(t,t[1:]+t[:1],t[2:]+t[:2])

def main(contract_path,digest):
    need(sha(contract_path)==digest,'Frozen assembly contract');c=json.loads(contract_path.read_text())
    need(c['assembly_authorized']is True and c['root_and_peer_source_review_complete']is True and c['actual_cap_assessment_accepted']is True,'Separate reviewed assembly authority and accepted stopped cap assessment')
    need(sha(__file__)==c['assembler_sha256']and sha(sys.executable)==c['python_sha256'],'Source/interpreter identity')
    need(set(c['required_review_records'])=={'cap_assessment','cap_root_review','cap_result_peer'}and all(isinstance(v,dict)and v.get('path')and v.get('sha256')for v in c['required_review_records'].values()),'Completed cap assessment/root/peer bindings required')
    for record in c['required_review_records'].values():
        f=ROOT/record['path'];need(f.is_file()and not f.is_symlink()and sha(f)==record['sha256'],'Required stopped review changed')
    output=ROOT/c['expected_output'];need(output.parent==ROOT/'work/962-engineering'and not output.exists()and not output.is_symlink(),'Fresh exact task-owned assembly output')
    paths={key:ROOT/value for key,value in c['paths'].items()}
    for name,h in c['input_sha256'].items():
        f=ROOT/name;need(f.is_file()and not f.is_symlink()and sha(f)==h,'Before bound input drift')
    need(all(str(p.relative_to(ROOT))in c['input_sha256']for p in paths.values()),'Every consumed role explicitly hash-bound')
    assessment=json.loads((ROOT/c['required_review_records']['cap_assessment']['path']).read_text());need(assessment['status']=='independent_cap_bytes_Fraction_quality_topology_checked'and assessment['exact_faces_below_2_over_29']==0 and assessment['full_head_admitted']is False,'Accepted stopped independent cap assessment, not head admission')
    bindings={Path(k).resolve():v for k,v in assessment['file_sha256'].items()};need(len(bindings)==len(assessment['file_sha256']),'No assessment path aliases')
    need(all(p.resolve()in bindings and bindings[p.resolve()]==sha(p)for key,p in paths.items()if key in['original_cap','map','fixed_faces','refined_cap','cap_origins','cap_face_sources','cap_report']),'Every consumed cap input/output associated to stopped Fraction assessment')
    report=json.loads(paths['cap_report'].read_text());need(report['status']=='cap_only_local_candidate'and report['stage']=='complete'and report['exported']is True and all(v is True for v in report['guards'].values())and report['after_quality']['below_necessary_bound']==0,'Complete native cap result association only')
    head,nv,nf=read(paths['head']);oldcap,cnv,cnf=read(paths['original_cap']);cap,cv,cf=read(paths['refined_cap'])
    need((nv,nf,cnv,cnf,cv,cf)==(869355,1739126,3508,3508,5884,8976),'Frozen actual input counts')
    global_vertices=ids(paths['global_vertices']);global_faces=ids(paths['global_faces']);fixed=ids(paths['fixed_faces'])
    need(global_vertices==sorted(set(global_vertices))and len(global_vertices)==cnv and global_vertices[-1]<nv,'Complete local/global cap vertices')
    need(global_faces==sorted(set(global_faces))and len(global_faces)==cnf and global_faces[-1]<nf,'Complete local/global cap faces')
    need(fixed==sorted(set(fixed))and len(fixed)==38 and fixed[-1]<cnf,'Exact38 local fixed-cap IDs')
    oldfaces=list(rows(oldcap,cnv))
    for i,g in enumerate(global_vertices):need(point(oldcap,i)==point(head,g),'Every original cap coordinate byte association')
    for i,g in enumerate(global_faces):need(struct.pack('<QQQ',*(global_vertices[v]for v in oldfaces[i]))==head[24+24*nv+24*g:48+24*nv+24*g],'Every original ordered cap face source row')
    raw=paths['map'].read_bytes();need(len(raw)==1222*16,'Complete1222 map rows');pairs=list(struct.iter_unpack('<QQ',raw))
    need([a for a,b in pairs]==sorted({a for a,b in pairs})and all(a<cnv and b<cnv for a,b in pairs),'Sorted unique bounded local map')
    need(sum(a==b for a,b in pairs)==506 and sum(a!=b for a,b in pairs)==716,'Exact identity/nonidentity map split')
    localmap=dict(pairs);image=lambda v:localmap.get(v,v);need(all(image(image(v))==image(v)for v in range(cnv)),'Idempotent complete map')
    mapping={global_vertices[a]:global_vertices[b]for a,b in pairs};removed={a for a,b in mapping.items()if a!=b}
    side=json.loads(paths['mixed_report'].read_text());expected_map={v:g['selected_keeper']for g in side['groups_and_all_keeper_candidates']for v in g['members']}
    need(mapping==expected_map and len(side['groups_and_all_keeper_candidates'])==506,'Exact complete independently checked keeper map')
    need(side['status']=='complete_independent_choices_and_simultaneous_side_census'and side['simultaneous_side_census']['poor_faces']==0,'Accepted scoped mixed-side data association')
    origins=ids(paths['cap_origins']);cap_sources=ids(paths['cap_face_sources']);need(len(origins)==cv and len(cap_sources)==cf,'Complete cap provenance arrays')
    old_origins=[v for v in origins if v!=MAX];retained_cap={image(v)for v in range(cnv)}
    need(len(old_origins)==len(set(old_origins))and set(old_origins)==retained_cap and origins.count(MAX)==3092,'Complete retained/new cap vertex association')
    need(all(v==MAX or point(cap,i)==point(head,global_vertices[v])for i,v in enumerate(origins)),'All refined old-coordinate bytes exact d2af source')
    keep=[v for v in range(nv)if v not in removed];need(len(keep)==868639,'All original uncontracted vertices retained')
    index={v:i for i,v in enumerate(keep)};coordinates=bytearray().join(point(head,v)for v in keep);coordinate_origins=array('Q',keep);cap_to_head=[];new_cap_ids=[]
    for i,v in enumerate(origins):
        if v!=MAX:cap_to_head.append(index[global_vertices[v]])
        else:cap_to_head.append(len(coordinate_origins));coordinate_origins.append(MAX);coordinates.extend(point(cap,i));new_cap_ids.append(i)
    face_bytes=bytearray();face_sources=array('Q');old_to_new_faces=array('Q',[MAX])*nf;used=set();dropped=[];changed=[];cap_ids=set(global_faces)
    for fid,t in enumerate(rows(head,nv)):
        need(len(set(t))==3 and max(t)<nv,'Source triangle indices')
        if fid in cap_ids:continue
        mapped=tuple(mapping.get(v,v)for v in t)
        if len(set(mapped))<3:dropped.append(fid);continue
        if mapped!=t:changed.append(fid)
        row=tuple(index[v]for v in mapped);old_to_new_faces[fid]=len(face_sources);face_bytes.extend(struct.pack('<QQQ',*row));face_sources.append(fid);used.update(row)
    need(dropped==side['simultaneous_side_census']['dropped_source_face_ids']and len(dropped)==716,'Exactly716 expected noncap drops only')
    need(changed==side['simultaneous_side_census']['changed_surviving_source_face_ids'],'Every changed surviving noncap row associated')
    first_cap=len(face_sources);found=set();fixed_keys={v:canonical(oldfaces[v])for v in fixed}
    for i,t in enumerate(rows(cap,cv)):
        need(len(set(t))==3 and max(t)<cv,'Refined cap indices');sid=cap_sources[i]
        if sid!=MAX:
            need(sid in fixed_keys and sid not in found and canonical(tuple(origins[v]for v in t))==fixed_keys[sid],'Every fixed-cap source cell once');found.add(sid)
            need(all(image(v)==v for v in oldfaces[sid]),'Fixed cell vertices not contracted');old_to_new_faces[global_faces[sid]]=len(face_sources)
        row=tuple(cap_to_head[v]for v in t);need(len(set(row))==3,'Nondegenerate assembled cap index row');face_bytes.extend(struct.pack('<QQQ',*row));face_sources.append(MAX if sid==MAX else global_faces[sid]);used.update(row)
    need(found==set(fixed)and len(coordinate_origins)==871731 and len(face_sources)==1743878,'Exact derived assembled counts and38fixed cells')
    need(used==set(range(len(coordinate_origins))),'Every retained/new output vertex referenced; no arbitrary orphan removal')
    result=b'962SURF1'+struct.pack('<QQ',len(coordinate_origins),len(face_sources))+coordinates+face_bytes
    payloads={'candidate.bin':result,'vertex-coordinate-origins.u64':encoded(coordinate_origins),'face-source-ids.u64':encoded(face_sources),'old-to-new-vertices.u64':encoded(index[mapping.get(v,v)]for v in range(nv)),'old-to-new-faces.u64':encoded(old_to_new_faces),'cap-to-head-vertices.u64':encoded(cap_to_head),'cap-to-head-faces.u64':encoded(range(first_cap,first_cap+cf)),'new-point-cap-vertex-ids.u64':encoded(new_cap_ids)}
    output.mkdir()
    for name,data in payloads.items():
        with(output/name).open('xb')as stream:stream.write(data)
        need((output/name).read_bytes()==data,'Complete output byte readback')
    for name,h in c['input_sha256'].items():need(sha(ROOT/name)==h,'After bound input drift')
    for record in c['required_review_records'].values():need(sha(ROOT/record['path'])==record['sha256'],'After stopped review drift')
    need(sha(contract_path)==digest and sha(sys.executable)==c['python_sha256'],'After contract/runtime drift')
    report=dict(status='complete_byte_index_assembly_only_not_head_admission',contract_sha256=digest,assembler_sha256=sha(__file__),input_sha256=c['input_sha256'],source_vertices=nv,source_faces=nf,removed_cap_faces=cnf,removed_noncap_faces=dropped,changed_surviving_noncap_faces=changed,inserted_cap_faces=cf,retained_original_vertices=len(keep),new_cap_interior_vertices=len(new_cap_ids),output_vertices=len(coordinate_origins),output_faces=len(face_sources),fixed_cap_faces=len(found),all_outputs_read_back_byte_exact=True,coordinate_origin_basis='d2af local vertex IDs; UINT64_MAX plus new-point-cap-vertex-ids for cap interior constructions',face_origin_basis='d2af face ID for retained/mapped noncap and38fixed cap cells; UINT64_MAX for other cap triangles',all_inputs_unchanged=True,head_quality_topology_intersections_neighbors_distance_features_evaluated=False,head_surface_or_solver_admitted=False,manufacturing_authorized=False,output_sha256={name:sha(output/name)for name in payloads},output_bytes={name:len(data)for name,data in payloads.items()})
    with(output/'manifest.json').open('x')as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--contract-sha256',required=True);args=parser.parse_args();main(args.contract,args.contract_sha256)
