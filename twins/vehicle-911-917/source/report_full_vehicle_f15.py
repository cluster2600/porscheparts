#!/usr/bin/env python3
"""Verify native F15 exports and arrange their unretouched views for review."""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from annotate_picogk_visualization_f11 import cropped_capture, font, sha256
from prepare_picogk_alignment_f13 import validate_alignment

ROOT = Path(__file__).resolve().parents[3]
TWIN = ROOT / "twins/vehicle-911-917"
REQUIRED_COMPONENTS = {
    "body_shell", "front_glazing", "floor", "firewall", "rear_structure_corridors",
    "front_structure_corridors", "engine_service_envelope", "engine_topology_proxy",
    "transaxle_schematic", "rear_halfshafts", "wheels_and_hubs", "wheel_motion_keepouts",
    "seat_left", "seat_right", "turbo_left", "turbo_right", "quarter_intake_left",
    "quarter_intake_right", "exhaust_left", "exhaust_right", "tail_cooling_duct_left",
    "tail_cooling_duct_right", "steering_reservations", "dashboard", "tail_plenum",
    "tail_heat_exchanger", "fixed_930_style_tail", "front_and_rear_lighting",
    *{f"{axle}_brake_{side}" for axle in ("front", "rear") for side in ("left", "right")},
    *{f"{part}_{axle}_{side}" for part in ("suspension_corridor", "spring_damper_reservation")
      for axle in ("front", "rear") for side in ("left", "right")},
    "fuel_cell", "battery", "oil_tank", "charge_cooler_left", "charge_cooler_right",
    "pedal_box", "electrical_controls",
}
VIEWS = {"exterior": "Integrated exterior", "side": "Side elevation", "top": "Mechanical plan",
         "mechanical": "Body removed", "section": "Longitudinal half-section", "rear": "Rear elevation"}
REQUIRED_CHECKS = {
    "engine_service_envelope__floor", "engine_service_envelope__firewall",
    "engine_service_envelope__rear_structure_corridors", "rear_halfshafts__rear_structure_corridors",
    "transaxle_schematic__rear_structure_corridors", "transaxle_schematic__floor",
    "wheel_motion_keepouts__rear_structure_corridors", "wheel_motion_keepouts__front_structure_corridors",
    "wheel_motion_keepouts__floor", "seat_left__firewall", "seat_right__firewall",
    "exhaust_left__rear_structure_corridors", "exhaust_right__rear_structure_corridors",
    "quarter_intake_left__firewall", "quarter_intake_right__firewall",
    "fuel_cell__steering_reservations", "oil_tank__transaxle_schematic",
    "engine_service_envelope__body_shell", "transaxle_schematic__body_shell",
    "quarter_intake_left__body_shell", "quarter_intake_right__body_shell",
    "tail_cooling_duct_left__body_shell", "tail_cooling_duct_right__body_shell",
    "engine_20mm_plus_numerical_guard__floor", "engine_20mm_plus_numerical_guard__body_shell",
    "engine_50mm_plus_numerical_guard__firewall",
}


def validate_private_scan(report):
    """The F15 record of the scan: unpromoted, bound to its F13 receipt, with exported bounds that agree with it."""
    scan = report["private_scan"]
    if (set(scan) != {"scan_sha256", "alignment_sha256", "scale_verified", "physical_datum_verified", "alignment"}
            or scan["scale_verified"] is not False or scan["physical_datum_verified"] is not False):
        raise ValueError("Private scan record incomplete or promoted")
    receipt = scan["alignment"]
    if type(receipt) is not dict or receipt.get("input_stl_sha256") != scan["scan_sha256"]:
        raise ValueError("Not the F13 alignment receipt of this scan")
    lo, hi = receipt.get("bounds_min_mm"), receipt.get("bounds_max_mm")
    part = next(p["properties"] for p in report["components"] if p["id"] == "private_engine_scan")
    # The exported scan is a half-voxel shell on voxel bounds, so allow two voxels around the receipt's mesh bounds.
    tolerance = 2 * report["voxel_size_mm"]
    if (type(lo) is not list or type(hi) is not list or len(lo) != 3 or len(hi) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in lo + hi)
            or any(abs(a - b) > tolerance for a, b in zip(lo + hi, part["bounds_min_mm"] + part["bounds_max_mm"]))):
        raise ValueError("Private scan bounds differ from its F13 receipt")


def validate_scope(report, config):
    if report.get("phase") != "F15" or report.get("status") != "produced_packaging_study_not_accepted_vehicle":
        raise ValueError("Not an F15 packaging result")
    if (report.get("release_gates") != config["release_gates"]
            or not report["release_gates"] or any(v is not False for v in report["release_gates"].values())
            or report.get("unknowns") != config["unknowns"] or any(v is not None for v in report["unknowns"].values())
            or report.get("all_functional_components_modelled") is not False
            or report.get("mounting_interfaces_measured") is not False):
        raise ValueError("Physical claims cannot be promoted")
    ids = [part["id"] for part in report["components"]]
    expected = REQUIRED_COMPONENTS | ({"private_engine_scan"} if report.get("private_scan") else set())
    if len(ids) != len(set(ids)) or set(ids) != expected:
        raise ValueError("Missing, duplicate or undeclared component")
    if {view["id"] for view in report["views"]} != set(VIEWS) or len(report["views"]) != len(VIEWS):
        raise ValueError("Incomplete native views")
    if report["voxel_size_mm"] != config["voxel_size_mm"]:
        raise ValueError("Resolution mismatch")
    for part in report["components"]:
        p = part["properties"]
        if not math.isfinite(p["volume_mm3"]) or p["volume_mm3"] <= 0:
            raise ValueError("Empty or invalid component")
        if (len(p["bounds_min_mm"]) != 3 or len(p["bounds_max_mm"]) != 3
                or any(not math.isfinite(a) or not math.isfinite(b) or a >= b
                       for a, b in zip(p["bounds_min_mm"], p["bounds_max_mm"]))):
            raise ValueError("Invalid component bounds")
    expected_checks = REQUIRED_CHECKS | ({"private_scan__firewall", "private_scan__transaxle"} if report.get("private_scan") else set())
    if set(report["checks"]) != expected_checks or any(type(check["collision"]) is not bool for check in report["checks"].values()):
        raise ValueError("Collision results missing or invalid")
    if report.get("private_scan"):
        validate_private_scan(report)


def checked_file(directory, relative, expected_hash):
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory.resolve()) or sha256(path) != expected_hash.lower():
        raise ValueError("Changed or out-of-scope file: " + relative)
    return path


def verify_report(directory):
    report = json.loads((directory / "vehicle-report-f15.json").read_text())
    config = json.loads((TWIN / "full-vehicle-study-f15.json").read_text())
    validate_scope(report, config)
    if report["private_scan"]:
        # Provenance, input digests and rigidity follow the F13 producer's own rules.
        validate_alignment(report["private_scan"]["alignment"])
    expected_sources = {str(p.relative_to(ROOT)) for p in (
        TWIN / "full-vehicle-study-f15.json", TWIN / "picogk/Program.cs", TWIN / "picogk/FullVehicleStudy.cs",
        TWIN / "picogk/Vehicle911917Packaging.csproj", TWIN / "picogk-mechanical-f13.json",
        TWIN / "picogk-full-vehicle-f12.json", ROOT / config["source_vehicle_reference"])}
    if len(report["inputs"]) != len(expected_sources) or {v["path"] for v in report["inputs"]} != expected_sources:
        raise ValueError("Incomplete source provenance")
    for entry in report["inputs"]:
        checked_file(ROOT, entry["path"], entry["sha256"])
    for part in report["components"]:
        for suffix in ("stl", "vdb"):
            checked_file(directory, part[suffix], part[suffix + "_sha256"])
    for view in report["views"]:
        checked_file(directory, view["file"], view["sha256"])
    for suffix in ("stl", "vdb"):
        checked_file(directory, report["inspection_assembly"][suffix], report["inspection_assembly"][suffix + "_sha256"])
    return report, config


def build(directory):
    report, config = verify_report(directory)
    clashes = [key for key, check in report["checks"].items() if check["collision"]]
    preview = directory / "full-vehicle-board-f15.png"
    canvas = Image.new("RGB", (2600, 2100), "#f3f4f6")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 2600, 165), fill="#172738")
    draw.text((50, 30), "911 / 917  |  INTEGRATED VEHICLE PACKAGING", font=font(42, bold=True), fill="white")
    mode = "PRIVATE UNCALIBRATED SCAN OVERLAY" if report["private_scan"] else "PUBLIC HYPOTHETICAL GEOMETRY"
    draw.text((50, 103), f"F15  /  Native PicoGK {report['kernel']}  /  {len(report['components'])} exported components  /  {mode}", font=font(24), fill="#cbd5e1")
    lookup = {v["id"]: v for v in report["views"]}
    for i, key in enumerate(("exterior", "mechanical", "top", "section")):
        x, y = 50 + (i % 2) * 1290, 205 + (i // 2) * 780
        draw.text((x, y), f"0{i+1}  {VIEWS[key].upper()}", font=font(27, bold=True), fill="#172738")
        capture = cropped_capture(directory / lookup[key]["file"])
        fitted = ImageOps.contain(capture, (1210, 660), Image.Resampling.LANCZOS)
        canvas.paste(fitted, (x + (1210-fitted.width)//2, y+55+(660-fitted.height)//2))
    draw.rectangle((50, 1775, 2550, 1930), fill="#e0e7ed")
    summary = [f"Wheelbase {report['wheelbase_mm']:.0f} mm  |  Rear tyre outer width {report['rear_tyre_outer_width_mm']:.0f} mm  |  Two seats, no rear seats",
               f"Nominal engine/floor gap {report['nominal_engine_floor_gap_mm']:.0f} mm  |  Engine/firewall {report['nominal_engine_firewall_gap_mm']:.0f} mm  |  {len(clashes)} detected clashes in {len(report['checks'])} pair tests",
               "Movement: +/-80 mm vertical only; front yaw +/-30 deg sensitivity. No measured linkage or mounting interfaces."]
    for i, line in enumerate(summary):
        draw.text((75, 1795+i*43), line, font=font(25), fill="#24374b")
    draw.text((50, 1970), "PACKAGING REVIEW ONLY  |  Not a complete functional vehicle, supplier CAD, or a 1,600 hp capability validation.", font=font(27, bold=True), fill="#9c3926")
    draw.text((50, 2020), "Blue-grey: body/structure   Ochre: engine/transaxle   Cyan: air/cooling   Copper: hot routes   Green: ancillary reservations", font=font(23), fill="#526275")
    canvas.save(preview)
    for key, view in lookup.items():
        capture = Image.open(directory / view["file"]).convert("RGB")
        capture.save(directory / ("vehicle-" + key + "-f15.png"))
    rows = "\n".join(f"| {key.replace('__', ' / ')} | {'CLASH' if value['collision'] else 'No intersection in this model'} |" for key, value in report["checks"].items())
    parts = "\n".join(f"| {p['id']} | {p['system']} | [{p['stl']}]({p['stl']}) |" for p in report["components"])
    text = f"""# F15 integrated vehicle review

![Native PicoGK assembly](full-vehicle-board-f15.png)

Status: **packaging trial, not an accepted automotive design**. The model contains
{len(report['components'])} separate exported geometries and six native views.
Private scan overlay: {bool(report['private_scan'])}. No rear seats are created.

## Geometry checks

The engine reservation is {config['engine_bounds_mm']} mm. Its nominal floor gap
is {report['nominal_engine_floor_gap_mm']} mm; its gap to the firewall's rear face
is {report['nominal_engine_firewall_gap_mm']} mm. These replace F14's 10 mm floor
gap and the earlier firewall check that did not subtract wall half-thickness.
The floor test expands the engine by 20 + two voxels = 30 mm; the firewall test
expands it by 50 + two voxels = 60 mm. Neither is physical fitment evidence.

The test reports **{len(clashes)} intersections**, not an all-clear vehicle.
Only the pairs listed below are tested. Intentional contacts and untested pairs
are not silently interpreted as clearances. No structural load path is validated.

| Pair | Native result |
|---|---|
{rows}

## Scope and unresolved engineering

Body stations, front track, seats, equipment, links and air paths are explicitly
hypothetical. Documentary base dimensions describe a 993, not a measured 930.
The engine topology proxy contains twelve lateral cylinder reservations; it is
not a reconstruction of engine internals. The optional local scan only replaces
that proxy in the views, and remains uncalibrated and private.

Rear track is 1,840 mm; tyres occupy 2,100 mm. The body reaches 2,200 mm nominal
width before its voxel shell thickness. This makes F14's width consequence
visible; it does not select the width or establish traction. Tyre bottom is
Z = {report['nominal_tyre_bottom_z_mm']} mm, not Z = 0; no ride-height claim is made.

Wheel reservation motion is prescribed independently of the displayed links.
Front yaw uses a conservative continuous bounding rectangle; bump is vertical
translation only. Wheel-arch subtraction is a construction rule, not an
independent suspension-clearance result. Toe, camber and hub migration remain
unknown. Firewall is a single constant-X plane trimmed to the body volume;
penetrations, sealing, insulation and attachments are not designed.

The front floor narrows from 1,100 to 880 mm ahead of X=500 mm to clear the
front steering envelope. Exhaust routes pass outboard of the rear crossmember.
The roof of the engine bay at X=2,320 / 2,722 mm is raised to 1,110 / 1,030 mm;
the cabin roof stations are unchanged. Quarter-intake and tail-feed apertures
are declared construction features; their sealing and reinforcement are unknown.

Fuel/oil/charge coolers, brakes, steering and suspension parts are envelopes,
not working systems. Restraints, mounts, fasteners, service connections,
electrical harnesses and production tolerances are not fully modelled.
Turbo/exhaust/cooling connections need supplier ports and thermal clearances.
The raised fixed tail contains a heat-exchanger reservation, without any
downforce, cooling-capacity or 1,600 hp strength claim.

## Component inventory

STL and VDB share the same millimetre coordinate system. Editable masters are
the tracked C# and JSON, not the meshes. These exports are **not for manufacture**.
The combined [inspection mesh](vehicle-inspection-assembly.stl) and
[PicoGK volume](vehicle-inspection-assembly.vdb) are convenience unions;
the individual exports below retain component separation.

| Component | System | Mesh |
|---|---|---|
{parts}
"""
    (directory / "engineering-review-f15.md").write_text(text)
    artifacts = [preview, directory / "engineering-review-f15.md", *directory.glob("vehicle-*-f15.png")]
    (directory / "delivery-manifest-f15.json").write_text(json.dumps({
        "status": "verified_files_not_physical_validation", "private_scan_present": bool(report["private_scan"]),
        "report_sha256": sha256(directory / "vehicle-report-f15.json"),
        "reporter_sha256": sha256(Path(__file__)),
        "files": [{"file": p.name, "sha256": sha256(p)} for p in artifacts]}, indent=2) + "\n")
    print(json.dumps({"components": len(report["components"]), "checks": len(report["checks"]), "clashes": clashes, "preview": str(preview)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/911-917-picogk-f15")
    build(parser.parse_args().output.resolve())
