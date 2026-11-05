#!/usr/bin/env python3
"""Restore parent geometry outside selected, source-bound protrusion components."""
import argparse
import json
from pathlib import Path

import numpy as np
from prepare_aligned import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("parent","candidate","localization","planes","plan","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    report=json.loads((a.localization/"report.json").read_text())
    plan=json.loads(a.plan.read_text())
    assert report["parent_sha256"]==sha(a.parent) and report["candidate_sha256"]==sha(a.candidate)
    with np.load(a.parent,allow_pickle=False) as data:ov,of=data["vertices"],data["triangles"]
    with np.load(a.candidate,allow_pickle=False) as data:v,f=data["vertices"],data["triangles"]
    data=np.load(a.localization/"private-localization.npz",allow_pickle=False)
    parent_ids=data["face_parent_ids"];vertex_ids=data["vertex_parent_ids"]
    planes=np.array([r["keep_negative_halfspace_coefficients"] for r in json.loads(a.planes.read_text())])
    selected_parent=np.zeros(len(of),bool);selected_caps=np.zeros(len(f),bool)
    cap_tags=np.zeros(len(f),np.int8);chosen=[]
    for row in report["cap_domains"]:
        rule=plan["selection_hypothesis"]
        expected=(rule["cap_area_mm2"][0]<=row["cap_area_mm2"]<=rule["cap_area_mm2"][1]
                  and row["circularity"]>=rule["minimum_circularity"]
                  and row["outward_extent_mm"]>=rule["minimum_outward_extension_mm"])
        assert expected==row["selected_provisional_threaded_protrusion"]
        if not expected:continue
        cap=row["cap_id"];ids=data[f"cap_{cap}_outside_parent_faces"]
        other=[i for i in range(len(planes)) if i!=row["plane_index"]]
        for start in range(0,len(ids),50000):
            q=ov[of[ids[start:start+50000]]]
            assert np.all(q@planes[other,:3].T+planes[other,3]<=0),"Selected component crosses another construction plane"
        selected_parent[ids]=True
        caps=data[f"cap_{cap}_faces"]
        selected_caps[caps]=True;cap_tags[caps]=row["plane_index"]+1
        chosen.append(cap)
    assert chosen
    skin=(parent_ids>=0)&selected_parent[np.maximum(parent_ids,0)]
    assert not np.any(skin&selected_caps)
    candidate_ids=np.flatnonzero(skin|selected_caps)
    original_ids=np.flatnonzero(~selected_parent)
    # Reuse original indexed vertices by provenance, not approximate coordinate welding.
    new=np.flatnonzero(vertex_ids<0)
    mapping=vertex_ids.copy();mapping[new]=len(ov)+np.arange(len(new))
    master=np.concatenate((ov,v[new]))
    output_faces=np.concatenate((of[original_ids],mapping[f[candidate_ids]]))
    used,remapped=np.unique(output_faces,return_inverse=True)
    output_vertices=master[used];output_faces=remapped.reshape(-1,3)
    np.savez_compressed(a.output/"head-local-hypothesis-source-mm.npz",vertices=output_vertices,triangles=output_faces)
    tags=np.r_[np.zeros(len(original_ids),dtype=np.int8),cap_tags[candidate_ids]]
    np.save(a.output/"private-face-construction-tags.npy",tags)
    np.savez_compressed(a.output/"private-source-provenance.npz",retained_parent_face_ids=original_ids,
                        global_candidate_face_ids=candidate_ids,global_candidate_parent_ids=parent_ids[candidate_ids],
                        master_vertex_ids=used,global_new_vertex_ids=new)
    summary={"source_sha256":sha(Path(__file__)),"local_plan_sha256":sha(a.plan),
             "parent_sha256":sha(a.parent),"global_candidate_sha256":sha(a.candidate),
             "localization_report_sha256":sha(a.localization/"report.json"),
             "selected_provisional_protrusion_domains":chosen,"unselected_domains_restored":report["unselected_cap_domains_restored"],
             "retained_parent_triangles_with_identical_coordinates_and_orientation":len(original_ids),
             "clipped_skin_triangles":int(skin.sum()),"assumed_cap_triangles":int(selected_caps.sum()),
             "output_vertices":len(output_vertices),"output_triangles":len(output_faces),
             "unselected_fin_and_boss_faces_preserved":True,"independent_output_validation_required":True,
             "physical_acceptance":False,"manufacturing_qualified":False}
    (a.output/"construction.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary))


if __name__=="__main__":
    main()
