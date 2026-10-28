"""Compose the original-bound 935 inspection USD with eight PicoGK witnesses.

The added prims are geometric inspection annotations. The source-unit-to-metre
conversion is conditional and establishes no physical mounting dimension.
"""

import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

import numpy as np


DTYPE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
FLAGS = ("scale_verified", "interfaces_verified", "mechanism_dynamics_validated",
         "historical_installation_verified", "manufacturing_authorized", "physical_validation")
DRIVE_SHA256 = "fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def triangles(path: Path, expected: int) -> np.ndarray:
    with path.open("rb") as stream:
        header = stream.read(84)
    if (len(header) != 84 or struct.unpack("<I", header[80:])[0] != expected
            or not 100 <= expected <= 1_000_000 or path.stat().st_size != 84 + 50 * expected):
        raise ValueError("Complete bounded PicoGK binary STL required")
    return np.memmap(path, mode="r", dtype=DTYPE, offset=84, shape=(expected,))["vertices"]


def run(base_dir: Path, witness_dir: Path, output: Path) -> None:
    from pxr import Gf, Usd, UsdGeom, Vt

    base_dir, witness_dir, output = (path.resolve() for path in (base_dir, witness_dir, output))
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ output directory")
    base_stage = base_dir / "assembly-inspection.usdc"
    base_report = json.loads((base_dir / "report.json").read_text())
    if (base_report["status"] != "inspection_exports_audited"
            or base_report["usd_sha256"] != digest(base_stage)
            or base_report["native_receipt_sha256"] != "b63b4830d028c3455e7e40e25180f62463057794148b380661483a02f8069a2b"
            or base_report["source_coordinate_unit"] != "uncalibrated_scan_unit"
            or base_report["millimetre_to_metre_scale"] != .001
            or base_report["export_triangles_preserved"] is not True
            or any(base_report[key] is not False for key in FLAGS)):
        raise ValueError("Pinned unqualified original-bound 935 USD required")
    components = {row["id"]: row for row in base_report["components"]}
    if set(components) != {"engine_context", "drive_observed", "rotor_candidate", "provisional_shroud"}:
        raise ValueError("Four-component 935 base required")
    if components["drive_observed"]["sha256"] != DRIVE_SHA256:
        raise ValueError("Witness and USD drive frames do not share the same mesh")
    receipt_path = witness_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if (receipt["status"] != "PicoGK_scan_feature_witness_only"
            or receipt["drive_stl_sha256"] != DRIVE_SHA256
            or receipt["report_sha256"] != "da8093bb6c71cd364035dfcf5ced88732062a108c0a8af2ead21e6b111900c3c"
            or receipt["source_unit_to_mm_verified"] is not False
            or receipt["interface_verified"] is not False
            or receipt["manufacturing_authorized"] is not False
            or len(receipt["openings"]) != 8):
        raise ValueError("Pinned unqualified PicoGK witnesses required")
    for index, row in enumerate(receipt["openings"]):
        if (row["id"] != index or row["file"] != f"opening_{index:02}.stl"
                or digest(witness_dir / row["file"]) != row["sha256"]):
            raise ValueError("Witness identity or mesh hash changed")

    output.mkdir(parents=True, mode=0o700)
    copied_base = output / "base-assembly.usdc"
    shutil.copyfile(base_stage, copied_base)
    if digest(copied_base) != base_report["usd_sha256"]:
        raise ValueError("Copied base USD changed")
    stage_path = output / "assembly-with-flange-witness.usdc"
    stage = Usd.Stage.CreateNew(str(stage_path))
    stage.GetRootLayer().subLayerPaths = ["base-assembly.usdc"]
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = stage.GetPrimAtPath("/World")
    if not world or not world.IsValid():
        raise ValueError("Base world did not compose")
    stage.SetDefaultPrim(world)
    inspection = UsdGeom.Xform.Define(stage, "/World/inspection")
    inspection.GetPrim().SetCustomData({"classification": "PicoGK_wall_location_witness_not_mounting_material",
                                        "PicoGK_receipt_sha256": digest(receipt_path),
                                        "source_unit_to_mm_verified": False,
                                        "physical_validation": False,
                                        "manufacturing_authorized": False})
    for index, row in enumerate(receipt["openings"]):
        vertices = np.asarray(triangles(witness_dir / row["file"], row["triangles"]), dtype=np.float32)
        points = (vertices.reshape(-1, 3).astype(np.float64) * .001).astype(np.float32)
        mesh = UsdGeom.Mesh.Define(stage, f"/World/inspection/flange_opening_{index:02}")
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
        mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(row["triangles"], 3, dtype=np.int32)))
        mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.arange(len(points), dtype=np.int32)))
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateDisplayColorAttr([Gf.Vec3f(.95, .12, .62)])
        mesh.CreateDisplayOpacityAttr([.75])
        mesh.CreateExtentAttr([Gf.Vec3f(*map(float, point)) for point in (points.min(axis=0), points.max(axis=0))])
        mesh.GetPrim().SetCustomData({"classification": "PicoGK_inspection_shell_not_part_material",
                                      "source_stl_sha256": row["sha256"], "source_unit_to_mm_verified": False})
    stage.GetRootLayer().Save()
    reopened = Usd.Stage.Open(str(stage_path), load=Usd.Stage.LoadNone)
    if (UsdGeom.GetStageMetersPerUnit(reopened) != 1 or UsdGeom.GetStageUpAxis(reopened) != UsdGeom.Tokens.z
            or reopened.GetDefaultPrim().GetPath().pathString != "/World"):
        raise ValueError("Composed USD metadata changed")
    if {p.GetName() for p in reopened.GetPrimAtPath("/World").GetChildren()} != set(components) | {"inspection"}:
        raise ValueError("Base component identity lost")
    if {p.GetName() for p in reopened.GetPrimAtPath("/World/inspection").GetChildren()} != {
            f"flange_opening_{i:02}" for i in range(8)}:
        raise ValueError("Witness identity lost")
    rows = []
    for index, row in enumerate(receipt["openings"]):
        source = triangles(witness_dir / row["file"], row["triangles"])
        expected = (np.asarray(source, dtype=np.float64).reshape(-1, 3) * .001).astype(np.float32)
        mesh = UsdGeom.Mesh(reopened.GetPrimAtPath(f"/World/inspection/flange_opening_{index:02}"))
        points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float32)
        indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int32)
        counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int32)
        if (not np.array_equal(points, expected)
                or not np.array_equal(indices, np.arange(len(expected), dtype=np.int32))
                or not np.all(counts == 3) or len(counts) != row["triangles"]):
            raise ValueError("Composed USD witness triangles differ from PicoGK STL")
        rows.append({"id": index, "triangles": len(counts), "source_stl_sha256": row["sha256"],
                     "usd_points_match_source_times_point_001_exactly": True})
    if digest(copied_base) != base_report["usd_sha256"]:
        raise ValueError("Base USD modified during composition")
    result = {"status": "inspection_usd_with_eight_picogk_witnesses",
              "base_usd_sha256": base_report["usd_sha256"],
              "PicoGK_witness_receipt_sha256": digest(receipt_path),
              "composed_usd_sha256": digest(stage_path), "stage_meters_per_unit": 1,
              "source_unit_to_stage_metre_factor_assumed": .001,
              "base_component_count": 4, "witness_component_count": 8,
              "witness_triangles": sum(row["triangles"] for row in rows), "witnesses": rows,
              "source_unit_to_mm_verified": False, "engine_mount_verified": False,
              "manufacturing_authorized": False, "physical_validation": False}
    (output / "composition-report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "composed_usd_sha256": result["composed_usd_sha256"],
                      "witness_triangles": result["witness_triangles"]}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: compose_flange_witness_usd.py BASE_EXPORT_DIR WITNESS_NATIVE_DIR NEW_PRIVATE_OUTPUT")
    run(*(Path(arg) for arg in sys.argv[1:]))
