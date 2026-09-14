#!/usr/bin/env python3
"""Criblage CalculiX thermo-mécanique du levier de porte AlSi10Mg F0.

Le STEP, les deux alésages encastrés et la charge de 150 N restent des
hypothèses indépendantes. Trois maillages C3D10 exécutent chacun un cas froid
et un cas température-déplacement stationnaire. Ce calcul ferme une boucle
numérique reproductible ; il ne qualifie ni la géométrie 993 ni l'ouverture
d'urgence de la porte.
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


PART_ID = "993-INT-DOOR-OPENER-LEVER-F0-0001"
TWIN_ID = "TWIN-993-DOOR-OPENER-LEVER-ALSI10MG-F0"
PULL_FORCE_N = 150.0
REFERENCE_TEMPERATURE_C = 20.0
HAND_END_TEMPERATURE_C = 80.0
ANALYTIC_VON_MISES_MPA = 45.63288288065964

# EOS M 290 / AlSi10Mg / 30 um, état brut de fabrication publié. Les valeurs
# E et nu sont provisoires et non des admissibles de pièce.
DENSITY_TONNE_MM3 = 2.67e-9
ELASTIC_MODULUS_MPA = 70_000.0
POISSON_RATIO = 0.33
THERMAL_EXPANSION_PER_K = 22.0e-6
THERMAL_CONDUCTIVITY_W_MM_K = 0.100
VERTICAL_YIELD_MPA = 233.0
MINIMUM_ULTIMATE_MPA = 461.0
FATIGUE_STRENGTH_20M_MPA = 110.0
FATIGUE_REFERENCE_CYCLES = 20_000_000

# Variables du concept F0 servant uniquement à retrouver ses surfaces.
MOUNT_BORE_X_MM = (26.0, 44.0)
MOUNT_BORE_RADIUS_MM = 2.5
MOUNT_BORE_Z_MIN_MM = 14.0
MOUNT_BORE_Z_MAX_MM = 20.0
LOAD_PAD_X_MIN_MM = 88.0
PLATE_Z_MIN_MM = 22.0


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
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
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
    tolerance = max(0.10, 0.12 * mesh_size_mm)

    def on_mount_bore(point: tuple[float, float, float]) -> bool:
        x, y, z = point
        if not (MOUNT_BORE_Z_MIN_MM - tolerance <= z <= MOUNT_BORE_Z_MAX_MM + tolerance):
            return False
        return any(
            abs(math.hypot(x - bore_x, y) - MOUNT_BORE_RADIUS_MM) <= tolerance
            for bore_x in MOUNT_BORE_X_MM
        )

    fixed = sorted(tag for tag in boundary_nodes if on_mount_bore(points[tag]))
    load_pad = sorted(
        tag
        for tag in boundary_nodes
        if points[tag][0] >= LOAD_PAD_X_MIN_MM - tolerance
        and points[tag][2] >= PLATE_Z_MIN_MM - tolerance
    )
    sets = {"FIXED_MOUNT_BORES": fixed, "HAND_LOAD_PAD": load_pad}
    missing = {name: len(values) for name, values in sets.items() if len(values) < 4}
    if missing:
        raise RuntimeError(f"insufficient_boundary_nodes:{missing}")
    if set(fixed) & set(load_pad):
        raise RuntimeError("boundary_overlap")
    return sets


def mesh_step(step: Path, case: Path, mesh_size_mm: float) -> dict[str, object]:
    import gmsh

    case.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("993_door_opener_lever_alsi10mg_f0")
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
            int(tag): tuple(float(value) for value in coordinates[3 * index : 3 * index + 3])
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
        gmsh.write(str(case / "door-opener.msh"))
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
    assert isinstance(points, dict) and isinstance(elements, list) and isinstance(sets, dict)
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
    load_pad = mesh["sets"]["HAND_LOAD_PAD"]
    nodal_force_n = PULL_FORCE_N / len(load_pad)
    stream.write("*CLOAD\n")
    for tag in load_pad:
        stream.write(f"{tag},3,{nodal_force_n:.12g}\n")


def write_cold_deck(path: Path, mesh: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\n993 door opener AlSi10Mg F0 cold static screen\n")
        write_common_mesh(stream, mesh)
        stream.write("*STEP\n*STATIC\n*BOUNDARY\nFIXED_MOUNT_BORES,1,3\n")
        write_load(stream, mesh)
        stream.write("*EL PRINT,ELSET=BODY\nS\n*NODE PRINT,NSET=NALL\nU\n*EL FILE\nS\n*NODE FILE\nU\n*END STEP\n")


def write_hot_deck(path: Path, mesh: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\n993 door opener AlSi10Mg F0 sequential hot screen\n")
        write_common_mesh(stream, mesh)
        stream.write(
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\n"
            f"NALL,{REFERENCE_TEMPERATURE_C:.10g}\n"
            "*STEP\n*UNCOUPLED TEMPERATURE-DISPLACEMENT,STEADY STATE\n1.,1.\n"
            "*BOUNDARY\nFIXED_MOUNT_BORES,1,3\n"
            f"FIXED_MOUNT_BORES,11,11,{REFERENCE_TEMPERATURE_C:.10g}\n"
            f"HAND_LOAD_PAD,11,11,{HAND_END_TEMPERATURE_C:.10g}\n"
        )
        write_load(stream, mesh)
        stream.write("*EL PRINT,ELSET=BODY\nS\nHFL\n*NODE PRINT,NSET=NALL\nU\nNT\n*EL FILE\nS,HFL\n*NODE FILE\nU,NT\n*END STEP\n")


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
                int(fields[0]); int(fields[1])
                stresses.append(von_mises([float(value) for value in fields[2:8]]))
            except ValueError:
                continue
        elif mode == "displacement" and len(fields) >= 4:
            try:
                int(fields[0])
                vector = [float(value) for value in fields[1:4]]
                displacements.append(math.sqrt(sum(value**2 for value in vector)))
            except ValueError:
                continue
        elif mode == "temperature" and len(fields) >= 2:
            try:
                int(fields[0]); temperatures.append(float(fields[1]))
            except ValueError:
                continue
    if not stresses or not displacements:
        raise RuntimeError(f"missing_mechanical_results:{path.name}")
    if require_temperature and not temperatures:
        raise RuntimeError(f"missing_temperature_results:{path.name}")
    result: dict[str, object] = {
        "von_mises_mpa": {"p95": percentile(stresses, 0.95), "p99": percentile(stresses, 0.99), "maximum": max(stresses)},
        "displacement_mm": {"p99": percentile(displacements, 0.99), "maximum": max(displacements)},
    }
    if temperatures:
        result["temperature_c"] = {"minimum": min(temperatures), "p50": percentile(temperatures, 0.50), "p95": percentile(temperatures, 0.95), "maximum": max(temperatures)}
    return result


def run_ccx(ccx: str, case: Path, job: str) -> dict[str, object]:
    completed = subprocess.run([ccx, "-i", job], cwd=case, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
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
        "artifacts": {path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in (case / f"{job}.inp", dat, frd, log)},
    }


def goodman_screen(peak_stress_mpa: float) -> dict[str, object]:
    alternating = peak_stress_mpa / 2.0
    mean = peak_stress_mpa / 2.0
    corrected = FATIGUE_STRENGTH_20M_MPA * (1.0 - mean / MINIMUM_ULTIMATE_MPA)
    return {
        "zero_to_peak_p95_stress_mpa": peak_stress_mpa,
        "alternating_stress_proxy_mpa": alternating,
        "mean_stress_proxy_mpa": mean,
        "modified_goodman_allowable_proxy_mpa": corrected,
        "coupon_ratio_allowable_to_alternating": corrected / alternating,
        "reference_cycles": FATIGUE_REFERENCE_CYCLES,
        "equation": "sigma_a/Se + sigma_m/Su = 1",
        "life_prediction": None,
        "transferable_to_part": False,
        "reason": "EOS reports turned fully-reversed coupons; the F0 notch, raw surface, porosity and door duty cycle are unqualified.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mesh-sizes", default="4.0,3.0,2.2")
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

    version = subprocess.run([ccx, "-v"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout.strip()
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
        cold_job = "door-opener-cold"
        hot_job = "door-opener-hot"
        write_cold_deck(case / f"{cold_job}.inp", mesh)
        write_hot_deck(case / f"{hot_job}.inp", mesh)
        cold_runtime = run_ccx(ccx, case, cold_job)
        hot_runtime = run_ccx(ccx, case, hot_job)
        cases.append({
            "mesh": mesh["metrics"],
            "cold_linear_static": {**parse_dat(case / f"{cold_job}.dat", False), **cold_runtime},
            "hot_sequential_thermomechanical": {**parse_dat(case / f"{hot_job}.dat", True), **hot_runtime},
        })

    previous, finest = cases[-2], cases[-1]
    cold_change = relative_change(finest["cold_linear_static"]["von_mises_mpa"]["p95"], previous["cold_linear_static"]["von_mises_mpa"]["p95"])
    hot_change = relative_change(finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"], previous["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"])
    temperature_change = relative_change(finest["hot_sequential_thermomechanical"]["temperature_c"]["maximum"], previous["hot_sequential_thermomechanical"]["temperature_c"]["maximum"])
    finest_cold_p95 = finest["cold_linear_static"]["von_mises_mpa"]["p95"]
    finest_hot_p95 = finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"]

    report = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "status": "f0_real_calculix_six_case_screen_complete_no_print_or_vehicle_release",
        "inputs": {
            "runner_repository_path": "twins/993-door-opener-lever-alsi10mg-f0/source/run_calculix_thermomechanical_screen.py",
            "runner_sha256": sha256(Path(__file__).resolve()),
            "step_repository_path": "parts/993-int-door-opener-lever-f0-0001/derived/door_opener_lever_f0.step",
            "step_sha256": sha256(args.step),
            "geometry_authority": "Independent synthetic F0 BREP constrained only by a commercial product envelope; no measured Porsche interface.",
            "pull_force_n": PULL_FORCE_N,
            "force_authority": "Synthetic regression load; real pull vector, stops, misuse and cycle spectrum are not measured.",
            "reference_temperature_c": REFERENCE_TEMPERATURE_C,
            "hand_end_temperature_c": HAND_END_TEMPERATURE_C,
            "thermal_authority": "Synthetic stationary 60 C gradient; no measured door temperature, convection or solar loading.",
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
            "mesh": "Gmsh second-order tetrahedra imported from the exact STEP",
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
            "load_application": "exact total 150 N distributed equally over the synthetic hand-end surface nodes",
            "restraint": "all displacement degrees fixed on both synthetic mounting bore surfaces; conservative rigid-bond idealization",
        },
        "cases": cases,
        "grid_comparison_fine_vs_previous": {
            "cold_p95_stress_relative_change": cold_change,
            "hot_p95_stress_relative_change": hot_change,
            "hot_maximum_temperature_relative_change": temperature_change,
            "screening_threshold": 0.10,
            "threshold_authority": "Project numerical-screen threshold only; not a component acceptance criterion.",
        },
        "analytic_cross_check": {
            "cantilever_von_mises_mpa": ANALYTIC_VON_MISES_MPA,
            "fea_cold_p95_to_analytic_ratio": finest_cold_p95 / ANALYTIC_VON_MISES_MPA,
            "interpretation": "The analytic cantilever and two-bore 3D restraint differ; their ratio is diagnostic, not calibration.",
        },
        "ambient_reference_strength_ratios": {
            "cold_p95_yield_to_stress": VERTICAL_YIELD_MPA / finest_cold_p95,
            "cold_maximum_yield_to_stress": VERTICAL_YIELD_MPA / finest["cold_linear_static"]["von_mises_mpa"]["maximum"],
            "hot_p95_ambient_yield_to_stress": VERTICAL_YIELD_MPA / finest_hot_p95,
            "hot_maximum_ambient_yield_to_stress": VERTICAL_YIELD_MPA / finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["maximum"],
            "authority": "Coupon ratios against ambient values only; none is a hot component margin.",
        },
        "fatigue_proxy": goodman_screen(finest_cold_p95),
        "numerical_gates": {
            "six_solver_executions_complete": len(cases) >= 3,
            "cold_p95_grid_change_below_10_percent": cold_change < 0.10,
            "hot_p95_grid_change_below_10_percent": hot_change < 0.10,
            "hot_temperature_grid_change_below_10_percent": temperature_change < 0.10,
        },
        "engineering_gates": {
            "measured_geometry_and_fit": False,
            "measured_pull_load_stops_and_misuse": False,
            "measured_thermal_and_vibration_environment": False,
            "qualified_hot_material_surface_and_corrosion_allowables": False,
            "pivot_contact_wear_and_fastener_preload_solved": False,
            "modal_harmonic_and_impact_completed": False,
            "part_fatigue_life_completed": False,
            "emergency_egress_and_professional_review": False,
        },
        "interpretation": {
            "mechanical": "The synthetic 150 N pull is solved on the F0 geometry, but actual pivot, stops, contact, misuse and door compliance are absent.",
            "thermal": "The 20-to-80 C imposed field is a numerical screen, not a measured door environment.",
            "fatigue": "The Goodman result is a coupon comparison only and cannot establish door-release life.",
            "physicsnemo": "No training or inference: six uncorrelated cases are not an admissible surrogate dataset.",
            "manufacturing": "Passing numerical gates cannot authorize printing, installation or reliance for vehicle egress.",
        },
        "selected_variant": None,
        "metal_print_authorized": False,
        "vehicle_installation_authorized": False,
        "release_authorized": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"CALCULIX_DOOR_OPENER_F0_PASS executions={2 * len(cases)} selected=none cold_p95_grid_change={cold_change:.6f} hot_p95_grid_change={hot_change:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
