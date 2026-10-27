"""Prepare a separate water-surface derivative; never replace the native master."""
import argparse
import hashlib
import json
import math
from pathlib import Path

LIMIT_MM = .0625


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def admitted(metrics):
    values = metrics["sampled_deviations_mm"]
    return (len(values) == 4 and all(math.isfinite(v) and 0 <= v <= LIMIT_MM for v in values)
            and metrics["watertight"] and metrics["consistent_winding"]
            and metrics["components"] == 1 and metrics["euler_preserved"]
            and math.isfinite(metrics["relative_volume_change"])
            and abs(metrics["relative_volume_change"]) <= .02)


def prepare(source, expected_sha, output):
    if sha(source) != expected_sha:
        raise ValueError("Native water surface differs from its inspection receipt")
    if output.exists():
        raise ValueError("Output must be new")
    from meshlib import mrmeshpy as mr
    output.mkdir(parents=True)
    mesh = mr.loadMesh(source)
    before = mesh.topology.numValidFaces()
    settings = mr.DecimateSettings()
    settings.maxError = LIMIT_MM
    settings.optimizeVertexPos = False
    mr.decimateMesh(mesh, settings)
    candidate = output / "coolant.stl"
    mr.saveMesh(mesh, candidate)
    report = dict(status="awaiting_independent_surface_checks", original_faces=before,
                  faces=mesh.topology.numValidFaces(), source_sha256=expected_sha,
                  candidate_sha256=sha(candidate), script_sha256=sha(Path(__file__)),
                  settings=dict(max_error_parameter_mm=LIMIT_MM, optimize_vertex_positions=False),
                  geometry_admitted=False, manufacturing_authorized=False)
    (output / "native-report.json").write_text(json.dumps(report, indent=2) + "\n")


def inspect(source, candidate, output):
    import numpy as np
    import trimesh
    report = json.loads((output / "native-report.json").read_text())
    if sha(source) != report["source_sha256"] or sha(candidate) != report["candidate_sha256"]:
        raise ValueError("Surface input changed")
    if (output / "surface-report.json").exists():
        raise ValueError("Do not replace an inspection")
    original = trimesh.load_mesh(source, process=True)
    proposal = trimesh.load_mesh(candidate, process=True)
    deviations = []
    # shortcut: vertices and centroids are sampled, not a continuous Hausdorff bound.
    for target, samples in ((proposal, original.vertices), (original, proposal.vertices),
                            (proposal, original.triangles_center), (original, proposal.triangles_center)):
        maximum = 0.
        for start in range(0, len(samples), 1024):
            distances = trimesh.proximity.closest_point(target, samples[start:start + 1024])[1]
            if not np.isfinite(distances).all():
                raise ValueError("Nonfinite sampled distance")
            maximum = max(maximum, float(distances.max()))
        deviations.append(maximum)
    metrics = dict(sampled_deviations_mm=deviations, watertight=bool(proposal.is_watertight),
                   consistent_winding=bool(proposal.is_winding_consistent),
                   components=int(proposal.body_count), euler_preserved=original.euler_number == proposal.euler_number,
                   relative_volume_change=float(proposal.volume / original.volume - 1),
                   volume_mm3=float(proposal.volume), original_volume_mm3=float(original.volume),
                   trimesh_version=trimesh.__version__)
    report.update(status="surface_derivative_screen_only", independent_checks=metrics,
                  geometry_admitted=admitted(metrics), inspection_script_sha256=sha(Path(__file__)))
    (output / "surface-report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "inspect"))
    parser.add_argument("source", type=Path)
    parser.add_argument("expected_sha")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if sha(args.source) != args.expected_sha:
        raise ValueError("Unexpected source")
    if args.mode == "prepare":
        prepare(args.source, args.expected_sha, args.output)
    else:
        inspect(args.source, args.output / "coolant.stl", args.output)
