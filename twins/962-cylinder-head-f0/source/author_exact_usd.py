"""Author original mesh coordinates as USDA; separate from vendor conversion."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reader():
    path = Path(__file__).with_name("mesh_head.py")
    spec = importlib.util.spec_from_file_location("exact_usd_stl_reader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def xyz(point):
    # Nine significant decimal digits round-trip every finite IEEE binary32.
    return "(" + ", ".join(format(float(v), ".9g") for v in point) + ")"


def author(source, output):
    source, output = Path(source), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Output must be new; preserve previous evidence")
    before = sha(source)
    mesh = reader()
    original, points, faces = mesh.read_binary_stl(source)
    if not (points[faces] == original).all():
        raise ValueError("Original oriented triangle reconstruction changed")
    lo, hi = points.min(axis=0), points.max(axis=0)
    with output.open("x", encoding="utf-8") as stream:
        stream.write('#usda 1.0\n(\n    defaultPrim = "Head"\n'
                     '    metersPerUnit = 0.001\n    upAxis = "Z"\n'
                     '    customLayerData = {\n'
                     f'        string sourceSTLSHA256 = "{before}"\n'
                     '        string authoringRoute = "exact-source-mesh"\n'
                     '    }\n)\n\ndef Xform "Head"\n{\n'
                     '    def Mesh "Solid"\n    {\n'
                     '        uniform token subdivisionScheme = "none"\n'
                     '        uniform token orientation = "rightHanded"\n'
                     f'        float3[] extent = [{xyz(lo)}, {xyz(hi)}]\n'
                     '        point3f[] points = [\n')
        for point in points:
            stream.write("            " + xyz(point) + ",\n")
        stream.write("        ]\n        int[] faceVertexCounts = [\n")
        for _ in faces:
            stream.write("            3,\n")
        stream.write("        ]\n        int[] faceVertexIndices = [\n")
        for face in faces:
            stream.write("            " + ", ".join(str(int(v)) for v in face) + ",\n")
        stream.write("        ]\n    }\n}\n")
    if sha(source) != before:
        raise ValueError("Source changed during read-only authoring")
    return {
        "status": "source_mesh_authored_not_yet_native_USD_validated",
        "route": "explicit_exact_OpenUSD_source_authoring_not_vendor_conversion",
        "source_sha256": before, "source_unchanged": True,
        "source_triangles": len(original), "indexed_points": len(points),
        "bounds_mm": [lo.tolist(), hi.tolist()],
        "source_float32_coordinate_reconstruction_exact": True,
        "writer_sha256": sha(Path(__file__)),
        "reader_sha256": sha(Path(mesh.__file__)),
        "python_version": platform.python_version(),
        "USDA_sha256": sha(output), "USDA_bytes": output.stat().st_size,
        "frame": {"up_axis": "Z", "meters_per_unit": 0.001,
                  "transform": "identity", "subdivision_scheme": "none"},
        "material_assigned": False, "physics_schemas_assigned": False,
        "solver_fields_imported": False, "manufacturing_authorized": False,
    }


def save_native(source, output):
    source, output = Path(source), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Output must be new; preserve previous evidence")
    before = sha(source)
    import usd_convert_cad
    from pxr import Usd, UsdGeom
    if usd_convert_cad.get_version() != "0.2.0":
        raise ValueError("Expected the verified isolated bundled runtime 0.2.0")
    stage = Usd.Stage.Open(str(source), Usd.Stage.LoadAll)
    if not stage:
        raise ValueError("Authored source USDA did not open")
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/Head/Solid"))
    if (not mesh or UsdGeom.GetStageUpAxis(stage) != "Z"
            or UsdGeom.GetStageMetersPerUnit(stage) != 0.001
            or mesh.GetSubdivisionSchemeAttr().Get() != "none"):
        raise ValueError("Expected original-frame Z/mm unsubdivided source mesh")
    # Claim a new path exclusively; Export can replace only our empty placeholder.
    with output.open("xb"):
        pass
    if not stage.GetRootLayer().Export(str(output), args={"format": "usdc"}):
        raise ValueError("Native OpenUSD serialization failed")
    if sha(source) != before:
        raise ValueError("Authored source USDA changed during native serialization")
    return {
        "status": "native_exact_source_serialized_independent_audit_required",
        "route": "explicit_exact_OpenUSD_source_authoring_not_vendor_conversion",
        "USDA_sha256": before, "USDA_unchanged": True,
        "USD_sha256": sha(output), "USD_bytes": output.stat().st_size,
        "writer_sha256": sha(Path(__file__)),
        "python_version": platform.python_version(),
        "bundled_converter_package_version": usd_convert_cad.get_version(),
        "OpenUSD_version": Usd.GetVersion(),
        "material_assigned": False, "physics_schemas_assigned": False,
        "solver_fields_imported": False, "manufacturing_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--native-save", action="store_true",
                        help="Serialize the separately authored USDA with existing native OpenUSD")
    args = parser.parse_args()
    if args.report and (args.report.exists() or args.report.is_symlink()):
        raise FileExistsError("Report must be new; preserve previous evidence")
    result = (save_native if args.native_save else author)(args.source, args.output)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.report:
        with args.report.open("x", encoding="utf-8") as stream:
            stream.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
