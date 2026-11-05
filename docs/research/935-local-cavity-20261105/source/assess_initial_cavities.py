"""Check convexity, face admissibility, quality and packing before mesh edits."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
FACES = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
HULL = [[0, 2, 3], [0, 3, 4], [0, 4, 2], [1, 2, 3], [1, 3, 4], [1, 4, 2]]
SUPPORT = np.array([[*face, other] for face in HULL for other in range(5) if other not in face])
ALTERNATIVE = np.array([[2, 3, 4, 0], [2, 4, 3, 1]])


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def determinants(xyz, exact):
    low, high = exact.determinant_interval(xyz)
    value = np.einsum("ij,ij->i", xyz[:, 1] - xyz[:, 0], np.cross(xyz[:, 2] - xyz[:, 0], xyz[:, 3] - xyz[:, 0]))
    signs = np.where(low > 0, 1, np.where(high < 0, -1, 0)).astype(np.int8)
    ambiguous = (signs == 0) | (np.sign(value) != signs)
    for i in np.flatnonzero(ambiguous):
        precise = exact.exact_determinant(xyz[i])
        value[i] = float(precise)
        signs[i] = (precise > 0) - (precise < 0)
    return value, signs, int(ambiguous.sum())


def quality(xyz, exact):
    determinant, signs, fallback = determinants(xyz, exact)
    volume = np.abs(determinant) / 6
    edge_sum = sum(np.sum((xyz[:, i] - xyz[:, j]) ** 2, axis=1) for i, j in PAIRS)
    return 12 * (3 * volume) ** (2 / 3) / edge_sum, signs, fallback


def convex(points, exact):
    _, signs, fallback = determinants(points[:, SUPPORT].reshape(-1, 4, 3), exact)
    signs = signs.reshape(-1, 6, 2)
    return np.all(signs[:, :, 0] * signs[:, :, 1] > 0, axis=1), fallback


def boundary_chain_equal(old, new):
    faces = np.concatenate((old[:, :, FACES].reshape(-1, 12, 3), new[:, :, FACES].reshape(-1, 8, 3)), axis=1)
    inversions = ((faces[:, :, 0] > faces[:, :, 1]).astype(np.int8)
                  + (faces[:, :, 0] > faces[:, :, 2]).astype(np.int8)
                  + (faces[:, :, 1] > faces[:, :, 2]).astype(np.int8))
    signs = 1 - 2 * (inversions % 2)
    signs[:, 12:] *= -1
    ordered_faces = np.sort(faces, axis=2)
    order = np.lexsort((ordered_faces[:, :, 2], ordered_faces[:, :, 1], ordered_faces[:, :, 0]), axis=1)
    ordered_faces = np.take_along_axis(ordered_faces, order[:, :, None], axis=1)
    signs = np.take_along_axis(signs, order, axis=1)
    pairs_equal = np.all(ordered_faces[:, ::2] == ordered_faces[:, 1::2], axis=(1, 2))
    distinct_pairs = np.all(np.any(ordered_faces[:, 2::2] != ordered_faces[:, :-2:2], axis=2), axis=1)
    cancelled = np.all(signs[:, ::2] + signs[:, 1::2] == 0, axis=1)
    return pairs_equal & distinct_pairs & cancelled


def existing_face(outer, cells, index):
    keys, starts, counts, order = index
    options = np.array([[0, 1, 2], [0, 2, 1], [1, 2, 0]])
    pairs = outer[:, options[:, :2]]
    packed = np.minimum(pairs[:, :, 0], pairs[:, :, 1]).astype(np.uint64) * np.uint64(2**32) + np.maximum(pairs[:, :, 0], pairs[:, :, 1]).astype(np.uint64)
    positions = np.searchsorted(keys, packed)
    assert np.array_equal(keys[positions], packed)
    choice = np.argmin(counts[positions], axis=1)
    selected = positions[np.arange(len(outer)), choice]
    third = outer[np.arange(len(outer)), options[choice, 2]]
    sizes = counts[selected]
    owners = np.repeat(np.arange(len(outer)), sizes)
    offsets = np.arange(len(owners)) - np.repeat(np.cumsum(sizes) - sizes, sizes)
    incident = order[starts[selected][owners] + offsets] // 6
    present = np.any(cells[incident] == third[owners, None], axis=1)
    result = np.zeros(len(outer), dtype=bool)
    np.logical_or.at(result, owners, present)
    return result


def pack(rows, faces, gains, keys, cell_count):
    occupied = np.zeros(cell_count, dtype=bool)
    accepted, created = [], set()
    overlap = duplicate_face = 0
    for i in np.lexsort((keys, -gains)):
        if occupied[rows[i]].any():
            overlap += 1
            continue
        face = tuple(map(int, faces[i]))
        if face in created:
            duplicate_face += 1
            continue
        occupied[rows[i]] = True
        created.add(face)
        accepted.append(int(i))
    return np.asarray(accepted, dtype=np.int64), overlap, duplicate_face


def controls(path, exact):
    assert sha(path) == "2051ab4e59bddb09cc1066f90105144c6c6a0c552c92af4bfc7d5a25b94374b3"
    with np.load(path, allow_pickle=False) as data:
        nodes, old = data["nodes"], data["tets"]
    points = nodes[[3, 4, 0, 1, 2]][None]
    assert convex(points, exact)[0].all()
    concave = points.copy()
    concave[0, 0] = points[0, [1, 2, 3, 4]].mean(axis=0)
    assert not convex(concave, exact)[0].any()
    new = np.array([[[0, 1, 2, 3], [0, 2, 1, 4]]])
    _, signs, _ = quality(nodes[new].reshape(-1, 4, 3), exact)
    for i in np.flatnonzero(signs < 0):
        new.reshape(-1, 4)[i, [1, 2]] = new.reshape(-1, 4)[i, [2, 1]]
    assert boundary_chain_equal(old[None], new).all()
    forged = new.copy()
    forged[0, 0, [1, 2]] = forged[0, 0, [2, 1]]
    assert not boundary_chain_equal(old[None], forged).any()
    rows = np.array([[0, 1, 2], [2, 3, 4]])
    selected, conflict, duplicate = pack(rows, np.array([[0, 1, 2], [3, 4, 5]]), np.array([1, 2]), np.array([1, 2]), 5)
    assert selected.tolist() == [1] and conflict == 1
    selected, conflict, duplicate = pack(np.array([[0, 1, 2], [3, 4, 5]]), np.array([[0, 1, 2], [0, 1, 2]]), np.array([1, 2]), np.array([1, 2]), 6)
    assert selected.tolist() == [1] and duplicate == 1
    return {"known_convex_bipyramid_passes": True, "interior_apex_concavity_refused": True,
            "oriented_chain_and_forged_orientation_control": True,
            "overlapping_cells_and_duplicate_new_face_refused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "coverage-report", "cache", "index", "inspector", "control", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    coverage = json.loads(args.coverage_report.read_text())
    global_report = json.loads((args.index / "report.json").read_text())
    assert sha(args.mesh) == coverage["mesh_sha256"] == global_report["mesh_sha256"]
    assert sha(args.cache) == coverage["private_cavity_cache_sha256"] == global_report["cache_sha256"]
    assert sha(args.coverage_report) == global_report["coverage_report_sha256"]
    assert sha(args.inspector) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    spec = importlib.util.spec_from_file_location("frozen_cavity_quality", args.inspector)
    exact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exact)
    tests = controls(args.control, exact)
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"].astype(np.uint32)
    with np.load(args.cache, allow_pickle=False) as data:
        edge_keys, rows, outer, bad_ids = (data[key] for key in ("edge_keys", "cell_ids", "outer_vertices", "bad_cell_ids"))
    index = []
    for name in ("edge_keys", "edge_starts", "edge_counts", "edge_order"):
        path = args.index / ("private-" + name + ".npy")
        assert sha(path) == global_report["global_index_sha256"][path.name]
        index.append(np.load(path, mmap_mode="r", allow_pickle=False))
    plan = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(args.mesh),
            "cavity_cache_sha256": sha(args.cache), "initial_cavities": len(edge_keys),
            "strict_convex_hull_required": True, "exact_oriented_boundary_chain_required": True,
            "new_central_face_must_be_absent": True, "local_minimum_quality_must_not_worsen": True,
            "ultra_low_bin_must_not_increase": .0001, "bad_bin_must_strictly_decrease": .01,
            "packing": "Greedy descending integer repair gain then ascending edge key; disjoint source cells and unique new central faces",
            "mesh_modification_allowed": False, "new_paid_compute_usd": 0}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    bad = np.zeros(len(cells), dtype=bool)
    bad[bad_ids] = True
    feasible = np.zeros(len(rows), dtype=bool)
    new_cells = np.empty((len(rows), 2, 4), dtype=np.uint32)
    gain = np.zeros(len(rows), dtype=np.int64)
    hull_total = absent_total = quality_total = chain_rejected = fallback = 0
    for start in range(0, len(rows), 2000):
        stop = min(start + 2000, len(rows))
        endpoints = np.column_stack((edge_keys[start:stop] // np.uint64(2**32), edge_keys[start:stop] % np.uint64(2**32))).astype(np.uint32)
        vertices = np.column_stack((endpoints, outer[start:stop]))
        hull, extra = convex(nodes[vertices], exact)
        fallback += extra
        proposed = vertices[:, ALTERNATIVE].copy()
        new_quality, signs, extra = quality(nodes[proposed].reshape(-1, 4, 3), exact)
        fallback += extra
        flat = proposed.reshape(-1, 4)
        negative = signs < 0
        flat[negative] = flat[negative][:, [0, 2, 1, 3]]
        new_quality = new_quality.reshape(-1, 2)
        old = cells[rows[start:stop]]
        old_quality, old_signs, extra = quality(nodes[old].reshape(-1, 4, 3), exact)
        fallback += extra
        assert np.all(old_signs > 0)
        old_quality = old_quality.reshape(-1, 3)
        assert np.array_equal(old_quality < .01, bad[rows[start:stop]])
        improvement = (old_quality < .01).sum(axis=1) - (new_quality < .01).sum(axis=1)
        good_quality = ((new_quality.min(axis=1) >= old_quality.min(axis=1)) & (improvement > 0)
                        & ((new_quality < .0001).sum(axis=1) <= (old_quality < .0001).sum(axis=1))
                        & np.all(signs.reshape(-1, 2) != 0, axis=1))
        absent = ~existing_face(outer[start:stop], cells, index)
        chain = boundary_chain_equal(old, proposed)
        feasible[start:stop] = hull & good_quality & absent & chain
        new_cells[start:stop] = proposed
        gain[start:stop] = improvement
        hull_total += int(hull.sum())
        absent_total += int((hull & absent).sum())
        quality_total += int((hull & absent & good_quality).sum())
        chain_rejected += int((hull & ~chain).sum())
    eligible = np.flatnonzero(feasible)
    selected, overlap, duplicate_face = pack(rows[eligible], outer[eligible], gain[eligible], edge_keys[eligible], len(cells))
    selected = eligible[selected]
    predicted_gain = int(gain[selected].sum())
    optimistic_gain = int(gain[eligible].sum())
    covered = np.unique(rows[eligible].ravel())
    optimistic_gain = min(optimistic_gain, int(bad[covered].sum()))
    proposal = args.output / "private-packed-proposal.npz"
    np.savez_compressed(proposal, edge_keys=edge_keys[selected], old_cell_ids=rows[selected],
                        new_cells=new_cells[selected], repair_gains=gain[selected])
    result = {**plan, "coverage_report_sha256": sha(args.coverage_report), "global_report_sha256": sha(args.index / "report.json"),
              "controls": tests, "strict_convex_cavities": hull_total, "convex_with_absent_central_face": absent_total,
              "convex_absent_and_quality_improving": quality_total, "convex_boundary_chain_failures": chain_rejected,
              "admissible_initial_cavities": len(eligible), "optimistic_any_initial_packing_gain_upper_bound": optimistic_gain,
              "greedy_packed_cavities": len(selected), "greedy_packed_bad_cell_repair_gain": predicted_gain,
              "packing_cell_conflicts": overlap, "packing_duplicate_new_faces": duplicate_face,
              "required_repairs": coverage["required_bad_cell_repairs"],
              "optimistic_admissible_initial_pass_target_reachable": optimistic_gain >= coverage["required_bad_cell_repairs"],
              "greedy_packed_initial_target_passed": predicted_gain >= coverage["required_bad_cell_repairs"],
              "predicted_bad_cells_if_applied": int(bad.sum()) - predicted_gain,
              "exact_sign_fallbacks_including_controls_excluded": fallback,
              "packed_proposal_sha256": sha(proposal), "coordinates_modified": False, "connectivity_modified": False,
              "dynamic_sequences_or_other_valences_not_excluded": True,
              "physics_admitted": False, "manufacturing_qualified": False, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
