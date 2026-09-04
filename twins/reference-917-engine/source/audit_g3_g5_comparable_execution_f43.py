#!/usr/bin/env python3
"""Audit G3-G5 evidence and the fail-closed F43 2V/4V execution contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = ROOT / "twins/reference-917-engine/f43-g3-g5-comparable-execution.json"


class ContractError(ValueError):
    """Raised when the comparison contract is unsafe or internally inconsistent."""


def _reject_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ContractError(f"non-finite JSON constant: {token}")
            ),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"top-level JSON must be an object: {path}")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def relative_difference(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1e-12)


def _safe_repo_path(relative: str) -> Path:
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ContractError(f"path escapes repository: {relative}") from exc
    if candidate.is_symlink() or not candidate.is_file():
        raise ContractError(f"evidence must be an existing regular file: {relative}")
    return candidate


def _require_exact_keys(data: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(data)
    if actual != expected:
        raise ContractError(
            f"{label} keys differ: missing={sorted(expected-actual)} extra={sorted(actual-expected)}"
        )


def _find_turbo_variant(cycle_contract: dict[str, Any]) -> dict[str, Any]:
    variants = cycle_contract.get("engine_variants")
    if not isinstance(variants, list):
        raise ContractError("F33 cycle engine_variants missing")
    selected = [
        row for row in variants
        if row.get("id") == "917_2026_flat12_twin_turbo_1600hp_target"
    ]
    if len(selected) != 1:
        raise ContractError("F33 turbo source variant is not unique")
    return selected[0]


def validate_contract(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _require_exact_keys(
        contract,
        {
            "schema_version", "id", "classification", "authority_boundary",
            "upstream_evidence", "comparison_geometry", "shared_turbo_boundary",
            "three_mesh_execution", "numerical_acceptance",
            "f43_air_cooling_LPBF_DOE", "f43_secondary_oil_cooling_DOE",
            "synthetic_test_policy", "release_gates",
        },
        "contract",
    )
    if contract["schema_version"] != "1.0.0":
        raise ContractError("unsupported schema_version")
    if contract["id"] != "917-head-f43-g3-g5-comparable-execution":
        raise ContractError("wrong contract id")
    authority = contract["authority_boundary"]
    for key in (
        "new_dimensions_invented",
        "historical_1973_geometry_relabelled_as_2026_geometry",
        "synthetic_results_are_engine_evidence",
        "physical_validation_claimed",
    ):
        if authority.get(key) is not False:
            raise ContractError(f"authority_boundary.{key} must remain false")

    sources: dict[str, dict[str, Any]] = {}
    for row in contract["upstream_evidence"]:
        if set(row) != {"id", "path", "sha256"}:
            raise ContractError("upstream evidence rows must contain id/path/sha256 only")
        if row["id"] in sources:
            raise ContractError(f"duplicate upstream id: {row['id']}")
        path = _safe_repo_path(row["path"])
        actual = sha256(path)
        if actual != row["sha256"]:
            raise ContractError(f"upstream hash mismatch: {row['id']}")
        sources[row["id"]] = load_json(path)

    expected_sources = {
        "f29_geometry_report", "f33_integrated_contract", "f33_integrated_report",
        "f33_cycle_contract", "f33_cycle_report", "f34_external_cooling",
        "f36_cross_solver", "f37_ice_engine_foam", "f37_oil_hydraulic_screen",
        "f41_lpbf_geometry",
        "f41_lpbf_audit", "f42_cooling_cross_check", "f42_2_material_screen",
    }
    if set(sources) != expected_sources:
        raise ContractError("upstream evidence inventory is incomplete")

    geometry = contract["comparison_geometry"]
    report_path = _safe_repo_path(geometry["report_path"])
    if sha256(report_path) != geometry["report_sha256"]:
        raise ContractError("comparison geometry report hash mismatch")
    geometry_report = load_json(report_path)
    variants = geometry.get("paired_variants")
    if not isinstance(variants, list) or [row.get("architecture") for row in variants] != ["2v", "4v"]:
        raise ContractError("comparison geometry must contain the ordered 2v/4v pair")
    reported = {row["architecture"]: row for row in geometry_report["variants"]}
    for row in variants:
        reference = reported.get(row["architecture"])
        if reference is None:
            raise ContractError("geometry report architecture missing")
        if row["step_sha256"] != reference["step"]["sha256"]:
            raise ContractError("STEP digest drift in geometry pair")
        if row["stl_sha256"] != reference["stl"]["sha256"]:
            raise ContractError("STL digest drift in geometry pair")
        for gate in (
            "geometry_file_available_in_repository",
            "sealed_intake_exhaust_fluid_domain_available",
            "moving_piston_valve_domain_available",
            "engine_installed_external_air_domain_available",
        ):
            if row.get(gate) is not False:
                raise ContractError(f"comparison geometry {gate} must remain false")
    if geometry.get("same_generation_revision_verified") is not True:
        raise ContractError("paired variants must be bound to one geometry report revision")
    for gate in ("same_external_envelope_verified", "same_interfaces_verified", "execution_authorized"):
        if geometry.get(gate) is not False:
            raise ContractError(f"comparison_geometry.{gate} must remain false")

    shared = contract["shared_turbo_boundary"]
    if shared.get("applies_identically_to") != ["2v", "4v"]:
        raise ContractError("shared turbo boundary must apply identically to 2v and 4v")
    if shared.get("validated") is not False:
        raise ContractError("shared turbo boundary cannot be marked validated")
    turbo = _find_turbo_variant(sources["f33_cycle_contract"])["forward_solver_input"]
    exact_map = {
        "engine_speed_rpm": "speed_rpm",
        "bore_mm": "bore_mm",
        "stroke_mm": "stroke_mm",
        "cylinder_count": "cylinder_count",
        "compression_ratio": "compression_ratio",
        "manifold_pressure_pa_abs": "manifold_pressure_pa_abs",
        "manifold_temperature_k": "manifold_temperature_k",
        "volumetric_efficiency": "volumetric_efficiency",
        "equivalence_ratio": "equivalence_ratio",
        "exhaust_pressure_pa_abs": "exhaust_pressure_pa_abs",
    }
    for target_key, source_key in exact_map.items():
        if shared.get(target_key) != turbo.get(source_key):
            raise ContractError(f"shared turbo boundary drift: {target_key}")
    turbo_screen = turbo["turbo_screening_input"]
    for key in (
        "compressor_inlet_pressure_pa_abs", "compressor_inlet_temperature_k",
        "charge_path_loss_pa", "turbine_inlet_temperature_k",
        "turbine_outlet_pressure_pa_abs",
    ):
        if shared.get(key) != turbo_screen.get(key):
            raise ContractError(f"shared turbo component boundary drift: {key}")
    if shared.get("combustion_calibration_available") is not False or shared.get("cam_and_valve_laws_available") is not False:
        raise ContractError("missing calibration and valve laws must remain explicit")

    execution = contract["three_mesh_execution"]
    if execution.get("mesh_ids") != ["coarse", "medium", "fine"]:
        raise ContractError("exactly three ordered mesh levels are required")
    if set(execution["characteristic_cell_sizes_mm"].values()) != {None}:
        raise ContractError("metric mesh sizes must stay null without certified scale and domains")
    domains = execution.get("domains")
    if not isinstance(domains, list) or [row.get("id") for row in domains] != [
        "G3_steady_port_flow", "G4_moving_engine_cycle", "G5_external_air_cooling"
    ]:
        raise ContractError("G3/G4/G5 domain matrix is incomplete")
    for row in domains:
        if row.get("architectures") != ["2v", "4v"]:
            raise ContractError("each domain must contain the same 2v/4v pair")
        if row.get("method_a") == row.get("method_b"):
            raise ContractError("cross-method implementations must be independent")
        if row.get("geometry_ready") is not False or row.get("execution_authorized") is not False:
            raise ContractError("unavailable geometry cannot be authorized")
    expected_cases = len(domains) * 2 * len(execution["mesh_ids"])
    if execution.get("planned_case_count") != expected_cases or execution.get("executed_case_count") != 0:
        raise ContractError("planned/executed G3-G5 case counts are inconsistent")

    acceptance = contract["numerical_acceptance"]
    for key in (
        "mass_balance_relative_maximum", "energy_balance_relative_maximum",
        "fine_to_medium_primary_metric_change_maximum",
        "cross_method_relative_difference_maximum",
    ):
        value = acceptance.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 < value < 1.0:
            raise ContractError(f"invalid numerical threshold: {key}")
    if acceptance.get("numerical_pass_is_physical_validation") is not False:
        raise ContractError("numerical pass cannot be promoted to physical validation")

    doe = contract["f43_air_cooling_LPBF_DOE"]
    expected_designs = [
        "D0_scan_faithful_baseline", "D1_through_air_teardrop",
        "D2_through_air_diamond", "D3_variable_fin_pitch_thickness",
        "D4_open_pin_fins", "D5_open_lattice", "D6_conduction_ribs",
    ]
    if [row.get("id") for row in doe.get("designs", [])] != expected_designs:
        raise ContractError("F43 LPBF cooling DOE design set is incomplete")
    if any(value is not None for value in doe["dimension_parameters_mm"].values()):
        raise ContractError("unqualified LPBF dimensions must stay null")
    if doe.get("mesh_ids") != execution["mesh_ids"]:
        raise ContractError("DOE must use the same three mesh labels")
    if doe.get("planned_case_count") != len(expected_designs) * 3 or doe.get("executed_case_count") != 0:
        raise ContractError("DOE planned/executed case counts are inconsistent")
    envelope = doe["external_envelope_control"]
    if envelope.get("maximum_allowed_deviation_mm") is not None or envelope.get("measured_deviation_per_design_mm") is not None:
        raise ContractError("external-envelope deviation cannot be invented")
    if envelope.get("quasi_identical_verified") is not False:
        raise ContractError("quasi-identical envelope is not verified")
    prohibited = set(doe["prohibited_features"])
    required_prohibitions = {
        "liquid_cooling_jacket", "closed_internal_cavity", "blind_powder_trap",
        "microchannel_without_demonstrated_CT_probability_of_detection",
        "microchannel_without_demonstrated_powder_removal",
    }
    if not required_prohibitions.issubset(prohibited):
        raise ContractError("LPBF cooling prohibitions are incomplete")
    if doe.get("selected_design") is not None:
        raise ContractError("no DOE design can be selected before execution")
    if doe.get("geometry_generation_authorized") is not False or doe.get("simulation_authorized") is not False:
        raise ContractError("F43 geometry/simulation must remain blocked")

    oil = contract["f43_secondary_oil_cooling_DOE"]
    if oil.get("role") != "secondary_local_heat_pickup_and_valvetrain_lubrication_air_forced_remains_primary":
        raise ContractError("oil cooling must remain secondary to forced air")
    required_oil_architecture = {
        "dry_sump_pressure_supply_to_head_distribution_gallery",
        "calibrated_jets_toward_exhaust_zone_springs_and_rocker_or_cam_carrier",
        "open_gravity_returns_to_scavenge_pickup",
        "scavenge_return_to_external_dry_sump_tank_and_oil_cooler",
    }
    if not required_oil_architecture.issubset(set(oil.get("architecture", []))):
        raise ContractError("secondary oil architecture is incomplete")
    passage_policy = set(oil.get("printed_passage_policy", []))
    for requirement in (
        "through_or_open_ended_only", "flushable_from_machined_access",
        "CT_inspectable_with_probability_of_detection_study",
        "no_blind_powder_trap", "no_liquid_jacket_around_combustion_chamber",
    ):
        if requirement not in passage_policy:
            raise ContractError(f"oil passage policy missing: {requirement}")
    if any(value is not None for value in oil["design_lock_values"].values()):
        raise ContractError("unsourced oil design-lock values must stay null")
    if oil.get("existing_F37_values_are_design_lock") is not False:
        raise ContractError("F37 analytical oil hypotheses cannot become a design lock")
    if oil.get("planned_case_count") is not None or oil.get("executed_case_count") != 0:
        raise ContractError("oil DOE case count cannot be invented")
    if oil.get("selected_design") is not None:
        raise ContractError("oil design cannot be selected before DOE")
    if oil.get("geometry_generation_authorized") is not False or oil.get("simulation_authorized") is not False:
        raise ContractError("oil geometry/simulation must remain blocked")

    if any(value is not False for value in contract["release_gates"].values()):
        raise ContractError("every release gate must remain literal false")
    sources["comparison_geometry_report"] = geometry_report
    return sources


def evaluate_synthetic_fixture(fixture: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    policy = contract["synthetic_test_policy"]
    if fixture.get("classification") != policy["required_classification"]:
        raise ContractError("synthetic fixture classification missing or incorrect")
    if fixture.get("physical_or_release_evidence") is not False:
        raise ContractError("synthetic fixture cannot be physical or release evidence")
    fixture_gates = fixture.get("release_gates")
    if not isinstance(fixture_gates, dict) or not fixture_gates or any(
        value is not False for value in fixture_gates.values()
    ):
        raise ContractError("all synthetic fixture release gates must remain false")
    architectures = fixture.get("architectures")
    if not isinstance(architectures, dict) or set(architectures) != {"2v", "4v"}:
        raise ContractError("synthetic fixture must exercise both architectures")
    thresholds = contract["numerical_acceptance"]
    details: dict[str, Any] = {}
    for architecture in ("2v", "4v"):
        rows = architectures[architecture]
        if [row.get("mesh_id") for row in rows] != ["coarse", "medium", "fine"]:
            raise ContractError("synthetic fixture must contain three ordered meshes")
        evaluated = []
        for row in rows:
            values = [value for key, value in row.items() if key != "mesh_id"]
            if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in values):
                raise ContractError("synthetic fixture values must be finite numbers")
            mass_error = relative_difference(row["mass_in_kg_s"], row["mass_out_kg_s"])
            energy_residual = row["total_energy_out_w"] - row["total_energy_in_w"] - row["wall_heat_w"]
            energy_error = abs(energy_residual) / max(
                abs(row["total_energy_out_w"]), abs(row["total_energy_in_w"]), abs(row["wall_heat_w"]), 1e-12
            )
            cross_error = relative_difference(row["method_a_mass_flow_kg_s"], row["method_b_mass_flow_kg_s"])
            evaluated.append({
                "mesh_id": row["mesh_id"],
                "mass_balance_relative": mass_error,
                "energy_balance_relative": energy_error,
                "cross_method_mass_flow_relative": cross_error,
            })
        mesh_error = relative_difference(
            rows[-2]["method_a_mass_flow_kg_s"], rows[-1]["method_a_mass_flow_kg_s"]
        )
        details[architecture] = {
            "rows": evaluated,
            "fine_to_medium_relative": mesh_error,
            "numerical_pipeline_passed": all(
                item["mass_balance_relative"] <= thresholds["mass_balance_relative_maximum"]
                and item["energy_balance_relative"] <= thresholds["energy_balance_relative_maximum"]
                and item["cross_method_mass_flow_relative"] <= thresholds["cross_method_relative_difference_maximum"]
                for item in evaluated
            ) and mesh_error <= thresholds["fine_to_medium_primary_metric_change_maximum"],
        }
    return {
        "classification": fixture["classification"],
        "excluded_from_engine_evidence": True,
        "architectures": details,
        "validator_math_passed": all(row["numerical_pipeline_passed"] for row in details.values()),
        "physical_or_release_gate_opened": False,
    }


def build_report(contract_path: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    sources = validate_contract(contract)

    f29 = sources["f29_geometry_report"]
    f29_turbo = {
        row["architecture"]: row
        for row in f29["variants"]
        if row["scenario_id"] == "917_30_1973_turbo_5374"
    }
    legacy_bounds_equal = (
        f29_turbo["2v"]["reopened_step_shape"]["bounds_size_mm"]
        == f29_turbo["4v"]["reopened_step_shape"]["bounds_size_mm"]
    )

    f33 = sources["f33_integrated_report"]
    legacy = f33["equivalent_port_cfd"]
    flow_rows = legacy["architectures"]
    legacy_mesh = {}
    for architecture in ("2v", "4v"):
        rows = flow_rows[architecture]
        fine_to_medium = relative_difference(rows[-2]["mass_flow_kg_s"], rows[-1]["mass_flow_kg_s"])
        legacy_mesh[architecture] = {
            "mesh_ids": [row["mesh_id"] for row in rows],
            "cell_counts": [row["cells"] for row in rows],
            "mass_flow_kg_s": [row["mass_flow_kg_s"] for row in rows],
            "fine_to_medium_relative": fine_to_medium,
            "passes_F43_five_percent_mesh_rule": fine_to_medium
            <= contract["numerical_acceptance"]["fine_to_medium_primary_metric_change_maximum"],
        }
    row_keys = set().union(*(set(row) for rows in flow_rows.values() for row in rows))
    mass_balance_fields = {"inlet_mass_flow_kg_s", "outlet_mass_flow_kg_s"}.issubset(row_keys)
    energy_balance_fields = {
        "total_enthalpy_flux_in_w", "total_enthalpy_flux_out_w", "wall_heat_flux_w"
    }.issubset(row_keys)

    cycle = sources["f33_cycle_report"]
    turbo_predictions = [
        row["forward_prediction"] for row in cycle["forward_predictions"]
        if row["configuration"] == "twin_turbo"
    ]
    if len(turbo_predictions) != 1:
        raise ContractError("F33 executed turbo prediction is not unique")
    turbo_prediction = turbo_predictions[0]

    ice = sources["f37_ice_engine_foam"]
    oil = sources["f37_oil_hydraulic_screen"]
    f34 = sources["f34_external_cooling"]
    f36 = sources["f36_cross_solver"]
    f42 = sources["f42_cooling_cross_check"]
    material = sources["f42_2_material_screen"]

    planned = contract["three_mesh_execution"]
    doe = contract["f43_air_cooling_LPBF_DOE"]
    report = {
        "schema_version": "1.0.0",
        "id": "917-head-f43-g3-g5-comparable-execution-audit",
        "classification": "deterministic_existing_evidence_audit_and_blocked_execution_matrix_not_new_CFD_not_validation",
        "status": "audit_complete_comparable_execution_blocked",
        "contract": {
            "path": str(contract_path.relative_to(ROOT)),
            "sha256": sha256(contract_path),
            "all_upstream_hashes_verified": True,
        },
        "geometry_audit": {
            "selected_comparison_revision": contract["comparison_geometry"]["revision_id"],
            "paired_geometry_report_hash_verified": True,
            "paired_geometry_files_available_in_repository": False,
            "paired_fluid_domains_available": False,
            "same_external_envelope_verified": False,
            "legacy_F29_1973_concept_pair_exists": True,
            "legacy_F29_1973_reopened_STEP_bounds_equal": legacy_bounds_equal,
            "legacy_F29_pair_reused_as_F33_2026_geometry": False,
            "scan_faithful_2v_variant_available": False,
        },
        "existing_G3_OpenFOAM_audit": {
            "classification": legacy["classification"],
            "executed_case_count": sum(len(rows) for rows in flow_rows.values()),
            "solver_return_codes_all_zero": all(
                row["solver_returncode"] == 0 for rows in flow_rows.values() for row in rows
            ),
            "architectures": legacy_mesh,
            "same_flowbench_boundary_used": True,
            "turbo_boundary_used": False,
            "full_runner_or_moving_valve_geometry_used": legacy["full_runner_and_moving_valve_geometry_used"],
            "boundary_mass_balance_fields_present": mass_balance_fields,
            "energy_balance_fields_present": energy_balance_fields,
            "independent_second_method_present": False,
            "accepted_for_F43_comparison": False,
            "four_valve_fine_mass_flow_gain_percent_legacy": legacy["four_valve_fine_mass_flow_change_percent"],
        },
        "existing_Cantera_audit": {
            "classification": turbo_prediction["classification"],
            "cantera_equilibrium_uv_executed": turbo_prediction["numerical_scope"]["cantera_equilibrium_uv_executed"],
            "crank_angle_time_marching_executed": turbo_prediction["numerical_scope"]["crank_angle_time_marching_executed"],
            "mass_identity_residual_kg_s": turbo_prediction["trapped_charge"]["mass_identity_residual_kg_s"],
            "valve_architecture_is_an_input": False,
            "same_2v_4v_turbo_case_executed": False,
            "accepted_for_G4_cross_method": False,
        },
        "existing_ICEEngineFoam_audit": {
            "exact_iceEngineFoam_executable_present": ice["requested_solver_probe"]["iceEngineFoam_executable_present"],
            "executed_case_classification": ice["executed_reference_case"]["classification"],
            "executed_valve_count": ice["executed_reference_case"]["valve_count"],
            "porsche_917_geometry_used": ice["executed_reference_case"]["porsche_917_geometry_used"],
            "four_valve_case_executed": ice["gates"]["f37_four_valve_moving_mesh_executed"],
            "cantera_coupled": ice["executed_reference_case"]["cantera_coupled_to_case"],
            "accepted_for_G4_cross_method": False,
        },
        "existing_G5_air_cooling_audit": {
            "F34_OpenFOAM": {
                "solver_completed": f34["solver_completed"],
                "classification": f34["classification"],
                "architecture": "4v_only",
                "relative_energy_imbalance": f34["results"]["relative_energy_imbalance"],
                "pressure_drop_pa": f34["results"]["pressure_drop_pa"],
                "effective_h_w_m2k": f34["results"]["effective_h_w_m2k"],
                "strict_mesh_passed": f34["mesh"]["strict_check_mesh_passed"],
            },
            "F36_cross_solver": {
                "classification": f36["classification"],
                "cooling_closed": f36["decision"]["cooling_closure"]["cooling_closed"],
                "RANS_two_grid_agreement": f36["decision"]["cooling_closure"]["rans_two_grid_agreement"],
                "full_CHT": f36["decision"]["proof_matrix"]["full conjugate heat transfer"],
            },
            "F42_cross_method": {
                "classification": f42["classification"],
                "h_gate_passed": f42["decision"]["cross_method_h_gate_passed"],
                "pressure_gate_passed": f42["decision"]["cross_method_pressure_gate_passed"],
                "exact_F41_OpenFOAM_case_accepted": f42["decision"]["exact_F41_openfoam_numerical_case_accepted"],
                "full_head_CHT_complete": f42["decision"]["full_head_CHT_complete"],
                "architecture": "4v_only",
            },
            "paired_2v_4v_same_geometry_revision_exists": False,
            "accepted_for_F43_comparison": False,
        },
        "existing_secondary_oil_audit": {
            "classification": oil["status"],
            "case_ids": [row["id"] for row in oil["cases"]],
            "physical_oil_rig_correlated": oil["gates"]["physical_oil_rig_correlated"],
            "methods_are_independent_for_laminar_flow": False,
            "reason_methods_not_independent": "Hagen-Poiseuille and Darcy-Weisbach with f=64/Re reduce to the same laminar relation.",
            "jet_impingement_CFD_executed": False,
            "multiphase_aeration_and_drainback_executed": False,
            "values_promoted_to_F43_design_lock": False,
            "accepted_for_F43_oil_DOE": False,
        },
        "shared_turbo_boundary": {
            "defined_once_and_applied_identically_in_contract": True,
            "source_variant_id": contract["shared_turbo_boundary"]["source_variant_id"],
            "validated": False,
            "executed_in_paired_G3_G4_G5_cases": False,
        },
        "planned_execution": {
            "domains": [row["id"] for row in planned["domains"]],
            "architectures": ["2v", "4v"],
            "meshes": planned["mesh_ids"],
            "planned_case_count": planned["planned_case_count"],
            "executed_case_count": planned["executed_case_count"],
            "mass_balance_required": True,
            "energy_balance_required": True,
            "cross_method_relative_difference_maximum": contract["numerical_acceptance"]["cross_method_relative_difference_maximum"],
        },
        "F43_LPBF_air_cooling_DOE": {
            "baseline": doe["designs"][0]["id"],
            "candidate_ids": [row["id"] for row in doe["designs"][1:]],
            "mesh_count_per_design": len(doe["mesh_ids"]),
            "planned_case_count": doe["planned_case_count"],
            "executed_case_count": doe["executed_case_count"],
            "dimension_parameters_all_null": all(value is None for value in doe["dimension_parameters_mm"].values()),
            "external_envelope_quasi_identical_verified": doe["external_envelope_control"]["quasi_identical_verified"],
            "liquid_jacket_prohibited": "liquid_cooling_jacket" in doe["prohibited_features"],
            "closed_cavity_prohibited": "closed_internal_cavity" in doe["prohibited_features"],
            "CT_and_powder_removal_required": True,
            "selected_design": doe["selected_design"],
        },
        "F43_secondary_oil_cooling_DOE": {
            "air_forced_remains_primary": True,
            "printed_passages_through_flushable_CT_inspectable_required": True,
            "design_lock_values_all_null": all(
                value is None
                for value in contract["f43_secondary_oil_cooling_DOE"]["design_lock_values"].values()
            ),
            "planned_case_count": contract["f43_secondary_oil_cooling_DOE"]["planned_case_count"],
            "executed_case_count": contract["f43_secondary_oil_cooling_DOE"]["executed_case_count"],
            "selected_design": contract["f43_secondary_oil_cooling_DOE"]["selected_design"],
        },
        "material_boundary": {
            "candidate_count": len(material["materials"]),
            "all_hot_band_gates_false": all(not row["hot_band_gate"] for row in material["materials"]),
            "thermal_stress_acceptance_available": False,
        },
        "synthetic_fixture": {
            "path": contract["synthetic_test_policy"]["fixture_path"],
            "role": "validator_math_only",
            "included_in_engine_evidence_metrics": False,
        },
        "exact_gaps": [
            "GAP-GEO-01: F33 paired STEP/STL solver-surrogate files are not published in the repository.",
            "GAP-GEO-02: no sealed 2V/4V intake, exhaust, moving-engine and installed-air domains share one verified external revision.",
            "GAP-GEO-03: no scan-faithful 2V counterpart exists for the F41 four-valve local-only master.",
            "GAP-BC-01: F33 turbo values are unvalidated clean-sheet hypotheses and cam/valve laws are absent.",
            "GAP-G3-01: the six F33 OpenFOAM runs are equivalent rectangular ports, not full runner/valve geometry.",
            "GAP-G3-02: F33 rows lack inlet/outlet mass balance and total-energy balance fields and no independent second method exists.",
            "GAP-G3-03: F33 medium-to-fine mass-flow changes exceed the F43 five-percent rule for both architectures.",
            "GAP-G4-01: Cantera executed a four-state equilibrium screen, not a crank-angle 2V/4V cycle.",
            "GAP-G4-02: the only moving-mesh engine run is a generic 2D two-valve tutorial; exact iceEngineFoam and F37/F41 4V were not run.",
            "GAP-G5-01: F34/F36/F42 air-cooling evidence is four-valve only; no paired 2V case exists.",
            "GAP-G5-02: exact-F41 OpenFOAM was not accepted, F36 RANS failed closure, and no whole-head CHT is complete.",
            "GAP-LPBF-01: all DOE dimensions, external-deviation limit, CT resolution and powder-removal thresholds remain unqualified.",
            "GAP-OIL-01: oil properties versus temperature, supply map, jet coefficients, coking limit and scavenge boundary are not sourced.",
            "GAP-OIL-02: F37 oil equations are algebraically equivalent in laminar flow and do not model jets, aeration or drainback.",
            "GAP-OIL-03: no geometry-resolved oil CFD or tilted/accelerated dry-sump rig correlation exists.",
            "GAP-MAT-01: all five F42.2 material hot-band gates remain false, so thermal-stress acceptance is unavailable.",
        ],
        "decision": {
            "comparable_2v_4v_execution_complete": False,
            "new_long_solver_run_started": False,
            "reason_no_run": "geometry and boundary preflight is blocked; running would create non-comparable evidence",
            "F43_LPBF_cooling_improvement_quantified": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "release_gates": contract["release_gates"],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--check", type=Path)
    args = parser.parse_args()

    contract_path = args.contract.resolve()
    report = build_report(contract_path)
    payload = canonical_bytes(report)
    if args.check:
        check_path = args.check.resolve()
        if not check_path.is_file() or check_path.read_bytes() != payload:
            raise SystemExit(f"stale or missing audit report: {check_path}")
        print(f"OK   {check_path.relative_to(ROOT)}")
        return 0
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit("output must remain inside repository") from exc
    if output.exists() and output.is_symlink():
        raise SystemExit("refusing symlink output")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    print(f"WROTE {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
