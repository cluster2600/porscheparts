"""Screen the two predeclared grid phases independently; no mesh repair."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from audit import HERE, ROOT, sha, stable_volume, surface, zero_mask


def vertex_cloud_distance(first, second):
    """Order-independent sampled-vertex distance, NOT a surface Hausdorff bound."""
    a, b = np.unique(first.reshape(-1, 3), axis=0), np.unique(second.reshape(-1, 3), axis=0)
    if not len(a) or not len(b) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Finite nonempty vertex clouds required")
    return float(max(cKDTree(a).query(b)[0].max(), cKDTree(b).query(a)[0].max()))


def run(replay, phase, output):
    if output.exists():
        raise FileExistsError(output)
    expected = sha(HERE.parent/"field-lattice/evidence/report.json")
    results, comparisons = {}, {}
    for resolution in ("050", "025"):
        label = "phase-"+resolution
        folder = phase/label
        native = json.loads((folder/"native.json").read_text())
        if (native["input_report_sha256"] != expected or native["case_id"] != label or
                native["original_design_parameters_changed"] is not False or native["mesh_repaired"] is not False):
            raise ValueError("Invalid phase input")
        triangles, digest = surface.load_binary_stl(folder/"raw.stl")
        if len(triangles) != native["triangles"]:
            raise ValueError("Triangle count changed")
        vertices, inverse = np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
        topology = surface.audit_arrays(vertices,inverse.reshape(-1,3))
        centred = stable_volume(triangles)
        global_triangles = triangles + np.array(native["local_to_F0_translation_mm"])
        baseline, _ = surface.load_binary_stl(replay/("global-"+resolution)/"raw.stl")
        local, _ = surface.load_binary_stl(replay/("local-"+resolution)/"raw.stl")
        local_receipt = json.loads((replay/("local-"+resolution)/"native.json").read_text())
        comparisons[resolution] = {
            "baseline_to_local_vertex_cloud_distance_mm": vertex_cloud_distance(baseline,local+np.array(local_receipt["local_to_F0_translation_mm"])),
            "baseline_to_phase_vertex_cloud_distance_mm": vertex_cloud_distance(baseline,global_triangles),
            "surface_hausdorff_bound_proven": False,
            "replay_audit_indexwise_vertex_delta_is_not_a_geometric_distance": True}
        global32 = global_triangles.astype(np.float32).astype(float)
        results[label] = {"native": native, "raw_stl_sha256": digest,
            "raw_vdb_sha256": sha(folder/"raw.vdb"), "native_receipt_sha256": sha(folder/"native.json"),
            "topology": topology, "centred_float64_signed_volume_mm3": centred,
            "native_volume_relative_difference": abs(native["volume_mm3"]-centred)/abs(centred),
            "float32_globalization_zero_area_faces": int(zero_mask(global32).sum()),
            "numerical_mesh_candidate": bool(topology["closed_oriented_combinatorial_surface_screen_pass"] and topology["edge_connected_face_components"]==1),
            "solver_ready": False, "manufacturing_authorized": False}
        print(label, "zero faces:",topology["exact_zero_area_faces"],"closed:",topology["closed_oriented_combinatorial_surface_screen_pass"],flush=True)
    volumes = [results["phase-"+r]["centred_float64_signed_volume_mm3"] for r in ("050","025")]
    report = {"schema":"964-lattice-grid-phase-assessment/v1", "cases":results,
        "order_independent_comparisons":comparisons,
        "phase_refinement_volume_relative_change":abs(volumes[1]-volumes[0])/abs(volumes[1]),
        "continuum_convergence_proven":False,"native_reported_volume_not_used_as_mass_evidence":True,
        "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),HERE/"Phase.cs",HERE/"Phase.csproj",HERE/"audit.py")},
        "structural_analysis_executed":False,"product_strength_validated":False,"manufacturing_authorized":False}
    with output.open("x") as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write("\n")
    return report


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay",type=Path);parser.add_argument("phase",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    run(args.replay,args.phase,args.output)
