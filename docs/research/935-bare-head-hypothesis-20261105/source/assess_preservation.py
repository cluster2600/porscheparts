#!/usr/bin/env python3
"""Audit the retained parent surface and disclose whole-scan and cut-region distances."""
import argparse
import json
from pathlib import Path

import igl
import numpy as np
from prepare_aligned import sha


def records(a):
    a=np.ascontiguousarray(a)
    return a.view(np.dtype([(str(i),a.dtype) for i in range(3)])).reshape(-1)


def canonical(f):
    start=f.argmin(axis=1)
    return np.take_along_axis(f,(start[:,None]+np.arange(3))%3,axis=1)


def sample(v,f,n,seed):
    area=np.empty(len(f))
    for start in range(0,len(f),100000):
        q=v[f[start:start+100000]]
        area[start:start+len(q)]=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)/2
    rng=np.random.default_rng(seed)
    ids=rng.choice(len(f),size=n,p=area/area.sum())
    u=np.sqrt(rng.random(n));w=rng.random(n)
    bary=np.column_stack((1-u,u*(1-w),u*w))
    return (v[f[ids]]*bary[:,:,None]).sum(axis=1),ids,area


def stats(distance):
    return {"samples":len(distance),"p50_mm":float(np.quantile(distance,.5)),
            "p95_mm":float(np.quantile(distance,.95)),"p99_mm":float(np.quantile(distance,.99)),
            "max_mm":float(distance.max())}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("parent","candidate","scan","planes","tags","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    with np.load(a.parent,allow_pickle=False) as data:
        old_v,old_f=data["vertices"],data["triangles"]
    with np.load(a.candidate,allow_pickle=False) as data:
        v,f=data["vertices"],data["triangles"]
    tags=np.load(a.tags,allow_pickle=False)
    planes=np.array([x["keep_negative_halfspace_coefficients"] for x in json.loads(a.planes.read_text())])
    old_records=records(old_v);order=np.argsort(old_records)
    ordered=old_records[order]
    assert not np.any(ordered[1:]==ordered[:-1]),"Ambiguous parent coordinate identity"
    selected=np.searchsorted(ordered,records(v))
    valid=selected<len(order)
    selected=np.minimum(selected,len(order)-1)
    valid &= ordered[selected]==records(v)
    vertex_ids=np.where(valid,order[selected],-1)
    mapped=vertex_ids[f]
    intact=np.all(mapped>=0,axis=1)
    old_keys=records(canonical(old_f));face_order=np.argsort(old_keys);ordered_faces=old_keys[face_order]
    query=records(canonical(mapped[intact]))
    index=np.searchsorted(ordered_faces,query)
    assert np.all(index<len(ordered_faces)) and np.all(ordered_faces[index]==query),"Retained face differs from oriented parent triangle"
    unchanged_ids=face_order[index]
    fully_inside=[];crossing=[]
    for start in range(0,len(old_f),100000):
        xyz=old_v[old_f[start:start+100000]]
        distance=xyz@planes[:,:3].T+planes[:,3]
        kept=np.all(distance<=0,axis=(1,2))
        fully_inside.extend((np.flatnonzero(kept)+start).tolist())
        crosses=np.any((distance.min(axis=1)<=0)&(distance.max(axis=1)>=0),axis=1)
        crossing.extend((np.flatnonzero(crosses)+start).tolist())
    assert np.array_equal(np.sort(unchanged_ids),np.asarray(fully_inside)),"Fully retained original parent triangles not preserved"
    partial=np.flatnonzero((tags==0)&~intact)
    q=v[f[partial]]
    cross_f=old_f[np.asarray(crossing)]
    _,nearest,_=igl.point_mesh_squared_distance(q.mean(axis=1),old_v,cross_f)
    original=old_v[cross_f[nearest]]
    e0,e1=original[:,1]-original[:,0],original[:,2]-original[:,0]
    # Dominant-axis determinants avoid squaring the conditioning of thin facets.
    axes=np.array([[1,2],[2,0],[0,1]])[np.abs(np.cross(e0,e1)).argmax(axis=1)]
    x=np.take_along_axis(e0,axes,axis=1)
    y=np.take_along_axis(e1,axes,axis=1)
    delta=np.take_along_axis(q-original[:,0,None,:],axes[:,None,:],axis=2)
    denominator=x[:,0]*y[:,1]-x[:,1]*y[:,0]
    assert np.all(denominator!=0)
    u=(delta[:,:,0]*y[:,None,1]-delta[:,:,1]*y[:,None,0])/denominator[:,None]
    w=(x[:,None,0]*delta[:,:,1]-x[:,None,1]*delta[:,:,0])/denominator[:,None]
    bary=np.stack((1-u-w,u,w),axis=2)
    positive=np.maximum(bary,0);positive/=positive.sum(axis=2)[:,:,None]
    points=np.einsum("nki,nij->nkj",positive,original)
    maximum=float(np.linalg.norm(q-points,axis=2).max()) if len(partial) else 0.
    assert maximum<1e-8,"Changed skin not bounded inside its original parent triangle"
    np.savez_compressed(a.output/"private-parent-face-provenance.npz",candidate_vertex_parent_ids=vertex_ids,
                        unchanged_parent_face_ids=unchanged_ids,partial_candidate_faces=partial,
                        partial_parent_faces=np.asarray(crossing)[nearest])
    with np.load(a.scan,allow_pickle=False) as data:
        scan_v,scan_f=data["vertices"],data["triangles"]
    points,source_ids,_=sample(scan_v,scan_f,100000,935051)
    squared,_,_=igl.point_mesh_squared_distance(points,v,f)
    distances=np.sqrt(np.maximum(squared,0))
    inside=np.all(points@planes[:,:3].T+planes[:,3]<=0,axis=1)
    reverse,reverse_ids,area=sample(v,f,100000,935052)
    squared,_,_=igl.point_mesh_squared_distance(reverse,scan_v,scan_f)
    np.savez_compressed(a.output/"private-distance-samples.npz",scan_face_ids=source_ids,scan_distances=distances,
                        inside_construction_halfspaces=inside,candidate_face_ids=reverse_ids,
                        candidate_distances=np.sqrt(np.maximum(squared,0)))
    report={"source_sha256":sha(Path(__file__)),"parent_sha256":sha(a.parent),"candidate_sha256":sha(a.candidate),
            "scan_arrays_sha256":sha(a.scan),"intact_parent_faces_preserved_with_identical_coordinates_and_orientation":int(intact.sum()),
            "all_fully_kept_parent_faces_preserved":True,"partially_clipped_parent_surface_triangles":len(partial),
            "partial_skin_whole_triangle_containment_upper_bound_mm":maximum,
            "assumed_cap_faces":[int((tags==i).sum()) for i in (1,2,3)],
            "assumed_cap_area_mm2":[float(area[tags==i].sum()) for i in (1,2,3)],
            "scan_to_candidate_all":stats(distances),"scan_to_candidate_inside_construction_halfspaces":stats(distances[inside]),
            "scan_to_candidate_outside_construction_halfspaces":stats(distances[~inside]),
            "candidate_to_scan_all":stats(np.sqrt(np.maximum(squared,0))),
            "sampling_is_not_global_error_bound_or_specimen_metrology":True,
            "construction_halfspaces_are_not_accepted_anatomical_labels":True,"manufacturing_qualified":False}
    (a.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


if __name__=="__main__":
    main()
