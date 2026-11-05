#!/usr/bin/env python3
"""Check direct parent provenance and disclose unconditioned scan distances."""
import argparse
import json
from pathlib import Path
import igl
import numpy as np
from assess_preservation import sample,stats
from assemble_single_plane_local import check_partial
from prepare_aligned import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("parent","candidate","provenance","tags","scan","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    with np.load(a.parent,allow_pickle=False) as data:ov,of=data["vertices"],data["triangles"]
    with np.load(a.candidate,allow_pickle=False) as data:v,f=data["vertices"],data["triangles"]
    with np.load(a.provenance,allow_pickle=False) as data:
        parent_faces=data["parent_face_ids"];parent_vertices=data["source_parent_vertex_ids"];removed=data["removed_parent_faces"]
    tags=np.load(a.tags,allow_pickle=False)
    old=parent_vertices>=0
    assert np.array_equal(v[old],ov[parent_vertices[old]])
    mapped=parent_vertices[f];intact=np.all(mapped>=0,axis=1)
    assert np.array_equal(mapped[intact],of[parent_faces[intact]])
    expected=np.setdiff1d(np.arange(len(of)),removed,assume_unique=True)
    assert np.array_equal(np.sort(parent_faces[intact]),expected)
    partial=np.flatnonzero((tags==0)&~intact)
    bound=check_partial(v[f[partial]],ov[of[parent_faces[partial]]])
    assert bound<1e-8
    with np.load(a.scan,allow_pickle=False) as data:sv,sf=data["vertices"],data["triangles"]
    points,source_ids,_=sample(sv,sf,100000,935051)
    squared,_,_=igl.point_mesh_squared_distance(points,v,f);distance=np.sqrt(np.maximum(squared,0))
    parent_squared,_,_=igl.point_mesh_squared_distance(points,ov,of);parent_distance=np.sqrt(np.maximum(parent_squared,0))
    reverse,reverse_ids,area=sample(v,f,100000,935052)
    reverse_squared,_,_=igl.point_mesh_squared_distance(reverse,sv,sf);reverse_distance=np.sqrt(np.maximum(reverse_squared,0))
    np.savez_compressed(a.output/"private-distance-samples.npz",scan_face_ids=source_ids,
                        scan_to_candidate_mm=distance,scan_to_parent_mm=parent_distance,
                        candidate_face_ids=reverse_ids,candidate_to_scan_mm=reverse_distance)
    report={"source_sha256":sha(Path(__file__)),"parent_sha256":sha(a.parent),"candidate_sha256":sha(a.candidate),
            "provenance_sha256":sha(a.provenance),"scan_arrays_sha256":sha(a.scan),
            "retained_original_parent_triangles_identical":int(intact.sum()),
            "all_unselected_parent_faces_preserved":True,"clipped_skin_triangles":len(partial),
            "partial_skin_whole_triangle_containment_upper_bound_mm":bound,
            "assumed_cap_faces":[int((tags==i).sum()) for i in (1,2,3)],
            "assumed_cap_area_mm2":[float(area[tags==i].sum()) for i in (1,2,3)],
            "scan_to_parent_all":stats(parent_distance),"scan_to_local_candidate_all":stats(distance),
            "local_candidate_to_scan_all":stats(reverse_distance),
            "source_samples_with_distance_increase_over_0p01mm":int((distance-parent_distance>.01).sum()),
            "sample_seed_scan":935051,"sample_seed_candidate":935052,
            "samples_are_not_a_global_bound_or_physical_metrology":True,"no_anatomical_exclusion_from_all_sample_results":True,
            "physical_acceptance":False,"manufacturing_qualified":False}
    (a.output/"report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report))


if __name__=="__main__":main()
