"""Reconcile all original source IDs, native chart coverage and partition seams.

This joins already independently inspected actual STEP files to the complete
acquisition. Native point-contact fan splits and chart seams remain explicit.
Neither the provenance map nor these counts supplies physical inspection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024**2), b""):h.update(data)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); started = time.monotonic()
    args.output.mkdir(mode=0o700, exist_ok=False)
    arrays = args.prepared/"source-arrays.npz"; plan = args.prepared/"source-atlas-plan.npz"
    assert sha(arrays) == "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"
    assert sha(plan) == "f26389c910ded839b94de910f495c0110a0fd103fc860af2b4a07e25139d5026"
    terminal = json.loads((args.results/"terminal.json").read_text())
    assert terminal["complete"] and terminal["requested_all_chunks"] and terminal["all_owned_children_reaped"]
    assert [i["chunk"] for i in terminal["completed_chunks"]] == list(range(83))
    manifest = json.loads((args.results/"manifest.json").read_text()); assert manifest["complete"]
    expected = {x["path"]:x for x in manifest["files"]}
    assert len(expected) == len(manifest["files"])
    actual = {str(p.relative_to(args.results)) for p in args.results.rglob("*") if p.is_file()}
    assert actual == set(expected)|{"manifest.json"}
    for name, item in expected.items():
        p = args.results/name
        assert not p.is_symlink() and p.resolve().is_relative_to(args.results.resolve())
        assert p.stat().st_size == item["bytes"] and sha(p) == item["sha256"]
    with np.load(arrays, allow_pickle=False) as a:faces = a["triangles"]; vertex_count = len(a["vertices"])
    with np.load(plan, allow_pickle=False) as p:
        owner = p["source_chunk_owner"]; reasons = p["source_quarantine_reason_bits"]
    assert len(faces) == len(owner) == len(reasons) == 2466040 and vertex_count == 1281608
    admitted = np.flatnonzero(owner >= 0); quarantine = np.flatnonzero(owner < 0)
    assert len(admitted) == 2465836 and len(quarantine) == 204
    assert np.array_equal(reasons == 0, owner >= 0)
    covered = np.zeros(len(faces), dtype=np.uint8); records = []
    for index in range(83):
        root = args.results/("chunk-"+str(index).zfill(4)); wanted = np.flatnonzero(owner == index)
        build = json.loads((root/"build-report.json").read_text())
        proof = json.loads((root/"independent-verification.json").read_text())
        assert build["chunk"] == proof["chunk"] == index
        assert build["source_faces"] == proof["source_faces"] == len(wanted)
        assert proof["independent_original_acquisition_not_builder_map"]
        comparison = proof["native_source_comparison"]
        assert all(comparison["checks"].values()) and comparison["vertex_roundtrip_maximum_mm"] == 0
        assert proof["all_native_support_planes_inspected"] == len(wanted)
        assert proof["native_support_plane_residual_maximum_nominal_mm"] <= 1e-8
        assert proof["step_sha256"] == build["step_sha256"]
        mapping = root/"private-source-chart-map.npz"; assert sha(mapping) == build["source_map_sha256"]
        with np.load(mapping, allow_pickle=False) as m:
            ids = m["source_face_ids"]; original_vertices = m["chart_original_vertex_ids"]; chart_faces = m["chart_faces"]
            assert np.array_equal(ids, wanted)
            assert np.array_equal(original_vertices[chart_faces], faces[ids])
        covered[wanted] += 1
        records.append({"chunk": index, "faces": len(wanted), "native_edges": comparison["edges"],
                        "native_boundary_edges": comparison["source_boundary_edges"],
                        "native_vertices": comparison["native_vertices"], "shells": comparison["shells"],
                        "extra_point_contact_fan_vertices": build["topology"]["additional_coincident_chart_vertices"],
                        "plane_residual": proof["native_support_plane_residual_maximum_nominal_mm"],
                        "proof_sha256": sha(root/"independent-verification.json")})
    assert np.all(covered[admitted] == 1) and np.all(covered[quarantine] == 0)
    tri = faces[admitted]
    edges = np.stack((tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]), axis=1).reshape(-1, 2)
    direction = edges[:, 0] < edges[:, 1]; codes = edges.min(axis=1)*vertex_count+edges.max(axis=1)
    order = np.argsort(codes, kind="stable"); codes = codes[order]
    edge_owner = np.repeat(owner[admitted], 3)[order]; direction = direction[order]
    starts = np.r_[0, np.flatnonzero(codes[1:] != codes[:-1])+1]; uses = np.diff(np.r_[starts, len(codes)])
    assert np.all((uses == 1)|(uses == 2))
    paired = starts[uses == 2]; assert np.all(direction[paired] != direction[paired+1])
    seams = paired[edge_owner[paired] != edge_owner[paired+1]]
    unique_edges = len(starts); boundary_edges = int(np.count_nonzero(uses == 1)); seam_count = len(seams)
    assert unique_edges == 3748827 and boundary_edges == 100146
    assert sum(r["native_edges"] for r in records) == unique_edges+seam_count
    assert sum(r["native_boundary_edges"] for r in records) == boundary_edges+2*seam_count
    seam_file = args.output/"private-chart-seams.npz"
    np.savez_compressed(seam_file, source_edge_vertex_ids=np.column_stack((codes[seams]//vertex_count, codes[seams]%vertex_count)),
                        first_chunk=edge_owner[seams], second_chunk=edge_owner[seams+1])
    result = {"source_sha256": sha(__file__), "arrays_sha256": sha(arrays), "plan_sha256": sha(plan),
              "results_manifest_sha256": sha(args.results/"manifest.json"), "all_manifest_payload_bytes_verified": True,
              "all_original_records_accounted": len(faces), "admitted_source_faces_once_in_actual_native_STEP": len(admitted),
              "quarantined_source_faces_retained_unchanged_outside_native_CAD": len(quarantine),
              "charts": len(records), "original_source_edges": unique_edges, "original_open_edges": boundary_edges,
              "two_use_source_edges_partitioned_across_charts": seam_count,
              "sum_native_chart_edges": sum(r["native_edges"] for r in records),
              "sum_native_chart_boundary_edges": sum(r["native_boundary_edges"] for r in records),
              "chart_seam_multiplicity_reconciled": True, "per_chart": records,
              "private_seam_map_sha256": sha(seam_file),
              "source_vertex_point_contacts_and_chart_seams_not_globally_sewn": True,
              "maximum_original_vertex_error_nominal_mm": 0.0,
              "maximum_native_plane_residual_nominal_mm": max(r["plane_residual"] for r in records),
              "no_unknown_surface_caps_or_hidden_geometry_inferred": True,
              "closed_head_solid_created": False, "physical_acceptance": False, "manufacturing_authorized": False,
              "seconds": time.monotonic()-started}
    with (args.output/"report.json").open("x") as stream:json.dump(result, stream, indent=2); stream.write("\n")
    print(json.dumps({k:v for k,v in result.items() if k != "per_chart"}))


if __name__ == "__main__":main()
