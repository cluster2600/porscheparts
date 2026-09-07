#!/usr/bin/env python3
"""Publie la comparaison CFD F50 expurgée, les GCI et les graphes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(root: Path, relative_path: str) -> dict:
    path = root / relative_path
    require(path.is_file(), f"artefact_introuvable:{relative_path}")
    return {"path": relative_path, "sha256": sha256(path)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def flow_gate(case: dict) -> bool:
    return all(value for name, value in case["gates"].items() if name != "energy")


def sanitise_case(case: dict) -> dict:
    solver_step = case["steps"][-1]
    solver_was_invoked = bool(solver_step.get("command")) and solver_step["command"][0] == "foamRun"
    require(solver_was_invoked, f"preuve_execution_absente:{case['case_id']}")
    return {
        "case_id": case["case_id"],
        "variant": case["variant"],
        "screen": case["screen"],
        "level": case["level"],
        "F48_native_tetrahedron_count": case["F48_native_tetrahedron_count"],
        "F48_native_volume_scan_units_cubed": case["F48_native_volume_scan_units_cubed"],
        "source_mesh_sha256": case["source_mesh_sha256"],
        "source_density_kg_m3": case["source_density_kg_m3"],
        "kinematic_viscosity_m2_s": case["kinematic_viscosity_m2_s"],
        "imposed_physical_pressure_difference_pa": case["imposed_physical_pressure_difference_pa"],
        "mesh": case["mesh"],
        "patch_type_audit": case["patch_type_audit"],
        "latest_iteration": case["latest_iteration"],
        "residuals": case["residuals"],
        "residual_checks": case["residual_checks"],
        "sink_mass_flow_tail_spread_percent": case["sink_mass_flow_tail_spread_percent"],
        "values": case["values"],
        "gates": case["gates"],
        "flow_numerical_gate_pass": flow_gate(case),
        "energy_gate_applicable": False,
        "case_validation_gate_pass": False,
        "status": case["status"],
        "execution_status": "EXECUTED",
        "legacy_input_execution_status": case.get("execution_status"),
        "execution_status_normalization": "legacy builder metadata prepared_not_run is superseded by recorded foamRun command, return code, elapsed time and log SHA-256",
        "solver_step": {
            "return_code": solver_step["return_code"],
            "elapsed_s": solver_step["elapsed_s"],
            "log_sha256": solver_step["log_sha256"],
        },
        "validation_claim": False,
    }


def gci(cases: list[dict]) -> dict:
    by_level = {case["level"]: case for case in cases}
    if set(by_level) != {"coarse", "medium", "fine"}:
        return {"status": "unavailable_missing_grid", "pass": False}
    if not all(case["flow_numerical_gate_pass"] for case in by_level.values()):
        return {"status": "unavailable_unconverged_grid", "pass": False}
    fine, medium, coarse = (by_level[name] for name in ("fine", "medium", "coarse"))
    phi1 = abs(fine["values"]["sink_mass_flow_kg_s"])
    phi2 = abs(medium["values"]["sink_mass_flow_kg_s"])
    phi3 = abs(coarse["values"]["sink_mass_flow_kg_s"])
    h1 = fine["F48_native_tetrahedron_count"] ** (-1.0 / 3.0)
    h2 = medium["F48_native_tetrahedron_count"] ** (-1.0 / 3.0)
    h3 = coarse["F48_native_tetrahedron_count"] ** (-1.0 / 3.0)
    r21, r32 = h2 / h1, h3 / h2
    e21, e32 = phi2 - phi1, phi3 - phi2
    if min(abs(e21), abs(e32), phi1, phi2, phi3) == 0:
        return {"status": "unavailable_zero_difference", "pass": False}
    s = 1.0 if e32 / e21 > 0 else -1.0
    p = 2.0
    converged_order = False
    for _ in range(200):
        numerator = r21**p - s
        denominator = r32**p - s
        if numerator <= 0 or denominator <= 0:
            break
        p_new = abs(math.log(abs(e32 / e21)) + math.log(numerator / denominator)) / math.log(r21)
        if not math.isfinite(p_new) or p_new <= 0 or p_new > 50:
            break
        if abs(p_new - p) < 1e-10:
            p = p_new
            converged_order = True
            break
        p = 0.5 * p + 0.5 * p_new
    if not converged_order:
        return {
            "status": "observed_order_not_converged",
            "refinement_ratios": {"r21_medium_over_fine": r21, "r32_coarse_over_medium": r32},
            "mass_flows_kg_s": {"fine": phi1, "medium": phi2, "coarse": phi3},
            "monotonic": s > 0,
            "pass": False,
        }
    phi_ext = (r21**p * phi1 - phi2) / (r21**p - 1.0)
    ea21 = abs((phi1 - phi2) / phi1)
    ea32 = abs((phi2 - phi3) / phi2)
    gci21 = 1.25 * ea21 / (r21**p - 1.0) * 100.0
    gci32 = 1.25 * ea32 / (r32**p - 1.0) * 100.0
    asymptotic = gci32 / (r21**p * gci21) if gci21 else None
    passed = s > 0 and 0.5 <= p <= 10.0 and gci21 <= 5.0 and asymptotic is not None and 0.9 <= asymptotic <= 1.1
    return {
        "status": "GCI_PASS" if passed else "GCI_FAIL",
        "mass_flows_kg_s": {"fine": phi1, "medium": phi2, "coarse": phi3},
        "refinement_ratios": {"r21_medium_over_fine": r21, "r32_coarse_over_medium": r32},
        "differences_kg_s": {"epsilon21_medium_minus_fine": e21, "epsilon32_coarse_minus_medium": e32},
        "monotonic": s > 0,
        "observed_order": p,
        "Richardson_extrapolated_mass_flow_kg_s": phi_ext,
        "GCI_fine_medium_percent": gci21,
        "GCI_medium_coarse_percent": gci32,
        "asymptotic_ratio": asymptotic,
        "gate_definition": "monotonic, 0.5<=p<=10, GCI_fine<=5%, 0.9<=asymptotic_ratio<=1.1",
        "pass": passed,
    }


def make_flow_plot(case_index: dict[str, dict], output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    colors = {"2V": "#1f77b4", "4V": "#d62728"}
    markers = {"2V": "o", "4V": "s"}
    for ax, screen in zip(axes, ("intake", "exhaust")):
        for variant in ("2V", "4V"):
            rows = sorted(
                [case for case in case_index.values() if case["variant"] == variant and case["screen"] == screen],
                key=lambda case: case["F48_native_tetrahedron_count"],
            )
            x = [case["F48_native_tetrahedron_count"] ** (-1 / 3) for case in rows]
            y = [
                abs(case["values"]["sink_mass_flow_kg_s"])
                if case["values"]["sink_mass_flow_kg_s"] is not None
                else math.nan
                for case in rows
            ]
            ax.plot(x, y, color=colors[variant], linewidth=1.5, alpha=0.7, label=f"{variant}, brut")
            for xx, yy, case in zip(x, y, rows):
                marker = markers[variant] if case["flow_numerical_gate_pass"] else "x"
                ax.scatter([xx], [yy], marker=marker, color=colors[variant], s=58, linewidths=2)
                ax.annotate(case["level"], (xx, yy), xytext=(4, 5), textcoords="offset points", fontsize=8)
        ax.set_title("Admission" if screen == "intake" else "Échappement")
        ax.set_xlabel(r"Taille effective $N^{-1/3}$")
        ax.set_ylabel("|Débit massique| (kg/s)")
        ax.grid(alpha=0.3)
        ax.legend()
    fig.suptitle("Porsche 917 F50 — contrôle OpenFOAM stationnaire incompressible\nΔp = 10 kPa, domaines F48 inchangés; croix = porte numérique fermée")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def make_collapse_plot(diagnostic: dict, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for case_id, case in diagnostic["transient_F49"].items():
        rows = [item["first_crossing"] for item in case["threshold_crossings"] if item["first_crossing"]]
        rows.append({"physical_time_s": case["final_physical_time_s"], "time_step_s": case["minimum_time_step_s"]})
        rows.sort(key=lambda item: item["time_step_s"], reverse=True)
        ax.plot([r["physical_time_s"] * 1000 for r in rows], [r["time_step_s"] for r in rows], marker="o", label=case_id)
    ax.set_yscale("log")
    ax.set_xlabel("Temps physique atteint (ms)")
    ax.set_ylabel("Pas de temps (s, échelle logarithmique)")
    ax.set_title("F49 échappement — effondrement du pas adaptatif\nCo maintenu ≈0,1 par réduction de Δt, pas par convergence")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def make_gate_plot(case_index: dict[str, dict], output: Path) -> None:
    ordered = [case_index[key] for key in sorted(case_index)]
    labels = [case["case_id"] for case in ordered]
    mass = [
        case["values"]["mass_imbalance_percent"]
        if case["values"]["mass_imbalance_percent"] is not None
        else math.nan
        for case in ordered
    ]
    plateau = [
        case["sink_mass_flow_tail_spread_percent"]
        if case["sink_mass_flow_tail_spread_percent"] is not None
        else math.nan
        for case in ordered
    ]
    residual_ratio = []
    for case in ordered:
        fields = case["residuals"]["fields"] or {}
        scaled = [
            fields.get("p") / 1e-6 if fields.get("p") is not None else 1e6,
            *[
                fields.get(name) / 1e-5 if fields.get(name) is not None else 1e6
                for name in ("Ux", "Uy", "Uz", "k", "omega")
            ],
        ]
        residual_ratio.append(max(scaled))
    fig, axes = plt.subplots(3, 1, figsize=(13, 11), constrained_layout=True)
    for ax, values, title in (
        (axes[0], mass, "Déséquilibre massique"),
        (axes[1], plateau, "Dispersion du débit sur les dix derniers points"),
    ):
        colors = ["#2ca02c" if value is not None and value <= 1.0 else "#d62728" for value in values]
        ax.bar(labels, values, color=colors)
        ax.axhline(1.0, color="black", linestyle="--", linewidth=1.2, label="porte 1 %")
        ax.set_yscale("log")
        ax.set_ylabel("%")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
        ax.legend()
        ax.tick_params(axis="x", rotation=35)
    colors = ["#2ca02c" if value <= 1.0 else "#d62728" for value in residual_ratio]
    axes[2].bar(labels, residual_ratio, color=colors)
    axes[2].axhline(1.0, color="black", linestyle="--", linewidth=1.2, label="porte normalisée")
    axes[2].set_yscale("log")
    axes[2].set_ylabel("max(résidu / seuil)")
    axes[2].set_title("Résidu le plus contraignant, normalisé par son seuil")
    axes[2].grid(axis="y", alpha=0.25, which="both")
    axes[2].legend()
    axes[2].tick_params(axis="x", rotation=35)
    fig.suptitle("Porsche 917 F50 — contrôles numériques stationnaires\nVert = sous la porte; rouge = porte fermée")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--f49-report", type=Path, required=True)
    parser.add_argument("--incompressible-report", action="append", type=Path, required=True)
    parser.add_argument("--incompressible-execution-site", choices=("kali", "vast"), required=True)
    parser.add_argument("--execution-bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnostic = json.loads(args.diagnostic.read_text(encoding="utf-8"))
    f49 = json.loads(args.f49_report.read_text(encoding="utf-8"))
    cases = []
    inputs = []
    runtime_authorities = []
    for path in args.incompressible_report:
        report = json.loads(path.read_text(encoding="utf-8"))
        require(report["ellipse_or_oval_proxy_used"] is False, f"proxy_interdit:{path}")
        require(report["outer_or_inner_geometry_modified"] is False, f"geometrie_modifiee:{path}")
        cases.extend(report["cases"])
        inputs.append({"filename": path.name, "sha256": sha256(path), "case_count": len(report["cases"])})
        runtime_authorities.append(
            {
                "openfoam_environment": report["openfoam_environment"],
                "image_expected": report["image_expected"],
                "image_id_expected": report["image_id_expected"],
            }
        )
    require(len(cases) == 12, f"matrice_incomplete:{len(cases)}")
    require(len({case["case_id"] for case in cases}) == 12, "cas_dupliques")
    expected = {f"{variant.lower()}-{level}-{screen}" for variant in ("2V", "4V") for level in ("coarse", "medium", "fine") for screen in ("intake", "exhaust")}
    require({case["case_id"] for case in cases} == expected, "matrice_cas_incorrecte")
    require(all(item == runtime_authorities[0] for item in runtime_authorities), "autorite_runtime_incoherente")
    require(args.execution_bundle.is_file(), f"bundle_execution_introuvable:{args.execution_bundle}")
    case_index = {case["case_id"]: sanitise_case(case) for case in cases}
    grid = {}
    for variant in ("2V", "4V"):
        grid[variant] = {}
        for screen in ("intake", "exhaust"):
            grid[variant][screen] = gci([case for case in case_index.values() if case["variant"] == variant and case["screen"] == screen])
    variant_comparison = {}
    for screen in ("intake", "exhaust"):
        variant_comparison[screen] = {}
        for level in ("coarse", "medium", "fine"):
            c2 = case_index[f"2v-{level}-{screen}"]
            c4 = case_index[f"4v-{level}-{screen}"]
            raw_m2 = c2["values"]["sink_mass_flow_kg_s"]
            raw_m4 = c4["values"]["sink_mass_flow_kg_s"]
            m2 = abs(raw_m2) if raw_m2 is not None else None
            m4 = abs(raw_m4) if raw_m4 is not None else None
            variant_comparison[screen][level] = {
                "2V_mass_flow_kg_s": m2,
                "4V_mass_flow_kg_s": m4,
                "4V_minus_2V_percent": (m4 / m2 - 1.0) * 100.0 if m2 not in (None, 0.0) and m4 is not None else None,
                "both_flow_numerical_gates_pass": c2["flow_numerical_gate_pass"] and c4["flow_numerical_gate_pass"],
                "performance_claim": False,
            }
    cross_method = {}
    for case_id, steady in case_index.items():
        transient = f49["case_index"].get(case_id)
        if transient is None:
            cross_method[case_id] = {"status": "unavailable_F49_case_missing", "pass": False}
            continue
        transient_flow = transient.get("values", {}).get("sink_mass_flow_kg_s")
        steady_flow = steady["values"]["sink_mass_flow_kg_s"]
        raw_delta = None
        if transient_flow not in (None, 0.0) and steady_flow is not None:
            raw_delta = (abs(steady_flow) / abs(transient_flow) - 1.0) * 100.0
        cross_method[case_id] = {
            "status": "unavailable_F49_not_converged",
            "raw_difference_percent_not_validated": raw_delta,
            "F49_converged_claim": transient.get("converged_claim", False),
            "F50_incompressible_flow_numerical_gate_pass": steady["flow_numerical_gate_pass"],
            "pass": False,
        }
    flow_image = output_dir / "917-f50-incompressible-grid-comparison.png"
    collapse_image = output_dir / "917-f50-transient-timestep-collapse.png"
    gate_image = output_dir / "917-f50-incompressible-numerical-gates.png"
    make_flow_plot(case_index, flow_image)
    make_collapse_plot(diagnostic, collapse_image)
    make_gate_plot(case_index, gate_image)
    csv_path = output_dir / "917-f50-incompressible-cases.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["case_id", "cells", "sink_mass_flow_kg_s", "mass_imbalance_percent", "plateau_percent", "flow_gate_pass", "energy_gate_applicable"])
        for case_id in sorted(case_index):
            case = case_index[case_id]
            writer.writerow([
                case_id,
                case["F48_native_tetrahedron_count"],
                case["values"]["sink_mass_flow_kg_s"],
                case["values"]["mass_imbalance_percent"],
                case["sink_mass_flow_tail_spread_percent"],
                case["flow_numerical_gate_pass"],
                False,
            ])
    all_flow = all(case["flow_numerical_gate_pass"] for case in case_index.values())
    all_gci = all(grid[variant][screen]["pass"] for variant in grid for screen in grid[variant])
    if all_flow and all_gci:
        overall_status = "FLOW_AND_THREE_GRID_GATES_PASS_ENERGY_AND_CROSS_METHOD_RED"
    elif all_flow:
        overall_status = "FLOW_CASE_GATES_PASS_THREE_GRID_GCI_FAIL_CLOSED"
    else:
        overall_status = "CFD_RECOVERY_FAIL_CLOSED"
    report = {
        "schema_version": "porsche-917-f50-cfd-recovery-public/v1",
        "status": overall_status,
        "inputs": inputs,
        "diagnostic": {"sha256": sha256(args.diagnostic), "summary": diagnostic},
        "F49_public_report_sha256": sha256(args.f49_report),
        "source_artifacts": {
            name: artifact(root, path)
            for name, path in {
                "contract": "twins/reference-917-engine/f50-cfd-recovery-contract.json",
                "steady_compressible_contract": "twins/reference-917-engine/f50-steady-cfd-contract.json",
                "F48_domain_report": "twins/reference-917-engine/evidence/f48-cfd-domains/f48-cfd-domain-report.json",
                "F49_boundary_condition_contract": "twins/reference-917-engine/f49-cfd-cht-contract.json",
                "F49_public_report": "twins/reference-917-engine/evidence/f49-cfd-cht/f49-cfd-cht-report.json",
                "transient_diagnostic": "twins/reference-917-engine/source/diagnose_cfd_recovery_f50.py",
                "steady_compressible_builder": "twins/reference-917-engine/source/build_cfd_cases_f50_steady.py",
                "steady_compressible_runner": "twins/reference-917-engine/source/run_cfd_cases_f50_steady.py",
                "incompressible_builder": "twins/reference-917-engine/source/build_cfd_cases_f50_incompressible.py",
                "incompressible_runner": "twins/reference-917-engine/source/run_cfd_cases_f50_incompressible.py",
                "publisher": "twins/reference-917-engine/source/publish_cfd_recovery_f50.py",
            }.items()
        },
        "runtime_authority": runtime_authorities[0],
        "compute_provenance": {
            "transient_diagnostic_site": "kali",
            "steady_compressible_attempt_site": "kali",
            "steady_incompressible_matrix_site": args.incompressible_execution_site,
            "execution_bundle": {
                "filename": args.execution_bundle.name,
                "bytes": args.execution_bundle.stat().st_size,
                "sha256": sha256(args.execution_bundle),
            },
        },
        "method": {
            "software": "OpenFOAM Foundation 14",
            "solver": "foamRun -solver incompressibleFluid",
            "formulation": "steady incompressible RANS kOmegaSST",
            "physical_pressure_difference_pa": 10000.0,
            "density_model": "one constant ideal-gas source-state density per screen",
            "energy_equation_solved": False,
        },
        "case_count": len(case_index),
        "case_index": case_index,
        "normalizations": {
            "legacy_execution_status": "all selected runner inputs retained prepared_not_run from the build manifest; public cases are normalized to EXECUTED only after a recorded foamRun command and log hash are required"
        },
        "three_grid_GCI": grid,
        "variant_comparison": variant_comparison,
        "cross_method_F49_transient_vs_F50_incompressible": cross_method,
        "gates": {
            "all_12_flow_numerical_gates_pass": all_flow,
            "all_four_three_grid_GCI_gates_pass": all_gci,
            "mass_balance_all_below_1_percent": all(case["gates"]["mass"] for case in case_index.values()),
            "residual_and_plateau_all_pass": all(case["gates"]["residuals"] and case["gates"]["plateau"] for case in case_index.values()),
            "energy_balance_below_1_percent": False,
            "cross_method_agreement_below_5_percent": False,
            "conjugate_CHT_executed": False,
            "manufacturing_authorized": False,
            "engine_start_authorized": False,
        },
        "limitations": [
            "incompressible control has no energy equation, so the strict energy gate is unavailable",
            "F49 transient and F50 steady-compressible exhaust formulations diverged",
            "F49 transient cases are not converged, so cross-method differences are not validation evidence",
            "F48 domains are analytic gas volumes under an unverified 1 scan unit = 1 mm assumption",
            "no solid domain, conjugate heat transfer, moving valves, piston, combustion or physical correlation is present",
        ],
        "geometry_modified": False,
        "ellipse_or_oval_proxy_used": False,
        "Vast_used": args.incompressible_execution_site == "vast",
        "images": {
            "grid_comparison": {"path": str(flow_image.relative_to(root)), "sha256": sha256(flow_image)},
            "time_step_collapse": {"path": str(collapse_image.relative_to(root)), "sha256": sha256(collapse_image)},
            "numerical_gates": {"path": str(gate_image.relative_to(root)), "sha256": sha256(gate_image)},
        },
        "csv": {"path": str(csv_path.relative_to(root)), "sha256": sha256(csv_path)},
        "validation_claim": False,
    }
    report_path = output_dir / "f50-cfd-recovery-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    publication = {
        "schema_version": "porsche-917-f50-cfd-recovery-publication/v1",
        "report": {"path": str(report_path.relative_to(root)), "sha256": sha256(report_path)},
        "diagnostic_input_sha256": sha256(args.diagnostic),
        "incompressible_execution_inputs": inputs,
        "incompressible_execution_site": args.incompressible_execution_site,
        "execution_bundle_sha256": sha256(args.execution_bundle),
        "published_files": [
            {"path": str(path.relative_to(root)), "sha256": sha256(path)}
            for path in (report_path, csv_path, flow_image, collapse_image, gate_image)
        ],
        "raw_mesh_or_scan_published": False,
        "geometry_modified": False,
        "ellipse_or_oval_proxy_used": False,
        "validation_claim": False,
    }
    publication_path = output_dir / "publication.json"
    publication_path.write_text(json.dumps(publication, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "sha256": sha256(report_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
