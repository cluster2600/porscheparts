"""Gate one default-optimizer head call on a boundary-only 3-to-2 flip witness.

The preceding cube witness requires interior movement. This new analytic convex
bipyramid independently checks the topology-changing capability needed for
fixed-boundary-only bad cells. The previous failure and head target stay intact.
"""
import argparse
from fractions import Fraction
import importlib.util
import json
import os
from pathlib import Path

import numpy as np


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "python", "scientific-site", "retained-sources", "repository",
                 "input-arrays", "input-msh", "input-inspection", "surface", "surface-report"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.root.mkdir(mode=0o700, exist_ok=False)
    helper = module(args.retained_sources / "run_optimization.py", "retained_topology_bounds")
    sha, save, run = helper.sha, helper.save, helper.run
    assert sha(args.input_arrays) == "b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.input_msh) == "dd06871fe45c765836d9690b5e6dd4bc00cc62cd9389b2ae16b5a4aa9831ba08"
    assert sha(args.surface) == "5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    before_head = json.loads(args.input_inspection.read_text())
    geometry = json.loads(args.surface_report.read_text())
    assert before_head["all_cells_positive_for_stored_binary_coordinates"] and before_head["all_internal_faces_oppositely_oriented"]
    assert before_head["mesh_sha256"] == sha(args.input_arrays) and before_head["surface_sha256"] == sha(args.surface) == geometry["input_sha256"]
    assert before_head["actual_complete_boundary_and_orientation_exact"] and geometry["geometry_export_gate_passed"]
    inspector = args.repository / "docs/research/935-unoptimized-volume-20261105/source/inspect_interval_volume.py"
    frozen = args.repository / "docs/research/935-local-physics-20261105/source/inspect_tetrahedra.py"
    assert sha(inspector) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    exact = module(inspector, "retained_topology_orientations")
    wrapper = Path(__file__).with_name("optimize_topology_volume.py")
    recipe = args.retained_sources / "optimize_volume.py"
    plan = {"source_sha256": sha(Path(__file__)), "wrapper_sha256": sha(wrapper),
            "retained_recipe_sha256": sha(recipe), "input_arrays_sha256": sha(args.input_arrays),
            "surface_sha256": sha(args.surface), "upstream_verdict": "Relocation bound excludes 50% target; fixed-boundary topology change requires a distinct analytic witness",
            "method": "Gmsh default", "one_api_call": True, "api_niter": 1,
            "head_alarm_seconds": 900, "sampled_rss_limit_gib": 40,
            "head_bin_reduction_min_fraction": .5, "ultra_low_bin_must_not_increase": .0001,
            "minimum_quality_must_not_worsen": True, "control_minimum_floor": .01,
            "control_minimum_improvement_factor": 10, "control_requires_known_3_to_2_flip": True,
            "parameter_sweep": False, "new_paid_compute_usd": 0, "physics_admitted": False}
    save(args.root / "plan.json", plan)
    vertices = np.array([[1e-6, 0, 0], [-1, 1, 0], [-1, -1, 0], [0, 0, 1], [0, 0, -1]], dtype=float)
    boundary = np.array([[3, 0, 1], [3, 1, 2], [3, 2, 0], [4, 1, 0], [4, 2, 1], [4, 0, 2]])
    for face in boundary:
        others = [v for v in range(5) if v not in face]
        signs = [exact.exact_determinant(vertices[[*face, v]]) for v in others]
        assert all(value < 0 for value in signs) or all(value > 0 for value in signs)
        if signs[0] > 0:
            face[[1, 2]] = face[[2, 1]]
    surface = args.root / "bipyramid-surface.npz"
    np.savez_compressed(surface, vertices=vertices, triangles=boundary)
    volume = Fraction(2, 3) * (1 + Fraction.from_float(float(vertices[0, 0])))
    report = args.root / "bipyramid-surface.json"
    save(report, {"input_sha256": sha(surface), "geometry_export_gate_passed": True,
                  "signed_volume_mm3": float(volume), "scope": "Synthetic analytic convex hull; exact supporting-face tests; not a Porsche dimension"})
    for filename, cells in (("bipyramid-before.npz", [[3, 4, 0, 1], [3, 4, 1, 2], [3, 4, 2, 0]]),
                            ("bipyramid-alternative.npz", [[0, 1, 2, 3], [0, 2, 1, 4]])):
        cells = np.array(cells)
        total = Fraction(0)
        for cell in cells:
            value = exact.exact_determinant(vertices[cell])
            if value < 0:
                cell[[1, 2]] = cell[[2, 1]]
                value = -value
            assert value > 0
            total += value / 6
        assert total == volume
        np.savez_compressed(args.root / filename, nodes=vertices, tets=cells, boundary=boundary)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(args.scientific_site)

    def inspect(name, mesh, surface_path, report_path):
        done = run(args.root, name, [str(args.python), "-B", str(inspector), "--mesh", str(mesh),
                   "--surface", str(surface_path), "--surface-report", str(report_path),
                   "--frozen-inspector", str(frozen), "--output", str(args.root / name)], env, 600)
        if done["exit_code"]:
            save(args.root / "terminal.json", {"terminal": "independent_inspection_failed", "stage": name,
                 "physics_admitted": False, "new_paid_compute_usd": 0})
            raise SystemExit(1)
        return json.loads((args.root / name / "report.json").read_text())

    before = inspect("control-before", args.root / "bipyramid-before.npz", surface, report)
    alternative = inspect("analytic-alternative", args.root / "bipyramid-alternative.npz", surface, report)
    floor = max(.01, 10 * before["mean_ratio_quantiles"]["minimum"])
    assert alternative["mean_ratio_quantiles"]["minimum"] >= floor
    base = [str(args.python), "-B", str(wrapper), "--audited-recipe", str(args.retained_sources / "optimize_audited_volume.py"),
            "--recipe", str(recipe), "--interval-inspector", str(inspector)]
    done = run(args.root, "control-native", base + ["--input-arrays", str(args.root / "bipyramid-before.npz"),
               "--surface", str(surface), "--output", str(args.root / "control-optimized"), "--deadline-seconds", "60"], env, 60)
    if done["exit_code"]:
        save(args.root / "terminal.json", {"terminal": "control_native_failed_no_head_run", "new_paid_compute_usd": 0})
        raise SystemExit(1)
    after = inspect("control-after", args.root / "control-optimized/candidate.npz", surface, report)
    with np.load(args.root / "control-optimized/candidate.npz", allow_pickle=False) as actual, np.load(args.root / "bipyramid-alternative.npz", allow_pickle=False) as expected:
        known_flip = sorted(map(tuple, np.sort(actual["tets"], axis=1))) == sorted(map(tuple, np.sort(expected["tets"], axis=1)))
    if after["mean_ratio_quantiles"]["minimum"] < floor or not known_flip:
        save(args.root / "terminal.json", {"terminal": "topology_control_rejected_no_head_run", "known_flip": known_flip,
             "minimum_quality": after["mean_ratio_quantiles"]["minimum"], "required_floor": floor, "new_paid_compute_usd": 0})
        raise SystemExit(1)
    save(args.root / "control-admission.json", {"known_3_to_2_flip": True, "minimum_before": before["mean_ratio_quantiles"]["minimum"],
         "minimum_after": after["mean_ratio_quantiles"]["minimum"], "independent_boundary_and_cells_passed": True})
    done = run(args.root, "head-native", base + ["--input-msh", str(args.input_msh), "--input-arrays", str(args.input_arrays),
               "--surface", str(args.surface), "--output", str(args.root / "head-optimized"), "--deadline-seconds", "900"], env, 900)
    if done["exit_code"]:
        save(args.root / "terminal.json", {"terminal": "head_native_failed_closed", "execution": done,
             "physics_admitted": False, "new_paid_compute_usd": 0})
        raise SystemExit(1)
    after = inspect("head-inspection", args.root / "head-optimized/candidate.npz", args.surface, args.surface_report)
    reduction = 1 - after["mean_ratio_below"]["0.01"] / before_head["mean_ratio_below"]["0.01"]
    checks = {"bin_reduction": reduction >= .5, "ultra_low_count": after["mean_ratio_below"]["0.0001"] <= before_head["mean_ratio_below"]["0.0001"],
              "minimum_quality": after["mean_ratio_quantiles"]["minimum"] >= before_head["mean_ratio_quantiles"]["minimum"]}
    save(args.root / "terminal.json", {"terminal": "head_checked", "checks": checks, "diagnostic_target_passed": all(checks.values()),
         "below_0p01_reduction_fraction": reduction, "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0})


if __name__ == "__main__":
    main()
