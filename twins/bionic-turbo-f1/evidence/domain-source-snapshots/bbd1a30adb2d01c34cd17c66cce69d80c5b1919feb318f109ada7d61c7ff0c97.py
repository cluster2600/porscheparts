"""Read-only reconstruction of OpenCFD v2406 face-plane concavity diagnostics."""
from pathlib import Path
import hashlib
import json
import re
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "twins/bionic-turbo-f1/cfd"))
from run_case import label_list

SOURCE_ROOT = "https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/"
SOURCES = [SOURCE_ROOT + "src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/" + name
           for name in ("primitiveMeshTools.C", "primitiveMeshCheck.C")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def body(path):
    raw = path.read_text()
    if not re.search(r"\bformat\s+ascii\s*;", raw):
        raise ValueError("ASCII mesh required")
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", raw, flags=re.S)
    m = re.search(r"\}\s*(\d+)\s*\((.*)\)\s*$", clean, re.S)
    if not m:
        raise ValueError(f"Cannot parse {path}")
    return int(m[1]), m[2]


def face_geometry(vertices):
    """primitiveMeshTools::makeFaceCentresAndAreas, double precision."""
    n = vertices.shape[1]
    mean = np.sum(vertices, axis=1) / n
    if n == 3:
        return mean, 0.5 * np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    normals = np.cross(np.roll(vertices, -1, axis=1) - vertices, mean[:, None, :] - vertices)
    weights = np.linalg.norm(normals, axis=2)
    total = weights.sum(axis=1)
    if np.any(total < 1e-150):
        raise ValueError("Zero face area")
    centers = ((vertices + np.roll(vertices, -1, axis=1) + mean[:, None, :]) * weights[:, :, None]).sum(axis=1) / (3 * total[:, None])
    return centers, 0.5 * normals.sum(axis=1)


def summary(values):
    return {str(q): float(np.percentile(values, q)) for q in (0, 50, 90, 95, 99, 100)}


def main(case, output):
    if output.exists():
        raise ValueError("Refusing to overwrite diagnostic")
    mesh = case / "constant/polyMesh"
    inputs = [mesh / n for n in ("points", "faces", "owner", "neighbour", "sets/concaveCells", "cellLevel")]
    hashes = {str(p.relative_to(case)): sha(p) for p in inputs}
    hashes["log.checkMesh"] = sha(case / "log.checkMesh")
    npoints, text = body(mesh / "points")
    points = np.fromstring(text.translate(str.maketrans({"(": " ", ")": " "})), sep=" ").reshape(-1, 3)
    assert len(points) == npoints
    nf, text = body(mesh / "faces")
    face_tokens = np.fromstring(text.translate(str.maketrans({"(": " ", ")": " "})), dtype=np.int64, sep=" ")
    faces, cursor = [], 0
    for _ in range(nf):
        n = face_tokens[cursor]
        faces.append(face_tokens[cursor + 1:cursor + 1 + n])
        cursor += 1 + n
    assert cursor == len(face_tokens)
    owners = np.array(label_list((mesh / "owner").read_text()))
    neighbours = np.array(label_list((mesh / "neighbour").read_text()))
    expected = np.array(label_list((mesh / "sets/concaveCells").read_text()))
    levels = np.array(label_list((mesh / "cellLevel").read_text()))
    nc = int(max(owners.max(), neighbours.max()) + 1)
    assert len(owners) == nf and len(levels) == nc
    centers = np.empty((nf, 3)); areas = np.empty((nf, 3))
    valences = np.array([len(f) for f in faces])
    for n in np.unique(valences):
        ids = np.flatnonzero(valences == n)
        for start in range(0, len(ids), 10000):
            group = ids[start:start + 10000]
            vertices = points[np.array([faces[i] for i in group])]
            centers[group], areas[group] = face_geometry(vertices)
    normals = areas / np.linalg.norm(areas, axis=1)[:, None]
    cell_labels = np.concatenate([owners, neighbours])
    face_labels = np.concatenate([np.arange(nf), np.arange(len(neighbours))])
    order = np.argsort(cell_labels, kind="stable")
    counts = np.bincount(cell_labels, minlength=nc)
    starts = np.concatenate([[0], counts.cumsum()])
    adjacency = face_labels[order]
    qmax = np.empty(nc); dmax = np.empty(nc); edge_pair = np.empty((nc, 2), dtype=np.int64)
    estimate = np.empty((nc, 3)); volumes = np.empty(nc)
    for n in np.unique(counts):
        cellids = np.flatnonzero(counts == n)
        for start in range(0, len(cellids), 5000):
            ids = cellids[start:start + 5000]
            fi = adjacency[starts[ids, None] + np.arange(n)]
            fc = centers[fi]
            outward = np.where(owners[fi] == ids[:, None], 1, -1)
            normal = normals[fi] * outward[:, :, None]
            delta = fc[:, None, :, :] - fc[:, :, None, :]
            distance = np.einsum("nijk,nik->nij", delta, normal)
            norm = np.maximum(np.linalg.norm(delta, axis=3), 1e-300)
            cosine = distance / norm
            diagonal = np.arange(n)
            cosine[:, diagonal, diagonal] = -np.inf
            distance[:, diagonal, diagonal] = -np.inf
            qmax[ids] = cosine.max(axis=(1, 2))
            dmax[ids] = distance.max(axis=(1, 2))
            pair = np.argmax(distance.reshape(len(ids), -1), axis=1)
            edge_pair[ids, 0] = fi[np.arange(len(ids)), pair // n]
            edge_pair[ids, 1] = fi[np.arange(len(ids)), pair % n]
            ce = fc.mean(axis=1)
            pv3 = np.einsum("nik,nik->ni", areas[fi] * outward[:, :, None], fc - ce[:, None, :])
            volumes[ids] = pv3.sum(axis=1) / 3
            estimate[ids] = np.einsum("ni,nik->nk", pv3, .75 * fc + .25 * ce[:, None, :]) / pv3.sum(axis=1)[:, None]
    flagged = np.flatnonzero(qmax > -1e-6)
    exact_match = np.array_equal(np.sort(expected), flagged)
    near = flagged[qmax[flagged] <= 1e-6]
    positive = flagged[qmax[flagged] > 1e-6]
    boundary_cells = set(owners[len(neighbours):].tolist())
    transition_cells = set(owners[:len(neighbours)][levels[owners[:len(neighbours)]] != levels[neighbours]].tolist())
    transition_cells.update(neighbours[levels[owners[:len(neighbours)]] != levels[neighbours]].tolist())
    worst = flagged[np.argsort(dmax[flagged])[-12:][::-1]]
    rows = []
    for c in flagged:
        rows.append({"cell": int(c), "q_max": float(qmax[c]), "penetration_max_mm": float(dmax[c] * 1000),
                     "penetration_over_cuberoot_volume": float(max(dmax[c], 0) / np.cbrt(volumes[c])),
                     "volume_mm3": float(volumes[c] * 1e9), "center_mm": (estimate[c] * 1000).tolist(),
                     "face_count": int(counts[c]), "cell_level": int(levels[c]),
                     "boundary_adjacent": int(c) in boundary_cells, "refinement_transition_adjacent": int(c) in transition_cells,
                     "max_penetration_faces": edge_pair[c].tolist(),
                     "classification": "near_coplanar_q_within_1e-6" if qmax[c] <= 1e-6 else "positive_face_plane_penetration"})
    for name, old in hashes.items():
        if sha(case / name) != old:
            raise ValueError("Mesh input changed during diagnostic")
    result = {
        "status": "diagnostic_only", "mesh_gate_changed": False, "performance_validated": False,
        "case": str(case.resolve()), "input_sha256": hashes, "script_sha256": sha(Path(__file__)),
        "source_urls": SOURCES, "source_version": "OpenCFD v2406",
        "method": "Face centers/areas reproduce primitiveMeshTools central triangulation. Outward area normals follow owner/neighbour. All ordered distinct face pairs tested. q=(Cf_j-Cf_i).n_i/|Cf_j-Cf_i|; d=(Cf_j-Cf_i).n_i. q>-1e-6 reproduces checkConcaveCells.",
        "diagnostic_bands_not_acceptance_criteria": "q in (-1e-6,+1e-6] is near coplanar, q>+1e-6 is positive penetration outside that band. Neither band establishes solver accuracy or authorizes a mesh.",
        "counts": {"cells": nc, "flagged": len(flagged), "native_flagged": len(expected), "near_coplanar": len(near), "positive_penetration": len(positive),
                   "positive_boundary_adjacent": sum(int(c) in boundary_cells for c in positive),
                   "positive_refinement_transition_adjacent": sum(int(c) in transition_cells for c in positive)},
        "native_cell_set_exactly_reproduced": exact_match,
        "native_ids_not_reproduced": np.setdiff1d(expected, flagged).tolist(),
        "new_ids_not_native": np.setdiff1d(flagged, expected).tolist(),
        "flagged_q_percentiles": summary(qmax[flagged]),
        "flagged_penetration_mm_percentiles": summary(dmax[flagged] * 1000),
        "near_coplanar_penetration_max_mm": float(dmax[near].max() * 1000) if len(near) else None,
        "positive_penetration_mm_counts_over": {str(t): int(np.count_nonzero(dmax[flagged] * 1000 > t)) for t in (0, 1e-6, .001, .01, .05, .1, .25)},
        "reconstructed_total_volume_m3": float(volumes.sum()), "reconstructed_min_volume_m3": float(volumes.min()),
        "worst_penetration_cell_ids": worst.tolist(), "flagged_cells": rows,
        "limitations": ["Checks centers against face planes; this is not exhaustive polyhedron convexity or self-intersection validation.",
                        "ASCII points use the saved precision; exact agreement with the native cell set is checked independently.",
                        "No mesh geometry, quality gate, solver input or physical result is modified."]}
    with output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ("counts", "native_cell_set_exactly_reproduced", "flagged_q_percentiles", "flagged_penetration_mm_percentiles", "positive_penetration_mm_counts_over")}, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
