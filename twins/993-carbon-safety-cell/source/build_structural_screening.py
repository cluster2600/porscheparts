#!/usr/bin/env python3
"""Présélection EF treillis d'une monocoque carbone 964/993 feuille blanche.

Ce modèle F1 compare des topologies. Il ne représente ni une coque stratifiée,
ni des liaisons collées, ni un crash. Les rigidités et masses produites sont des
indicateurs de classement qui devront être recalés sur une EF coque composite
et sur des essais physiques avant toute décision de fabrication.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "993-carbon-safety-cell"
DEFAULT_CONFIG = TWIN_ROOT / "design-space.json"
DEFAULT_OUTPUT = TWIN_ROOT / "derived"


@dataclass(frozen=True)
class Node:
    identifier: str
    x_mm: float
    y_mm: float
    z_mm: float

    @property
    def xyz(self) -> tuple[float, float, float]:
        return (self.x_mm, self.y_mm, self.z_mm)


@dataclass(frozen=True)
class Member:
    identifier: str
    node_a: str
    node_b: str
    group: str
    material: str
    area_mm2: float


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: objet JSON attendu")
    return value


def _add_member(
    members: list[Member],
    name: str,
    a: str,
    b: str,
    group: str,
    material: str,
    areas: dict[str, float],
) -> None:
    area = float(areas.get(group, 0.0))
    if area > 0.0:
        members.append(Member(name, a, b, group, material, area))


def build_topology(config: dict[str, Any], architecture: dict[str, Any]) -> tuple[list[Node], list[Member]]:
    """Construit un treillis spatial volontairement indépendant des photos ZESAD."""

    geometry = config["screening_geometry_mm"]
    stations = [
        ("F", float(geometry["front_axle_x"]), float(geometry["front_half_track"])),
        ("A", float(geometry["dash_x"]), float(geometry["cell_half_width"])),
        ("B", float(geometry["rear_bulkhead_x"]), float(geometry["cell_half_width"])),
        ("R", float(geometry["rear_axle_x"]), float(geometry["rear_half_track"])),
    ]
    floor_z = float(geometry["floor_z"])
    belt_z = float(geometry["belt_z"])
    roof_z = float(geometry["roof_z"])

    nodes: list[Node] = []
    for station, x_mm, half_width in stations:
        for side, sign in (("L", 1.0), ("R", -1.0)):
            nodes.append(Node(f"{station}_{side}_FLOOR", x_mm, sign * half_width, floor_z))
            nodes.append(Node(f"{station}_{side}_BELT", x_mm, sign * half_width, belt_z))

    if architecture.get("roof_ring"):
        for station, x_mm, half_width in stations[1:3]:
            roof_half_width = half_width * float(geometry["roof_width_ratio"])
            for side, sign in (("L", 1.0), ("R", -1.0)):
                nodes.append(Node(f"{station}_{side}_ROOF", x_mm, sign * roof_half_width, roof_z))

    areas = {key: float(value) for key, value in architecture["effective_member_areas_mm2"].items()}
    members: list[Member] = []
    carbon = "carbon_equivalent"

    # Chaque section transversale est triangulée afin que le modèle treillis ne
    # contienne pas de mécanisme. Ces diagonales représentent une peau travaillante,
    # pas des barres physiques à fabriquer telles quelles.
    for station, _, _ in stations:
        _add_member(members, f"{station}_FLOOR_CROSS", f"{station}_L_FLOOR", f"{station}_R_FLOOR", "floor_cross", carbon, areas)
        _add_member(members, f"{station}_BELT_CROSS", f"{station}_L_BELT", f"{station}_R_BELT", "bulkhead", carbon, areas)
        for side in ("L", "R"):
            _add_member(members, f"{station}_{side}_VERTICAL", f"{station}_{side}_FLOOR", f"{station}_{side}_BELT", "side_vertical", carbon, areas)
        _add_member(members, f"{station}_BULKHEAD_D1", f"{station}_L_FLOOR", f"{station}_R_BELT", "bulkhead_shear", carbon, areas)
        _add_member(members, f"{station}_BULKHEAD_D2", f"{station}_R_FLOOR", f"{station}_L_BELT", "bulkhead_shear", carbon, areas)

    for (station_a, _, _), (station_b, _, _) in zip(stations, stations[1:]):
        for side in ("L", "R"):
            _add_member(members, f"{station_a}{station_b}_{side}_FLOOR_RAIL", f"{station_a}_{side}_FLOOR", f"{station_b}_{side}_FLOOR", "floor_rail", carbon, areas)
            _add_member(members, f"{station_a}{station_b}_{side}_BELT_RAIL", f"{station_a}_{side}_BELT", f"{station_b}_{side}_BELT", "sill", carbon, areas)
            _add_member(members, f"{station_a}{station_b}_{side}_SIDE_D1", f"{station_a}_{side}_FLOOR", f"{station_b}_{side}_BELT", "side_shear", carbon, areas)
            _add_member(members, f"{station_a}{station_b}_{side}_SIDE_D2", f"{station_a}_{side}_BELT", f"{station_b}_{side}_FLOOR", "side_shear", carbon, areas)
        _add_member(members, f"{station_a}{station_b}_FLOOR_D1", f"{station_a}_L_FLOOR", f"{station_b}_R_FLOOR", "floor_shear", carbon, areas)
        _add_member(members, f"{station_a}{station_b}_FLOOR_D2", f"{station_a}_R_FLOOR", f"{station_b}_L_FLOOR", "floor_shear", carbon, areas)
        _add_member(members, f"{station_a}{station_b}_BELT_D1", f"{station_a}_L_BELT", f"{station_b}_R_BELT", "belt_shear", carbon, areas)
        _add_member(members, f"{station_a}{station_b}_BELT_D2", f"{station_a}_R_BELT", f"{station_b}_L_BELT", "belt_shear", carbon, areas)
        _add_member(members, f"{station_a}{station_b}_SPACE_D1", f"{station_a}_L_FLOOR", f"{station_b}_R_BELT", "space_shear", carbon, areas)
        _add_member(members, f"{station_a}{station_b}_SPACE_D2", f"{station_a}_R_FLOOR", f"{station_b}_L_BELT", "space_shear", carbon, areas)
        _add_member(members, f"{station_a}{station_b}_SPACE_D3", f"{station_a}_L_BELT", f"{station_b}_R_FLOOR", "space_shear", carbon, areas)
        _add_member(members, f"{station_a}{station_b}_SPACE_D4", f"{station_a}_R_BELT", f"{station_b}_L_FLOOR", "space_shear", carbon, areas)

    if architecture.get("roof_ring"):
        roof_material = str(architecture.get("roof_material", carbon))
        for station in ("A", "B"):
            for side in ("L", "R"):
                _add_member(members, f"{station}_{side}_PILLAR", f"{station}_{side}_BELT", f"{station}_{side}_ROOF", "roof_pillar", roof_material, areas)
            _add_member(members, f"{station}_ROOF_CROSS", f"{station}_L_ROOF", f"{station}_R_ROOF", "roof_cross", roof_material, areas)
            _add_member(members, f"{station}_ROOF_FRAME_D1", f"{station}_L_BELT", f"{station}_R_ROOF", "roof_shear", roof_material, areas)
            _add_member(members, f"{station}_ROOF_FRAME_D2", f"{station}_R_BELT", f"{station}_L_ROOF", "roof_shear", roof_material, areas)
        for side in ("L", "R"):
            _add_member(members, f"AB_{side}_ROOF_RAIL", f"A_{side}_ROOF", f"B_{side}_ROOF", "roof_rail", roof_material, areas)
        _add_member(members, "AB_ROOF_D1", "A_L_ROOF", "B_R_ROOF", "roof_shear", roof_material, areas)
        _add_member(members, "AB_ROOF_D2", "A_R_ROOF", "B_L_ROOF", "roof_shear", roof_material, areas)
        _add_member(members, "AB_ROOF_SPACE_D1", "A_L_ROOF", "B_R_BELT", "roof_shear", roof_material, areas)
        _add_member(members, "AB_ROOF_SPACE_D2", "A_R_ROOF", "B_L_BELT", "roof_shear", roof_material, areas)
        _add_member(members, "AB_ROOF_SPACE_D3", "B_L_ROOF", "A_R_BELT", "roof_shear", roof_material, areas)
        _add_member(members, "AB_ROOF_SPACE_D4", "B_R_ROOF", "A_L_BELT", "roof_shear", roof_material, areas)
        # Jambes inclinées vers les interfaces avant/arrière : architecture propre
        # au concept et non relevée sur la pièce de référence.
        for side in ("L", "R"):
            _add_member(members, f"FA_{side}_WINDSCREEN", f"F_{side}_BELT", f"A_{side}_ROOF", "roof_rail", roof_material, areas)
            _add_member(members, f"BR_{side}_BACKSTAY", f"B_{side}_ROOF", f"R_{side}_BELT", "roof_rail", roof_material, areas)

    if architecture.get("central_tunnel"):
        tunnel_half = float(geometry["tunnel_half_width"])
        node_index = {node.identifier: node for node in nodes}
        for station, x_mm, _ in stations:
            for side, sign in (("L", 1.0), ("R", -1.0)):
                identifier = f"{station}_TUNNEL_{side}"
                nodes.append(Node(identifier, x_mm, sign * tunnel_half, floor_z + float(geometry["tunnel_height"])))
                _add_member(members, f"{station}_TUNNEL_LINK_{side}", f"{station}_{side}_FLOOR", identifier, "tunnel", carbon, areas)
                opposite = "R" if side == "L" else "L"
                _add_member(members, f"{station}_TUNNEL_CROSS_{side}", f"{station}_{opposite}_FLOOR", identifier, "tunnel_shear", carbon, areas)
                _add_member(members, f"{station}_TUNNEL_BELT_{side}", f"{station}_{side}_BELT", identifier, "tunnel_shear", carbon, areas)
        for (station_a, _, _), (station_b, _, _) in zip(stations, stations[1:]):
            for side in ("L", "R"):
                _add_member(members, f"{station_a}{station_b}_TUNNEL_{side}", f"{station_a}_TUNNEL_{side}", f"{station_b}_TUNNEL_{side}", "tunnel", carbon, areas)
            _add_member(members, f"{station_a}{station_b}_TUNNEL_D1", f"{station_a}_TUNNEL_L", f"{station_b}_TUNNEL_R", "tunnel_shear", carbon, areas)
            _add_member(members, f"{station_a}{station_b}_TUNNEL_D2", f"{station_a}_TUNNEL_R", f"{station_b}_TUNNEL_L", "tunnel_shear", carbon, areas)
        # Eviter une variable locale volontairement inutilisée dans les outils lint.
        del node_index

    identifiers = {node.identifier for node in nodes}
    if len(identifiers) != len(nodes):
        raise ValueError("identifiants de nœuds dupliqués")
    for member in members:
        if member.node_a not in identifiers or member.node_b not in identifiers:
            raise ValueError(f"{member.identifier}: nœud inconnu")
    return nodes, members


def _zeros(size: int) -> list[list[float]]:
    return [[0.0 for _ in range(size)] for _ in range(size)]


def _cholesky_solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Résout Kx=f sans dépendance externe ; K doit être symétrique définie positive."""

    size = len(vector)
    lower = _zeros(size)
    scale = max(max(abs(value) for value in row) for row in matrix)
    tolerance = max(scale * 1.0e-12, 1.0e-9)
    for row in range(size):
        for column in range(row + 1):
            residual = matrix[row][column]
            for inner in range(column):
                residual -= lower[row][inner] * lower[column][inner]
            if row == column:
                if residual <= tolerance:
                    raise ValueError(f"matrice singulière ou mécanisme au ddl {row}: {residual:.6e}")
                lower[row][column] = math.sqrt(residual)
            else:
                lower[row][column] = residual / lower[column][column]

    intermediate = [0.0 for _ in range(size)]
    for row in range(size):
        residual = vector[row]
        for column in range(row):
            residual -= lower[row][column] * intermediate[column]
        intermediate[row] = residual / lower[row][row]

    solution = [0.0 for _ in range(size)]
    for row in range(size - 1, -1, -1):
        residual = intermediate[row]
        for column in range(row + 1, size):
            residual -= lower[column][row] * solution[column]
        solution[row] = residual / lower[row][row]
    return solution


def solve_truss(
    nodes: list[Node],
    members: list[Member],
    materials: dict[str, dict[str, float]],
    loads: dict[tuple[str, int], float],
    fixed_dofs: set[tuple[str, int]],
) -> tuple[dict[str, tuple[float, float, float]], float]:
    node_index = {node.identifier: index for index, node in enumerate(nodes)}
    total_dofs = 3 * len(nodes)
    stiffness = _zeros(total_dofs)
    mass_kg = 0.0

    for member in members:
        a = nodes[node_index[member.node_a]]
        b = nodes[node_index[member.node_b]]
        delta = tuple(b_value - a_value for a_value, b_value in zip(a.xyz, b.xyz))
        length = math.sqrt(sum(value * value for value in delta))
        if length <= 0.0:
            raise ValueError(f"{member.identifier}: longueur nulle")
        direction = tuple(value / length for value in delta)
        material = materials[member.material]
        factor = float(material["elastic_modulus_MPa"]) * member.area_mm2 / length
        local = [[factor * direction[i] * direction[j] for j in range(3)] for i in range(3)]
        indices_a = [3 * node_index[member.node_a] + axis for axis in range(3)]
        indices_b = [3 * node_index[member.node_b] + axis for axis in range(3)]
        for row in range(3):
            for column in range(3):
                value = local[row][column]
                stiffness[indices_a[row]][indices_a[column]] += value
                stiffness[indices_b[row]][indices_b[column]] += value
                stiffness[indices_a[row]][indices_b[column]] -= value
                stiffness[indices_b[row]][indices_a[column]] -= value
        volume_m3 = member.area_mm2 * length * 1.0e-9
        mass_kg += volume_m3 * float(material["density_kg_m3"])

    force = [0.0 for _ in range(total_dofs)]
    for (node_id, axis), value in loads.items():
        force[3 * node_index[node_id] + axis] += value

    fixed = {3 * node_index[node_id] + axis for node_id, axis in fixed_dofs}
    free = [dof for dof in range(total_dofs) if dof not in fixed]
    reduced = [[stiffness[row][column] for column in free] for row in free]
    reduced_force = [force[row] for row in free]
    reduced_solution = _cholesky_solve(reduced, reduced_force)
    full = [0.0 for _ in range(total_dofs)]
    for dof, value in zip(free, reduced_solution):
        full[dof] = value

    displacements = {
        node.identifier: tuple(full[3 * index + axis] for axis in range(3))
        for index, node in enumerate(nodes)
    }
    return displacements, mass_kg


def analyze_architecture(config: dict[str, Any], architecture: dict[str, Any]) -> dict[str, Any]:
    nodes, members = build_topology(config, architecture)
    materials = config["screening_materials"]
    load = config["load_cases"]["torsion_screening"]
    force_n = float(load["opposed_vertical_force_per_side_N"])
    fixed = {
        (f"R_{side}_{level}", axis)
        for side in ("L", "R")
        for level in ("FLOOR", "BELT")
        for axis in range(3)
    }
    if architecture.get("central_tunnel"):
        fixed |= {(f"R_TUNNEL_{side}", axis) for side in ("L", "R") for axis in range(3)}
    displacements, active_mass_kg = solve_truss(
        nodes,
        members,
        materials,
        {("F_L_FLOOR", 2): force_n, ("F_R_FLOOR", 2): -force_n},
        fixed,
    )
    front_track_mm = float(config["screening_geometry_mm"]["front_half_track"]) * 2.0
    twist_rad = (
        displacements["F_L_FLOOR"][2] - displacements["F_R_FLOOR"][2]
    ) / front_track_mm
    torque_n_mm = force_n * front_track_mm
    torsional_stiffness = torque_n_mm / abs(twist_rad) / 1000.0 * math.pi / 180.0

    lateral = config["load_cases"]["side_intrusion_screening"]
    lateral_force = float(lateral["inward_force_N"])
    side_fixed = {(f"{station}_R_{level}", axis) for station in ("A", "B") for level in ("FLOOR", "BELT") for axis in range(3)}
    side_fixed |= {(f"R_{side}_FLOOR", axis) for side in ("L", "R") for axis in range(3)}
    if architecture.get("central_tunnel"):
        side_fixed |= {(f"R_TUNNEL_{side}", axis) for side in ("L", "R") for axis in range(3)}
    side_displacements, _ = solve_truss(
        nodes,
        members,
        materials,
        {("A_L_BELT", 1): -lateral_force / 2.0, ("B_L_BELT", 1): -lateral_force / 2.0},
        side_fixed,
    )
    mean_intrusion = abs((side_displacements["A_L_BELT"][1] + side_displacements["B_L_BELT"][1]) / 2.0)
    side_stiffness = lateral_force / mean_intrusion

    primary_materials = sorted({member.material for member in members})
    required_material = str(config["material_policy"]["primary_structure_material"])
    return {
        "architecture_id": architecture["architecture_id"],
        "description": architecture["description"],
        "node_count": len(nodes),
        "member_count": len(members),
        "primary_structure_materials": primary_materials,
        "meets_primary_structure_material_policy": primary_materials == [required_material],
        "active_member_mass_kg": round(active_mass_kg, 3),
        "torsion": {
            "torque_Nm": round(torque_n_mm / 1000.0, 3),
            "twist_deg": round(abs(twist_rad) * 180.0 / math.pi, 6),
            "stiffness_Nm_per_deg": round(torsional_stiffness, 1),
        },
        "side_intrusion": {
            "force_N": lateral_force,
            "mean_displacement_mm": round(mean_intrusion, 6),
            "stiffness_N_per_mm": round(side_stiffness, 1),
        },
        "displacements_mm": {
            node_id: [round(value, 9) for value in vector]
            for node_id, vector in sorted(displacements.items())
        },
    }


def _score_results(config: dict[str, Any], results: list[dict[str, Any]]) -> None:
    target = config["screening_gates"]
    baseline = results[0]["torsion"]["stiffness_Nm_per_deg"]
    for result in results:
        torsion = result["torsion"]["stiffness_Nm_per_deg"]
        mass = result["active_member_mass_kg"]
        ratio = torsion / baseline
        result["screening"] = {
            "relative_torsional_stiffness": round(ratio, 3),
            "specific_torsional_stiffness_Nm_per_deg_per_kg": round(torsion / mass, 1),
            "passes_provisional_torsion_target": torsion >= float(target["provisional_torsional_stiffness_Nm_per_deg"]),
            "passes_relative_improvement_target": ratio >= float(target["minimum_relative_improvement_vs_open_tub"]),
            "passes_active_member_mass_ceiling": mass <= float(target["active_member_mass_ceiling_kg"]),
            "passes_primary_structure_material_policy": result["meets_primary_structure_material_policy"],
        }


def select_architecture(results: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [
        result for result in results
        if result["screening"]["passes_provisional_torsion_target"]
        and result["screening"]["passes_relative_improvement_target"]
        and result["screening"]["passes_active_member_mass_ceiling"]
        and result["screening"]["passes_primary_structure_material_policy"]
    ]
    candidates = eligible or results
    selected = max(
        candidates,
        key=lambda result: (
            result["screening"]["specific_torsional_stiffness_Nm_per_deg_per_kg"],
            result["torsion"]["stiffness_Nm_per_deg"],
        ),
    )
    return {
        "architecture_id": selected["architecture_id"],
        "selection_basis": "meilleure rigidite torsionnelle specifique parmi les candidats tout CFRP qui passent les portes provisoires" if eligible else "aucun candidat tout CFRP ne passe toutes les portes provisoires; meilleur classement exploratoire seulement",
        "eligible_architecture_ids": [result["architecture_id"] for result in eligible],
        "manufacturing_release": False,
        "road_release": False,
        "track_release": False,
    }


def build_report(config: dict[str, Any]) -> dict[str, Any]:
    results = [analyze_architecture(config, architecture) for architecture in config["architectures"]]
    _score_results(config, results)
    selection = select_architecture(results)
    selected_architecture = next(
        architecture for architecture in config["architectures"]
        if architecture["architecture_id"] == selection["architecture_id"]
    )
    platform_screening = []
    for platform_id, dimensions in config["platform_reference_dimensions_mm"].items():
        platform_config = json.loads(json.dumps(config))
        platform_config["screening_geometry_mm"]["front_half_track"] = float(dimensions["front_track"]) / 2.0
        platform_config["screening_geometry_mm"]["rear_half_track"] = float(dimensions["rear_track"]) / 2.0
        platform_result = analyze_architecture(platform_config, selected_architecture)
        platform_screening.append(
            {
                "platform_id": platform_id,
                "wheelbase_mm": dimensions["wheelbase"],
                "front_track_mm": dimensions["front_track"],
                "rear_track_mm": dimensions["rear_track"],
                "active_member_mass_kg": platform_result["active_member_mass_kg"],
                "torsional_stiffness_Nm_per_deg": platform_result["torsion"]["stiffness_Nm_per_deg"],
                "side_intrusion_stiffness_N_per_mm": platform_result["side_intrusion"]["stiffness_N_per_mm"],
                "claim_scope": "enveloppe de voie comme position d'application des charges F1; pas une coordonnee de suspension",
            }
        )
    return {
        "schema_version": "1.0.0",
        "analysis_id": "964-993-CARBON-MONOCOQUE-STRUCTURAL-SCREENING-F1",
        "status": "screening_complete_not_validated",
        "design_origin": "clean_sheet_original_topology",
        "source_boundary": {
            "reference_source": "SRC-ZESAD-CARBON-MONOCOQUE-964-993",
            "use": "fonction et topologie visuelle generales uniquement",
            "copied_dimensions_or_surfaces": False,
            "ruf_supplier_relationship_supported": False,
        },
        "model_scope": {
            "method": "linear_3d_pin_jointed_truss",
            "solver": "dependency_free_cholesky_reference",
            "units": "N_mm_MPa",
            "purpose": "classement relatif de topologies avant EF coque composite",
            "not_proven": [
                "rigidite d'une coque composite reelle",
                "resistance ou rupture du stratifie",
                "flambement, collage, inserts, fatigue, impact ou crash",
                "compatibilite dimensionnelle avec un vehicule 964 ou 993",
                "aptitude route, circuit, fabrication ou homologation",
            ],
        },
        "inputs": {
            "geometry_mm": config["screening_geometry_mm"],
            "materials": config["screening_materials"],
            "load_cases": config["load_cases"],
            "gates": config["screening_gates"],
            "material_policy": config["material_policy"],
            "mass_and_load_basis": config["mass_and_load_basis"],
        },
        "architectures": results,
        "selection": selection,
        "dual_platform_envelope_screening": platform_screening,
        "release_gates": {
            "dimensional_scan_correlated": False,
            "laminate_allowables_from_coupons": False,
            "composite_shell_mesh_converged": False,
            "bonded_joint_models_correlated": False,
            "modal_and_fatigue_cases_passed": False,
            "roof_crush_case_correlated": False,
            "front_side_rear_crash_cases_passed": False,
            "prototype_torsion_test_correlated": False,
            "professional_engineering_review": False,
            "road_homologation": False,
            "track_eligibility": False,
        },
    }


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Présélection structurelle F1 — monocoque carbone 964/993",
        "",
        f"Statut : **{report['status']}**.",
        "",
        "Ce calcul treillis linéaire classe des architectures originales. Il ne prouve ni une coque stratifiée, ni un crash, ni une aptitude route/circuit.",
        "",
        "| Architecture | Matériaux primaires | Masse active (kg) | Torsion (Nm/deg) | Ratio / tub ouvert | Intrusion latérale (N/mm) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for result in report["architectures"]:
        lines.append(
            f"| `{result['architecture_id']}` | {', '.join(result['primary_structure_materials'])} | {result['active_member_mass_kg']:.3f} | "
            f"{result['torsion']['stiffness_Nm_per_deg']:.1f} | "
            f"{result['screening']['relative_torsional_stiffness']:.3f} | "
            f"{result['side_intrusion']['stiffness_N_per_mm']:.1f} |"
        )
    selection = report["selection"]
    lines.extend(
        [
            "",
            "## Sélection numérique",
            "",
            f"Candidat retenu pour la CAO conceptuelle : `{selection['architecture_id']}`.",
            "",
            selection["selection_basis"],
            "",
            "La masse véhicule de 1 200 kg est un objectif de conception. Elle produit une enveloppe préliminaire de 35 303,94 N à 3 g verticaux, sans encore répartir cette charge aux interfaces.",
            "",
            "## Portes restant fermées",
            "",
        ]
    )
    for gate, passed in report["release_gates"].items():
        if not passed:
            lines.append(f"- `{gate}`")
    return "\n".join(lines) + "\n"


def report_csv(report: dict[str, Any]) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        [
            "architecture_id",
            "active_member_mass_kg",
            "torsional_stiffness_Nm_per_deg",
            "relative_torsional_stiffness",
            "side_intrusion_stiffness_N_per_mm",
            "passes_provisional_gates",
        ]
    )
    for result in report["architectures"]:
        screening = result["screening"]
        writer.writerow(
            [
                result["architecture_id"],
                result["active_member_mass_kg"],
                result["torsion"]["stiffness_Nm_per_deg"],
                screening["relative_torsional_stiffness"],
                result["side_intrusion"]["stiffness_N_per_mm"],
                all(
                    screening[key]
                    for key in (
                        "passes_provisional_torsion_target",
                        "passes_relative_improvement_target",
                        "passes_active_member_mass_ceiling",
                        "passes_primary_structure_material_policy",
                    )
                ),
            ]
        )
    return stream.getvalue()


def selected_topology(config: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    architecture_id = report["selection"]["architecture_id"]
    architecture = next(item for item in config["architectures"] if item["architecture_id"] == architecture_id)
    nodes, members = build_topology(config, architecture)
    return {
        "schema_version": "1.0.0",
        "design_id": config["design_id"],
        "architecture": architecture,
        "nodes": [
            {"node_id": node.identifier, "xyz_mm": list(node.xyz)} for node in nodes
        ],
        "members": [
            {
                "member_id": member.identifier,
                "node_a": member.node_a,
                "node_b": member.node_b,
                "group": member.group,
                "material": member.material,
                "effective_area_mm2": member.area_mm2,
            }
            for member in members
        ],
        "claim_scope": "treillis de présélection, pas une définition de stratifié ou de fabrication",
    }


def calculix_deck(config: dict[str, Any], topology: dict[str, Any]) -> str:
    node_numbers = {node["node_id"]: index for index, node in enumerate(topology["nodes"], start=1)}
    rear_fixed_ids = ["R_L_FLOOR", "R_R_FLOOR", "R_L_BELT", "R_R_BELT"]
    rear_fixed_ids.extend(node_id for node_id in ("R_TUNNEL_L", "R_TUNNEL_R") if node_id in node_numbers)
    materials = config["screening_materials"]
    used_material_names = sorted({member["material"] for member in topology["members"]})
    lines = [
        "** 964/993 All-Carbon Monocoque - F1 topology screening only",
        "** NOT A ROAD/TRACK/FABRICATION RELEASE",
        "*NODE",
    ]
    for node in topology["nodes"]:
        x_mm, y_mm, z_mm = node["xyz_mm"]
        lines.append(f"{node_numbers[node['node_id']]}, {x_mm:.6f}, {y_mm:.6f}, {z_mm:.6f}")
    lines.append("*ELEMENT, TYPE=T3D2, ELSET=ALL_MEMBERS")
    element_groups: dict[tuple[str, float], list[int]] = {}
    for element_id, member in enumerate(topology["members"], start=1):
        lines.append(f"{element_id}, {node_numbers[member['node_a']]}, {node_numbers[member['node_b']]}")
        element_groups.setdefault((member["material"], float(member["effective_area_mm2"])), []).append(element_id)
    for set_index, ((material, area), element_ids) in enumerate(sorted(element_groups.items()), start=1):
        set_name = f"SECTION_{set_index}"
        lines.append(f"*ELSET, ELSET={set_name}")
        for offset in range(0, len(element_ids), 12):
            lines.append(", ".join(str(value) for value in element_ids[offset:offset + 12]))
        lines.append(f"*SOLID SECTION, ELSET={set_name}, MATERIAL={material.upper()}")
        lines.append(f"{area:.9f}")
    for name in used_material_names:
        material = materials[name]
        lines.extend(
            [
                f"*MATERIAL, NAME={name.upper()}",
                "*ELASTIC",
                f"{float(material['elastic_modulus_MPa']):.6f}, {float(material['poisson_ratio']):.6f}",
                "*DENSITY",
                f"{float(material['density_kg_m3']) * 1.0e-12:.12e}",
            ]
        )
    lines.extend(
        [
            "*NSET, NSET=REAR_FIXED",
            ", ".join(str(node_numbers[node_id]) for node_id in rear_fixed_ids),
            "*NSET, NSET=FRONT_READ",
            f"{node_numbers['F_L_FLOOR']}, {node_numbers['F_R_FLOOR']}",
            "*STEP",
            "*STATIC",
            "*BOUNDARY",
            "REAR_FIXED, 1, 3",
            "*CLOAD",
        ]
    )
    force = float(config["load_cases"]["torsion_screening"]["opposed_vertical_force_per_side_N"])
    lines.extend(
        [
            f"{node_numbers['F_L_FLOOR']}, 3, {force:.6f}",
            f"{node_numbers['F_R_FLOOR']}, 3, {-force:.6f}",
            "*NODE PRINT, NSET=FRONT_READ",
            "U",
            "*EL PRINT, ELSET=ALL_MEMBERS",
            "S, E",
            "*END STEP",
        ]
    )
    return "\n".join(lines) + "\n"


def build_outputs(config: dict[str, Any]) -> dict[Path, str]:
    report = build_report(config)
    topology = selected_topology(config, report)
    return {
        DEFAULT_OUTPUT / "structural-screening.json": json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        DEFAULT_OUTPUT / "structural-screening.md": report_markdown(report),
        DEFAULT_OUTPUT / "structural-screening.csv": report_csv(report),
        DEFAULT_OUTPUT / "selected-topology.json": json.dumps(topology, indent=2, ensure_ascii=False) + "\n",
        DEFAULT_OUTPUT / "selected-torsion.inp": calculix_deck(config, topology),
    }


def run(write: bool, config_path: Path = DEFAULT_CONFIG) -> int:
    outputs = build_outputs(load_json(config_path))
    stale: list[Path] = []
    for path, content in outputs.items():
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(path)
    if stale:
        for path in stale:
            print(f"stale: {path.relative_to(ROOT)}")
        return 1
    action = "written" if write else "current"
    print(f"carbon safety cell screening: {len(outputs)} outputs {action}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return run(write=args.write, config_path=args.config.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
