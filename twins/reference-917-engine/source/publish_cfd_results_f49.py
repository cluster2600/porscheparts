#!/usr/bin/env python3
"""Agrège et publie les preuves OpenFOAM F49 sans champs bruts ni géométrie."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def pct_change(new: float, reference: float) -> float:
    return (new / reference - 1.0) * 100.0


def ideal_gas_mass_flow(p0: float, p2: float, temperature: float, area_m2: float) -> dict:
    gamma = 1.4
    gas_constant = 287.05
    ratio = p2 / p0
    critical = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    if ratio <= critical:
        flux = p0 / math.sqrt(temperature) * math.sqrt(gamma / gas_constant) * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        regime = "choked"
    else:
        flux = p0 / math.sqrt(temperature) * math.sqrt(
            2.0 * gamma / (gas_constant * (gamma - 1.0))
            * (ratio ** (2.0 / gamma) - ratio ** ((gamma + 1.0) / gamma))
        )
        regime = "subcritical"
    return {
        "gamma": gamma,
        "specific_gas_constant_j_kg_k": gas_constant,
        "pressure_ratio": ratio,
        "critical_pressure_ratio": critical,
        "regime": regime,
        "limiting_area_m2": area_m2,
        "Cd_assumed": 1.0,
        "ideal_upper_bound_mass_flow_kg_s": flux * area_m2,
        "role": "one_dimensional_inviscid_upper_bound_not_a_second_CFD_solution",
    }


def convergence_from_record(record: dict, targets: dict) -> dict:
    fields = record.get("residuals", {}).get("fields") or {}
    checks = {
        "p": fields.get("p") is not None and fields["p"] <= targets["p"],
        "U": all(fields.get(name) is not None and fields[name] <= targets["U"] for name in ("Ux", "Uy", "Uz")),
        "k": fields.get("k") is not None and fields["k"] <= targets["k"],
        "omega": fields.get("omega") is not None and fields["omega"] <= targets["omega"],
        "h": fields.get("h") is not None and fields["h"] <= targets["h"],
    }
    return {"residual_checks": checks, "residual_gate_pass": all(checks.values())}


def reassess_corrective_energy(record: dict, threshold_percent: float) -> None:
    values = record["values"]
    m_source = values.get("source_mass_flow_kg_s")
    m_sink = values.get("sink_mass_flow_kg_s")
    source_terms = values.get("source_total_energy_terms")
    sink_terms = values.get("sink_total_energy_terms")
    wall_flux = values.get("wall_heat_flux_integral_w")
    storage = values.get("unsteady_total_energy_storage") or {}
    sensible_storage = storage.get("finite_difference_storage_rate_w")
    if None in (m_source, m_sink, wall_flux, sensible_storage) or not source_terms or not sink_terms:
        values["energy_balance_residual_w"] = None
        values["approximate_energy_imbalance_percent"] = None
        record["approximate_energy_balance_gate_pass"] = False
        return
    cp = 1005.0
    tref = 298.15
    source_ht_absolute = cp * source_terms[0] + 0.5 * source_terms[1]
    sink_ht_absolute = cp * sink_terms[0] + 0.5 * sink_terms[1]
    net_advective_out = m_source * source_ht_absolute + m_sink * sink_ht_absolute
    mass_storage = -(m_source + m_sink)
    reference_storage = cp * tref * mass_storage
    absolute_storage = sensible_storage + reference_storage
    residual = absolute_storage + net_advective_out - wall_flux
    denominator = max(abs(absolute_storage), abs(net_advective_out), abs(wall_flux), 1.0)
    storage.update(
        {
            "mass_storage_rate_from_boundary_flux_kg_s": mass_storage,
            "OpenFOAM_hConst_default_Tref_k": tref,
            "enthalpy_reference_storage_rate_w": reference_storage,
            "absolute_total_energy_storage_rate_w": absolute_storage,
        }
    )
    values.update(
        {
            "source_specific_total_enthalpy_j_kg": source_ht_absolute,
            "sink_specific_total_enthalpy_j_kg": sink_ht_absolute,
            "net_advective_total_enthalpy_out_w": net_advective_out,
            "unsteady_total_energy_storage": storage,
            "energy_balance_sign_convention": "absolute_storage + outward_advective_total_enthalpy - wallHeatFlux_reported",
            "energy_balance_residual_w": residual,
            "approximate_energy_imbalance_percent": abs(residual) / denominator * 100.0,
            "energy_balance_publication_reassessment": "reference-invariant correction using OpenFOAM hConst default Tref and boundary mass storage",
        }
    )
    record["approximate_energy_balance_gate_pass"] = (
        record["solver_return_code_zero"] and values["approximate_energy_imbalance_percent"] <= threshold_percent
    )


def render(report: dict, output: Path) -> list[Path]:
    colors = {"2V": "#c86b31", "4V": "#2a7f9e"}
    levels = ("coarse", "medium")
    screens = ("intake", "exhaust")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for axis, screen in zip(axes, screens):
        for variant in ("2V", "4V"):
            records = [report["case_index"][f"{variant.lower()}-{level}-{screen}"] for level in levels]
            if all(item["solver_return_code_zero"] for item in records):
                flow = [abs(item["values"]["sink_mass_flow_kg_s"]) for item in records]
                axis.plot(levels, flow, marker="o", linestyle="none", markersize=8, label=variant, color=colors[variant])
        if not axis.lines:
            axis.text(
                0.5,
                0.5,
                "Aucun résultat comparable\n(échec ou horizon non atteint)",
                ha="center",
                va="center",
                transform=axis.transAxes,
            )
        axis.set_title(f"Écran {screen} — Δp imposé 10 kPa")
        axis.set_ylabel("Débit massique [kg/s]")
        axis.grid(alpha=0.25)
        if axis.lines:
            axis.legend()
    fig.suptitle("F49 — OpenFOAM 14, points bruts non convergés (contrôles de grille différents)", fontweight="bold")
    flow_path = output / "917-f49-openfoam-flow-comparison.png"
    fig.savefig(flow_path, dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for axis, screen in zip(axes, screens):
        labels = []
        imbalance = []
        residual = []
        for variant in ("2V", "4V"):
            for level in levels:
                item = report["case_index"][f"{variant.lower()}-{level}-{screen}"]
                labels.append(f"{variant}\n{level[0].upper()}")
                imbalance.append(item["values"]["mass_imbalance_percent"] if item["solver_return_code_zero"] else math.nan)
                fields = item.get("residuals", {}).get("fields") or {}
                residual.append(max(value for key, value in fields.items() if key != "time" and value is not None))
        x = list(range(len(labels)))
        bar_colors = ["#b23a48" if not math.isnan(value) and value > 1.0 else "#c4a35a" for value in imbalance]
        axis.bar(x, imbalance, color=bar_colors, label="déséquilibre masse [%]")
        if all(math.isnan(value) for value in imbalance):
            axis.text(0.5, 0.5, "Aucun bilan valide\n(échec solveur)", ha="center", va="center", transform=axis.transAxes)
        axis.set_xticks(x, labels)
        axis.set_yscale("log")
        axis.axhline(1.0, color="#b23a48", linestyle="--", label="seuil 1 %")
        axis.set_title(f"Bilans {screen}")
        axis.set_ylabel("Déséquilibre masse [%], échelle log")
        axis.grid(axis="y", alpha=0.25)
        axis.legend(fontsize=8)
    fig.suptitle("F49 — contrôle numérique réel; CHT et convergence trois grilles absentes", fontweight="bold")
    gate_path = output / "917-f49-numerical-gates.png"
    fig.savefig(gate_path, dpi=180)
    plt.close(fig)
    return [flow_path, gate_path]


def publish(project_root: Path, work_root: Path, output: Path) -> dict:
    contract_path = project_root / "twins/reference-917-engine/f49-cfd-cht-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    correction_path = project_root / "twins/reference-917-engine/f49-cfd-cht-corrective-coarse.json"
    correction = json.loads(correction_path.read_text(encoding="utf-8"))
    require(correction["base_contract"]["sha256"] == sha256(contract_path), "correction_base_hash_mismatch")
    runtime_policy_path = project_root / "twins/reference-917-engine/f49-cfd-cht-runtime-policy.json"
    runtime_policy = json.loads(runtime_policy_path.read_text(encoding="utf-8"))
    require(
        runtime_policy["bound_inputs"]["base_contract_sha256"] == sha256(contract_path),
        "runtime_policy_base_hash_mismatch",
    )
    require(
        runtime_policy["bound_inputs"]["executed_corrective_profile_sha256"] == sha256(correction_path),
        "runtime_policy_correction_hash_mismatch",
    )
    for name in ("builder_without_residualControl", "runner", "failed_rerun_summarizer"):
        runtime_artifact = runtime_policy["bound_inputs"][name]
        require(
            sha256(project_root / runtime_artifact["path"]) == runtime_artifact["sha256"],
            f"runtime_policy_{name}_hash_mismatch",
        )
    require(runtime_policy["PIMPLE_residualControl_early_stop_enabled"] is False, "residual_early_stop_must_be_disabled")
    aate_path = work_root / "aate-binary-smoke.json"
    require(aate_path.is_file(), "aate_binary_smoke_absent")
    aate_smoke = json.loads(aate_path.read_text(encoding="utf-8"))
    require(aate_smoke["framework_revision"] == contract["aate_icengines"]["framework_revision"], "aate_revision_mismatch")
    require(all(item["help_return_code"] == 0 for item in aate_smoke["binaries"].values()), "aate_binary_smoke_failed")
    require(aate_smoke["engine_case_executed"] is False, "aate_case_claim_forbidden")
    execution_paths = sorted(work_root.glob("execution-*.json"))
    require(len(execution_paths) == 4, f"execution_report_count:{len(execution_paths)}")
    initial_cases = []
    execution_inputs = []
    for path in execution_paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        require(raw["contract_sha256"] == sha256(contract_path), f"contract_hash_mismatch:{path.name}")
        require(raw["AATE_dynamic_engine_case_executed"] is False, "aate_claim_forbidden")
        require(raw["conjugate_CHT_executed"] is False, "cht_claim_forbidden")
        execution_inputs.append({"filename": path.name, "sha256": sha256(path)})
        require(raw.get("numerical_correction_sha256") in (None, ""), "initial_report_cannot_claim_correction")
        initial_cases.extend(raw["cases"])
    require(len(initial_cases) == 8, f"initial_executed_case_count:{len(initial_cases)}")
    initial_index = {case["case_id"]: case for case in initial_cases}
    expected = {f"{variant.lower()}-{level}-{screen}" for variant in ("2V", "4V") for level in ("coarse", "medium") for screen in ("intake", "exhaust")}
    require(set(initial_index) == expected, f"initial_case_matrix_mismatch:{sorted(set(initial_index) ^ expected)}")
    corrective_paths = sorted(work_root.glob("corrective-[24]V-coarse-*.json"))
    require(len(corrective_paths) == 4, f"corrective_report_count:{len(corrective_paths)}")
    first_corrective_cases = []
    corrective_inputs = []
    corrective_environments = []
    correction_sha256 = sha256(correction_path)
    for path in corrective_paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        require(raw["contract_sha256"] == sha256(contract_path), f"corrective_contract_hash_mismatch:{path.name}")
        require(raw.get("numerical_correction_sha256") == correction_sha256, f"correction_hash_mismatch:{path.name}")
        environment = raw.get("openfoam_environment") or {}
        require(environment.get("configDict") == "/opt/openfoam14/etc/configDict", f"openfoam_configDict_unproved:{path.name}")
        corrective_environments.append(environment)
        corrective_inputs.append({"filename": path.name, "sha256": sha256(path)})
        first_corrective_cases.extend(raw["cases"])
    expected_corrective = {f"{variant.lower()}-coarse-{screen}" for variant in ("2V", "4V") for screen in ("intake", "exhaust")}
    first_corrective_index = {case["case_id"]: case for case in first_corrective_cases}
    require(
        set(first_corrective_index) == expected_corrective,
        f"corrective_case_matrix_mismatch:{sorted(set(first_corrective_index) ^ expected_corrective)}",
    )
    rerun_failure_path = work_root / "corrective-rerun-failures.json"
    require(rerun_failure_path.is_file(), "corrective_exhaust_rerun_failure_report_absent")
    rerun_failure = json.loads(rerun_failure_path.read_text(encoding="utf-8"))
    require(rerun_failure["contract_sha256"] == sha256(contract_path), "corrective_rerun_contract_hash_mismatch")
    require(
        rerun_failure.get("numerical_correction_sha256") == correction_sha256,
        "corrective_rerun_profile_hash_mismatch",
    )
    require(rerun_failure["Vast_used"] is False, "corrective_rerun_vast_claim_forbidden")
    corrective_inputs.append({"filename": rerun_failure_path.name, "sha256": sha256(rerun_failure_path)})
    rerun_cases = rerun_failure["cases"]
    rerun_index = {case["case_id"]: case for case in rerun_cases}
    expected_rerun = {"2v-coarse-exhaust", "4v-coarse-exhaust"}
    require(set(rerun_index) == expected_rerun, f"corrective_rerun_matrix_mismatch:{sorted(set(rerun_index) ^ expected_rerun)}")
    require(
        all(
            case["status"] == "TIME_STEP_COLLAPSE_FAIL"
            and case["minimum_horizon_reached"] is False
            and case["PIMPLE_residualControl_present"] is False
            for case in rerun_cases
        ),
        "corrective_rerun_failure_not_proved",
    )
    corrective_index = dict(first_corrective_index)
    corrective_cases = list(corrective_index.values())
    require(all(environment == corrective_environments[0] for environment in corrective_environments), "corrective_environment_mismatch")
    for case in corrective_cases:
        reassess_corrective_energy(case, contract["comparison_gates"]["approximate_energy_imbalance_percent_at_most"])
    index = dict(initial_index)
    index.update(corrective_index)
    cases = list(index.values())
    minimum_horizon = runtime_policy["minimum_physical_time_before_positive_stop_s"]
    for case in cases:
        case["convergence_assessment"] = convergence_from_record(case, contract["openfoam"]["residual_targets"])
        final_time = (case.get("residuals", {}).get("fields") or {}).get("time")
        minimum_horizon_reached = final_time is not None and final_time >= minimum_horizon - 1.0e-12
        case["convergence_assessment"]["minimum_physical_horizon_s"] = minimum_horizon
        case["convergence_assessment"]["final_sample_time_s"] = final_time
        case["convergence_assessment"]["minimum_horizon_reached"] = minimum_horizon_reached
        positive_stop_checks = {
            "minimum_horizon_reached": minimum_horizon_reached,
            "final_window_mass_flow_plateau": bool(
                case.get("convergence_screen", {}).get("sink_mass_flow_plateau_at_most_1_percent", False)
            ),
            "mass_balance_gate_pass": bool(case.get("mass_balance_gate_pass", False)),
            "total_enthalpy_balance_gate_pass": bool(case.get("approximate_energy_balance_gate_pass", False)),
            "residual_gate_pass": case["convergence_assessment"]["residual_gate_pass"],
        }
        case["convergence_assessment"]["positive_stop_checks"] = positive_stop_checks
        case["convergence_assessment"]["positive_stop_gate_pass"] = all(positive_stop_checks.values())
        if case in first_corrective_cases and not minimum_horizon_reached:
            case["convergence_assessment"]["interpretation"] = "premature_residualControl_stop_preserved_as_failed_smoke"
        case["temperature_constraint_activation_quantified"] = False
        case["converged_claim"] = False

    f48_report = json.loads((project_root / contract["authority"]["F48_public_mesh_report"]["path"]).read_text(encoding="utf-8"))
    analytic = {}
    for variant in ("2V", "4V"):
        analytic[variant] = {}
        patches = f48_report["gas_domains"][variant]["medium"]["patches"]
        for screen_name, screen in contract["openfoam"]["screens"].items():
            source_area = patches[screen["source_patch"]]["surface_area_scan_units_squared"]
            sink_area = patches[screen["sink_patch"]]["surface_area_scan_units_squared"]
            area_m2 = min(source_area, sink_area) * 1.0e-6
            bound = ideal_gas_mass_flow(
                screen["source_total_pressure_pa_abs"],
                screen["sink_static_pressure_pa_abs"],
                screen["source_temperature_k"],
                area_m2,
            )
            medium = index[f"{variant.lower()}-medium-{screen_name}"]
            bound["OpenFOAM_medium_to_ideal_ratio"] = (
                abs(medium["values"]["sink_mass_flow_kg_s"]) / bound["ideal_upper_bound_mass_flow_kg_s"]
                if medium["solver_return_code_zero"]
                else None
            )
            analytic[variant][screen_name] = bound

    comparisons = {}
    for screen in ("intake", "exhaust"):
        comparisons[screen] = {}
        for level in ("coarse", "medium"):
            two = index[f"2v-{level}-{screen}"]
            four = index[f"4v-{level}-{screen}"]
            if (
                two["solver_return_code_zero"]
                and four["solver_return_code_zero"]
                and two["convergence_assessment"]["minimum_horizon_reached"]
                and four["convergence_assessment"]["minimum_horizon_reached"]
            ):
                m2 = abs(two["values"]["sink_mass_flow_kg_s"])
                m4 = abs(four["values"]["sink_mass_flow_kg_s"])
                comparisons[screen][level] = {
                    "status": "available_unconverged_static_screen_no_performance_claim",
                    "imposed_pressure_difference_pa": contract["openfoam"]["screens"][screen]["imposed_pressure_difference_pa"],
                    "2V_mass_flow_kg_s": m2,
                    "4V_mass_flow_kg_s": m4,
                    "4V_minus_2V_mass_flow_percent": pct_change(m4, m2),
                    "interpretation": "static_screen_conductance_only",
                }
            else:
                comparisons[screen][level] = {
                    "status": "unavailable_solver_failure_or_minimum_horizon_not_reached",
                    "2V_solver_return_code_zero": two["solver_return_code_zero"],
                    "4V_solver_return_code_zero": four["solver_return_code_zero"],
                    "2V_minimum_horizon_reached": two["convergence_assessment"]["minimum_horizon_reached"],
                    "4V_minimum_horizon_reached": four["convergence_assessment"]["minimum_horizon_reached"],
                }
        grid_records = {}
        for variant in ("2V", "4V"):
            coarse = index[f"{variant.lower()}-coarse-{screen}"]
            medium = index[f"{variant.lower()}-medium-{screen}"]
            grid_records[variant] = (
                {
                    "status": "unavailable_mixed_numerical_controls",
                    "mass_flow_change_percent": None,
                }
                if coarse["solver_return_code_zero"] and medium["solver_return_code_zero"]
                else {"status": "unavailable_solver_failure"}
            )
        comparisons[screen]["coarse_to_medium"] = grid_records

    report = {
        "schema_version": "porsche-917-f49-public-cfd-cht-evidence/v1",
        "status": "OPENFOAM_STATIC_SCREENS_EXECUTED_FAIL_CLOSED_NO_AATE_ENGINE_CASE_NO_CHT",
        "contract": {"path": str(contract_path.relative_to(project_root)), "sha256": sha256(contract_path)},
        "corrective_coarse_contract": {"path": str(correction_path.relative_to(project_root)), "sha256": correction_sha256},
        "runtime_policy": {
            "path": str(runtime_policy_path.relative_to(project_root)),
            "sha256": sha256(runtime_policy_path),
            "PIMPLE_residualControl_early_stop_enabled": runtime_policy["PIMPLE_residualControl_early_stop_enabled"],
            "minimum_physical_time_before_positive_stop_s": minimum_horizon,
            "maximum_authorized_future_horizon_s": runtime_policy["maximum_authorized_future_horizon_s"],
            "positive_stop_requires_all": runtime_policy["positive_stop_requires_all"],
        },
        "corrective_Courant_guard": {
            "configured_target": correction["numerical_controls"]["maximum_Courant_number"],
            "control_tolerance_fraction": 0.005,
            "maximum_accepted_observed": correction["numerical_controls"]["maximum_Courant_number"] * 1.005,
            "rationale": "explicit 0.5 percent controller/decimal tolerance; exact maximum remains published",
        },
        "execution_inputs": execution_inputs,
        "corrective_execution_inputs": corrective_inputs,
        "corrective_openfoam_environment": corrective_environments[0],
        "AATE_binary_smoke": {**aate_smoke, "sha256": sha256(aate_path)},
        "image_execution_evidence": {
            "name": "3dprinting993-cfd-cae-f47:kali-local",
            "image_id": "sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17",
            "platform": "linux/amd64",
            "host": "Kali 192.168.2.3",
            "registry_digest_verified": False,
        },
        "case_count": len(cases),
        "solver_attempt_count_including_superseded": len(initial_cases) + len(first_corrective_cases) + len(rerun_cases),
        "superseded_initial_coarse_attempts": {
            case_id: {
                "solver_return_code_zero": initial_index[case_id]["solver_return_code_zero"],
                "status": initial_index[case_id]["status"],
            }
            for case_id in sorted(expected_corrective)
        },
        "superseded_corrective_exhaust_early_stops": {
            case_id: {
                "solver_return_code_zero": first_corrective_index[case_id]["solver_return_code_zero"],
                "final_sample_time_s": (first_corrective_index[case_id].get("residuals", {}).get("fields") or {}).get("time"),
                "status": "FAILED_SMOKE_PREMATURE_RESIDUAL_CONTROL_STOP",
            }
            for case_id in sorted(expected_rerun)
        },
        "failed_full_horizon_exhaust_reruns": rerun_index,
        "bounded_corrective_plan": {
            "observed_failure_class": "time_step_collapse_after_numerical_instability",
            "physical_cause_established": False,
            "ordered_actions": [
                "locate the first divergence among U, h, k and omega and correlate it with patch flux direction",
                "audit source/sink thermodynamic values and reversed-flow boundary behavior",
                "initialize from a conservative cold-flow solution instead of a uniform hot start",
                "test a source-temperature ramp and a wall-treatment formulation in a new numerical contract",
                "repeat the 5 ms local smoke with unchanged mass, energy, residual and Courant gates",
            ],
            "Vast_expected_to_fix_numerical_instability_automatically": False,
            "Vast_remains_forbidden_until_local_5ms_smoke_reaches_horizon": True,
        },
        "case_index": index,
        "comparisons": comparisons,
        "independent_analytic_method": analytic,
        "gates": {
            "all_eight_solvers_return_code_zero": all(case["solver_return_code_zero"] for case in cases),
            "solver_attempt_count": len(initial_cases) + len(first_corrective_cases) + len(rerun_cases),
            "selected_case_count": len(cases),
            "solver_return_code_zero_count": sum(bool(case["solver_return_code_zero"]) for case in cases),
            "corrective_patch_type_audits_pass": all(case.get("patch_type_audit", {}).get("pass", False) for case in corrective_cases),
            "corrective_observed_Courant_within_target_plus_0_5_percent": all(
                case.get("Courant_number", {}).get("maximum_reported") is not None
                and case["Courant_number"]["maximum_reported"] <= correction["numerical_controls"]["maximum_Courant_number"] * 1.005
                for case in corrective_cases
            ),
            "corrective_unsteady_energy_storage_available": all(
                case.get("values", {}).get("unsteady_total_energy_storage", {}).get("finite_difference_storage_rate_w") is not None
                for case in corrective_cases
            ),
            "corrective_minimum_horizon_reached": all(
                case["convergence_assessment"]["minimum_horizon_reached"] for case in corrective_cases
            ),
            "PIMPLE_residualControl_early_stop_disabled_for_future_runs": (
                runtime_policy["PIMPLE_residualControl_early_stop_enabled"] is False
            ),
            "combined_positive_stop_gate_implemented_in_post_processing": True,
            "all_combined_positive_stop_gates_pass": all(
                case["convergence_assessment"]["positive_stop_gate_pass"] for case in cases
            ),
            "all_openfoam_mesh_gates_pass": all(case["mesh_gate_pass"] for case in cases),
            "all_mass_balance_gates_pass": all(case["mass_balance_gate_pass"] for case in cases),
            "all_approximate_energy_balance_gates_pass": all(case["approximate_energy_balance_gate_pass"] for case in cases),
            "all_residual_gates_pass": all(case["convergence_assessment"]["residual_gate_pass"] for case in cases),
            "temperature_constraint_activation_quantified": False,
            "three_grid_solution_available": False,
            "three_grid_convergence_pass": False,
            "AATE_dynamic_engine_case_executed": False,
            "cross_method_agreement_pass": False,
            "conjugate_CHT_executed": False,
            "thermal_CHT_validated": False,
            "fitment_validated": False,
            "manufacturing_authorized": False,
            "engine_start_authorized": False,
        },
        "limitations": [
            "F48 is an analytic gas volume and does not contain the unchanged F43 external skin or a solid head.",
            "The 10 kPa differential is imposed; it is not a predicted engine pressure loss.",
            "The pressure screens are not crank-angle-resolved firing-cycle simulations.",
            "F47 min/max envelopes are comparison bounds, not boundary conditions.",
            "No solid region means no conjugate heat transfer, metal temperature or thermal stress result.",
            "AATE cannot run a truthful moving-engine case without piston/valve surfaces and measured motion laws.",
            "Only coarse and medium solutions were executed; fine cases are prepared but not run.",
            "Corrective coarse and initial medium use different numerical controls; grid convergence is therefore unavailable.",
            "The two corrective exhaust smokes stopped before 5 ms through the now-disabled PIMPLE residualControl; both remain failed smokes and cannot support a flow comparison.",
            "Residuals are metrics only in the corrected runtime policy; a future positive stop requires the minimum horizon, final-window plateau, mass, total-enthalpy and residual gates together.",
            "The F48 reference volume is exact OCC mass while OpenFOAM integrates the converted linear tetrahedra; the 4V coarse 1.5 percent deviation is a discretization/conversion gate failure, not a geometry repair.",
        ],
        "validation_claim": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    public_aate_path = output / "aate-binary-smoke.json"
    shutil.copyfile(aate_path, public_aate_path)
    report_path = output / "f49-cfd-cht-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    images = render(report, output)
    publication = {
        "schema_version": "porsche-917-f49-publication/v1",
        "files": {
            "report": {"path": str(report_path.relative_to(project_root)), "sha256": sha256(report_path)},
            "aate_binary_smoke": {"path": str(public_aate_path.relative_to(project_root)), "sha256": sha256(public_aate_path)},
            **{path.stem: {"path": str(path.relative_to(project_root)), "sha256": sha256(path)} for path in images},
        },
        "raw_mesh_or_field_committed": False,
    }
    publication_path = output / "publication.json"
    publication_path.write_text(json.dumps(publication, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("twins/reference-917-engine/evidence/f49-cfd-cht"))
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    output = args.output if args.output.is_absolute() else project_root / args.output
    report = publish(project_root, args.work_root.resolve(), output.resolve())
    print(json.dumps({"status": report["status"], "case_count": report["case_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
