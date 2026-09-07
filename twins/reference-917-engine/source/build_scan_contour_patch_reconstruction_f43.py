#!/usr/bin/env python3
"""Reconstruit la seule peau externe F43 depuis des coupes locales du stock F36.

Ce générateur ne contient aucune primitive d'enveloppe globale. Les quarante-
quatre contours issus du stock sont d'abord alignés; trois coupes dont les
transitions ont produit des auto-intersections reproductibles sont ensuite
retirées localement. Le dernier contour pathologique est remplacé par la forme
du contour voisin, à sa cote Z d'origine. Le résultat est une base B-Rep
externe, pas une culasse fonctionnelle et encore moins une pièce libérée.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import gmsh
import numpy as np
import trimesh

from build_scan_locked_outer_brep_f40 import (
    canonicalize_step,
    profile_sequence,
    require,
    sha256,
)


PHASE = "F43"
CONTOUR_POINTS = 128
FIN_THICKNESS_SCAN_UNITS = 1.5
REMOVED_LEVELS = {
    41.25: "surface_meshing_invalid_between_z39_75_and_z41_25",
    70.25: "surface_meshing_self_intersection_near_z70",
    75.75: "segment_facet_intersection_in_transition_z74_875_to_z76_875",
}
TOP_LEVEL = 82.0
TOP_DONOR_LEVEL = 79.5


def align_adjacent_profiles(
    profiles: list[tuple[float, np.ndarray, str]],
) -> list[dict[str, object]]:
    """Aligne seulement l'origine cyclique, sans déplacer un point de contour."""

    aligned: list[dict[str, object]] = []
    previous: np.ndarray | None = None
    for z, raw_points, kind in profiles:
        points = np.asarray(raw_points, dtype=float)
        shift = 0
        if previous is not None:
            rms = [
                float(
                    np.sqrt(
                        np.mean(
                            np.sum((np.roll(points, -candidate, axis=0) - previous) ** 2, axis=1)
                        )
                    )
                )
                for candidate in range(len(points))
            ]
            shift = int(np.argmin(rms))
            points = np.roll(points, -shift, axis=0)
        aligned.append(
            {
                "z": float(z),
                "kind": kind,
                "cyclic_shift": shift,
                "points": points,
            }
        )
        previous = points
    return aligned


def local_repairs(profiles: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict]]:
    by_level = {float(item["z"]): item for item in profiles}
    donor = np.asarray(by_level[TOP_DONOR_LEVEL]["points"], dtype=float).copy()
    repaired: list[dict[str, object]] = []
    removed: list[dict] = []
    for item in profiles:
        z = float(item["z"])
        if z in REMOVED_LEVELS:
            removed.append({"z_scan_units": z, "reason": REMOVED_LEVELS[z]})
            continue
        result = dict(item)
        if z == TOP_LEVEL:
            result["points"] = donor
            result["kind"] = "top_rebuilt_from_adjacent_profile"
        repaired.append(result)
    return repaired, removed


def linear_wire(points_xy: np.ndarray, z: float) -> int:
    occ = gmsh.model.occ
    points = [occ.addPoint(float(x), float(y), z) for x, y in points_xy]
    edges = [occ.addLine(points[index], points[(index + 1) % len(points)]) for index in range(len(points))]
    return occ.addWire(edges, checkClosed=True)


def build(stock_path: Path, output_dir: Path) -> dict:
    stock = trimesh.load_mesh(stock_path, process=True)
    require(isinstance(stock, trimesh.Trimesh), "stock_F36_non_maillage")
    require(stock.is_watertight, "stock_F36_non_etanche")
    anchored = profile_sequence(stock, CONTOUR_POINTS, FIN_THICKNESS_SCAN_UNITS)
    aligned = align_adjacent_profiles(anchored)
    profiles, removed = local_repairs(aligned)
    require(len(aligned) == 44, f"nombre_contours_source_inattendu:{len(aligned)}")
    require(len(profiles) == 41, f"nombre_contours_repares_inattendu:{len(profiles)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    step_path = output_dir / "917-head-scan-contour-repaired-v2-f43.step"
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Geometry.Tolerance", 1.0e-7)
        gmsh.model.add("f43_scan_contour_local_patch")
        wires = [
            linear_wire(np.asarray(item["points"], dtype=float), float(item["z"]))
            for item in profiles
        ]
        entities = gmsh.model.occ.addThruSections(
            wires,
            makeSolid=True,
            makeRuled=True,
            maxDegree=3,
        )
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        require(len(volumes) == 1 and any(dim == 3 for dim, _ in entities), "BRep_non_monobloc")
        gmsh.write(str(step_path))
    finally:
        gmsh.finalize()
    canonicalize_step(step_path)

    report = {
        "schema": "porsche-917-f43-private-builder/v1",
        "phase": PHASE,
        "source": {
            "sha256": sha256(stock_path),
            "classification": "private_scan_derived_stock_not_committed",
        },
        "construction": {
            "source_contour_count": len(aligned),
            "retained_contour_count": len(profiles),
            "points_per_contour": CONTOUR_POINTS,
            "profile_curve_type": "piecewise_linear_closed_wire",
            "loft_type": "ruled_OCCT_sections",
            "cyclic_alignment_only": True,
            "removed_local_levels": removed,
            "top_rebuild": {
                "target_z_scan_units": TOP_LEVEL,
                "donor_profile_z_scan_units": TOP_DONOR_LEVEL,
                "target_z_preserved": True,
            },
            "global_ellipse_used": False,
            "global_box_used": False,
        },
        "output": {
            "step_sha256": sha256(step_path),
            "step_bytes": step_path.stat().st_size,
            "repository_policy": "private_local_only_scan_derived_geometry",
        },
        "scope": {
            "external_skin_only": True,
            "functional_internal_geometry_present": False,
            "manufacturing_authorized": False,
        },
    }
    report_path = output_dir / "917-head-scan-contour-repaired-v2-f43-private-build.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.stock, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
