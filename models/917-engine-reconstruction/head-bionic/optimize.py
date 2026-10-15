"""Bounded packing and cam-law optimization; no material or operating qualification."""
import importlib.util
import itertools
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("bionic_valvetrain", ROOT / "twins/m64-cylinder-head/source/valvetrain/valvetrain.py")
VT = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = VT
spec.loader.exec_module(VT)


def packing():
    rows = []
    for intake, exhaust, x, y in itertools.product(range(30, 35), range(25, 30), (18, 18.25, 18.5, 18.75, 19), (17, 17.25, 17.5, 17.75, 18)):
        ri, re = intake / 2 + 1.5, exhaust / 2 + 1.5
        ligament = min(2*x-2*ri, 2*x-2*re, 2*y-ri-re)
        bore_margin = 42.5 - math.hypot(x, y) - max(intake, exhaust) / 2
        rows.append({"intake_mm": intake, "exhaust_mm": exhaust, "x_mm": x, "y_mm": y,
                     "seat_ligament_mm": ligament, "conservative_bore_margin_mm": bore_margin,
                     "face_area_mm2": math.pi/2*(intake**2+exhaust**2), "passed": ligament >= 2 and bore_margin >= 1.5})
    feasible = [r for r in rows if r["passed"]]
    if not feasible:
        raise ValueError("No feasible valve packing")
    selected = max(feasible, key=lambda r: (r["face_area_mm2"], r["seat_ligament_mm"], r["conservative_bore_margin_mm"]))
    return selected, rows


def law_parameters(role, lift, duration, centre):
    p = VT.default_valve(role)
    for name, value in {"max_lift_mm": lift, "main_event_duration_crank_deg": duration,
                        "centreline_crank_deg": centre,"spring_installed_length_mm":44,
                        "spring_wire_diameter_mm":4,"lash_cold_mm":.1}.items():
        p[name] = VT.P(value, p[name]["unit"], "assumed", "Bounded 917 design search, not factory timing")
    return p


def timing(layout, roof_mm=10, rpm=8000):
    import numpy as np
    phi = np.linspace(0, 4*math.pi, 2881)
    alpha = math.radians(8)
    face_z = roof_mm - layout["y_mm"]*math.tan(alpha) - 2.6/math.cos(alpha)
    result, campaigns = {}, {}
    for role, diameter, centres, lifts in (("intake", layout["intake_mm"], (100,105,110,115,120), (9.5,10.5,11.5)),
                                          ("exhaust", layout["exhaust_mm"], (600,605,610,615,620), (8,9,10))):
        rows = []
        for lift, duration, centre in itertools.product(lifts, (220,230,240), centres):
            p = law_parameters(role, lift, duration, centre)
            law = VT.CamLaw.from_params(p)
            motion = law.valve_lift(phi)*1000
            closed = face_z - diameter/2*math.sin(alpha) + 2
            gaps = closed + VT.piston_drop(phi,.066,.132)*1000 - motion*math.cos(alpha)
            poly = VT.main_poly(law.c).deriv(1)
            roots = poly.deriv().roots()
            critical = [-1,1] + [float(z.real) for z in roots if abs(z.imag)<1e-9 and -1<=z.real<=1]
            lift_derivative_bound = law.max_lift_m*1000*max(abs(poly(u)) for u in critical)/(law.main_duration_rad/2)
            lift_derivative_bound += law.ramp_height_m*1000*1.875/law.ramp_duration_rad
            piston_derivative_bound = 33 + 33**2/(2*math.sqrt(132**2-33**2))
            interval_allowance = (piston_derivative_bound + lift_derivative_bound*math.cos(alpha))*math.radians(.25)/2
            lower_bound = float(gaps.min()-interval_allowance)
            kin=law.valve_kinematics(phi,rpm);negative=kin["acceleration_m_s2"]<0
            gas_force=math.pi*diameter**2/4*.2
            for preload in (300,350,400,450,500,550):
                p["spring_preload_N"]=VT.P(preload,"N","assumed","Bounded spring search; grade and fatigue unqualified")
                spring = VT.spring_properties(p, VT.default_parameters()["engine"])
                # shortcut: rigid tracking and a 0.11 kg mass ceiling; replace by measured dynamics and hot material data.
                force=spring["preload_N"]+spring["rate_N_m"]*kin["lift_m"][negative]-gas_force
                margin=float(np.min(force/(-.11*kin["acceleration_m_s2"][negative])))
                rows.append({"max_lift_mm":lift,"main_duration_deg":duration,"centreline_deg":centre,
                             "spring_preload_N":preload,"assumed_adverse_pressure_bar":2,
                             "sample_min_gap_mm":float(gaps.min()),"continuous_ideal_plane_gap_lower_bound_mm":lower_bound,
                             "quasistatic_outer_spring_margin_assumed_mass_kg_0_11":margin,
                             "coil_bind_gap_mm":spring["coil_bind_clearance_m"]*1000,
                             "max_spring_shear_stress_MPa_unqualified":spring["shear_stress_max_lift_MPa"],
                             "integrated_curtain_area_mm2_deg":float(np.trapezoid(math.pi*diameter*motion,np.degrees(phi))),
                             "passed":lower_bound>=2 and margin>=1.25 and spring["coil_bind_ok"]})
        feasible=[r for r in rows if r["passed"]]
        if not feasible:
            raise ValueError("No feasible assumed timing: " + role)
        result[role]=max(feasible,key=lambda r:(round(r["integrated_curtain_area_mm2_deg"],6),-r["max_spring_shear_stress_MPa_unqualified"],r["continuous_ideal_plane_gap_lower_bound_mm"]))
        campaigns[role]=rows
    return {"face_z_mm":face_z,"rpm_case":rpm,"roles":result,
            "scope":"conservative_continuous_ideal_rigid_axial_plane_bound_not_hot_or_follower_validation"}, campaigns
