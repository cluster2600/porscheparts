"""Replace annulus inertia with pinned corrected-rotor inertia in a hypothesis screen."""

import hashlib
import json
import math
import sys
from pathlib import Path


OLD_SHA256 = "07d73cb349cc68825f18fcd167aba17a4dca3dee98963b4122c22c6ad99e5db4"
ROTOR_SHA256 = "e433e4fc6b8ef81f48f6e8edfac237884a689604bc1fde2ff335077f553446cf"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(old_path, rotor_path, output_path):
    output = Path(output_path).resolve()
    if not output.is_relative_to((Path.cwd() / "work").resolve()) or output.exists():
        raise ValueError("A new private work/ output is required")
    if sha(old_path) != OLD_SHA256 or sha(rotor_path) != ROTOR_SHA256:
        raise ValueError("Input hash mismatch")
    old = json.loads(Path(old_path).read_text())
    rotor = json.loads(Path(rotor_path).read_text())
    if old["status"] != "completed_hypothesis_tests" or rotor["status"] != "conditional_rotor_inertial_screen_only":
        raise ValueError("Unexpected input scope")
    assumptions = old["assumptions"]
    gear_diameter = assumptions["gear_pitch_diameter_m"]
    shaft_diameter = assumptions["shaft_diameter_m"]
    if gear_diameter <= 0 or shaft_diameter <= 0:
        raise ValueError("Invalid assumed transmission geometry")
    geometry = {card["id"]: card for card in rotor["materials"]}
    if len(geometry) != 10 or len(old["system_screen"]) != 160:
        raise ValueError("Unexpected case family")

    rows = []
    for case in old["system_screen"]:
        card = geometry[case["material"]]
        operating = next(row for row in card["operating_at_1mm_per_source_unit"]
                         if row["rotor_rpm_hypothesis"] == case["rpm"])
        stop = str(case["stop_time_s"])
        inertial = operating["stop_torque_Nm"][stop]
        assumed_fan = case["models"]["steady_drive_budget"]["steady_fan_torque_nm"]
        old_inertial = abs(case["models"]["inertia_and_unbalance"]["rotor_acceleration_torque_nm"])
        if not math.isclose(case["torque_magnitude_sum_nm"], old_inertial + assumed_fan, rel_tol=1e-12):
            raise ValueError("Old case torque accounting changed")
        torque = inertial + assumed_fan
        rows.append({"id": case["id"], "material": case["material"],
                     "rotor_rpm_hypothesis": case["rpm"],
                     "stop_time_s_hypothesis": case["stop_time_s"],
                     "network_resistance_multiplier_hypothesis": case["resistance_multiplier"],
                     "old_annulus_mass_kg": case["assumed_mass_kg"],
                     "corrected_rotor_mass_kg": card["scale_cases"][1]["mass_kg"],
                     "old_inertial_torque_Nm": old_inertial,
                     "corrected_rotor_inertial_torque_Nm": inertial,
                     "retained_assumed_fan_torque_Nm": assumed_fan,
                     "updated_magnitude_torque_Nm": torque,
                     "updated_gear_tangential_force_N": 2 * torque / gear_diameter,
                     "updated_solid_shaft_torsion_MPa": 16 * torque / (math.pi * shaft_diameter**3) / 1e6})

    if len({row["id"] for row in rows}) != 160:
        raise ValueError("Duplicate or missing case")
    report = {"status": "conditional_drive_load_rebase_not_mechanical_qualification",
              "old_hypothesis_sha256": OLD_SHA256, "corrected_rotor_screen_sha256": ROTOR_SHA256,
              "case_count": len(rows), "assumed_gear_pitch_diameter_m": gear_diameter,
              "assumed_solid_shaft_diameter_m": shaft_diameter,
              "scale_verified": False, "gear_and_shaft_dimensions_verified": False,
              "fan_torque_measured": False, "material_allowables_verified": False,
              "safe_speed_established": False, "full_system_validated": False,
              "cases": rows}
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "case_count": len(rows),
                      "output_sha256": sha(output)}), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: rebase_root0p7_drive_loads.py OLD_HYPOTHESIS_JSON ROTOR_SCREEN_JSON NEW_PRIVATE_JSON")
    main(*sys.argv[1:])
