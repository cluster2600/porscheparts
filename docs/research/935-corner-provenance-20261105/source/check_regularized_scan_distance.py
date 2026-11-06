"""Recheck complete-scan deviations using the identical frozen forward samples."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("surface","scan","frame","preservation","old-samples","old-manifest","helper","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    assert sha(args.helper)=="46e845ade2a427e7365191e2002256a2565a74b5710452bfaa0b482ecd519550"
    assert sha(args.scan)=="dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"
    assert sha(args.frame)=="fadd49707617c6339360009c2a279fe469bec0567f7b3dbe0191172bc9088766"
    assert sha(args.old_manifest)=="8efc92c65dc1c4e98e89f021226cedb57c7f883eb7e670f5f925ae27b0d78302"
    manifest=json.loads(args.old_manifest.read_text())
    expected=next(row for row in manifest["files"] if row["path"]=="scan-distance-check/private-samples.npz")
    assert sha(args.old_samples)==expected["sha256"]
    proof=json.loads(args.preservation.read_text());assert proof["candidate_sha256"]==sha(args.surface)
    assert proof["preservation_checks_passed"]
    spec=importlib.util.spec_from_file_location("frozen_scan_distance",args.helper)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    frame=json.loads(args.frame.read_text());rotation=np.array(frame["rotation_rows"])
    offset=np.array(frame["translation_after_rotation_mm"])
    assert np.max(np.abs(rotation@rotation.T-np.eye(3)))<1e-12 and abs(np.linalg.det(rotation)-1)<1e-12
    with np.load(args.surface,allow_pickle=False) as d:cv,cf=d["vertices"],d["triangles"]
    vertices=(cv-offset)@rotation
    roundtrip=float(np.linalg.norm(vertices@rotation.T+offset-cv,axis=1).max());assert roundtrip<1e-9
    with np.load(args.scan,allow_pickle=False) as d:sv,sf=d["vertices"],d["triangles"]
    points,ids=helper.sample(sv,sf,935051)
    with np.load(args.old_samples,allow_pickle=False) as d:
        assert np.array_equal(ids,d["scan_face_ids"])
        before=d["scan_to_before_mm"];old_reverse=d["before_to_scan_mm"]
    after=helper.distance(points,vertices,cf)
    reverse_points,reverse_ids=helper.sample(vertices,cf,935052)
    reverse=helper.distance(reverse_points,sv,sf)
    change=float(np.abs(after-before).max())
    assert change<=proof["composed_complete_surface_correspondence_bound_mm"]+1e-8
    np.savez_compressed(args.output/"private-distances.npz",scan_face_ids=ids,
        scan_to_candidate_mm=after,candidate_face_ids=reverse_ids,candidate_to_scan_mm=reverse)
    result={"source_sha256":sha(Path(__file__)),"helper_sha256":sha(args.helper),
            "surface_sha256":sha(args.surface),"scan_sha256":sha(args.scan),"frame_sha256":sha(args.frame),
            "old_samples_sha256":sha(args.old_samples),"preservation_sha256":sha(args.preservation),
            "samples_per_direction":100000,"same_forward_sample_definition_and_ids":True,
            "source_frame_roundtrip_max_mm":roundtrip,"no_anatomical_exclusions":True,
            "baseline_to_scan_all":helper.stats(old_reverse),"scan_to_baseline_all":helper.stats(before),
            "scan_to_regularized_all":helper.stats(after),"regularized_to_scan_all":helper.stats(reverse),
            "maximum_paired_forward_distance_change_mm":change,
            "composed_independent_model_correspondence_bound_mm":proof["composed_complete_surface_correspondence_bound_mm"],
            "reverse_samples_are_not_paired_physical_points":True,
            "sampling_is_not_global_scan_distance_or_metrology":True,
            "physical_acceptance":False,"manufacturing_qualified":False,"seconds":time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
