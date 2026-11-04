"""Create a private, source-preserving scan workspace before cell reconstruction."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REGISTRATION = ROOT / "twins/964-chassis/derived/scan-recalage-20260925.json"
REGIONS = HERE / "regions.json"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def admit(scan, vertices_path, faces_path):
    receipt = json.loads(REGISTRATION.read_text())
    for path, expected in ((scan, receipt["source_sha256"]),
                           (vertices_path, receipt["outputs"]["verts_vehicle.npy"]),
                           (faces_path, receipt["outputs"]["faces.npy"])):
        if digest(path) != expected:
            raise ValueError("Input does not match the retained scan registration")
    vertices = np.load(vertices_path, allow_pickle=False)
    faces = np.load(faces_path, allow_pickle=False)
    if vertices.shape != (2400031, 3) or faces.shape != (4684929, 3):
        raise ValueError("Unexpected source-array shape")
    if not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError("Invalid source arrays")
    return vertices, faces, receipt


def partition(vertices, faces, regions):
    """Whole source faces only; preserve every face exactly once in the assembly."""
    assigned = np.zeros(len(faces), dtype=bool)
    groups = {}
    for region in regions:
        bounds = np.array(region["bounds"]).reshape(3, 2)
        inside = ((vertices >= bounds[:, 0]) & (vertices <= bounds[:, 1])).all(axis=1)
        selected = inside[faces].all(axis=1) & ~assigned
        groups[region["name"]] = np.flatnonzero(selected).astype(np.int32)
        assigned |= selected
    groups["Context"] = np.flatnonzero(~assigned).astype(np.int32)
    return groups


def plane_segments(vertices, faces, axis, position, scope, tolerance=1e-6):
    """Intersect source triangles without joining gaps or inventing closed sections.

    Triangles touching the plane at a vertex/edge within numerical tolerance are
    counted separately and excluded, including coplanar triangles. That policy
    avoids ambiguous duplicate segments; tolerance is not metrology uncertainty.
    """
    if axis not in (0, 1, 2) or not math.isfinite(position):
        raise ValueError("Invalid section plane")
    bounds = np.asarray(scope, dtype=float).reshape(3, 2)
    if not np.isfinite(bounds).all() or (bounds[:, 0] > bounds[:, 1]).any():
        raise ValueError("Invalid section scope")
    inside = ((vertices >= bounds[:, 0]) & (vertices <= bounds[:, 1])).all(axis=1)
    eligible = np.flatnonzero(inside[faces].all(axis=1))
    tri = vertices[faces[eligible]].astype(np.float64)
    delta = tri[:, :, axis] - position
    touching = np.any(np.abs(delta) <= tolerance, axis=1)
    crossing = (delta.min(axis=1) < -tolerance) & (delta.max(axis=1) > tolerance)
    selected = crossing & ~touching
    ids, tri, delta = eligible[selected], tri[selected], delta[selected]
    ends = np.empty((len(ids), 2, 3), dtype=np.float64)
    counts = np.zeros(len(ids), dtype=np.int8)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        rows = np.flatnonzero(delta[:, a] * delta[:, b] < 0)
        weight = -delta[rows, a] / (delta[rows, b] - delta[rows, a])
        ends[rows, counts[rows]] = tri[rows, a] + weight[:, None] * (tri[rows, b] - tri[rows, a])
        counts[rows] += 1
    if not np.all(counts == 2):
        raise ValueError("Unexpected triangle-plane intersection multiplicity")
    return ids.astype(np.int32), ends, int(touching.sum())


def write_stage(vertices, faces, groups, config, target):
    from pxr import Gf, Sdf, Usd, UsdGeom, Vt
    stage = Usd.Stage.CreateNew(str(target))
    root = UsdGeom.Xform.Define(stage, "/ScanReview").GetPrim()
    stage.SetDefaultPrim(root)
    UsdGeom.SetStageMetersPerUnit(stage, 0.001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root.CreateAttribute("scan:classification", Sdf.ValueTypeNames.String).Set(
        "Observed source triangles; search windows are not accepted body components")
    for flag in ("bodySegmentationValidated", "structuralDatumsRegistered",
                 "fitmentValidated", "manufacturingReleased", "interiorSurfacesReconstructed"):
        root.CreateAttribute("scan:" + flag, Sdf.ValueTypeNames.Bool).Set(False)
    colours = {r["name"]: r["colour"] for r in config["regions"]}
    metadata = {}
    for name, face_ids in groups.items():
        selected = faces[face_ids]
        vertex_ids, inverse = np.unique(selected, return_inverse=True)
        points = np.ascontiguousarray(vertices[vertex_ids], dtype=np.float32)
        mesh = UsdGeom.Mesh.Define(stage, "/ScanReview/Observed/" + name)
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
        mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(selected), 3, dtype=np.int32)))
        mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(inverse.astype(np.int32)))
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateDoubleSidedAttr(True)
        if len(points):
            mesh.CreateExtentAttr([Gf.Vec3f(*map(float, points.min(axis=0))), Gf.Vec3f(*map(float, points.max(axis=0)))])
        mesh.CreateDisplayColorAttr([Gf.Vec3f(*colours.get(name, [0.57, 0.59, 0.63]))])
        prim = mesh.GetPrim()
        prim.CreateAttribute("scan:sourceVertexIds", Sdf.ValueTypeNames.IntArray).Set(
            Vt.IntArray.FromNumpy(vertex_ids.astype(np.int32)))
        prim.CreateAttribute("scan:sourceFaceIds", Sdf.ValueTypeNames.IntArray).Set(
            Vt.IntArray.FromNumpy(face_ids))
        prim.CreateAttribute("scan:componentIdentified", Sdf.ValueTypeNames.Bool).Set(False)
        metadata[name] = {"source_triangles": len(face_ids), "source_vertices": len(vertex_ids),
                          "source_face_ids_sha256": hashlib.sha256(face_ids.astype("<i4").tobytes()).hexdigest()}
    for name in config["unobserved_requirements"]:
        prim = UsdGeom.Xform.Define(stage, "/ScanReview/RequiredUnobserved/" + name).GetPrim()
        prim.CreateAttribute("scan:status", Sdf.ValueTypeNames.String).Set("required_surface_not_established_by_this_scan_review")
    stage.GetRootLayer().Save()
    return metadata


def render(stage_path, config, output):
    """Render only the reopened USD; colours identify search zones, not materials."""
    from pxr import Usd, UsdGeom
    import pyvista as pv
    stage = Usd.Stage.Open(str(stage_path))
    meshes = []
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            m = UsdGeom.Mesh(prim)
            points = np.array(m.GetPointsAttr().Get())
            indices = np.array(m.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
            poly = pv.PolyData(points, np.column_stack((np.full(len(indices), 3), indices)))
            meshes.append((poly, tuple(m.GetDisplayColorAttr().Get()[0])))
    plot = pv.Plotter(off_screen=True, window_size=(1600, 1000))
    try:
        plot.set_background("#e5e9ee")
        for poly, colour in meshes:
            plot.add_mesh(poly, color=colour, smooth_shading=False)
        plot.add_text("964 | OBSERVED UNDERBODY WORKSPACE\nSearch regions, not a reconstructed carbon cell", font_size=15, color="black")
        plot.add_text("Source triangles unchanged | Local VTK view of reopened USD\nOpposite-side visibility is not an interior scan | Provisional frame, mm", position="lower_left", font_size=11, color="black")
        plot.enable_parallel_projection()
        views = {
            "underbody": ([(-1100, 0, -3300), (-1100, 0, 300), (1, 0, 0)], 2300),
            "oblique": ([(-2300, -3300, -1900), (-1100, 0, 300), (0, 0, 1)], 2100),
            "left_side": ([(-1100, 3500, 300), (-1100, 0, 300), (0, 0, 1)], 2100),
            "central_floor": ([(-1075, 0, -2300), (-1075, 0, 300), (1, 0, 0)], 1050),
        }
        images = {}
        for name, (camera, scale) in views.items():
            plot.camera_position = camera
            plot.camera.parallel_scale = scale
            target = output / (name + ".png")
            plot.render()
            plot.screenshot(target)
            images[name] = {"camera": camera, "parallel_scale_mm": scale, "sha256": digest(target)}
        if len({image["sha256"] for image in images.values()}) != len(images):
            raise ValueError("Distinct inspection cameras produced repeated images")
        frame_samples = {}
        video = output / "underbody-orbit.mp4"
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
                   "-video_size", "1600x1000", "-framerate", "24", "-i", "pipe:0", "-an",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", str(video)]
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            for index in range(120):
                angle = 2 * math.pi * index / 120
                plot.camera_position = [(-1100 + 2900 * math.cos(angle), 2900 * math.sin(angle), -2100),
                                        (-1100, 0, 300), (0, 0, 1)]
                plot.camera.parallel_scale = 2300
                plot.render()
                frame = plot.screenshot(return_img=True)[:, :, :3]
                if index in (0, 30, 60, 90):
                    frame_samples[str(index)] = hashlib.sha256(np.ascontiguousarray(frame).tobytes()).hexdigest()
                encoder.stdin.write(np.ascontiguousarray(frame).tobytes())
            encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError("Video encoding failed")
        if len(set(frame_samples.values())) != 4:
            raise ValueError("Quarter-orbit frames are repeated")
        return {"images": images, "video": {"path": video.name, "sha256": digest(video), "frames": 120, "fps": 24, "raw_frame_samples_sha256": frame_samples},
                "pyvista": pv.__version__, "vtk": str(pv.vtk_version_info)}
    finally:
        plot.close()


def render_sections(section_data, target):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    fig, axes = plt.subplots(3, 2, figsize=(16, 12), constrained_layout=True)
    for ax, (entry, segments) in zip(axes.flat, section_data):
        horizontal = 1 if entry["axis"] == 0 else 0
        ax.add_collection(LineCollection(segments[:, :, [horizontal, 2]], linewidths=0.7, colors="#125978"))
        ax.autoscale()
        ax.set_ylim(0, 1100)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(entry["name"] + " | observed intersections")
        ax.set_xlabel(("Y" if horizontal == 1 else "X") + " (provisional mm)")
        ax.set_ylabel("Z (provisional mm)")
        ax.grid(alpha=0.2)
    fig.suptitle("964 source-triangle sections | gaps remain gaps; no enclosed cell or interior inferred", fontsize=15)
    fig.savefig(target, dpi=120)
    plt.close(fig)


def build(scan, vertices_path, faces_path, output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "work") or output.exists():
        raise ValueError("Output must be a new private directory under repository work/")
    vertices, faces, receipt = admit(scan, vertices_path, faces_path)
    config = json.loads(REGIONS.read_text())
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".cell-scan-", dir=output.parent))
    try:
        groups = partition(vertices, faces, config["regions"])
        metadata = write_stage(vertices, faces, groups, config, staging / "observed-underbody.usdc")
        sections, section_data = {}, []
        for entry in config["sections"]:
            ids, segments, touching = plane_segments(vertices, faces, entry["axis"], entry["position_mm"], config["section_scope_bounds"])
            archive = staging / (entry["name"] + ".npz")
            np.savez_compressed(archive, source_face_ids=ids, endpoints=segments)
            sections[entry["name"]] = {"segments": len(ids), "touching_triangles_excluded": touching, "sha256": digest(archive)}
            section_data.append((entry, segments))
        render_sections(section_data, staging / "sections.png")
        checker = subprocess.run(["usdchecker", "--strict", str(staging / "observed-underbody.usdc")], text=True, capture_output=True)
        (staging / "usdchecker.txt").write_text(checker.stdout + checker.stderr)
        if checker.returncode:
            raise ValueError("Strict USD check failed")
        media = render(staging / "observed-underbody.usdc", config, staging)
        # A separate reader/checker must verify the assembly before it is accepted.
        report = {"classification": "observed_scan_workspace_not_reconstructed_monocoque",
                  "source_sha256": receipt["source_sha256"],
                  "input_array_sha256": {"verts_vehicle.npy": digest(vertices_path), "faces.npy": digest(faces_path)},
                  "source_triangles": len(faces), "source_vertices": len(vertices), "groups": metadata,
                  "unselected_triangles_retained_as_context": len(groups["Context"]),
                  "search_region_triangles": sum(len(v) for k, v in groups.items() if k != "Context"),
                  "coverage_denominator": "All input faces; region counts are not percentage completion or semantic body coverage",
                  "sections": sections, "section_numerical_tolerance_mm": 1e-6,
                  "sections_image_sha256": digest(staging / "sections.png"),
                  "stage_sha256": digest(staging / "observed-underbody.usdc"),
                  "author_sha256": digest(__file__), "regions_sha256": digest(REGIONS),
                  "registration_sha256": digest(REGISTRATION),
                  "strict_usdchecker_exit_code": checker.returncode,
                  "python": platform.python_version(), "numpy": np.__version__, "media": media,
                  "publication": "USD, arrays, screenshots and video are private scan-derived data; no redistribution rights established",
                  "release_flags": {"body_segmentation_validated": False, "interior_reconstructed": False,
                                    "registered_hardpoints": False, "fitment_validated": False, "manufacturing_released": False}}
        if digest(scan) != receipt["source_sha256"]:
            raise ValueError("Original scan changed during review")
        (staging / "run.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        staging.rename(output)
        return report
    except BaseException:
        shutil.rmtree(staging)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.scan, args.vertices, args.faces, args.output)
    print(json.dumps({"source_triangles": result["source_triangles"], "search_region_triangles": result["search_region_triangles"],
                      "groups": {k: v["source_triangles"] for k, v in result["groups"].items()}}))


if __name__ == "__main__":
    main()
