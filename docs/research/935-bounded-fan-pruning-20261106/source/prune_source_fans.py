"""Create a separately masked, bounded smaller-fan omission hypothesis."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k] for k in data.files}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def group_metrics(points,faces,parent_rows):
    p=points[faces];area=float(np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1).sum()/2)
    diagonal=float(np.linalg.norm(np.ptp(p.reshape(-1,3),axis=0)))
    return dict(parent_face_rows=list(map(int,parent_rows)),facets=len(faces),area_nominal_mm2=area,bounds_diagonal_nominal_mm=diagonal)


def removal_allowed(group,limits):
    return (group['facets']<=limits['max_facets_per_removed_fan'] and
            group['area_nominal_mm2']<=limits['max_area_per_removed_fan_nominal_mm2'] and
            group['bounds_diagonal_nominal_mm']<=limits['max_diagonal_nominal_mm'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();job=json.loads(args.job.read_text());started=time.monotonic()
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    base=load(job['mesh']);points,original=base['points'],base['triangles'];kept=np.arange(len(original),dtype=np.int64)
    fan_count=module(job['fan_source'],'frozen_whole_vertex_fans').vertex_fans
    local=module(job['link_source'],'frozen_contact_face_links').contact_fans
    limits=job['limits'];journal=[];stop='round_limit';initial=None
    for ordinal in range(limits['max_rounds']):
        faces=original[kept];counts,_=fan_count(faces,len(points));targets=np.flatnonzero(counts>1)
        if initial is None:initial=int(len(targets))
        if not len(targets):stop='used_vertices_manifold';break
        incident=np.flatnonzero(np.any(np.isin(faces,targets),axis=1));contacts=[];remove=set()
        for target in targets:
            rows=incident[np.any(faces[incident]==target,axis=1)];groups=local(faces[rows],int(target));assert len(groups)==counts[target]
            metrics=[group_metrics(points,faces[rows[x['local_face_rows']]],kept[rows[x['local_face_rows']]]) for x in groups]
            largest=min(range(len(metrics)),key=lambda i:(-metrics[i]['area_nominal_mm2'],metrics[i]['parent_face_rows'][0]))
            allowed=all(removal_allowed(x,limits) for i,x in enumerate(metrics) if i!=largest)
            if allowed:
                for i,x in enumerate(metrics):
                    if i!=largest:remove.update(x['parent_face_rows'])
            contacts.append(dict(contact_vertex=int(target),groups=metrics,retained_group=largest,removal_admitted=allowed))
        previously_removed=len(original)-len(kept)
        assert remove.issubset(set(map(int,kept)))
        permitted=previously_removed+len(remove)<=limits['max_total_removed_facets']
        journal.append(dict(round=ordinal,current_face_count=len(kept),nonmanifold_contacts=len(targets),private_contacts=contacts,
                            requested_parent_face_rows=sorted(remove),total_removal_limit_passed=permitted))
        if not remove or not permitted:stop='no_further_bounded_omission';break
        kept=kept[~np.isin(kept,np.array(sorted(remove),dtype=np.int64))]
    final,_=fan_count(original[kept],len(points));converged=not np.any(final>1)
    if converged:stop='used_vertices_manifold'
    removed=np.setdiff1d(np.arange(len(original),dtype=np.int64),kept,assume_unique=True)
    result={}
    for key,value in base.items():
        if key in ('points','global_node_ids'):result[key]=value
        elif key=='triangles' or (value.ndim==1 and len(value)==len(original)):result[key]=value[kept]
        else:raise AssertionError('Unsupported parent provenance field: '+key)
    result['parent_face_rows']=kept
    args.output.mkdir(mode=0o700,exist_ok=False)
    np.savez_compressed(args.output/'candidate.npz',**result)
    np.savez_compressed(args.output/'private-omission-mask.npz',retained_parent_face_rows=kept,removed_parent_face_rows=removed,
                        omitted_source_face_ids=base['original_face_ids'][removed],omitted_source_fragment_indices=base['source_fragment_indices'][removed],
                        omitted_surface_kinds=base['inferred_surface_kind'][removed])
    (args.output/'private-round-journal.json').write_text(json.dumps(journal,indent=2)+'\n')
    with (args.output/'candidate.obj').open('w') as stream:
        stream.write('# SOURCE-OMISSION STUDY; explicit private mask; project mm; NOT PRINT READY\n')
        for point in points:stream.write('v '+' '.join(format(float(x),'.17g') for x in point)+'\n')
        for face in result['triangles']:stream.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')
    for row in job['inputs']:assert sha(row['path'])==row['sha256']
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),parent_mesh_sha256=sha(job['mesh']),
                candidate_NPZ_sha256=sha(args.output/'candidate.npz'),candidate_OBJ_sha256=sha(args.output/'candidate.obj'),
                initial_nonmanifold_used_vertices=initial,final_nonmanifold_used_vertices=int(np.count_nonzero(final>1)),
                parent_triangles=len(original),retained_triangles=len(kept),removed_triangles=len(removed),rounds=len(journal),stop_reason=stop,
                convergence_reached=converged,coordinates_changed=False,index_duplicates_created=False,
                omissions_are_hypotheses_not_proven_scan_damage=True,full_bare_head_created=False,
                physical_acceptance=False,manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
