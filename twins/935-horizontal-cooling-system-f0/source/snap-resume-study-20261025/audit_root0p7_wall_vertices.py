"""Measure all rotor and OpenFOAM-wall vertices against opposing triangles."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import trimesh
from trimesh.proximity import closest_point

EXPECTED_ROTOR_SHA256 = "ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6"
EXPECTED_WALL_SHA256 = {
    3: "d1d56bd0f3dc7bafbfd83cb3b11629037c640c1c1736b0780aec012fa5e63d79",
    5: "2458f4877b0d6c3bb50b8906ba9f0c08d8e3215d65545a6d584bfa63a6acc7ee",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def distances(source: trimesh.Trimesh, target: trimesh.Trimesh) -> np.ndarray:
    result = np.empty(len(source.vertices), dtype=np.float64)
    for start in range(0, len(result), 5000):
        stop = min(start + 5000, len(result))
        _, found, _ = closest_point(target, source.vertices[start:stop])
        if not np.isfinite(found).all() or np.any(found < 0):
            raise ValueError("Invalid closest-triangle distances")
        result[start:stop] = found
    return result


def summarize(mesh: trimesh.Trimesh, values: np.ndarray) -> dict:
    worst = int(np.argmax(values))
    return {"unique_vertices_checked": len(values),
            "p50_mm_conditional": float(np.quantile(values, .5) * 1000),
            "p95_mm_conditional": float(np.quantile(values, .95) * 1000),
            "p99_mm_conditional": float(np.quantile(values, .99) * 1000),
            "max_mm_conditional": float(values[worst] * 1000),
            "max_vertex_index": worst,
            "max_vertex_coordinates_m_conditional": mesh.vertices[worst].tolist()}


def render(rotor: trimesh.Trimesh, rows: list[dict], arrays: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    names = ["spacing 3", "spacing 5"]
    for axis, key, title in ((axes[0], "wall_to_rotor", "Wall vertices to rotor"),
                             (axes[1], "rotor_to_wall", "Rotor vertices to wall")):
        width = .32
        x = np.arange(2)
        axis.bar(x - width / 2, [row[key]["p95_mm_conditional"] for row in rows],
                 width, label="p95")
        axis.bar(x + width / 2, [row[key]["max_mm_conditional"] for row in rows],
                 width, label="max")
        axis.set(xticks=x, xticklabels=names, ylabel="Distance, conditional mm", title=title)
        axis.legend()
    indices = np.linspace(0, len(rotor.vertices) - 1, 20_000, dtype=int)
    points = rotor.vertices[indices]
    values = arrays["rotor_to_wall_spacing5_m"][indices] * 1000
    scatter = axes[2].scatter(points[:, 0], points[:, 1], c=values, s=1,
                              cmap="magma", vmin=0, vmax=.6)
    worst = rows[1]["rotor_to_wall"]["max_vertex_coordinates_m_conditional"]
    axes[2].plot(worst[0], worst[1], marker="x", color="cyan", markersize=8)
    axes[2].set(xlabel="X, conditional m", ylabel="Y, conditional m",
                title="Rotor → spacing-5 wall; sampled display")
    axes[2].set_aspect("equal")
    fig.colorbar(scatter, ax=axes[2], label="Distance, conditional mm")
    fig.suptitle("935 corrected rotor: all vertices checked; triangle interiors not bounded")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def run(rotor_path: Path, wall3_path: Path, wall5_path: Path, output: Path) -> None:
    paths = {"rotor": rotor_path.resolve(), "wall3": wall3_path.resolve(),
             "wall5": wall5_path.resolve()}
    output = output.resolve()
    if output.exists() or output in (path.parent for path in paths.values()):
        raise ValueError("Use a fresh private output directory")
    if (digest(paths["rotor"]) != EXPECTED_ROTOR_SHA256
            or any(digest(paths[f"wall{spacing}"]) != EXPECTED_WALL_SHA256[spacing]
                   for spacing in (3, 5))):
        raise ValueError("Unexpected corrected rotor or exported wall")
    rotor = trimesh.load_mesh(paths["rotor"], process=True)
    if len(rotor.vertices) != 439_365 or len(rotor.faces) != 878_730:
        raise ValueError("Unexpected corrected rotor topology")
    rows = []
    arrays = {}
    for spacing in (3, 5):
        wall = trimesh.load_mesh(paths[f"wall{spacing}"], process=True)
        wall_to = distances(wall, rotor)
        rotor_to = distances(rotor, wall)
        arrays[f"wall_to_rotor_spacing{spacing}_m"] = wall_to
        arrays[f"rotor_to_wall_spacing{spacing}_m"] = rotor_to
        rows.append({"spacing": spacing, "wall_stl_sha256": EXPECTED_WALL_SHA256[spacing],
                     "wall_faces": len(wall.faces), "rotor_faces": len(rotor.faces),
                     "wall_to_rotor": summarize(wall, wall_to),
                     "rotor_to_wall": summarize(rotor, rotor_to)})
    output.mkdir(mode=0o700)
    data = output / "wall-vertex-distances.npz"
    np.savez_compressed(data, **arrays)
    image = output / "wall-vertex-distances.png"
    render(rotor, rows, arrays, image)
    report = {"status": "all_unique_vertices_checked_not_full_surface_acceptance",
              "analysis_source_sha256": digest(Path(__file__)),
              "rotor_obj_sha256": EXPECTED_ROTOR_SHA256,
              "rotor_vertices": len(rotor.vertices), "cases": rows,
              "arrays_sha256": digest(data), "image_sha256": digest(image),
              "all_unique_vertices_checked": True,
              "triangle_interior_supremum_verified": False,
              "source_unit_to_mm_verified": False,
              "mesh_quality_passed": False, "CFD_accepted": False,
              "manufacturing_authorized": False}
    path = output / "wall-vertex-distances.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for result in (data, image, path):
        result.chmod(0o600)
    print(json.dumps({"status": report["status"],
                      "report_sha256": digest(path),
                      "arrays_sha256": report["arrays_sha256"],
                      "image_sha256": report["image_sha256"]}))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: audit_root0p7_wall_vertices.py ROTOR_OBJ WALL3_STL WALL5_STL NEW_PRIVATE_OUTPUT")
    run(*(Path(arg) for arg in sys.argv[1:]))
