#!/usr/bin/env python3
"""993 engine cooling fan guide-vane ring (stator), AlSi10Mg concept F1.

The F1 impeller leaves the air spinning; that swirl is lost pressure. This
fixed ring of vanes sits right behind the rotor, in the same annulus, and
turns the swirl back into pressure (the rotor-plus-diffuser idea behind
Dyson's motors). Vane angles are designed from the F1 rotor's exit swirl,
station by station, with the same one-dimensional cascade model. The vane
count is picked from a rotor-stator interaction tone screen.

Everything is synthetic: rotor, speeds, engine resistance and interfaces.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path


PART_ID = "993-ENG-FAN-STATOR-ALSI10MG-F1-0001"
ROTOR_PART_ID = "993-ENG-COOLING-IMPELLER-WE43-F1-0001"
HOUSING_PART_ID = "993-ENG-FAN-HOUSING-ALSI10MG-F0-0001"
ROOT = Path(__file__).resolve().parents[3]
ROTOR_SCRIPT = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001/source/cooling_impeller_f1.py"


def _load_rotor_module():
    spec = importlib.util.spec_from_file_location("cooling_impeller_f1", ROTOR_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


R = _load_rotor_module()

# Vane row. Synthetic, sized to the F1 rotor annulus.
VANE_COUNT_CANDIDATES = range(12, 32)
TARGET_DIFFUSION_FACTOR = 0.40
MINIMUM_SOLIDITY = 0.8
MAXIMUM_SOLIDITY = 1.6
THICKNESS_TO_CHORD = 0.079          # on the 59.5 mm span of the cup-hub rotor, keeps both modal bounds 20 % off every BPF line
MINIMUM_VANE_THICKNESS_MM = 1.5
ROTOR_STATOR_AXIAL_GAP_MM = 15.0     # about half a rotor hub chord, for wake mixing
RING_AXIAL_MARGIN_MM = 2.0
INNER_RING_BORE_MM = 70.0            # F0 housing synthetic alternator seat
INNER_RING_THICKNESS_MM = 3.0        # sleeve under the vane roots, at the rotor hub radius
INNER_WEB_THICKNESS_MM = 4.0         # flange from the sleeve to the seat, on the plate face
SEAT_SLEEVE_THICKNESS_MM = 3.0
OUTER_RING_THICKNESS_MM = 2.5
OUTER_RING_OUTER_DIAMETER_MM = 248.0 # same as the rotor, fits the EOS M 290 plate
EOS_M290_PLATE_MM = 250.0
HOUSING_SHELL_INNER_DIAMETER_MM = 294.0  # F0 housing, 300 mm OD minus 2 x 3 mm shell

# Tone screen: a rotor-stator interaction mode m = n*B - k*V propagates in the
# duct when its tip phase speed reaches the speed of sound, |m| <= n*B*M_tip.
TONE_HARMONICS = (1, 2)
TONE_MACH_MARGIN = 1.2               # cut-off must hold at 1.2 x the overspeed tip Mach

# Material: AlSi10Mg. The ring does not spin, so magnesium's density gain is
# small next to its corrosion and galvanic cost in the cooling-air stream.
DENSITY_KG_M3 = 2670.0
ELASTIC_MODULUS_PA = 70.0e9
YIELD_STRENGTH_PA = 245.0e6
MINIMUM_SCREEN_RATIO = 1.5
MINIMUM_MODAL_SEPARATION_RATIO = 0.20
AIRFOIL_AREA_FACTOR = R.AIRFOIL_AREA_FACTOR
AIRFOIL_MINOR_INERTIA_FACTOR = R.AIRFOIL_MINOR_INERTIA_FACTOR


def rotor_exit(rotor: dict[str, object], flow_m3_s: float, speed_rpm: float) -> list[dict[str, float]]:
    """Axial velocity and swirl leaving each F1 rotor station, with the
    shroud leakage recirculated and simple radial equilibrium solved as in
    the rotor model."""
    base = R.rotor_performance(rotor, flow_m3_s, speed_rpm, shrouded=True, stator=False, bellmouth=True)
    # Radial equilibrium sets the axial velocity at each station.
    return [
        {
            "radius_mm": e["radius_mm"],
            "axial_velocity_m_s": e["axial_velocity_m_s"],
            "swirl_m_s": e["swirl_m_s"],
            "swirl_angle_deg": math.degrees(math.atan(e["swirl_m_s"] / e["axial_velocity_m_s"])),
        }
        for e in base["exit_stations"]
    ]


def design_vanes(exit_flow: list[dict[str, float]], vane_count: int) -> list[dict[str, float]]:
    """Zero-incidence inlet, zero exit swirl after Carter deviation, chord
    from a target diffusion factor."""
    vanes = []
    for e in exit_flow:
        alpha2 = e["swirl_angle_deg"]
        a2 = math.radians(alpha2)
        # DF for a row turning alpha2 -> 0: 1 - cos(a2) + sin(a2)/(2 sigma)
        denominator = TARGET_DIFFUSION_FACTOR - 1.0 + math.cos(a2)
        solidity = math.sin(a2) / (2.0 * denominator) if denominator > 0.0 else MAXIMUM_SOLIDITY
        solidity = min(max(solidity, MINIMUM_SOLIDITY), MAXIMUM_SOLIDITY)
        kappa1, kappa2 = R.metal_angles(alpha2, 0.0, solidity)
        r_mm = e["radius_mm"]
        chord = solidity * 2.0 * math.pi * r_mm / vane_count
        vanes.append({
            "radius_mm": r_mm,
            "inlet_flow_angle_deg": alpha2,
            "solidity": solidity,
            "chord_mm": chord,
            "thickness_mm": max(THICKNESS_TO_CHORD * chord, MINIMUM_VANE_THICKNESS_MM),
            "inlet_metal_deg": kappa1,
            "outlet_metal_deg": kappa2,
            "camber_deg": kappa1 - kappa2,
            "stagger_deg": (kappa1 + kappa2) / 2.0,
        })
    return vanes


def tone_screen(vane_count: int, blade_count: int, tip_mach: float) -> dict[str, object]:
    cut_on = []
    for n in TONE_HARMONICS:
        limit = n * blade_count * tip_mach * TONE_MACH_MARGIN
        for k in range(-4, 5):
            m = n * blade_count - k * vane_count
            if abs(m) <= limit:
                cut_on.append({"harmonic": n, "k": k, "mode": m})
    return {
        "vane_count": vane_count,
        "coprime_with_blades": math.gcd(vane_count, blade_count) == 1,
        "cut_on_modes": cut_on,
        "bpf_interaction_cut_off": not any(c["harmonic"] == 1 for c in cut_on),
    }


def choose_vane_count(blade_count: int, tip_mach: float) -> tuple[int, list[dict[str, object]]]:
    """Fewest vanes that are coprime with the blades and cut off every
    first-harmonic (blade-pass) interaction mode with the Mach margin.
    Second-harmonic modes are reported, not optimised: silencing them all
    would need about three vanes per blade."""
    screens = [tone_screen(v, blade_count, tip_mach) for v in VANE_COUNT_CANDIDATES]
    eligible = [s for s in screens if s["coprime_with_blades"] and s["bpf_interaction_cut_off"]]
    best = min(eligible, key=lambda s: s["vane_count"])
    return best["vane_count"], screens


def vane_structure(vanes: list[dict[str, float]], rotor: dict[str, object],
                   exit_flow: list[dict[str, float]], vane_count: int,
                   flow_m3_s: float, speed_rpm: float) -> dict[str, float]:
    rho_air = R.air_density()
    length_m = (rotor["tip_radius_mm"] - rotor["hub_radius_mm"]) / 1000.0
    area = sum(AIRFOIL_AREA_FACTOR * v["chord_mm"] * v["thickness_mm"] for v in vanes) / len(vanes) / 1.0e6
    inertia = sum(
        AIRFOIL_MINOR_INERTIA_FACTOR * v["chord_mm"] * v["thickness_mm"] ** 3 for v in vanes
    ) / len(vanes) / 1.0e12
    root_inertia_mm4 = min(AIRFOIL_MINOR_INERTIA_FACTOR * v["chord_mm"] * v["thickness_mm"] ** 3 for v in vanes)
    root_thickness_mm = next(
        v["thickness_mm"] for v in vanes
        if AIRFOIL_MINOR_INERTIA_FACTOR * v["chord_mm"] * v["thickness_mm"] ** 3 == root_inertia_mm4
    )
    base = math.sqrt(ELASTIC_MODULUS_PA * inertia / (DENSITY_KG_M3 * area * length_m**4)) / (2.0 * math.pi)
    pinned_hz = math.pi**2 * base
    clamped_hz = 4.730040744862704**2 * base
    rev_hz = speed_rpm / 60.0
    bpf_hz = rotor["blade_count"] * rev_hz
    overspeed_bpf_hz = bpf_hz * R.SYNTHETIC_OVERSPEED_FACTOR
    # The real end fixity lies between pinned and clamped: screen both.
    separation = min(
        abs(mode - f) / f
        for mode in (pinned_hz, clamped_hz)
        for f in (bpf_hz, 2.0 * bpf_hz, overspeed_bpf_hz, 2.0 * overspeed_bpf_hz)
    )
    # Reaction torque of removing the swirl, shared by the vanes, applied as
    # a uniform load on a pinned-pinned span (conservative bending).
    mean_rcu = sum(e["radius_mm"] / 1000.0 * e["swirl_m_s"] for e in exit_flow) / len(exit_flow)
    reaction_torque = rho_air * flow_m3_s * mean_rcu
    mean_radius = (rotor["tip_radius_mm"] + rotor["hub_radius_mm"]) / 2000.0
    force_per_vane = reaction_torque / mean_radius / vane_count
    moment = force_per_vane * length_m / 8.0
    bending_pa = moment * (root_thickness_mm / 2000.0) / (root_inertia_mm4 / 1.0e12)
    return {
        "vane_span_mm": length_m * 1000.0,
        "first_mode_pinned_hz": pinned_hz,
        "first_mode_clamped_hz": clamped_hz,
        "blade_pass_frequency_hz": bpf_hz,
        "overspeed_blade_pass_frequency_hz": overspeed_bpf_hz,
        "modal_separation_ratio_worst": separation,
        "resonance_crossing_fan_rpm_range": [
            pinned_hz / rotor["blade_count"] * 60.0,
            clamped_hz / rotor["blade_count"] * 60.0,
        ],
        "crossing_note": "the first vane mode meets blade-pass at a fan speed inside this range; any practical vane is crossed somewhere between idle and redline, so a forced-response check with measured damping is still required",
        "swirl_reaction_torque_nm": reaction_torque,
        "aero_force_per_vane_n": force_per_vane,
        "aero_bending_stress_mpa": bending_pa / 1.0e6,
        "yield_to_aero_bending_ratio": YIELD_STRENGTH_PA / bending_pa,
    }


def ring_envelope(vanes: list[dict[str, float]]) -> dict[str, float]:
    axial = max(v["chord_mm"] * math.cos(math.radians(v["stagger_deg"])) for v in vanes)
    return {
        "vane_axial_extent_mm": axial,
        "ring_axial_length_mm": math.ceil(axial + 2.0 * RING_AXIAL_MARGIN_MM),
    }


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    rotor = R.design_f1_rotor()
    speed = R.SYNTHETIC_NOMINAL_SPEED_RPM
    generic = R.CONFIGURATIONS["F1_rotor_with_matched_stator_and_bellmouth"]
    design_point = R.operating_point(rotor, speed, **generic)
    exit_flow = rotor_exit(rotor, design_point["flow_m3_s"], speed)

    overspeed_tip_mach = (
        R.angular_speed(speed * R.SYNTHETIC_OVERSPEED_FACTOR) * rotor["tip_radius_mm"] / 1000.0
        / math.sqrt(R.AIR_GAMMA * R.AIR_GAS_CONSTANT_J_KG_K * (R.SYNTHETIC_AIR_TEMPERATURE_C + 273.15))
    )
    vane_count, tone_screens = choose_vane_count(rotor["blade_count"], overspeed_tip_mach)
    vanes = design_vanes(exit_flow, vane_count)

    configs = {
        "F1_rotor_only_sharp_inlet": dict(shrouded=True, stator=False, bellmouth=False),
        "F1_rotor_plus_designed_stator_sharp_inlet": dict(shrouded=True, stator=True, bellmouth=False,
                                                          stator_vanes=vanes),
        "F1_rotor_plus_designed_stator_and_bellmouth": dict(shrouded=True, stator=True, bellmouth=True,
                                                            stator_vanes=vanes),
    }
    points = {name: R.operating_point(rotor, speed, **cfg) for name, cfg in configs.items()}
    reference = R.operating_point(R.design_reference_rotor(), speed, **R.CONFIGURATIONS["R0_conventional_rotor"])
    comparison = {
        name: {
            "flow_gain_vs_rotor_only": p["flow_m3_s"] / points["F1_rotor_only_sharp_inlet"]["flow_m3_s"] - 1.0,
            "flow_gain_vs_R0": p["flow_m3_s"] / reference["flow_m3_s"] - 1.0,
            "shaft_power_ratio_vs_rotor_only": p["shaft_power_w"] / points["F1_rotor_only_sharp_inlet"]["shaft_power_w"],
            "flow_gain_at_equal_shaft_power_vs_R0": (p["efficiency"] / reference["efficiency"]) ** (1.0 / 3.0) - 1.0,
        }
        for name, p in points.items()
    }

    stator_point = points["F1_rotor_plus_designed_stator_and_bellmouth"]
    off_design_exit = rotor_exit(rotor, stator_point["flow_m3_s"], speed)
    vane_rows = []
    for v, e in zip(vanes, off_design_exit):
        row = R.cascade(e["swirl_angle_deg"], v["inlet_metal_deg"], v["outlet_metal_deg"], v["solidity"])
        vane_rows.append({
            "radius_mm": v["radius_mm"],
            "incidence_deg": row["incidence_deg"],
            "residual_exit_swirl_deg": row["beta2_deg"],
            "diffusion_factor": row["diffusion_factor"],
            "equivalent_diffusion_ratio": row["equivalent_diffusion_ratio"],
            "stalled": row["stalled"],
        })

    structure = vane_structure(vanes, rotor, exit_flow, vane_count, stator_point["flow_m3_s"], speed)
    envelope = ring_envelope(vanes)
    cad_mass_g = cad_volume_mm3 / 1.0e9 * DENSITY_KG_M3 * 1000.0 if cad_volume_mm3 else None
    integration = {
        "rotor_part_id": ROTOR_PART_ID,
        "housing_part_id": HOUSING_PART_ID,
        "annulus_hub_tip_mm": [rotor["hub_radius_mm"], rotor["tip_radius_mm"]],
        "ring_outer_diameter_mm": OUTER_RING_OUTER_DIAMETER_MM,
        "ring_bore_mm": INNER_RING_BORE_MM,
        "rotor_stator_axial_gap_mm": ROTOR_STATOR_AXIAL_GAP_MM,
        "fits_eos_m290_flat": OUTER_RING_OUTER_DIAMETER_MM < EOS_M290_PLATE_MM,
        "radial_gap_to_f0_housing_shell_mm": (HOUSING_SHELL_INNER_DIAMETER_MM - OUTER_RING_OUTER_DIAMETER_MM) / 2.0,
        "mounting": "undefined: the F0 housing has no seat for a vane ring; a housing F1 must add one",
        "authority": "synthetic F0/F1 values only; no measured housing, alternator or tinware interface",
    }
    results = {
        "cad_volume_mm3": cad_volume_mm3,
        "cad_mass_g": cad_mass_g,
        "vane_count": vane_count,
        "stator_flow_m3_s": stator_point["flow_m3_s"],
        "stator_efficiency": stator_point["efficiency"],
        "flow_gain_vs_rotor_only": comparison["F1_rotor_plus_designed_stator_and_bellmouth"]["flow_gain_vs_rotor_only"],
        "flow_gain_vs_R0": comparison["F1_rotor_plus_designed_stator_and_bellmouth"]["flow_gain_vs_R0"],
        "stator_alone_flow_gain_vs_rotor_only": comparison["F1_rotor_plus_designed_stator_sharp_inlet"]["flow_gain_vs_rotor_only"],
        "flow_gain_at_equal_shaft_power_vs_R0": comparison["F1_rotor_plus_designed_stator_and_bellmouth"]["flow_gain_at_equal_shaft_power_vs_R0"],
        "maximum_residual_exit_swirl_deg": max(abs(r["residual_exit_swirl_deg"]) for r in vane_rows),
        "stalled_vane_stations": sum(int(r["stalled"]) for r in vane_rows),
        "first_harmonic_interaction_cut_off": tone_screen(vane_count, rotor["blade_count"], overspeed_tip_mach)["bpf_interaction_cut_off"],
        "modal_screen_pass": structure["modal_separation_ratio_worst"] >= MINIMUM_MODAL_SEPARATION_RATIO,
        "aero_bending_screen_pass": structure["yield_to_aero_bending_ratio"] >= MINIMUM_SCREEN_RATIO,
    }
    results["preliminary_screen_pass"] = (
        results["flow_gain_vs_rotor_only"] > 0.0
        and results["stalled_vane_stations"] == 0
        and results["first_harmonic_interaction_cut_off"]
        and results["modal_screen_pass"]
        and results["aero_bending_screen_pass"]
        and integration["fits_eos_m290_flat"]
    )
    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f1_guide_vane_ring_mathematical_screen",
        "design_intent": [
            "turn the F1 rotor's exit swirl back into static pressure before the air reaches the cylinder tinware",
            "vane angles designed station by station from the F1 rotor's exit flow at its stator operating point",
            "vane count chosen so every first-harmonic rotor-stator interaction tone is cut off in the duct",
            "same annulus and outer diameter as the F1 rotor so the ring prints flat on the EOS M 290",
        ],
        "synthetic_cases": {
            "speed_rpm": speed,
            "design_flow_m3_s": design_point["flow_m3_s"],
            "system_curve": "dp = K Q^2 through 1.01 m3/s at 800 Pa, as in F0 and the F1 rotor",
            "overspeed_tip_mach": overspeed_tip_mach,
            "authority": "regression inputs only; no measured 993 speed, fan map or engine resistance",
        },
        "rotor_exit_flow": exit_flow,
        "vane_design": vanes,
        "vane_off_design_rows": vane_rows,
        "tone_screen": {
            "criterion": "mode m = n*B - k*V cut on when |m| <= n*B*M_tip*1.2 (thin-annulus approximation with Mach margin)",
            "blade_count": rotor["blade_count"],
            "chosen_vane_count": vane_count,
            "candidates": tone_screens,
        },
        "operating_points": points,
        "reference_R0": reference,
        "comparison": comparison,
        "structure": structure,
        "envelope": envelope,
        "integration": integration,
        "material": {
            "candidate": "EOS Aluminium AlSi10Mg LPBF T6 comparison",
            "density_kg_m3": DENSITY_KG_M3,
            "elastic_modulus_pa": ELASTIC_MODULUS_PA,
            "yield_strength_pa": YIELD_STRENGTH_PA,
            "why_not_we43": "a stationary ring gains little from magnesium; aluminium avoids a magnesium surface in the hot, wet cooling stream",
        },
        "results": results,
        "interpretation": {
            "gain": "the gain over the rotor alone comes from recovering swirl, so shaft power barely changes while flow rises",
            "tones": "rotor-stator interaction is the main new noise source; the tone screen is a thin-annulus estimate, not an acoustic model",
            "blockage": "vane and ring blockage and the wakes of the housing spokes are not modelled",
            "integration": "the ring has no seat in the F0 housing; it defines what a housing F1 must provide",
        },
        "release_blockers": [
            "The rotor, the speeds and the engine resistance are synthetic.",
            "The stator model is one-dimensional: no CFD, rig test or acoustic measurement.",
            "No housing seat, fastening, alternator clearance or tinware interface exists.",
            "Vane wakes, blockage and the upstream housing spokes are not modelled.",
            "No vibration test of the vanes under rotor wakes.",
            "No manufacture or installation is authorized.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def vane_section_wire(vane: dict[str, float], radius_mm: float, z_mid: float, planar: bool):
    from build123d import Edge, Vector, Wire

    upper, lower = R.airfoil_points(
        vane["chord_mm"], vane["thickness_mm"], max(vane["camber_deg"], 0.5), vane["stagger_deg"]
    )

    def place(pts):
        # Mirror s: the stator's leading edge faces the rotor's swirl (+s).
        if planar:
            return [Vector(radius_mm, -ps, z_mid + pz) for ps, pz in pts]
        return [
            Vector(radius_mm * math.cos(-ps / radius_mm), radius_mm * math.sin(-ps / radius_mm), z_mid + pz)
            for ps, pz in pts
        ]

    up, low = place(upper), place(lower)
    return Wire([Edge.make_spline(up), Edge.make_line(up[-1], low[-1]), Edge.make_spline(low[::-1])])


def build_geometry():
    from build123d import Align, Cylinder, Pos, Rot, Solid

    screen = engineering_screen()
    vanes = screen["vane_design"]
    vane_count = screen["results"]["vane_count"]
    rotor = R.design_f1_rotor()
    length = screen["envelope"]["ring_axial_length_mm"]
    hub_r = rotor["hub_radius_mm"]
    tip_r = rotor["tip_radius_mm"]
    centered_min = (Align.CENTER, Align.CENTER, Align.MIN)

    # Inner ring: a sleeve under the vanes, a flange web on the plate face
    # (z = 0, printed without supports) and a sleeve on the alternator seat.
    seat_r = INNER_RING_BORE_MM / 2.0
    inner = Cylinder(hub_r, length, align=centered_min) - Pos(
        0.0, 0.0, INNER_WEB_THICKNESS_MM
    ) * Cylinder(hub_r - INNER_RING_THICKNESS_MM, length, align=centered_min)
    inner = inner + Cylinder(seat_r + SEAT_SLEEVE_THICKNESS_MM, length, align=centered_min)
    inner = inner - Pos(0.0, 0.0, -1.0) * Cylinder(seat_r, length + 2.0, align=centered_min)
    outer = Cylinder(OUTER_RING_OUTER_DIAMETER_MM / 2.0, length, align=centered_min) - Pos(
        0.0, 0.0, -1.0
    ) * Cylinder(tip_r, length + 2.0, align=centered_min)
    body = inner + outer

    z_mid = length / 2.0
    sections = [(vanes[0], hub_r - INNER_RING_THICKNESS_MM / 2.0, True)]   # root cap inside the sleeve
    sections += [(v, v["radius_mm"], False) for v in vanes[1:-1:2]]
    sections += [(vanes[-1], vanes[-1]["radius_mm"], False), (vanes[-1], tip_r + 1.2, True)]
    vane = Solid.make_loft([vane_section_wire(v, r, z_mid, p) for v, r, p in sections])
    if not vane.is_valid:
        raise SystemExit("The lofted F1 vane is not a valid solid.")
    for index in range(vane_count):
        body = body + Rot(0.0, 0.0, index * 360.0 / vane_count) * vane
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--stl", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    cad_volume_mm3 = None
    envelope = None
    if args.out:
        from build123d import export_step, export_stl, import_step

        shape = build_geometry()
        if not shape.is_valid or len(shape.solids()) != 1:
            raise SystemExit("The F1 vane ring must be one valid BREP solid.")
        bbox = shape.bounding_box()
        envelope = [bbox.size.X, bbox.size.Y, bbox.size.Z]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(shape, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 1:
            raise SystemExit("The re-read STEP does not keep the valid solid.")
        if abs(roundtrip.volume - shape.volume) > 0.05:
            raise SystemExit("The re-read STEP does not reproduce the OCCT volume.")
        cad_volume_mm3 = roundtrip.volume
        if args.stl:
            export_stl(shape, str(args.stl), tolerance=0.02, angular_tolerance=0.1)

    report = engineering_screen(cad_volume_mm3)
    if args.out and envelope is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "semantic_solids": ["fan_guide_vane_ring_f1"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "vane_count": report["results"]["vane_count"],
            "maximum_volume_delta_mm3": 0.05,
        }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["results"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
