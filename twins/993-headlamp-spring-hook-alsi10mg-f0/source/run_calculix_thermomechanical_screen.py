#!/usr/bin/env python3
"""Criblage CalculiX thermo-mécanique du crochet de phare AlSi10Mg F0.

Le STEP, les appuis et les chargements restent des hypothèses indépendantes.
Trois maillages C3D10 exécutent chacun un cas froid et un cas stationnaire
température-déplacement. Le calcul vérifie la chaîne, pas le montage 993.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess


PART_ID = "993-ELEC-HEADLAMP-SPRING-HOOK-F0-0001"
TWIN_ID = "TWIN-993-HEADLAMP-SPRING-HOOK-ALSI10MG-F0"

# Enveloppe de régression F0 ; aucune valeur n'est une mesure du phare.
SPRING_FORCE_N = 30.0
REFERENCE_TEMPERATURE_C = 25.0
SOCKET_TEMPERATURE_C = 80.0
TIP_TEMPERATURE_C = 180.0
ANALYTIC_VON_MISES_MPA = 15.347536447260843

# Route publique EOS M 290 / AlSi10Mg / 30 um, état brut de fabrication.
# E et nu ne figurent pas dans la fiche route et restent provisoires.
DENSITY_TONNE_MM3 = 2.67e-9
ELASTIC_MODULUS_MPA = 70_000.0
POISSON_RATIO = 0.33
THERMAL_EXPANSION_PER_K = 22.0e-6
THERMAL_CONDUCTIVITY_W_MM_K = 0.100
VERTICAL_YIELD_MPA = 233.0
MINIMUM_ULTIMATE_MPA = 461.0
FATIGUE_STRENGTH_20M_MPA = 110.0
FATIGUE_REFERENCE_CYCLES = 20_000_000

# Cotes du concept F0, utilisées uniquement pour sélectionner ses surfaces.
CAVITY_LENGTH_MM = 7.5
CAVITY_HALF_WIDTH_MM = 2.25
CAVITY_FLOOR_Z_MM = 1.5
CAVITY_ROOF_Z_MM = 5.5
LOAD_PAD_X_MIN_MM = 13.0
ARM_TOP_Z_MM = 15.0
TIP_X_MIN_MM = 13.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))
    return ordered[index]


def relative_change(current: float, previous: float) -> float:
    if current == 0.0:
        return math.inf
    return abs(current - previous) / abs(current)


def von_mises(components: list[float]) -> float:
    sxx, syy, szz, sxy, sxz, syz = components
    return math.sqrt(
        0.5
        * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy**2 + sxz**2 + syz**2)
    )


def write_set(stream, name: str, values: list[int]) -> None:
    stream.write(f"*NSET,NSET={name}\n")
    for index in range(0, len(values), 16):
        stream.write(",".join(str(value) for value in values[index : index + 16]) + "\n")


def boundary_sets(
    points: dict[int, tuple[float, float, float]],
    boundary_nodes: set[int],
    mesh_size_mm: float,
) -> dict[str, list[int]]:
    tolerance = max(0.08, 0.10 * mesh_size_mm)

    def on_cavity(point: tuple[float, float, float]) -> bool:
        x, y, z = point
        inside_x = -tolerance <= x <= CAVITY_LENGTH_MM + tolerance
        inside_y = abs(y) <= CAVITY_HALF_WIDTH_MM + tolerance
        inside_z = CAVITY_FLOOR_Z_MM - tolerance <= z <= CAVITY_ROOF_Z_MM + tolerance
        side = abs(abs(y) - CAVITY_HALF_WIDTH_MM) <= tolerance and inside_x and inside_z
        floor = abs(z - CAVITY_FLOOR_Z_MM) <= tolerance and inside_x and inside_y
        roof = abs(z - CAVITY_ROOF_Z_MM) <= tolerance and inside_x and inside_y
        end = abs(x - CAVITY_LENGTH_MM) <= tolerance and inside_y and inside_z
        return side or floor or roof or end

    fixed = sorted(tag for tag in boundary_nodes if on_cavity(points[tag]))
    load_pad = sorted(
        tag
        for tag in boundary_nodes
        if points[tag][0] >= LOAD_PAD_X_MIN_MM - tolerance
        and abs(points[tag][2] - ARM_TOP_Z_MM) <= tolerance
    )
    hot_tip = sorted(
        tag
        for tag in boundary_nodes
        if points[tag][0] >= TIP_X_MIN_MM - tolerance
        and points[tag][2] >= 7.0 - tolerance
    )
    sets = {
        "BONDED_CAVITY": fixed,
        "SPRING_LOAD_PAD": load_pad,
        "HOT_TIP": hot_tip,
    }
    missing = {name: len(values) for name, values in sets.items() if len(values) < 4}
    if missing:
        raise RuntimeError(f"insufficient_boundary_nodes:{missing}")
    if set(fixed) & set(hot_tip):
        raise RuntimeError("thermal_boundary_overlap")
    return sets


def mesh_step(step: Path, case: Path, mesh_size_mm: float) -> dict[str, object]:
    import gmsh

    case.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("993_headlamp_spring_hook_alsi10mg_f0")
        gmsh.merge(str(step))
        volumes = gmsh.model.getEntities(3)
        if len(volumes) != 1:
            raise RuntimeError(f"expected_one_volume_got:{len(volumes)}")
        surfaces = gmsh.model.getBoundary(volumes, oriented=False, recursive=False)
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.SecondOrderLinear", 1)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.model.mesh.generate(3)

        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        points = {
            int(tag): tuple(
                float(value) for value in coordinates[3 * index : 3 * index + 3]
            )
            for index, tag in enumerate(node_tags)
        }
        boundary_nodes: set[int] = set()
        for _, surface_tag in surfaces:
            tags, _, _ = gmsh.model.mesh.getNodes(2, surface_tag, includeBoundary=True)
            boundary_nodes.update(int(tag) for tag in tags)

        element_types, element_tags, element_nodes = gmsh.model.mesh.getElements(3)
        elements: list[tuple[int, tuple[int, ...]]] = []
        for element_type, tags, nodes in zip(element_types, element_tags, element_nodes):
            if int(element_type) != 11:
                continue
            for index, tag in enumerate(tags):
                offset = 10 * index
                gmsh_nodes = [int(item) for item in nodes[offset : offset + 10]]
                calculix_nodes = tuple(gmsh_nodes[:8] + [gmsh_nodes[9], gmsh_nodes[8]])
                elements.append((int(tag), calculix_nodes))
        gmsh.write(str(case / "hook.msh"))
    finally:
        gmsh.finalize()

    if not elements:
        raise RuntimeError("no_quadratic_tetrahedra")
    sets = boundary_sets(points, boundary_nodes, mesh_size_mm)
    return {
        "points": points,
        "elements": elements,
        "sets": sets,
        "metrics": {
            "mesh_size_mm": mesh_size_mm,
            "nodes": len(points),
            "quadratic_tetrahedra": len(elements),
            "boundary_nodes": len(boundary_nodes),
            "boundary_set_counts": {name: len(values) for name, values in sets.items()},
        },
    }


def write_common_mesh(stream, mesh: dict[str, object]) -> None:
    points = mesh["points"]
    elements = mesh["elements"]
    sets = mesh["sets"]
    assert isinstance(points, dict)
    assert isinstance(elements, list)
    assert isinstance(sets, dict)
    stream.write("*NODE\n")
    for tag in sorted(points):
        x, y, z = points[tag]
        stream.write(f"{tag},{x:.10g},{y:.10g},{z:.10g}\n")
    stream.write("*ELEMENT,TYPE=C3D10,ELSET=BODY\n")
    for tag, nodes in elements:
        stream.write(f"{tag}," + ",".join(str(node) for node in nodes) + "\n")
    write_set(stream, "NALL", sorted(points))
    for name, values in sets.items():
        write_set(stream, name, values)
    stream.write(
        "*MATERIAL,NAME=ALSI10MG_SCREEN\n"
        "*ELASTIC\n"
        f"{ELASTIC_MODULUS_MPA:.10g},{POISSON_RATIO:.10g}\n"
        f"*EXPANSION,ZERO={REFERENCE_TEMPERATURE_C:.10g}\n"
        f"{THERMAL_EXPANSION_PER_K:.10g}\n"
        "*CONDUCTIVITY\n"
        f"{THERMAL_CONDUCTIVITY_W_MM_K:.10g}\n"
        "*DENSITY\n"
        f"{DENSITY_TONNE_MM3:.10g}\n"
        "*SOLID SECTION,ELSET=BODY,MATERIAL=ALSI10MG_SCREEN\n"
    )


def write_load(stream, mesh: dict[str, object]) -> None:
    load_pad = mesh["sets"]["SPRING_LOAD_PAD"]
    nodal_force_n = -SPRING_FORCE_N / len(load_pad)
    stream.write("*CLOAD\n")
    for tag in load_pad:
        stream.write(f"{tag},3,{nodal_force_n:.12g}\n")


def write_cold_deck(path: Path, mesh: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\n993 headlamp hook AlSi10Mg F0 cold static screen\n")
        write_common_mesh(stream, mesh)
        stream.write("*STEP\n*STATIC\n*BOUNDARY\nBONDED_CAVITY,1,3\n")
        write_load(stream, mesh)
        stream.write(
            "*EL PRINT,ELSET=BODY\nS\n"
            "*NODE PRINT,NSET=NALL\nU\n"
            "*EL FILE\nS\n*NODE FILE\nU\n*END STEP\n"
        )


def write_hot_deck(path: Path, mesh: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\n993 headlamp hook AlSi10Mg F0 sequential hot screen\n")
        write_common_mesh(stream, mesh)
        stream.write(
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\n"
            f"NALL,{REFERENCE_TEMPERATURE_C:.10g}\n"
            "*STEP\n*UNCOUPLED TEMPERATURE-DISPLACEMENT,STEADY STATE\n1.,1.\n"
            "*BOUNDARY\nBONDED_CAVITY,1,3\n"
            f"BONDED_CAVITY,11,11,{SOCKET_TEMPERATURE_C:.10g}\n"
            f"HOT_TIP,11,11,{TIP_TEMPERATURE_C:.10g}\n"
        )
        write_load(stream, mesh)
        stream.write(
            "*EL PRINT,ELSET=BODY\nS\nHFL\n"
            "*NODE PRINT,NSET=NALL\nU\nNT\n"
            "*EL FILE\nS,HFL\n*NODE FILE\nU,NT\n*END STEP\n"
        )


def parse_dat(path: Path, require_temperature: bool) -> dict[str, object]:
    stresses: list[float] = []
    displacements: list[float] = []
    temperatures: list[float] = []
    mode = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw.lower()
        if "stresses" in lower and "sxx" in lower:
            mode = "stress"
            continue
        if "displacements" in lower and ("dx" in lower or "vx" in lower):
            mode = "displacement"
            continue
        if "temperatures" in lower:
            mode = "temperature"
            continue
        fields = raw.split()
        if mode == "stress" and len(fields) >= 8:
            try:
                int(fields[0])
                int(fields[1])
                components = [float(value) for value in fields[2:8]]
            except ValueError:
                continue
            stresses.append(von_mises(components))
        elif mode == "displacement" and len(fields) >= 4:
            try:
                int(fields[0])
                vector = [float(value) for value in fields[1:4]]
            except ValueError:
                continue
            displacements.append(math.sqrt(sum(value**2 for value in vector)))
        elif mode == "temperature" and len(fields) >= 2:
            try:
                int(fields[0])
                temperatures.append(float(fields[1]))
            except ValueError:
                continue
    if not stresses or not displacements:
        raise RuntimeError(f"missing_mechanical_results:{path.name}")
    if require_temperature and not temperatures:
        raise RuntimeError(f"missing_temperature_results:{path.name}")
    result: dict[str, object] = {
        "von_mises_mpa": {
            "p95": percentile(stresses, 0.95),
            "p99": percentile(stresses, 0.99),
            "maximum": max(stresses),
        },
        "displacement_mm": {
            "p99": percentile(displacements, 0.99),
            "maximum": max(displacements),
        },
    }
    if temperatures:
        result["temperature_c"] = {
            "minimum": min(temperatures),
            "p50": percentile(temperatures, 0.50),
            "p95": percentile(temperatures, 0.95),
            "maximum": max(temperatures),
        }
    return result


def run_ccx(ccx: str, case: Path, job: str) -> dict[str, object]:
    completed = subprocess.run(
        [ccx, "-i", job],
        cwd=case,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log = case / f"{job}.log"
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        tail = " | ".join(completed.stdout.splitlines()[-8:])
        raise RuntimeError(f"calculix_failed:{job}:{completed.returncode}:{tail}")
    dat = case / f"{job}.dat"
    frd = case / f"{job}.frd"
    if not dat.is_file() or not frd.is_file():
        raise RuntimeError(f"missing_calculix_outputs:{job}")
    return {
        "return_code": completed.returncode,
        "artifacts": {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in (case / f"{job}.inp", dat, frd, log)
        },
    }


def goodman_screen(peak_stress_mpa: float) -> dict[str, object]:
    alternating = peak_stress_mpa / 2.0
    mean = peak_stress_mpa / 2.0
    corrected_allowable = FATIGUE_STRENGTH_20M_MPA * (
        1.0 - mean / MINIMUM_ULTIMATE_MPA
    )
    return {
        "zero_to_peak_p95_stress_mpa": peak_stress_mpa,
        "alternating_stress_proxy_mpa": alternating,
        "mean_stress_proxy_mpa": mean,
        "modified_goodman_allowable_proxy_mpa": corrected_allowable,
        "coupon_ratio_allowable_to_alternating": corrected_allowable / alternating,
        "reference_cycles": FATIGUE_REFERENCE_CYCLES,
        "equation": "sigma_a/Se + sigma_m/Su = 1",
        "life_prediction": None,
        "transferable_to_part": False,
        "reason": "EOS reports turned fully-reversed coupons; the F0 surface, notch, hot cycle and vibration spectrum are unqualified.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mesh-sizes", default="1.5,1.0,0.7")
    parser.add_argument("--ccx", default="ccx")
    parser.add_argument("--runtime-image-ref", default="not_recorded")
    parser.add_argument("--runtime-image-id", default="not_recorded")
    args = parser.parse_args()

    if not args.step.is_file():
        raise FileNotFoundError(args.step)
    ccx = shutil.which(args.ccx)
    if ccx is None:
        raise RuntimeError(f"calculix_executable_not_found:{args.ccx}")
    import gmsh

    version = subprocess.run(
        [ccx, "-v"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    ).stdout.strip()
    mesh_sizes = [float(value) for value in args.mesh_sizes.split(",")]
    if len(mesh_sizes) < 3 or any(value <= 0.0 for value in mesh_sizes):
        raise ValueError("at_least_three_positive_mesh_sizes_required")
    if mesh_sizes != sorted(mesh_sizes, reverse=True):
        raise ValueError("mesh_sizes_must_be_coarse_to_fine")

    args.work_root.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    for mesh_size_mm in mesh_sizes:
        case = args.work_root / f"mesh-{str(mesh_size_mm).replace('.', 'p')}"
        mesh = mesh_step(args.step, case, mesh_size_mm)
        cold_job = "hook-cold"
        hot_job = "hook-hot"
        write_cold_deck(case / f"{cold_job}.inp", mesh)
        write_hot_deck(case / f"{hot_job}.inp", mesh)
        cold_runtime = run_ccx(ccx, case, cold_job)
        hot_runtime = run_ccx(ccx, case, hot_job)
        cold_results = parse_dat(case / f"{cold_job}.dat", False)
        hot_results = parse_dat(case / f"{hot_job}.dat", True)
        cases.append(
            {
                "mesh": mesh["metrics"],
                "cold_linear_static": {**cold_results, **cold_runtime},
                "hot_sequential_thermomechanical": {**hot_results, **hot_runtime},
            }
        )

    previous = cases[-2]
    finest = cases[-1]
    cold_p95_change = relative_change(
        finest["cold_linear_static"]["von_mises_mpa"]["p95"],
        previous["cold_linear_static"]["von_mises_mpa"]["p95"],
    )
    hot_p95_change = relative_change(
        finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"],
        previous["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"],
    )
    hot_temperature_change = relative_change(
        finest["hot_sequential_thermomechanical"]["temperature_c"]["maximum"],
        previous["hot_sequential_thermomechanical"]["temperature_c"]["maximum"],
    )
    finest_cold_p95 = finest["cold_linear_static"]["von_mises_mpa"]["p95"]
    finest_hot_p95 = finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"]
    fatigue = goodman_screen(finest_cold_p95)
    report = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "status": "f0_real_calculix_six_case_screen_complete_no_print_release",
        "inputs": {
            "runner_repository_path": "twins/993-headlamp-spring-hook-alsi10mg-f0/source/run_calculix_thermomechanical_screen.py",
            "runner_sha256": sha256(Path(__file__).resolve()),
            "step_repository_path": "parts/993-elec-headlamp-spring-hook-f0-0001/derived/headlamp_spring_hook_f0.step",
            "step_sha256": sha256(args.step),
            "geometry_authority": "Independent synthetic F0 BREP; no commercial or OEM surface and no measured headlamp interface.",
            "spring_force_n": SPRING_FORCE_N,
            "force_authority": "Synthetic regression load; spring force, direction, contact patch and service spectrum are not measured.",
            "reference_temperature_c": REFERENCE_TEMPERATURE_C,
            "socket_temperature_c": SOCKET_TEMPERATURE_C,
            "tip_temperature_c": TIP_TEMPERATURE_C,
            "thermal_authority": "Synthetic stationary 100 C gradient; no measured lamp temperature, radiation, convection or adhesive temperature map.",
        },
        "material": {
            "candidate": "EOS Aluminium AlSi10Mg / EOS M 290 / 30 um, as-manufactured screening route",
            "source": "catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json",
            "density_tonne_mm3": DENSITY_TONNE_MM3,
            "published_vertical_yield_mpa": VERTICAL_YIELD_MPA,
            "published_minimum_ultimate_mpa": MINIMUM_ULTIMATE_MPA,
            "published_fatigue_strength_20m_mpa": FATIGUE_STRENGTH_20M_MPA,
            "published_vertical_thermal_conductivity_w_mm_k": THERMAL_CONDUCTIVITY_W_MM_K,
            "published_average_thermal_expansion_25_to_200_per_k": THERMAL_EXPANSION_PER_K,
            "provisional_elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "provisional_poisson_ratio": POISSON_RATIO,
            "temperature_dependent_strength_card_available": False,
            "part_design_allowable_available": False,
        },
        "solver": {
            "analysis": "CalculiX cold linear static plus steady uncoupled temperature-displacement, C3D10",
            "mesh": "Gmsh second-order tetrahedra imported from the exact committed STEP",
            "calculix_version_output": version,
            "gmsh_version": str(gmsh.__version__),
            "python": platform.python_version(),
            "runtime_image_ref": args.runtime_image_ref,
            "runtime_image_id": args.runtime_image_id,
            "execution_count": 2 * len(cases),
        },
        "equations_and_discretization": {
            "beam_reference": "sigma=M*c/I; tau_max=1.5*F/A; sigma_vm=sqrt(sigma^2+3*tau^2)",
            "linear_elasticity": "div(sigma)+b=0; sigma=C:(epsilon-epsilon_th)",
            "thermal_conduction": "div(k*grad(T))=0",
            "thermal_strain": "epsilon_th=alpha*(T-T_ref)",
            "fatigue_proxy": "modified Goodman: sigma_a/Se + sigma_m/Su = 1",
            "load_application": "exact total 30 N distributed equally over external top-pad nodes",
            "restraint": "all displacement degrees fixed on the synthetic inner cavity; conservative rigid-bond idealization",
        },
        "cases": cases,
        "grid_comparison_fine_vs_previous": {
            "cold_p95_stress_relative_change": cold_p95_change,
            "hot_p95_stress_relative_change": hot_p95_change,
            "hot_maximum_temperature_relative_change": hot_temperature_change,
            "screening_threshold": 0.10,
            "threshold_authority": "Project numerical-screen threshold only; not a component acceptance criterion.",
        },
        "analytic_cross_check": {
            "cantilever_von_mises_mpa": ANALYTIC_VON_MISES_MPA,
            "fea_cold_p95_to_analytic_ratio": finest_cold_p95 / ANALYTIC_VON_MISES_MPA,
            "interpretation": "Different restraint and three-dimensional load path are expected; agreement is diagnostic, not calibration.",
        },
        "ambient_reference_strength_ratios": {
            "cold_p95_yield_to_stress": VERTICAL_YIELD_MPA / finest_cold_p95,
            "cold_maximum_yield_to_stress": VERTICAL_YIELD_MPA
            / finest["cold_linear_static"]["von_mises_mpa"]["maximum"],
            "hot_p95_ambient_yield_to_stress": VERTICAL_YIELD_MPA / finest_hot_p95,
            "hot_maximum_ambient_yield_to_stress": VERTICAL_YIELD_MPA
            / finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["maximum"],
            "authority": "Coupon ratios against ambient values only; none is a hot part margin.",
        },
        "fatigue_proxy": fatigue,
        "bond_screen": {
            "analytic_average_shear_mpa": 0.23529411764705882,
            "equation": "tau_average=F/A_bond",
            "adhesive_selected": False,
            "hot_shear_allowable_available": False,
            "peel_stress_solved": False,
            "pass": False,
        },
        "numerical_gates": {
            "six_solver_executions_complete": len(cases) >= 3,
            "cold_p95_grid_change_below_10_percent": cold_p95_change < 0.10,
            "hot_p95_grid_change_below_10_percent": hot_p95_change < 0.10,
            "hot_temperature_grid_change_below_10_percent": hot_temperature_change < 0.10,
        },
        "engineering_gates": {
            "measured_geometry_and_fit": False,
            "measured_spring_load_and_contact": False,
            "measured_thermal_and_vibration_environment": False,
            "qualified_hot_material_and_surface_allowables": False,
            "adhesive_joint_selected_and_solved": False,
            "modal_harmonic_and_vibration_completed": False,
            "part_fatigue_life_completed": False,
            "professional_engineering_review": False,
        },
        "interpretation": {
            "mechanical": "The synthetic 30 N load is solved on the F0 geometry, but actual spring contact and adhesive compliance are absent.",
            "thermal": "The 80-to-180 C imposed field is a conservative numerical screen, not a lamp CHT result.",
            "fatigue": "The Goodman value is a coupon comparison only; it cannot establish component life.",
            "physicsnemo": "No training or inference: six uncorrelated cases are not an admissible surrogate dataset.",
            "manufacturing": "Passing numerical gates cannot authorize printing, bonding, lamp retention or road use.",
        },
        "selected_variant": None,
        "metal_print_authorized": False,
        "vehicle_installation_authorized": False,
        "release_authorized": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "CALCULIX_HEADLAMP_HOOK_F0_PASS "
        f"executions={2 * len(cases)} selected=none "
        f"cold_p95_grid_change={cold_p95_change:.6f} "
        f"hot_p95_grid_change={hot_p95_change:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
