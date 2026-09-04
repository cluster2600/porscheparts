#!/usr/bin/env python3
"""Construit et contrôle les enveloppes BOM partielles de distribution F36.

Les composants sont des volumes paramétriques de packaging et non des copies
des références commerciales 964. Le rapport distingue les équations résolues,
les hypothèses et les portes physiques qui restent fermées.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh

from build_scan_conforming_4v_f36 import add_mesh, cylinder_between, decimated, set_view, valve_axis


DENSITY_KG_M3 = {
    "head": 2670.0,
    "Ti-6Al-4V": 4430.0,
    "INCONEL_alloy_751": 8240.0,
    "steel": 7850.0,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def transform_for_segment(start: np.ndarray, end: np.ndarray) -> np.ndarray:
    direction = np.asarray(end, dtype=float) - np.asarray(start, dtype=float)
    length = float(np.linalg.norm(direction))
    if length <= 0.0:
        raise ValueError("segment nul")
    transform = trimesh.geometry.align_vectors([0.0, 0.0, 1.0], direction / length)
    transform[:3, 3] = 0.5 * (np.asarray(start, dtype=float) + np.asarray(end, dtype=float))
    return transform


def annulus_between(start: np.ndarray, end: np.ndarray, r_min: float, r_max: float, sections: int = 48) -> trimesh.Trimesh:
    length = float(np.linalg.norm(np.asarray(end) - np.asarray(start)))
    return trimesh.creation.annulus(
        r_min=float(r_min),
        r_max=float(r_max),
        height=length,
        sections=sections,
        transform=transform_for_segment(start, end),
    )


def disc_between(start: np.ndarray, end: np.ndarray, radius: float, sections: int = 48) -> trimesh.Trimesh:
    return cylinder_between(start, end, radius, sections)


def spring_mesh(
    start: np.ndarray,
    direction: np.ndarray,
    basis_x: np.ndarray,
    basis_y: np.ndarray,
    height: float,
    mean_radius: float,
    wire_radius: float,
    turns: float,
) -> trimesh.Trimesh:
    sample_count = max(56, int(turns * 18))
    parameter = np.linspace(0.0, 1.0, sample_count)
    phase = 2.0 * math.pi * turns * parameter
    points = (
        start[None, :]
        + direction[None, :] * (height * parameter[:, None])
        + mean_radius * np.cos(phase)[:, None] * basis_x[None, :]
        + mean_radius * np.sin(phase)[:, None] * basis_y[None, :]
    )
    segments = [
        cylinder_between(points[index], points[index + 1], wire_radius, 10)
        for index in range(len(points) - 1)
    ]
    return trimesh.util.concatenate(segments)


def colour(mesh: trimesh.Trimesh, rgba: tuple[int, int, int, int]) -> trimesh.Trimesh:
    mesh.visual.face_colors = np.tile(np.asarray(rgba, dtype=np.uint8), (len(mesh.faces), 1))
    return mesh


def spring_rate_n_per_mm(wire_mm: float, mean_diameter_mm: float, active_coils: float, shear_modulus_gpa: float = 79.0) -> float:
    return shear_modulus_gpa * 1000.0 * wire_mm**4 / (8.0 * mean_diameter_mm**3 * active_coils)


def wahl_factor(mean_diameter_mm: float, wire_mm: float) -> float:
    index = mean_diameter_mm / wire_mm
    return (4.0 * index - 1.0) / (4.0 * index - 4.0) + 0.615 / index


def spring_shear_mpa(force_n: float, wire_mm: float, mean_diameter_mm: float) -> float:
    return wahl_factor(mean_diameter_mm, wire_mm) * 8.0 * force_n * mean_diameter_mm / (math.pi * wire_mm**3)


def hot_diameter(cold_mm: float, alpha_per_k: float, temperature_c: float, reference_c: float = 20.0) -> float:
    return cold_mm * (1.0 + alpha_per_k * (temperature_c - reference_c))


def guide_contact_pressure_mpa(diametral_interference_mm: float, diameter_mm: float, head_e_gpa: float = 66.0, guide_e_gpa: float = 200.0) -> float:
    radial_strain = 0.5 * diametral_interference_mm / diameter_mm
    compliance = 1.0 / (head_e_gpa * 1000.0) + 1.0 / (guide_e_gpa * 1000.0)
    return radial_strain / compliance


def valve_mass_kg(head_diameter_mm: float, stem_diameter_mm: float, density_kg_m3: float) -> float:
    volume_mm3 = math.pi * (head_diameter_mm / 2.0) ** 2 * 2.5 + math.pi * (stem_diameter_mm / 2.0) ** 2 * 96.0
    return volume_mm3 * density_kg_m3 * 1.0e-9


def basis_for_axis(direction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    basis_x = np.asarray([1.0, 0.0, 0.0])
    basis_y = np.cross(direction, basis_x)
    basis_y /= np.linalg.norm(basis_y)
    return basis_x, basis_y


def add_part(scene: trimesh.Scene, meshes: list[trimesh.Trimesh], mesh: trimesh.Trimesh, name: str, rgba: tuple[int, int, int, int]) -> None:
    mesh = colour(mesh, rgba)
    meshes.append(mesh)
    scene.add_geometry(mesh, node_name=name, geom_name=name)


def build_components(report: dict, contract: dict) -> tuple[trimesh.Scene, list[trimesh.Trimesh], dict]:
    architecture = report["geometry"]["architecture"]
    scene = trimesh.Scene()
    meshes: list[trimesh.Trimesh] = []
    component_counts: dict[str, int] = {}

    for family, valve_colour in (("intake", (74, 171, 214, 255)), ("exhaust", (224, 105, 66, 255))):
        data = architecture[family]
        guide_inner = float(data.get("guide_inner_diameter_mm", 7.04 if family == "intake" else 7.08))
        guide_outer = float(data.get("guide_outer_diameter_mm", 15.0))
        seat_outer = float(data.get("seat_outer_diameter_mm", data["head_diameter_mm"] + 3.2))
        for index, centre in enumerate(data["centres_mm"], start=1):
            start, end = valve_axis(centre, data["tilt_y_deg"], 96.0)
            direction = end - start
            direction /= np.linalg.norm(direction)
            basis_x, basis_y = basis_for_axis(direction)
            suffix = f"{family}-{index}"

            valve = trimesh.util.concatenate(
                [
                    disc_between(start - 1.25 * direction, start + 1.25 * direction, data["head_diameter_mm"] / 2.0, 64),
                    cylinder_between(start, end, data["stem_diameter_mm"] / 2.0, 32),
                ]
            )
            add_part(scene, meshes, valve, f"valve-{suffix}", valve_colour)

            guide = annulus_between(
                start + 4.0 * direction,
                start + 60.0 * direction,
                guide_inner / 2.0,
                guide_outer / 2.0,
            )
            add_part(scene, meshes, guide, f"guide-{suffix}", (151, 159, 166, 255))

            seat = annulus_between(
                start - 0.5 * direction,
                start + 6.5 * direction,
                0.5 * (data["head_diameter_mm"] - 3.0),
                0.5 * seat_outer,
                64,
            )
            add_part(scene, meshes, seat, f"seat-{suffix}", (204, 153, 64, 255))

            seal = annulus_between(start + 59.0 * direction, start + 69.0 * direction, 3.55, 6.0, 40)
            add_part(scene, meshes, seal, f"stem-seal-{suffix}", (71, 92, 78, 255))

            lower = annulus_between(start + 41.0 * direction, start + 42.5 * direction, 4.0, 15.5, 48)
            add_part(scene, meshes, lower, f"lower-seat-{suffix}", (122, 128, 134, 255))

            outer = spring_mesh(start + 43.0 * direction, direction, basis_x, basis_y, 45.0, 12.5, 2.25, 5.5)
            inner = spring_mesh(start + 43.0 * direction, direction, basis_x, basis_y, 45.0, 8.5, 1.5, 6.5)
            add_part(scene, meshes, trimesh.util.concatenate((outer, inner)), f"dual-spring-{suffix}", (111, 127, 137, 255))

            upper = annulus_between(start + 88.0 * direction, start + 94.0 * direction, 3.7, 14.0, 48)
            add_part(scene, meshes, upper, f"upper-retainer-{suffix}", (170, 176, 181, 255))
            keeper = annulus_between(start + 91.0 * direction, start + 96.0 * direction, 3.5, 5.2, 32)
            add_part(scene, meshes, keeper, f"keeper-pair-{suffix}", (192, 197, 201, 255))
            shim = disc_between(start + 96.0 * direction, start + 98.5 * direction, 6.0, 40)
            add_part(scene, meshes, shim, f"shim-{suffix}", (201, 205, 208, 255))

    for index, (x, y) in enumerate(report["geometry"]["packaging_checks"]["stud_centres_local_mm"], start=1):
        stud = cylinder_between(np.asarray([x, y, -8.0]), np.asarray([x, y, 107.0]), 5.0, 32)
        nut = disc_between(np.asarray([x, y, 98.0]), np.asarray([x, y, 107.0]), 9.0, 6)
        add_part(scene, meshes, stud, f"head-stud-{index}", (117, 121, 125, 255))
        add_part(scene, meshes, nut, f"head-nut-{index}", (153, 157, 160, 255))

    for index, x in enumerate((-51.0, 51.0), start=1):
        dowel = cylinder_between(np.asarray([x, 0.0, -8.0]), np.asarray([x, 0.0, 4.0]), 4.0, 32)
        add_part(scene, meshes, dowel, f"location-dowel-{index}", (181, 185, 188, 255))

    sensor = cylinder_between(np.asarray([0.0, 101.0, 50.0]), np.asarray([0.0, 122.0, 50.0]), 4.0, 32)
    add_part(scene, meshes, sensor, "temperature-sensor", (214, 180, 67, 255))

    for item in contract["bom"]:
        component_counts[item["id"]] = int(item["quantity"])
    return scene, meshes, component_counts


def analyse(report: dict, contract: dict, head: trimesh.Trimesh) -> dict:
    assumptions = contract["operating_assumptions"]
    architecture = report["geometry"]["architecture"]
    head_density = DENSITY_KG_M3["head"]
    head_mass = float(head.volume) * head_density * 1.0e-9

    outer = next(item for item in contract["bom"] if item["id"] == "dual_valve_spring")["nominal"]
    k_outer = spring_rate_n_per_mm(outer["outer_wire_mm"], outer["outer_mean_diameter_mm"], outer["outer_active_coils"])
    k_inner = spring_rate_n_per_mm(outer["inner_wire_mm"], outer["inner_mean_diameter_mm"], outer["inner_active_coils"])
    k_total = k_outer + k_inner
    lift = float(assumptions["nominal_valve_lift_mm"])
    seat_force = float(outer["seat_load_n"])
    open_force = seat_force + k_total * lift
    outer_open_force = open_force * k_outer / k_total
    inner_open_force = open_force * k_inner / k_total
    outer_bind_margin = outer["installed_height_mm"] - lift - (outer["outer_active_coils"] + 1.5) * outer["outer_wire_mm"]
    inner_bind_margin = outer["installed_height_mm"] - lift - (outer["inner_active_coils"] + 1.5) * outer["inner_wire_mm"]

    cam_speed_rad_s = math.pi * assumptions["maximum_engine_speed_rpm"] / 60.0
    event_rad = math.radians(assumptions["cam_event_duration_cam_deg"])
    maximum_acceleration = 0.5 * lift / 1000.0 * (2.0 * math.pi / event_rad) ** 2 * cam_speed_rad_s**2

    family_results = {}
    for family, density, additional_mass in (
        ("intake", DENSITY_KG_M3["Ti-6Al-4V"], 0.040),
        ("exhaust", DENSITY_KG_M3["INCONEL_alloy_751"], 0.044),
    ):
        data = architecture[family]
        valve_mass = valve_mass_kg(data["head_diameter_mm"], data["stem_diameter_mm"], density)
        moving_mass = valve_mass + additional_mass
        inertia_force = moving_mass * maximum_acceleration
        mid_lift_force = seat_force + 0.5 * k_total * lift
        peak_combustion_force = assumptions["turbo_peak_cylinder_pressure_mpa"] * math.pi * (data["head_diameter_mm"] / 2.0) ** 2
        mean_seat_pressure = peak_combustion_force / (math.pi * (data["head_diameter_mm"] - 1.5) * 1.5)
        family_results[family] = {
            "valve_mass_kg": valve_mass,
            "screen_moving_mass_kg": moving_mass,
            "maximum_harmonic_acceleration_m_s2": maximum_acceleration,
            "maximum_inertial_force_n": inertia_force,
            "mid_lift_spring_force_n": mid_lift_force,
            "dynamic_force_margin_ratio": mid_lift_force / inertia_force,
            "peak_combustion_force_n": peak_combustion_force,
            "mean_seat_contact_pressure_mpa": mean_seat_pressure,
        }

    alpha_head = 23.0e-6
    alpha_guide = 11.5e-6
    guide_temperature = assumptions["guide_reference_temperature_c"]
    guide_cold_interference = 15.0 - 14.94
    guide_hot_interference = hot_diameter(15.0, alpha_guide, guide_temperature) - hot_diameter(14.94, alpha_head, guide_temperature)
    intake_clearance_hot = hot_diameter(7.04, alpha_guide, guide_temperature) - hot_diameter(7.0, 8.6e-6, 250.0)
    exhaust_clearance_hot = hot_diameter(7.08, alpha_guide, guide_temperature) - hot_diameter(7.0, 13.3e-6, assumptions["exhaust_stem_reference_temperature_c"])

    seat_results = {}
    for family, alpha_seat in (("intake", 11.5e-6), ("exhaust", 12.5e-6)):
        data = architecture[family]
        seat_outer = float(data.get("seat_outer_diameter_mm", data["head_diameter_mm"] + 3.2))
        seat_bore = float(data.get("seat_bore_diameter_mm", seat_outer - (0.12 if family == "intake" else 0.10)))
        hot_interference = hot_diameter(seat_outer, alpha_seat, 260.0) - hot_diameter(seat_bore, alpha_head, 260.0)
        seat_results[family] = {
            "cold_diametral_interference_mm": seat_outer - seat_bore,
            "hot_diametral_interference_mm": hot_interference,
        }

    spring = {
        "outer_rate_n_per_mm": k_outer,
        "inner_rate_n_per_mm": k_inner,
        "combined_rate_n_per_mm": k_total,
        "seat_load_n": seat_force,
        "open_load_n": open_force,
        "outer_coil_bind_margin_mm": outer_bind_margin,
        "inner_coil_bind_margin_mm": inner_bind_margin,
        "outer_open_wahl_shear_mpa": spring_shear_mpa(outer_open_force, outer["outer_wire_mm"], outer["outer_mean_diameter_mm"]),
        "inner_open_wahl_shear_mpa": spring_shear_mpa(inner_open_force, outer["inner_wire_mm"], outer["inner_mean_diameter_mm"]),
        "spintron_correlation": False,
    }
    guide = {
        "cold_diametral_interference_mm": guide_cold_interference,
        "hot_diametral_interference_mm": guide_hot_interference,
        "cold_contact_pressure_screen_mpa": guide_contact_pressure_mpa(guide_cold_interference, 15.0),
        "hot_contact_pressure_screen_mpa": guide_contact_pressure_mpa(guide_hot_interference, 15.0),
        "intake_hot_diametral_stem_clearance_mm": intake_clearance_hot,
        "exhaust_hot_diametral_stem_clearance_mm": exhaust_clearance_hot,
    }
    gates = {
        "bare_head_mass_at_or_below_2_83_kg": head_mass <= 2.83,
        "guide_hot_interference_positive": guide_hot_interference >= 0.02,
        "intake_hot_stem_clearance_0_02_to_0_08_mm": 0.02 <= intake_clearance_hot <= 0.08,
        "exhaust_hot_stem_clearance_0_04_to_0_12_mm": 0.04 <= exhaust_clearance_hot <= 0.12,
        "seat_hot_interference_positive": all(item["hot_diametral_interference_mm"] >= 0.015 for item in seat_results.values()),
        "spring_coil_bind_margin_at_least_1_5_mm": min(outer_bind_margin, inner_bind_margin) >= 1.5,
        "dynamic_force_margin_at_least_1_2": min(item["dynamic_force_margin_ratio"] for item in family_results.values()) >= 1.2,
        "spring_shear_screen_below_1000_mpa": max(spring["outer_open_wahl_shear_mpa"], spring["inner_open_wahl_shear_mpa"]) <= 1000.0,
        "supplier_dimensions_measured": False,
        "spintron_correlated": False,
        "metal_print_authorized": False,
        "engine_start_authorized": False,
    }
    return {
        "schema_version": "1.0.0",
        "phase": "F36",
        "status": "valvetrain_parametric_screen_complete_release_blocked",
        "classification": "conditional_math_screen_using_unmeasured_component_hypotheses",
        "head": {
            "volume_mm3_if_scale_is_mm": float(head.volume),
            "candidate_density_kg_m3": head_density,
            "bare_mass_kg_if_scale_is_mm": head_mass,
            "benchmark_mass_kg": 2.83,
        },
        "guide_fit": guide,
        "seat_fit": seat_results,
        "spring": spring,
        "valves": family_results,
        "equations": {
            "spring_rate": "k=G*d^4/(8*D^3*N_active)",
            "harmonic_cam_acceleration": "a_max=h/2*(2*pi/beta_cam)^2*omega_cam^2",
            "combustion_force": "F=p*pi*d_valve^2/4",
            "thermal_diameter": "D_hot=D_20*(1+alpha*(T-20C))",
            "press_fit_screen": "p=(delta_d/(2*D))/(1/E_head+1/E_insert)",
        },
        "gates": gates,
    }


def render(head: trimesh.Trimesh, parts: list[trimesh.Trimesh], analysis: dict, output: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="f36-valvetrain-render-") as temporary_name:
        head_preview = decimated(head, 65000, Path(temporary_name), "head-preview")
    cutaway_faces = np.where(head_preview.triangles_center[:, 0] <= 1.0)[0]
    head_cutaway = head_preview.submesh([cutaway_faces], append=True, repair=False)
    figure = plt.figure(figsize=(15, 9), facecolor="#0b1118")
    figure.suptitle("F36 — culasse 4V et enveloppes BOM partielles", color="white", fontsize=21, fontweight="bold", y=0.97)
    figure.text(0.5, 0.93, "SOUPAPES · GUIDES · SIEGES · JOINTS · DOUBLE RESSORT · COUPELLES · DEMI-LUNES · GOUJONS · SONDE", ha="center", color="#f0bd58", fontsize=10, fontweight="bold")
    for panel, (elev, azim, title) in enumerate(((20.0, -52.0, "Assemblage externe"), (8.0, 4.0, "Coupe latérale / axes 4V")), start=1):
        axis = figure.add_subplot(1, 2, panel, projection="3d", facecolor="#101b24")
        displayed_head = head_cutaway if panel == 2 else head_preview
        add_mesh(axis, displayed_head, "#a77c3e", 0.24 if panel == 2 else 0.90, 70000)
        for part in parts:
            rgba = np.asarray(part.visual.face_colors[0], dtype=float) / 255.0
            add_mesh(axis, part, rgba[:3], 0.98, 30000)
        set_view(axis, np.vstack((head.bounds[0] - [0, 0, 8], head.bounds[1] + [0, 0, 25])), elev, azim, title)
    mass = analysis["head"]["bare_mass_kg_if_scale_is_mm"]
    dynamic = min(item["dynamic_force_margin_ratio"] for item in analysis["valves"].values())
    figure.text(0.5, 0.035, f"masse nue calculée {mass:.3f} kg (cible 2,83: {'PASS' if mass <= 2.83 else 'FAIL'}) · marge dynamique ressort {dynamic:.2f} · échelle et composants fournisseur non mesurés", color="#d6dde3", ha="center", fontsize=10)
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.08, top=0.90, wspace=0.01)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    head = trimesh.load_mesh(args.head, process=True)
    if not isinstance(head, trimesh.Trimesh) or not head.is_watertight:
        raise SystemExit("la culasse F36 doit être un solide étanche")
    geometry_report = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    scene, parts, component_counts = build_components(geometry_report, contract)
    scene.add_geometry(colour(head.copy(), (161, 119, 57, 110)), node_name="f36-head", geom_name="f36-head")
    analysis = analyse(geometry_report, contract, head)
    analysis["declared_component_counts"] = component_counts
    analysis["component_counts_source"] = "copied_from_contract_bom_not_counted_from_scene"
    analysis["assembly_scope"] = {
        "head_component_interference_executed": False,
        "rocker_carrier_rockers_and_camshafts_present": False,
        "stud_preload_and_contact_executed": False,
        "thermal_contact_paths_executed": False,
        "classification": "partial_parametric_envelopes_not_integrated_F37_assembly",
    }
    analysis["inputs"] = {
        "head_sha256": sha256(args.head),
        "geometry_report_sha256": sha256(args.geometry_report),
        "assembly_contract_sha256": sha256(args.contract),
    }

    assembly_path = args.output / "917-head-f36-complete-valvetrain.local.glb"
    image_path = args.output / "917-head-f36-complete-valvetrain.png"
    report_path = args.output / "valvetrain-analysis.json"
    scene.export(assembly_path)
    render(head, parts, analysis, image_path)
    analysis["local_files"] = {
        assembly_path.name: {"sha256": sha256(assembly_path), "bytes": assembly_path.stat().st_size},
        image_path.name: {"sha256": sha256(image_path), "bytes": image_path.stat().st_size},
    }
    save_json(report_path, analysis)
    print(json.dumps({"status": analysis["status"], "report": str(report_path), "image": str(image_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
