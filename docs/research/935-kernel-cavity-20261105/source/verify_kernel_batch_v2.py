"""Verify and pack disjoint retained centroid and new kernel-point cavities."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def save(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "prepared", "recovered", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    base = args.repository/"docs/research"
    geometry = load(base/"935-residual-source-admission-20261105/source/convex_partition_contract.py", "batch_verified_geometry", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    contract = load(base/"935-signed-partition-20261105/source/centroid_star_contract.py", "batch_shared_contract", "0983f355f6983a3d5611144362871f404e969bd5f11e6ad7889a0fce35b054bb")
    verifier = load(base/"935-signed-partition-20261105/source/verify_centroid_cavity.py", "batch_independent_Fraction_verifier", "17f11125eefc470fabb061d39d1d5e397f3621a301059e87baf95924d52df0a7")
    oracle = load(base/"935-residual-source-admission-20261105/source/verify_partition_flips.py", "batch_independent_planes", "beb8cde3ec10a526726c117c38e9cdc029c3eab6f325a80dfe32b61a1ea57301")
    condition = load(base/"935-native-solver-admission-20261105/source/inspect_metric_disagreement.py", "batch_independent_condition", "df44407d6d808729fc9cf00f079a6b21ff30260b584b5dec1d9dec064416d64e")
    kernel_witness = load(Path(__file__).with_name("verify_kernel_witness.py"), "independent_kernel_witnesses", "527bef925a4b871d4c854020ab47ff79cba7dd06c26fab23e4ad2e3b2e122499")
    dual_controls = kernel_witness.controls()
    assert sha(args.reference) == "27dde093e6fedc8ccc474725e121877d9a183ac83c57900d68a1aadbcbc873e7"
    with np.load(args.reference, allow_pickle=False) as data:
        control_nodes, control_old, control_augmented, control_new = data["source_nodes"], data["old_cells"], data["reference_nodes"], data["reference_cells"]
    _, ideal, _, _, planes, _ = kernel_witness.cone(control_nodes, control_old, control_augmented[-1], control_new, contract, geometry, oracle, verifier)
    assert ideal == (F(0), F(103, 144)+F(1, 1 << 26), F(0)) and len(planes) == 81
    for bad in (control_new[:, [0, 2, 1, 3]], control_new[[0, 0, *range(2, 12)]]):
        try:
            kernel_witness.cone(control_nodes, control_old, control_augmented[-1], bad, contract, geometry, oracle, verifier)
        except AssertionError:
            pass
        else:
            raise AssertionError("Forged control accepted")
    save(args.output/"controls.json", {"literal_concave_reference_passed": True, "independent_fraction_planes": 81, "reversed_and_duplicate_cells_refused": True, **dual_controls})
    job_path = args.prepared/"job.json"; job = json.loads(job_path.read_text())
    terminal = json.loads((args.recovered/"terminal.json").read_text())
    assert terminal["complete"] and terminal["case_filter"] is None and terminal["all_owned_workers_joined"]
    assert terminal["job_sha256"] == sha(job_path) and terminal["cases_completed"] == len(job["cases"])
    for row in json.loads((args.recovered/"manifest.json").read_text())["files"]:
        assert Path(row["path"]).name == row["path"] and sha(args.recovered/row["path"]) == row["sha256"]
    for row in job["files"]:
        assert sha(args.prepared/row["path"]) == row["sha256"]
    mesh = args.parent/"partition-verification/candidate.npz"
    assert sha(mesh) == job["source_mesh_sha256"] == "1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d"
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    values_path = args.parent/"partition-whole-condition/private-exact-severe-values.json"
    assert sha(values_path) == "e339ca30c5ebf16f68dbaa5a14fe059df9a4de09f3069f0c1a1176f75b8a1878"
    values = {r["cell_id"]: F(*map(int, r["reciprocal_frobenius_squared"])) for r in json.loads(values_path.read_text())}
    targets = sorted((i for i, q in values.items() if q <= F(1, 10**32)), key=lambda i: (values[i], i))
    assert len(targets) == 26
    admitted = []; kernel_audits = []
    for row in job["cases"]:
        case = json.loads((args.prepared/row["path"]).read_text())
        result = json.loads((args.recovered/(row["case_id"]+".json")).read_text())
        assert result["input_sha256"] == sha(args.prepared/row["path"]) and result["case_id"] == case["case_id"]
        if result.get("center_method") == "fixed_highs_ds_Linf_kernel_proposal":
            check = kernel_witness.check(case["nodes"], contract.boundary(case["old_cells"]), result["kernel_proposal"])
            assert not result["admitted"] or check["strict_stored_point"]
            kernel_audits.append({"case_id": case["case_id"], **check})
        if result["admitted"]:
            admitted.append((case, result, set(case["source_global_cell_ids"])))
    assert len(kernel_audits) == 7
    save(args.output/"private-kernel-audits.json", kernel_audits)
    # Fixed deterministic policy: exact worst target first; cover most remaining
    # targets, then replace fewer source rows, then lexical case ID. No overlap.
    occupied = set(); selected = []
    for target in targets:
        if target in occupied:
            continue
        options = [r for r in admitted if target in r[2] and not occupied.intersection(r[2])]
        if not options:
            continue
        choice = min(options, key=lambda r: (-len(r[2].intersection(targets)), len(r[2]), r[0]["case_id"]))
        selected.append(choice); occupied.update(choice[2])
    assert selected and targets[0] in occupied
    thresholds = (1000, 10**6, 10**9, 10**12, 10**15, 2**52, 10**16, 3*2**52)
    old_bins_total = np.zeros(5, dtype=np.int64); new_bins_total = old_bins_total.copy()
    old_condition_total = np.zeros(8, dtype=np.int64); new_condition_total = old_condition_total.copy()
    points = []; replacements = []; private = []; witness_count = 0; witness_hashes = []
    for index, (case, result, source_ids) in enumerate(selected):
        ids = np.array(case["source_global_cell_ids"], dtype=np.int64)
        vertices = np.array(case["source_global_vertex_ids"], dtype=np.int64)
        assert np.array_equal(ids, np.unique(ids)) and np.array_equal(vertices, np.unique(vertices))
        local_nodes = np.array(case["nodes"], dtype=np.float64); old = np.array(case["old_cells"], dtype=np.uint32)
        assert np.array_equal(local_nodes.view(np.uint64), nodes[vertices].view(np.uint64))
        assert np.array_equal(vertices[old], cells[ids]) and source_ids == set(map(int, ids))
        point = np.array([float.fromhex(v) for v in result["new_point_hex"]], dtype=np.float64)
        new = np.array(result["new_cells"], dtype=np.uint32)
        if result.get("center_method") == "fixed_highs_ds_Linf_kernel_proposal":
            augmented, ideal, before, after, planes, proof = kernel_witness.cone(local_nodes, old, point, new, contract, geometry, oracle, verifier)
            assert result["kernel_proposal"]["point_hex"] == result["new_point_hex"]
        else:
            augmented, ideal, before, after, planes, proof = verifier.local(local_nodes, old, point, new, contract, geometry, oracle)
            assert ideal == tuple(F(*map(int, v)) for v in result["ideal_centroid"])
        assert before == result["old_bins"] and after == result["new_bins"]
        counts = []
        for coords, rows in ((local_nodes, old), (augmented, new)):
            exact_values = []
            for tet in rows:
                p = [[F.from_float(float(x)) for x in coords[v]] for v in tet]
                matrix = [[p[column+1][axis]-p[0][axis] for column in range(3)] for axis in range(3)]
                determinant, reciprocal = condition.exact_condition(matrix)
                assert determinant > 0; exact_values.append(reciprocal)
            counts.append([sum(q <= F(1, t*t) for q in exact_values) for t in thresholds])
        assert counts[0] == list(result["old_condition_counts"].values())
        assert counts[1] == list(result["new_condition_counts"].values()) and all(a >= b for a, b in zip(*counts))
        old_bins_total += before; new_bins_total += after
        old_condition_total += counts[0]; new_condition_total += counts[1]
        assert not np.any(np.all(nodes == point, axis=1))
        assert all(not np.array_equal(point.view(np.uint64), p.view(np.uint64)) for p in points)
        points.append(point)
        remap = np.append(vertices, len(nodes)+index); replacements.append(remap[new].astype(cells.dtype))
        witness = args.output/(case["case_id"]+"-private-Fraction-planes.json")
        save(witness, planes); witness_count += len(planes); witness_hashes.append(sha(witness))
        private.append({"case_id": case["case_id"], "old_cell_ids": list(map(int, ids)), "new_node_id": len(nodes)+index,
                        "new_cells": replacements[-1].tolist(), "input_sha256": result["input_sha256"], "planes_sha256": sha(witness)})
    removed = np.array(sorted(occupied), dtype=np.int64); keep = np.ones(len(cells), bool); keep[removed] = False
    augmented = np.vstack((nodes, points)); new_rows = np.concatenate(replacements); candidate = np.concatenate((cells[keep], new_rows))
    output = args.output/"candidate.npz"; np.savez_compressed(output, nodes=augmented, tets=candidate, boundary=boundary)
    with np.load(output, allow_pickle=False) as exported:
        assert np.array_equal(exported["nodes"].view(np.uint64), augmented.view(np.uint64))
        assert np.array_equal(exported["tets"], candidate) and np.array_equal(exported["boundary"], boundary)
    mapping = args.output/"private-source-map.npz"
    np.savez_compressed(mapping, replaced_source_cell_ids=removed, new_candidate_cell_ids=np.arange(keep.sum(), len(candidate), dtype=np.int64))
    save(args.output/"private-selection.json", private)
    report = {"source_sha256": sha(Path(__file__)), "parent_mesh_sha256": sha(mesh), "candidate_sha256": sha(output),
        "remote_job_sha256": sha(job_path), "proposal_cases_available": len(job["cases"]), "proposal_admitted_cases": len(admitted),
        "new_proposal_cases_executed": terminal["cases_executed_new"], "prior_proposal_cases_reused": terminal["cases_reused_without_execution"],
        "independently_checked_kernel_proposals": len(kernel_audits),
        "independent_exact_duals_checked": sum(x["exact_dual_checked"] for x in kernel_audits),
        "independent_no_strict_kernel_certificates": sum(x["no_strict_single_point_kernel_proved"] for x in kernel_audits),
        "selected_kernel_cavities": sum(r[1].get("center_method") == "fixed_highs_ds_Linf_kernel_proposal" for r in selected),
        "selected_disjoint_cavities": len(selected), "target_source_cells": len(targets), "target_source_cells_replaced": len(occupied.intersection(targets)),
        "old_cells_replaced": len(removed), "new_cells": len(new_rows), "new_numerical_interior_points": len(points),
        "nodes_before": len(nodes), "nodes_after": len(augmented), "tetrahedra_before": len(cells), "tetrahedra_after": len(candidate),
        "all_original_coordinates_bit_identical": True, "all_complete_boundary_rows_bit_identical": True,
        "all_unmodified_cell_tuples_identical": True, "independent_Fraction_point_construction_volume_and_thresholds_passed": True,
        "independent_complete_oriented_triangle_chain_equal": True, "independent_exact_separating_plane_witnesses": witness_count,
        "independent_Fraction_condition_counts_match_remote": True, "shared_source_admission_and_domain_contract_explicit": True,
        "old_local_bins": old_bins_total.tolist(), "new_local_bins": new_bins_total.tolist(),
        "old_local_condition_counts": old_condition_total.tolist(), "new_local_condition_counts": new_condition_total.tolist(),
        "private_source_map_sha256": sha(mapping), "private_selection_sha256": sha(args.output/"private-selection.json"),
        "global_intersection_status_inherited_not_exhaustively_upgraded": True,
        "whole_volume_and_fresh_complete_condition_census_required": True, "physics_admitted": False,
        "manufacturing_qualified": False, "seconds": time.monotonic()-started}
    save(args.output/"report.json", report); signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
