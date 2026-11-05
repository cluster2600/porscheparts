#!/usr/bin/env python3
"""Select local protrusions from independent one-plane constructions; retain fins.

One plane must not truncate the root of a feature cut by another plane. Each
local fragment is therefore derived independently from the unmodified parent.
"""
import argparse
import json
from pathlib import Path

import igl
import numpy as np
from assess_preservation import records, canonical
from localize_cuts import components
from prepare_aligned import sha


def check_partial(q, original):
    e0,e1=original[:,1]-original[:,0],original[:,2]-original[:,0]
    axes=np.array([[1,2],[2,0],[0,1]])[np.abs(np.cross(e0,e1)).argmax(axis=1)]
    x=np.take_along_axis(e0,axes,axis=1);y=np.take_along_axis(e1,axes,axis=1)
    delta=np.take_along_axis(q-original[:,0,None,:],axes[:,None,:],axis=2)
    den=x[:,0]*y[:,1]-x[:,1]*y[:,0]
    assert np.all(den!=0)
    u=(delta[:,:,0]*y[:,None,1]-delta[:,:,1]*y[:,None,0])/den[:,None]
    w=(x[:,None,0]*delta[:,:,1]-x[:,None,1]*delta[:,:,0])/den[:,None]
    bary=np.maximum(np.stack((1-u-w,u,w),axis=2),0)
    bary/=bary.sum(axis=2)[:,:,None]
    interior=np.einsum("nki,nij->nkj",bary,original)
    return float(np.linalg.norm(q-interior,axis=2).max()) if len(q) else 0.


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("parent","cases","planes","plan","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    with np.load(a.parent,allow_pickle=False) as data:ov,of=data["vertices"],data["triangles"]
    plan=json.loads(a.plan.read_text());rule=plan["selection_hypothesis"]
    planes=json.loads(a.planes.read_text())
    vertex_order=np.argsort(records(ov));vertex_keys=records(ov)[vertex_order]
    assert not np.any(vertex_keys[1:]==vertex_keys[:-1])
    face_keys=records(canonical(of));face_order=np.argsort(face_keys);face_keys=face_keys[face_order]
    removed=np.zeros(len(of),bool);extra_vertices=[];extra_count=0
    fragments=[];fragment_parent=[];fragment_tags=[];all_rows=[];case_checks=[]
    for plane_index,row in enumerate(planes):
        case=a.cases/str(plane_index)/"candidate"
        v=np.fromfile(case/"vertices.f64le",dtype="<f8").reshape(-1,3)
        f=np.fromfile(case/"faces.i64le",dtype="<i8").reshape(-1,3)
        equation=np.array(row["keep_negative_halfspace_coefficients"])
        value=ov@equation[:3]+equation[3]
        pos=np.searchsorted(vertex_keys,records(v));good=pos<len(vertex_keys)
        pos=np.minimum(pos,len(vertex_keys)-1);good&=vertex_keys[pos]==records(v)
        vertex_parent=np.where(good,vertex_order[pos],-1)
        mapped=vertex_parent[f];intact=np.all(mapped>=0,axis=1)
        key=records(canonical(mapped[intact]));found=np.searchsorted(face_keys,key)
        assert np.all(found<len(face_keys)) and np.all(face_keys[found]==key)
        face_parent=np.full(len(f),-1,dtype=np.int64);face_parent[intact]=face_order[found]
        caps=np.zeros(len(f),bool)
        for start in range(0,len(f),100000):
            residual=v[f[start:start+100000]]@equation[:3]+equation[3]
            caps[start:start+len(residual)]=np.abs(residual).max(axis=1)<1e-8
        active=np.flatnonzero(value[of].max(axis=1)>0)
        crossing=active[value[of[active]].min(axis=1)<=0]
        partial=np.flatnonzero(~intact&~caps)
        _,nearest,_=igl.point_mesh_squared_distance(v[f[partial]].mean(axis=1),ov,of[crossing])
        face_parent[partial]=crossing[nearest]
        bound=check_partial(v[f[partial]],ov[of[crossing[nearest]]])
        assert bound<1e-8,"Clipped skin is not contained in its parent triangle"
        expected=np.flatnonzero(value[of].max(axis=1)<=0)
        assert np.array_equal(np.sort(face_parent[intact]),expected)
        count,labels=components(of,active,value)
        outside_map=np.full(len(of),-1,dtype=np.int32);outside_map[active]=labels
        cap_ids=np.flatnonzero(caps);cap_count,cap_labels=components(f,cap_ids)
        neighbours={}
        for face in partial:
            for vertex in f[face]:neighbours.setdefault(int(vertex),[]).append(int(face))
        domains=[]
        for label in range(cap_count):
            ids=cap_ids[cap_labels==label];tri=f[ids]
            owners=set()
            for vertex in np.unique(tri):
                for face in neighbours.get(int(vertex),[]):
                    owner=int(outside_map[face_parent[face]])
                    if owner>=0:owners.add(owner)
            assert len(owners)==1,"Ambiguous cap/outside component"
            owner=owners.pop();outside_ids=active[labels==owner]
            q=v[tri];area=float(np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1).sum()/2)
            edges=tri[:,[[0,1],[1,2],[2,0]]].reshape(-1,2)
            keys=(np.minimum(edges[:,0],edges[:,1]).astype(np.uint64)<<np.uint64(32))|np.maximum(edges[:,0],edges[:,1]).astype(np.uint64)
            _,first,uses=np.unique(keys,return_index=True,return_counts=True)
            boundary=edges[first[uses==1]]
            perimeter=float(np.linalg.norm(v[boundary[:,1]]-v[boundary[:,0]],axis=1).sum())
            circularity=4*np.pi*area/perimeter**2 if perimeter else 0.
            extension=float(value[np.unique(of[outside_ids])].max()/np.linalg.norm(equation[:3]))
            selected=(rule["cap_area_mm2"][0]<=area<=rule["cap_area_mm2"][1]
                      and circularity>=rule["minimum_circularity"] and extension>=rule["minimum_outward_extension_mm"])
            domains.append({"cap_ids":ids,"outside_ids":outside_ids,"outside_component":owner,
                            "area_mm2":area,"circularity":circularity,"extension_mm":extension,
                            "selected":bool(selected),"cap_label":label})
        case_removed=np.zeros(len(of),bool);case_caps=np.zeros(len(f),bool)
        for domain in domains:
            # A single isolated protrusion must not share its outside region with
            # an unselected cap/fin domain. Keep ambiguous geometry unchanged.
            siblings=sum(d["outside_component"]==domain["outside_component"] for d in domains)
            selected=domain["selected"] and siblings==1
            all_rows.append({k:val for k,val in domain.items() if k not in ("cap_ids","outside_ids")}|{"selected":selected,"plane_index":plane_index,"cap_triangles":len(domain["cap_ids"]),"outside_parent_triangles":len(domain["outside_ids"]),"outside_component_cap_domains":siblings})
            if selected:
                assert not np.any(removed[domain["outside_ids"]]),"Selected regions overlap across independent planes"
                case_removed[domain["outside_ids"]]=True
                case_caps[domain["cap_ids"]]=True
        removed|=case_removed
        keep=((face_parent>=0)&case_removed[np.maximum(face_parent,0)])|case_caps
        fragment_faces=f[keep]
        used=np.unique(fragment_faces)
        new=used[vertex_parent[used]<0]
        index=vertex_parent.copy();index[new]=len(ov)+extra_count+np.arange(len(new))
        extra_vertices.append(v[new]);extra_count+=len(new)
        fragments.append(index[fragment_faces]);fragment_parent.append(face_parent[keep])
        fragment_tags.append(np.where(case_caps[keep],plane_index+1,0).astype(np.int8))
        case_checks.append({"plane_index":plane_index,"candidate_vertices_sha256":sha(case/"vertices.f64le"),
                            "candidate_faces_sha256":sha(case/"faces.i64le"),"all_fully_kept_parent_faces_identical":True,
                            "partial_skin_containment_upper_bound_mm":bound,"selected_domains":sum(x["selected"] and x["plane_index"]==plane_index for x in all_rows)})
        print(json.dumps(case_checks[-1]),flush=True)
    keep_parent=np.flatnonzero(~removed)
    master=np.concatenate([ov,*extra_vertices]);output_faces=np.concatenate([of[keep_parent],*fragments])
    used,indices=np.unique(output_faces,return_inverse=True)
    output_vertices=master[used];output_faces=indices.reshape(-1,3)
    tags=np.concatenate([np.zeros(len(keep_parent),np.int8),*fragment_tags])
    parent_faces=np.concatenate([keep_parent,*fragment_parent])
    np.savez_compressed(a.output/"head-local-hypothesis-source-mm.npz",vertices=output_vertices,triangles=output_faces)
    np.save(a.output/"private-face-construction-tags.npy",tags)
    np.savez_compressed(a.output/"private-source-provenance.npz",parent_face_ids=parent_faces,
                        source_parent_vertex_ids=np.where(used<len(ov),used,-1),removed_parent_faces=np.flatnonzero(removed))
    report={"source_sha256":sha(Path(__file__)),"plan_sha256":sha(a.plan),"parent_sha256":sha(a.parent),
            "planes_sha256":sha(a.planes),"cap_domains":all_rows,"single_plane_checks":case_checks,
            "selected_provisional_protrusions":sum(x["selected"] for x in all_rows),
            "retained_parent_triangles_identical":len(keep_parent),"clipped_skin_triangles":int(((tags==0)&(parent_faces>=0)).sum()-len(keep_parent)),
            "assumed_cap_triangles":int((tags>0).sum()),"output_vertices":len(output_vertices),"output_triangles":len(output_faces),
            "all_unselected_parent_faces_preserved":True,"coordinate_welding_used":False,
            "independent_geometry_acceptance_required":True,"physical_acceptance":False,"manufacturing_qualified":False}
    (a.output/"construction.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:val for k,val in report.items() if k not in ("cap_domains","single_plane_checks")}))


if __name__=="__main__":
    main()
