#!/usr/bin/env python3
"""Build a 4V oil-gallery study and two original review prototypes.

The inherited source CAD is a private input. No OEM fit or physical validation
is implied by passing CAD/mesh checks. All outputs go to a new directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import build123d as b
import numpy as np
import trimesh


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def teardrop(r: float, start: tuple[float, float, float], lateral: tuple[float, float, float]):
    """270 degree circular underside plus two tangent 45 degree roof planes."""
    s, u, v = b.Vector(start), b.Vector(lateral), b.Vector(0, 0, 1)
    left = s - u * (r / math.sqrt(2)) + v * (r / math.sqrt(2))
    right = s + u * (r / math.sqrt(2)) + v * (r / math.sqrt(2))
    bottom, apex = s - v * r, s + v * (r * math.sqrt(2))
    arc = b.Edge.make_three_point_arc(left, bottom, right)
    return b.Face(b.Wire([arc, b.Edge.make_line(right, apex), b.Edge.make_line(apex, left)]))


def gallery_y(p: dict):
    r, a, z, y0, yt = (p[k] for k in ["gallery_radius", "gallery_half_spacing", "gallery_z", "gallery_start_y", "gallery_turn_y"])
    if not (r > 0 and a > 2 * r and yt > y0):
        raise ValueError("invalid head gallery parameters")
    path = b.Wire([
        b.Edge.make_line((-a, y0, z), (-a, yt, z)),
        b.Edge.make_three_point_arc((-a, yt, z), (0, yt + a, z), (a, yt, z)),
        b.Edge.make_line((a, yt, z), (a, y0, z)),
    ])
    return b.sweep(teardrop(r, (-a, y0, z), (1, 0, 0)), path=path, is_frenet=False), 2 * (yt - y0) + math.pi * a


def gallery_x(p: dict):
    r, a, z, xt = (p[k] for k in ["gallery_radius", "gallery_half_spacing", "gallery_z", "gallery_turn_x"])
    x0 = -p["length"] / 2
    if not (r > 0 and a > 2 * r and xt > x0):
        raise ValueError("invalid coupon gallery parameters")
    path = b.Wire([
        b.Edge.make_line((x0, a, z), (xt, a, z)),
        b.Edge.make_three_point_arc((xt, a, z), (xt + a, 0, z), (xt, -a, z)),
        b.Edge.make_line((xt, -a, z), (x0, -a, z)),
    ])
    return b.sweep(teardrop(r, (x0, a, z), (0, 1, 0)), path=path, is_frenet=False), 2 * (xt - x0) + math.pi * a


def profile_metrics(r: float):
    area = (3 * math.pi / 4 + 1) * r * r
    perimeter = (3 * math.pi / 2 + 2) * r
    return {"radius": r, "area_mm2": area, "perimeter_mm": perimeter, "hydraulic_diameter_mm": 4 * area / perimeter, "roof_slope_degrees": 45, "section_height_mm": r * (1 + math.sqrt(2))}


def mesh_report(path: Path):
    mesh = trimesh.load_mesh(path, process=False)
    # STL repeats vertices; exact float-value welding is an audit representation,
    # not a tolerance-based repair or a change to the delivered STL.
    vertices, inverse = np.unique(mesh.vertices, axis=0, return_inverse=True)
    faces = inverse[mesh.faces]
    q = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, incidence = np.unique(edges, axis=0, return_counts=True)
    return {
        "triangles": len(faces), "watertight": bool(q.is_watertight),
        "winding_consistent": bool(q.is_winding_consistent),
        "boundary_edges": int(np.count_nonzero(incidence == 1)),
        "nonmanifold_edges": int(np.count_nonzero(incidence > 2)),
        "zero_area_triangles": int(np.count_nonzero(q.area_faces == 0)),
        "signed_volume_mm3": float(q.volume),
        "self_intersections_tested": False,
        "welding": "identical_STL_float_values_only_no_tolerance_repair",
    }


def export_checked(shape, out: Path, name: str, mesh: bool = True):
    step, stl = out / f"{name}.step", out / f"{name}-concept-only.stl"
    if not shape.is_valid or not shape.solids():
        raise ValueError(f"invalid_shape:{name}")
    b.export_step(shape, step)
    reread = b.import_step(step)
    delta = abs(reread.volume - shape.volume) / max(abs(shape.volume), 1)
    report = {
        "BRep_valid_before_export": bool(shape.is_valid), "BRep_valid_after_STEP": bool(reread.is_valid),
        "solids_before": len(shape.solids()), "solids_after": len(reread.solids()),
        "volume_mm3_under_declared_hypothesis": float(shape.volume),
        "STEP_relative_volume_delta": delta, "STEP_sha256": sha256(step),
        "full_BOP_executed": False, "manufacturing_authorized": False,
    }
    if not reread.is_valid or len(reread.solids()) != len(shape.solids()) or delta > 1e-7:
        raise ValueError(f"STEP_readback_failed:{name}")
    if mesh:
        b.export_stl(shape, stl, tolerance=0.12, angular_tolerance=0.18)
        report["STL"] = mesh_report(stl)
        report["STL_sha256"] = sha256(stl)
        if not report["STL"]["watertight"] or not report["STL"]["winding_consistent"] or report["STL"]["zero_area_triangles"]:
            # Keep the rejected export and evidence, never silently repair it.
            report["mesh_accepted_for_review"] = False
        else:
            report["mesh_accepted_for_review"] = True
    return report


def hydraulic_screen(p: dict, length_mm: float, r: float):
    profile = profile_metrics(r)
    rho = p["density_kg_m3_hypothesis"]
    cp = p["specific_heat_J_kgK_hypothesis"]
    area, dh, length = profile["area_mm2"] * 1e-6, profile["hydraulic_diameter_mm"] * 1e-3, length_mm * 1e-3
    rows = []
    for mu in p["dynamic_viscosity_Pa_s_hypotheses"]:
        for flow in p["flow_per_head_L_min_hypotheses"]:
            q = flow * 1e-3 / 60
            v = q / area
            re = rho * v * dh / mu
            if re >= 2300:
                raise ValueError("laminar_screen_out_of_regime")
            friction = 64 / re * length / dh * rho * v * v / 2
            minor = p["total_minor_loss_K_hypothesis"] * rho * v * v / 2
            rows.append({"flow_L_min": flow, "viscosity_Pa_s": mu, "velocity_m_s": v, "Re": re,
                         "friction_pressure_drop_bar": friction / 1e5, "minor_pressure_drop_bar": minor / 1e5,
                         "total_pressure_drop_bar": (friction + minor) / 1e5,
                         "enthalpy_transport_capacity_W_at_assumed_delta_T": rho * q * cp * p["oil_temperature_rise_K_hypothesis"]})
    return {"status": "sensitivity_calculation_not_CFD_or_heat_transfer_validation", "profile": profile,
            "conservative_tool_path_length_mm": length_mm, "hypotheses": p, "cases": rows,
            "missing": ["actual_oil_grade_and_temperature_viscosity_curve", "pump_and_complete_return_circuit", "noncircular_friction_factor", "fittings_and_branch_losses", "air_and_combustion_heat_loads", "oil_metal_heat_transfer_and_hotspots"],
            "heat_removed_from_head_W": None, "thermal_margin": None}


def coupon_build(p: dict):
    fluid, length = gallery_x(p)
    r, a, z = p["gallery_radius"], p["gallery_half_spacing"], p["gallery_z"]
    clearances = {
        "right_wall": p["length"] / 2 - (p["gallery_turn_x"] + a + r),
        "side_wall": p["width"] / 2 - (a + r),
        "bottom_wall": z - r,
        "roof_wall": p["height"] - (z + math.sqrt(2) * r),
    }
    if min(clearances.values()) < p["minimum_nominal_ligament_screen"]:
        raise ValueError("coupon_nominal_ligament_below_screen")
    blank = b.Box(p["length"], p["width"], p["height"], align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN))
    body = blank.cut(fluid)
    return body, fluid, length, clearances


def stand_build(p: dict):
    diameter = p["stem_reference_diameter"] + p["diametral_design_clearance"]
    if diameter <= p["stem_reference_diameter"] or p["boss_radius"] <= diameter / 2 + 2:
        raise ValueError("stand_clearance_invalid")
    base = b.Box(p["length"], p["width"], p["base_height"], align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN))
    boss = b.Cylinder(p["boss_radius"], p["boss_height"], align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN))
    bore = b.Pos(0, 0, -1) * b.Cylinder(diameter / 2, p["boss_height"] + 2, align=(b.Align.CENTER, b.Align.CENTER, b.Align.MIN))
    return (base + boss).cut(bore)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--parameters", type=Path, default=Path(__file__).with_name("parameters.json"))
    parser.add_argument("--original-only", action="store_true", help="omit all private scan-derived head geometry")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("output_directory_must_be_new")
    args.output.mkdir(parents=True)
    cad = args.output / "cad"
    cad.mkdir()
    p = json.loads(args.parameters.read_text())
    started = time.perf_counter()
    report = {"schema_version": "1.0.0", "status": "geometric_concept_not_engine_ready", "units": p["length_unit"],
              "source_code_sha256": sha256(Path(__file__)), "parameters_sha256": sha256(args.parameters), "release": p["release"],
              "checks": {}, "hypotheses": p, "geometry": {}, "source_inputs_unchanged": True}
    try:
        coupon, coupon_fluid, length, clearances = coupon_build(p["coupon"])
        for name, shape in [("oil-gallery-coupon", coupon), ("coupon-fluid-domain", coupon_fluid), ("turbo-valve-inspection-stand", stand_build(p["valve_stand"]))]:
            print(f"Exporting {name}", flush=True)
            report["geometry"][name] = export_checked(shape, cad, name)
        expected = profile_metrics(p["coupon"]["gallery_radius"])["area_mm2"] * length
        report["checks"]["coupon_connected_fluid"] = len(coupon_fluid.solids()) == 1
        report["checks"]["coupon_analytic_sweep_volume"] = abs(coupon_fluid.volume - expected) / expected < 1e-7
        report["coupon"] = {"two_open_accesses": True, "blind_branches": 0, "continuous_turn_radius": p["coupon"]["gallery_half_spacing"],
                            "nominal_ligaments_mm": clearances, "powder_removal_physically_demonstrated": False,
                            "internal_supports_present_in_CAD": False, "LPBF_overhang_and_surface_quality_qualified": False,
                            "processing": "choose_parameter_set; inspect_and_clean_both_ports; no_manufacturing_order"}
        hp = p["head"]
        _, head_length = gallery_y(hp)
        report["hydraulics"] = hydraulic_screen(p["hydraulic_screen"], head_length, hp["gallery_radius"])
        if not args.original_only:
            files = [args.project_root / hp["source"], args.project_root / hp["assembly"]]
            expected_hashes = [hp["source_sha256"], hp["assembly_sha256"]]
            if [sha256(f) for f in files] != expected_hashes:
                raise ValueError("private_source_digest_mismatch")
            print("Importing immutable four-seat head", flush=True)
            inherited = b.import_step(files[0]).solids()[0]
            assembly = b.import_step(files[1])
            solids = list(assembly.solids())
            body_indices = [i for i, s in enumerate(solids) if abs(s.volume - inherited.volume) / inherited.volume < 1e-7]
            if len(solids) != 13 or len(body_indices) != 1:
                raise ValueError("inherited_assembly_identity_ambiguous")
            components = [s for i, s in enumerate(solids) if i != body_indices[0]]
            gallery, tool_length = gallery_y(hp)
            print("Boolean gallery proposal on an independent head copy", flush=True)
            candidate = inherited.cut(gallery)
            intersections = inherited.intersect(gallery)
            if not intersections or len(intersections.solids()) != 1:
                raise ValueError("head_fluid_domain_not_single_connected_solid")
            internal = b.Compound(children=list(intersections))
            removed = inherited.volume - candidate.volume
            fraction = removed / inherited.volume
            if not (0 < fraction < hp["maximum_removed_volume_fraction_screen"]):
                raise ValueError("head_removed_volume_screen_failed")
            insert_overlaps = []
            for c in components:
                common = c.intersect(gallery)
                insert_overlaps.append(sum(abs(x.volume) for x in common.solids()) if common else 0)
            if max(insert_overlaps) > 1e-5:
                raise ValueError("gallery_intersects_inherited_valve_seat_or_guide")
            for name, shape in [("head-4v-air-oil-proposal", candidate), ("head-oil-tool", gallery), ("head-fluid-domain", internal), ("head-source-context", inherited)]:
                print(f"Exporting {name}", flush=True)
                report["geometry"][name] = export_checked(shape, cad, name)
            report["geometry"]["head-4v-air-oil-assembly"] = export_checked(b.Compound(children=[candidate, *components]), cad, "head-4v-air-oil-assembly", mesh=False)
            for i, s in enumerate(components, 1):
                b.export_stl(s, cad / f"component-{i:02d}-context.stl", tolerance=0.08, angular_tolerance=0.18)
            bb0, bb1 = inherited.bounding_box(), candidate.bounding_box()
            bbox_delta = max(abs(a - c) for a, c in zip([*bb0.min, *bb0.max], [*bb1.min, *bb1.max]))
            report["head"] = {"inherited_source_sha256": expected_hashes[0], "inherited_assembly_sha256": expected_hashes[1],
                              "body_index_found_by_volume": body_indices[0], "component_count": len(components), "fluid_connected_solid_count": len(internal.solids()),
                              "removed_material_volume_mm3_hypothesis": removed, "removed_material_fraction": fraction,
                              "oil_component_intersection_volumes_mm3_hypothesis": insert_overlaps,
                              "bounding_box_max_delta_scan_units": bbox_delta, "gallery_tool_length_mm_hypothesis": tool_length,
                              "source_fins_redesigned": False, "continuous_minimum_wall_certified": False,
                              "source_closed_caps_are_not_CT": True, "powder_removal_validated": False,
                              "opening_count_and_no_unintended_surface_breakthrough_certified": False,
                              "complete_M64_head": False, "full_ports_chamber_piston_spark_plug_cam_oil_circuit_defined": False,
                              "minimum_hot_wall_allowable_mm": None}
            report["checks"]["gallery_has_no_volumetric_intersection_with_12_components"] = max(insert_overlaps) <= 1e-5
            report["checks"]["head_bbox_preserved"] = bbox_delta < 1e-6
            report["source_inputs_unchanged"] = [sha256(f) for f in files] == expected_hashes
        report["checks"]["all_exported_BRep_and_STEP_checks"] = all(g["BRep_valid_after_STEP"] for g in report["geometry"].values())
        report["checks"]["all_review_STL_checks"] = all(g.get("mesh_accepted_for_review", True) for g in report["geometry"].values())
        report["status"] = "geometry_review_passed_not_physical_validation" if all(report["checks"].values()) else "review_mesh_or_geometry_gate_failed"
    except Exception as exc:
        report["status"] = "rejected_partial_outputs_kept"
        report["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["elapsed_seconds"] = time.perf_counter() - started
        (args.output / "verification.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(f"Report: {args.output / 'verification.json'}", flush=True)


if __name__ == "__main__":
    main()
