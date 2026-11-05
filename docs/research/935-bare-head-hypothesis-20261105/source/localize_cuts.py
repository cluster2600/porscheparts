#!/usr/bin/env python3
"""Audit connected cut-cap domains before selecting local protrusion hypotheses.

Restore every parent face outside unselected domains; never delete a fin merely
because it extends beyond a provisional mounting plane.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from prepare_aligned import sha


def components(faces, ids, vertex_values=None):
    faces=faces[ids]
    edge=faces[:,[[0,1],[1,2],[2,0]]].reshape(-1,2)
    owner=np.repeat(np.arange(len(faces)),3)
    if vertex_values is not None:
        keep=vertex_values[edge].max(axis=1)>0
        edge,owner=edge[keep],owner[keep]
    key=(np.minimum(edge[:,0],edge[:,1]).astype(np.uint64)<<np.uint64(32))|np.maximum(edge[:,0],edge[:,1]).astype(np.uint64)
    order=np.argsort(key,kind="stable")
    same=key[order[1:]]==key[order[:-1]]
    a,b=owner[order[:-1]][same],owner[order[1:]][same]
    graph=coo_matrix((np.ones(len(a),bool),(a,b)),shape=(len(faces),len(faces))).tocsr()
    return connected_components(graph,directed=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("parent","candidate","provenance","tags","planes","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    with np.load(a.parent,allow_pickle=False) as data:ov,of=data["vertices"],data["triangles"]
    with np.load(a.candidate,allow_pickle=False) as data:v,f=data["vertices"],data["triangles"]
    tags=np.load(a.tags,allow_pickle=False)
    with np.load(a.provenance,allow_pickle=False) as data:
        vertex_parent=data["candidate_vertex_parent_ids"]
        intact_ids=data["unchanged_parent_face_ids"]
        partial_ids=data["partial_candidate_faces"]
        partial_parent=data["partial_parent_faces"]
    intact=np.all(vertex_parent[f]>=0,axis=1)
    face_parent=np.full(len(f),-1,dtype=np.int64)
    assert intact.sum()==len(intact_ids)
    face_parent[intact]=intact_ids;face_parent[partial_ids]=partial_parent
    planes=np.array([r["keep_negative_halfspace_coefficients"] for r in json.loads(a.planes.read_text())])
    cap_vertex_face={}
    partial_neighbours={}
    for face in partial_ids:
        for vertex in f[face]:partial_neighbours.setdefault(int(vertex),[]).append(int(face))
    rows=[];private=[]
    for plane_index,plane in enumerate(planes):
        value=ov@plane[:3]+plane[3]
        active=np.flatnonzero(value[of].max(axis=1)>0)
        count,outside_labels=components(of,active,value)
        parent_component=np.full(len(of),-1,dtype=np.int32);parent_component[active]=outside_labels
        cap_ids=np.flatnonzero(tags==plane_index+1)
        cap_count,cap_labels=components(f,cap_ids)
        for label in range(cap_count):
            ids=cap_ids[cap_labels==label];tri=f[ids];vertices=np.unique(tri)
            possible=set()
            for vertex in vertices:
                for neighbour in partial_neighbours.get(int(vertex),[]):
                    cid=int(parent_component[face_parent[neighbour]])
                    if cid>=0:possible.add(cid)
            assert len(possible)==1,"Cap-to-parent outside component is ambiguous"
            outside_id=possible.pop();outside_faces=active[outside_labels==outside_id]
            xyz=v[tri];cross=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]);area=float(np.linalg.norm(cross,axis=1).sum()/2)
            edge=tri[:,[[0,1],[1,2],[2,0]]].reshape(-1,2)
            key=(np.minimum(edge[:,0],edge[:,1]).astype(np.uint64)<<np.uint64(32))|np.maximum(edge[:,0],edge[:,1]).astype(np.uint64)
            unique,first,uses=np.unique(key,return_index=True,return_counts=True)
            boundary=edge[first[uses==1]]
            perimeter=float(np.linalg.norm(v[boundary[:,1]]-v[boundary[:,0]],axis=1).sum())
            outward=float(value[np.unique(of[outside_faces])].max()/np.linalg.norm(plane[:3]))
            circularity=4*np.pi*area/perimeter**2 if perimeter else 0.
            # Predeclared provisional classifier: size/roundness AND an external stem.
            selected=10<=area<=150 and circularity>=.7 and outward>=5
            row={"cap_id":len(rows),"plane_index":plane_index,"cap_triangles":len(ids),
                 "parent_outside_faces":len(outside_faces),"cap_area_mm2":area,"perimeter_mm":perimeter,
                 "circularity":circularity,"outward_extent_mm":outward,
                 "selected_provisional_threaded_protrusion":bool(selected),"anatomical_acceptance":False}
            rows.append(row);private.append((ids,outside_faces))
    np.savez_compressed(a.output/"private-localization.npz",face_parent_ids=face_parent,vertex_parent_ids=vertex_parent,
                        **{f"cap_{i}_faces":x[0] for i,x in enumerate(private)},
                        **{f"cap_{i}_outside_parent_faces":x[1] for i,x in enumerate(private)})
    report={"source_sha256":sha(Path(__file__)),"parent_sha256":sha(a.parent),"candidate_sha256":sha(a.candidate),
            "classifier_is_construction_hypothesis":True,"cap_domains":rows,
            "selected_cap_domains":sum(r["selected_provisional_threaded_protrusion"] for r in rows),
            "unselected_cap_domains_restored":sum(not r["selected_provisional_threaded_protrusion"] for r in rows),
            "manufacturing_qualified":False}
    (a.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


if __name__=="__main__":
    main()
