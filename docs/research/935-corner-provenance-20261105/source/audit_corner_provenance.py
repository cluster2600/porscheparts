"""Trace forcing faces and acute sectors through clipping and reconstruction.

An unmatched acquired triangle is unestablished correspondence, not proof of an
unobserved surface or a removable physical feature. No geometry is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def records(array):
    return np.ascontiguousarray(array).view(np.dtype([(str(i),array.dtype) for i in range(3)])).ravel()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("mesh","baseline","provenance","tags","parent-vertices","parent-faces","raw-arrays","sectors","sector-manifest","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    expected={"mesh":"7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f",
              "baseline":"05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594",
              "provenance":"b6bafbf36b5c6cb8f76025ea9d9206d391f14341f6e1c808a7224e478901f0ed",
              "tags":"877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f",
              "parent_vertices":"7e94589278033ac69b3013f3170c94d7d47669bd2144372e9a2e22012bb1669f",
              "parent_faces":"ae78efb6a4b79690220b864b6b4d00ebcaf3ab1f5d1390b6d7b471795dec6ddb",
              "raw_arrays":"dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a",
              "sector_manifest":"d835279d915d43e14be48eac7fe80e7fa644a316de928002451a75660cb730a2"}
    for name,value in expected.items():assert sha(getattr(args,name))==value,name
    manifest=json.loads(args.sector_manifest.read_text())
    sector_row=next(r for r in manifest["files"] if r["path"]=="feature-corner-audit/private-corner-sectors.npz")
    assert sha(args.sectors)==sector_row["sha256"]
    plan={"source_sha256":sha(Path(__file__)),"input_sha256":expected,"sector_sha256":sha(args.sectors),
          "scope":"Upstream provenance and indexed identity only; no reconstruction or physical feature classification",
          "classifications":["inherited_parent_triangle","new_cut_fragment","assumed_cap","conditioning_retriangulated"],
          "original_obj_sha256":"4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486",
          "new_paid_compute_usd":0,"geometry_modified":False}
    (args.output/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    with np.load(args.mesh,allow_pickle=False) as d:v,f=d["vertices"],d["triangles"]
    with np.load(args.baseline,allow_pickle=False) as d:bv,bf=d["vertices"],d["triangles"]
    with np.load(args.provenance,allow_pickle=False) as d:pfid,pvid=d["parent_face_ids"],d["source_parent_vertex_ids"]
    tags=np.load(args.tags,allow_pickle=False)
    pv=np.memmap(args.parent_vertices,dtype="<f8",mode="r").reshape(-1,3)
    pf=np.memmap(args.parent_faces,dtype="<i8",mode="r").reshape(-1,3)
    with np.load(args.sectors,allow_pickle=False) as d:sectors=d["records"]
    sector_ids=sectors[:,0].astype(np.int64);assert len(sector_ids)==170
    q=np.empty(len(f))
    for start in range(0,len(f),100000):
        xyz=v[f[start:start+100000]];a,b,c=xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0],xyz[:,2]-xyz[:,1]
        q[start:start+len(xyz)]=2*np.sqrt(3)*np.linalg.norm(np.cross(a,b),axis=1)/np.sum(a*a+b*b+c*c,axis=1)
    forcing=np.flatnonzero(q**(2/3)<.01);assert len(forcing)==633
    assert np.isin(sector_ids,forcing).all()
    selected=np.union1d(forcing,sector_ids)
    unchanged=(f[selected]==bf[selected]).all(axis=1)
    mapped=pvid[bf[selected]];all_parent=(mapped>=0).all(axis=1)
    category=np.full(len(selected),"new_cut_fragment",dtype="<U32")
    category[all_parent]="inherited_parent_triangle"
    category[tags[selected]>0]="assumed_cap"
    category[~unchanged]="conditioning_retriangulated"
    inherited=category=="inherited_parent_triangle"
    assert np.all(pfid[selected[inherited]]>=0)
    original=pf[pfid[selected[inherited]]];mapped_inherited=mapped[inherited]
    assert np.all(np.any(np.stack([(original==np.roll(mapped_inherited,k,axis=1)).all(axis=1) for k in range(3)]),axis=0))
    changed_coordinates=np.any(np.any(v!=bv,axis=1)[f[selected]],axis=1)
    current_all_parent=(pvid[f[selected]]>=0).all(axis=1)
    raw_identity=np.zeros(len(selected),bool)
    with np.load(args.raw_arrays,allow_pickle=False) as d:rv,rf=d["vertices"],d["triangles"]
    raw_keys=records(rv);ordering=np.argsort(raw_keys);ordered=raw_keys[ordering]
    selected_parent_ids=np.unique(pfid[selected][pfid[selected]>=0])
    selected_parent_vertices=np.unique(pf[selected_parent_ids])
    parent_points=pv[selected_parent_vertices]
    location=np.searchsorted(ordered,records(parent_points));inside=location<len(ordered)
    location=np.minimum(location,len(ordered)-1);inside&=ordered[location]==records(parent_points)
    raw_vertex_index=np.full(len(pv),-1,dtype=np.int64)
    raw_vertex_index[selected_parent_vertices[inside]]=ordering[location[inside]]
    possible=raw_vertex_index[pf[pfid[selected[inherited]]]]
    matched=(possible>=0).all(axis=1)
    acquired_keys=np.sort(records(np.sort(rf,axis=1)))
    key=records(np.sort(possible[matched],axis=1));position=np.searchsorted(acquired_keys,key)
    good=position<len(acquired_keys);position=np.minimum(position,len(acquired_keys)-1)
    good&=acquired_keys[position]==key
    rows=np.flatnonzero(inherited)[matched];raw_identity[rows]=good
    def counts(ids):
        mask=np.isin(selected,ids)
        return {"faces":int(mask.sum()),"by_origin":{name:int((mask&(category==name)).sum()) for name in plan["classifications"]},
                "coordinates_changed_by_conditioning":int((mask&changed_coordinates).sum()),
                "exact_indexed_acquired_triangle_ancestry":int((mask&raw_identity).sum()),
                "inherited_parent_vertices_only":int((mask&current_all_parent).sum())}
    result={"source_sha256":sha(Path(__file__)),"inputs_sha256":expected,"sector_sha256":sha(args.sectors),
            "forcing_faces":counts(forcing),"sector_faces":counts(sector_ids),
            "parent_envelope_faces":len(pf),"raw_acquired_faces":len(rf),
            "selected_parent_vertices":len(selected_parent_vertices),"selected_parent_vertices_exactly_in_raw":int(inside.sum()),
            "inherited_parent_face_indices_independently_verified":True,
            "classification_does_not_identify_physical_features":True,
            "no_exact_raw_match_means_unestablished_not_unobserved":True,
            "geometry_modified":False,"physics_admitted":False,"manufacturing_qualified":False,
            "seconds":time.monotonic()-started}
    np.savez_compressed(args.output/"private-provenance.npz",face_ids=selected,origin=category,
        exact_raw_triangle_ancestry=raw_identity,coordinates_changed=changed_coordinates)
    (args.output/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
