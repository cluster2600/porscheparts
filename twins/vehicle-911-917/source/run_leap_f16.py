#!/usr/bin/env python3
"""Build the installed LEAP libraries and retain a separate public F16 run."""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageOps
from annotate_picogk_visualization_f11 import cropped_capture, font, sha256
from report_full_vehicle_f15 import verify_report, checked_file

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "twins/vehicle-911-917/leap-f16"
GATES = ("supplier_ports_measured", "coolant_circuit_designed", "fluid_solver_executed",
         "structural_solver_executed", "manufacturing_authorized")
REVISIONS = {"leap71/LEAP71_ShapeKernel": "554bce4791d2676ed00bd6704f6eb010111a7fd3",
             "leap71/LEAP71_LatticeLibrary": "81c3c7b2064c19e573c38d76ac09bf1cd2f562d5"}
PARTS = {"tail_lattice_insert", "tail_core_air", *(
    name + "_" + side + suffix for name in ("quarter_intake", "tail_cooling_duct")
    for side in ("left", "right") for suffix in ("", "_air"))}
OBSTACLES = {"firewall", "body_shell", "rear_structure_corridors", "transaxle_schematic",
             "wheel_motion_keepouts", "exhaust_left", "exhaust_right", "tail_plenum", "fixed_930_style_tail"}


def validate_config(c):
    if c["phase"] != "F16" or c["units"] != "mm" or c["voxel_size_mm"] != 5:
        raise ValueError("F16 requires F15's millimetre/5 mm grid")
    if any(c.get(key) is not False for key in GATES):
        raise ValueError("Physical claims cannot be promoted")
    def bounded(v, lo, hi):
        if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi:
            raise ValueError("Invalid or unresolved study dimension")
    bounded(c["duct_wall_mm"], 15, 25)
    if len(c["ducts"]) != 2 or {d["id"] for d in c["ducts"]} != {"quarter_intake", "tail_cooling_duct"}:
        raise ValueError("Unexpected duct inventory")
    for d in c["ducts"]:
        if len(d["inner_radius_mm"]) != 2 or not 4 <= len(d["control_points_mm"]) <= 6:
            raise ValueError("Invalid spline or section")
        for r in d["inner_radius_mm"]:
            bounded(r, 30, 90)
        previous = None
        for p in d["control_points_mm"]:
            if len(p) != 3 or p == previous:
                raise ValueError("Degenerate route")
            for v, lo, hi in zip(p, (1500, 300, 500), (3400, 1050, 1100)):
                bounded(v, lo, hi)
            previous = p
    bounded(c["lattice"]["beam_diameter_mm"], 15, 25)
    bounded(c["lattice"]["cell_mm"], 50, 80)
    bounded(c["lattice"]["boundary_inset_mm"], 10, 20)


def installed_files(leap):
    install = json.loads((leap / "setup/installation.json").read_text())
    libraries = {p["repository"]: p for p in install["libraries"]}
    files = [leap / "runtime/PicoGK.dll", leap / "runtime/SkiaSharp.dll",
             leap / "libraries/PicoGK/assets/ViewerEnvironment.zip"]
    files += sorted((leap / "runtime").rglob("*.dylib"))
    for repo, revision in REVISIONS.items():
        if libraries[repo]["revision"] != revision or libraries[repo]["license"] != "Apache-2.0":
            raise ValueError("Unreviewed installed library revision or licence")
        directory = leap / "libraries" / repo.split("/")[1]
        source_dir = directory / ("ShapeKernel" if "ShapeKernel" in repo else "LatticeLibrary")
        files += sorted(source_dir.rglob("*.cs")) + [directory / "LICENSE"]
    for p in files:
        if sha256(p) != install["sha256"].get(str(p.relative_to(leap))):
            raise ValueError("Installed file differs from installation receipt: " + str(p))
    return files


def verify_output(output):
    r = json.loads((output / "report.json").read_text())
    validate_config(r["config"])
    if r["phase"] != "F16" or r["status"] != "geometry_study_not_qualified_vehicle" or r["manufacturing_authorized"] is not False:
        raise ValueError("Invalid native status")
    if len(r["components"]) != len(PARTS) or {p["id"] for p in r["components"]} != PARTS:
        raise ValueError("Incomplete native component set")
    for p in r["components"]:
        if not math.isfinite(p["volume_mm3"]) or p["volume_mm3"] <= 0 or p["triangles"] <= 0 or p["vdb_equal"] is not True:
            raise ValueError("Invalid geometry result")
        for kind in ("stl", "vdb"):
            checked_file(output, p[kind], p[kind + "_sha256"])
    for source in r["input_receipt"]["files"]:
        if sha256(Path(source["path"])) != source["sha256"]:
            raise ValueError("Stale input receipt")
    exchange = r["field_exchange"]
    if (exchange["field_count"] != 4 or exchange["solid_air_equal"] is not True
            or exchange["bidirectional_values_equal"] is not True or exchange["physical_solver_executed"] is not False
            or exchange["added_value_negative_control_rejected"] is not True
            or min(exchange["scalar_active_values"], exchange["vector_active_values"]) <= 0):
        raise ValueError("Incomplete field roundtrip")
    expected_checks = {p + "__" + obstacle for p in PARTS if not p.endswith("_air") for obstacle in OBSTACLES}
    if set(r["checks"]) != expected_checks or any(type(v["collision"]) is not bool or
            not math.isfinite(v["volume_mm3"]) or v["volume_mm3"] < 0 for v in r["checks"].values()):
        raise ValueError("Incomplete collision results")
    checked_file(output, exchange["file"], exchange["sha256"])
    if len(r["views"]) != 5 or {v["id"] for v in r["views"]} != {"mechanical", "exterior", "air_paths", "tail_core", "air_domains"}:
        raise ValueError("Incomplete native views")
    for view in r["views"]:
        checked_file(output, view["file"], view["sha256"])
    return r


def board(output, r):
    canvas = Image.new("RGB", (2400, 1850), "#f3f4f6")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 2400, 140), fill="#172738")
    draw.text((45, 25), "911 / 917  |  SHAPEKERNEL + LATTICELIBRARY", font=font(40, bold=True), fill="white")
    draw.text((45, 86), "F16 / Native geometry / 5 mm voxels / Public packaging hypotheses", font=font(25), fill="#cbd5e1")
    labels = {"mechanical": "ASSEMBLY CONTEXT", "air_paths": "SMOOTH DUCTS + TAIL INSERT", "tail_core": "OPEN BCC INSERT — NO COOLANT CIRCUIT", "air_domains": "SEPARATE AIR RESERVATIONS"}
    views = {v["id"]: v for v in r["views"]}
    for i, (key, label) in enumerate(labels.items()):
        x, y = 45 + i % 2 * 1190, 180 + i // 2 * 710
        draw.text((x, y), label, font=font(25, bold=True), fill="#172738")
        capture = cropped_capture(output / views[key]["file"])
        fitted = ImageOps.contain(capture, (1110, 625), Image.Resampling.LANCZOS)
        canvas.paste(fitted, (x + (1110-fitted.width)//2, y+50+(625-fitted.height)//2))
    clashes = [name for name, check in r["checks"].items() if check["collision"]]
    draw.text((45, 1640), f"{len(clashes)} intersections in {len(r['checks'])} selected checks | BCC solid fraction: {100*r['solid_fraction_in_zone']:.1f}%", font=font(27), fill="#9c3926")
    draw.text((45, 1690), "VDB: solid + air + geometric scalar/vector fields, reloaded and compared in both directions.", font=font(25), fill="#172738")
    draw.text((45, 1760), "NOT A QUALIFIED HEAT EXCHANGER / No CFD, strength, fitment or 1,600 hp validation.", font=font(27, bold=True), fill="#9c3926")
    canvas.save(output / "leap-f16-board.png")
    for view in r["views"]:
        with Image.open(output / view["file"]) as im:
            im.convert("RGB").save(output / (view["id"] + ".png"))


def run(leap, baseline, output):
    config = json.loads((STUDY / "study.json").read_text()); validate_config(config)
    old, _ = verify_report(baseline)
    if old["private_scan"] is not None:
        raise ValueError("F16 public workflow does not admit private scan data")
    if output.exists() or output.with_name(output.name + "-build").exists():
        raise ValueError("Use a new output directory; previous runs are retained")
    files = installed_files(leap) + list(STUDY.glob("*")) + [Path(__file__),
        ROOT / "twins/vehicle-911-917/full-vehicle-study-f15.json", baseline / "vehicle-report-f15.json"]
    files += [baseline / p["vdb"] for p in old["components"]]
    build_dir = output.with_name(output.name + "-build"); build_dir.mkdir(parents=True)
    receipt = {"baseline": str(baseline), "output": str(output), "config": str(STUDY / "study.json"),
               "vehicle_config": str(ROOT / "twins/vehicle-911-917/full-vehicle-study-f15.json"),
               "libraries": REVISIONS, "revision_basis": "installed receipt and matching source hashes",
               "files": [{"path": str(p), "sha256": sha256(p)} for p in files if p.is_file()]}
    receipt_path = build_dir / "inputs.json"; receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    dotnet = leap / "sdk/dotnet"
    with (build_dir / "build.log").open("w") as log:
        subprocess.run([str(dotnet), "build", str(STUDY / "VehicleLeap.csproj"), "--configfile", str(STUDY / "NuGet.Config"),
                        "-p:LeapRoot=" + str(leap), "-o", str(build_dir / "bin")], stdout=log, stderr=subprocess.STDOUT, check=True)
    spec = importlib.util.spec_from_file_location("native_lock", ROOT / "parts/picogk-catalog/tools/run_part.py")
    lock = importlib.util.module_from_spec(spec); spec.loader.exec_module(lock)
    lock.acquire(timeout_s=60)
    try:
        subprocess.run([str(dotnet), str(build_dir / "bin/VehicleLeap.dll"), str(receipt_path)], check=True,
                       env={**os.environ, "DOTNET_ROOT": str(leap / "sdk")})
    finally:
        lock.LOCK.unlink(missing_ok=True)
    result = verify_output(output); board(output, result)
    print(json.dumps({"board": str(output / "leap-f16-board.png"), "components": len(result["components"]),
                      "clashes": [k for k, v in result["checks"].items() if v["collision"]]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leap-root", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=ROOT / "work/911-917-picogk-f15")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.leap_root.resolve(), args.baseline.resolve(), args.output.resolve())
