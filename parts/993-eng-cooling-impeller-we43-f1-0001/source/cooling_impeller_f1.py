#!/usr/bin/env python3
"""993 engine cooling impeller, concept F1 in LPBF WE43, redesigned from the
visual rebuild of the original Turbo rotor.

F1 keeps the rebuild's envelope and interfaces: 245 mm, the deep cup around
the alternator with its twelve windows, three bolt holes and bore, eleven
blades and no shroud. It replaces the rebuild's constant-pitch cambered
plates with twisted airfoil blades designed from velocity triangles, and
moves to a lighter alloy. Gains are quoted against the rebuild rotor in the
same housing, on a duty inferred from the rebuild.

The flow simulation is a one-dimensional blade-element (streamline) model:
Euler work, Carter deviation, Lieblein diffusion losses, tip-leakage and
swirl losses, solved against a quadratic system curve. It is a mathematical
estimate on synthetic inputs, not CFD and not a measurement.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-COOLING-IMPELLER-WE43-F1-0001"
PREDECESSOR_PART_ID = "993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001"
HOUSING_PART_ID = "993-ENG-FAN-HOUSING-ALSI10MG-F0-0001"

ROOT = Path(__file__).resolve().parents[3]
REBUILD_PARAMETERS = (
    ROOT / "twins/993-engine-cooling-fan-system-f0/source/picogk-reference/reference.json"
)
REBUILD = json.loads(REBUILD_PARAMETERS.read_text(encoding="utf-8"))
REBUILD_CAMBER_HEIGHT_MM = 2.0       # parabolic camber height hard-coded in the rebuild's Program.cs

# Duty. No 993 fan map or engine resistance is published. The duty is
# inferred from the rebuild itself: the engine-resistance curve K Q^2 that
# runs the rebuild rotor at its best efficiency at the nominal speed, in the
# same bellmouth housing (matched_duty() recomputes these two values; a test
# keeps them in step). It inherits every visual hypothesis of the rebuild,
# the 48 degree blade pitch first.
SYNTHETIC_NOMINAL_SPEED_RPM = 10_000.0
SYNTHETIC_OVERSPEED_FACTOR = 1.20
SYNTHETIC_AIRFLOW_M3_S = 2.340
SYNTHETIC_PRESSURE_RISE_PA = 2155.0
SYNTHETIC_AIR_TEMPERATURE_C = 80.0
AMBIENT_PRESSURE_PA = 101_325.0
AIR_GAMMA = 1.4
AIR_GAS_CONSTANT_J_KG_K = 287.05
OPERATING_IMPELLER_TEMPERATURE_C = 150.0
REFERENCE_TEMPERATURE_C = 20.0
MINIMUM_SCREEN_RATIO = 1.5
MINIMUM_MODAL_SEPARATION_RATIO = 0.20

# Integration: the F0 housing throat is 252 mm (synthetic).
HOUSING_SYNTHETIC_THROAT_MM = 252.0
MINIMUM_SYNTHETIC_RADIAL_CLEARANCE_MM = 2.0
EOS_M290_PLATE_MM = 250.0

# F1 keeps the rebuild's envelope and interfaces: same 245 mm diameter, same
# cup (alternator space, web, twelve windows, three bolt holes and bore),
# eleven blades, no shroud. Only the blades and the alloy change.
OUTER_DIAMETER_MM = float(REBUILD["rotor_diameter_mm"])
SHROUDED = False
SHROUD_OUTER_RADIUS_MM = OUTER_DIAMETER_MM / 2.0   # no shroud: the blade tip radius
SHROUD_THICKNESS_MM = 0.0
LABYRINTH_TOOTH_COUNT = 0
LABYRINTH_TOOTH_WIDTH_MM = 1.5
CUP_DEPTH_MM = float(REBUILD["cup_rear_z_mm"] - REBUILD["cup_front_z_mm"])
AXIAL_DEPTH_MM = CUP_DEPTH_MM
HUB_OUTER_DIAMETER_MM = 2.0 * REBUILD["cup_radius_mm"]
HUB_RIM_THICKNESS_MM = float(REBUILD["wall_mm"])
HUB_WEB_THICKNESS_MM = float(REBUILD["web_mm"])
HUB_BORE_DIAMETER_MM = 2.0 * REBUILD["bore_radius_mm"]
HUB_BOSS_DIAMETER_MM = HUB_BORE_DIAMETER_MM   # no boss: the separate bearing hub bolts on
VENT_COUNT = int(REBUILD["vent_count"])
VENT_RADIUS_MM = float(REBUILD["vent_radius_mm"])
VENT_RADIAL_HALFWIDTH_MM = float(REBUILD["vent_radial_halfwidth_mm"])
VENT_TANGENTIAL_HALFWIDTH_MM = float(REBUILD["vent_tangential_halfwidth_mm"])
BOLT_COUNT = 3
BOLT_CIRCLE_RADIUS_MM = float(REBUILD["bolt_circle_radius_mm"])
BOLT_HOLE_RADIUS_MM = float(REBUILD["bolt_hole_radius_mm"])
BLADE_COUNT = int(REBUILD["blade_count"])   # 11: coprime with the 6 housing spokes and a 17-vane stator
MAX_BLADE_AXIAL_PROJECTION_MM = 50.0       # inside the 56 mm cup depth
HUB_THICKNESS_TO_CHORD = 0.10
TIP_THICKNESS_TO_CHORD = 0.06
MINIMUM_BLADE_THICKNESS_MM = 1.5
TARGET_DIFFUSION_FACTOR = 0.30            # longer chords than 0.45: stall margin equal to the rebuild, blade mode 35 % above the spoke order
MAXIMUM_SOLIDITY = 1.6
VORTEX_EXPONENT = 1.0                # c_u2 ~ r^-n: 1 = free vortex (uniform exit flow), 0 = constant swirl
DESIGN_FLOW_GAIN = 1.10              # +10 % design flow: lands at the rebuild's shaft power
DESIGN_EFFICIENCY_GUESS = 0.80
AERO_STATIONS = 11

# Optional housing features (not part of this rotor, reported apart).
STATOR_VANE_COUNT = 17
STATOR_SOLIDITY = 1.2
BELLMOUTH_INLET_LOSS_K = 0.05
SHARP_INLET_LOSS_K = 0.50

# Reference: the rebuild rotor, modelled as eleven cambered constant-pitch
# plates between the cup and the tip, in the same housing as F1.
REFERENCE_BLADE_COUNT = int(REBUILD["blade_count"])
REFERENCE_HUB_OUTER_DIAMETER_MM = HUB_OUTER_DIAMETER_MM
REFERENCE_TIP_RADIUS_MM = OUTER_DIAMETER_MM / 2.0
REFERENCE_TIP_GAP_MM = (HOUSING_SYNTHETIC_THROAT_MM - OUTER_DIAMETER_MM) / 2.0
REFERENCE_PLATE_LOSS_FACTOR = 1.5    # thick cambered plate vs airfoil
TIP_GAP_EFFICIENCY_SLOPE = 2.0       # delta_eta = 2 * tau / h (unshrouded axial rotors)
LABYRINTH_DISCHARGE_COEFFICIENT = 0.5

# Materials. Values are published room-temperature data or generic handbook
# comparisons; none is a hot, rotating, HCF or burst allowable.
MATERIALS = {
    "WE43_LPBF_T6": {
        "density_kg_m3": 1840.0,
        "elastic_modulus_pa": 44.0e9,
        "yield_strength_pa": 219.0e6,
        "thermal_expansion_per_k": 26.7e-6,
        "sources": [
            "SRC-ORNL-WE43-LPBF-HYER-2020 (yield 219 MPa after 536 C/24 h + 205 C/48 h)",
            "SRC-AZOM-ELEKTRON-WE43-PROPERTIES (density 1.8 g/cm3, 26.7 um/m/C, service to 300 C)",
        ],
        "assumed": "density 1840 kg/m3 and modulus 44 GPa are generic magnesium comparison values",
    },
    "Scalmalloy_LPBF": {
        "density_kg_m3": 2670.0,
        "elastic_modulus_pa": 70.0e9,
        "yield_strength_pa": 480.0e6,
        "thermal_expansion_per_k": 23.0e-6,
        "sources": ["SRC-APWORKS-SCALMALLOY (yield 480 MPa, UTS 520 MPa, 13 %)"],
        "assumed": "density, modulus and expansion are generic aluminium comparison values",
    },
    "AlSi10Mg_LPBF_T6": {
        "density_kg_m3": 2670.0,
        "elastic_modulus_pa": 70.0e9,
        "yield_strength_pa": 245.0e6,
        "thermal_expansion_per_k": 21.0e-6,
        "sources": ["SRC-EOS-ALSI10MG-CURRENT-PAGE (F0 comparison values)"],
        "assumed": "same generic comparison as F0",
    },
}
PRIMARY_MATERIAL = "WE43_LPBF_T6"
STEEL_SHAFT_EXPANSION_PER_K = 12.0e-6
POISSON_RATIO = 0.3
AIRFOIL_AREA_FACTOR = 0.685          # NACA 4-digit section area / (t * c)
AIRFOIL_MINOR_INERTIA_FACTOR = 0.036 # I_min / (c * t^3)
SPOKE_COUNT = 6                      # F0 housing spokes upstream of the rotor


# --------------------------------------------------------------------------
# Air and kinematics
# --------------------------------------------------------------------------

def air_density() -> float:
    return AMBIENT_PRESSURE_PA / (
        AIR_GAS_CONSTANT_J_KG_K * (SYNTHETIC_AIR_TEMPERATURE_C + 273.15)
    )


def angular_speed(speed_rpm: float) -> float:
    return speed_rpm * 2.0 * math.pi / 60.0


def system_coefficient() -> float:
    """Quadratic engine resistance through the synthetic F0 point."""
    return SYNTHETIC_PRESSURE_RISE_PA / SYNTHETIC_AIRFLOW_M3_S**2


def blade_tip_radius_mm() -> float:
    return SHROUD_OUTER_RADIUS_MM - SHROUD_THICKNESS_MM


def stations(hub_mm: float, tip_mm: float, count: int = AERO_STATIONS) -> list[float]:
    """Equal-area radial stations (m), one per annular strip centroid."""
    out = []
    for i in range(count):
        a0 = hub_mm**2 + (tip_mm**2 - hub_mm**2) * i / count
        a1 = hub_mm**2 + (tip_mm**2 - hub_mm**2) * (i + 1) / count
        out.append(math.sqrt((a0 + a1) / 2.0) / 1000.0)
    return out


# --------------------------------------------------------------------------
# Cascade model
# --------------------------------------------------------------------------

def carter_m(outlet_metal_deg: float) -> float:
    """Carter's rule coefficient for a circular-arc camber line."""
    return 0.23 + 0.002 * outlet_metal_deg


def metal_angles(beta1_deg: float, beta2_deg: float, solidity: float) -> tuple[float, float]:
    """Zero-incidence inlet metal angle and outlet metal angle giving beta2
    after Carter deviation delta = m * camber / sqrt(sigma)."""
    kappa1 = beta1_deg
    kappa2 = beta2_deg
    for _ in range(50):
        m = carter_m(kappa2)
        kappa2 = (beta2_deg - m * kappa1 / math.sqrt(solidity)) / (1.0 - m / math.sqrt(solidity))
    return kappa1, kappa2


def cascade(beta1_deg: float, kappa1_deg: float, kappa2_deg: float, solidity: float,
            loss_factor: float = 1.0, axial_velocity_ratio: float = 1.0) -> dict[str, float]:
    """Exit flow angle, equivalent diffusion ratio and total-pressure loss
    coefficient (on inlet relative dynamic head) of one blade row section.
    axial_velocity_ratio is c_x2 / c_x1 across the row (radial equilibrium);
    at 1.0 the Lieblein forms reduce to their constant-axial-velocity versions."""
    camber = kappa1_deg - kappa2_deg
    deviation = carter_m(kappa2_deg) * camber / math.sqrt(solidity)
    beta2_deg = kappa2_deg + deviation
    incidence = beta1_deg - kappa1_deg
    b1 = math.radians(beta1_deg)
    b2 = math.radians(beta2_deg)
    avr = axial_velocity_ratio
    w2_over_w1 = avr * math.cos(b1) / math.cos(b2)
    d_eq = (1.0 / w2_over_w1) * (
        1.12
        + 0.0117 * abs(incidence) ** 1.43
        + 0.61 * math.cos(b1) ** 2 / solidity * (math.tan(b1) - avr * math.tan(b2))
    )
    # Loss correlation is singular at D_eq = exp(1/1.17) = 2.35: hold it at
    # the 2.2 stall limit; stalled stations are flagged, not trusted. Below
    # 1.0 (accelerating rows, only reached at extreme axial velocity ratios)
    # it is held at its unloaded value.
    d_eq_safe = min(max(d_eq, 1.0), 2.2)
    momentum_thickness = 0.004 / (1.0 - 1.17 * math.log(d_eq_safe))
    omega = (
        2.0 * momentum_thickness * solidity / math.cos(b2)
        * w2_over_w1 ** 2
    ) * loss_factor
    diffusion_factor = (
        1.0 - w2_over_w1
        + math.cos(b1) * (math.tan(b1) - avr * math.tan(b2)) / (2.0 * solidity)
    )
    return {
        "beta2_deg": beta2_deg,
        "deviation_deg": deviation,
        "incidence_deg": incidence,
        "equivalent_diffusion_ratio": d_eq,
        "diffusion_factor": diffusion_factor,
        "loss_coefficient": omega,
        "stalled": d_eq > 2.2,
    }


def _root(f, lo: float, hi: float, tol: float, guess: float | None = None) -> float:
    """Root of f, increasing on [lo, hi] with f(lo) < 0 < f(hi). A secant
    from guess is tried first (it converges in a few steps on the smooth
    residuals here); Illinois false position on the bracket is the fallback."""
    if guess is not None and lo < guess < hi:
        x0, x1 = guess, guess * (1.0 + 1.0e-3) if guess else tol
        f0, f1 = f(x0), f(x1)
        for _ in range(8):
            if f1 == f0:
                break
            x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
            if not lo < x2 < hi:
                break
            x0, f0, x1 = x1, f1, x2
            f1 = f(x1)
            if abs(f1) < tol or abs(x1 - x0) < tol:
                return x1
    f_lo, f_hi = f(lo), f(hi)
    side = 0
    x = lo
    for _ in range(100):
        x = (lo * f_hi - hi * f_lo) / (f_hi - f_lo)
        fx = f(x)
        if abs(fx) < tol or hi - lo < tol:
            break
        if fx < 0.0:
            lo, f_lo = x, fx
            if side == -1:
                f_hi /= 2.0
            side = -1
        else:
            hi, f_hi = x, fx
            if side == 1:
                f_lo /= 2.0
            side = 1
    return x


def radial_equilibrium(radii_m: list[float], mean_axial_m_s: float, rho: float,
                       exit_swirl, total_pressure_rise) -> dict[str, object]:
    """Simple radial equilibrium behind the rotor, on equal-area stations.

    (1/rho) dp0/dr = c_x dc_x/dr + (c_u / r) d(r c_u)/dr, marched implicitly
    from the hub: at each station the exit swirl exit_swirl(i, c_x2) and the
    total-pressure rise total_pressure_rise(i, c_x2, c_u2) are re-evaluated
    with the station's own axial velocity, so off-design blade rows (where
    the swirl depends on c_x2) are solved, not iterated. The hub value is set
    so the mean axial velocity carries the flow. Inlet flow is uniform and
    swirl-free. A station whose c_x2 would fall under a tenth of the mean is
    held there and counted as flow collapse."""
    n = len(radii_m)
    floor = 0.1 * mean_axial_m_s
    ceiling = 4.0 * mean_axial_m_s
    tol = 1.0e-7 * mean_axial_m_s

    last = [mean_axial_m_s] * n          # warm start: the previous march

    def march(hub_c_x: float) -> tuple[list[float], list[float], int]:
        c_x2 = [hub_c_x]
        c_u2 = [exit_swirl(0, hub_c_x)]
        dp0 = [total_pressure_rise(0, hub_c_x, c_u2[0])]
        collapsed = 0
        for i in range(1, n):
            r0, r1 = radii_m[i - 1], radii_m[i]

            def residual(x):
                cu = exit_swirl(i, x)
                rhs = c_x2[-1] ** 2 + 2.0 * (
                    (total_pressure_rise(i, x, cu) - dp0[-1]) / rho
                    - 0.5 * (cu / r1 + c_u2[-1] / r0) * (r1 * cu - r0 * c_u2[-1])
                )
                return x * x - rhs

            x = _root(residual, floor, ceiling, tol, guess=last[i])
            if x <= floor * (1.0 + 1.0e-9) and residual(floor) >= 0.0:
                x = floor
                collapsed += 1
            elif x >= ceiling * (1.0 - 1.0e-9) and residual(ceiling) <= 0.0:
                x = ceiling
                collapsed += 1
            cu = exit_swirl(i, x)
            c_x2.append(x)
            c_u2.append(cu)
            dp0.append(total_pressure_rise(i, x, cu))
        last[:] = c_x2
        return c_x2, c_u2, collapsed

    def excess(hub_c_x: float) -> float:
        return sum(march(hub_c_x)[0]) / n - mean_axial_m_s

    hub = _root(excess, floor, ceiling, tol, guess=mean_axial_m_s)
    c_x2, c_u2, collapsed = march(hub)
    collapsed += int(hub <= floor * (1.0 + 1.0e-9) or hub >= ceiling * (1.0 - 1.0e-9))
    return {"axial_m_s": c_x2, "swirl_m_s": c_u2, "collapsed_station_count": collapsed}


# --------------------------------------------------------------------------
# Rotor designs
# --------------------------------------------------------------------------

def design_f1_rotor() -> dict[str, object]:
    """Velocity-triangle design of the F1 blades at the design point."""
    rho = air_density()
    omega = angular_speed(SYNTHETIC_NOMINAL_SPEED_RPM)
    hub_mm = HUB_OUTER_DIAMETER_MM / 2.0
    tip_mm = blade_tip_radius_mm()
    area = math.pi * ((tip_mm / 1000.0) ** 2 - (hub_mm / 1000.0) ** 2)
    q_design = SYNTHETIC_AIRFLOW_M3_S * DESIGN_FLOW_GAIN
    dp_design = system_coefficient() * q_design**2
    c_x = q_design / area
    radii = stations(hub_mm, tip_mm)
    # Swirl law c_u2 = C * r^-n, C set so the mass-averaged ideal work matches
    # the required total pressure / guessed efficiency. Unless n = 1 (free
    # vortex) the work varies with radius, and radial equilibrium redistributes
    # the exit axial velocity; the blade exit angles follow that profile.
    target_work = dp_design / DESIGN_EFFICIENCY_GUESS / rho
    shape = [omega * r * r ** (-VORTEX_EXPONENT) for r in radii]
    swirl_constant = target_work / (sum(shape) / len(radii))
    exit_flow = None
    for _ in range(30):
        exit_flow = radial_equilibrium(
            radii, c_x, rho,
            lambda i, cx2, C=swirl_constant: C * radii[i] ** (-VORTEX_EXPONENT),
            lambda i, cx2, cu2: rho * omega * radii[i] * cu2,
        )
        mass_work = sum(
            omega * r * cu * cx2 / c_x
            for r, cu, cx2 in zip(radii, exit_flow["swirl_m_s"], exit_flow["axial_m_s"])
        ) / len(radii)
        correction = target_work / mass_work
        swirl_constant *= correction
        if abs(correction - 1.0) < 1.0e-9:
            break
    sections = []
    for r, c_x2 in zip(radii, exit_flow["axial_m_s"]):
        u = omega * r
        c_u2 = swirl_constant * r ** (-VORTEX_EXPONENT)
        avr = c_x2 / c_x
        beta1 = math.degrees(math.atan(u / c_x))
        beta2 = math.degrees(math.atan((u - c_u2) / c_x2))
        w1 = math.hypot(c_x, u)
        w2 = math.hypot(c_x2, u - c_u2)
        denominator = TARGET_DIFFUSION_FACTOR - 1.0 + w2 / w1
        solidity = (
            c_u2 / (2.0 * w1 * denominator)
            if denominator > 0.0 else MAXIMUM_SOLIDITY
        )
        solidity = min(max(solidity, 0.5), MAXIMUM_SOLIDITY)
        kappa1, kappa2 = metal_angles(beta1, beta2, solidity)
        stagger = (kappa1 + kappa2) / 2.0
        chord_mm = solidity * 2.0 * math.pi * r * 1000.0 / BLADE_COUNT
        chord_limit = MAX_BLADE_AXIAL_PROJECTION_MM / math.cos(math.radians(stagger))
        if chord_mm > chord_limit:
            chord_mm = chord_limit
            solidity = chord_mm * BLADE_COUNT / (2.0 * math.pi * r * 1000.0)
            kappa1, kappa2 = metal_angles(beta1, beta2, solidity)
            stagger = (kappa1 + kappa2) / 2.0
        span = (r * 1000.0 - hub_mm) / (tip_mm - hub_mm)
        t_over_c = HUB_THICKNESS_TO_CHORD + (TIP_THICKNESS_TO_CHORD - HUB_THICKNESS_TO_CHORD) * span
        thickness_mm = max(t_over_c * chord_mm, MINIMUM_BLADE_THICKNESS_MM)
        sections.append({
            "radius_mm": r * 1000.0,
            "blade_speed_m_s": u,
            "design_swirl_m_s": c_u2,
            "beta1_deg": beta1,
            "beta2_deg": beta2,
            "exit_axial_velocity_m_s": c_x2,
            "axial_velocity_ratio": avr,
            "de_haller_ratio": w2 / w1,
            "solidity": solidity,
            "chord_mm": chord_mm,
            "thickness_mm": thickness_mm,
            "inlet_metal_deg": kappa1,
            "outlet_metal_deg": kappa2,
            "camber_deg": kappa1 - kappa2,
            "stagger_deg": stagger,
        })
    return {
        "design_flow_m3_s": q_design,
        "design_system_pressure_pa": dp_design,
        "design_axial_velocity_m_s": c_x,
        "annulus_area_m2": area,
        "swirl_constant": swirl_constant,
        "vortex_exponent": VORTEX_EXPONENT,
        "design_exit_collapsed_station_count": exit_flow["collapsed_station_count"],
        "hub_radius_mm": hub_mm,
        "tip_radius_mm": tip_mm,
        "blade_count": BLADE_COUNT,
        "sections": sections,
    }


def design_reference_rotor(pitch_deg: float | None = None) -> dict[str, object]:
    """The rebuild rotor: eleven constant-pitch plates from the cup to the
    tip, chord tapering from root to tip, with the rebuild's 2 mm parabolic
    camber read as a circular arc. Pitch is measured from the plane of
    rotation, as in the rebuild's Program.cs. Every value is the rebuild's
    visual hypothesis."""
    pitch = REBUILD["blade_pitch_deg"] if pitch_deg is None else pitch_deg
    stagger = 90.0 - pitch
    hub_mm = REFERENCE_HUB_OUTER_DIAMETER_MM / 2.0
    tip_mm = REFERENCE_TIP_RADIUS_MM
    root, tip_chord = REBUILD["blade_root_chord_mm"], REBUILD["blade_tip_chord_mm"]
    sections = []
    for r in stations(hub_mm, tip_mm):
        r_mm = r * 1000.0
        span = (r_mm - hub_mm) / (tip_mm - hub_mm)
        chord = root + (tip_chord - root) * span
        camber = math.degrees(2.0 * math.atan(4.0 * REBUILD_CAMBER_HEIGHT_MM / chord))
        sections.append({
            "radius_mm": r_mm,
            "chord_mm": chord,
            "solidity": chord * REFERENCE_BLADE_COUNT / (2.0 * math.pi * r_mm),
            "camber_deg": camber,
            "stagger_deg": stagger,
            "inlet_metal_deg": stagger + camber / 2.0,
            "outlet_metal_deg": stagger - camber / 2.0,
            "thickness_mm": float(REBUILD["blade_thickness_mm"]),
        })
    return {
        "source": "twins/993-engine-cooling-fan-system-f0/source/picogk-reference/reference.json",
        "blade_pitch_from_rotation_plane_deg": pitch,
        "hub_radius_mm": hub_mm,
        "tip_radius_mm": tip_mm,
        "annulus_area_m2": math.pi * ((tip_mm / 1000.0) ** 2 - (hub_mm / 1000.0) ** 2),
        "blade_count": REFERENCE_BLADE_COUNT,
        "sections": sections,
    }


# --------------------------------------------------------------------------
# Off-design performance and operating point
# --------------------------------------------------------------------------

def rotor_performance(rotor: dict[str, object], flow_m3_s: float, speed_rpm: float, *,
                      shrouded: bool, stator: bool, bellmouth: bool,
                      loss_factor: float = 1.0,
                      stator_vanes: list[dict[str, float]] | None = None) -> dict[str, float]:
    """Useful pressure rise (Pa) the fan delivers against the engine at a
    given flow and speed, area-averaged over equal-area stations.
    stator_vanes, one entry per rotor station, replaces the generic
    zero-exit-swirl stator with a designed vane row."""
    rho = air_density()
    omega = angular_speed(speed_rpm)
    area = rotor["annulus_area_m2"]
    hub_mm = rotor["hub_radius_mm"]
    tip_mm = rotor["tip_radius_mm"]
    # Shroud leakage recirculates part of the rotor flow through the gap.
    leak = 0.0
    rotor_flow = flow_m3_s
    if shrouded:
        gap_m = (HOUSING_SYNTHETIC_THROAT_MM - OUTER_DIAMETER_MM) / 2000.0
        gap_area = math.pi * HOUSING_SYNTHETIC_THROAT_MM / 1000.0 * gap_m
    sections = rotor["sections"]
    n = len(sections)
    radii = [s["radius_mm"] / 1000.0 for s in sections]
    euler = rotor_loss = stator_loss = swirl_loss = mixing_loss = 0.0
    stalled = 0
    exit_flow = None
    for _ in range(3 if shrouded else 1):
        c_x = rotor_flow / area
        rows = [None] * n

        def blade_row(i, c_x2):
            u = omega * radii[i]
            beta1 = math.degrees(math.atan(u / c_x))
            rows[i] = cascade(beta1, sections[i]["inlet_metal_deg"], sections[i]["outlet_metal_deg"],
                              sections[i]["solidity"], loss_factor, axial_velocity_ratio=c_x2 / c_x)
            return u - c_x2 * math.tan(math.radians(rows[i]["beta2_deg"]))

        def total_pressure_rise(i, c_x2, c_u2):
            u = omega * radii[i]
            return rho * u * c_u2 - rows[i]["loss_coefficient"] * 0.5 * rho * (u**2 + c_x**2)

        exit_flow = radial_equilibrium(radii, c_x, rho, blade_row, total_pressure_rise)
        euler = rotor_loss = stator_loss = swirl_loss = mixing_loss = 0.0
        stalled = 0
        for index in range(n):
            u = omega * radii[index]
            c_x2 = exit_flow["axial_m_s"][index]
            c_u2 = exit_flow["swirl_m_s"][index]
            row = rows[index]
            weight = c_x2 / c_x                       # equal areas: mass share
            stalled += int(row["stalled"])
            w1_sq = u**2 + c_x**2
            euler += weight * rho * u * c_u2
            rotor_loss += weight * row["loss_coefficient"] * 0.5 * rho * w1_sq
            # Borda-Carnot mixing of the non-uniform axial profile downstream.
            mixing_loss += weight * 0.5 * rho * (c_x2 - c_x) ** 2
            if stator and c_u2 > 0.0:
                alpha2 = math.degrees(math.atan(c_u2 / c_x2))
                if stator_vanes is None:
                    k1, k2 = metal_angles(alpha2, 0.0, STATOR_SOLIDITY)
                    vane = cascade(alpha2, k1, k2, STATOR_SOLIDITY)
                else:
                    v = stator_vanes[index]
                    vane = cascade(alpha2, v["inlet_metal_deg"], v["outlet_metal_deg"], v["solidity"])
                c_u3 = c_x2 * math.tan(math.radians(vane["beta2_deg"]))
                stator_loss += weight * vane["loss_coefficient"] * 0.5 * rho * (c_x2**2 + c_u2**2)
                swirl_loss += weight * 0.5 * rho * c_u3**2
            else:
                swirl_loss += weight * 0.5 * rho * c_u2**2
        euler, rotor_loss, stator_loss, swirl_loss, mixing_loss = (
            euler / n, rotor_loss / n, stator_loss / n, swirl_loss / n, mixing_loss / n
        )
        if shrouded:
            dp_gap = max(euler - rotor_loss, 0.0)
            leak = LABYRINTH_DISCHARGE_COEFFICIENT * gap_area * math.sqrt(2.0 * dp_gap / rho)
            rotor_flow = flow_m3_s + leak
    tip_gap_loss = 0.0
    if not shrouded:
        blade_height = tip_mm - hub_mm
        tip_gap_loss = TIP_GAP_EFFICIENCY_SLOPE * REFERENCE_TIP_GAP_MM / blade_height * euler
    inlet_k = BELLMOUTH_INLET_LOSS_K if bellmouth else SHARP_INLET_LOSS_K
    c_x_delivered = rotor_flow / area
    inlet_loss = inlet_k * 0.5 * rho * c_x_delivered**2
    useful = (euler - rotor_loss - stator_loss - swirl_loss - mixing_loss
              - tip_gap_loss - inlet_loss)
    shaft_power = euler * rotor_flow
    return {
        "flow_m3_s": flow_m3_s,
        "rotor_flow_m3_s": rotor_flow,
        "leakage_m3_s": leak,
        "euler_pressure_pa": euler,
        "rotor_profile_loss_pa": rotor_loss,
        "stator_loss_pa": stator_loss,
        "exit_swirl_loss_pa": swirl_loss,
        "exit_mixing_loss_pa": mixing_loss,
        "tip_gap_loss_pa": tip_gap_loss,
        "inlet_loss_pa": inlet_loss,
        "useful_pressure_pa": useful,
        "air_power_w": useful * flow_m3_s,
        "shaft_power_w": shaft_power,
        "efficiency": useful * flow_m3_s / shaft_power if shaft_power > 0.0 else 0.0,
        "stalled_station_count": stalled,
        "exit_collapsed_station_count": exit_flow["collapsed_station_count"],
        "exit_stations": [
            {"radius_mm": r * 1000.0, "axial_velocity_m_s": cx, "swirl_m_s": cu}
            for r, cx, cu in zip(radii, exit_flow["axial_m_s"], exit_flow["swirl_m_s"])
        ],
    }


def operating_point(rotor, speed_rpm: float, **config) -> dict[str, float]:
    """Flow where fan useful pressure = K * Q^2 (false position)."""
    k = system_coefficient()
    flow = _root(
        lambda q: k * q**2 - rotor_performance(rotor, q, speed_rpm, **config)["useful_pressure_pa"],
        0.05, 4.0, 1.0e-9,
    )
    perf = rotor_performance(rotor, flow, speed_rpm, **config)
    perf["system_pressure_pa"] = k * flow**2
    return perf


def fan_curve(rotor, speed_rpm: float, flows: list[float], **config) -> list[dict[str, float]]:
    out = []
    for q in flows:
        perf = rotor_performance(rotor, q, speed_rpm, **config)
        out.append({
            "flow_m3_s": q,
            "useful_pressure_pa": perf["useful_pressure_pa"],
            "stalled_station_count": perf["stalled_station_count"],
        })
    return out


def stall_flow(rotor, speed_rpm: float, **config) -> float:
    """Lowest flow at which no station exceeds the D_eq stall limit."""
    lo, hi = 0.05, 4.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if rotor_performance(rotor, mid, speed_rpm, **config)["stalled_station_count"]:
            lo = mid
        else:
            hi = mid
    return hi


CONFIGURATIONS = {
    "REF_rebuild_rotor": {"shrouded": False, "stator": False, "bellmouth": True,
                          "loss_factor": REFERENCE_PLATE_LOSS_FACTOR},
    "F1_rotor_in_rebuild_housing": {"shrouded": False, "stator": False, "bellmouth": True},
    "F1_rotor_with_matched_stator": {"shrouded": False, "stator": True, "bellmouth": True},
}
REFERENCE = "REF_rebuild_rotor"
F1_ROTOR = "F1_rotor_in_rebuild_housing"
F1_STATOR = "F1_rotor_with_matched_stator"


def matched_duty(rotor: dict[str, object] | None = None) -> dict[str, float]:
    """Flow and pressure at the rebuild rotor's best efficiency at the
    nominal speed (golden section over its unstalled range). The engine
    curve through this point is the duty both rotors are compared on."""
    rotor = design_reference_rotor() if rotor is None else rotor
    config = CONFIGURATIONS[REFERENCE]
    speed = SYNTHETIC_NOMINAL_SPEED_RPM
    lo = stall_flow(rotor, speed, **config)

    def eta(q):
        return rotor_performance(rotor, q, speed, **config)["efficiency"]

    hi = 2.0 * lo
    g = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    for _ in range(60):
        c, d = b - g * (b - a), a + g * (b - a)
        if eta(c) > eta(d):
            b = d
        else:
            a = c
    flow = (a + b) / 2.0
    point = rotor_performance(rotor, flow, speed, **config)
    return {"flow_m3_s": flow, "pressure_rise_pa": point["useful_pressure_pa"],
            "efficiency": point["efficiency"], "shaft_power_w": point["shaft_power_w"],
            "stall_onset_flow_m3_s": lo}


# --------------------------------------------------------------------------
# Structure, dynamics, thermal, per material
# --------------------------------------------------------------------------

def blade_mass_properties(design: dict[str, object], density: float) -> dict[str, float]:
    """Mass, radial moment and root area of one blade from the aero stations,
    trapezoidal integration from hub to shroud."""
    secs = design["sections"]
    radii = [design["hub_radius_mm"]] + [s["radius_mm"] for s in secs] + [design["tip_radius_mm"]]
    areas = [AIRFOIL_AREA_FACTOR * s["chord_mm"] * s["thickness_mm"] for s in secs]
    areas = [areas[0]] + areas + [areas[-1]]
    mass = moment = 0.0
    for i in range(len(radii) - 1):
        dr = (radii[i + 1] - radii[i]) / 1000.0
        a = (areas[i] + areas[i + 1]) / 2.0 / 1.0e6
        rm = (radii[i] + radii[i + 1]) / 2000.0
        mass += density * a * dr
        moment += density * a * dr * rm
    root = secs[0]
    root_inertia = AIRFOIL_MINOR_INERTIA_FACTOR * root["chord_mm"] * root["thickness_mm"] ** 3
    mean_area = sum(areas) / len(areas)
    mean_inertia = sum(
        AIRFOIL_MINOR_INERTIA_FACTOR * s["chord_mm"] * s["thickness_mm"] ** 3 for s in secs
    ) / len(secs)
    return {
        "mass_kg": mass,
        "radial_moment_kg_m": moment,
        "root_area_mm2": areas[0],
        "root_minor_inertia_mm4": root_inertia,
        "mean_area_mm2": mean_area,
        "mean_minor_inertia_mm4": mean_inertia,
        "length_m": (design["tip_radius_mm"] - design["hub_radius_mm"]) / 1000.0,
    }


def structural_screen(design: dict[str, object], material: dict[str, float],
                      cad_volume_mm3: float | None,
                      aero: dict[str, float] | None = None) -> dict[str, object]:
    """aero: the nominal-speed operating point (shaft power, useful pressure)
    used for the cantilever root bending of unshrouded blades, scaled to
    overspeed with the square of speed."""
    rho = material["density_kg_m3"]
    e = material["elastic_modulus_pa"]
    sy = material["yield_strength_pa"]
    omega_n = angular_speed(SYNTHETIC_NOMINAL_SPEED_RPM)
    omega_o = angular_speed(SYNTHETIC_NOMINAL_SPEED_RPM * SYNTHETIC_OVERSPEED_FACTOR)
    blade = blade_mass_properties(design, rho)

    # Shroud (when fitted): free thin ring, and worst case where blades carry
    # all of it. Without a shroud the ring terms vanish.
    r_out = SHROUD_OUTER_RADIUS_MM / 1000.0
    r_in = blade_tip_radius_mm() / 1000.0
    ring_volume = math.pi * (r_out**2 - r_in**2) * AXIAL_DEPTH_MM / 1000.0
    tooth_volume = LABYRINTH_TOOTH_COUNT * math.pi * (
        (OUTER_DIAMETER_MM / 2000.0) ** 2 - r_out**2
    ) * LABYRINTH_TOOTH_WIDTH_MM / 1000.0
    ring_mass = rho * (ring_volume + tooth_volume) if SHROUDED else 0.0
    ring_mean_radius = (r_out + r_in) / 2.0
    tip_speed_o = omega_o * OUTER_DIAMETER_MM / 2000.0
    shroud_hoop_pa = rho * tip_speed_o**2 if SHROUDED else None
    blade_pull_n = blade["radial_moment_kg_m"] * omega_o**2
    ring_share_n = ring_mass / BLADE_COUNT * ring_mean_radius * omega_o**2
    root_stress_blade_only = blade_pull_n / blade["root_area_mm2"] * 1.0e6
    root_stress_with_ring = (blade_pull_n + ring_share_n) / blade["root_area_mm2"] * 1.0e6
    # Aerodynamic bending of a cantilever blade: tangential (torque) and
    # axial (pressure) loads spread evenly along the span, root moment F L / 2.
    aero_bending_pa = 0.0
    if aero is not None:
        scale = SYNTHETIC_OVERSPEED_FACTOR**2
        r_mean = (design["hub_radius_mm"] + design["tip_radius_mm"]) / 2000.0
        omega_nominal = omega_n
        tangential = aero["shaft_power_w"] / omega_nominal / r_mean / BLADE_COUNT
        area = design["annulus_area_m2"]
        axial = aero["useful_pressure_pa"] * area / BLADE_COUNT
        force = scale * math.hypot(tangential, axial)
        moment = force * blade["length_m"] / 2.0
        root = design["sections"][0]
        z_min = blade["root_minor_inertia_mm4"] / (root["thickness_mm"] / 2.0) / 1.0e9
        aero_bending_pa = moment / z_min
        root_stress_with_ring += aero_bending_pa

    # Hub cup, two worst cases like the shroud. (a) The rim is a free ring
    # carrying its own mass and the blade (and shroud) pull, with no help
    # from the web. (b) The web is an annular disc, bored, loaded at its
    # outer edge by everything outboard of it, with the boss counted as web.
    ro = HUB_OUTER_DIAMETER_MM / 2000.0
    r_rim_in = ro - HUB_RIM_THICKNESS_MM / 1000.0
    r_boss = HUB_BOSS_DIAMETER_MM / 2000.0
    ri = HUB_BORE_DIAMETER_MM / 2000.0
    depth = AXIAL_DEPTH_MM / 1000.0
    web = HUB_WEB_THICKNESS_MM / 1000.0
    rim_volume = math.pi * (ro**2 - r_rim_in**2) * depth
    web_volume = math.pi * (r_rim_in**2 - r_boss**2) * web
    boss_volume = math.pi * (r_boss**2 - ri**2) * depth
    rim_mass = rho * rim_volume
    web_mass = rho * web_volume
    boss_mass = rho * boss_volume
    hub_mass = rim_mass + web_mass + boss_mass
    nu = POISSON_RATIO
    outboard_pull_n = BLADE_COUNT * (blade_pull_n + ring_share_n)
    rim_mean = (ro + r_rim_in) / 2.0
    rim_hoop = (
        rho * (omega_o * rim_mean) ** 2
        + outboard_pull_n / (2.0 * math.pi * HUB_RIM_THICKNESS_MM / 1000.0 * depth)
    )
    rim_pull_n = outboard_pull_n + rim_mass * rim_mean * omega_o**2
    disk_bore_hoop = (3.0 + nu) / 4.0 * rho * omega_o**2 * (
        r_rim_in**2 + (1.0 - nu) / (3.0 + nu) * ri**2
    )
    rim_pressure = rim_pull_n / (2.0 * math.pi * r_rim_in * web)
    rim_bore_hoop = 2.0 * rim_pressure * r_rim_in**2 / (r_rim_in**2 - ri**2)
    hub_bore_hoop = disk_bore_hoop + rim_bore_hoop

    # Blade modes: cantilever (no shroud credit) and clamped-clamped (shroud
    # fully rigid), both with Southwell centrifugal stiffening.
    area_m2 = blade["mean_area_mm2"] / 1.0e6
    inertia_m4 = blade["mean_minor_inertia_mm4"] / 1.0e12
    length = blade["length_m"]
    base = math.sqrt(e * inertia_m4 / (rho * area_m2 * length**4)) / (2.0 * math.pi)
    cantilever_hz = 1.875104068711961**2 * base
    clamped_hz = 4.730040744862704**2 * base
    rev_hz = SYNTHETIC_NOMINAL_SPEED_RPM / 60.0
    cantilever_running = math.sqrt(cantilever_hz**2 + 1.17 * rev_hz**2)
    clamped_running = math.sqrt(clamped_hz**2 + 1.17 * rev_hz**2)
    spoke_order_hz = SPOKE_COUNT * rev_hz
    stator_order_hz = STATOR_VANE_COUNT * rev_hz
    governing_mode = clamped_running if SHROUDED else cantilever_running
    shrouded_separation = min(
        abs(governing_mode - spoke_order_hz) / spoke_order_hz,
        abs(governing_mode - stator_order_hz) / stator_order_hz,
    )

    # Thermal: differential growth against a steel shaft, and F0's fully
    # constrained comparison kept for continuity.
    delta_t = OPERATING_IMPELLER_TEMPERATURE_C - REFERENCE_TEMPERATURE_C
    bore_loosening_mm = (
        (material["thermal_expansion_per_k"] - STEEL_SHAFT_EXPANSION_PER_K)
        * HUB_BORE_DIAMETER_MM * delta_t
    )
    constrained_thermal_pa = e * material["thermal_expansion_per_k"] * delta_t

    analytical_mass = BLADE_COUNT * blade["mass_kg"] + ring_mass + hub_mass
    cad_mass = cad_volume_mm3 / 1.0e9 * rho if cad_volume_mm3 else None
    polar_inertia = (
        0.5 * ring_mass * (r_out**2 + r_in**2)
        + 0.5 * rim_mass * (ro**2 + r_rim_in**2)
        + 0.5 * web_mass * (r_rim_in**2 + r_boss**2)
        + 0.5 * boss_mass * (r_boss**2 + ri**2)
        + BLADE_COUNT * blade["radial_moment_kg_m"] * (ro + length / 2.0) * 1.1
    )
    results = {
        "cad_mass_g": cad_mass * 1000.0 if cad_mass is not None else None,
        "analytical_mass_g": analytical_mass * 1000.0,
        "single_blade_mass_g": blade["mass_kg"] * 1000.0,
        "shroud_mass_g": ring_mass * 1000.0,
        "overspeed_tip_speed_m_s": tip_speed_o,
        "shrouded": SHROUDED,
        "overspeed_shroud_hoop_stress_mpa": shroud_hoop_pa / 1.0e6 if SHROUDED else None,
        "yield_to_shroud_hoop_ratio": sy / shroud_hoop_pa if SHROUDED else None,
        "overspeed_blade_root_stress_blade_only_mpa": root_stress_blade_only / 1.0e6,
        "overspeed_blade_root_stress_worst_mpa": root_stress_with_ring / 1.0e6,
        "overspeed_blade_root_aero_bending_mpa": aero_bending_pa / 1.0e6,
        "yield_to_blade_root_ratio_worst_case": sy / root_stress_with_ring,
        "hub_mass_g": hub_mass * 1000.0,
        "overspeed_hub_rim_hoop_stress_mpa": rim_hoop / 1.0e6,
        "yield_to_hub_rim_ratio": sy / rim_hoop,
        "overspeed_hub_bore_hoop_stress_mpa": hub_bore_hoop / 1.0e6,
        "yield_to_hub_bore_ratio": sy / hub_bore_hoop,
        "blade_first_mode_cantilever_hz": cantilever_running,
        "blade_first_mode_clamped_by_shroud_hz": clamped_running,
        "spoke_order_hz": spoke_order_hz,
        "stator_order_hz": stator_order_hz,
        "governing_blade_mode_hz": governing_mode,
        "modal_separation_ratio": shrouded_separation,
        "cantilever_mode_below_spoke_order": cantilever_running < spoke_order_hz,
        "hub_bore_loosening_on_steel_shaft_mm": bore_loosening_mm,
        "fully_constrained_thermal_stress_mpa": constrained_thermal_pa / 1.0e6,
        "yield_to_constrained_thermal_ratio": sy / constrained_thermal_pa,
        "approximate_polar_inertia_kg_m2": polar_inertia,
        "overspeed_kinetic_energy_j": 0.5 * polar_inertia * omega_o**2,
    }
    centrifugal = [
        results["yield_to_blade_root_ratio_worst_case"],
        results["yield_to_hub_rim_ratio"],
        results["yield_to_hub_bore_ratio"],
    ]
    if SHROUDED:
        centrifugal.append(results["yield_to_shroud_hoop_ratio"])
    results["centrifugal_screen_pass"] = min(centrifugal) >= MINIMUM_SCREEN_RATIO
    results["modal_screen_pass"] = shrouded_separation >= MINIMUM_MODAL_SEPARATION_RATIO
    results["constrained_thermal_screen_pass"] = (
        results["yield_to_constrained_thermal_ratio"] >= MINIMUM_SCREEN_RATIO
    )
    return results


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

REBUILD_GENERATION = ROOT / "twins/993-engine-cooling-fan-system-f0/results/reference/generation.json"
FVD_ROTOR_MASS_KG = 0.9              # FVD commercial listing, material not stated (REFERENCE_REBUILD.md)


def rebuild_rotor_volume_mm3() -> float:
    record = json.loads(REBUILD_GENERATION.read_text(encoding="utf-8"))
    return next(p["volume_mm3"] for p in record["parts"] if p["part"] == "rotor")


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    design = design_f1_rotor()
    reference = design_reference_rotor()
    rotors = {REFERENCE: reference, F1_ROTOR: design, F1_STATOR: design}
    speed = SYNTHETIC_NOMINAL_SPEED_RPM
    points = {
        name: operating_point(rotors[name], speed, **cfg)
        for name, cfg in CONFIGURATIONS.items()
    }
    base = points[REFERENCE]
    comparison = {
        name: {
            "flow_gain_vs_rebuild": p["flow_m3_s"] / base["flow_m3_s"] - 1.0,
            "shaft_power_ratio_vs_rebuild": p["shaft_power_w"] / base["shaft_power_w"],
            # Q^3 * K = eta * P_shaft: flow each design would move on the rebuild's power.
            "flow_gain_at_equal_shaft_power_vs_rebuild": (p["efficiency"] / base["efficiency"]) ** (1.0 / 3.0) - 1.0,
        }
        for name, p in points.items()
    }
    for name, cfg in CONFIGURATIONS.items():
        onset = stall_flow(rotors[name], speed, **cfg)
        points[name]["stall_onset_flow_m3_s"] = onset
        points[name]["stall_margin"] = points[name]["flow_m3_s"] / onset - 1.0
    flows = [round(1.2 + 0.1 * i, 2) for i in range(22)]
    curves = {
        name: fan_curve(rotors[name], speed, flows, **cfg)
        for name, cfg in CONFIGURATIONS.items()
    }
    curves["system"] = [
        {"flow_m3_s": q, "useful_pressure_pa": system_coefficient() * q**2} for q in flows
    ]
    speed_sweep = [
        {
            "speed_rpm": rpm,
            "F1_rotor_flow_m3_s": operating_point(design, rpm, **CONFIGURATIONS[F1_ROTOR])["flow_m3_s"],
            "rebuild_flow_m3_s": operating_point(reference, rpm, **CONFIGURATIONS[REFERENCE])["flow_m3_s"],
        }
        for rpm in (3000.0, 6000.0, 8000.0, 10000.0, 12000.0)
    ]
    # Sensitivity: the duty and the rebuild's pitch are both inferred.
    k = system_coefficient()
    duty_sensitivity = []
    for factor in (0.6, 1.0, 1.6):
        row = {"resistance_factor": factor}
        for name in (REFERENCE, F1_ROTOR, F1_STATOR):
            q = _root(
                lambda x, n=name: factor * k * x**2
                - rotor_performance(rotors[n], x, speed, **CONFIGURATIONS[n])["useful_pressure_pa"],
                0.05, 8.0, 1.0e-9,
            )
            perf = rotor_performance(rotors[name], q, speed, **CONFIGURATIONS[name])
            row[name] = {"flow_m3_s": q, "efficiency": perf["efficiency"],
                         "shaft_power_w": perf["shaft_power_w"],
                         "stalled_station_count": perf["stalled_station_count"]}
        row["F1_flow_gain_at_equal_power"] = (
            row[F1_ROTOR]["efficiency"] / row[REFERENCE]["efficiency"]) ** (1.0 / 3.0) - 1.0
        duty_sensitivity.append(row)
    pitch_sensitivity = []
    for pitch in (43.0, 48.0, 53.0):
        ref = design_reference_rotor(pitch)
        perf = operating_point(ref, speed, **CONFIGURATIONS[REFERENCE])
        pitch_sensitivity.append({
            "rebuild_pitch_deg": pitch,
            "rebuild_flow_m3_s": perf["flow_m3_s"],
            "rebuild_efficiency": perf["efficiency"],
            "rebuild_stalled_station_count": perf["stalled_station_count"],
            "F1_flow_gain_vs_rebuild": points[F1_ROTOR]["flow_m3_s"] / perf["flow_m3_s"] - 1.0,
            "F1_flow_gain_at_equal_power_vs_rebuild": (
                points[F1_ROTOR]["efficiency"] / perf["efficiency"]) ** (1.0 / 3.0) - 1.0
            if perf["efficiency"] > 0.0 else None,
        })
    aero_load = {"shaft_power_w": points[F1_ROTOR]["shaft_power_w"],
                 "useful_pressure_pa": points[F1_ROTOR]["useful_pressure_pa"]}
    materials = {
        name: {**{k: v for k, v in m.items()},
               "results": structural_screen(design, m, cad_volume_mm3, aero_load)}
        for name, m in MATERIALS.items()
    }
    primary = materials[PRIMARY_MATERIAL]["results"]
    rebuild_volume = rebuild_rotor_volume_mm3()
    mass = {
        "rebuild_rotor_volume_mm3": rebuild_volume,
        "f1_cad_volume_mm3": cad_volume_mm3,
        "volume_ratio_f1_to_rebuild": cad_volume_mm3 / rebuild_volume if cad_volume_mm3 else None,
        "rebuild_mass_in_alsi10mg_g": rebuild_volume / 1.0e3 * 2.67,
        "rebuild_mass_in_we43_g": rebuild_volume / 1.0e3 * 1.84,
        "f1_mass_in_we43_g": cad_volume_mm3 / 1.0e3 * 1.84 if cad_volume_mm3 else None,
        "fvd_listed_original_mass_g": FVD_ROTOR_MASS_KG * 1000.0,
        "note": "the rebuild volume is a visual reconstruction; FVD's 0.9 kg listing (material not stated) implies 3.2 g/cm3 on it, so the rebuild probably under-represents the real rotor's material",
    }
    radial_clearance = (HOUSING_SYNTHETIC_THROAT_MM - OUTER_DIAMETER_MM) / 2.0
    integration = {
        "housing_part_id": HOUSING_PART_ID,
        "housing_synthetic_throat_mm": HOUSING_SYNTHETIC_THROAT_MM,
        "impeller_outer_diameter_mm": OUTER_DIAMETER_MM,
        "radial_clearance_mm": radial_clearance,
        "housing_fit_screen_pass": radial_clearance >= MINIMUM_SYNTHETIC_RADIAL_CLEARANCE_MM,
        "eos_m290_plate_mm": EOS_M290_PLATE_MM,
        "fits_eos_m290_flat": OUTER_DIAMETER_MM < EOS_M290_PLATE_MM,
        "cup_kept_from_rebuild": {
            "cup_outer_diameter_mm": HUB_OUTER_DIAMETER_MM,
            "cup_depth_mm": CUP_DEPTH_MM,
            "wall_mm": HUB_RIM_THICKNESS_MM,
            "web_mm": HUB_WEB_THICKNESS_MM,
            "bore_diameter_mm": HUB_BORE_DIAMETER_MM,
            "vent_count": VENT_COUNT,
            "bolt_holes": BOLT_COUNT,
        },
        "authority": "the rebuild's visual hypotheses; no measured interface",
    }
    stalled = {name: p["stalled_station_count"] for name, p in points.items()}
    aero_pass = (
        comparison[F1_ROTOR]["flow_gain_at_equal_shaft_power_vs_rebuild"] > 0.0
        and stalled[F1_ROTOR] == 0
        and min(s["de_haller_ratio"] for s in design["sections"]) >= 0.72
    )
    screen_pass = (
        aero_pass
        and integration["housing_fit_screen_pass"]
        and primary["centrifugal_screen_pass"]
        and primary["modal_screen_pass"]
    )
    return {
        "schema_version": "2.0.0",
        "part_id": PART_ID,
        "status": "f1_rebuild_based_impeller_mathematical_screen",
        "reference": {
            "rebuild_parameters": "twins/993-engine-cooling-fan-system-f0/source/picogk-reference/reference.json",
            "rebuild_report": "twins/993-engine-cooling-fan-system-f0/REFERENCE_REBUILD.md",
            "authority": "visual reconstruction of the Turbo rotor from FVD photographs; blade count and window count observed, other shape values are hypotheses",
            "superseded_f1_revision": "an earlier F1 (120 mm hub, shroud, 248 mm) was a generic fan derived from the synthetic F0; it did not keep the original cup or alternator space",
        },
        "design_intent": [
            "keep the rebuild's envelope and interfaces: 245 mm, 165 mm cup 56 mm deep, web, twelve windows, three bolt holes, bore",
            "eleven twisted, cambered airfoil blades from velocity triangles instead of constant-pitch cambered plates",
            "free vortex: even exit flow under radial equilibrium",
            "no shroud, like the original: blades remain open and printable from outside",
            "WE43 magnesium",
            "optional housing stator reported separately",
        ],
        "synthetic_cases": {
            "nominal_speed_rpm": speed,
            "overspeed_factor": SYNTHETIC_OVERSPEED_FACTOR,
            "system_curve": "dp = K Q^2 through the rebuild rotor's best-efficiency point in a bellmouth housing",
            "duty_flow_m3_s": SYNTHETIC_AIRFLOW_M3_S,
            "duty_pressure_pa": SYNTHETIC_PRESSURE_RISE_PA,
            "system_coefficient_pa_s2_m6": k,
            "air_temperature_c": SYNTHETIC_AIR_TEMPERATURE_C,
            "air_density_kg_m3": air_density(),
            "overspeed_tip_mach": angular_speed(speed * SYNTHETIC_OVERSPEED_FACTOR) * OUTER_DIAMETER_MM / 2000.0
            / math.sqrt(AIR_GAMMA * AIR_GAS_CONSTANT_J_KG_K * (SYNTHETIC_AIR_TEMPERATURE_C + 273.15)),
            "authority": "inferred from the rebuild's visual blade angles; no measured 993 speed, pulley ratio, fan map or engine resistance",
        },
        "rotor_design": design,
        "reference_rotor": reference,
        "aero_model": {
            "method": "equal-area blade-element streamline model with simple radial equilibrium behind the rotor",
            "radial_equilibrium": "(1/rho) dp0/dr = c_x dc_x/dr + (c_u/r) d(r c_u)/dr marched implicitly from the hub, mean axial velocity carries the flow; Lieblein terms use the local axial velocity ratio; the non-uniform exit profile is mixed out with a Borda-Carnot loss",
            "work": "Euler dp0 = rho U c_u2, no inlet swirl",
            "deviation": "Carter: delta = (0.23 + 0.002 kappa2) theta / sqrt(sigma)",
            "profile_loss": "Lieblein D_eq with incidence term; theta/c = 0.004/(1 - 1.17 ln D_eq); stall flag D_eq > 2.2; rebuild plates x 1.5",
            "tip_loss": "unshrouded: delta_eta = 2 tau/h with the 3.5 mm gap of a 245 mm rotor in the 252 mm throat, for both rotors",
            "swirl_loss": "exit swirl dynamic head lost unless a stator row recovers it",
            "inlet_loss": f"bellmouth K = {BELLMOUTH_INLET_LOSS_K} on axial dynamic head, for both rotors",
            "limits": "pure axial annulus from the cup to the tip; the alternator air through the cup windows, the housing spokes and the real inlet are not modelled; not CFD",
        },
        "operating_points": points,
        "comparison": comparison,
        "fan_curves": curves,
        "speed_sweep": speed_sweep,
        "duty_sensitivity": duty_sensitivity,
        "rebuild_pitch_sensitivity": pitch_sensitivity,
        "upstream_f0_integration": integration,
        "mass": mass,
        "material_screens": materials,
        "primary_material": PRIMARY_MATERIAL,
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "duty_flow_m3_s": SYNTHETIC_AIRFLOW_M3_S,
            "rebuild_flow_m3_s": base["flow_m3_s"],
            "f1_flow_m3_s": points[F1_ROTOR]["flow_m3_s"],
            "f1_flow_gain_vs_rebuild": comparison[F1_ROTOR]["flow_gain_vs_rebuild"],
            "f1_with_stator_flow_gain_vs_rebuild": comparison[F1_STATOR]["flow_gain_vs_rebuild"],
            "f1_flow_gain_at_equal_power_vs_rebuild": comparison[F1_ROTOR]["flow_gain_at_equal_shaft_power_vs_rebuild"],
            "f1_with_stator_flow_gain_at_equal_power_vs_rebuild": comparison[F1_STATOR]["flow_gain_at_equal_shaft_power_vs_rebuild"],
            "f1_minimum_de_haller_ratio": min(s["de_haller_ratio"] for s in design["sections"]),
            "f1_shaft_power_w": points[F1_ROTOR]["shaft_power_w"],
            "rebuild_shaft_power_w": base["shaft_power_w"],
            "stalled_stations": stalled,
            "stall_margins": {name: p["stall_margin"] for name, p in points.items()},
            "volume_ratio_f1_to_rebuild": mass["volume_ratio_f1_to_rebuild"],
            "aero_screen_pass": aero_pass,
            "housing_fit_screen_pass": integration["housing_fit_screen_pass"],
            "primary_material_centrifugal_screen_pass": primary["centrifugal_screen_pass"],
            "primary_material_modal_screen_pass": primary["modal_screen_pass"],
            "primary_material_constrained_thermal_screen_pass": primary["constrained_thermal_screen_pass"],
            "preliminary_screen_pass": screen_pass,
        },
        "dfam_screen": {
            "rotating_part": True,
            "enclosed_blade_passages": False,
            "orientation": "web on the plate, cup opening upward; blades are open from outside, so their downward faces can be supported and the supports reached",
            "orientation_selected": False,
            "magnesium_lpbf_notes": "WE43 LPBF is offered by few service bureaus; powder is reactive and needs an inert, Mg-rated machine",
            "corrosion_and_galvanic": "Mg needs a conversion or PEO coating and isolation from the steel bolts, the bearing hub and the aluminium housing",
            "hub_interface": "the separate bearing hub bolts to the web as in the rebuild; a Mg web on steel bolts needs inserts or washers sized for creep",
            "dynamic_balance_defined": False,
        },
        "interpretation": {
            "flow": "F1 keeps the rebuild's envelope and duty; its gains come from airfoil blades and matched loading only",
            "original_part": "the comparison is with the rebuild rotor, a visual reconstruction; no claim of gain over the Porsche part is made",
            "power": "more flow through the same engine costs more shaft power; the equal-power gain isolates what the blade design alone buys",
            "tip_gap": "the 3.5 mm tip gap of a 245 mm rotor in the 252 mm throat costs both rotors more than their blade profiles; closing it is a housing change",
            "stator": "a matched stator recovers the exit swirl, the largest gain left in this envelope",
            "dyson": "Coanda entrainment (bladeless fans) adds flow only in free air; against engine fin resistance it loses pressure",
        },
        "release_blockers": [
            "The rebuild geometry, the duty inferred from it and the engine resistance are not measured.",
            "The flow model is one-dimensional: no CFD, rig curve or measured fan map exists.",
            "No claim of gain over the Porsche part is made.",
            "WE43 values are published coupon or generic data: no hot, HCF or notched allowable.",
            "Alternator air through the cup windows is not modelled.",
            "No shaft, hub, pulley, alternator or housing interface is measured.",
            "No balance, overspeed, burst-containment, vibration or endurance test.",
            "No corrosion or galvanic protection qualified for magnesium on the engine.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def airfoil_points(chord: float, thickness: float, camber_deg: float,
                   stagger_deg: float, samples: int = 24
                   ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Upper and lower surfaces, leading to trailing edge, in unwrapped
    (tangential s, axial z) coordinates: circular-arc camber line with NACA
    4-digit thickness, centred on mid-chord. Leading edge upstream (low z),
    turned toward -s (against rotation)."""
    theta = math.radians(max(camber_deg, 0.5))
    radius = chord / (2.0 * math.sin(theta / 2.0))
    t = thickness / chord
    xi = math.radians(stagger_deg)
    d = (-math.sin(xi), math.cos(xi))
    n = (-math.cos(xi), -math.sin(xi))
    upper, lower = [], []
    for i in range(samples + 1):
        beta = math.pi * i / samples
        xn = (1.0 - math.cos(beta)) / 2.0
        x = xn * chord
        yc = math.sqrt(max(radius**2 - (x - chord / 2.0) ** 2, 0.0)) - radius * math.cos(theta / 2.0)
        slope = -(x - chord / 2.0) / math.sqrt(max(radius**2 - (x - chord / 2.0) ** 2, 1e-12))
        phi = math.atan(slope)
        yt = 5.0 * t * chord * (
            0.2969 * math.sqrt(xn) - 0.1260 * xn - 0.3516 * xn**2 + 0.2843 * xn**3 - 0.1015 * xn**4
        )
        upper.append((x - yt * math.sin(phi), yc + yt * math.cos(phi)))
        lower.append((x + yt * math.sin(phi), yc - yt * math.cos(phi)))

    def frame(pts):
        return [((x - chord / 2.0) * d[0] + y * n[0], (x - chord / 2.0) * d[1] + y * n[1]) for x, y in pts]

    return frame(upper), frame(lower)


def geometry_sections(design: dict[str, object]) -> list[dict[str, float]]:
    """Loft sections: a planar cap buried in the cup rim, wrapped aero
    sections, and the tip section; with a shroud, a planar cap buried in it."""
    secs = design["sections"]
    first, last = dict(secs[0]), dict(secs[-1])
    first["radius_mm"] = design["hub_radius_mm"] - HUB_RIM_THICKNESS_MM / 2.0   # inside the cup rim
    first["planar"] = True
    if not SHROUDED:
        # Planar cap past the tip; build_geometry trims it to the tip circle.
        last["radius_mm"] = design["tip_radius_mm"] + 2.0
        last["planar"] = True
        return [first] + secs[1:-1:2] + [secs[-1], last]
    last["radius_mm"] = design["tip_radius_mm"] + 1.3
    last["planar"] = True
    return [first] + secs[1:-1:2] + [secs[-1], last]


def section_wire(section: dict[str, float], z_mid: float):
    from build123d import Edge, Vector, Wire

    r = section["radius_mm"]
    upper, lower = airfoil_points(
        section["chord_mm"], section["thickness_mm"], section["camber_deg"], section["stagger_deg"]
    )

    def place(pts):
        if section.get("planar"):
            return [Vector(r, ps, z_mid + pz) for ps, pz in pts]
        return [Vector(r * math.cos(ps / r), r * math.sin(ps / r), z_mid + pz) for ps, pz in pts]

    up, low = place(upper), place(lower)
    return Wire([
        Edge.make_spline(up),
        Edge.make_line(up[-1], low[-1]),
        Edge.make_spline(low[::-1]),
    ])


def build_geometry():
    from build123d import Align, Axis, Box, Cylinder, Pos, Rot, Solid, fillet

    design = design_f1_rotor()
    centered_min = (Align.CENTER, Align.CENTER, Align.MIN)
    # The rebuild's cup, kept as the alternator space and the interface: rim
    # under the blade roots, web on the plate face (z = 0, printed without
    # supports), twelve windows, three bolt holes and the bore. The rebuild's
    # ribs between the windows and its rounded web transition are not
    # reproduced.
    rim_inner = HUB_OUTER_DIAMETER_MM / 2.0 - HUB_RIM_THICKNESS_MM
    body = Cylinder(HUB_OUTER_DIAMETER_MM / 2.0, CUP_DEPTH_MM, align=centered_min) - Pos(
        0.0, 0.0, HUB_WEB_THICKNESS_MM
    ) * Cylinder(rim_inner, CUP_DEPTH_MM, align=centered_min)
    body = body - Pos(0.0, 0.0, -1.0) * Cylinder(
        HUB_BORE_DIAMETER_MM / 2.0, HUB_WEB_THICKNESS_MM + 2.0, align=centered_min
    )
    window = Box(2.0 * VENT_RADIAL_HALFWIDTH_MM, 2.0 * VENT_TANGENTIAL_HALFWIDTH_MM,
                 HUB_WEB_THICKNESS_MM + 2.0, align=centered_min)
    window = fillet(window.edges().filter_by(Axis.Z), 2.5)
    for index in range(VENT_COUNT):
        body = body - Rot(0.0, 0.0, index * 360.0 / VENT_COUNT) * Pos(VENT_RADIUS_MM, 0.0, -1.0) * window
    hole = Cylinder(BOLT_HOLE_RADIUS_MM, HUB_WEB_THICKNESS_MM + 2.0, align=centered_min)
    for index in range(BOLT_COUNT):
        body = body - Rot(0.0, 0.0, index * 360.0 / BOLT_COUNT) * Pos(
            BOLT_CIRCLE_RADIUS_MM, 0.0, -1.0) * hole

    z_mid = CUP_DEPTH_MM / 2.0
    blade = Solid.make_loft([section_wire(s, z_mid) for s in geometry_sections(design)])
    if not SHROUDED:
        blade = blade & Pos(0.0, 0.0, -10.0) * Cylinder(
            design["tip_radius_mm"], CUP_DEPTH_MM + 20.0, align=centered_min)
    if not blade.is_valid:
        raise SystemExit("The lofted F1 blade is not a valid solid.")
    for index in range(BLADE_COUNT):
        body = body + Rot(0.0, 0.0, index * 360.0 / BLADE_COUNT) * blade
    return body


def plot_curves(report: dict[str, object], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = {
        REFERENCE: "rebuild of the original rotor (reference)",
        F1_ROTOR: "F1 rotor, same housing",
        F1_STATOR: "F1 + matched stator",
        "system": "engine resistance K·Q² inferred from the rebuild",
    }
    styles = {
        REFERENCE: ("#7a7a7a", "-"),
        F1_ROTOR: ("#1f6fb2", "-"),
        F1_STATOR: ("#2e8b57", "-"),
        "system": ("#b03a2e", "--"),
    }
    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    for name, pts in report["fan_curves"].items():
        valid = [p for p in pts if p["useful_pressure_pa"] > 0.0 and not p.get("stalled_station_count")]
        q = [p["flow_m3_s"] for p in valid]
        dp = [p["useful_pressure_pa"] for p in valid]
        color, ls = styles[name]
        ax.plot(q, dp, ls, color=color, label=labels[name], lw=2)
    for name, p in report["operating_points"].items():
        ax.plot(p["flow_m3_s"], p["system_pressure_pa"], "o", color=styles[name][0])
        ax.annotate(f"{p['flow_m3_s']:.2f} m³/s", (p["flow_m3_s"], p["system_pressure_pa"]),
                    textcoords="offset points", xytext=(6, -12), fontsize=8, color=styles[name][0])
    ax.text(0.01, 0.02, "curves stop where the model predicts blade stall (D_eq > 2.2); left of that it is not valid",
            transform=ax.transAxes, fontsize=7, color="#555555")
    ax.set_xlabel("air flow (m³/s)")
    ax.set_ylabel("useful pressure rise (Pa)")
    ax.set_title("F1 vs rebuild rotor, 1D blade-element model at 10,000 rpm — inferred duty, not measured", fontsize=10)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)


def step_volume_tolerance_mm3(volume_mm3: float) -> float:
    """STEP re-read tolerance: 0.05 mm3, or one part per million of the
    volume when larger (curved lofts re-integrate a few tenths of a mm3 apart)."""
    return max(0.05, 1.0e-6 * volume_mm3)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--stl", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--plot", type=Path)
    args = parser.parse_args()

    cad_volume_mm3 = None
    envelope = None
    if args.out:
        from build123d import export_step, export_stl, import_step

        shape = build_geometry()
        if not shape.is_valid or len(shape.solids()) != 1:
            raise SystemExit("The F1 impeller must be one valid BREP solid.")
        bbox = shape.bounding_box()
        envelope = [bbox.size.X, bbox.size.Y, bbox.size.Z]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(shape, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 1:
            raise SystemExit("The re-read STEP does not keep the valid solid.")
        if abs(roundtrip.volume - shape.volume) > step_volume_tolerance_mm3(shape.volume):
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
            "semantic_solids": ["rebuild_based_cooling_impeller_f1"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "blade_count": BLADE_COUNT,
            "loft_sections_per_blade": len(geometry_sections(design_f1_rotor())),
            "labyrinth_tooth_count": LABYRINTH_TOOTH_COUNT,
            "maximum_volume_delta_mm3": step_volume_tolerance_mm3(cad_volume_mm3),
        }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.plot:
        plot_curves(report, args.plot)
    print(json.dumps(report["results"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
