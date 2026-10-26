"""Conditional annular-body screen for the unresolved 935 output/hub gap."""

import hashlib
import json
import math
from pathlib import Path
import sys


HUB_SHA256 = "b45d4eab6d6a6d8ac89035bbf8d23d0f9fb3b110a9fc1a479e2e46430bd8a660"
LOAD_SHA256 = "dbc3a4e68aea7b47c6a34019f3ab400aa5ff981f84fab56ce42675e03c20d8f1"
ROTOR_SHA256 = "e433e4fc6b8ef81f48f6e8edfac237884a689604bc1fde2ff335077f553446cf"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(hub_path, loads_path, rotor_path, output_path):
    output = Path(output_path).resolve()
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("A fresh private work/ report is required")
    if (digest(hub_path), digest(loads_path), digest(rotor_path)) != (HUB_SHA256, LOAD_SHA256, ROTOR_SHA256):
        raise ValueError("Input hash mismatch")
    hub = json.loads(Path(hub_path).read_text())
    loads = json.loads(Path(loads_path).read_text())
    rotor = json.loads(Path(rotor_path).read_text())
    if (hub["shaft_hub_fit_verified"] or loads["scale_verified"] or
            loads["case_count"] != 160 or len(rotor["materials"]) != 10):
        raise ValueError("Unexpected input scope")
    points = hub["nearest_points_rotor_then_drive_source_units"]
    outer = math.hypot(*points[0][:2]) * 1e-3
    inner = math.hypot(*points[1][:2]) * 1e-3
    length = 20e-3  # shortcut: four observed axial bands span -20..0; replace after shaft identification.
    if not 0 < inner < outer or any(abs(p[2] - points[0][2]) > 1e-6 for p in points):
        raise ValueError("Nearest points do not define the expected radial gap")
    polar = math.pi * (outer**4 - inner**4) / 2
    volume = math.pi * (outer**2 - inner**2) * length
    cards = {card["id"]: card for card in rotor["materials"]}
    if len(cards) != 10:
        raise ValueError("Duplicate material card")
    cases = []
    for case in loads["cases"]:
        card = cards[case["material"]]
        cases.append({"id": case["id"], "material": case["material"],
                      "rotor_rpm_hypothesis": case["rotor_rpm_hypothesis"],
                      "stop_time_s_hypothesis": case["stop_time_s_hypothesis"],
                      "network_resistance_multiplier_hypothesis": case["network_resistance_multiplier_hypothesis"],
                      "body_mass_kg_if_same_material": volume * card["density_g_cm3"] * 1000,
                      "retained_hypothetical_torque_Nm": case["updated_magnitude_torque_Nm"],
                      "ideal_annulus_outer_nominal_shear_MPa": case["updated_magnitude_torque_Nm"] * outer / polar / 1e6})
    if len(cases) != 160 or len({case["id"] for case in cases}) != 160:
        raise ValueError("Incomplete load family")
    result = {"status": "hypothetical_annular_body_screen_no_coupling_design",
              "hub_metrology_sha256": HUB_SHA256, "drive_loads_sha256": LOAD_SHA256,
              "rotor_material_screen_sha256": ROTOR_SHA256,
              "assumed_mm_per_source_unit": 1.0, "observed_axial_band_span_source_units": [-20, 0],
              "inner_radius_from_one_drive_nearest_point_mm_hypothesis": inner * 1000,
              "outer_radius_from_one_rotor_nearest_point_mm_hypothesis": outer * 1000,
              "ideal_annulus_volume_cm3": volume * 1e6,
              "ideal_annulus_polar_section_m4": polar,
              "case_count": len(cases), "cases": cases,
              "full_shaft_circumference_observed": False,
              "shaft_identity_and_axis_verified": False, "fit_or_axial_retention_defined": False,
              "torque_transfer_mechanism_defined": False, "stress_concentration_checked": False,
              "temperature_and_fatigue_checked": False, "scale_verified": False,
              "strength_or_safe_speed_qualified": False, "manufacturing_authorized": False}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "cases": len(cases), "sha256": digest(output)}))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: screen_hub_annulus.py HUB_METROLOGY LOAD_SCREEN ROTOR_MATERIAL_SCREEN NEW_PRIVATE_JSON")
    run(*sys.argv[1:])
