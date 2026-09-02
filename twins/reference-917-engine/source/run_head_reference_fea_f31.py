#!/usr/bin/env python3
"""Exécute le criblage EF 3D F31 des quatre concepts de culasse F29."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import subprocess
from typing import Any

import gmsh
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = ROOT / "twins/reference-917-engine/head-reference-cae-f31.json"
DEFAULT_OUTPUT = ROOT / "work/917-head-reference-cae-f31"


class F31Error(RuntimeError):
    """Une entrée, un maillage ou un calcul F31 est invalide."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise F31Error(f"expected_json_object:{path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"


def calculix_version() -> str:
    completed = subprocess.run(
        ["ccx", "-v"], capture_output=True, text=True, check=False
    )
    match = re.search(
        r"(?:CalculiX\s+)?Version\s+([0-9.]+)",
        completed.stdout + completed.stderr,
    )
    if not match:
        raise F31Error("calculix_version_not_detected")
    return match.group(1)


def node_set(name: str, node_ids: list[int]) -> str:
    if not node_ids:
        raise F31Error(f"empty_node_set:{name}")
    rows = [
        ", ".join(str(node_id) for node_id in node_ids[index : index + 16])
        for index in range(0, len(node_ids), 16)
    ]
    return f"*NSET, NSET={name}\n" + "\n".join(rows) + "\n"


def verify_inputs(
    root: Path,
    contract: dict[str, Any],
    study: dict[str, Any],
    geometry_report: dict[str, Any],
) -> dict[str, dict[str, Path]]:
    if contract.get("phase") != "F31":
        raise F31Error("contract_phase_mismatch")
    if any(contract.get("release_gates", {}).values()):
        raise F31Error("release_gate_open")
    if study.get("phase") != "F29" or len(study.get("variants", [])) != 4:
        raise F31Error("f29_study_not_four_variants")
    if geometry_report.get("variant_count") != 4:
        raise F31Error("f29_geometry_report_not_four_variants")

    report_variants = {item["id"]: item for item in geometry_report["variants"]}
    paths: dict[str, dict[str, Path]] = {}
    for variant in study["variants"]:
        variant_id = variant["id"]
        if variant_id not in report_variants:
            raise F31Error(f"geometry_report_missing_variant:{variant_id}")
        step_info = report_variants[variant_id]["step"]
        stl_info = report_variants[variant_id]["stl"]
        geometry_root = root / contract["input"]["geometry_root"]
        step_path = geometry_root / step_info["path"]
        stl_path = geometry_root / stl_info["path"]
        if not step_path.is_file() or sha256(step_path) != step_info["sha256"]:
            raise F31Error(f"step_digest_mismatch:{variant_id}")
        if not stl_path.is_file() or sha256(stl_path) != stl_info["sha256"]:
            raise F31Error(f"stl_digest_mismatch:{variant_id}")
        paths[variant_id] = {"step": step_path, "stl": stl_path}
    return paths


def mesh_defeatured_variant(
    variant: dict[str, Any],
    contract: dict[str, Any],
    mesh_size_mm: float,
    mesh_path: Path,
    geometry_path: Path,
) -> tuple[dict[int, np.ndarray], int, dict[str, Any]]:
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size_mm * 0.65)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 18)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.model.add("head_f31")
        bore_radius = float(variant["bore_mm"]) / 2.0
        params = variant["cad_parameters"]
        height_mm = float(contract["solver_geometry"]["height_mm"])
        outer_radius_mm = float(params["outer_radius_mm"])
        body = gmsh.model.occ.addCylinder(
            0.0, 0.0, 0.0, 0.0, 0.0, height_mm, outer_radius_mm
        )
        chamber_center_z = -bore_radius + float(params["chamber_depth_mm"])
        tools = [
            (3, gmsh.model.occ.addSphere(0.0, 0.0, chamber_center_z, bore_radius))
        ]

        through_start = -2.0
        through_height = height_mm + 4.0
        spark_radius = float(params["spark_plug_bore_diameter_mm"]) / 2.0
        tools.append(
            (
                3,
                gmsh.model.occ.addCylinder(
                    0.0, 0.0, through_start, 0.0, 0.0, through_height, spark_radius
                ),
            )
        )
        fastener_radius = float(params["fastener_hole_diameter_mm"]) / 2.0
        fastener_ring = bore_radius + 10.0
        for angle_degrees in (45.0, 135.0, 225.0, 315.0):
            angle = math.radians(angle_degrees)
            tools.append(
                (
                    3,
                    gmsh.model.occ.addCylinder(
                        fastener_ring * math.cos(angle),
                        fastener_ring * math.sin(angle),
                        through_start,
                        0.0,
                        0.0,
                        through_height,
                        fastener_radius,
                    ),
                )
            )
        for valve_type, diameter_key in (
            ("intake", "intake_diameter_mm"),
            ("exhaust", "exhaust_diameter_mm"),
        ):
            throat_radius = 0.43 * float(variant[diameter_key])
            for x_mm, y_mm in variant["valve_positions_xy_mm"][valve_type]:
                tools.append(
                    (
                        3,
                        gmsh.model.occ.addCylinder(
                            float(x_mm),
                            float(y_mm),
                            through_start,
                            0.0,
                            0.0,
                            through_height,
                            throat_radius,
                        ),
                    )
                )
        cut_entities, _ = gmsh.model.occ.cut([(3, body)], tools, removeObject=True, removeTool=True)
        gmsh.model.occ.synchronize()
        volumes = [tag for dimension, tag in cut_entities if dimension == 3]
        if len(volumes) != 1:
            raise F31Error(
                f"defeatured_geometry_not_one_volume:{variant['id']}:{len(volumes)}"
            )
        volume = volumes[0]
        volume_mm3 = float(gmsh.model.occ.getMass(3, volume))
        gmsh.model.addPhysicalGroup(3, [volume], name="BODY")
        gmsh.write(str(geometry_path))
        try:
            gmsh.model.mesh.generate(3)
        except Exception as exc:
            raise F31Error(
                f"gmsh_volume_mesh_failed:{variant['id']}:{mesh_size_mm}:{gmsh.logger.getLastError()}"
            ) from exc
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        element_types, element_tags, _ = gmsh.model.mesh.getElements(3, volume)
        tetrahedron_count = 0
        for element_type, tags in zip(element_types, element_tags):
            properties = gmsh.model.mesh.getElementProperties(element_type)
            if properties[0].startswith("Tetrahedron"):
                tetrahedron_count += len(tags)
        nodes = {
            int(tag): np.asarray(coordinates[3 * index : 3 * index + 3], dtype=float)
            for index, tag in enumerate(node_tags)
        }
        gmsh.option.setNumber("Mesh.SaveAll", 0)
        gmsh.write(str(mesh_path))
    finally:
        gmsh.finalize()
    if not nodes or tetrahedron_count <= 0:
        raise F31Error(f"empty_volume_mesh:{variant['id']}")
    geometry_metrics = {
        "kind": "defeatured_deck_volume",
        "height_mm": height_mm,
        "volume_mm3": volume_mm3,
        "geometry_sha256": sha256(geometry_path),
        "direct_f29_step_or_stl_meshed": False,
    }
    return nodes, tetrahedron_count, geometry_metrics


def select_boundary_nodes(
    nodes: dict[int, np.ndarray],
    variant: dict[str, Any],
    mesh_size_mm: float,
) -> dict[str, list[int]]:
    bore_radius = float(variant["bore_mm"]) / 2.0
    chamber_depth = float(variant["cad_parameters"]["chamber_depth_mm"])
    chamber_center_z = -bore_radius + chamber_depth
    deck_tolerance = max(0.12, mesh_size_mm * 0.04)
    sphere_tolerance = max(0.45, mesh_size_mm * 0.12)

    deck = sorted(
        node_id
        for node_id, xyz in nodes.items()
        if abs(float(xyz[2])) <= deck_tolerance
    )
    deck_ids = set(deck)
    chamber = sorted(
        node_id
        for node_id, xyz in nodes.items()
        if node_id not in deck_ids
        and deck_tolerance < float(xyz[2]) <= chamber_depth + sphere_tolerance
        and abs(
            math.sqrt(
                float(xyz[0]) ** 2
                + float(xyz[1]) ** 2
                + (float(xyz[2]) - chamber_center_z) ** 2
            )
            - bore_radius
        )
        <= sphere_tolerance
    )
    if len(deck) < 8:
        raise F31Error(f"insufficient_deck_nodes:{len(deck)}")
    if len(chamber) < 8:
        raise F31Error(f"insufficient_chamber_nodes:{len(chamber)}")

    anchor = min(deck, key=lambda node_id: (nodes[node_id][0], nodes[node_id][1]))
    guide_candidates = [node_id for node_id in deck if node_id != anchor]
    guide = max(guide_candidates, key=lambda node_id: nodes[node_id][0])
    return {
        "all": sorted(nodes),
        "deck": deck,
        "chamber": chamber,
        "anchor": [anchor],
        "guide": [guide],
    }


def thermal_field_c(
    nodes: dict[int, np.ndarray],
    ambient_c: float,
    chamber_c: float,
    head_height_mm: float,
) -> dict[int, float]:
    delta = chamber_c - ambient_c
    values = {}
    for node_id, xyz in nodes.items():
        height_fraction = min(1.0, max(0.0, float(xyz[2]) / head_height_mm))
        values[node_id] = ambient_c + delta * (1.0 - height_fraction) ** 1.7
    return values


def write_deck(
    mesh_path: Path,
    solve_path: Path,
    nodes: dict[int, np.ndarray],
    sets: dict[str, list[int]],
    contract: dict[str, Any],
    variant: dict[str, Any],
    load_case: str,
) -> dict[str, float]:
    if load_case not in set(contract["solver"]["load_cases"]):
        raise F31Error(f"unsupported_load_case:{load_case}")
    material = contract["material"]
    bc = contract["boundary_conditions"]
    scenario_pressure_mpa = float(variant["screening_peak_cylinder_pressure_mpa"])
    bore_area_mm2 = math.pi * (float(variant["bore_mm"]) / 2.0) ** 2
    pressure_resultant_n = scenario_pressure_mpa * bore_area_mm2
    node_force_n = pressure_resultant_n / len(sets["chamber"])
    chamber_temperature_c = (
        float(bc["turbo_chamber_screening_temperature_c"])
        if "turbo" in variant["scenario_id"]
        else float(bc["na_chamber_screening_temperature_c"])
    )
    temperatures = thermal_field_c(
        nodes,
        float(bc["ambient_temperature_c"]),
        chamber_temperature_c,
        float(variant["cad_parameters"]["head_height_mm"]),
    )
    temperature_rows = "\n".join(
        f"{node_id}, {temperatures[node_id]:.8f}" for node_id in sorted(temperatures)
    )
    load_rows = "\n".join(
        f"{node_id}, 3, {node_force_n:.12f}" for node_id in sets["chamber"]
    )
    temperature_block = ""
    if load_case in {"thermal_only", "combined"}:
        temperature_block = "*TEMPERATURE\n" + temperature_rows + "\n"
    else:
        temperature_block = (
            "*TEMPERATURE\n"
            + f"NALL, {float(bc['ambient_temperature_c']):.8f}\n"
        )
    load_block = ""
    if load_case in {"pressure_only", "combined"}:
        load_block = "*CLOAD\n" + load_rows + "\n"
    deck = (
        f"*INCLUDE, INPUT={mesh_path.name}\n"
        + node_set("NALL", sets["all"])
        + node_set("DECK", sets["deck"])
        + node_set("CHAMBER", sets["chamber"])
        + node_set("ANCHOR", sets["anchor"])
        + node_set("GUIDE", sets["guide"])
        + "*MATERIAL, NAME=ALF357_SCREEN\n"
        + "*ELASTIC\n"
        + f"{float(material['youngs_modulus_mpa']):.8f}, {float(material['poisson_ratio']):.8f}\n"
        + "*EXPANSION\n"
        + f"{float(material['thermal_expansion_per_k']):.12f}\n"
        + "*DENSITY\n"
        + f"{float(material['density_kg_m3']) * 1.0e-12:.12e}\n"
        + "*SOLID SECTION, ELSET=BODY, MATERIAL=ALF357_SCREEN\n"
        + "*INITIAL CONDITIONS, TYPE=TEMPERATURE\n"
        + f"NALL, {float(bc['ambient_temperature_c']):.8f}\n"
        + "*STEP\n*STATIC\n"
        + "*BOUNDARY\nDECK, 3, 3\nANCHOR, 1, 2\nGUIDE, 2, 2\n"
        + temperature_block
        + load_block
        + "*NODE PRINT, NSET=NALL\nU\n"
        + "*NODE PRINT, NSET=DECK\nRF\n"
        + "*EL PRINT, ELSET=BODY\nS\n"
        + "*END STEP\n"
    )
    solve_path.write_text(deck, encoding="utf-8", newline="\n")
    return {
        "pressure_mpa": scenario_pressure_mpa,
        "projected_bore_area_mm2": bore_area_mm2,
        "applied_axial_resultant_n": pressure_resultant_n,
        "force_per_chamber_node_n": node_force_n,
        "ambient_temperature_c": float(bc["ambient_temperature_c"]),
        "chamber_screening_temperature_c": chamber_temperature_c,
        "pressure_applied": load_case in {"pressure_only", "combined"},
        "thermal_field_applied": load_case in {"thermal_only", "combined"},
    }


def parse_dat(dat_path: Path) -> dict[str, float]:
    lines = dat_path.read_text(encoding="utf-8", errors="replace").splitlines()
    displacements: list[float] = []
    reaction_z: list[float] = []
    von_mises: list[float] = []
    mode = ""
    for line in lines:
        lower = line.lower()
        if "displacements (vx,vy,vz)" in lower:
            mode = "u"
            continue
        if "forces (fx,fy,fz)" in lower:
            mode = "rf"
            continue
        if "stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz)" in lower:
            mode = "s"
            continue
        parts = line.split()
        if mode in {"u", "rf"} and len(parts) == 4 and parts[0].isdigit():
            values = [float(value) for value in parts[1:]]
            if mode == "u":
                displacements.append(math.sqrt(sum(value * value for value in values)))
            else:
                reaction_z.append(values[2])
            continue
        if mode == "s" and len(parts) == 8 and parts[0].isdigit() and parts[1].isdigit():
            sxx, syy, szz, sxy, sxz, syz = (float(value) for value in parts[2:])
            mises = math.sqrt(
                0.5
                * (
                    (sxx - syy) ** 2
                    + (syy - szz) ** 2
                    + (szz - sxx) ** 2
                    + 6.0 * (sxy**2 + sxz**2 + syz**2)
                )
            )
            von_mises.append(mises)
            continue
    if not displacements or not von_mises or not reaction_z:
        raise F31Error(
            f"incomplete_calculix_dat:u={len(displacements)}:s={len(von_mises)}:rf={len(reaction_z)}"
        )
    stresses = np.asarray(von_mises, dtype=float)
    return {
        "maximum_displacement_mm": float(max(displacements)),
        "maximum_von_mises_mpa": float(np.max(stresses)),
        "p95_von_mises_mpa": float(np.percentile(stresses, 95.0)),
        "p99_von_mises_mpa": float(np.percentile(stresses, 99.0)),
        "summed_deck_reaction_z_n": float(sum(reaction_z)),
        "stress_integration_point_count": int(len(stresses)),
    }


def solve_case(
    root: Path,
    output_root: Path,
    contract: dict[str, Any],
    variant: dict[str, Any],
    geometry_paths: dict[str, Path],
    mesh_size_mm: float,
) -> dict[str, Any]:
    case_dir = output_root / variant["id"] / f"mesh-{mesh_size_mm:g}mm"
    case_dir.mkdir(parents=True, exist_ok=False)
    mesh_path = case_dir / "mesh.inp"
    solver_geometry_path = case_dir / "solver-geometry.step"
    nodes, tetrahedron_count, geometry_metrics = mesh_defeatured_variant(
        variant,
        contract,
        mesh_size_mm,
        mesh_path,
        solver_geometry_path,
    )
    sets = select_boundary_nodes(nodes, variant, mesh_size_mm)
    load_case_results = {}
    for load_case in contract["solver"]["load_cases"]:
        solve_path = case_dir / f"{load_case}.inp"
        loads = write_deck(
            mesh_path, solve_path, nodes, sets, contract, variant, load_case
        )
        completed = subprocess.run(
            ["ccx", "-i", load_case],
            cwd=case_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        (case_dir / f"{load_case}.stdout.txt").write_text(
            completed.stdout, encoding="utf-8"
        )
        (case_dir / f"{load_case}.stderr.txt").write_text(
            completed.stderr, encoding="utf-8"
        )
        dat_path = case_dir / f"{load_case}.dat"
        if completed.returncode != 0 or not dat_path.is_file():
            tail = (completed.stdout + "\n" + completed.stderr)[-1800:]
            raise F31Error(
                f"calculix_failed:{variant['id']}:{mesh_size_mm}:{load_case}:{tail}"
            )
        load_result = parse_dat(dat_path)
        reaction_balance_error = None
        if load_case == "pressure_only":
            reaction_balance_error = abs(
                abs(load_result["summed_deck_reaction_z_n"])
                - loads["applied_axial_resultant_n"]
            ) / loads["applied_axial_resultant_n"]
        load_result.update(
            {
                "deck_sha256": sha256(solve_path),
                "dat_sha256": sha256(dat_path),
                "calculix_returncode": completed.returncode,
                "loads": loads,
                "pressure_reaction_balance_relative_error": reaction_balance_error,
            }
        )
        load_case_results[load_case] = load_result
    return {
        "mesh_size_mm": mesh_size_mm,
        "node_count": len(nodes),
        "tetrahedron_count": tetrahedron_count,
        "deck_node_count": len(sets["deck"]),
        "chamber_node_count": len(sets["chamber"]),
        "mesh_sha256": sha256(mesh_path),
        "solver_geometry": geometry_metrics,
        "load_cases": load_case_results,
    }


def convergence(cases: list[dict[str, Any]], limit: float) -> dict[str, Any]:
    ordered = sorted(cases, key=lambda item: item["mesh_size_mm"], reverse=True)
    previous, finest = ordered[-2], ordered[-1]
    previous_value = previous["load_cases"]["combined"]["maximum_displacement_mm"]
    finest_value = finest["load_cases"]["combined"]["maximum_displacement_mm"]
    denominator = max(abs(finest_value), 1.0e-12)
    relative_change = abs(
        finest_value - previous_value
    ) / denominator
    return {
        "metric": "maximum_displacement_mm",
        "last_two_mesh_relative_change": relative_change,
        "acceptance_limit": limit,
        "passed": relative_change <= limit,
    }


def run(root: Path, contract_path: Path, output_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise F31Error(f"output_exists:{output_root}")
    contract = load_json(contract_path)
    study_path = root / contract["input"]["design_study"]
    geometry_report_path = root / contract["input"]["geometry_report"]
    study = load_json(study_path)
    geometry_report = load_json(geometry_report_path)
    step_paths = verify_inputs(root, contract, study, geometry_report)
    output_root.mkdir(parents=True)

    scenarios = {
        scenario["id"]: scenario
        for scenario in load_json(
            root / "twins/reference-917-engine/clean-sheet-cylinder-head-f29.json"
        )["scenarios"]
    }
    variants = []
    for variant_source in study["variants"]:
        variant = dict(variant_source)
        scenario = scenarios[variant["scenario_id"]]
        variant["screening_peak_cylinder_pressure_mpa"] = scenario[
            "screening_peak_cylinder_pressure_mpa"
        ]
        cases = [
            solve_case(
                root,
                output_root,
                contract,
                variant,
                step_paths[variant["id"]],
                float(mesh_size),
            )
            for mesh_size in contract["solver"]["mesh_sizes_mm"]
        ]
        convergence_result = convergence(
            cases,
            float(contract["solver"]["maximum_relative_change_last_two_meshes"]),
        )
        finest = min(cases, key=lambda item: item["mesh_size_mm"])
        finest_combined = finest["load_cases"]["combined"]
        variants.append(
            {
                "id": variant["id"],
                "scenario_id": variant["scenario_id"],
                "architecture": variant["architecture"],
                "step_sha256": sha256(step_paths[variant["id"]]["step"]),
                "stl_sha256": sha256(step_paths[variant["id"]]["stl"]),
                "cases": cases,
                "convergence": convergence_result,
                "finest_mesh_summary": finest,
                "screening_yield_margin_p95": float(contract["material"]["screening_yield_mpa"])
                / max(finest_combined["p95_von_mises_mpa"], 1.0e-12),
            }
        )

    comparisons = []
    for scenario_id in sorted({item["scenario_id"] for item in variants}):
        by_architecture = {
            item["architecture"]: item
            for item in variants
            if item["scenario_id"] == scenario_id
        }
        two = by_architecture["2v"]["finest_mesh_summary"]
        four = by_architecture["4v"]["finest_mesh_summary"]
        two_combined = two["load_cases"]["combined"]
        four_combined = four["load_cases"]["combined"]
        comparisons.append(
            {
                "scenario_id": scenario_id,
                "four_valve_change_percent": {
                    "maximum_displacement": 100.0
                    * (
                        four_combined["maximum_displacement_mm"]
                        / two_combined["maximum_displacement_mm"]
                        - 1.0
                    ),
                    "p95_von_mises": 100.0
                    * (
                        four_combined["p95_von_mises_mpa"]
                        / two_combined["p95_von_mises_mpa"]
                        - 1.0
                    ),
                    "tetrahedron_count": 100.0
                    * (four["tetrahedron_count"] / two["tetrahedron_count"] - 1.0),
                },
                "decision_scope": "same_boundary_condition_linear_FEA_screen_only",
            }
        )

    all_cases = [case for item in variants for case in item["cases"]]
    load_runs = [
        load_result
        for case in all_cases
        for load_result in case["load_cases"].values()
    ]
    reaction_limit = float(
        contract["acceptance"]["pressure_only_reaction_balance_relative_error_maximum"]
    )
    passed = (
        len(variants) == 4
        and len(all_cases) == 12
        and all(item["convergence"]["passed"] for item in variants)
        and all(
            case["load_cases"]["pressure_only"][
                "pressure_reaction_balance_relative_error"
            ]
            <= reaction_limit
            for case in all_cases
        )
        and all(
            item["finest_mesh_summary"]["tetrahedron_count"]
            >= int(contract["solver"]["minimum_elements_finest_mesh"])
            for item in variants
        )
    )
    report = {
        "schema_version": "1.0.0",
        "phase": "F31",
        "status": "passed_reference_solver_screening_not_physical_validation" if passed else "failed_closed",
        "toolchain": {
            "gmsh_api": gmsh.GMSH_API_VERSION,
            "calculix": calculix_version(),
            "platform": f"linux/{platform.machine()}",
            "container_policy": "containers/cae-reference-f31.Dockerfile",
        },
        "input_sha256": {
            "contract": sha256(contract_path),
            "design_study": sha256(study_path),
            "geometry_report": sha256(geometry_report_path),
        },
        "variants": variants,
        "comparisons": comparisons,
        "checks": {
            "variant_count": len(variants),
            "case_count": len(all_cases),
            "calculix_run_count": len(load_runs),
            "all_calculix_runs_returned_zero": all(
                item["calculix_returncode"] == 0 for item in load_runs
            ),
            "all_pressure_reaction_balances_passed": all(
                case["load_cases"]["pressure_only"][
                    "pressure_reaction_balance_relative_error"
                ]
                <= reaction_limit
                for case in all_cases
            ),
            "all_mesh_convergence_checks_passed": all(item["convergence"]["passed"] for item in variants),
            "all_finest_meshes_meet_minimum_elements": all(
                item["finest_mesh_summary"]["tetrahedron_count"]
                >= int(contract["solver"]["minimum_elements_finest_mesh"])
                for item in variants
            ),
        },
        "claims": {
            "three_dimensional_linear_fea_executed": True,
            "measured_917_geometry_used": False,
            "validated_boundary_conditions_used": False,
            "hot_material_card_used": False,
            "fatigue_or_tmf_solved": False,
            "physical_correlation_completed": False,
            "manufacturing_or_engine_start_authorized": False,
        },
        "release_gates": contract["release_gates"],
    }
    (output_root / "report.json").write_text(canonical_json(report), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args.root.resolve(), args.contract.resolve(), args.output.resolve())
    except (F31Error, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(canonical_json({"phase": "F31", "status": "failed_closed", "error": str(exc)}))
        return 1
    print(canonical_json({"phase": "F31", "status": report["status"], "output": str(args.output)}))
    return 0 if report["status"].startswith("passed_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
