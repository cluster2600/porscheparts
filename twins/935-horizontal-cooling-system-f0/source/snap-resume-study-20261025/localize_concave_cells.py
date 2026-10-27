"""Locate rejected OpenFOAM cells in a copied, unchanged-quality 935 mesh."""

import hashlib
import itertools
import json
from pathlib import Path
import re
import sys

import numpy as np

QUALITY_SHA256 = "bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d"
SOURCE_KEYS = ("constant/polyMesh/points", "constant/polyMesh/faces",
               "constant/polyMesh/owner", "constant/polyMesh/neighbour",
               "constant/polyMesh/boundary", "system/meshQualityDict")
RADIAL_BINS = np.array([0, .05, .10, .14, .18, .22, .27])
AXIAL_BINS = np.array([-.21, -.10, -.05, 0, .05, .10, .21])


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_set(path: Path) -> np.ndarray:
    with path.open() as stream:
        for line in stream:
            if line.strip().isdigit():
                count = int(line.strip())
                break
        else:
            raise ValueError("OpenFOAM cellSet count missing")
        if not 1 <= count <= 10_000_000 or next(stream).strip() != "(":
            raise ValueError("Invalid OpenFOAM cellSet header")
        values = np.fromiter((int(next(stream).strip()) for _ in range(count)),
                             dtype=np.int64, count=count)
        if next(stream).strip() != ")" or len(np.unique(values)) != count:
            raise ValueError("Incomplete or duplicate cellSet indices")
    return values


def read_label_list(path: Path) -> np.ndarray:
    with path.open() as stream:
        for line in stream:
            if line.strip().isdigit():
                count = int(line.strip())
                break
        else:
            raise ValueError("OpenFOAM label-list count missing")
        if not 1 <= count <= 20_000_000 or next(stream).strip() != "(":
            raise ValueError("Invalid OpenFOAM label-list header")
        values = np.fromiter((int(next(stream).strip()) for _ in range(count)),
                             dtype=np.int32, count=count)
        if next(stream).strip() != ")":
            raise ValueError("Incomplete OpenFOAM label list")
    return values


def rotor_graph_layers(case: Path, cell_count: int, bad_ids: np.ndarray) -> list[dict]:
    mesh = case / "constant/polyMesh"
    boundary = (mesh / "boundary").read_text()
    rotor = re.search(r"\brotor\s*\{([^{}]*)\}", boundary, re.DOTALL)
    if not rotor:
        raise ValueError("Rotor boundary patch missing")
    count_match = re.search(r"\bnFaces\s+(\d+)\s*;", rotor.group(1))
    start_match = re.search(r"\bstartFace\s+(\d+)\s*;", rotor.group(1))
    if not count_match or not start_match:
        raise ValueError("Rotor patch face interval missing")
    face_count, start = int(count_match.group(1)), int(start_match.group(1))
    owner, neighbour = read_label_list(mesh / "owner"), read_label_list(mesh / "neighbour")
    if (not len(neighbour) < start < len(owner) or start + face_count > len(owner)
            or owner.min() < 0 or neighbour.min() < 0
            or owner.max() >= cell_count or neighbour.max() >= cell_count):
        raise ValueError("Invalid native owner/neighbour or rotor face interval")
    bad = np.zeros(cell_count, dtype=bool)
    bad[bad_ids] = True
    reached = np.zeros(cell_count, dtype=bool)
    reached[owner[start:start + face_count]] = True
    rows = []
    previous_all = previous_bad = 0
    for depth in range(6):
        all_count = int(reached.sum())
        bad_count = int(np.count_nonzero(reached & bad))
        rows.append({"internal_face_graph_hops_from_rotor_wall": depth,
                     "new_cells": all_count - previous_all,
                     "new_concave_cells": bad_count - previous_bad,
                     "cumulative_cells": all_count,
                     "cumulative_concave_cells": bad_count,
                     "fraction_of_all_concave_reached": bad_count / len(bad_ids)})
        previous_all, previous_bad = all_count, bad_count
        if depth == 5:
            break
        incident = reached[owner[:len(neighbour)]] | reached[neighbour]
        expanded = reached.copy()
        expanded[owner[:len(neighbour)][incident]] = True
        expanded[neighbour[incident]] = True
        if int(expanded.sum()) <= all_count:
            raise ValueError("Graph expansion stopped before five layers")
        reached = expanded
    rows.append({"internal_face_graph_hops_from_rotor_wall": ">5",
                 "new_cells": cell_count - previous_all,
                 "new_concave_cells": len(bad_ids) - previous_bad})
    return rows


def centre_chunks(path: Path):
    with path.open() as stream:
        for line in stream:
            if line.lstrip().startswith("internalField"):
                break
        else:
            raise ValueError("OpenFOAM internalField missing")
        if "nonuniform List<vector>" not in line:
            raise ValueError("Expected ASCII nonuniform vector field")
        count = int(next(stream).strip())
        if not 1 <= count <= 10_000_000 or next(stream).strip() != "(":
            raise ValueError("Invalid OpenFOAM centre-field header")
        for offset in range(0, count, 100_000):
            lines = list(itertools.islice(stream, min(100_000, count - offset)))
            if len(lines) != min(100_000, count - offset) or any(
                    not row.strip().startswith("(") or not row.strip().endswith(")")
                    for row in lines):
                raise ValueError("Invalid or truncated vector field")
            values = np.fromstring(" ".join(lines).replace("(", " ").replace(")", " "),
                                   sep=" ")
            if len(values) != 3 * len(lines) or not np.isfinite(values).all():
                raise ValueError("Invalid centre coordinates")
            yield count, offset, values.reshape(-1, 3)
        if next(stream).strip() != ")":
            raise ValueError("OpenFOAM centre-field closing token missing")


def band_rows(edges: np.ndarray, all_counts: np.ndarray, bad_counts: np.ndarray) -> list[dict]:
    return [{"interval_m": [float(edges[i]), float(edges[i + 1])],
             "all_cells": int(all_counts[i]), "concave_cells": int(bad_counts[i]),
             "fraction": float(bad_counts[i] / all_counts[i]) if all_counts[i] else None}
            for i in range(len(edges) - 1)]


def render(all_grid: np.ndarray, bad_grid: np.ndarray, radial: np.ndarray,
           axial: np.ndarray, layers: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fraction = np.divide(bad_grid, all_grid, out=np.full_like(all_grid, np.nan, dtype=float),
                         where=all_grid >= 50)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for ax, grid, title, cmap in ((axes[0], all_grid, "All cell centres", "viridis"),
                                  (axes[1], fraction, "Concave-cell fraction, ≥50 cells/bin", "magma")):
        plot = ax.pcolormesh(axial, radial, grid, shading="auto", cmap=cmap)
        fig.colorbar(plot, ax=ax)
        ax.set(xlabel="Axial Z, m (conditional scale)", ylabel="Radius, m",
               title=title)
    axes[2].bar([str(row["internal_face_graph_hops_from_rotor_wall"]) for row in layers],
                [row["new_concave_cells"] for row in layers])
    axes[2].set(xlabel="Internal-face graph hops from rotor wall",
                ylabel="Concave cells in ring", title="Topology depth; >5 is unresolved")
    fig.suptitle("935 rejected CFD mesh: spatial diagnostic, not solver admission")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def run(case: Path, output: Path) -> None:
    case, output = case.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to(case.parent):
        raise ValueError("Use a new analysis output beside the copied case")
    execution = json.loads((case / "execution.json").read_text())
    if (execution["status"] != "diagnostic_only_rejected_mesh"
            or execution["CFD_accepted"] or execution["timeout"]
            or execution["source_input_sha256"] != execution["copied_input_sha256"]
            or set(execution["copied_input_sha256"]) != set(SOURCE_KEYS)
            or execution["copied_input_sha256"]["system/meshQualityDict"] != QUALITY_SHA256):
        raise ValueError("Unverified copied mesh or changed quality criteria")
    if any(digest(case / key) != execution["copied_input_sha256"][key] for key in SOURCE_KEYS):
        raise ValueError("Copied input changed after native check")
    source = Path(execution["source_case"])
    if any(digest(source / key) != execution["source_input_sha256"][key] for key in SOURCE_KEYS):
        raise ValueError("Parent case input changed after copying")
    log = (case / "log.checkMesh.localization").read_text()
    match = re.search(r"Concave cells .*number of cells: (\d+)", log)
    build = re.search(r"^Build\s*:\s*(\S+)", log, re.MULTILINE)
    if (not match or "Failed 1 mesh checks." not in log
            or not build or not build.group(1).startswith("13-")
            or "Number of duplicate (not baffle) faces found: 2" not in log):
        raise ValueError("Expected rejected native mesh diagnosis missing")
    bad_ids = read_set(case / "constant/polyMesh/sets/concaveCells")
    if len(bad_ids) != int(match.group(1)):
        raise ValueError("Native concave-cell set disagrees with log")
    centre_path = case / "constant/C"
    radial_all = np.zeros(len(RADIAL_BINS) - 1, dtype=np.int64)
    radial_bad = radial_all.copy()
    axial_all = np.zeros(len(AXIAL_BINS) - 1, dtype=np.int64)
    axial_bad = axial_all.copy()
    grid_radial = np.linspace(0, .27, 55)
    grid_axial = np.linspace(-.21, .21, 85)
    all_grid = np.zeros((len(grid_radial) - 1, len(grid_axial) - 1), dtype=np.int64)
    bad_grid = all_grid.copy()
    count = None
    for total, offset, centres in centre_chunks(centre_path):
        if count is None:
            count = total
            if bad_ids.min() < 0 or bad_ids.max() >= total:
                raise ValueError("Concave-cell index outside centre field")
        elif total != count:
            raise ValueError("Centre-field count changed between chunks")
        radius = np.hypot(centres[:, 0], centres[:, 1])
        z = centres[:, 2]
        selected = np.isin(np.arange(offset, offset + len(centres)), bad_ids, assume_unique=True)
        radial_all += np.histogram(radius, bins=RADIAL_BINS)[0]
        radial_bad += np.histogram(radius[selected], bins=RADIAL_BINS)[0]
        axial_all += np.histogram(z, bins=AXIAL_BINS)[0]
        axial_bad += np.histogram(z[selected], bins=AXIAL_BINS)[0]
        all_grid += np.histogram2d(radius, z, bins=(grid_radial, grid_axial))[0].astype(np.int64)
        bad_grid += np.histogram2d(radius[selected], z[selected],
                                   bins=(grid_radial, grid_axial))[0].astype(np.int64)
    if (int(radial_all.sum()) != count or int(axial_all.sum()) != count
            or int(radial_bad.sum()) != len(bad_ids)
            or int(axial_bad.sum()) != len(bad_ids)):
        raise ValueError("Spatial bins did not account for every cell")
    layers = rotor_graph_layers(case, count, bad_ids)
    result = {"status": "rejected_mesh_concavity_localized_not_CFD_admitted",
              "analysis_source_sha256": digest(Path(__file__)),
              "openfoam_build": build.group(1),
              "copied_case": str(case), "parent_mesh_sha256": execution["source_input_sha256"],
              "centre_field_sha256": digest(centre_path),
              "concave_set_sha256": digest(case / "constant/polyMesh/sets/concaveCells"),
              "native_log_sha256": digest(case / "log.checkMesh.localization"),
              "quality_dictionary_sha256": QUALITY_SHA256,
              "cell_count": count, "concave_cell_count": len(bad_ids),
              "radial_bands": band_rows(RADIAL_BINS, radial_all, radial_bad),
              "axial_bands": band_rows(AXIAL_BINS, axial_all, axial_bad),
              "rotor_wall_graph_layers": layers,
              "fraction_outside_rotor_axial_slab_abs_z_gt_0p05": float(
                  (axial_bad[0] + axial_bad[1] + axial_bad[-2] + axial_bad[-1]) / len(bad_ids)),
              "source_unit_to_mm_verified": False, "analysis_length_scale_conditional": True,
              "mesh_quality_passed": False, "CFD_executed": False,
              "CFD_accepted": False, "manufacturing_authorized": False}
    output.mkdir(mode=0o700)
    report = output / "concavity-localization.json"
    report.write_text(json.dumps(result, indent=2) + "\n")
    image = output / "concavity-localization.png"
    render(all_grid, bad_grid, grid_radial, grid_axial, layers, image)
    for path in output.iterdir():
        path.chmod(0o600)
    print(json.dumps({"status": result["status"], "concave_cell_count": len(bad_ids),
                      "outside_rotor_slab_fraction": result["fraction_outside_rotor_axial_slab_abs_z_gt_0p05"],
                      "report_sha256": digest(report), "image_sha256": digest(image)}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: localize_concave_cells.py COPIED_NATIVE_CASE NEW_PRIVATE_OUTPUT_DIR")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
