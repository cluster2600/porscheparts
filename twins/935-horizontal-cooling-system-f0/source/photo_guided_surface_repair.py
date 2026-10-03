#!/usr/bin/env python3
"""Create a private, visual-only watertight reconstruction from an open scan.

The web photographs passed to this tool document the intended external topology
only. They do not register the scan, supply dimensions, or validate interfaces.
Raw scans and reconstructed meshes stay under an ignored work/ directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_private_output(output: Path) -> None:
    if output.exists():
        raise ValueError("Output directory must be new")
    for parent in (output, *output.parents):
        marker = parent / ".git"
        if marker.exists():
            relative = output.relative_to(parent)
            if not relative.parts or relative.parts[0] != "work":
                raise ValueError("Output must be under ignored work/ in a repository")
            return
    raise ValueError("Output must be inside a repository work/ directory")


def require_photo_references(references: list[str]) -> list[str]:
    if not references:
        raise ValueError("At least one web photograph reference is required")
    if len(set(references)) != len(references):
        raise ValueError("Photo references must be unique")
    for reference in references:
        if not reference.startswith("https://"):
            raise ValueError("Photo references must use HTTPS URLs")
    return references


def audit(mesh_path: Path) -> dict:
    import trimesh

    # Binary STL repeats vertices per triangle; merge equal coordinates before
    # assessing closure so that the audit tests topology, not serialization.
    mesh = trimesh.load(mesh_path, force="mesh", process=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError("Expected one reconstructed mesh")
    components = mesh.split(only_watertight=False)
    return {
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.faces),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "connected_components": len(components),
        "bounds": mesh.bounds.tolist(),
        "positive_volume_conditional": bool(mesh.is_watertight and mesh.volume > 0),
        "volume_source_units_cubed_conditional": float(mesh.volume) if mesh.is_watertight else None,
    }


def remove_poisson_dust(mesh_path: Path) -> dict:
    import trimesh

    mesh = trimesh.load(mesh_path, force="mesh", process=True)
    components = mesh.split(only_watertight=False)
    minimum_faces = max(100, len(mesh.faces) // 1_000)
    kept = [component for component in components if len(component.faces) >= minimum_faces]
    if not kept:
        raise ValueError("Poisson reconstruction contains no non-dust components")
    cleaned = trimesh.util.concatenate(kept)
    cleaned.export(mesh_path, file_type="stl")
    return {"input_components": len(components), "kept_components": len(kept),
            "minimum_faces": minimum_faces,
            "removed_faces": sum(len(component.faces) for component in components if len(component.faces) < minimum_faces)}


def pymeshlab_topology_audit(mesh_path: Path) -> dict:
    import pymeshlab

    checks = {}
    for name, key in (("compute_selection_by_self_intersections_per_face", "self_intersection_faces"),
                      ("compute_selection_by_non_manifold_edges_per_face", "non_manifold_edge_faces"),
                      ("compute_selection_by_non_manifold_per_vertex", "non_manifold_vertices")):
        meshset = pymeshlab.MeshSet()
        meshset.load_new_mesh(str(mesh_path))
        meshset.apply_filter(name)
        checks[key] = meshset.current_mesh().selected_face_number() if key != "non_manifold_vertices" else meshset.current_mesh().selected_vertex_number()
    return checks


def render_preview(mesh_path: Path, preview_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    import trimesh

    mesh = trimesh.load(mesh_path, force="mesh", process=True)
    figure = plt.figure(figsize=(12, 6), layout="constrained")
    for index, (a, b, title) in enumerate(((0, 2, "vue latérale"),
                                             (0, 1, "vue axiale")), 1):
        axis = figure.add_subplot(1, 2, index)
        polygons = mesh.vertices[mesh.faces][:, :, [a, b]]
        axis.add_collection(PolyCollection(polygons, facecolor="#547a9c", edgecolor="none", antialiased=False))
        axis.autoscale()
        axis.set(title=title, aspect="equal")
        axis.set_axis_off()
    figure.suptitle("935 — reconstruction visuelle privée, surfaces complétées par Poisson")
    figure.savefig(preview_path, dpi=180)
    plt.close(figure)


def reconstruct(input_path: Path, expected_sha256: str, output: Path,
                photo_references: list[str], target_faces: int, poisson_depth: int) -> dict:
    if sha256(input_path) != expected_sha256:
        raise ValueError("Input scan hash mismatch")
    if target_faces < 10_000 or poisson_depth not in range(6, 13):
        raise ValueError("Unsupported visual reconstruction resolution")
    require_private_output(output)
    photo_references = require_photo_references(photo_references)
    try:
        import pymeshlab
    except ImportError as error:
        raise RuntimeError("Install pymeshlab in a private numerical environment") from error

    output.mkdir(parents=True)
    scan_copy = output / "source-open-scan-copy.obj"
    shutil.copy2(input_path, scan_copy)
    meshset = pymeshlab.MeshSet()
    meshset.load_new_mesh(str(scan_copy))
    source = {"vertices": meshset.current_mesh().vertex_number(),
              "triangles": meshset.current_mesh().face_number()}
    meshset.apply_filter("meshing_decimation_quadric_edge_collapse",
                         targetfacenum=target_faces, preserveboundary=True,
                         preservenormal=True, preservetopology=False,
                         autoclean=True)
    meshset.apply_filter("compute_normal_per_face")
    meshset.apply_filter("compute_normal_per_vertex")
    meshset.apply_filter("generate_surface_reconstruction_screened_poisson",
                         depth=poisson_depth, fulldepth=5, cgdepth=0,
                         scale=1.1, samplespernode=1.5, pointweight=4.0,
                         iters=8, confidence=False, preclean=True, threads=8)
    meshset.apply_filter("compute_normal_per_face")
    meshset.apply_filter("compute_normal_per_vertex")
    repaired = output / "repaired-visual-only.stl"
    meshset.save_current_mesh(str(repaired), binary=True)
    source_copy_hash = sha256(scan_copy)
    if source_copy_hash != expected_sha256 or sha256(input_path) != expected_sha256:
        raise ValueError("Input scan changed during reconstruction")
    dust_removal = remove_poisson_dust(repaired)
    result = audit(repaired)
    result["topology_screen"] = pymeshlab_topology_audit(repaired)
    preview = output / "visual-reconstruction-preview.png"
    render_preview(repaired, preview)
    receipt = {
        "status": "private_photo_guided_visual_reconstruction" if result["watertight"] else "private_photo_guided_reconstruction_rejected",
        "input_sha256": expected_sha256,
        "input": source,
        "method": {
            "scan": "quadric decimation, normal estimation, screened Poisson closure",
            "photo_use": "external topology and blade-layout review only; no camera registration or numerical geometry derived from photographs",
            "target_faces": target_faces,
            "poisson_depth": poisson_depth,
        },
        "photo_references": photo_references,
        "result": result,
        "poisson_dust_removal": dust_removal,
        "scale_verified": False,
        "interfaces_verified": False,
        "dimensionally_accurate": False,
        "solver_ready": False,
        "manufacturing_authorized": False,
        "raw_scan_published": False,
        "output_sha256": sha256(repaired),
        "preview_sha256": sha256(preview),
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("sha256")
    parser.add_argument("output", type=Path)
    parser.add_argument("--photo-reference", action="append", default=[])
    parser.add_argument("--target-faces", type=int, default=180_000)
    parser.add_argument("--poisson-depth", type=int, default=9)
    args = parser.parse_args()
    receipt = reconstruct(args.input.resolve(), args.sha256, args.output.resolve(),
                          args.photo_reference, args.target_faces, args.poisson_depth)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
