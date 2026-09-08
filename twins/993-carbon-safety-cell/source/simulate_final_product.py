#!/usr/bin/env python3
"""Simule les cas globaux F1 du produit final conceptuel 964/993.

Le modèle reste le treillis linéaire de présélection. Les cas globaux servent à
détecter les chemins trop souples avant la future EF coque composite; ils ne
produisent ni contrainte admissible de stratifié, ni facteur de sécurité.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import build_structural_screening as structural


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "993-carbon-safety-cell"
DEFAULT_CONFIG = TWIN_ROOT / "design-space.json"
DEFAULT_OUTPUT = TWIN_ROOT / "derived" / "final-product-f1-screening.json"


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def selected_architecture(config: dict[str, Any]) -> dict[str, Any]:
    selected = structural.load_json(TWIN_ROOT / "derived" / "structural-screening.json")["selection"]["architecture_id"]
    return next(item for item in config["architectures"] if item["architecture_id"] == selected)


def end_ring_supports(nodes: list[structural.Node]) -> set[tuple[str, int]]:
    return {
        (node.identifier, axis)
        for node in nodes
        if node.identifier.startswith(("F_", "R_"))
        for axis in range(3)
    }


def cabin_nodes(nodes: list[structural.Node]) -> list[str]:
    return sorted(node.identifier for node in nodes if node.identifier.startswith(("A_", "B_")))


def axial_response(
    nodes: list[structural.Node],
    members: list[structural.Member],
    materials: dict[str, dict[str, float]],
    displacements: dict[str, tuple[float, float, float]],
) -> dict[str, Any]:
    node_map = {node.identifier: node for node in nodes}
    rows = []
    for member in members:
        a = node_map[member.node_a]
        b = node_map[member.node_b]
        delta = tuple(bv - av for av, bv in zip(a.xyz, b.xyz))
        length = math.sqrt(sum(value * value for value in delta))
        direction = tuple(value / length for value in delta)
        du = tuple(
            displacements[member.node_b][axis] - displacements[member.node_a][axis]
            for axis in range(3)
        )
        axial_extension = sum(du[axis] * direction[axis] for axis in range(3))
        strain = axial_extension / length
        stress = float(materials[member.material]["elastic_modulus_MPa"]) * strain
        rows.append({
            "member_id": member.identifier,
            "group": member.group,
            "axial_strain": strain,
            "equivalent_axial_stress_MPa": stress,
            "axial_force_N": stress * member.area_mm2,
        })
    governing = max(rows, key=lambda item: abs(item["equivalent_axial_stress_MPa"]))
    return {
        "maximum_absolute_axial_strain": round(max(abs(item["axial_strain"]) for item in rows), 9),
        "maximum_absolute_equivalent_axial_stress_MPa": round(abs(governing["equivalent_axial_stress_MPa"]), 6),
        "governing_member_id": governing["member_id"],
        "governing_member_group": governing["group"],
        "allowable_or_factor_of_safety": None,
    }


def run_inertial_case(
    nodes: list[structural.Node],
    members: list[structural.Member],
    materials: dict[str, dict[str, float]],
    name: str,
    axis: int,
    resultant_N: float,
) -> dict[str, Any]:
    targets = cabin_nodes(nodes)
    load_per_node = resultant_N / len(targets)
    loads = {(node_id, axis): load_per_node for node_id in targets}
    displacements, active_mass = structural.solve_truss(
        nodes, members, materials, loads, end_ring_supports(nodes)
    )
    magnitudes = {
        node_id: math.sqrt(sum(value * value for value in vector))
        for node_id, vector in displacements.items()
    }
    governing_node = max(magnitudes, key=magnitudes.get)
    return {
        "case_id": name,
        "axis": ("X", "Y", "Z")[axis],
        "resultant_N": round(resultant_N, 3),
        "load_application": "resultant répartie uniformément sur les nœuds A/B du treillis",
        "boundary_condition": "anneaux F/R encastrés; interfaces réelles non disponibles",
        "target_node_count": len(targets),
        "maximum_displacement_mm": round(magnitudes[governing_node], 6),
        "governing_node_id": governing_node,
        "active_member_mass_kg": round(active_mass, 3),
        "axial_response": axial_response(nodes, members, materials, displacements),
        "passes_release_requirement": False,
    }


def build_report(config: dict[str, Any]) -> dict[str, Any]:
    architecture = selected_architecture(config)
    nodes, members = structural.build_topology(config, architecture)
    loads = config["mass_and_load_basis"]["load_envelope"]
    cases = [
        run_inertial_case(nodes, members, config["screening_materials"], "vertical_bump_3g", 2, -float(loads["vertical_bump_3g_N"])),
        run_inertial_case(nodes, members, config["screening_materials"], "braking_1_5g", 0, -float(loads["longitudinal_braking_1_5g_N"])),
        run_inertial_case(nodes, members, config["screening_materials"], "cornering_1_8g", 1, -float(loads["lateral_cornering_1_8g_N"])),
    ]
    baseline = structural.analyze_architecture(config, architecture)
    return {
        "schema_version": "1.0.0",
        "simulation_id": "964-993-CARBON-MONOCOQUE-FINAL-PRODUCT-F1-0001",
        "status": "global_load_screening_complete_not_structural_validation",
        "architecture_id": architecture["architecture_id"],
        "model": {
            "type": "linear_3d_pin_jointed_truss",
            "node_count": len(nodes),
            "member_count": len(members),
            "material": "isotropic equivalent carbon for topology ranking",
            "geometry_authority": "F1 hypothesis envelope",
        },
        "existing_local_cases": {
            "torsional_stiffness_Nm_per_deg": baseline["torsion"]["stiffness_Nm_per_deg"],
            "side_intrusion_stiffness_N_per_mm": baseline["side_intrusion"]["stiffness_N_per_mm"],
        },
        "global_inertial_cases": cases,
        "not_proven": [
            "laminate stress, ply failure or delamination",
            "joint, insert, bearing and pull-out strength",
            "buckling, modal response and fatigue",
            "roof crush, impact and crashworthiness",
            "964/993 dimensional compatibility",
            "road, track, TÜV or manufacturing release"
        ],
        "next_solver_model": {
            "mesh": "Gmsh composite shell mesh from measured F2 midsurfaces",
            "reference_solver": "CalculiX composite shell with zone layups",
            "post_processing": "meshio/PyVista/ParaView",
            "surrogate": "PhysicsNeMo only after converged and correlated DOE exists",
            "visualization": "OpenUSD/Omniverse after solver results are traceable"
        },
        "release_gates": {
            "measured_F2_geometry": False,
            "composite_shell_mesh_converged": False,
            "laminate_allowables_correlated": False,
            "joints_and_inserts_correlated": False,
            "modal_buckling_fatigue_passed": False,
            "crash_cases_passed": False,
            "physical_torsion_test_correlated": False,
            "professional_review": False,
            "road_or_track_release": False
        }
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Simulation du produit final — présélection F1",
        "",
        f"Architecture : `{report['architecture_id']}`. Statut : `{report['status']}`.",
        "",
        "| Cas | Résultante | Déplacement maximal | Contrainte axiale équivalente maximale |",
        "|---|---:|---:|---:|",
    ]
    for case in report["global_inertial_cases"]:
        lines.append(
            f"| {case['case_id']} | {abs(case['resultant_N']):.1f} N | "
            f"{case['maximum_displacement_mm']:.3f} mm | "
            f"{case['axial_response']['maximum_absolute_equivalent_axial_stress_MPa']:.3f} MPa |"
        )
    lines.extend([
        "",
        f"Torsion F1 existante : {report['existing_local_cases']['torsional_stiffness_Nm_per_deg']:.1f} N·m/deg. "
        f"Intrusion latérale F1 : {report['existing_local_cases']['side_intrusion_stiffness_N_per_mm']:.1f} N/mm.",
        "",
        "Les contraintes sont celles d'un matériau isotrope équivalent dans un treillis; aucun facteur de sécurité composite n'est calculable.",
        "Toutes les portes de libération restent fermées.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choisir exactement --write ou --check")
    report = build_report(structural.load_json(args.config))
    rendered = canonical_json(report)
    markdown = render_markdown(report)
    markdown_path = args.output.with_suffix(".md")
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        markdown_path.write_text(markdown, encoding="utf-8")
        return 0
    if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
        print(f"{args.output}: sortie absente ou obsolète")
        return 1
    if not markdown_path.exists() or markdown_path.read_text(encoding="utf-8") != markdown:
        print(f"{markdown_path}: sortie absente ou obsolète")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
