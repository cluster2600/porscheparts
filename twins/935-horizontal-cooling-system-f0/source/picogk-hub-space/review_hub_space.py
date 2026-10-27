"""Independent FCL surface review of a conditional PicoGK 935 hub-space mesh."""

import json
import math
from pathlib import Path
import sys
import time

import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_surface_contacts import fixtures, load, query, sha  # noqa: E402

ROTOR_SHA256 = "5522ec1af957a4523244bc2b2f05ff902b52eb882e1cb3b2ef88b093ffb598eb"
DRIVE_SHA256 = "fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35"


def run(native: Path, assembly: Path, target: Path) -> None:
    native, assembly, target = native.resolve(), assembly.resolve(), target.resolve()
    if target.exists() or not target.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ report")
    hub_receipt = json.loads((native / "receipt.json").read_text())
    assembly_receipt = json.loads((assembly / "receipt.json").read_text())
    if (hub_receipt["status"] != "visual_hub_space_hypothesis_not_a_coupling"
            or hub_receipt["scale_verified"] or hub_receipt["functional_component"]
            or hub_receipt["rotor_sha256"] != ROTOR_SHA256
            or hub_receipt["drive_sha256"] != DRIVE_SHA256
            or sha(native / "hub-space-hypothesis.stl") != hub_receipt["mesh_sha256"]):
        raise ValueError("PicoGK hub-space input invalid")
    components = {row["id"]: row for row in assembly_receipt["components"]}
    expected = {"rotor_candidate": ROTOR_SHA256, "drive_observed": DRIVE_SHA256}
    for name, digest in expected.items():
        if components[name]["sha256"] != digest or sha(assembly / components[name]["file"]) != digest:
            raise ValueError(f"Pinned {name} changed")
    controls = fixtures()
    start = time.monotonic()
    mesh = trimesh.load_mesh(native / "hub-space-hypothesis.stl", process=True)
    inner, outer = hub_receipt["inner_radius_mm_hypothesis"], hub_receipt["outer_radius_mm_hypothesis"]
    z_min, z_max = hub_receipt["axial_span_mm_hypothesis"]
    analytic_volume = math.pi * (outer * outer - inner * inner) * (z_max - z_min)
    shape = {"watertight": bool(mesh.is_watertight),
             "winding_consistent": bool(mesh.is_winding_consistent),
             "euler_number": int(mesh.euler_number),
             "mesh_volume_mm3_hypothesis": float(mesh.volume),
             "analytic_volume_mm3_hypothesis": analytic_volume,
             "relative_volume_difference": float(mesh.volume / analytic_volume - 1)}
    if (not shape["watertight"] or not shape["winding_consistent"]
            or shape["euler_number"] != 0 or abs(shape["relative_volume_difference"]) >= .01):
        raise ValueError("PicoGK visual envelope fails independent shape checks")
    hub = load(native / "hub-space-hypothesis.stl", hub_receipt["triangles"])
    pairs = []
    for name in ("drive_observed", "rotor_candidate"):
        row = components[name]
        result = query(hub, load(assembly / row["file"], row["triangles"]))
        pairs.append({"component": name, "sha256": row["sha256"], **result})
        print(name, result, flush=True)
    report = {"status": "conditional_hub_space_surface_review",
              "hub_receipt_sha256": sha(native / "receipt.json"),
              "assembly_receipt_sha256": sha(assembly / "receipt.json"),
              "fixtures": controls, "shape": shape, "pairs": pairs,
              "observed_surface_clearance_pass": all(not row["surface_crossing"] for row in pairs),
              "elapsed_s": time.monotonic() - start,
              "source_unit_to_mm_verified": False, "solid_containment_checked": False,
              "fit_verified": False, "torque_path_defined": False,
              "manufacturing_authorized": False}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    print("report_sha256", sha(target))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: review_hub_space.py NATIVE_OUTPUT ASSEMBLY_OUTPUT NEW_PRIVATE_JSON")
    run(*(Path(arg) for arg in sys.argv[1:]))
