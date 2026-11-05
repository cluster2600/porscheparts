#!/usr/bin/env python3
"""Bind exact contact proofs to actual mesh bytes, then apply a rigid build frame."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def admit(mesh, raw_report, contacts, contact_source, validator_source):
    raw=json.loads(raw_report.read_text())
    proofs=json.loads(contacts.read_text())
    assert raw["input_sha256"]==sha(mesh)
    assert proofs["source_sha256"]==sha(contact_source)
    for key in ("zero_area_triangles","open_edges","nonmanifold_edges","inconsistently_oriented_edges"):
        assert raw[key]==0,key
    assert raw["vertex_manifold"] and raw["signed_volume_mm3"]>0
    assert raw["connected_components"]==1
    with np.load(mesh,allow_pickle=False) as data:
        v,f=data["vertices"],data["triangles"]
    assert len(v)==raw["vertices"] and len(f)==raw["triangles"]
    assert len(np.unique(f))==len(v)
    pairs_path=raw_report.parent/"intersection-pairs.npy"
    pairs=np.load(pairs_path,allow_pickle=False)
    assert len(pairs)==raw["intersection_pairs"]==proofs["raw_reported_pairs"]
    checker=module(contact_source,"exact_contacts")
    checker.controls()
    assert len(pairs)==len(proofs["private_pair_proofs"])
    for pair, row in zip(pairs,proofs["private_pair_proofs"]):
        assert list(map(int,pair))==row["triangle_pair"]
        actual=checker.prove(v,f,*map(int,pair))
        assert actual is not None and actual==row["proof"]
    validator=module(validator_source,"geometry_validator")
    validator.shell_controls()
    shell=validator.classify_shells(v,f,np.zeros(len(v),dtype=np.int32))
    assert shell["one_material_body"]
    result={**raw,"raw_predicate_intersection_pairs":len(pairs),
            "proved_indexed_shared_simplex_contacts":len(pairs),"proper_nonadjacent_intersection_pairs":0,
            "exact_contact_report_sha256":sha(contacts),"exact_contact_source_sha256":sha(contact_source),
            "raw_report_sha256":sha(raw_report),"pair_file_sha256":sha(pairs_path),
            "geometry_validator_sha256":sha(validator_source),"solid_shell_classification":shell,
            "geometry_export_gate_passed":True,
            "acceptance_scope":"Closed candidate under declared construction hypotheses; all raw findings independently classified; no physical/manufacturing qualification"}
    return v,f,result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("mesh","raw-report","contacts","contact-source","validator-source","frame","planes","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(exist_ok=False)
    v,f,report=admit(a.mesh,a.raw_report,a.contacts,a.contact_source,a.validator_source)
    (a.output/"source-geometry-admission.json").write_text(json.dumps(report,indent=2)+"\n")
    frame=np.load(a.frame,allow_pickle=False)
    assert np.max(np.abs(frame@frame.T-np.eye(3)))<1e-12
    assert abs(np.linalg.det(frame)-1)<1e-12
    aligned=v@frame.T
    offset=np.array([10.,10.,10.])-aligned.min(axis=0)
    aligned+=offset
    inverse=(aligned-offset)@frame
    error=float(np.linalg.norm(inverse-v,axis=1).max())
    assert error<1e-9
    planes=np.array([row["keep_negative_halfspace_coefficients"] for row in json.loads(a.planes.read_text())])
    tags=np.zeros(len(f),dtype=np.int8)
    for start in range(0,len(f),100000):
        xyz=v[f[start:start+100000]]
        residual=xyz@planes[:,:3].T+planes[:,3]
        cap=np.abs(residual).max(axis=1)<1e-8
        if np.any(cap.sum(axis=1)>1):
            raise ValueError("Ambiguous cap face classification")
        for index in range(len(planes)):
            tags[start:start+len(xyz)][cap[:,index]]=index+1
    np.save(a.output/"private-face-construction-tags.npy",tags)
    np.savez_compressed(a.output/"head-build-mm.npz",vertices=aligned,triangles=f)
    transform={"source_mesh_sha256":sha(a.mesh),"source_frame_sha256":sha(a.frame),
               "rotation_rows":frame.tolist(),"translation_after_rotation_mm":offset.tolist(),
               "all_face_indices_preserved":True,"inverse_roundtrip_max_mm":error,
               "head_bounds_mm":[aligned.min(axis=0).tolist(),aligned.max(axis=0).tolist()],
               "face_tag_counts":[int((tags==i).sum()) for i in range(4)],
               "tag_names":["retained_or_trimmed_parent_surface","assumed_back_cap","assumed_low_B_cap","assumed_high_B_cap"],
               "physical_acceptance":False,"manufacturing_qualified":False}
    (a.output/"private-rigid-frame-and-tags.json").write_text(json.dumps(transform,indent=2)+"\n")
    print(json.dumps({"geometry_admitted_under_hypotheses":True,"face_tag_counts":transform["face_tag_counts"],
                      "inverse_roundtrip_max_mm":error,"manufacturing_qualified":False}))


if __name__=="__main__":
    main()
