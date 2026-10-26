"""Screen conditional rotor mass and inertial drive loads from the pinned surface."""

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh


ROTOR_SHA256 = "5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a"
CARDS_SHA256 = "f5b9dea9663b092541f77cb4485e8e3fbcaa6a3797c07ab31f7538401ee3fdd2"
RPM_CASES = (3000, 6000, 8500, 11000)
STOP_SECONDS = (0.1, 1.0)
SCALE_CASES_MM_PER_SOURCE_UNIT = (0.8, 1.0, 1.2)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(rotor_path, cards_path, output_path):
    output = Path(output_path).resolve()
    if not output.is_relative_to((Path.cwd() / "work").resolve()) or output.exists():
        raise ValueError("A new private work/ output is required")
    if sha(rotor_path) != ROTOR_SHA256 or sha(cards_path) != CARDS_SHA256:
        raise ValueError("Input hash mismatch")

    box = trimesh.creation.box(extents=(2, 3, 4))
    assert abs(box.volume - 24) < 1e-12
    assert abs(box.moment_inertia[2, 2] - 26) < 1e-12
    mesh = trimesh.load_mesh(rotor_path, process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError("A closed, outward-oriented rotor is required")
    volume_source3 = float(mesh.volume)
    centre = np.asarray(mesh.center_mass)
    polar_source5 = float(mesh.moment_inertia[2, 2] + mesh.volume * np.dot(centre[:2], centre[:2]))
    if not np.isfinite(polar_source5) or polar_source5 <= 0:
        raise ValueError("Invalid polar inertia")

    cards = json.loads(Path(cards_path).read_text())["materials"]
    if len(cards) != 10 or len({card["id"] for card in cards}) != 10:
        raise ValueError("Unexpected material-card set")
    materials = []
    for card in cards:
        density = float(card["density_g_cm3"])
        if not math.isfinite(density) or density <= 0:
            raise ValueError("Invalid density")
        scale_cases = []
        for scale in SCALE_CASES_MM_PER_SOURCE_UNIT:
            mass = density * volume_source3 * scale**3 * 1e-6
            polar = density * 1000 * polar_source5 * (scale * .001)**5
            scale_cases.append({"mm_per_source_unit": scale, "mass_kg": mass,
                                "polar_inertia_kg_m2": polar})
        inertia = scale_cases[1]["polar_inertia_kg_m2"]
        operating = []
        for rpm in RPM_CASES:
            omega = rpm * 2 * math.pi / 60
            operating.append({"rotor_rpm_hypothesis": rpm,
                              "kinetic_energy_J": .5 * inertia * omega**2,
                              "stop_torque_Nm": {str(stop): inertia * omega / stop
                                                 for stop in STOP_SECONDS}})
        materials.append({"id": card["id"], "density_g_cm3": density,
                          "density_card_scope": card["card_scope"],
                          "scale_cases": scale_cases,
                          "operating_at_1mm_per_source_unit": operating})

    result = {"status": "conditional_rotor_inertial_screen_only",
              "rotor_sha256": ROTOR_SHA256, "material_cards_sha256": CARDS_SHA256,
              "rotor_faces": len(mesh.faces), "volume_source_units_cubed": volume_source3,
              "centre_of_mass_source_units": centre.tolist(),
              "polar_volume_inertia_about_origin_source_units_to_fifth": polar_source5,
              "axis": "candidate Z axis through source origin; not a verified shaft datum",
              "scale_verified": False, "rpm_verified": False,
              "uniform_density_solid_assumed": True,
              "mass_scale_exponent": 3, "inertia_scale_exponent": 5,
              "material_strength_or_fatigue_qualified": False,
              "safe_speed_established": False, "full_assembly_loads_established": False,
              "materials": materials}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "rotor_faces": len(mesh.faces),
                      "materials": len(materials), "output_sha256": sha(output)}), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: screen_root0p7_rotor_dynamics.py PINNED_ROTOR_OFF PINNED_MATERIALS_JSON NEW_PRIVATE_JSON")
    main(*sys.argv[1:])
