"""Localize source-indexed errors and exercise native-verifier refusal controls."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_components(faces):
    parent = np.arange(len(faces))
    uses = {}

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for index, triangle in enumerate(faces):
        for a, b in zip(triangle, np.roll(triangle, 1)):
            edge = tuple(sorted((int(a), int(b))))
            if edge in uses:
                parent[find(index)] = find(uses[edge][0])
            uses.setdefault(edge, []).append(index)
    return np.array([find(index) for index in range(len(faces))]), uses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("trial", "verification", "arrays", "paper", "preparation", "output", "cad-python"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Existing residual audit refused")
    plan = json.loads((args.trial / "plan.json").read_text())
    verification = json.loads((args.verification / "verification.json").read_text())
    if verification["correspondence_gate_passed"] or digest(args.arrays) != plan["input_sha256"]["arrays"]:
        raise SystemExit("Expected a rejected candidate and original acquired arrays")
    if digest(args.trial / "candidate-private.npz") != verification["candidate_sha256"]:
        raise SystemExit("Candidate no longer matches independent verification")
    with np.load(args.arrays, allow_pickle=False) as data:
        vertices, triangles = data["vertices"], data["triangles"]
    with np.load(args.trial / "candidate-private.npz", allow_pickle=False) as data:
        selected = data["selected_source_faces"]
    faces = triangles[selected]
    with np.load(args.verification / "native-errors-private.npz", allow_pickle=False) as data:
        ids = data["source_vertex_ids"]
        correspondence, projection = data["correspondence_error_mm"], data["native_projection_error_mm"]
    if not np.array_equal(ids, np.unique(faces)):
        raise SystemExit("Native-error source IDs changed")
    local = np.searchsorted(ids, faces)
    limit = plan["point_correspondence_limit_mm"]
    bad = correspondence > limit
    bad_faces = bad[local].any(axis=1)
    labels, edges = source_components(faces)
    components = []
    for group in np.unique(labels):
        subset = labels == group
        used = np.unique(local[subset])
        components.append({"faces": int(subset.sum()), "vertices": len(used),
                           "vertices_over_limit": int(bad[used].sum()),
                           "faces_incident_to_over_limit_vertices": int(bad_faces[subset].sum())})
    points = vertices[faces]
    normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    length = np.linalg.norm(normals, axis=1)
    if np.any(length == 0):
        raise SystemExit("Unexpected degenerate source face")
    normals /= length[:, None]
    pairs = np.array([use for use in edges.values() if len(use) == 2], dtype=int)
    angles = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", normals[pairs[:, 0]], normals[pairs[:, 1]]), -1, 1)))
    args.output.mkdir(parents=True)
    np.savez_compressed(args.output / "residual-localization-private.npz",
                        selected_source_face_ids=selected, source_vertex_ids=ids,
                        component_labels=labels, vertices_over_limit=bad,
                        faces_incident_to_over_limit_vertices=bad_faces)
    controls = {}
    verifier = Path(__file__).with_name("verify_periodic_wall.py")
    with tempfile.TemporaryDirectory(prefix="935-periodic-refusals-") as directory:
        temporary = Path(directory)
        cases = ("changed_source_membership", "forged_maximum_score", "existing_output")
        for name in cases:
            trial = temporary / name
            trial.mkdir()
            for filename in ("plan.json", "candidate-private.npz", "fit-report.json"):
                shutil.copy2(args.trial / filename, trial / filename)
            output = temporary / (name + "-output")
            if name == "changed_source_membership":
                with np.load(trial / "candidate-private.npz", allow_pickle=False) as data:
                    candidate = {key: data[key].copy() for key in data.files}
                candidate["source_vertex_ids"][0] += 1
                np.savez_compressed(trial / "candidate-private.npz", **candidate)
                expected = "Source membership mismatch"
            elif name == "forged_maximum_score":
                report = json.loads((trial / "fit-report.json").read_text())
                report["all_source"]["maximum_mm"] = 0
                report["correspondence_screen_passed"] = True
                (trial / "fit-report.json").write_text(json.dumps(report))
                expected = "Native geometry disagrees"
            else:
                output.mkdir()
                (output / "sentinel.txt").write_text("existing output must stay unchanged\n")
                expected = "Existing verification directory refused"
            command = [str(args.cad_python), str(verifier), "--trial", str(trial),
                       "--arrays", str(args.arrays), "--paper", str(args.paper),
                       "--preparation", str(args.preparation), "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            (args.output / (name + ".log")).write_text(result.stdout + result.stderr)
            passed = result.returncode != 0 and expected in result.stderr and not (output / "verification.json").exists()
            if name == "changed_source_membership":
                passed = passed and not output.exists()
            if name == "existing_output":
                passed = passed and (output / "sentinel.txt").read_text() == "existing output must stay unchanged\n"
            controls[name] = bool(passed)
    if not all(controls.values()):
        raise ValueError("Native verifier refusal controls failed")
    report = {"source_faces": len(faces), "source_vertices": len(ids),
              "components": sorted(components, key=lambda item: item["faces"], reverse=True),
              "components_with_over_limit_vertices": sum(c["vertices_over_limit"] > 0 for c in components),
              "faces_incident_to_over_limit_vertices": int(bad_faces.sum()),
              "faces_with_all_three_vertices_over_limit": int(bad[local].all(axis=1).sum()),
              "source_boundary_edges": sum(len(use) == 1 for use in edges.values()),
              "nonmanifold_source_edges": sum(len(use) > 2 for use in edges.values()),
              "source_internal_dihedral_p95_degrees": float(np.quantile(angles, 0.95)),
              "source_internal_edges_over_30_degrees": int((angles > 30).sum()),
              "native_projection_vertices_over_limit": int((projection > limit).sum()),
              "refusal_controls": controls, "verifier_source_sha256": digest(verifier),
              "audit_source_sha256": digest(__file__),
              "interpretation": "Residuals describe this rejected smooth model, not defects or deletable outliers in the acquired specimen.",
              "source_geometry_changed": False, "baseline_replaced": False,
              "physical_acceptance": False, "manufacturing_authorized": False}
    with (args.output / "audit.json").open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
