"""Generate and independently check the incomplete engine-mount shape study."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FAMILY = HERE.parent
STATUS = "shape_study_only_unmeasured_interfaces_no_manufacturing"
SPECS = ("engine-bracket", "mount-housing", "isolator-envelope")
REQUIRED = {"bracket_to_carrier": 4, "carrier_to_left_mount": 1,
            "carrier_to_right_mount": 1, "left_mount_to_body": 2,
            "right_mount_to_body": 2, "bracket_to_engine": None}
MEASUREMENTS = ("centres_mm", "axes", "bore_diameters_mm", "mating_faces",
                "datums", "tolerances", "measurement_evidence")
CARRIER = ROOT / "parts/993-eng-carrier-0001/derived/qwen-concept-f1/carrier-concept.stl"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight(contract=None):
    if contract is None:
        contract = json.loads((FAMILY / "interface-contract.json").read_text())
    if contract["variant"] != "993_Turbo" or set(contract["interfaces"]) != set(REQUIRED):
        raise ValueError("Wrong variant or incomplete independent interface contract")
    if contract["manufacturing_authorized"] is not False or contract["functional_geometry_produced"] is not False:
        raise ValueError("This study cannot authorize functional geometry")
    for name, count in REQUIRED.items():
        actual = contract["interfaces"][name]["attachment_sites"]
        if actual != count or (count is not None and type(actual) is not int):
            raise ValueError("Independent attachment counts cannot be weakened: " + name)
        if any(field not in contract["interfaces"][name] for field in MEASUREMENTS):
            raise ValueError("Missing measurement fields: " + name)
    # shortcut: no qualified interface inspector exists here; measured input alone cannot grant acceptance.
    return {"decision": "blocked", "unverified_interfaces": sorted(REQUIRED),
            "unknown_attachment_counts": ["bracket_to_engine"],
            "is_fitment_validated": False, "is_material_qualified": False,
            "manufacturing_authorized": False}


def read_stl(path):
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError("Incomplete binary STL: " + path.name)
    count = struct.unpack_from("<I", data, 80)[0]
    if not 0 < count <= 5_000_000 or len(data) != 84 + 50 * count:
        raise ValueError("Invalid binary STL length: " + path.name)
    points, faces, lookup = [], [], {}
    for row in struct.iter_unpack("<12fH", data[84:]):
        face = []
        for i in (3, 6, 9):
            point = tuple(row[i:i + 3])
            if not all(math.isfinite(v) for v in point):
                raise ValueError("Nonfinite STL coordinates")
            if point not in lookup:
                lookup[point] = len(points)
                points.append(point)
            face.append(lookup[point])
        if len(set(face)) != 3:
            raise ValueError("Degenerate STL face")
        faces.append(face)
    return points, faces


def remove_degenerate_faces(path, output):
    data = path.read_bytes()
    if len(data) < 84 or len(data) != 84 + 50 * struct.unpack_from("<I", data, 80)[0]:
        raise ValueError("Invalid native binary STL")
    kept = []
    for start in range(84, len(data), 50):
        row = struct.unpack_from("<12fH", data, start)
        a, b, c = (tuple(row[i:i + 3]) for i in (3, 6, 9))
        if not all(math.isfinite(v) for p in (a, b, c) for v in p):
            raise ValueError("Nonfinite native coordinates")
        ab, ac = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        cross = [ab[1]*ac[2] - ab[2]*ac[1], ab[2]*ac[0] - ab[0]*ac[2], ab[0]*ac[1] - ab[1]*ac[0]]
        if any(cross):
            kept.append(data[start:start + 50])
    output.write_bytes(data[:80] + struct.pack("<I", len(kept)) + b"".join(kept))
    return (len(data) - 84) // 50 - len(kept)


def mesh_check(path):
    points, faces = read_stl(path)
    edges, balance, neighbours = Counter(), Counter(), defaultdict(set)
    volume = 0.0
    for face in faces:
        a, b, c = (points[i] for i in face)
        volume += (a[0] * (b[1]*c[2] - b[2]*c[1]) +
                   a[1] * (b[2]*c[0] - b[0]*c[2]) +
                   a[2] * (b[0]*c[1] - b[1]*c[0])) / 6
        for a_id, b_id in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((a_id, b_id)))
            edges[edge] += 1
            balance[edge] += 1 if a_id < b_id else -1
            neighbours[a_id].add(b_id)
            neighbours[b_id].add(a_id)
    unseen, components = set(range(len(points))), 0
    while unseen:
        components += 1
        pending = [unseen.pop()]
        while pending:
            node = pending.pop()
            new = neighbours[node] & unseen
            unseen.difference_update(new)
            pending.extend(new)
    if any(n != 2 for n in edges.values()) or any(balance.values()) or volume <= 0 or components != 1:
        raise ValueError("Mesh failed closure, winding, volume or connectivity check: " + path.name)
    return {"triangles": len(faces), "closed_edges": True, "consistent_winding": True,
            "connected_components": components, "volume_mm3": volume,
            "bounds_mm": [[min(p[i] for p in points) for i in range(3)],
                          [max(p[i] for p in points) for i in range(3)]]}


def write_mesh_usd(stl, output):
    points, faces = read_stl(stl)
    text = '#usda 1.0\n(defaultPrim = "Part"\nmetersPerUnit = 0.001\nupAxis = "Z")\n'
    text += 'def Xform "Part" {\n custom bool manufacturing_authorized = false\n'
    text += ' def Mesh "Geometry" {\n uniform token subdivisionScheme = "none"\n'
    text += " point3f[] points = [" + ", ".join(str(p) for p in points) + "]\n"
    text += " int[] faceVertexCounts = [" + ", ".join(["3"] * len(faces)) + "]\n"
    text += " int[] faceVertexIndices = [" + ", ".join(str(i) for f in faces for i in f) + "]\n}\n}\n"
    output.write_text(text)


def generate(output, dll, dotnet="dotnet", shape_study=False):
    audit = preflight()
    if not shape_study:
        raise ValueError("Functional generation blocked: --shape-study permits unmeasured geometry only")
    if output.exists() or output.is_symlink():
        raise ValueError("Output directory must be new")
    output.mkdir(parents=True)
    native = output / "native"
    native.mkdir()
    with (output / "native.log").open("w") as log:
        for stem in SPECS:
            subprocess.run([dotnet, str(dll), str(HERE / (stem + ".json")), str(native)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
    removed = {}
    for path in native.glob("*.stl"):
        removed[path.name] = remove_degenerate_faces(path, output / path.name)
    for path in native.glob("*.json"):
        shutil.move(path, output / path.name)
    shutil.copyfile(CARRIER, output / "carrier-reference.stl")
    for path in output.glob("*.stl"):
        mesh_check(path)
        write_mesh_usd(path, path.with_suffix(".usda"))
    assembly = '#usda 1.0\n(defaultPrim = "EngineMountStudy"\nmetersPerUnit = 0.001\nupAxis = "Z")\n'
    assembly += 'def Xform "EngineMountStudy" {\n custom bool manufacturing_authorized = false\n'
    assembly += ' custom string pose_status = "exploded_illustration_only_not_measured_assembly"\n'
    instances = [("CarrierReference", "carrier-reference", (0, 0, 0)),
                 ("CentralBracket", "993-ENG-BRACKET-0001", (0, 0, 100)),
                 ("LeftHousing", "993-ENG-MOUNTING-0001", (-275, 0, 80)),
                 ("RightHousing", "993-ENG-MOUNTING-0001", (275, 0, 80)),
                 ("LeftIsolatorEnvelope", "993-ENG-MOUNTING-ISOLATOR-F0", (-275, 0, 145)),
                 ("RightIsolatorEnvelope", "993-ENG-MOUNTING-ISOLATOR-F0", (275, 0, 145))]
    for name, stem, pose in instances:
        assembly += (f' def Xform "{name}" (prepend references = @{stem}.usda@</Part>) {{\n'
                     f' double3 xformOp:translate = {pose}\n'
                     ' uniform token[] xformOpOrder = ["xformOp:translate"]\n }\n')
    (output / "assembly.usda").write_text(assembly + "}\n")
    inputs = [FAMILY / "interface-contract.json", CARRIER,
              ROOT / "parts/picogk-catalog/engine/EngineMounts.cs",
              ROOT / "parts/picogk-catalog/engine/EngineSdf.cs",
              ROOT / "containers/m64-leap71/sources.lock"]
    inputs += sorted((ROOT / "parts/picogk-catalog/common").glob("*.cs"))
    inputs += [HERE / (s + ".json") for s in SPECS] + [Path(__file__)]
    report = {"schema_version": "1.0.0", "status": STATUS, "interface_audit": audit,
              "pose_status": "exploded_illustration_only_not_measured_assembly",
              "selected_material": None, "stiffness_and_damping": None,
              "mass_estimates_qualified": False,
              "exact_zero_area_faces_removed": removed,
              "carrier_reference": "Archived Qwen F1 comparison only; R9 and its evidence remain unchanged.",
              "native_runtime": {"engine_dll_sha256": sha256(dll),
                                 "picogk_dll_sha256": sha256(dll.parent / "PicoGK.dll"),
                                 "dotnet_version": subprocess.check_output([dotnet, "--version"], text=True).strip()},
              "native_density_note": "Native runner density is zero: its zero mass is a disabled estimate, not part mass.",
              "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in inputs},
              "artifacts": {str(p.relative_to(output)): sha256(p) for p in sorted(output.rglob("*"))
                            if p.is_file() and p.suffix in (".stl", ".usda", ".json")},
              "meshes": {p.name: mesh_check(p) for p in sorted(output.glob("*.stl"))}}
    # This completion report is written only after every native output and mesh check passes.
    (output / "study-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def check(output):
    report = json.loads((output / "study-report.json").read_text())
    if report["status"] != STATUS or report["interface_audit"] != preflight():
        raise ValueError("Study status or independent attachment audit drifted")
    if report["selected_material"] is not None or report["stiffness_and_damping"] is not None or report["mass_estimates_qualified"] is not False:
        raise ValueError("Geometry cannot qualify material, mount stiffness or mass")
    for name, expected in report["inputs"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError("Study input changed: " + name)
    expected_artifacts = {"carrier-reference.stl", "carrier-reference.usda", "assembly.usda"}
    for stem in SPECS:
        spec = json.loads((HERE / (stem + ".json")).read_text())
        expected_artifacts.update(spec["part_id"] + ext for ext in (".stl", ".usda", ".report.json"))
        expected_artifacts.add("native/" + spec["part_id"] + ".stl")
    if set(report["artifacts"]) != expected_artifacts:
        raise ValueError("Missing or unexpected study artifact")
    if set(report["meshes"]) != {name for name in expected_artifacts if name.endswith(".stl") and "/" not in name}:
        raise ValueError("Missing independent mesh inspection")
    for name, expected in report["artifacts"].items():
        if sha256(output / name) != expected:
            raise ValueError("Study artifact changed: " + name)
    for name, metrics in report["meshes"].items():
        if mesh_check(output / name) != metrics:
            raise ValueError("Mesh inspection drifted: " + name)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--shape-study", action="store_true")
    parser.add_argument("--engine-dll", type=Path)
    parser.add_argument("--dotnet", default="dotnet")
    parser.add_argument("--output-dir", type=Path, default=FAMILY / "derived")
    args = parser.parse_args()
    if args.check:
        check(args.output_dir)
    else:
        if args.engine_dll is None:
            parser.error("--engine-dll is required for native generation")
        generate(args.output_dir, args.engine_dll, args.dotnet, args.shape_study)
    print("Engine mount shape study checked; functional acceptance remains blocked.")


if __name__ == "__main__":
    main()
