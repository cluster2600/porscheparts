#!/usr/bin/env python3
"""Audit the raw PicoGK piston screening meshes without repairing them."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    screen = json.loads(args.screen.read_text(encoding="utf-8"))
    audits = []
    for variant in screen["variants"]:
        geometry = variant["geometry"]
        path = args.raw_directory / geometry["output_stl"]
        mesh = trimesh.load_mesh(path, process=True)
        edges = np.sort(mesh.edges, axis=1)
        _, counts = np.unique(edges, axis=0, return_counts=True)
        audits.append(
            {
                "variant_id": variant["variant_id"],
                "file": path.name,
                "sha256_matches_screen": sha256(path) == geometry["output_sha256"],
                "watertight": bool(mesh.is_watertight),
                "winding_consistent": bool(mesh.is_winding_consistent),
                "body_count": int(mesh.body_count),
                "boundary_edge_count": int(np.count_nonzero(counts == 1)),
                "nonmanifold_edge_count": int(np.count_nonzero(counts > 2)),
                "maximum_edge_multiplicity": int(counts.max()),
                "envelope_mm": [round(float(value), 6) for value in mesh.extents],
                "volume_mm3": round(float(mesh.volume), 6),
            }
        )

    all_hashes_match = all(item["sha256_matches_screen"] for item in audits)
    all_meshes_watertight = all(item["watertight"] for item in audits)
    report = {
        "schema_version": "1.0.0",
        "status": "failed_output_mesh_integrity",
        "source_screen_sha256": sha256(args.screen),
        "method": "trimesh process=True followed by undirected edge multiplicity audit",
        "all_hashes_match": all_hashes_match,
        "all_meshes_watertight": all_meshes_watertight,
        "variants": audits,
        "decision": {
            "picogk_geometry_gate_passed": False,
            "reason": "All raw meshes retain non-manifold edges after vertex processing; none may be promoted to CAD, LPBF slicing or SimReady.",
            "repair_attempted": False,
            "manufacturing_authorized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        "PICOGK_OUTPUT_AUDIT_FAIL"
        f" hashes_match={all_hashes_match} watertight={all_meshes_watertight}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
