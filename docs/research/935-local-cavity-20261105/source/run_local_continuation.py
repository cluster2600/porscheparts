"""Finish the predeclared, at-most-three-pass local topology experiment."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "repository", "python", "scientific-site", "input-mesh", "input-report",
                 "original", "surface", "surface-report", "control"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).parent
    helper = args.repository / "docs/research/935-volume-optimization-20261105/source/run_optimization.py"
    spec = importlib.util.spec_from_file_location("retained_local_iteration_bounds", helper)
    bounded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bounded)
    sha, save = bounded.sha, bounded.save
    assert sha(helper) == "674e984510d9429d4a92ac5609aa618b5c86d476cd4f18175f357958523dbda2"
    assert sha(args.input_mesh) == "cdecefa2f2bda0eafb11cc00076dc38b375614f22585be37b260541c74b78836"
    assert sha(args.input_report) == "33b697f0757c40f5a891340045e9970e0035a178376ebf510353846e28577b19"
    inspector = args.repository / "docs/research/935-unoptimized-volume-20261105/source/inspect_interval_volume.py"
    frozen = args.repository / "docs/research/935-local-physics-20261105/source/inspect_tetrahedra.py"
    assert sha(inspector) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    assert sha(frozen) == "fe8c7fa88f35d2d14094438bbae3b0860bde085a39b68f7ab941790cb4d1bec3"
    assert not (args.root / "iteration-plan.json").exists()
    save(args.root / "iteration-plan.json", {"source_sha256": sha(Path(__file__)), "first_pass_already_checked": True,
         "maximum_declared_passes": 3, "additional_wall_budget_seconds": 900, "original_bad_cells": 526110,
         "unchanged_target_bad_cell_limit": 263055, "new_paid_compute_usd": 0, "physics_admitted": False})
    deadline = time.monotonic() + 900
    env = os.environ.copy()
    env["PYTHONPATH"] = str(args.scientific_site)
    current, current_report = args.input_mesh, args.input_report
    state = {"physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0}
    for iteration in (2, 3):
        before = json.loads(current_report.read_text())
        phase = args.root / ("pass-" + str(iteration).zfill(3))
        phase.mkdir(mode=0o700, exist_ok=False)
        construction = phase / "construction"
        tasks = [("construction", [str(source / "construct_iterated_pass.py"), "--mesh", str(current), "--mesh-report", str(current_report),
            "--original", str(args.original), "--surface", str(args.surface), "--core-dir", str(source), "--inspector", str(inspector),
            "--control", str(args.control), "--iteration", str(iteration), "--output", str(construction)]),
            ("local-proof", [str(source / "verify_iterated_domains.py"), "--source", str(current), "--source-report", str(current_report),
            "--construction-report", str(construction / "report.json"), "--candidate", str(construction / "candidate.npz"),
            "--proposal", str(construction / "proposal.npz"), "--inspector", str(inspector), "--control", str(args.control), "--output", str(phase / "local-proof")]),
            ("whole-volume", [str(inspector), "--mesh", str(construction / "candidate.npz"), "--surface", str(args.surface),
            "--surface-report", str(args.surface_report), "--frozen-inspector", str(frozen), "--output", str(phase / "whole-volume")])]
        for name, command in tasks:
            remaining = int(deadline - time.monotonic())
            if remaining < 30:
                save(args.root / "iteration-terminal.json", {**state, "terminal": "iteration_budget_exhausted", "iteration": iteration, "stage": name})
                return
            done = bounded.run(args.root, phase.name + "-" + name, [str(args.python), "-B", *command], env, min(600, remaining - 15))
            if done["exit_code"]:
                save(args.root / "iteration-terminal.json", {**state, "terminal": "iteration_failed_closed", "iteration": iteration, "stage": name, "execution": done})
                return
            if name == "construction" and not json.loads((construction / "report.json").read_text())["candidate_exported"]:
                save(args.root / "iteration-terminal.json", {**state, "terminal": "no_admissible_moves", "iteration": iteration,
                     "final_mesh_sha256": sha(current), "cumulative_50_percent_target_passed": False})
                return
        after = json.loads((phase / "whole-volume/report.json").read_text())
        produced = json.loads((construction / "report.json").read_text())
        proof = json.loads((phase / "local-proof/report.json").read_text())
        assert after["mesh_sha256"] == proof["candidate_sha256"] == produced["candidate_sha256"] == sha(construction / "candidate.npz")
        assert after["mean_ratio_below"]["0.01"] == produced["predicted_bad_cells"]
        assert after["mean_ratio_below"]["0.0001"] <= before["mean_ratio_below"]["0.0001"]
        assert after["mean_ratio_quantiles"]["minimum"] >= before["mean_ratio_quantiles"]["minimum"]
        current, current_report = construction / "candidate.npz", phase / "whole-volume/report.json"
        target = after["mean_ratio_below"]["0.01"] <= 263055
        save(phase / "admission.json", {"local_domains_and_complete_volume_passed": True,
             "cumulative_bad_cell_reduction_fraction": 1 - after["mean_ratio_below"]["0.01"] / 526110,
             "cumulative_50_percent_target_passed": target, **state})
        if target:
            save(args.root / "iteration-terminal.json", {**state, "terminal": "local_iteration_checked_relative_target_passed", "iterations": iteration,
                 "final_mesh_sha256": sha(current), "final_bad_cells": after["mean_ratio_below"]["0.01"],
                 "cumulative_50_percent_target_passed": True, "absolute_shape_gate_passed": after["diagnostic_quality_passed"]})
            print((args.root / "iteration-terminal.json").read_text(), flush=True)
            return
    save(args.root / "iteration-terminal.json", {**state, "terminal": "three_pass_limit_reached", "iterations": 3,
         "final_mesh_sha256": sha(current), "cumulative_50_percent_target_passed": False})


if __name__ == "__main__":
    main()
