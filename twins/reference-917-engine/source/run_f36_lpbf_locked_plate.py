#!/usr/bin/env python3
"""Ecran CalculiX de retrait LPBF F36 avec plateau verrouille.

Le solide oriente est suppose libre de contraintes a 280 C puis refroidi a
20 C, sa couche inferieure restant bloquee. Ce calcul lineaire constitue une
borne de sensibilite; il ne modelise ni depot couche par couche, ni plasticite,
ni relaxation, ni parametres laser calibres.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from run_scan_conforming_calculix_f36 import (
    largest_face_connected_component,
    parse_dat,
    percentile,
    sha256,
    write_set,
)


def prepare(stl: Path, output: Path, pitch: float, stress_free_c: float, final_c: float) -> dict:
    if output.exists():
        raise ValueError(f"output exists: {output}")
    output.mkdir(parents=True)
    mesh = trimesh.load_mesh(stl, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise ValueError("le solide LPBF oriente doit etre etanche")
    grid = mesh.voxelized(pitch=pitch, method="subdivide").fill(method="holes")
    raw = {tuple(int(value) for value in row) for row in grid.sparse_indices}
    occupied, component_count = largest_face_connected_component(raw)
    transform = np.asarray(grid.transform, dtype=float)
    node_ids: dict[tuple[int, int, int], int] = {}
    coordinates: dict[int, tuple[float, float, float]] = {}

    def node(corner: tuple[int, int, int]) -> int:
        if corner not in node_ids:
            tag = len(node_ids) + 1
            centre_index = np.asarray(corner, dtype=float) - 0.5
            point = trimesh.transform_points(centre_index[None, :], transform)[0]
            node_ids[corner] = tag
            coordinates[tag] = tuple(float(value) for value in point)
        return node_ids[corner]

    elements: list[tuple[int, tuple[int, ...]]] = []
    for element_id, (i, j, k) in enumerate(sorted(occupied), start=1):
        corners = (
            (i, j, k), (i + 1, j, k), (i + 1, j + 1, k), (i, j + 1, k),
            (i, j, k + 1), (i + 1, j, k + 1), (i + 1, j + 1, k + 1), (i, j + 1, k + 1),
        )
        elements.append((element_id, tuple(node(corner) for corner in corners)))

    minimum_z = min(point[2] for point in coordinates.values())
    plate = sorted(tag for tag, point in coordinates.items() if point[2] <= minimum_z + 1.05 * pitch)
    if len(elements) < 1000 or len(plate) < 20:
        raise RuntimeError("maillage ou contact plateau insuffisant")

    job = output / "head-f36-lpbf.inp"
    with job.open("w", encoding="utf-8") as stream:
        stream.write("*HEADING\nF36 locked build plate cooling sensitivity\n*NODE\n")
        for tag in sorted(coordinates):
            x, y, z = coordinates[tag]
            stream.write(f"{tag},{x:.9g},{y:.9g},{z:.9g}\n")
        stream.write("*ELEMENT,TYPE=C3D8,ELSET=EALL\n")
        for element_id, tags in elements:
            stream.write(f"{element_id}," + ",".join(str(tag) for tag in tags) + "\n")
        write_set(stream, "NSET", "NALL", sorted(coordinates))
        write_set(stream, "NSET", "BUILD_PLATE", plate)
        stream.write(
            "*MATERIAL,NAME=AHEADD_HT1_LPBF_SCREEN\n"
            "*ELASTIC\n66000.,0.33\n"
            "*EXPANSION\n2.3e-5\n"
            "*SOLID SECTION,ELSET=EALL,MATERIAL=AHEADD_HT1_LPBF_SCREEN\n"
            "*INITIAL CONDITIONS,TYPE=TEMPERATURE\n"
            f"NALL,{stress_free_c:.9g}\n"
            "*STEP\n*STATIC\n"
            "*BOUNDARY\nBUILD_PLATE,1,3\n"
            "*TEMPERATURE\n"
            f"NALL,{final_c:.9g}\n"
            "*EL PRINT,ELSET=EALL\nS\n"
            "*NODE PRINT,NSET=NALL\nU\n"
            "*EL FILE\nS,E\n"
            "*NODE FILE,NSET=NALL\nU,RF\n"
            "*END STEP\n"
        )
    report = {
        "schema_version": "1.0.0",
        "phase": "F36",
        "status": "lpbf_locked_plate_input_prepared",
        "classification": "linear_elastic_uniform_cooling_locked_plate_upper_bound_not_calibrated_lpbf",
        "mesh": {
            "pitch_mm_if_scale_is_mm": pitch,
            "hexahedra": len(elements),
            "nodes": len(coordinates),
            "plate_nodes": len(plate),
            "face_connected_components": component_count,
            "discarded_non_primary_voxels": len(raw) - len(occupied),
        },
        "thermal_load": {
            "stress_free_temperature_c": stress_free_c,
            "final_temperature_c": final_c,
            "delta_temperature_k": final_c - stress_free_c,
        },
        "material": {
            "id": "Aheadd_HT1_screen",
            "elastic_modulus_mpa_hypothesis": 66000.0,
            "poisson_hypothesis": 0.33,
            "thermal_expansion_per_k_hypothesis": 2.3e-5,
            "plasticity_and_stress_relaxation_included": False,
            "printed_coupon_card_qualified": False,
        },
        "input": {"stl_sha256": sha256(stl), "inp_sha256": sha256(job)},
        "release_claim": False,
    }
    (output / "preparation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def summarize(output: Path) -> dict:
    preparation = json.loads((output / "preparation.json").read_text(encoding="utf-8"))
    dat = output / "head-f36-lpbf.dat"
    stresses, displacements, _ = parse_dat(dat) if dat.is_file() else ([], [], None)
    p95 = percentile(stresses, 0.95)
    p99 = percentile(stresses, 0.99)
    maximum = max(stresses) if stresses else None
    report = {
        **preparation,
        "status": "lpbf_locked_plate_screen_complete" if stresses and displacements else "failed",
        "solver": "CalculiX",
        "results": {
            "stress_samples": len(stresses),
            "von_mises_p95_mpa": p95,
            "von_mises_p99_mpa": p99,
            "von_mises_max_mpa": maximum,
            "maximum_displacement_mm": max(displacements) if displacements else None,
        },
        "engineering_gates": {
            "calibrated_layer_activation_and_inherent_strain": False,
            "printed_coupon_material_card": False,
            "build_plate_and_support_contact_correlated": False,
            "machining_allowance_validated": False,
            "metal_print_authorized": False,
        },
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pitch", type=float)
    parser.add_argument("--stress-free-c", type=float, default=280.0)
    parser.add_argument("--final-c", type=float, default=20.0)
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        report = summarize(args.output)
    else:
        if args.stl is None or args.pitch is None:
            parser.error("--stl et --pitch sont requis en preparation")
        report = prepare(args.stl, args.output, args.pitch, args.stress_free_c, args.final_c)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
