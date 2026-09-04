#!/usr/bin/env python3
"""Construit et, sur demande, exécute le flat-12 motored F39 avec Aeolus1D.

F39 est volontairement limité à un cycle de respiration de 720 degrés sans
injection ni combustion. Les cotes de conduits, CdA et phases sont des
hypothèses typées. Le rapport ne peut donc jamais promouvoir ce calcul en
preuve de puissance, corrélation banc, démarrage ou fabrication.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
from collections import Counter, deque
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO_ROOT / "twins/reference-917-engine/unsteady-network-f39.json"
DEFAULT_OUTPUT = REPO_ROOT / "work/917-unsteady-network-f39"
REPORT_NAME = "unsteady-network-f39-report.json"
OUTPUT_OWNER = "porsche-917-unsteady-network-f39"


class F39InputError(ValueError):
    """Erreur déterministe de contrat, de provenance ou de topologie."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise F39InputError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_number(value: Any, label: str, *, positive: bool = False) -> float:
    require(not isinstance(value, bool) and isinstance(value, (int, float)), f"{label} must be numeric")
    result = float(value)
    require(math.isfinite(result), f"{label} must be finite")
    if positive:
        require(result > 0.0, f"{label} must be positive")
    return result


def verify_sources(project_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    declarations = contract.get("source_evidence")
    require(isinstance(declarations, dict) and len(declarations) == 6, "exactly six sources required")
    result: dict[str, Any] = {}
    expected_phases = {
        "cycle_thermal_contract_f33": "F33",
        "rotating_assembly_contract_f35": "F35",
        "gas_path_contract_f38": "F38",
        "clean_sheet_head_contract_f29": "F29",
    }
    for source_id, declaration in declarations.items():
        require(isinstance(declaration, dict), f"source_evidence.{source_id} invalid")
        relative_path = declaration.get("path")
        expected = declaration.get("expected_sha256")
        require(isinstance(relative_path, str), f"{source_id}.path required")
        require(isinstance(expected, str) and len(expected) == 64, f"{source_id}.expected_sha256 required")
        path = project_root / relative_path
        require(path.is_file(), f"source missing: {relative_path}")
        actual = sha256(path)
        require(actual == expected, f"source hash mismatch: {source_id}")
        document = load_json(path)
        if source_id in expected_phases:
            require(document.get("phase") == expected_phases[source_id], f"{source_id} phase mismatch")
        if source_id == "kinematics_contract_f2":
            require(str(document.get("status", "")).startswith("F2_"), "F2 kinematics status mismatch")
        result[source_id] = {
            "path": relative_path,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "hash_verified": True,
        }
    return result


def validate_phase_policy(contract: dict[str, Any]) -> dict[int, float]:
    policy = contract.get("phase_policy")
    require(isinstance(policy, dict), "phase_policy object required")
    firing_order = policy.get("firing_order_candidate")
    require(isinstance(firing_order, list) and len(firing_order) == 12, "twelve firing-order entries required")
    require(set(firing_order) == set(range(1, 13)), "firing order must contain cylinders 1..12 exactly once")
    interval = finite_number(policy.get("phase_interval_deg"), "phase_interval_deg", positive=True)
    require(math.isclose(interval, 60.0), "flat-12 candidate phase interval must be 60 degrees")
    require(policy.get("absolute_zero_validated") is False, "absolute phase must remain unvalidated")
    first = finite_number(policy.get("first_cylinder_phase_deg"), "first_cylinder_phase_deg")
    phases = {int(cylinder): (first + index * interval) % 720.0 for index, cylinder in enumerate(firing_order)}
    require(len(set(phases.values())) == 12, "cylinder phases must be unique over 720 degrees")
    require(sorted(phases.values()) == [float(value) for value in range(0, 720, 60)], "phases must cover 0..660 by 60 degrees")
    for name in ("intake_valve_group", "exhaust_valve_group"):
        valve = policy.get(name)
        require(isinstance(valve, dict), f"phase_policy.{name} required")
        opening = finite_number(valve.get("open_deg"), f"{name}.open_deg")
        center = finite_number(valve.get("center_deg"), f"{name}.center_deg")
        closing = finite_number(valve.get("close_deg"), f"{name}.close_deg")
        require(0.0 <= opening < 720.0 and 0.0 <= center < 720.0 and 0.0 <= closing < 720.0, f"{name} angles must be in one 720-degree cycle")
        require(finite_number(valve.get("duration_deg"), f"{name}.duration_deg", positive=True) == 280.0, f"{name} duration must be 280 degrees")
        require(math.isclose((center - opening) % 720.0, 140.0), f"{name} center must be half-duration after opening")
        require(math.isclose((closing - opening) % 720.0, 280.0), f"{name} closing must be one duration after opening")
        require(valve.get("lift_law") == "sin_squared_hypothesis", f"{name} lift law mismatch")
        require(valve.get("physical_valve_count_per_cylinder") == 2, f"{name} must contain two physical valves")
        finite_number(valve.get("total_geometric_port_area_m2"), f"{name}.total_geometric_port_area_m2", positive=True)
        cd = finite_number(valve.get("discharge_coefficient"), f"{name}.discharge_coefficient", positive=True)
        require(cd <= 1.0, f"{name} discharge coefficient must not exceed one")
        require("hypothesis" in str(valve.get("classification")), f"{name} must remain a hypothesis")
    return phases


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schema_version") == "1.0.0", "schema_version must be 1.0.0")
    require(contract.get("phase") == "F39", "contract.phase must be F39")
    require(contract.get("status") == "motored_unsteady_720_contract_fail_closed", "contract.status mismatch")
    require(contract.get("asset_id") == OUTPUT_OWNER, "contract.asset_id mismatch")
    authority = contract.get("authority_boundary")
    require(isinstance(authority, dict), "authority_boundary required")
    for key in (
        "motored_only",
        "requested_power_target_used_as_solver_input",
        "absolute_crank_phase_validated",
        "duct_geometry_measured",
        "valve_cda_measured",
        "physical_correlation_complete",
    ):
        expected = key == "motored_only"
        require(authority.get(key) is expected, f"authority_boundary.{key} must be {expected}")
    require(authority.get("combustion_enabled") is False, "combustion must be disabled")
    require(authority.get("fuel_injection_enabled") is False, "fuel injection must be disabled")
    variant = contract.get("variant")
    require(isinstance(variant, dict), "variant object required")
    require(variant.get("variant_id") == "917_2026_flat12_na_candidate", "F39 must use the NA candidate")
    require(variant.get("configuration") == "naturally_aspirated", "F39 configuration must be NA")
    require(variant.get("cylinder_count") == 12, "twelve cylinders required")
    require(finite_number(variant.get("cycle_degrees"), "cycle_degrees") == 720.0, "720-degree cycle required")
    for key in (
        "bore_mm",
        "stroke_mm",
        "compression_ratio",
        "connecting_rod_center_distance_mm",
        "speed_rpm",
        "intake_boundary_pressure_pa_abs",
        "exhaust_boundary_pressure_pa_abs",
        "initial_temperature_k",
    ):
        finite_number(variant.get(key), f"variant.{key}", positive=True)
    validate_phase_policy(contract)
    topology = contract.get("topology_contract")
    require(isinstance(topology, dict), "topology_contract required")
    require(topology.get("pipe_count") == 27, "exactly 27 pipes required")
    require(topology.get("topological_junction_count") == 15, "exactly 15 topological junctions required")
    require(topology.get("aeolus_junction_spec_count") == 3, "three Aeolus plenum junctions required")
    require(topology.get("aeolus_cylinder_spec_count") == 12, "twelve Aeolus cylinder specs required")
    require(topology.get("physical_valve_count") == 48, "forty-eight physical valves required")
    require(topology.get("aeolus_equivalent_valve_port_count") == 24, "twenty-four equivalent Aeolus valve ports required")
    require(topology.get("connected_graph_required") is True, "connected graph gate required")
    geometry = contract.get("network_geometry_hypotheses")
    require(isinstance(geometry, dict), "network_geometry_hypotheses required")
    require("not_measured" in str(geometry.get("classification")), "network geometry must remain unmeasured")
    for family in ("intake_trunk", "intake_runner", "exhaust_primary", "exhaust_outlet"):
        item = geometry.get(family)
        require(isinstance(item, dict), f"network geometry {family} required")
        finite_number(item.get("length_m"), f"{family}.length_m", positive=True)
        finite_number(item.get("area_m2"), f"{family}.area_m2", positive=True)
        require(isinstance(item.get("n_cells"), int) and item["n_cells"] >= 4, f"{family}.n_cells must be >= 4")
    runtime = contract.get("aeolus1d_runtime")
    require(isinstance(runtime, dict), "aeolus1d_runtime required")
    require(runtime.get("package") == "aeolus1d", "Aeolus1D package required")
    require(runtime.get("required_version") == "0.3.3", "Aeolus1D version must be pinned")
    numerical = contract.get("numerical_policy")
    require(isinstance(numerical, dict), "numerical_policy required")
    require(numerical.get("scheme") == "muscl", "MUSCL scheme required")
    require(numerical.get("limiter") == "minmod", "minmod limiter required")
    require(numerical.get("time_integrator") == "ssp_rk2", "SSP-RK2 required")
    cfl = finite_number(numerical.get("cfl"), "numerical_policy.cfl", positive=True)
    hard_cfl = finite_number(numerical.get("cfl_hard_limit"), "numerical_policy.cfl_hard_limit", positive=True)
    require(cfl <= hard_cfl < 0.8 + 1.0e-15, "CFL policy exceeds hard limit")
    require(numerical.get("requested_cycles") == 1, "F39 must request exactly one cycle")
    require(numerical.get("cycle_convergence", {}).get("evaluated_in_f39") is False, "cycle convergence must remain unevaluated")
    numerical_gates = contract.get("numerical_gates")
    require(
        isinstance(numerical_gates, dict)
        and set(numerical_gates)
        == {
            "source_hashes_verified",
            "topology_contract_valid",
            "aeolus_case_constructed",
            "full_720_time_march_executed",
            "runtime_fields_finite",
            "runtime_state_positive",
        },
        "exact numerical_gates contract required",
    )
    require(
        all(value is False for value in numerical_gates.values()),
        "all contract numerical gates must start false",
    )
    physical_release = contract.get("physical_release_gates")
    require(isinstance(physical_release, dict) and physical_release, "physical_release_gates required")
    require(
        all(value is False for value in physical_release.values()),
        "all physical release gates must remain false",
    )


def build_topology(contract: dict[str, Any]) -> dict[str, Any]:
    variant = contract["variant"]
    geometry = contract["network_geometry_hypotheses"]
    phase_policy = contract["phase_policy"]
    phases = validate_phase_policy(contract)
    p_intake = float(variant["intake_boundary_pressure_pa_abs"])
    p_exhaust = float(variant["exhaust_boundary_pressure_pa_abs"])
    temperature = float(variant["initial_temperature_k"])

    boundaries = [
        {"id": "bench_ambient", "kind": "stagnation_inlet", "pressure_pa_abs": p_intake, "temperature_k": temperature},
        {"id": "bench_extraction_negative_y", "kind": "pressure_outlet", "pressure_pa_abs": p_exhaust},
        {"id": "bench_extraction_positive_y", "kind": "pressure_outlet", "pressure_pa_abs": p_exhaust},
    ]
    junctions = [
        {"id": "intake_plenum", "kind": "intake_plenum", "aeolus_component": "JunctionSpec"},
        *[
            {
                "id": f"cylinder_c{number:02d}",
                "kind": "cylinder_control_volume",
                "aeolus_component": "CylinderSpec",
                "cylinder_number": number,
                "bank": "negative_y" if number <= 6 else "positive_y",
            }
            for number in range(1, 13)
        ],
        {"id": "exhaust_collector_negative_y", "kind": "exhaust_collector", "aeolus_component": "JunctionSpec"},
        {"id": "exhaust_collector_positive_y", "kind": "exhaust_collector", "aeolus_component": "JunctionSpec"},
    ]

    def pipe_record(pipe_id: str, family: str, left: str, right: str, pressure: float) -> dict[str, Any]:
        spec = geometry[family]
        return {
            "id": pipe_id,
            "family": family,
            "left_node": left,
            "right_node": right,
            "length_m": float(spec["length_m"]),
            "area_m2": float(spec["area_m2"]),
            "n_cells": int(spec["n_cells"]),
            "initial_pressure_pa_abs": pressure,
            "initial_temperature_k": temperature,
        }

    pipes = [pipe_record("intake_trunk", "intake_trunk", "bench_ambient", "intake_plenum", p_intake)]
    for number in range(1, 13):
        cylinder_node = f"cylinder_c{number:02d}"
        collector = "exhaust_collector_negative_y" if number <= 6 else "exhaust_collector_positive_y"
        pipes.append(pipe_record(f"intake_runner_c{number:02d}", "intake_runner", "intake_plenum", cylinder_node, p_intake))
        pipes.append(pipe_record(f"exhaust_primary_c{number:02d}", "exhaust_primary", cylinder_node, collector, p_exhaust))
    pipes.extend(
        [
            pipe_record("exhaust_outlet_negative_y", "exhaust_outlet", "exhaust_collector_negative_y", "bench_extraction_negative_y", p_exhaust),
            pipe_record("exhaust_outlet_positive_y", "exhaust_outlet", "exhaust_collector_positive_y", "bench_extraction_positive_y", p_exhaust),
        ]
    )
    cylinders = []
    valves = []
    for number in range(1, 13):
        cylinder_id = f"c{number:02d}"
        cylinders.append(
            {
                "id": cylinder_id,
                "node_id": f"cylinder_{cylinder_id}",
                "number": number,
                "bank": "negative_y" if number <= 6 else "positive_y",
                "event_phase_deg": phases[number],
                "theta_init_deg": (-phases[number]) % 720.0,
                "phase_classification": "candidate_even_fire_phase_absolute_zero_unvalidated",
                "combustion": None,
                "fuel_mass_per_cycle_kg": 0.0,
            }
        )
        for kind, pipe_id in (
            ("intake", f"intake_runner_c{number:02d}"),
            ("exhaust", f"exhaust_primary_c{number:02d}"),
        ):
            valve = phase_policy[f"{kind}_valve_group"]
            valves.append(
                {
                    "id": f"{kind}_valve_c{number:02d}",
                    "kind": kind,
                    "cylinder_id": cylinder_id,
                    "pipe_id": pipe_id,
                    "pipe_end": "right" if kind == "intake" else "left",
                    "open_deg": float(valve["open_deg"]),
                    "center_deg": float(valve["center_deg"]),
                    "close_deg": float(valve["close_deg"]),
                    "physical_valve_count": int(valve["physical_valve_count_per_cylinder"]),
                    "equivalent_port_area_m2": float(valve["total_geometric_port_area_m2"]),
                    "discharge_coefficient": float(valve["discharge_coefficient"]),
                    "classification": valve["classification"],
                }
            )
    return {"boundaries": boundaries, "junctions": junctions, "pipes": pipes, "cylinders": cylinders, "valves": valves}


def validate_topology(topology: dict[str, Any], contract: dict[str, Any]) -> None:
    expected = contract["topology_contract"]
    pipes = topology.get("pipes")
    junctions = topology.get("junctions")
    cylinders = topology.get("cylinders")
    valves = topology.get("valves")
    boundaries = topology.get("boundaries")
    require(isinstance(pipes, list) and len(pipes) == expected["pipe_count"], "generated topology must contain 27 pipes")
    require(isinstance(junctions, list) and len(junctions) == expected["topological_junction_count"], "generated topology must contain 15 junctions")
    require(isinstance(cylinders, list) and len(cylinders) == 12, "generated topology must contain 12 cylinders")
    require(isinstance(valves, list) and len(valves) == expected["aeolus_equivalent_valve_port_count"], "generated topology must contain 24 equivalent valve ports")
    require(sum(int(item["physical_valve_count"]) for item in valves) == expected["physical_valve_count"], "generated topology must represent 48 physical valves")
    require(isinstance(boundaries, list) and len(boundaries) == expected["boundary_count"], "generated topology must contain 3 boundaries")
    for label, items in (("pipe", pipes), ("junction", junctions), ("cylinder", cylinders), ("valve", valves), ("boundary", boundaries)):
        ids = [item.get("id") for item in items]
        require(all(isinstance(item_id, str) and item_id for item_id in ids), f"{label} ids required")
        require(len(ids) == len(set(ids)), f"duplicate {label} id")
    require(Counter(item["family"] for item in pipes) == Counter(expected["pipe_families"]), "pipe family counts mismatch")
    require(Counter(item["kind"] for item in junctions) == Counter(expected["junction_families"]), "junction family counts mismatch")
    require(sum(item["aeolus_component"] == "JunctionSpec" for item in junctions) == 3, "Aeolus junction count mismatch")
    require(sum(item["aeolus_component"] == "CylinderSpec" for item in junctions) == 12, "Aeolus cylinder count mismatch")
    node_ids = {item["id"] for item in junctions} | {item["id"] for item in boundaries}
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    pipe_ids = {item["id"] for item in pipes}
    for pipe in pipes:
        left = pipe.get("left_node")
        right = pipe.get("right_node")
        require(left in node_ids and right in node_ids and left != right, f"unresolved endpoints for {pipe.get('id')}")
        adjacency[left].add(right)
        adjacency[right].add(left)
    visited: set[str] = set()
    queue: deque[str] = deque(["bench_ambient"])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(adjacency[node] - visited)
    require(visited == node_ids, "generated network graph must be connected")
    by_cylinder: Counter[str] = Counter()
    for valve in valves:
        require(valve["pipe_id"] in pipe_ids, f"valve pipe missing: {valve['id']}")
        by_cylinder[valve["cylinder_id"]] += 1
        require("hypothesis" in valve["classification"], f"valve classification not fail-closed: {valve['id']}")
    require(set(by_cylinder) == {item["id"] for item in cylinders}, "valves must cover every cylinder")
    require(all(count == 2 for count in by_cylinder.values()), "each cylinder must have two valve ports")
    event_phases = [float(item["event_phase_deg"]) for item in cylinders]
    theta_offsets = [float(item["theta_init_deg"]) for item in cylinders]
    require(len(set(event_phases)) == 12 and sorted(event_phases) == [float(value) for value in range(0, 720, 60)], "generated cylinder event phases invalid")
    require(
        all(math.isclose(item["theta_init_deg"], (-item["event_phase_deg"]) % 720.0) for item in cylinders),
        "Aeolus theta offsets must be the negative modulo 720 of event phases",
    )
    require(len(set(theta_offsets)) == 12 and sorted(theta_offsets) == [float(value) for value in range(0, 720, 60)], "generated cylinder theta offsets invalid")


def build_aeolus_case(contract: dict[str, Any], topology: dict[str, Any]) -> Any:
    try:
        from aeolus1d.io.schema import (
            BCSpec,
            Case,
            CaseHeader,
            CrankshaftSpec,
            CylinderPortSpec,
            CylinderSpec,
            GasSpec,
            JunctionSpec,
            PipeSpec,
            PortSpec,
            UniformInit,
        )
    except ImportError as exc:
        raise F39InputError("Aeolus1D is required for --execute or --validate-aeolus") from exc

    required_version = contract["aeolus1d_runtime"]["required_version"]
    try:
        actual_version = importlib.metadata.version("aeolus1d")
    except importlib.metadata.PackageNotFoundError as exc:
        raise F39InputError("Aeolus1D package metadata unavailable") from exc
    require(actual_version == required_version, f"Aeolus1D version mismatch: expected {required_version}, got {actual_version}")
    numerical = contract["numerical_policy"]
    variant = contract["variant"]
    geometry = contract["network_geometry_hypotheses"]
    pipe_specs = [
        PipeSpec(
            id=item["id"],
            length=item["length_m"],
            n_cells=item["n_cells"],
            area=item["area_m2"],
            init=UniformInit(p=item["initial_pressure_pa_abs"], T=item["initial_temperature_k"], u=0.0),
        )
        for item in topology["pipes"]
    ]
    pipe_by_id = {item["id"]: item for item in topology["pipes"]}
    intake_ports = [PortSpec(pipe="intake_trunk", end="right", area=pipe_by_id["intake_trunk"]["area_m2"])]
    intake_ports.extend(
        PortSpec(pipe=f"intake_runner_c{number:02d}", end="left", area=pipe_by_id[f"intake_runner_c{number:02d}"]["area_m2"])
        for number in range(1, 13)
    )
    junction_specs = [
        JunctionSpec(
            id="intake_plenum",
            volume=geometry["intake_plenum_volume_m3"],
            init=UniformInit(p=variant["intake_boundary_pressure_pa_abs"], T=variant["initial_temperature_k"]),
            ports=intake_ports,
        )
    ]
    for bank, numbers in (("negative_y", range(1, 7)), ("positive_y", range(7, 13))):
        ports = [
            PortSpec(pipe=f"exhaust_primary_c{number:02d}", end="right", area=pipe_by_id[f"exhaust_primary_c{number:02d}"]["area_m2"])
            for number in numbers
        ]
        ports.append(PortSpec(pipe=f"exhaust_outlet_{bank}", end="left", area=pipe_by_id[f"exhaust_outlet_{bank}"]["area_m2"]))
        junction_specs.append(
            JunctionSpec(
                id=f"exhaust_collector_{bank}",
                volume=geometry["exhaust_collector_volume_m3_each"],
                init=UniformInit(p=variant["exhaust_boundary_pressure_pa_abs"], T=variant["initial_temperature_k"]),
                ports=ports,
            )
        )
    valve_by_id = {item["id"]: item for item in topology["valves"]}
    displacement = math.pi * (variant["bore_mm"] / 1000.0) ** 2 * (variant["stroke_mm"] / 1000.0) / 4.0
    clearance_volume = displacement / (variant["compression_ratio"] - 1.0)

    def cylinder_port(valve: dict[str, Any]) -> Any:
        opening = float(valve["open_deg"])
        duration = 280.0
        lift_cad = sorted({float(value) for value in range(0, 721, 10)} | {opening, float(valve["center_deg"]), float(valve["close_deg"])})
        lift_y = []
        for angle in lift_cad:
            phase_angle = 0.0 if math.isclose(angle, 720.0) else angle
            delta = (phase_angle - opening) % 720.0
            lift_y.append(math.sin(math.pi * delta / duration) ** 2 if delta <= duration else 0.0)
        return CylinderPortSpec(
            pipe=valve["pipe_id"],
            end=valve["pipe_end"],
            A_port=valve["equivalent_port_area_m2"],
            open_deg=valve["open_deg"],
            close_deg=valve["close_deg"],
            lift_cad=lift_cad,
            lift_y=lift_y,
            lift_max=1.0,
            Cd=valve["discharge_coefficient"],
        )

    cylinder_specs = []
    for cylinder in topology["cylinders"]:
        cylinder_id = cylinder["id"]
        number = int(cylinder["number"])
        cylinder_specs.append(
            CylinderSpec(
                id=cylinder_id,
                bore=variant["bore_mm"] / 1000.0,
                stroke=variant["stroke_mm"] / 1000.0,
                con_rod_length=variant["connecting_rod_center_distance_mm"] / 1000.0,
                clearance_volume=clearance_volume,
                # Aeolus1D 0.3.3 requires this legacy field in the Python
                # dataclass. Zero is its documented inheritance sentinel;
                # build_network resolves it from crankshaft.rpm below.
                omega_crank=0.0,
                theta_init_deg=cylinder["theta_init_deg"],
                init=UniformInit(p=variant["intake_boundary_pressure_pa_abs"], T=variant["initial_temperature_k"]),
                ports=[
                    cylinder_port(valve_by_id[f"intake_valve_c{number:02d}"]),
                    cylinder_port(valve_by_id[f"exhaust_valve_c{number:02d}"]),
                ],
                m_fuel_per_cycle=0.0,
                combustion=None,
                caloric_thermo=False,
                ignition="spark",
                knock_retard_deg_per_event=0.0,
                knock_retard_max_deg=0.0,
                knock_advance_deg_per_cycle=0.0,
            )
        )
    return Case(
        case=CaseHeader(
            name="porsche_917_f39_flat12_na_motored_720",
            t_end=numerical["expected_duration_s"],
            cfl=numerical["cfl"],
            scheme=numerical["scheme"],
            limiter=numerical["limiter"],
            rk=numerical["time_integrator"],
        ),
        gas=GasSpec(gamma=1.4, R_gas=287.05),
        pipes=pipe_specs,
        junctions=junction_specs,
        bcs=[
            BCSpec(pipe="intake_trunk", end="left", kind="stagnation_inlet", p0=variant["intake_boundary_pressure_pa_abs"], T0=variant["initial_temperature_k"]),
            BCSpec(pipe="exhaust_outlet_negative_y", end="right", kind="pressure_outlet", p_back=variant["exhaust_boundary_pressure_pa_abs"]),
            BCSpec(pipe="exhaust_outlet_positive_y", end="right", kind="pressure_outlet", p_back=variant["exhaust_boundary_pressure_pa_abs"]),
        ],
        cylinders=cylinder_specs,
        crankshaft=CrankshaftSpec(
            rpm=variant["speed_rpm"],
            theta0_deg=0.0,
            firing_order=[f"c{number:02d}" for number in contract["phase_policy"]["firing_order_candidate"]],
            firing_interval_deg=[0.0] + [60.0] * 11,
        ),
    )


def case_summary(case: Any) -> dict[str, Any]:
    return {
        "name": case.case.name,
        "pipe_spec_count": len(case.pipes),
        "junction_spec_count": len(case.junctions),
        "cylinder_spec_count": len(case.cylinders),
        "boundary_spec_count": len(case.bcs),
        "valve_port_count": sum(len(cylinder.ports) for cylinder in case.cylinders),
        "t_end_s": float(case.case.t_end),
        "cfl": float(case.case.cfl),
        "scheme": case.case.scheme,
        "limiter": case.case.limiter,
        "time_integrator": case.case.rk,
        "combustion_specs_present": sum(cylinder.combustion is not None for cylinder in case.cylinders),
        "fuel_mass_per_cycle_kg": sum(float(cylinder.m_fuel_per_cycle) for cylinder in case.cylinders),
        "crankshaft_rpm": float(case.crankshaft.rpm),
        "legacy_zero_omega_inheritance_sentinel_count": sum(float(cylinder.omega_crank) == 0.0 for cylinder in case.cylinders),
    }


def validate_effective_crank(case: Any) -> dict[str, Any]:
    """Materialise le réseau et vérifie que les 12 cylindres héritent 9000 rpm."""
    from aeolus1d.io.build import build_network

    network = build_network(case)
    cylinders = [
        component
        for component in network.junctions
        if isinstance(getattr(component, "id", None), str)
        and component.id.startswith("c")
        and hasattr(component, "omega_crank")
    ]
    expected = 2.0 * math.pi * float(case.crankshaft.rpm) / 60.0
    require(len(cylinders) == 12, "Aeolus runtime must materialise twelve cylinders")
    require(expected > 0.0, "global crankshaft speed must be positive")
    require(
        all(math.isclose(float(cylinder.omega_crank), expected, rel_tol=1.0e-12, abs_tol=1.0e-12) for cylinder in cylinders),
        "Aeolus runtime cylinders did not inherit the global crankshaft speed",
    )
    return {
        "runtime_cylinder_count": len(cylinders),
        "expected_omega_rad_s": expected,
        "minimum_runtime_omega_rad_s": min(float(cylinder.omega_crank) for cylinder in cylinders),
        "maximum_runtime_omega_rad_s": max(float(cylinder.omega_crank) for cylinder in cylinders),
        "global_crank_inheritance_verified": True,
    }


def expected_runtime_component_ids() -> set[str]:
    return {
        "intake_plenum",
        "exhaust_collector_negative_y",
        "exhaust_collector_positive_y",
        *(f"c{number:02d}" for number in range(1, 13)),
    }


def collect_runtime_diagnostics(
    pipes: dict[str, Any], components: list[Any]
) -> dict[str, Any]:
    """Publie et qualifie chaque état 1D et chaque volume 0D final.

    La vitesse peut être signée. En revanche densité, pression, température,
    masse, volume et énergie interne doivent rester strictement positifs.
    L'absence d'un conduit ou volume attendu ferme aussi la gate de positivité.
    """
    pipe_diagnostics: dict[str, Any] = {}
    component_diagnostics: dict[str, Any] = {}
    finite_fields = True
    positive_state = True
    pipe_density_minima: list[float] = []
    pipe_pressure_minima: list[float] = []
    pipe_temperature_minima: list[float] = []
    component_pressure_minima: list[float] = []
    component_temperature_minima: list[float] = []
    component_volume_minima: list[float] = []
    component_mass_minima: list[float] = []
    component_energy_minima: list[float] = []

    def finite_or_none(value: float) -> float | None:
        return value if math.isfinite(value) else None

    for pipe_id, pipe in sorted(pipes.items()):
        rho_raw, velocity_raw, pressure_raw = pipe.primitives()
        rho = [float(value) for value in rho_raw]
        velocity = [float(value) for value in velocity_raw]
        pressure = [float(value) for value in pressure_raw]
        require(rho and len(rho) == len(velocity) == len(pressure), f"pipe {pipe_id} primitive shape mismatch")
        gas_constant = float(getattr(pipe, "R_gas", 287.05))
        temperature = [
            p / (r * gas_constant) if r != 0.0 and gas_constant != 0.0 else math.inf
            for r, p in zip(rho, pressure)
        ]
        values = rho + velocity + pressure + temperature
        pipe_finite = all(math.isfinite(value) for value in values)
        rho_min = min(rho) if all(math.isfinite(value) for value in rho) else math.nan
        rho_max = max(rho) if all(math.isfinite(value) for value in rho) else math.nan
        velocity_min = min(velocity) if all(math.isfinite(value) for value in velocity) else math.nan
        velocity_max = max(velocity) if all(math.isfinite(value) for value in velocity) else math.nan
        pressure_min = min(pressure) if all(math.isfinite(value) for value in pressure) else math.nan
        pressure_max = max(pressure) if all(math.isfinite(value) for value in pressure) else math.nan
        temperature_min = min(temperature) if all(math.isfinite(value) for value in temperature) else math.nan
        temperature_max = max(temperature) if all(math.isfinite(value) for value in temperature) else math.nan
        pipe_positive = (
            pipe_finite
            and rho_min > 0.0
            and pressure_min > 0.0
            and temperature_min > 0.0
        )
        finite_fields = finite_fields and pipe_finite
        positive_state = positive_state and pipe_positive
        pipe_density_minima.append(rho_min)
        pipe_pressure_minima.append(pressure_min)
        pipe_temperature_minima.append(temperature_min)
        pipe_diagnostics[pipe_id] = {
            "cell_count": int(getattr(pipe, "N", len(rho))),
            "fields_finite": pipe_finite,
            "state_positive": pipe_positive,
            "density_kg_m3_min": finite_or_none(rho_min),
            "density_kg_m3_max": finite_or_none(rho_max),
            "velocity_m_s_min": finite_or_none(velocity_min),
            "velocity_m_s_max": finite_or_none(velocity_max),
            "pressure_pa_abs_min": finite_or_none(pressure_min),
            "pressure_pa_abs_max": finite_or_none(pressure_max),
            "temperature_k_min": finite_or_none(temperature_min),
            "temperature_k_max": finite_or_none(temperature_max),
        }

    for component in components:
        component_id = getattr(component, "id", "")
        if not isinstance(component_id, str) or not component_id or not hasattr(component, "volume"):
            finite_fields = False
            positive_state = False
            continue
        volume = component.volume
        pressure = float(volume.p)
        temperature = float(volume.T)
        volume_m3 = float(volume.V)
        mass = float(volume.m)
        internal_energy = float(volume.E_internal)
        values = [pressure, temperature, volume_m3, mass, internal_energy]
        component_finite = all(math.isfinite(value) for value in values)
        component_positive = component_finite and all(value > 0.0 for value in values)
        finite_fields = finite_fields and component_finite
        positive_state = positive_state and component_positive
        component_pressure_minima.append(pressure)
        component_temperature_minima.append(temperature)
        component_volume_minima.append(volume_m3)
        component_mass_minima.append(mass)
        component_energy_minima.append(internal_energy)
        diagnostic: dict[str, Any] = {
            "kind": "cylinder" if hasattr(component, "last_theta_deg") else "plenum",
            "fields_finite": component_finite,
            "state_positive": component_positive,
            "pressure_pa_abs": finite_or_none(pressure),
            "temperature_k": finite_or_none(temperature),
            "volume_m3": finite_or_none(volume_m3),
            "mass_kg": finite_or_none(mass),
            "internal_energy_j": finite_or_none(internal_energy),
        }
        if hasattr(component, "last_theta_deg"):
            theta_final = float(component.last_theta_deg)
            burned_fraction = float(getattr(component, "last_xb", 0.0))
            fuel_mass = float(getattr(component, "m_fuel_per_cycle", 0.0))
            cylinder_fields_finite = all(
                math.isfinite(value)
                for value in (theta_final, burned_fraction, fuel_mass)
            )
            finite_fields = finite_fields and cylinder_fields_finite
            diagnostic["fields_finite"] = bool(
                diagnostic["fields_finite"] and cylinder_fields_finite
            )
            diagnostic.update(
                {
                    "theta_final_deg": finite_or_none(theta_final),
                    "burned_mass_fraction": finite_or_none(burned_fraction),
                    "combustion_model_present": getattr(component, "combustion", None) is not None,
                    "fuel_mass_per_cycle_kg": finite_or_none(fuel_mass),
                }
            )
        component_diagnostics[component_id] = diagnostic

    expected_pipes = 27
    expected_components = expected_runtime_component_ids()
    exact_coverage = (
        len(pipe_diagnostics) == expected_pipes
        and set(component_diagnostics) == expected_components
        and len(component_diagnostics) == 15
    )
    finite_fields = finite_fields and exact_coverage
    positive_state = positive_state and finite_fields and exact_coverage

    def minimum(values: list[float]) -> float | None:
        if not values or not all(math.isfinite(value) for value in values):
            return None
        return min(values)

    return {
        "finite_fields": finite_fields,
        "positive_state": positive_state,
        "exact_runtime_coverage": exact_coverage,
        "pipe_diagnostic_count": len(pipe_diagnostics),
        "component_diagnostic_count": len(component_diagnostics),
        "pipe_diagnostics": pipe_diagnostics,
        "component_diagnostics": component_diagnostics,
        "state_minima": {
            "pipe_density_kg_m3": minimum(pipe_density_minima),
            "pipe_pressure_pa_abs": minimum(pipe_pressure_minima),
            "pipe_temperature_k": minimum(pipe_temperature_minima),
            "component_pressure_pa_abs": minimum(component_pressure_minima),
            "component_temperature_k": minimum(component_temperature_minima),
            "component_volume_m3": minimum(component_volume_minima),
            "component_mass_kg": minimum(component_mass_minima),
            "component_internal_energy_j": minimum(component_energy_minima),
        },
    }


def execute_case(case: Any, contract: dict[str, Any]) -> dict[str, Any]:
    from aeolus1d.io.case import run_case

    pipes, components, t_final = run_case(case, max_steps=contract["numerical_policy"]["maximum_steps"])
    diagnostics = collect_runtime_diagnostics(pipes, components)
    expected = float(contract["numerical_policy"]["expected_duration_s"])
    tolerance = float(contract["numerical_policy"]["time_completion_relative_tolerance"])
    completed = abs(float(t_final) - expected) <= tolerance * max(expected, 1.0e-30)
    return {
        "executed": True,
        "backend": "aeolus1d",
        "backend_version": importlib.metadata.version("aeolus1d"),
        "t_expected_s": expected,
        "t_final_s": float(t_final),
        "crank_degrees_advanced": float(t_final) * float(contract["variant"]["speed_rpm"]) * 6.0,
        "requested_720_window_completed": completed,
        "finite_fields": diagnostics["finite_fields"],
        "positive_state": diagnostics["positive_state"],
        "exact_runtime_coverage": diagnostics["exact_runtime_coverage"],
        "runtime_component_count": len(components),
        "pipe_diagnostic_count": diagnostics["pipe_diagnostic_count"],
        "component_diagnostic_count": diagnostics["component_diagnostic_count"],
        "pipe_diagnostics": diagnostics["pipe_diagnostics"],
        "component_diagnostics": diagnostics["component_diagnostics"],
        "state_minima": diagnostics["state_minima"],
    }


def derive_numerical_gates(
    *,
    source_hashes_verified: bool,
    topology_contract_valid: bool,
    aeolus_case_constructed: bool,
    execution: dict[str, Any],
) -> dict[str, bool]:
    """Dérive seulement les preuves numériques explicitement observées."""
    return {
        "source_hashes_verified": bool(source_hashes_verified),
        "topology_contract_valid": bool(topology_contract_valid),
        "aeolus_case_constructed": bool(aeolus_case_constructed),
        "full_720_time_march_executed": bool(
            execution.get("executed")
            and execution.get("requested_720_window_completed")
        ),
        "runtime_fields_finite": bool(execution.get("finite_fields")),
        "runtime_state_positive": bool(execution.get("positive_state")),
    }


def build_report(
    contract: dict[str, Any],
    project_root: Path,
    *,
    validate_aeolus: bool,
    execute: bool,
) -> dict[str, Any]:
    validate_contract(contract)
    sources = verify_sources(project_root, contract)
    topology = build_topology(contract)
    validate_topology(topology, contract)
    case = None
    aeolus_validation = False
    summary = None
    execution: dict[str, Any] = {
        "executed": False,
        "backend": "aeolus1d",
        "reason": "manifest_only_no_time_march",
        "requested_720_window_completed": False,
        "finite_fields": False,
        "positive_state": False,
        "exact_runtime_coverage": False,
        "pipe_diagnostic_count": 0,
        "component_diagnostic_count": 0,
        "pipe_diagnostics": {},
        "component_diagnostics": {},
        "state_minima": {
            "pipe_density_kg_m3": None,
            "pipe_pressure_pa_abs": None,
            "pipe_temperature_k": None,
            "component_pressure_pa_abs": None,
            "component_temperature_k": None,
            "component_volume_m3": None,
            "component_mass_kg": None,
            "component_internal_energy_j": None,
        },
    }
    if validate_aeolus or execute:
        case = build_aeolus_case(contract, topology)
        summary = case_summary(case)
        require(summary["pipe_spec_count"] == 27, "Aeolus case must contain 27 pipes")
        require(summary["junction_spec_count"] == 3, "Aeolus case must contain 3 plenum junction specs")
        require(summary["cylinder_spec_count"] == 12, "Aeolus case must contain 12 cylinder specs")
        require(summary["valve_port_count"] == 24, "Aeolus case must contain 24 valve ports")
        require(summary["combustion_specs_present"] == 0, "Aeolus case must remain motored")
        require(summary["fuel_mass_per_cycle_kg"] == 0.0, "Aeolus case fuel input must be zero")
        require(summary["legacy_zero_omega_inheritance_sentinel_count"] == 12, "all cylinder specs must request global crank inheritance")
        summary["effective_crank"] = validate_effective_crank(case)
        aeolus_validation = True
    if execute:
        require(case is not None, "Aeolus case construction required before execution")
        execution = execute_case(case, contract)
    numerical_gates = derive_numerical_gates(
        source_hashes_verified=True,
        topology_contract_valid=True,
        aeolus_case_constructed=aeolus_validation,
        execution=execution,
    )
    return {
        "schema_version": "1.0.0",
        "phase": "F39",
        "status": "motored_unsteady_720_manifest" if not execute else "motored_unsteady_720_run_unvalidated",
        "asset_id": OUTPUT_OWNER,
        "contract_sha256": sha256(DEFAULT_CONTRACT) if DEFAULT_CONTRACT.is_file() and contract == load_json(DEFAULT_CONTRACT) else None,
        "source_evidence": sources,
        "authority_boundary": contract["authority_boundary"],
        "variant": contract["variant"],
        "numerical_policy": contract["numerical_policy"],
        "topology": topology,
        "aeolus_case_summary": summary,
        "execution": execution,
        "numerical_gates": numerical_gates,
        "physical_release_gates": dict(contract["physical_release_gates"]),
        "prohibited_claims": list(contract["prohibited_claims"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-aeolus", action="store_true", help="Construit le Case Aeolus1D sans avancer le temps.")
    parser.add_argument("--execute", action="store_true", help="Exécute un cycle motored 720°; ne prouve aucune performance.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = load_json(args.contract.resolve())
    report = build_report(
        contract,
        args.project_root.resolve(),
        validate_aeolus=bool(args.validate_aeolus),
        execute=bool(args.execute),
    )
    report_path = args.output_dir.resolve() / REPORT_NAME
    write_json(report_path, report)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
