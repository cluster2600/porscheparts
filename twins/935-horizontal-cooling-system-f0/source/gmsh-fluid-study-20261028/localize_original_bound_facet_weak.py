"""Locate weak cells in the best original-export-bounded facet fluid trial."""

import argparse
import hashlib
import json
from pathlib import Path

import gmsh
import numpy as np


MESH_SHA = "0f6d5cadd5b48c3345e8440c5a881018ca463b005641c46e0b376d9ecbcd8bb7"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def locate(mesh, output):
    if (output.exists() or not output.is_relative_to(Path.cwd().resolve() / "work")
            or sha(mesh) != MESH_SHA):
        raise ValueError("Fresh private output and pinned best-trial mesh required")
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(mesh))
        tags, coords, _ = gmsh.model.mesh.getNodes()
        points = np.full((tags.max() + 1, 3), np.nan)
        points[tags] = coords.reshape(-1, 3)
        _, refs = gmsh.model.mesh.getElementsByType(4)
        cells = refs.reshape(-1, 4)
        rotor_nodes = np.unique(gmsh.model.mesh.getElementsByType(2, 4)[1])
        outer_nodes = np.unique(np.concatenate([
            gmsh.model.mesh.getElementsByType(2, marker)[1] for marker in (1, 2, 3)]))
        weak_ids, weak_ratios, weak_centres = [], [], []
        touch_rotor = touch_outer = 0
        for start in range(0, len(cells), 100000):
            end = min(start + 100000, len(cells))
            vertices = points[cells[start:end]]
            a, b, c, d = np.moveaxis(vertices, 1, 0)
            six = np.einsum("ij,ij->i", b-a, np.cross(c-a, d-a))
            edges = sum(np.einsum("ij,ij->i", vertices[:, i]-vertices[:, j],
                                  vertices[:, i]-vertices[:, j])
                        for i, j in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)))
            ratio = 12 * (np.abs(six) / 2) ** (2/3) / edges
            selected = np.flatnonzero(ratio < .01)
            if len(selected):
                chosen = cells[start:end][selected]
                weak_ids.append(selected + start)
                weak_ratios.append(ratio[selected])
                weak_centres.append(points[chosen].mean(axis=1))
                touch_rotor += int(np.isin(chosen, rotor_nodes).any(axis=1).sum())
                touch_outer += int(np.isin(chosen, outer_nodes).any(axis=1).sum())
        ids = np.concatenate(weak_ids)
        ratios = np.concatenate(weak_ratios)
        centres = np.concatenate(weak_centres)
        radius_mm_conditional = np.linalg.norm(centres[:, :2], axis=1) * 1000
        report = dict(status="rejected_fluid_mesh_weak_cells_localized",
                      mesh_sha256=MESH_SHA, tetrahedra=len(cells),
                      mean_ratio_below_0p01=len(ids), touch_rotor_node=touch_rotor,
                      touch_outer_node=touch_outer,
                      centre_radius_70_to_100_conditional_mm=int(
                          np.count_nonzero((radius_mm_conditional >= 70)
                                           & (radius_mm_conditional <= 100))),
                      min_mean_ratio=float(ratios.min()),
                      scale_verified=False, CFD_accepted=False,
                      manufacturing_authorized=False)
        output.mkdir(mode=0o700)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        np.savez_compressed(output / "weak-cells.npz", cell_ids=ids,
                            mean_ratio=ratios, centres_m=centres)
        return report
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    print(json.dumps(locate(args.mesh.resolve(), args.new_output.resolve())))
