"""Classify observed mesh boundaries around the 935 drive's axial openings."""

import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

DRIVE_SHA256 = "fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35"
DTYPE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
SEEDS = ((0.0, 30.0), (0.0, -30.0))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def roi_triangles(path: Path) -> np.ndarray:
    with path.open("rb") as stream:
        header = stream.read(84)
    if len(header) != 84:
        raise ValueError("Binary STL header required")
    count = struct.unpack("<I", header[80:])[0]
    if not 1 <= count <= 5_000_000 or path.stat().st_size != 84 + 50 * count:
        raise ValueError("Complete bounded binary STL required")
    mesh = np.memmap(path, mode="r", dtype=DTYPE, offset=84, shape=(count,))["vertices"]
    chunks = []
    for offset in range(0, count, 100_000):
        triangles = np.asarray(mesh[offset:offset + 100_000])
        centre = triangles.mean(axis=1)
        keep = ((np.hypot(centre[:, 0], centre[:, 1]) < 50)
                & (centre[:, 2] > -58) & (centre[:, 2] < -34))
        chunks.append(triangles[keep])
    return np.concatenate(chunks)


def boundary_components(triangles: np.ndarray) -> tuple[np.ndarray, list[dict], int]:
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    edges = np.sort(np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]],
                                    faces[:, [2, 0]])), axis=1)
    unique, count = np.unique(edges, axis=0, return_counts=True)
    boundary = unique[count == 1]
    degree = np.bincount(boundary.ravel(), minlength=len(vertices))
    graph = coo_matrix((np.ones(2 * len(boundary), dtype=np.uint8),
                        (np.r_[boundary[:, 0], boundary[:, 1]],
                         np.r_[boundary[:, 1], boundary[:, 0]])),
                       shape=(len(vertices), len(vertices))).tocsr()
    _, labels = connected_components(graph, directed=False)
    components = []
    for label in np.unique(labels[boundary[:, 0]]):
        component_edges = boundary[labels[boundary[:, 0]] == label]
        indices = np.unique(component_edges)
        points = vertices[indices].astype(np.float64)
        centroid = points.mean(axis=0)
        extent_min, extent_max = points.min(axis=0), points.max(axis=0)
        near_roi_cut = bool((np.hypot(points[:, 0], points[:, 1]).max() >= 49)
                            or extent_min[2] <= -57 or extent_max[2] >= -35)
        components.append({"edge_count": len(component_edges),
                           "vertex_count": len(indices),
                           "all_boundary_vertices_degree_two": bool(np.all(degree[indices] == 2)),
                           "centroid_source_units": centroid.tolist(),
                           "bbox_min_source_units": extent_min.tolist(),
                           "bbox_max_source_units": extent_max.tolist(),
                           "near_roi_cut": near_roi_cut,
                           "vertices": points})
    components.sort(key=lambda row: (-row["edge_count"], row["centroid_source_units"][1]))
    for index, row in enumerate(components):
        row["id"] = f"boundary-{index:03d}"
    return vertices, components, int(np.sum(count > 2))


def fixture() -> None:
    outer = np.array([[-2, -2, 0], [2, -2, 0], [2, 2, 0], [-2, 2, 0]])
    inner = outer / 2
    vertices = np.concatenate((outer, inner))
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.extend(((i, j, j + 4), (i, j + 4, i + 4)))
    _, components, nonmanifold = boundary_components(vertices[np.asarray(faces)])
    if (len(components) != 2 or sorted(row["edge_count"] for row in components) != [4, 4]
            or not all(row["all_boundary_vertices_degree_two"] for row in components)
            or nonmanifold):
        raise ValueError("Annular two-loop boundary fixture failed")


def render(triangles: np.ndarray, selected: list[list[dict]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, panels = plt.subplots(2, 2, figsize=(12, 9))
    centre = triangles.mean(axis=1)
    for row, (seed, contours) in enumerate(zip(SEEDS, selected)):
        near = centre[np.hypot(centre[:, 0] - seed[0], centre[:, 1] - seed[1]) < 7]
        for column, (i, j, title) in enumerate(((0, 1, "XY"), (1, 2, "YZ"))):
            ax = panels[row, column]
            ax.scatter(near[:, i], near[:, j], c="#b8c0c8", s=.25, rasterized=True)
            for index, contour in enumerate(contours):
                points = contour["vertices"]
                ax.scatter(points[:, i], points[:, j], s=2,
                           label=f"boundary {index + 1}: {contour['edge_count']} edges")
            ax.set(xlabel="XYZ"[i] + ", source units", ylabel="XYZ"[j] + ", source units",
                   title=f"Seed {seed}, {title}")
            ax.set_aspect("equal")
            ax.legend(fontsize=8)
    fig.suptitle("935 drive observed boundary contours; mesh topology does not identify a mounting hole")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(drive: Path, output: Path) -> None:
    drive, output = drive.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ output directory")
    if digest(drive) != DRIVE_SHA256:
        raise ValueError("Pinned observed drive surface changed")
    fixture()
    triangles = roi_triangles(drive)
    vertices, components, nonmanifold = boundary_components(triangles)
    selected = []
    for seed in SEEDS:
        candidates = [row for row in components
                      if np.linalg.norm(np.asarray(row["centroid_source_units"][:2]) - seed) < 5
                      and not row["near_roi_cut"] and row["edge_count"] >= 30]
        if len(candidates) != (1 if seed[1] > 0 else 2):
            raise ValueError("Observed opening-boundary contour count changed")
        selected.append(candidates)
    result = {"status": "observed_opening_boundary_topology_not_mounting_classification",
              "drive_stl_sha256": DRIVE_SHA256,
              "roi": {"centroid_radius_max_source_units": 50,
                      "centroid_z_open_interval_source_units": [-58, -34]},
              "roi_triangles": len(triangles), "roi_unique_exact_float_vertices": len(vertices),
              "boundary_edges": sum(row["edge_count"] for row in components),
              "boundary_components": len(components), "edges_with_more_than_two_incident_faces": nonmanifold,
              "annular_boundary_fixture_passed": True,
              "all_component_summaries": [{key: value for key, value in row.items() if key != "vertices"}
                                          for row in components],
              "seed_contours": [[{key: value for key, value in row.items() if key != "vertices"}
                                 for row in rows] for rows in selected],
              "roi_selection_can_create_other_boundary_contours": True,
              "source_unit_to_mm_verified": False, "physical_hole_count_verified": False,
              "through_condition_verified": False, "mounting_role_verified": False,
              "manufacturing_authorized": False}
    output.mkdir(parents=True, mode=0o700)
    report = output / "opening-boundaries.json"
    report.write_text(json.dumps(result, indent=2) + "\n")
    render(triangles, selected, output / "opening-boundaries.png")
    for path in output.iterdir():
        path.chmod(0o600)
    print(json.dumps({"status": result["status"], "report_sha256": digest(report),
                      "image_sha256": digest(output / "opening-boundaries.png")}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: audit_drive_opening_boundaries.py PINNED_DRIVE_STL NEW_PRIVATE_OUTPUT_DIR")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
