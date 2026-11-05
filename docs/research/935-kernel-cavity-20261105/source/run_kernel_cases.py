"""Try one fixed kernel construction only on previously uncovered extreme cases."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import signal
import time


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
    for name in ("repository", "parent", "previous", "control", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(120); started = time.monotonic()
    controls = json.loads((args.control/"report.json").read_text())
    kernel_path = Path(__file__).with_name("kernel_point.py")
    assert controls["kernel_source_sha256"] == sha(kernel_path) == "fdadd4986fd630843a07edfe280884beed9076a2f869ddca8ca50d010f254933"
    assert controls["literal_reference_and_proposed_cone_exact_volume_domain_and_quality_passed"]
    assert controls["negative_and_zero_width_exact_dual_bounds_passed"]
    assert sha(args.control/"literal-kernel-reference.npz") == controls["reference_sha256"]
    kernel = load(kernel_path, "fixed_kernel_proposer", controls["kernel_source_sha256"])
    assert sha(args.previous/"manifest.json") == "699cc762a0448f31e44099d34274dcfa7af938c33e1012b0669eaa896ec7b082"
    prepared = args.previous/"prepared"; prior = args.previous/"cloud-003/recovered/results"
    job_path = prepared/"job.json"; job = json.loads(job_path.read_text())
    assert sha(job_path) == "07f74999d6bd8232a25ddf36ab873ee28a176fb1fb0a7afda0557a6709030a53"
    for row in job["files"]:
        assert sha(prepared/row["path"]) == row["sha256"]
    for row in json.loads((prior/"manifest.json").read_text())["files"]:
        assert sha(prior/row["path"]) == row["sha256"]
    worker = load(prepared/"exact_cavity_worker.py", "retained_exact_condition_worker", "c1647d26211fee6445361fb140cea503a4ef7414cea2410a620aabbadf5ec922")
    geometry = load(prepared/"geometry_primitives.py", "kernel_case_geometry", worker.GEOMETRY_SHA)
    contract = load(prepared/"centroid_contract.py", "kernel_case_shared_domain", worker.CONTRACT_SHA)
    source_values = args.parent/"partition-whole-condition/private-exact-severe-values.json"
    assert sha(source_values) == "e339ca30c5ebf16f68dbaa5a14fe059df9a4de09f3069f0c1a1176f75b8a1878"
    values = {r["cell_id"]: F(*map(int, r["reciprocal_frobenius_squared"])) for r in json.loads(source_values.read_text())}
    targets = {i for i, q in values.items() if q*10**32 <= 1}; assert len(targets) == 26
    selection = json.loads((args.previous/"verification/private-selection.json").read_text())
    occupied = {i for case in selection for i in case["old_cell_ids"]}; missing = sorted(targets-occupied)
    assert len(missing) == 2
    results = []; executed = []; refusals = Counter(); dual_refusals = 0
    for row in job["cases"]:
        source = prepared/row["path"]; case = json.loads(source.read_text())
        previous = prior/(row["case_id"]+".json"); inherited = json.loads(previous.read_text())
        assert inherited["input_sha256"] == sha(source)
        destination = args.output/previous.name
        if not set(missing).intersection(case["source_global_cell_ids"]):
            shutil.copyfile(previous, destination); results.append(inherited); continue
        assert not inherited["admitted"], "New trial unexpectedly replaces an already admitted target proposal"
        result = {"case_id": case["case_id"], "input_sha256": sha(source), "admitted": False,
                  "source_mesh_sha256": case["source_mesh_sha256"], "center_method": "fixed_highs_ds_Linf_kernel_proposal",
                  "prior_centroid_result_sha256": sha(previous), "physics_admitted": False, "manufacturing_qualified": False}
        before = time.monotonic()
        try:
            nodes, old = case["nodes"], case["old_cells"]
            assert worker.coordinate_digest(nodes) == case["coordinates_f64_sha256"]
            assert worker.cell_digest(old) == case["cells_u32_sha256"]
            faces, _, _ = contract.source_admission(nodes, old, geometry)
            proposal = kernel.propose(nodes, faces, geometry); result["kernel_proposal"] = proposal
            dual = proposal["exact_dual"]
            if dual is not None and dual["no_strict_kernel_proved"]:
                dual_refusals += 1
                raise AssertionError("Exact nonpositive dual bound excludes every strict single-point cavity kernel")
            assert proposal["strict_kernel_for_stored_point"], "Once-rounded proposed point fails strict kernel admission"
            point = [float.fromhex(x) for x in proposal["point_hex"]]; augmented = nodes+[point]
            new = [[len(nodes), *face] for face in faces]
            proof = contract.certify(augmented, old, new, geometry)
            old_counts = worker.condition_counts(nodes, old, geometry)
            new_counts = worker.condition_counts(augmented, new, geometry)
            assert all(a >= b for a, b in zip(old_counts, new_counts)), "An exact condition threshold worsens"
            result.update(admitted=True, verdict="exact_local_kernel_partition_passed_pending_independent_global_verification",
                          old_cells=len(old), new_cells=new, new_point_hex=proposal["point_hex"],
                          exact_domain_volume=[str(proof["exact_domain_volume"].numerator), str(proof["exact_domain_volume"].denominator)],
                          old_bins=proof["old_bins"], new_bins=proof["new_bins"],
                          old_condition_counts=dict(zip(worker.LABELS, old_counts)), new_condition_counts=dict(zip(worker.LABELS, new_counts)),
                          new_minimum_quality_approx=float(proof["new_minimum_quality_cubed"])**(1/3),
                          old_pair_separations=proof["old_pair_separations"], new_pair_separations=proof["new_pair_separations"],
                          new_points=1, unchanged_complete_boundary=True, all_original_points_retained=True)
        except AssertionError as error:
            result.update(verdict="candidate_refused", reason=str(error) or "fixed_source_contract")
            refusals[result["reason"]] += 1
        result["seconds"] = time.monotonic()-before
        save(destination, result); results.append(result); executed.append(case["case_id"])
    assert len(executed) == 7 and len(results) == 131
    for row in job["files"]:
        assert sha(prepared/row["path"]) == row["sha256"]
    assert sha(job_path) == "07f74999d6bd8232a25ddf36ab873ee28a176fb1fb0a7afda0557a6709030a53"
    save(args.output/"private-target-review.json", {"uncovered_source_targets": missing, "new_trial_case_ids": executed})
    summary = {"source_sha256": sha(Path(__file__)), "kernel_source_sha256": sha(kernel_path), "job_sha256": sha(job_path),
               "complete": True, "case_filter": None, "cases_completed": len(results),
               "cases_executed_new": len(executed), "cases_reused_without_execution": len(results)-len(executed),
               "new_admitted_cases": sum(r["admitted"] for r in results if r["case_id"] in executed),
               "cases_admitted": sum(r["admitted"] for r in results), "exact_dual_no_strict_kernel_certificates": dual_refusals,
               "new_refusal_counts": dict(refusals), "all_owned_workers_joined": True, "workers": 1,
               "source_inputs_rehashed_unchanged": True, "mixed_centroid_and_kernel_proposals_share_parent_not_cumulative": True,
               "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
               "seconds": time.monotonic()-started}
    save(args.output/"terminal.json", summary)
    files = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(args.output.iterdir()) if p.is_file()]
    save(args.output/"manifest.json", {"files": files, "complete": True})
    signal.alarm(0); print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
