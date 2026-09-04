#!/usr/bin/env python3
"""Exécute et audite le contrôle CFD incompressible F50."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("f49_runner_inc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module_introuvable:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_residuals(case: Path, f49) -> dict:
    path = f49.latest_post(case, "residuals", "residuals.dat")
    if path is None:
        return {"path": None, "fields": None}
    rows = [line.split() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.startswith("#")]
    if not rows:
        return {"path": str(path.relative_to(case)), "fields": None}
    names = ("time", "p", "Ux", "Uy", "Uz", "k", "omega")
    fields = {name: float(value) for name, value in zip(names, rows[-1])}
    return {"path": str(path.relative_to(case)), "fields": fields}


def execute(case: Path, contract: dict, f49) -> dict:
    metadata = json.loads((case / "case.json").read_text(encoding="utf-8"))
    source = case / metadata["source_mesh"]
    if sha256(source) != metadata["source_mesh_sha256"]:
        raise RuntimeError(f"source_mesh_hash_mismatch:{metadata['case_id']}")
    for path in (case / "constant" / "polyMesh", case / "postProcessing"):
        if path.exists():
            shutil.rmtree(path)
    for path in case.iterdir():
        if path.is_dir() and re.fullmatch(r"[1-9][0-9]*", path.name):
            shutil.rmtree(path)
    steps = []
    msh2 = case / "source" / "domain-msh2.msh"
    steps.append(f49.run(["gmsh", str(source), "-format", "msh2", "-save", "-o", str(msh2)], case / "log.gmsh-msh2", case))
    steps.append(f49.run(["gmshToFoam", "-case", str(case), str(msh2)], case / "log.gmshToFoam", case))
    steps.append(f49.run(["transformPoints", "-case", str(case), "scale=(0.001 0.001 0.001)"], case / "log.transformPoints", case))
    f49.replace_patch_types(case / "constant" / "polyMesh" / "boundary", metadata["wall_patches"])
    screen = contract["openfoam"]["screens"][metadata["screen"]]
    patch_audit = f49.audit_patch_types(case, screen["source_patch"], screen["sink_patch"], metadata["wall_patches"])
    steps.append(f49.run(["checkMesh", "-case", str(case)], case / "log.checkMesh", case))
    expected_volume = metadata["F48_native_volume_scan_units_cubed"] * 1e-9
    mesh = f49.parse_check_mesh(case / "log.checkMesh", expected_volume)
    mesh_gate = (
        steps[-1]["return_code"] == 0
        and mesh["mesh_ok_marker"]
        and mesh["volume_relative_difference_from_F48"] is not None
        and mesh["volume_relative_difference_from_F48"] <= contract["mesh_matrix"]["openfoam_mesh_gate"]["cell_volume_relative_difference_from_F48_at_most"]
    )
    steps.append(f49.run(["foamRun", "-solver", "incompressibleFluid", "-case", str(case)], case / "log.foamRun-incompressible", case))
    solver_ok = steps[-1]["return_code"] == 0
    q_source = f49.scalar_result(case, "sourceVolumeFlow")
    q_sink = f49.scalar_result(case, "sinkVolumeFlow")
    rho = metadata["source_density_kg_m3"]
    m_source = q_source * rho if q_source is not None else None
    m_sink = q_sink * rho if q_sink is not None else None
    mass_error = (
        abs(m_source + m_sink) / max(abs(m_source), abs(m_sink)) * 100
        if m_source not in (None, 0.0) and m_sink is not None
        else None
    )
    tail = [value * rho for value in f49.scalar_tail(case, "sinkVolumeFlow")[-10:]]
    plateau = None
    if len(tail) >= 5 and max(abs(x) for x in tail) > 0:
        plateau = (max(tail) - min(tail)) / max(abs(x) for x in tail) * 100
    residuals = parse_residuals(case, f49)
    fields = residuals.get("fields") or {}
    targets = contract["openfoam"]["residual_targets"]
    residual_checks = {
        "p": fields.get("p") is not None and fields["p"] <= targets["p"],
        "U": all(fields.get(name) is not None and fields[name] <= targets["U"] for name in ("Ux", "Uy", "Uz")),
        "k": fields.get("k") is not None and fields["k"] <= targets["k"],
        "omega": fields.get("omega") is not None and fields["omega"] <= targets["omega"],
    }
    latest = max((float(p.name) for p in case.iterdir() if p.is_dir() and re.fullmatch(r"[0-9]+", p.name)), default=0.0)
    gates = {
        "mesh": mesh_gate,
        "patch_audit": patch_audit["pass"],
        "solver": solver_ok and latest >= metadata["fixed_iterations"],
        "mass": mass_error is not None and mass_error <= 1.0,
        "plateau": plateau is not None and plateau <= 1.0,
        "residuals": all(residual_checks.values()),
        "energy": False,
    }
    return {
        **metadata,
        "steps": steps,
        "mesh": mesh,
        "patch_type_audit": patch_audit,
        "latest_iteration": latest,
        "residuals": residuals,
        "residual_checks": residual_checks,
        "sink_mass_flow_last_ten_kg_s": tail,
        "sink_mass_flow_tail_spread_percent": plateau,
        "values": {
            "source_volume_flow_m3_s": q_source,
            "sink_volume_flow_m3_s": q_sink,
            "source_mass_flow_kg_s": m_source,
            "sink_mass_flow_kg_s": m_sink,
            "mass_imbalance_percent": mass_error,
            "energy_balance": None,
            "energy_balance_reason": "incompressible control has no energy equation",
        },
        "gates": gates,
        "case_gate_pass": all(gates.values()),
        "status": "FLOW_CONVERGED_ENERGY_UNAVAILABLE" if all(v for k, v in gates.items() if k != "energy") else "EXECUTED_FAIL_CLOSED",
        "validation_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--levels", nargs="+", choices=("coarse", "medium", "fine"), default=("coarse", "medium", "fine"))
    parser.add_argument("--variants", nargs="+", choices=("2V", "4V"), default=("2V", "4V"))
    parser.add_argument("--screens", nargs="+", choices=("intake", "exhaust"), default=("intake", "exhaust"))
    parser.add_argument("--report-name", default="incompressible-execution-report.json")
    args = parser.parse_args()
    root = args.project_root.resolve()
    work = args.work_root.resolve()
    f49 = load_module(root / "twins/reference-917-engine/source/run_cfd_cases_f49.py")
    env = f49.assert_openfoam_environment()
    contract_path = root / "twins/reference-917-engine/f49-cfd-cht-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    results = []
    for variant in args.variants:
        for level in args.levels:
            for screen in args.screens:
                result = execute(work / "cases" / f"{variant.lower()}-{level}-{screen}", contract, f49)
                results.append(result)
                print(json.dumps({"case": result["case_id"], "status": result["status"]}), flush=True)
    report = {
        "schema_version": "porsche-917-f50-incompressible-openfoam-execution/v1",
        "F49_contract_sha256": sha256(contract_path),
        "openfoam_environment": env,
        "image_expected": "3dprinting993-cfd-cae-f47:kali-local",
        "image_id_expected": "sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17",
        "cases": results,
        "outer_or_inner_geometry_modified": False,
        "ellipse_or_oval_proxy_used": False,
        "energy_equation_solved": False,
        "validation_claim": False,
    }
    output = work / args.report_name
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "sha256": sha256(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
