#!/usr/bin/env python3
"""Bounded serial pipeline. A completed run is not a converged head result."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boundary_contract(text: str) -> dict:
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    patches = {}
    for name, body in re.findall(r"([A-Za-z_][A-Za-z_0-9]*)\s*\{([^{}]*)\}", text):
        count = re.search(r"\bnFaces\s+(\d+)\s*;", body)
        if count:
            kind = re.search(r"\btype\s+(\w+)\s*;", body)
            if kind is None or name in patches:
                raise ValueError("missing type or duplicate boundary name")
            patches[name] = {"type": kind[1], "faces": int(count[1])}
    if set(patches) != {"inlet", "receiver_outlet", "walls"}:
        raise ValueError("unexpected or missing mesh boundary")
    if any(p["faces"] <= 0 for p in patches.values()):
        raise ValueError("empty intended mesh boundary")
    if {name: p["type"] for name, p in patches.items()} != {
            "inlet": "patch", "receiver_outlet": "patch", "walls": "wall"}:
        raise ValueError("invalid boundary types")
    return patches


def mesh_ok(log: str) -> bool:
    return "Mesh OK." in log and not re.search(r"Failed\s+\d+\s+mesh checks|FOAM FATAL", log)


def set_wall_patch_type(text: str) -> str:
    """Change metadata only; createPatch retains the type of an existing patch."""
    pattern = r"(\bwalls\s*\{[^{}]*?\btype\s+)patch(\s*;[^{}]*\})"
    changed, count = re.subn(pattern, r"\g<1>wall\2", text)
    if count != 1:
        raise ValueError("expected exactly one Gmsh walls patch to type as wall")
    boundary_contract(changed)
    return changed


def require_head_review(manifest: dict, review: dict | None) -> None:
    if manifest["purpose"] == "synthetic_runtime_smoke":
        return
    if (review is None or review.get("schema") != "m64-intake-pilot-review/v1"
            or review.get("approved_for_diagnostic_cfd") is not True
            or review.get("boundary_assignment_accepted") is not True
            or review.get("mesh_sha256") != manifest["mesh_sha256"]
            or not re.fullmatch(r"[a-f0-9]{64}", review.get("native_domain_sha256", ""))):
        raise ValueError("head pilot requires an independent native-domain and exact-mesh boundary review")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-dir", type=Path, required=True)
    ap.add_argument("--timeout-seconds", type=int, default=300)
    ap.add_argument("--stop-after-mesh", action="store_true")
    ap.add_argument("--poly-dual", action="store_true", help="explicit alternative FV mesh; feature angle 60 degrees")
    ap.add_argument("--review-receipt", type=Path, help="required for head_pilot, never inferred from patch names")
    args = ap.parse_args()
    if not 10 <= args.timeout_seconds <= 3600:
        raise ValueError("timeout must be 10..3600 seconds per stage")
    case = args.case_dir.resolve()
    manifest = json.loads((case / "case-manifest.json").read_text())
    review = json.loads(args.review_receipt.read_text()) if args.review_receipt else None
    require_head_review(manifest, review)
    if (case / "constant/polyMesh").exists() or (case / "execution-report.json").exists():
        raise ValueError("refusing to repeat conversion/scale/run in an existing case")
    if sha(case / "input.msh") != manifest["mesh_sha256"]:
        raise ValueError("input mesh changed after preparation")
    for name, expected in manifest["file_sha256"].items():
        if sha(case / name) != expected:
            raise ValueError(f"case file changed after preparation: {name}")
    report = {"schema": "m64-openfoam-intake-execution/v1", "purpose": manifest["purpose"],
              "case_manifest_sha256": sha(case / "case-manifest.json"),
              "runner_sha256": sha(Path(__file__)), "stages": [], "status": "running",
              "manufacturing_authorized": False, "head_performance_validated": False,
              "spatial_convergence_demonstrated": False, "physical_correlation": False,
              "solver_executed": False, "scale_applied": False}
    report["poly_dual_requested"] = args.poly_dual
    report["independent_review_receipt_sha256"] = sha(args.review_receipt) if args.review_receipt else None
    report_file = case / "execution-report.json"

    def save() -> None:
        report_file.write_text(json.dumps(report, indent=2) + "\n")

    def run(label: str, cmd: list[str]) -> None:
        started = time.monotonic()
        stage = {"name": label, "argv": cmd, "exit_code": None, "timed_out": False}
        log_path = case / f"log.{label}"
        with log_path.open("wb") as stream:
            try:
                done = subprocess.run(cmd, cwd=case, stdout=stream, stderr=subprocess.STDOUT,
                                      timeout=args.timeout_seconds, check=False)
                stage["exit_code"] = done.returncode
            except subprocess.TimeoutExpired:
                stage["timed_out"] = True
        stage["elapsed_seconds"] = time.monotonic() - started
        stage["log_sha256"] = sha(log_path)
        report["stages"].append(stage)
        save()
        print(json.dumps(stage), flush=True)
        if stage["exit_code"] != 0:
            raise RuntimeError(f"{label} failed or timed out; inspect its recorded log")

    save()
    try:
        run("gmshToFoam", ["gmshToFoam", "input.msh"])
        run("transformPoints", ["transformPoints", "scale=(0.001 0.001 0.001)"])
        report["scale_applied"] = True
        report["points_after_scale_sha256"] = sha(case / "constant/polyMesh/points")
        if args.poly_dual:
            # gmshToFoam creates a single all-air cellZone. Its primal-cell
            # indices are not remapped by polyDualMesh 14. The homogeneous
            # pilot has no zonal physics: archive this auxiliary selection,
            # preserving it, before changing the cells. Boundary patches stay.
            cell_zone = case / "constant/polyMesh/cellZones"
            if cell_zone.exists():
                zone_text = cell_zone.read_text()
                zone_names = re.findall(r"\b(\w+)\s*\{[^{}]*\bcellLabels\b", zone_text)
                if zone_names != ["air"]:
                    raise ValueError("poly-dual pilot only permits the homogeneous air cellZone")
                report["archived_primal_air_cell_zone_sha256"] = sha(cell_zone)
                cell_zone.rename(case / "primal-air-cellZones.archived")
            run("polyDualMesh", ["polyDualMesh", "60"])
            report["points_after_poly_dual_sha256"] = sha(case / "constant/polyMesh/points")
            if report["points_after_poly_dual_sha256"] == report["points_after_scale_sha256"]:
                raise RuntimeError("polyDualMesh did not change the constant mesh subsequently consumed")
        run("createPatch", ["createPatch", "-overwrite"])
        boundary_path = case / "constant/polyMesh/boundary"
        report["boundary_before_wall_type_sha256"] = sha(boundary_path)
        geometry_files = [case / "constant/polyMesh" / n for n in ("points", "faces", "owner", "neighbour")]
        geometry_before = {p.name: sha(p) for p in geometry_files}
        boundary_path.write_text(set_wall_patch_type(boundary_path.read_text()))
        report["boundary_after_wall_type_sha256"] = sha(boundary_path)
        report["wall_type_change_geometry_unchanged"] = geometry_before == {p.name: sha(p) for p in geometry_files}
        report["boundary"] = boundary_contract(boundary_path.read_text())
        run("checkMesh", ["checkMesh", "-allTopology", "-allGeometry"])
        report["checkMesh_passed"] = mesh_ok((case / "log.checkMesh").read_text())
        if not report["checkMesh_passed"]:
            raise RuntimeError("checkMesh did not explicitly report Mesh OK")
        if args.stop_after_mesh:
            report["status"] = "mesh_pipeline_completed_no_solver"
        else:
            report["solver_executed"] = True
            run("foamRun", ["foamRun"])
            report["status"] = "solver_completed_not_convergence_or_performance_validation"
    except (RuntimeError, ValueError, OSError) as error:
        report["status"] = "rejected_or_incomplete"
        report["error"] = str(error)
        save()
        raise SystemExit(2) from error
    save()
    print(json.dumps({"status": report["status"], "purpose": report["purpose"]}), flush=True)


if __name__ == "__main__":
    main()
