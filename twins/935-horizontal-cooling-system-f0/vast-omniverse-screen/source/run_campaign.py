#!/usr/bin/env python3
"""Generate and solve a bounded, explicitly unvalidated 935 fan material screen."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_positive(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return float(value)


def load_inputs(root: Path) -> tuple[dict, dict]:
    cards = read_json(root / "materials.json")
    scenario = read_json(root / "scenario.json")
    ids = []
    for card in cards["materials"]:
        ids.append(card["id"])
        if re.fullmatch(r"[a-z0-9_]+", card["id"]) is None:
            raise ValueError("invalid material identifier")
        for key in ("density_g_cm3", "young_modulus_GPa", "thermal_conductivity_W_mK", "specific_heat_J_kgK"):
            require_positive(card[key], f"{card['id']}.{key}")
        yield_value = card["yield_comparator_MPa"]
        if yield_value is not None:
            require_positive(yield_value, f"{card['id']}.yield_comparator_MPa")
    if len(ids) != 10 or len(set(ids)) != len(ids):
        raise ValueError("campaign requires ten distinct material cards")
    geometry = scenario["geometry"]
    for key in ("outer_diameter_mm", "blade_count", "disc_thickness_mm", "blade_height_mm", "hub_bore_diameter_mm"):
        require_positive(geometry[key], f"geometry.{key}")
    return cards, scenario


def load_input_contract(root: Path) -> dict:
    """Bind the comparative proxy to the separately published 935 evidence gate."""
    contract_root = root.parents[1] / "935-horizontal-cooling-system"
    matrix_path = contract_root / "data/input-matrix.json"
    coverage_path = contract_root / "research/coverage.json"
    matrix = read_json(matrix_path)
    coverage = read_json(coverage_path)
    if matrix.get("schema_version") != "1.0.0" or len(matrix.get("rows", [])) != 50:
        raise ValueError("935 input matrix is not the expected published contract")
    if len(matrix.get("variants", [])) != 6:
        raise ValueError("935 input contract must keep six variant scopes separate")
    if matrix.get("accepted_935_numeric_physical_claims") != 0:
        raise ValueError("comparative proxy cannot consume unreviewed 935 physical claims")
    if matrix.get("manufacturing_authorized") is not False:
        raise ValueError("935 input contract must keep manufacturing authorization closed")
    accepted_coverage_statuses = {
        "partial_awaiting_original_bundle",
        "completed_40_lane_public_synthesis_engine_data_partial",
    }
    if coverage.get("status") not in accepted_coverage_statuses:
        raise ValueError("935 research coverage status is not an allowed evidence state")
    if coverage.get("admitted_935_numeric_physical_claims") != 0:
        raise ValueError("935 coverage cannot admit numeric claims for this proxy")
    return {
        "matrix_path": "twins/935-horizontal-cooling-system/data/input-matrix.json",
        "matrix_sha256": sha(matrix_path),
        "matrix_rows": len(matrix["rows"]),
        "separate_variants": len(matrix["variants"]),
        "accepted_935_numeric_physical_claims": matrix["accepted_935_numeric_physical_claims"],
        "coverage_path": "twins/935-horizontal-cooling-system/research/coverage.json",
        "coverage_sha256": sha(coverage_path),
        "research_coverage": coverage["status"],
        "physical_claims_consumed": False,
    }


def build_proxy(step_path: Path, stl_path: Path, scenario: dict) -> dict:
    import cadquery as cq
    from cadquery import exporters
    import trimesh

    g = scenario["geometry"]
    outer_radius = float(g["outer_diameter_mm"]) / 2
    bore_radius = float(g["hub_bore_diameter_mm"]) / 2
    disc_t = float(g["disc_thickness_mm"])
    blade_h = float(g["blade_height_mm"])
    blades = int(g["blade_count"])
    # A deliberately simple union: its purpose is a reproducible comparative witness.
    solid = cq.Workplane("XY").circle(outer_radius).extrude(disc_t, both=True)
    solid = solid.union(cq.Workplane("XY").circle(30.0).extrude(16.0, both=True))
    radial_length, tangential_width = outer_radius * 0.62, outer_radius * 0.13
    centre_radius = outer_radius * 0.61
    for index in range(blades):
        angle = 360.0 * index / blades
        blade = (cq.Workplane("XY").box(radial_length, tangential_width, blade_h)
                 .translate((centre_radius, 0, disc_t / 2 + blade_h / 2))
                 .rotate((0, 0, 0), (0, 0, 1), angle + 24.0))
        solid = solid.union(blade)
    solid = solid.cut(cq.Workplane("XY").circle(bore_radius).extrude(40.0, both=True)).clean()
    step_path.parent.mkdir(parents=True, exist_ok=True)
    exporters.export(solid, str(step_path))
    exporters.export(solid, str(stl_path), tolerance=0.20, angularTolerance=0.20)
    mesh = trimesh.load_mesh(stl_path, process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError("proxy STL must be a closed positive solid")
    return {
        "triangles": int(len(mesh.faces)), "vertices": int(len(mesh.vertices)),
        "volume_mm3": float(mesh.volume), "center_of_mass_mm": [float(x) for x in mesh.center_mass],
        "unit_density_inertia_mm5": [[float(x) for x in row] for row in mesh.moment_inertia],
        "bounds_mm": [[float(x) for x in row] for row in mesh.bounds], "stl_sha256": sha(stl_path),
    }


def build_base_deck(stl_path: Path, out: Path, bore_radius: float) -> dict:
    import gmsh
    import numpy as np

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.NumThreads", 4)
        gmsh.merge(str(stl_path))
        gmsh.option.setNumber("Mesh.MeshOnlyEmpty", 1)
        surfaces = [tag for dim, tag in gmsh.model.getEntities(2)]
        loop = gmsh.model.geo.addSurfaceLoop(surfaces)
        volume = gmsh.model.geo.addVolume([loop])
        gmsh.model.geo.synchronize()
        gmsh.model.addPhysicalGroup(3, [volume], 1)
        gmsh.model.setPhysicalName(3, 1, "ROTOR")
        gmsh.option.setNumber("Mesh.MeshSizeMin", 2.0)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 6.0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 18)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("")
        gmsh.model.mesh.setOrder(2)
        points, _ = gmsh.model.mesh.getIntegrationPoints(11, "Gauss2")
        _, determinants, _ = gmsh.model.mesh.getJacobians(11, points)
        if not np.isfinite(determinants).all() or min(determinants) <= 0:
            raise ValueError("non-positive quadratic element Jacobian")
        gmsh.write(str(out / "base.inp"))
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        xyz = np.asarray(xyz).reshape(-1, 3)
        fixed = tags[np.hypot(xyz[:, 0], xyz[:, 1]) <= bore_radius + 0.25]
        types, element_tags, _ = gmsh.model.mesh.getElements(3)
        if list(types) != [11] or len(fixed) < 12:
            raise ValueError("expected quadratic tets and bore node set")
        return {"quadratic_tetrahedra": int(len(element_tags[0])), "nodes": int(len(tags)),
                "bore_fixed_nodes": int(len(fixed)), "minimum_jacobian": float(min(determinants)),
                "fixed_ids": [int(x) for x in fixed]}
    finally:
        gmsh.finalize()


def prepare_decks(base: Path, mesh: dict, cards: dict, scenario: dict, cases: Path) -> dict:
    raw = base.read_text(encoding="utf-8")
    bore = ",".join(str(node) for node in mesh["fixed_ids"])
    rpm = float(scenario["loads"]["static_rpm"])
    omega2 = (rpm * math.pi / 30.0) ** 2
    cases.mkdir()
    record = []
    for card in cards["materials"]:
        case = cases / card["id"]
        case.mkdir()
        header = raw + "\n*NSET,NSET=BORE\n"
        ids = mesh["fixed_ids"]
        header += "\n".join(",".join(str(value) for value in ids[index:index + 12]) for index in range(0, len(ids), 12)) + "\n"
        header += ("*MATERIAL,NAME=SCREEN\n*ELASTIC\n"
                   f"{float(card['young_modulus_GPa']) * 1000.0:.12g},{float(cards['poisson_ratio_common_assumed']):.12g}\n"
                   "*DENSITY\n"
                   f"{float(card['density_g_cm3']) * 1e-9:.12g}\n"
                   "*SOLID SECTION,ELSET=ROTOR,MATERIAL=SCREEN\n*BOUNDARY\nBORE,1,3\n")
        static = header + ("*STEP\n*STATIC\n*DLOAD\n"
                           f"ROTOR,CENTRIF,{omega2:.12g},0,0,0,0,0,1\n"
                           "*NODE PRINT,NSET=Nall\nU\n*EL PRINT,ELSET=ROTOR\nS\n*END STEP\n")
        modal = header + "*STEP\n*FREQUENCY\n12\n*END STEP\n"
        (case / "rotor.inp").write_text(static, encoding="utf-8")
        (case / "modal.inp").write_text(modal, encoding="utf-8")
        record.append({"id": card["id"], "rotor_deck_sha256": sha(case / "rotor.inp"), "modal_deck_sha256": sha(case / "modal.inp")})
    return {"base_deck_sha256": sha(base), "rpm": rpm, "cases": record}


def run_ccx(case: Path, name: str) -> None:
    executable = shutil.which("ccx")
    if executable is None:
        raise RuntimeError("ccx is not installed")
    result = subprocess.run([executable, "-i", name], cwd=case, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    (case / f"log.{name}").write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0 or "Job finished" not in result.stdout or "*ERROR" in result.stdout:
        raise RuntimeError(f"CalculiX failed for {case.name}/{name}")


def parse_static(case: Path, expected: str) -> dict:
    if sha(case / "rotor.inp") != expected:
        raise ValueError("static deck changed after preparation")
    stress, displacement, mode = [], [], ""
    for line in (case / "rotor.dat").read_text(encoding="utf-8", errors="replace").splitlines():
        lowered = line.lower()
        if "stresses" in lowered and "sxx" in lowered:
            mode = "stress"; continue
        if "displacements" in lowered and "vx" in lowered:
            mode = "displacement"; continue
        fields = line.split()
        if not fields or not fields[0].isdigit():
            continue
        if mode == "stress" and len(fields) == 8:
            xx, yy, zz, xy, xz, yz = map(float, fields[2:])
            stress.append(math.sqrt(.5*((xx-yy)**2+(yy-zz)**2+(zz-xx)**2)+3*(xy*xy+xz*xz+yz*yz)))
        if mode == "displacement" and len(fields) == 4:
            displacement.append(math.sqrt(sum(float(x)**2 for x in fields[1:])))
    if not stress or not displacement or not all(math.isfinite(x) for x in stress + displacement):
        raise ValueError("missing or non-finite static output")
    return {"von_mises_max_MPa": max(stress), "maximum_displacement_mm": max(displacement),
            "rotor_dat_sha256": sha(case / "rotor.dat"), "log_sha256": sha(case / "log.rotor")}


def parse_modes(case: Path, expected: str) -> list[float]:
    if sha(case / "modal.inp") != expected:
        raise ValueError("modal deck changed after preparation")
    text = (case / "modal.dat").read_text(encoding="utf-8", errors="replace").split("P A R T I C I P A T I O N")[0]
    modes = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 5 and fields[0].isdigit():
            eigen, omega, frequency, imaginary = map(float, fields[1:])
            if min(eigen, omega, frequency) > 0 and imaginary == 0 and math.isclose(omega, 2 * math.pi * frequency, rel_tol=1e-6):
                modes.append(frequency)
    if len(modes) != 12:
        raise ValueError("expected twelve modal results")
    return modes


def build_usd(out: Path, cards: dict, scenario: dict, geometry: dict, input_contract: dict) -> Path:
    from pxr import Gf, Usd, UsdGeom, UsdLux
    stage_path = out / "935-horizontal-fan-alloy-screen.usda"
    stage = Usd.Stage.CreateNew(str(stage_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    root = UsdGeom.Xform.Define(stage, "/FanAlloyScreen").GetPrim()
    stage.SetDefaultPrim(root)
    root.SetCustomData({"digitalTwinStatus": "exploratory_comparative_screen", "manufacturingAuthorized": False,
                        "scanTransferred": False, "interfacesVerified": False, "source": scenario["id"],
                        "inputContractSha256": input_contract["matrix_sha256"],
                        "accepted935NumericPhysicalClaims": input_contract["accepted_935_numeric_physical_claims"]})
    camera = UsdGeom.Camera.Define(stage, "/FanAlloyScreen/Camera")
    camera.CreateFocalLengthAttr(52.0)
    camera.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 600.0))
    light = UsdLux.DistantLight.Define(stage, "/FanAlloyScreen/KeyLight")
    light.CreateIntensityAttr(1800.0)
    light.AddRotateXOp().Set(180.0)
    g = scenario["geometry"]
    outer_radius = float(g["outer_diameter_mm"]) / 2.0
    disc_t = float(g["disc_thickness_mm"])
    blade_h = float(g["blade_height_mm"])
    radial_length, tangential_width = outer_radius * 0.62, outer_radius * 0.13
    centre_radius = outer_radius * 0.61
    variant_set = root.GetVariantSets().AddVariantSet("materialScenario")
    colors = [(0.65,0.65,0.7),(0.8,0.7,0.25),(0.5,0.55,0.6),(0.4,0.6,0.7),(0.75,0.45,0.25)]
    for index, card in enumerate(cards["materials"]):
        variant_set.AddVariant(card["id"])
        variant_set.SetVariantSelection(card["id"])
        with variant_set.GetVariantEditContext():
            prim = UsdGeom.Xform.Define(stage, "/FanAlloyScreen/Proxy").GetPrim()
            prim.SetCustomData({"materialScenario": card["name"], "source": card["source"], "yieldComparatorMPa": card["yield_comparator_MPa"],
                                "processQualifiedForPart": False, "variantRole": "comparison_only"})
            disc = UsdGeom.Cylinder.Define(stage, "/FanAlloyScreen/Proxy/Disc")
            disc.CreateRadiusAttr(outer_radius)
            disc.CreateHeightAttr(disc_t)
            disc.CreateDisplayColorAttr([colors[index % len(colors)]])
            hub = UsdGeom.Cylinder.Define(stage, "/FanAlloyScreen/Proxy/Hub")
            hub.CreateRadiusAttr(30.0)
            hub.CreateHeightAttr(16.0)
            hub.CreateDisplayColorAttr([colors[index % len(colors)]])
            for blade_index in range(int(g["blade_count"])):
                blade = UsdGeom.Cube.Define(stage, f"/FanAlloyScreen/Proxy/Blade{blade_index:02d}")
                blade.CreateSizeAttr(1.0)
                blade.CreateDisplayColorAttr([colors[index % len(colors)]])
                blade.AddTranslateOp().Set(Gf.Vec3d(centre_radius, 0.0, disc_t / 2.0 + blade_h / 2.0))
                blade.AddRotateZOp().Set(360.0 * blade_index / int(g["blade_count"]) + 24.0)
                blade.AddScaleOp().Set(Gf.Vec3f(radial_length, tangential_width, blade_h))
    variant_set.SetVariantSelection("alsi10mg")
    stage.GetRootLayer().documentation = "Exploratory 935 horizontal fan alloy screen. No physical validation or manufacturing authorization."
    stage.GetRootLayer().Save()
    return stage_path


def require_ovrtx_endpoint(endpoint: str) -> str:
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != 8001:
        raise ValueError("OVRTX endpoint must remain local loopback port 8001")
    if (parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise ValueError("OVRTX endpoint must not carry credentials or parameters")
    return endpoint.rstrip("/")


def render_ovrtx(stage_path: Path, out: Path, endpoint: str) -> dict:
    endpoint = require_ovrtx_endpoint(endpoint)
    camera_path = "/FanAlloyScreen/Camera"
    payload = {"url": stage_path.resolve().as_uri(), "force_render": True,
               "render_settings": {"camera_paths": [camera_path], "frame_range": {"start": 0, "end": 0},
                                   "camera_parameters": {"width": 1024, "height": 1024}, "sensors": ["rgb"],
                                   "apply_background_mask": False, "render_mode": "PathTracing",
                                   "num_sensor_updates": 16, "material_target": "All"}}
    request = urllib.request.Request(f"{endpoint}/render", data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=3600) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("status") != "success":
        raise RuntimeError(f"OVRTX render failed: {result.get('error')}")
    encoded = result.get("images", {}).get("0", {}).get(camera_path, {}).get("rgb")
    if not isinstance(encoded, str) or not encoded:
        raise RuntimeError("OVRTX render returned no RGB frame")
    image_path = out / "ovrtx-preview.png"
    image_path.write_bytes(base64.b64decode(encoded, validate=True))
    if image_path.stat().st_size < 1024:
        raise RuntimeError("OVRTX render output is unexpectedly small")
    return {"status": "passed", "endpoint": endpoint, "camera_path": camera_path,
            "image": {"path": str(image_path), "sha256": sha(image_path), "bytes": image_path.stat().st_size}}


def run(root: Path, out: Path, ovrtx_endpoint: str | None = None) -> dict:
    cards, scenario = load_inputs(root)
    input_contract = load_input_contract(root)
    out.mkdir(parents=True, exist_ok=False)
    geometry_dir = out / "geometry"; geometry_dir.mkdir()
    geometry = build_proxy(geometry_dir / "rotor-proxy.step", geometry_dir / "rotor-proxy.stl", scenario)
    mesh = build_base_deck(geometry_dir / "rotor-proxy.stl", geometry_dir, float(scenario["geometry"]["hub_bore_diameter_mm"]) / 2)
    preparation = prepare_decks(geometry_dir / "base.inp", mesh, cards, scenario, out / "cases")
    records = {item["id"]: item for item in preparation["cases"]}
    for card in cards["materials"]:
        run_ccx(out / "cases" / card["id"], "rotor")
    run_ccx(out / "cases" / "alsi10mg", "modal")
    base_modes = parse_modes(out / "cases" / "alsi10mg", records["alsi10mg"]["modal_deck_sha256"])
    volume = geometry["volume_mm3"]
    inertia_z_unit = geometry["unit_density_inertia_mm5"][2][2]
    rpm_static = preparation["rpm"]
    rows, results = [], []
    for card in cards["materials"]:
        static = parse_static(out / "cases" / card["id"], records[card["id"]]["rotor_deck_sha256"])
        rho, young = float(card["density_g_cm3"]), float(card["young_modulus_GPa"])
        frequency_scale = math.sqrt((young / rho) / (70.0 / 2.67))
        mass = volume * rho * 1e-6
        inertia = inertia_z_unit * rho * 1e-12
        thermal = math.log((float(scenario["geometry"]["outer_diameter_mm"]) / 2) / (float(scenario["geometry"]["hub_bore_diameter_mm"]) / 2)) / (2 * math.pi * float(card["thermal_conductivity_W_mK"]) * float(scenario["geometry"]["disc_thickness_mm"]) / 1000)
        result = {"id": card["id"], "name": card["name"], "mass_kg": mass, "polar_inertia_kg_m2": inertia,
                  "static_8500rpm": static, "modes_hz": [value * frequency_scale for value in base_modes],
                  "modal_method": "fresh CalculiX solve" if card["id"] == "alsi10mg" else "exact elastic similarity; common Poisson ratio and same mesh/restraint",
                  "thermal_radial_K_per_W_proxy": thermal, "thermal_diffusivity_m2_s_proxy": float(card["thermal_conductivity_W_mK"]) / (rho * 1000 * float(card["specific_heat_J_kgK"])),
                  "yield_comparator_MPa": card["yield_comparator_MPa"]}
        results.append(result)
        for rpm in scenario["loads"]["rpm_sweep"]:
            factor = (float(rpm) / rpm_static) ** 2
            peak = static["von_mises_max_MPa"] * factor
            comparator = card["yield_comparator_MPa"]
            rows.append({"material": card["id"], "rpm": rpm, "mass_kg": mass, "polar_inertia_kg_m2": inertia,
                         "tip_speed_m_s": (float(scenario["geometry"]["outer_diameter_mm"]) / 2000) * float(rpm) * math.pi / 30,
                         "kinetic_energy_J": .5 * inertia * (float(rpm) * math.pi / 30) ** 2,
                         "peak_von_mises_MPa": peak, "maximum_displacement_mm": static["maximum_displacement_mm"] * factor,
                         "yield_comparator_over_peak": None if comparator is None else comparator / peak,
                         "above_yield_comparator": None if comparator is None else peak > comparator,
                         "method": "fresh CalculiX static solve" if rpm == rpm_static else "linear-elastic omega-squared extrapolation"})
    usd = build_usd(out, cards, scenario, geometry, input_contract)
    render = None if ovrtx_endpoint is None else render_ovrtx(usd, out, ovrtx_endpoint)
    report = {"schema_version": "1.0.0", "status": "completed_unvalidated_comparative_screen", "generated_at": datetime.now(timezone.utc).isoformat(),
              "scenario": scenario, "input_contract": input_contract, "geometry": geometry, "mesh": {key: value for key, value in mesh.items() if key != "fixed_ids"},
              "materials": results, "rpm_sweep": rows, "usd": {"path": str(usd), "sha256": sha(usd)},
              "ovrtx_render": render,
              "solver": {"name": "CalculiX", "static_cases": len(cards["materials"]), "modal_cases": 1, "static_rpm": rpm_static},
              "limits": "Comparative proxy only: no scan mesh transfer, dimensional validation, interfaces, CFD, fatigue, balance, contact, residual stress, overspeed, burst or physical correlation.",
              "manufacturing_authorized": False, "vehicle_operation_authorized": False, "digital_twin_calibrated": False}
    (out / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {"files_sha256": {str(path.relative_to(out)): sha(path) for path in sorted(out.rglob("*")) if path.is_file() and path.name != "manifest.json"}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ovrtx-endpoint", default=None)
    args = parser.parse_args()
    report = run(args.root.resolve(), args.output.resolve(), args.ovrtx_endpoint)
    print(json.dumps({"status": report["status"], "output": str(args.output)}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
