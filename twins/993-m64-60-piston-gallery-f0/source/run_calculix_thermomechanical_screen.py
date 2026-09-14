#!/usr/bin/env python3
"""Criblage CalculiX thermomecanique du piston CP1 M64/60 F0.

Le maitre STEP et les conditions aux limites sont des hypotheses propres au F0.
Le script execute deux calculs reels sur trois tailles de maillage : une statique
froide et une analyse temperature-deplacement sequentielle stationnaire. Il ne
constitue ni une carte materiau CP1 a chaud, ni une validation de piston 993.
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


PART_ID = "993-ENG-PISTON-CP1-GALLERY-F0-0001"
TWIN_ID = "TWIN-993-M64-60-PISTON-GALLERY-F0"

# Cas F0 deja enregistre par le master build123d.
ENGINE_BORE_MM = 100.0
ENGINE_STROKE_MM = 76.4
ENGINE_SPEED_RPM = 6720.0
ROD_LENGTH_MM = 127.0
PISTON_MASS_G = 681.32
PIN_AND_RING_MASS_G = 140.0
PEAK_CYLINDER_PRESSURE_MPA = 12.0
CROWN_HEAT_INPUT_W = 5000.0
GALLERY_SINK_TEMPERATURE_C = 120.0
SKIRT_SINK_TEMPERATURE_C = 160.0
REFERENCE_TEMPERATURE_C = 20.0
DUTY_HOURS = 100.0

# CP1 : seules densite, limite elastique et conductivite sont publiees pour la
# route de comparaison. E, nu et alpha restent des placeholders analytiques.
DENSITY_TONNE_MM3 = 2.67e-9
COMPARISON_YIELD_MPA = 297.0
ELASTIC_MODULUS_MPA = 70_000.0
POISSON_RATIO = 0.33
THERMAL_EXPANSION_PER_K = 23.0e-6
THERMAL_CONDUCTIVITY_W_MM_K = 0.187

# Geometrie analytique F0 utilisee uniquement pour identifier les surfaces du
# meme STEP. Ce ne sont pas des cotes Porsche.
PIN_AXIS_Z_MM = -4.0
PIN_BORE_RADIUS_MM = 11.5
GALLERY_MAJOR_RADIUS_MM = 34.0
GALLERY_MINOR_RADIUS_MM = 3.5
GALLERY_CENTER_Z_MM = 26.0
PISTON_OUTER_RADIUS_MM = 49.5


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


def synthetic_loads() -> dict[str, float]:
    piston_area_mm2 = math.pi * ENGINE_BORE_MM**2 / 4.0
    gas_force_n = PEAK_CYLINDER_PRESSURE_MPA * piston_area_mm2
    crank_radius_m = ENGINE_STROKE_MM / 2000.0
    rod_length_m = ROD_LENGTH_MM / 1000.0
    omega_rad_s = 2.0 * math.pi * ENGINE_SPEED_RPM / 60.0
    tdc_acceleration_m_s2 = (
        crank_radius_m
        * omega_rad_s**2
        * (1.0 + crank_radius_m / rod_length_m)
    )
    reciprocating_mass_kg = (PISTON_MASS_G + PIN_AND_RING_MASS_G) / 1000.0
    inertia_force_n = reciprocating_mass_kg * tdc_acceleration_m_s2
    return {
        "piston_area_mm2": piston_area_mm2,
        "gas_force_n": gas_force_n,
        "tdc_acceleration_m_s2": tdc_acceleration_m_s2,
        "inertia_force_n": inertia_force_n,
        "conservative_axial_force_n": gas_force_n + inertia_force_n,
    }


def boundary_sets(
    points: dict[int, tuple[float, float, float]],
    boundary_node_tags: set[int],
    mesh_size_mm: float,
) -> dict[str, list[int]]:
    # Les noeuds d'ordre 2 restent droits pour eviter les Jacobiennes negatives;
    # leur milieu de corde n'est donc pas exactement projete sur le tore/la jupe.
    # Une tolerance geometrique fixe conserve les memes surfaces entre maillages.
    tolerance = max(0.75, 0.10 * mesh_size_mm)

    crown = sorted(
        tag
        for tag in boundary_node_tags
        if points[tag][2] >= 31.5
        and math.hypot(points[tag][0], points[tag][1]) <= 49.7
    )
    gallery = sorted(
        tag
        for tag in boundary_node_tags
        if abs(
            math.hypot(
                math.hypot(points[tag][0], points[tag][1]) - GALLERY_MAJOR_RADIUS_MM,
                points[tag][2] - GALLERY_CENTER_Z_MM,
            )
            - GALLERY_MINOR_RADIUS_MM
        )
        <= tolerance
    )
    skirt = sorted(
        tag
        for tag in boundary_node_tags
        if points[tag][2] <= 10.0
        and abs(
            math.hypot(points[tag][0], points[tag][1])
            - PISTON_OUTER_RADIUS_MM
        )
        <= tolerance
    )
    pin_bore = sorted(
        tag
        for tag in boundary_node_tags
        if abs(
            math.hypot(points[tag][1], points[tag][2] - PIN_AXIS_Z_MM)
            - PIN_BORE_RADIUS_MM
        )
        <= tolerance
        and abs(points[tag][0]) <= 46.2
    )
    sets = {
        "CROWN_LOAD": crown,
        "GALLERY_SINK": gallery,
        "SKIRT_SINK": skirt,
        "PIN_BORE": pin_bore,
    }
    missing = {name: len(values) for name, values in sets.items() if len(values) < 8}
    if missing:
        raise RuntimeError(f"insufficient_boundary_nodes:{missing}")
    if set(crown) & set(gallery):
        raise RuntimeError("crown_gallery_boundary_overlap")
    return sets


def mesh_step(step: Path, case: Path, mesh_size_mm: float) -> dict[str, object]:
    import gmsh

    case.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("993_m64_60_piston_cp1_f0")
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
        boundary_node_tags: set[int] = set()
        for _, surface_tag in surfaces:
            tags, _, _ = gmsh.model.mesh.getNodes(
                2, surface_tag, includeBoundary=True
            )
            boundary_node_tags.update(int(tag) for tag in tags)

        element_types, element_tags, element_nodes = gmsh.model.mesh.getElements(3)
        elements: list[tuple[int, tuple[int, ...]]] = []
        for element_type, tags, nodes in zip(
            element_types, element_tags, element_nodes
        ):
            if int(element_type) != 11:
                continue
            for index, tag in enumerate(tags):
                offset = 10 * index
                gmsh_nodes = [int(item) for item in nodes[offset : offset + 10]]
                calculix_nodes = tuple(
                    gmsh_nodes[:8] + [gmsh_nodes[9], gmsh_nodes[8]]
                )
                elements.append((int(tag), calculix_nodes))
        gmsh.write(str(case / "piston.msh"))
    finally:
        gmsh.finalize()

    if not elements:
        raise RuntimeError("no_quadratic_tetrahedra")
    sets = boundary_sets(points, boundary_node_tags, mesh_size_mm)
    return {
        "points": points,
        "elements": elements,
        "sets": sets,
        "metrics": {
            "mesh_size_mm": mesh_size_mm,
            "nodes": len(points),
            "quadratic_tetrahedra": len(elements),
            "boundary_nodes": len(boundary_node_tags),
            "boundary_set_counts": {
                name: len(values) for name, values in sets.items()
            },
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
        "*MATERIAL,NAME=CP1_SCREEN\n"
        "*ELASTIC\n"
        f"{ELASTIC_MODULUS_MPA:.10g},{POISSON_RATIO:.10g}\n"
        f"*EXPANSION,ZERO={REFERENCE_TEMPERATURE_C:.10g}\n"
        f"{THERMAL_EXPANSION_PER_K:.10g}\n"
        "*CONDUCTIVITY\n"
        f"{THERMAL_CONDUCTIVITY_W_MM_K:.10g}\n"
        "*DENSITY\n"
        f"{DENSITY_TONNE_MM3:.10g}\n"
        "*SOLID SECTION,ELSET=BODY,MATERIAL=CP1_SCREEN\n"
    )


def write_cold_deck(
    path: Path, mesh: dict[str, object], axial_force_n: float
) -> None:
    crown = mesh["sets"]["CROWN_LOAD"]
    with path.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\n993 piston CP1 F0 cold static screen\n")
        write_common_mesh(stream, mesh)
        stream.write(
            "*STEP\n*STATIC\n"
            "*BOUNDARY\nPIN_BORE,1,3\n"
            "*CLOAD\n"
        )
        nodal_force_n = -axial_force_n / len(crown)
        for tag in crown:
            stream.write(f"{tag},3,{nodal_force_n:.12g}\n")
        stream.write(
            "*EL PRINT,ELSET=BODY\nS\n"
            "*NODE PRINT,NSET=NALL\nU\n"
            "*EL FILE\nS\n"
            "*NODE FILE\nU\n"
            "*END STEP\n"
        )


def write_hot_deck(
    path: Path, mesh: dict[str, object], axial_force_n: float
) -> None:
    crown = mesh["sets"]["CROWN_LOAD"]
    with path.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\n993 piston CP1 F0 sequential hot screen\n")
        write_common_mesh(stream, mesh)
        stream.write(
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\n"
            f"NALL,{REFERENCE_TEMPERATURE_C:.10g}\n"
            "*STEP\n"
            "*UNCOUPLED TEMPERATURE-DISPLACEMENT,STEADY STATE\n"
            "1.,1.\n"
            "*BOUNDARY\n"
            "PIN_BORE,1,3\n"
            f"GALLERY_SINK,11,11,{GALLERY_SINK_TEMPERATURE_C:.10g}\n"
            f"SKIRT_SINK,11,11,{SKIRT_SINK_TEMPERATURE_C:.10g}\n"
            "*CFLUX\n"
        )
        nodal_heat_w = CROWN_HEAT_INPUT_W / len(crown)
        for tag in crown:
            stream.write(f"{tag},11,{nodal_heat_w:.12g}\n")
        stream.write("*CLOAD\n")
        nodal_force_n = -axial_force_n / len(crown)
        for tag in crown:
            stream.write(f"{tag},3,{nodal_force_n:.12g}\n")
        stream.write(
            "*EL PRINT,ELSET=BODY\nS\nHFL\n"
            "*NODE PRINT,NSET=NALL\nU\nNT\n"
            "*EL FILE\nS,HFL\n"
            "*NODE FILE\nU,NT\n"
            "*END STEP\n"
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


def relative_change(current: float, previous: float) -> float:
    if current == 0.0:
        return math.inf
    return abs(current - previous) / abs(current)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mesh-sizes", default="5.0,3.5,2.5")
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
    loads = synthetic_loads()
    cases: list[dict[str, object]] = []
    for mesh_size_mm in mesh_sizes:
        case = args.work_root / f"mesh-{str(mesh_size_mm).replace('.', 'p')}"
        mesh = mesh_step(args.step, case, mesh_size_mm)
        cold_job = "piston-cold"
        hot_job = "piston-hot"
        write_cold_deck(
            case / f"{cold_job}.inp",
            mesh,
            loads["conservative_axial_force_n"],
        )
        write_hot_deck(
            case / f"{hot_job}.inp",
            mesh,
            loads["conservative_axial_force_n"],
        )
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
    cycles = ENGINE_SPEED_RPM / 60.0 * DUTY_HOURS * 3600.0
    finest_hot_p95 = finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"]
    report = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "status": "f0_real_calculix_six_case_screen_complete_no_design_selected",
        "inputs": {
            "runner_repository_path": "twins/993-m64-60-piston-gallery-f0/source/run_calculix_thermomechanical_screen.py",
            "runner_sha256": sha256(Path(__file__).resolve()),
            "step_repository_path": "parts/993-eng-piston-cp1-gallery-f0-0001/derived/piston_cp1_gallery_f0.step",
            "step_sha256": sha256(args.step),
            "geometry_authority": "Independent synthetic F0 BREP; no Porsche or MAHLE piston surface.",
            "synthetic_loads": loads,
            "peak_cylinder_pressure_mpa": PEAK_CYLINDER_PRESSURE_MPA,
            "crown_heat_input_w": CROWN_HEAT_INPUT_W,
            "gallery_sink_temperature_c": GALLERY_SINK_TEMPERATURE_C,
            "skirt_sink_temperature_c": SKIRT_SINK_TEMPERATURE_C,
            "boundary_authority": "Regression envelope only; no measured pressure trace, heat flux, oil temperature, gallery film coefficient, contact or restraint.",
        },
        "material": {
            "candidate": "Aheadd CP1 LPBF screening card",
            "density_tonne_mm3": DENSITY_TONNE_MM3,
            "comparison_minimum_yield_mpa": COMPARISON_YIELD_MPA,
            "thermal_conductivity_w_mm_k": THERMAL_CONDUCTIVITY_W_MM_K,
            "provisional_elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "provisional_poisson_ratio": POISSON_RATIO,
            "provisional_thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "hot_card_qualified": False,
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
            "gas_force": "F_gas=p_peak*pi*bore^2/4",
            "tdc_acceleration": "a=r*omega^2*(1+r/L)",
            "inertia_force": "F_i=(m_piston+m_pin_rings)*a",
            "thermal_conduction": "div(k*grad(T))+q=0",
            "thermal_strain": "epsilon_th=alpha*(T-T_ref)",
            "linear_elasticity": "div(sigma)+b=0; sigma=C:(epsilon-epsilon_th)",
            "load_application": "exact total axial force and total crown power distributed equally over selected exterior crown nodes",
            "restraint": "all displacement degrees fixed on the synthetic pin-bore surface; conservative overconstraint for thermal stress",
        },
        "cases": cases,
        "grid_comparison_fine_vs_previous": {
            "cold_p95_stress_relative_change": cold_p95_change,
            "hot_p95_stress_relative_change": hot_p95_change,
            "hot_maximum_temperature_relative_change": hot_temperature_change,
            "screening_threshold": 0.10,
            "threshold_authority": "project numerical-screen threshold only; not a piston acceptance limit",
        },
        "fatigue_proxy": {
            "shaft_revolutions_at_100h": cycles,
            "combustion_events_per_cylinder_at_100h": cycles / 2.0,
            "zero_to_peak_p95_stress_amplitude_proxy_mpa": finest_hot_p95 / 2.0,
            "zero_to_peak_p95_mean_stress_proxy_mpa": finest_hot_p95 / 2.0,
            "cp1_hot_sn_curve_available": False,
            "predicted_life_cycles": None,
            "reason": "No route-specific CP1 hot fatigue, defect, creep or mean-stress card; cycle counting is not a life prediction.",
        },
        "ambient_reference_strength_ratios": {
            "cold_p95_yield_to_stress": COMPARISON_YIELD_MPA
            / finest["cold_linear_static"]["von_mises_mpa"]["p95"],
            "cold_maximum_yield_to_stress": COMPARISON_YIELD_MPA
            / finest["cold_linear_static"]["von_mises_mpa"]["maximum"],
            "hot_p95_yield_to_stress": COMPARISON_YIELD_MPA
            / finest_hot_p95,
            "hot_maximum_yield_to_stress": COMPARISON_YIELD_MPA
            / finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["maximum"],
            "authority": "Ratios against the published ambient minimum only; none is a hot design margin.",
        },
        "numerical_gates": {
            "six_solver_executions_complete": len(cases) >= 3,
            "cold_p95_grid_change_below_10_percent": cold_p95_change < 0.10,
            "hot_p95_grid_change_below_10_percent": hot_p95_change < 0.10,
            "hot_temperature_grid_change_below_10_percent": hot_temperature_change < 0.10,
        },
        "engineering_gates": {
            "measured_piston_geometry": False,
            "measured_transient_loads": False,
            "qualified_cp1_hot_material_card": False,
            "realistic_pin_ring_skirt_contact": False,
            "oil_gallery_cht_or_vof": False,
            "thermomechanical_fatigue_life": False,
            "pico_gk_variants_manifold_and_solved": False,
            "professional_engineering_review": False,
        },
        "interpretation": {
            "thermal": "The 5 kW nodal crown input and ideal 120/160 C sinks are a comparative bound, not combustion CHT or an oil-jet model.",
            "mechanical": "The exact total synthetic axial force is applied, but pressure normal direction, pin contact, rings and skirt contact are not resolved.",
            "hot_strength": "Ambient published CP1 yield is retained only as a comparison reference and cannot validate hot stress.",
            "pico_gk": "Non-manifold raw variants are excluded from this solve; the sound baseline STEP is the only solver geometry.",
            "physicsnemo": "No training or inference: this six-case uncorrelated screen is not an admissible surrogate dataset.",
        },
        "selected_variant": None,
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "CALCULIX_PISTON_F0_PASS "
        f"executions={2 * len(cases)} selected=none "
        f"cold_p95_grid_change={cold_p95_change:.6f} "
        f"hot_p95_grid_change={hot_p95_change:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
