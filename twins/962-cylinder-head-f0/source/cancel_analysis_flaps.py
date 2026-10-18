"""Cancel only exact, zero-thickness duplicate fins in a separate VTK derivative."""
import argparse
import json
from pathlib import Path
import signal
import time

import numpy as np

from mesh_head import ROOT, FAMILY, canonical_oriented, new_output, save, sha
from prepare_head_analysis import compact_unused, validate_surface

CONTRACT = FAMILY / "engineering/analysis-flap-contract.json"
CONTRACT_SHA256 = "ab456affb552b269eeef1794dfb36437df0c1c17bbce13881ce39ee6b50e96bd"


def cancel_exact_fins(points, faces):
    """Require a two-face opposite pair, one two-face tip and a four-face attachment edge."""
    _, inverse, counts = np.unique(np.sort(faces, axis=1), axis=0,
        return_inverse=True, return_counts=True)
    incidence = np.bincount(faces.ravel(), minlength=len(points))
    remove, rows = [], []
    for duplicate in np.where(counts > 1)[0]:
        ids = np.where(inverse == duplicate)[0]
        pair = faces[ids]
        if len(ids) != 2 or not np.array_equal(canonical_oriented(pair[:1]),
                canonical_oriented(pair[1:, ::-1])):
            raise ValueError("Only exact two-face opposite oriented pairs can be cancelled")
        vertices = np.unique(pair)
        tips = vertices[incidence[vertices] == 2]
        if len(tips) != 1:
            raise ValueError("A duplicate fin requires exactly one tip used by these two faces only")
        attachment = vertices[vertices != tips[0]]
        incident = np.where(np.sum(np.isin(faces, attachment), axis=1) == 2)[0]
        if len(incident) != 4:
            raise ValueError("Fin attachment must have exactly four incident faces before cancellation")
        rows.append(dict(removed_face_indices=ids.tolist(), oriented_faces=pair.tolist(),
            tip_vertex=int(tips[0]), attachment_edge=attachment.tolist(),
            attachment_coordinates_mm=points[attachment].tolist(),
            attachment_incident_faces_before=incident.tolist(), exact_opposite_pair=True))
        remove.extend(ids.tolist())
    if not rows:
        raise ValueError("No exact duplicate fins were found; this declared method is not applicable")
    keep = np.ones(len(faces), dtype=bool); keep[remove] = False
    used = np.unique(faces[keep])
    q, g = compact_unused(points, faces[keep])
    vertex_map = np.full(len(points), -1, dtype=np.int64); vertex_map[used] = np.arange(len(used))
    face_map = np.full(len(faces), -1, dtype=np.int64); face_map[keep] = np.arange(np.sum(keep))
    if not np.array_equal(q[g], points[faces[keep]]):
        raise ValueError("Kept face coordinates or orientation changed")
    return q, g, rows, vertex_map, face_map


def run(output):
    if sha(CONTRACT) != CONTRACT_SHA256:
        raise ValueError("Frozen cancellation contract changed")
    contract = json.loads(CONTRACT.read_text())
    verify = lambda: all(sha(ROOT / p) == h for p, h in contract["input_hashes"].items())
    if not verify():
        raise ValueError("Bound source, failed candidate or diagnostic changed")
    new_output(output); signal.alarm(300); started = time.monotonic()
    (output / "source-executed.py").write_bytes(Path(__file__).read_bytes())
    report = dict(status="running", source_sha256=sha(Path(__file__)), contract_sha256=sha(CONTRACT),
        contract=contract, qualification=dict(analysis_surface_geometric_gate_passed=False,
            solver_admission_established=False, engineering_accepted=False,
            mesh_convergence_established=False, manufacturing_authorized=False))
    try:
        candidate = ROOT / "work/962-engineering/analysis-surface-025-002/analysis-surface.npz"
        arrays = np.load(candidate); p, f = arrays["points_mm"], arrays["triangles"]
        q, g, rows, vertex_map, face_map = cancel_exact_fins(p, f)
        np.savez_compressed(output / "analysis-surface.npz", points_mm=q, triangles=g)
        np.savez_compressed(output / "before-after-index-maps.npz", old_vertex_to_new=vertex_map,
            old_face_to_new=face_map, kept_old_vertices=np.where(vertex_map >= 0)[0],
            kept_old_faces=np.where(face_map >= 0)[0])
        report.update(pairs=rows, vertices_before=len(p), triangles_before=len(f),
            vertices_after=len(q), triangles_after=len(g), removed_faces=int(np.sum(face_map < 0)),
            removed_unused_vertices=int(np.sum(vertex_map < 0)), kept_oriented_triangles_exact=True)
        if len(rows) != 8 or report["removed_faces"] != 16 or report["removed_unused_vertices"] != 8:
            raise ValueError("Observed exact fins differ from the predeclared candidate diagnosis")
        report["surface"] = validate_surface(q, g)
        if report["surface"]["euler_characteristic"] != -208:
            raise ValueError("Original Euler characteristic was not restored")
        original = json.loads((FAMILY / "derived/family/bore-95-report.json").read_text())
        original_volume = original["mesh_metrics"]["solid"]["volume_mm3"]
        report["original_volume_mm3"] = original_volume
        report["relative_volume_change_vs_original"] = report["surface"]["signed_volume_mm3"] / original_volume - 1
        report.update(status="exact_fin_cancellation_completed_independent_gates_pending")
    except Exception as exc:
        report.update(status="failed_outputs_preserved", error=type(exc).__name__+": "+str(exc))
    finally:
        report.update(wall_s=time.monotonic()-started,
            bound_inputs_unchanged=verify() and sha(CONTRACT) == CONTRACT_SHA256
                and sha(Path(__file__)) == report["source_sha256"]
                and sha(output / "source-executed.py") == report["source_sha256"],
            output_hashes={p.name: sha(p) for p in output.glob("*.npz")})
        if not report["bound_inputs_unchanged"]:
            report.update(status="failed_outputs_preserved", error="Bound inputs changed")
        save(output / "receipt.json", report); signal.alarm(0)
    print(json.dumps({k: report.get(k) for k in ("status", "wall_s", "vertices_after", "triangles_after", "error")}))
    return 0 if report["status"].startswith("exact_fin_cancellation_completed") else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output))
