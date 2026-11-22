"""Qualify a backend against CalculiX's committed tensors, then run the declared resolutions (contract.json).

Usage: python study.py OUT_DIR BACKEND
Writes OUT_DIR/n{N}-floor{F}/assessment.json for each case, OUT_DIR/qualification.json, and OUT_DIR/terminal.json
with the comparisons and the two verdicts of the contract. A rerun into the same OUT_DIR reuses a case only if its
assessment names the same resolution, void floor, target, backend family and geometry source; the solver script hash
of each case stays in its assessment. A case that fails is recorded in refusal.json and
the study stops there: no resolution is skipped or replaced.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rve_c3d8  # noqa: E402

CCX = HERE.parent / "constant-fraction-20261026" / "results" / "single-thread"
FLOORS = [(1e-4, "1e-4"), (1e-6, "1e-6")]


def tensor(path: Path) -> np.ndarray:
    return np.array(json.loads(path.read_text())["effective_C_MPa"])


BACKEND_FAMILY = {"scipy": "scipy SuperLU (CPU)", "cudss": "NVIDIA cuDSS", "cudss-hybrid": "NVIDIA cuDSS"}


def case(out: Path, n: int, floor: float, label: str, target: float, backend: str) -> dict:
    """Solve one case, or reuse an assessment already in OUT_DIR only if it is the same case from the same
    backend family on the same geometry source; anything else stops the study rather than mixing series."""
    folder = out / f"n{n}-floor{label}"
    if not (folder / "assessment.json").exists():
        rve_c3d8.run(n, floor, target, backend, folder)
    report = json.loads((folder / "assessment.json").read_text())
    identity = {"resolution": report["resolution"] == n, "void_floor": report["void_relative_stiffness"] == floor,
                "target_fraction": report["target_solid_fraction"] == target,
                "backend": report["solver"]["backend"].startswith(BACKEND_FAMILY[backend]),
                "geometry_source": report["geometry_source_sha256"] == rve_c3d8.hashlib.sha256(rve_c3d8.CASE.read_bytes()).hexdigest()}
    if not all(identity.values()):
        raise SystemExit(f"{folder}: an assessment from another case, backend or geometry source is in the way: {identity}")
    print(f"n={n} floor={label} min ratio {report['minimum_tensor_stiffness_ratio']:.7f} "
          f"dofs {report['dofs']} solve {report['solver']['solve_s']} s wall {report['wall_s']} s", flush=True)
    return report


def main() -> None:
    out, backend = Path(sys.argv[1]), sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    contract = json.loads((HERE / "contract.json").read_text())
    target = contract["unchanged_from_the_earlier_study"]["target_solid_fraction"]
    limit = contract["qualification_before_use"]["limit"]
    rows, qualification = [], []
    try:
        # 1. qualification against the committed CalculiX tensors
        for n in (16, 24, 32):
            for floor, label in FLOORS:
                mine = np.array(case(out, n, floor, label, target, backend)["effective_C_MPa"])
                theirs = tensor(CCX / f"n{n}-floor{label}" / "assessment.json")
                diff = float(np.linalg.norm(mine - theirs) / np.linalg.norm(theirs))
                qualification.append({"resolution": n, "void_floor": label, "relative_difference_to_calculix": diff,
                                      "passed": diff <= limit})
        admitted = all(q["passed"] for q in qualification)
        (out / "qualification.json").write_text(json.dumps({"backend": backend, "limit": limit, "admitted": admitted,
                                                            "cases": qualification}, indent=2) + "\n")
        print("qualification", "admitted" if admitted else "REFUSED", max(q["relative_difference_to_calculix"] for q in qualification), flush=True)
        if not admitted:
            raise SystemExit("backend not admitted: no resolution above N=32 is run")
        # 2. the declared series, on this backend's own tensors
        series = contract["resolutions"]["completion_of_the_declared_study"] + contract["resolutions"]["extension_declared_now"]
        for n in series:
            reports = [case(out, n, floor, label, target, backend) for floor, label in FLOORS]
            soft, hard = (np.array(r["effective_C_MPa"]) for r in reports)
            row = {"resolution": n, "solid_fraction": reports[1]["solid_fraction"],
                   "solid_fraction_error_relative": reports[1]["solid_fraction_error_relative"],
                   "gyroid_threshold": reports[1]["gyroid_threshold"],
                   "minimum_tensor_stiffness_ratio": reports[1]["minimum_tensor_stiffness_ratio"],
                   "relative_void_floor_tensor_change": float(np.linalg.norm(soft - hard) / np.linalg.norm(hard))}
            row["void_floor_test_passed"] = row["relative_void_floor_tensor_change"] <= 0.01
            if rows:
                previous = tensor(out / f"n{rows[-1]['resolution']}-floor1e-6" / "assessment.json")
                row["relative_tensor_resolution_change"] = float(np.linalg.norm(previous - hard) / np.linalg.norm(hard))
                row["resolution_change_passed"] = row["relative_tensor_resolution_change"] <= 0.02
            rows.append(row)
            (out / "comparison-progress.json").write_text(json.dumps(rows, indent=2) + "\n")
            print(row, flush=True)
        by_n = {r["resolution"]: r for r in rows}
        passes = lambda *ns: all(by_n[n].get("resolution_change_passed") and by_n[n]["void_floor_test_passed"] for n in ns)
        (out / "terminal.json").write_text(json.dumps({
            "status": "constant_fraction_refinement_study_completed", "backend": backend,
            "declared_study_converged": passes(32, 48), "declared_study_rule": "24->32 and 32->48 both pass",
            "extended_series_converged": passes(64, 80), "extended_series_rule": "48->64 and 64->80 both pass",
            "comparisons": rows, "carrier_convergence_demonstrated": False, "cellular_part_generated": False,
        }, indent=2) + "\n")
        print("done", passes(32, 48), passes(64, 80), flush=True)
    except BaseException as error:
        (out / "refusal.json").write_text(json.dumps({
            "error": type(error).__name__, "detail": str(error), "traceback": traceback.format_exc()[-3000:],
            "qualification": qualification, "completed_comparisons": rows, "epoch": time.time()}, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
