#!/usr/bin/env python3
"""Exécute la formulation CFD F50 stationnaire en deux étapes bornées.

Une initialisation laminaire stationnaire précède le calcul final RANS SST.
Les conditions aux limites physiques sont identiques pendant les deux étapes;
aucun résultat laminaire n'est utilisé comme résultat comparatif final.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path


CP_AIR_J_KG_K = 1005.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module_introuvable:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def set_iterations(control_path: Path, *, start_from: str, end_time: int) -> None:
    text = control_path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^startFrom\s+\w+;", f"startFrom {start_from};", text)
    text = re.sub(r"(?m)^endTime\s+[0-9.eE+\-]+;", f"endTime {end_time};", text)
    control_path.write_text(text, encoding="utf-8")


def set_transport(case: Path, mode: str) -> None:
    path = case / "constant" / "momentumTransport"
    if mode == "laminar":
        body = "simulationType laminar;\n"
    elif mode == "RAS":
        body = "simulationType RAS;\nRAS { model kOmegaSST; turbulence on; }\n"
    else:
        raise RuntimeError(f"transport_mode_inconnu:{mode}")
    path.write_text(
        "FoamFile\n{\n    format ascii;\n    class dictionary;\n"
        '    location "constant";\n    object momentumTransport;\n}\n\n' + body,
        encoding="utf-8",
    )


def latest_numeric_time(case: Path) -> float:
    values = []
    for path in case.iterdir():
        if path.is_dir():
            try:
                values.append(float(path.name))
            except ValueError:
                pass
    return max(values, default=0.0)


def latest_solution_path(case: Path) -> Path | None:
    candidates = []
    for path in case.iterdir():
        if not path.is_dir() or not all((path / name).is_file() for name in ("p", "T", "U")):
            continue
        try:
            candidates.append((float(path.name), path))
        except ValueError:
            pass
    return max(candidates, default=(None, None), key=lambda item: item[0])[1]


def patch_uniform_scalar(path: Path, patch: str, key: str, value: float) -> None:
    text = path.read_text(encoding="utf-8")
    block_pattern = re.compile(rf"(?ms)(^\s*{re.escape(patch)}\s*\{{)(.*?)(^\s*\}})")
    match = block_pattern.search(text)
    require(match is not None, f"patch_absent:{path}:{patch}")
    body = match.group(2)
    new_body, count = re.subn(
        rf"(?m)(^\s*{re.escape(key)}\s+uniform\s+)[^;]+;",
        rf"\g<1>{value:.12g};",
        body,
        count=1,
    )
    require(count == 1, f"cle_patch_absente:{path}:{patch}:{key}")
    text = text[: match.start(2)] + new_body + text[match.end(2) :]
    path.write_text(text, encoding="utf-8")


def set_internal_uniform(path: Path, value: float) -> None:
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(
        r"(?m)^(\s*internalField\s+uniform\s+)[^;]+;",
        rf"\g<1>{value:.12g};",
        text,
        count=1,
    )
    require(count == 1, f"internalField_absent:{path}")
    path.write_text(text, encoding="utf-8")


def set_source_state(solution_dir: Path, source_patch: str, p0: float, temperature: float, set_internal: bool) -> None:
    p_path = solution_dir / "p"
    t_path = solution_dir / "T"
    patch_uniform_scalar(p_path, source_patch, "p0", p0)
    if set_internal:
        patch_uniform_scalar(p_path, source_patch, "value", p0)
    patch_uniform_scalar(t_path, source_patch, "value", temperature)
    if set_internal:
        set_internal_uniform(p_path, p0)
        set_internal_uniform(t_path, temperature)


def prepare_mesh(case: Path, metadata: dict, contract: dict, f49) -> tuple[list[dict], dict, bool, dict]:
    source = case / metadata["source_mesh"]
    require(sha256(source) == metadata["source_mesh_sha256"], f"source_mesh_hash_mismatch:{metadata['case_id']}")
    for path in (case / "constant" / "polyMesh", case / "postProcessing"):
        if path.exists():
            shutil.rmtree(path)
    for path in case.iterdir():
        if path.is_dir() and re.fullmatch(r"[1-9][0-9]*(?:\.[0-9]+)?", path.name):
            shutil.rmtree(path)
    steps = []
    msh2 = case / "source" / "domain-msh2.msh"
    steps.append(f49.run(["gmsh", str(source), "-format", "msh2", "-save", "-o", str(msh2)], case / "log.gmsh-msh2", case))
    if steps[-1]["return_code"] != 0:
        return steps, {}, False, {}
    steps.append(f49.run(["gmshToFoam", "-case", str(case), str(msh2)], case / "log.gmshToFoam", case))
    if steps[-1]["return_code"] != 0:
        return steps, {}, False, {}
    steps.append(f49.run(["transformPoints", "-case", str(case), "scale=(0.001 0.001 0.001)"], case / "log.transformPoints", case))
    if steps[-1]["return_code"] != 0:
        return steps, {}, False, {}
    f49.replace_patch_types(case / "constant" / "polyMesh" / "boundary", metadata["wall_patches"])
    screen = contract["openfoam"]["screens"][metadata["screen"]]
    patch_audit = f49.audit_patch_types(case, screen["source_patch"], screen["sink_patch"], metadata["wall_patches"])
    require(patch_audit["pass"], f"patch_type_audit_failed:{metadata['case_id']}")
    steps.append(f49.run(["checkMesh", "-case", str(case)], case / "log.checkMesh", case))
    expected_volume_m3 = metadata["F48_native_volume_scan_units_cubed"] * 1.0e-9
    mesh = f49.parse_check_mesh(case / "log.checkMesh", expected_volume_m3)
    mesh_gate = (
        steps[-1]["return_code"] == 0
        and mesh["mesh_ok_marker"]
        and mesh["volume_relative_difference_from_F48"] is not None
        and mesh["volume_relative_difference_from_F48"]
        <= contract["mesh_matrix"]["openfoam_mesh_gate"]["cell_volume_relative_difference_from_F48_at_most"]
    )
    return steps, mesh, mesh_gate, patch_audit


def scalar_tail(case: Path, function_name: str, count: int = 10) -> list[float]:
    return list(getattr(load_module(Path(__file__).with_name("run_cfd_cases_f49.py"), "f49_tail"), "scalar_tail")(case, function_name))[-count:]


def parse_field_extrema(log_path: Path) -> dict:
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    result = {}
    patterns = {
        "U_max_m_s": r"maxMag\(all\) of U = ([+\-0-9.eE]+)",
        "T_min_k": r"min\(all\) of T = ([+\-0-9.eE]+)",
        "T_max_k": r"max\(all\) of T = ([+\-0-9.eE]+)",
        "k_min_m2_s2": r"min\(all\) of k = ([+\-0-9.eE]+)",
        "k_max_m2_s2": r"max\(all\) of k = ([+\-0-9.eE]+)",
        "omega_min_s-1": r"min\(all\) of omega = ([+\-0-9.eE]+)",
        "omega_max_s-1": r"max\(all\) of omega = ([+\-0-9.eE]+)",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        result[name] = float(match.group(1)) if match else None
    return result


def execute_case(case: Path, project_root: Path, f49_contract: dict, f50_contract: dict, f49) -> dict:
    metadata = json.loads((case / "case.json").read_text(encoding="utf-8"))
    steps, mesh, mesh_gate, patch_audit = prepare_mesh(case, metadata, f49_contract, f49)
    if not patch_audit:
        return {**metadata, "steps": steps, "status": "MESH_PREPARATION_FAILED", "validation_claim": False}
    ramp = f50_contract["method"]["laminar_initialization_ramp"]
    init_iterations = int(ramp[-1]["end_iteration"])
    total_iterations = int(metadata["fixed_iterations"])
    set_transport(case, "laminar")
    screen = f49_contract["openfoam"]["screens"][metadata["screen"]]
    sink_pressure = screen["sink_static_pressure_pa_abs"]
    final_pressure = screen["source_total_pressure_pa_abs"]
    final_temperature = screen["source_temperature_k"]
    wall_temperature = f49_contract["openfoam"]["common_boundary_conditions"]["wall_temperature_k"]
    init_steps = []
    init_reached = True
    for index, stage in enumerate(ramp):
        fraction = float(stage["fraction_of_final_pressure_and_temperature_delta"])
        stage_end = int(stage["end_iteration"])
        state_dir = latest_solution_path(case) or (case / "0")
        set_source_state(
            state_dir,
            screen["source_patch"],
            sink_pressure + fraction * (final_pressure - sink_pressure),
            wall_temperature + fraction * (final_temperature - wall_temperature),
            set_internal=index == 0,
        )
        set_iterations(
            case / "system" / "controlDict",
            start_from="startTime" if index == 0 else "latestTime",
            end_time=stage_end,
        )
        stage_step = f49.run(
            ["foamRun", "-solver", "fluid", "-case", str(case)],
            case / f"log.foamRun-laminar-ramp-{index + 1}",
            case,
        )
        stage_step["stage_fraction"] = fraction
        stage_step["stage_end_iteration"] = stage_end
        steps.append(stage_step)
        init_steps.append(stage_step)
        solution_path = latest_solution_path(case)
        reached = solution_path is not None and float(solution_path.name) >= stage_end
        if stage_step["return_code"] != 0 or not reached:
            init_reached = False
            break
    init_step = init_steps[-1]
    if init_reached:
        set_transport(case, "RAS")
        set_iterations(case / "system" / "controlDict", start_from="latestTime", end_time=total_iterations)
        final_step = f49.run(["foamRun", "-solver", "fluid", "-case", str(case)], case / "log.foamRun-steady-RANS", case)
        steps.append(final_step)
    else:
        final_step = {"return_code": None, "elapsed_s": 0.0, "log": None, "log_sha256": None, "command": []}
    final_reached = latest_numeric_time(case) >= total_iterations
    solver_ok = final_step["return_code"] == 0 and final_reached
    post_step = None
    if final_reached:
        extrema_log = case / "log.field-extrema"
        post_step = f49.run(
            [
                "foamPostProcess", "-solver", "fluid", "-latestTime", "-funcs",
                "(cellMaxMag(U) cellMin(T) cellMax(T) cellMin(k) cellMax(k) cellMin(omega) cellMax(omega))",
            ],
            extrema_log,
            case,
        )
        steps.append(post_step)
    extrema = parse_field_extrema(case / "log.field-extrema")
    m_in = f49.scalar_result(case, "sourceMassFlow")
    m_out = f49.scalar_result(case, "sinkMassFlow")
    source_terms = f49.vector_result(case, "sourceTotalEnergyTerms")
    sink_terms = f49.vector_result(case, "sinkTotalEnergyTerms")
    qwall = f49.heat_flux_integral(case)
    net_advective = None
    if None not in (m_in, m_out) and source_terms and sink_terms and len(source_terms) >= 2 and len(sink_terms) >= 2:
        source_h0 = CP_AIR_J_KG_K * source_terms[0] + 0.5 * source_terms[1]
        sink_h0 = CP_AIR_J_KG_K * sink_terms[0] + 0.5 * sink_terms[1]
        net_advective = m_in * source_h0 + m_out * sink_h0
    mass_imbalance = (
        abs(m_in + m_out) / max(abs(m_in), abs(m_out)) * 100.0
        if m_in not in (None, 0.0) and m_out is not None
        else None
    )
    energy_residual = net_advective - qwall if None not in (net_advective, qwall) else None
    energy_imbalance = (
        abs(energy_residual) / max(abs(net_advective), abs(qwall), 1.0) * 100.0
        if energy_residual is not None
        else None
    )
    residuals = f49.parse_residuals(case)
    fields = residuals.get("fields") or {}
    targets = f50_contract["strict_gates"]["residual_targets"]
    residual_checks = {
        "p": fields.get("p") is not None and fields["p"] <= targets["p"],
        "U": all(fields.get(n) is not None and fields[n] <= targets["U"] for n in ("Ux", "Uy", "Uz")),
        "k": fields.get("k") is not None and fields["k"] <= targets["k"],
        "omega": fields.get("omega") is not None and fields["omega"] <= targets["omega"],
        "h": fields.get("h") is not None and fields["h"] <= targets["h"],
    }
    tail = f49.scalar_tail(case, "sinkMassFlow")[-10:]
    plateau = None
    if len(tail) >= 5 and max(abs(x) for x in tail) > 0:
        plateau = (max(tail) - min(tail)) / max(abs(x) for x in tail) * 100.0
    gates = {
        "mesh": mesh_gate,
        "laminar_initialization": init_step["return_code"] == 0 and init_reached,
        "solver": solver_ok,
        "mass": mass_imbalance is not None and mass_imbalance <= f50_contract["strict_gates"]["mass_imbalance_percent_at_most"],
        "energy": energy_imbalance is not None and energy_imbalance <= f50_contract["strict_gates"]["steady_energy_imbalance_percent_at_most"],
        "plateau": plateau is not None and plateau <= f50_contract["strict_gates"]["sink_mass_flow_tail_spread_percent_at_most"],
        "residuals": all(residual_checks.values()),
        # OpenFOAM 14 ne publie pas un compteur d'activation du fvConstraint.
        # Le champ final intérieur ne prouve donc pas zéro activation historique.
        "temperature_constraint_activation_zero_quantified": False,
    }
    return {
        **metadata,
        "steps": steps,
        "mesh": mesh,
        "patch_type_audit": patch_audit,
        "latest_iteration": latest_numeric_time(case),
        "laminar_initialization_reached": init_reached,
        "laminar_initialization_stages": init_steps,
        "fixed_final_iteration_reached": final_reached,
        "residuals": residuals,
        "residual_checks": residual_checks,
        "sink_mass_flow_last_ten_kg_s": tail,
        "sink_mass_flow_tail_spread_percent": plateau,
        "field_extrema": extrema,
        "values": {
            "source_mass_flow_kg_s": m_in,
            "sink_mass_flow_kg_s": m_out,
            "mass_imbalance_percent": mass_imbalance,
            "sink_temperature_mass_weighted_k": f49.scalar_result(case, "sinkTemperature"),
            "source_total_energy_terms": source_terms,
            "sink_total_energy_terms": sink_terms,
            "net_advective_total_enthalpy_out_w": net_advective,
            "wall_heat_flux_integral_w": qwall,
            "steady_energy_balance_residual_w": energy_residual,
            "steady_energy_imbalance_percent": energy_imbalance,
            "energy_balance_sign_convention": "outward_advective_total_enthalpy - wallHeatFlux_reported",
            "imposed_pressure_difference_pa": screen["imposed_pressure_difference_pa"],
        },
        "gates": gates,
        "case_gate_pass": all(gates.values()),
        "converged_claim": all(gates.values()),
        "status": "EXECUTED_PASS" if all(gates.values()) else "EXECUTED_FAIL_CLOSED",
        "validation_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--levels", nargs="+", choices=("coarse", "medium", "fine"), default=("coarse", "medium", "fine"))
    parser.add_argument("--variants", nargs="+", choices=("2V", "4V"), default=("2V", "4V"))
    parser.add_argument("--screens", nargs="+", choices=("intake", "exhaust"), default=("intake", "exhaust"))
    parser.add_argument("--report-name", default="steady-execution-report.json")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    work_root = args.work_root.resolve()
    f49 = load_module(project_root / "twins/reference-917-engine/source/run_cfd_cases_f49.py", "f49_runner")
    environment = f49.assert_openfoam_environment()
    f49_contract = json.loads((project_root / "twins/reference-917-engine/f49-cfd-cht-contract.json").read_text(encoding="utf-8"))
    f50_contract_path = project_root / "twins/reference-917-engine/f50-steady-cfd-contract.json"
    f50_contract = json.loads(f50_contract_path.read_text(encoding="utf-8"))
    results = []
    for variant in args.variants:
        for level in args.levels:
            for screen in args.screens:
                case = work_root / "cases" / f"{variant.lower()}-{level}-{screen}"
                result = execute_case(case, project_root, f49_contract, f50_contract, f49)
                results.append(result)
                print(json.dumps({"case": result["case_id"], "status": result["status"]}), flush=True)
    report = {
        "schema_version": "porsche-917-f50-steady-openfoam-execution/v1",
        "F50_contract_sha256": sha256(f50_contract_path),
        "F49_contract_sha256": sha256(project_root / "twins/reference-917-engine/f49-cfd-cht-contract.json"),
        "openfoam_environment": environment,
        "image_expected": "3dprinting993-cfd-cae-f47:kali-local",
        "image_id_expected": "sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17",
        "cases": results,
        "conjugate_CHT_executed": False,
        "AATE_dynamic_engine_case_executed": False,
        "outer_or_inner_geometry_modified": False,
        "ellipse_or_oval_proxy_used": False,
        "validation_claim": False,
    }
    output = work_root / args.report_name
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "sha256": sha256(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
