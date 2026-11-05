"""Attribute sampled short chords to retained envelope skin or assumed cut caps."""
import argparse
import hashlib
import json
from pathlib import Path

import igl
import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("samples", "tags", "scan-arrays", "frame", "parent-manifest", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Existing attribution output refused"
    assert sha(args.scan_arrays) == "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"
    with np.load(args.samples, allow_pickle=False) as data:
        source, target = data["source_faces"], data["hit_faces"]
        points, hit_points, distances = data["points"], data["hit_points"], data["distance_mm"]
    tags = np.load(args.tags, allow_pickle=False)
    assert len(tags) == 8219310 and np.all((target >= 0) & (target < len(tags)))
    with np.load(args.scan_arrays, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    short = distances < .5
    endpoints_build = np.concatenate([points[short], hit_points[short]])
    manifest = json.loads(args.parent_manifest.read_text())
    frame_rows = [row for row in manifest["files"] if (args.parent_manifest.parent / row["path"]).resolve() == args.frame.resolve()]
    assert len(frame_rows) == 1 and sha(args.frame) == frame_rows[0]["sha256"]
    frame = json.loads(args.frame.read_text())
    assert frame["source_mesh_sha256"] == "4f875b028ce1eb5106ade3a08a115e29e26249e053a40ee49f02f643ffe457b6"
    rotation = np.asarray(frame["rotation_rows"])
    offset = np.asarray(frame["translation_after_rotation_mm"])
    assert np.max(np.abs(rotation @ rotation.T - np.eye(3))) < 1e-12
    endpoints = (endpoints_build - offset) @ rotation
    roundtrip = float(np.linalg.norm(endpoints @ rotation.T + offset - endpoints_build, axis=1).max())
    assert roundtrip < 1e-9
    squared, _, nearest = igl.point_mesh_squared_distance(endpoints, vertices, faces)
    raw_distances = np.sqrt(np.maximum(squared, 0)).reshape(2, -1).T
    summaries = []
    for threshold in [.1,.25,.5,1,2]:
        selected = distances < threshold
        summaries.append({"threshold_mm":threshold,"samples":int(selected.sum()),
                          "both_endpoints_on_retained_parent_skin":int((selected & (tags[source]==0) & (tags[target]==0)).sum()),
                          "one_or_more_endpoints_on_assumed_cut_caps":int((selected & ((tags[source]>0) | (tags[target]>0))).sum())})
    args.output.mkdir(mode=0o700)
    np.savez_compressed(args.output / "private-short-endpoint-source-distances.npz",
                        sample_ids=np.flatnonzero(short), endpoint_distances_to_raw_scan_mm=raw_distances,
                        nearest_original_scan_points=nearest)
    result = {"source_sha256":sha(Path(__file__)),"samples_sha256":sha(args.samples),"tags_sha256":sha(args.tags),
              "scan_arrays_sha256":sha(args.scan_arrays),"frame_sha256":sha(args.frame),
              "parent_manifest_sha256":sha(args.parent_manifest),"source_build_frame_roundtrip_max_mm":roundtrip,
              "source_frame_restored_before_scan_distance_query":True,"groups":summaries,
              "shorter_than_0p5mm_endpoint_distance_to_original_scan_mm":{
                  key:float(value) for key,value in zip(["minimum","median","p95","maximum"],np.quantile(raw_distances,[0,.5,.95,1]))},
              "both_endpoints_within_0p01mm_of_original_scan":int((raw_distances.max(axis=1)<=.01).sum()),
              "envelope_skin_is_not_original_scan_or_physical_metrology":True,
              "proximity_does_not_identify_a_wall_or_validate_inherited_closures":True,
              "physical_acceptance":False,"manufacturing_qualified":False}
    with (args.output / "report.json").open("x") as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == "__main__":
    main()
