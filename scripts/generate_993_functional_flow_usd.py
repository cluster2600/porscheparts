#!/usr/bin/env python3
"""Generate an F0 OpenUSD view of the Porsche 993 functional flow graph.

The stage is an engineering topology diagram.  It deliberately contains no
vehicle-part geometry, physics schemas, material assignments, collision shapes,
or SimReady claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "twins" / "vehicle-993" / "functional-flow-graph-f0.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "usd" / "993-functional-flow-f0.usda"
CONTRACT = ROOT / "twins" / "vehicle-993" / "functional-flow-openusd-f0.json"


class ContractError(ValueError):
    """Raised when the F0 visualization would be stale or overclaim fidelity."""


FLOW_COLORS: dict[str, tuple[float, float, float]] = {
    "configuration_metadata": (0.45, 0.45, 0.50),
    "mechanical_power": (0.95, 0.25, 0.15),
    "structural_wrench": (0.90, 0.60, 0.10),
    "thermofluid_mass_energy": (0.15, 0.55, 0.95),
    "electrical_power_and_signal": (0.95, 0.90, 0.15),
    "hydraulic_power": (0.55, 0.25, 0.90),
    "kinematic_command": (0.20, 0.80, 0.35),
    "vehicle_state": (0.15, 0.80, 0.80),
    "thermal_energy": (0.95, 0.40, 0.05),
    "occupant_control_load": (0.85, 0.30, 0.65),
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def usd_string(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def usd_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not name or name[0].isdigit():
        name = f"N_{name}"
    return name


def vector(values: tuple[float, float, float]) -> str:
    return f"({values[0]:.4f}, {values[1]:.4f}, {values[2]:.4f})"


def system_positions(system_ids: list[str]) -> dict[str, tuple[float, float, float]]:
    if set(system_ids) != {f"{index}xx" for index in range(10)}:
        raise ContractError("unexpected_system_ids")
    positions = {"0xx": (0.0, 0.0, 0.0)}
    outer_ids = [f"{index}xx" for index in range(1, 10)]
    for index, system_id in enumerate(outer_ids):
        angle = math.radians(90.0 - index * (360.0 / len(outer_ids)))
        positions[system_id] = (2.4 * math.cos(angle), 2.4 * math.sin(angle), 0.0)
    return positions


def render_stage(graph: dict[str, Any]) -> str:
    systems = graph.get("systems", [])
    edges = graph.get("flow_edges", [])
    positions = system_positions([str(item["system_id"]) for item in systems])
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "FunctionalFlow993"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "FunctionalFlow993" (',
        "    customData = {",
        '        string fidelity = "F0_functional_topology"',
        '        string purpose = "engineering_topology_diagram_not_vehicle_geometry"',
        "        bool simreadyValidated = false",
        "        bool physicsAssigned = false",
        "        bool materialAssigned = false",
        "        bool functioningVehicle = false",
        "    }",
        ")",
        "{",
        '    def Scope "Systems"',
        "    {",
    ]
    for system in systems:
        system_id = str(system["system_id"])
        position = positions[system_id]
        marker_color = (0.18, 0.45, 0.75) if system_id != "0xx" else (0.55, 0.55, 0.60)
        lines.extend(
            [
                f'        def Xform "{usd_name(f"System_{system_id}")}"',
                "        {",
                f"            custom string systemId = {usd_string(system_id)}",
                f"            custom string systemName = {usd_string(system.get('name', ''))}",
                f"            custom string criticality = {usd_string(system.get('criticality', ''))}",
                "            custom string fidelity = \"F0_system_marker\"",
                f"            custom int catalogueIllustrationCount = {int(system.get('catalogue_illustration_count', 0))}",
                f"            custom int turboSeedCandidateOccurrenceCount = {int(system.get('turbo_seed_candidate_occurrence_count', 0))}",
                "            custom bool partGeometryPresent = false",
                "            custom bool quantifiedPortsPresent = false",
                f"            double3 xformOp:translate = {vector(position)}",
                '            uniform token[] xformOpOrder = ["xformOp:translate"]',
                "",
                '            def Cube "Marker"',
                "            {",
                "                double size = 0.30",
                f"                color3f[] primvars:displayColor = [{vector(marker_color)}]",
                '                uniform token primvars:displayColor:interpolation = "constant"',
                "            }",
                "        }",
            ]
        )
    lines.extend(["    }", "", '    def Scope "Flows"', "    {"])
    for edge in edges:
        edge_id = str(edge["flow_edge_id"])
        flow_type = str(edge["flow_type_id"])
        if flow_type not in FLOW_COLORS:
            raise ContractError(f"unknown_flow_type:{flow_type}")
        source = positions[str(edge["source_system_id"])]
        target = positions[str(edge["target_system_id"])]
        layer = -0.05 if flow_type == "configuration_metadata" else 0.05
        start = (source[0], source[1], layer)
        end = (target[0], target[1], layer)
        width = 0.012 if flow_type == "configuration_metadata" else 0.025
        lines.extend(
            [
                f'        def BasisCurves "{usd_name(edge_id)}"',
                "        {",
                f"            custom string flowEdgeId = {usd_string(edge_id)}",
                f"            custom string flowTypeId = {usd_string(flow_type)}",
                f"            custom string sourceSystemId = {usd_string(edge['source_system_id'])}",
                f"            custom string targetSystemId = {usd_string(edge['target_system_id'])}",
                f"            custom string direction = {usd_string(edge.get('direction', ''))}",
                f"            custom string topologyStatus = {usd_string(edge.get('topology_status', ''))}",
                "            custom bool quantified = false",
                "            custom bool referenceSolverResultPresent = false",
                "            custom bool physicsNeMoResultPresent = false",
                "            custom bool simreadyBindingPresent = false",
                '            uniform token type = "linear"',
                "            int[] curveVertexCounts = [2]",
                f"            point3f[] points = [{vector(start)}, {vector(end)}]",
                f"            float[] widths = [{width:.4f}]",
                f"            color3f[] primvars:displayColor = [{vector(FLOW_COLORS[flow_type])}]",
                '            uniform token primvars:displayColor:interpolation = "constant"',
                "        }",
            ]
        )
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def build_contract(graph: dict[str, Any], stage: str) -> dict[str, Any]:
    scope = graph.get("scope", {})
    return {
        "$comment": (
            "Scene OpenUSD F0 de topologie fonctionnelle. Elle rend les systemes et "
            "flux inspectables sans representer la geometrie, la physique ou le "
            "fonctionnement du vehicule."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "functional_flow_graph": relative(GRAPH),
            "functional_flow_graph_sha256": sha256_file(GRAPH),
        },
        "stage": {
            "path": relative(OUTPUT),
            "sha256": sha256_bytes(stage.encode("utf-8")),
            "format": "OpenUSD_ASCII",
            "meters_per_unit": 1,
            "up_axis": "Z",
            "fidelity": "F0_functional_topology",
            "system_marker_count": int(scope.get("system_count", 0)),
            "flow_curve_count": int(scope.get("flow_edge_count", 0)),
            "part_geometry_count": 0,
            "quantified_port_count": 0,
            "physics_schema_count": 0,
            "material_assignment_count": 0,
        },
        "validation": {
            "deterministic_ascii_contract": "passed",
            "openusd_python_api": "not_run_requires_preflight",
            "asset_validator": "not_run_requires_preflight",
            "simready_foundation": "not_run_requires_preflight",
            "content_agents_material_physics": "not_run_requires_preflight",
            "property_assignment_intent": "run_for_end_to_end_request",
            "current_status": "authored_pending_cad_to_simready_preflight",
        },
        "claim_boundary": {
            "is_vehicle_geometry": False,
            "is_component_geometry": False,
            "is_physics_assigned": False,
            "is_material_assigned": False,
            "is_simready_validated": False,
            "is_virtual_mission_pass": False,
            "is_functioning_vehicle": False,
        },
        "next_gate": {
            "required": "cad_to_simready_preflight_then_minimum_usd_validation",
            "after_preflight": (
                "assigner les proprietes uniquement aux futures geometries F2/F3 "
                "qualifiees; ne pas conformer ce diagramme comme une voiture"
            ),
        },
    }


def validate(graph: dict[str, Any], stage: str, contract: dict[str, Any]) -> None:
    scope = graph.get("scope", {})
    if scope.get("system_count") != 10 or scope.get("flow_edge_count") != 29:
        raise ContractError("graph_scope")
    if stage.count('def Xform "System_') != 10:
        raise ContractError("system_marker_count")
    if stage.count("def BasisCurves") != 29:
        raise ContractError("flow_curve_count")
    for prohibited in (
        "UsdPhysics",
        "RigidBodyAPI",
        "CollisionAPI",
        "MassAPI",
        "MaterialBindingAPI",
    ):
        if prohibited in stage:
            raise ContractError(f"prohibited_schema:{prohibited}")
    stage_contract = contract.get("stage", {})
    if stage_contract.get("sha256") != sha256_bytes(stage.encode("utf-8")):
        raise ContractError("stage_digest")
    if stage_contract.get("part_geometry_count") != 0:
        raise ContractError("part_geometry_overclaim")
    claims = contract.get("claim_boundary", {})
    if any(value is not False for value in claims.values()):
        raise ContractError("claim_boundary")
    validation = contract.get("validation", {})
    if validation.get("deterministic_ascii_contract") != "passed":
        raise ContractError("ascii_contract")
    if validation.get("current_status") != "authored_pending_cad_to_simready_preflight":
        raise ContractError("validation_status")


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        graph = load_json(GRAPH)
        stage = render_stage(graph)
        contract = build_contract(graph, stage)
        validate(graph, stage, contract)
        expected_contract = render_json(contract)
        if args.write:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(stage, encoding="utf-8")
            CONTRACT.write_text(expected_contract, encoding="utf-8")
            print(f"wrote {relative(OUTPUT)}")
            print(f"wrote {relative(CONTRACT)}")
            return 0
        for path in (OUTPUT, CONTRACT):
            if not path.is_file():
                print(f"missing:{path}")
                return 1
        if args.check:
            if OUTPUT.read_text(encoding="utf-8") != stage:
                print(f"stale:{OUTPUT}")
                return 1
            if CONTRACT.read_text(encoding="utf-8") != expected_contract:
                print(f"stale:{CONTRACT}")
                return 1
        checked_contract = load_json(CONTRACT)
        checked_stage = OUTPUT.read_text(encoding="utf-8")
        validate(graph, checked_stage, checked_contract)
        if checked_contract.get("source_boundary", {}).get(
            "functional_flow_graph_sha256"
        ) != sha256_file(GRAPH):
            raise ContractError("source_digest")
        print(f"valid {relative(OUTPUT)}")
        print(f"valid {relative(CONTRACT)}")
        return 0
    except ContractError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
