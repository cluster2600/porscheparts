#!/usr/bin/env python3
"""Criblage géométrique LPBF générique, fail-closed et sans fichier machine.

Le noyau de coupe, d'épaisseur et de dépoudrage réutilise les fonctions déjà
testées du programme F50. Le présent adaptateur retire les hypothèses propres à
la culasse 917 et lie chaque résultat au master et au maillage par SHA-256.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
KERNEL_PATH = (
    ROOT
    / "twins/reference-917-engine/source/run_f50_lpbf_geometry_audit.py"
)
PART_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,63}$")


class ScreenError(RuntimeError):
    """Erreur contrôlée du criblage AM."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ScreenError(f"expected_object:{path.name}")
    return value


def load_kernel():
    spec = importlib.util.spec_from_file_location("lpbf_f50_kernel", KERNEL_PATH)
    if spec is None or spec.loader is None:
        raise ScreenError("cannot_load_f50_geometry_kernel")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_machine(card: dict[str, Any]) -> None:
    required = {
        "manufacturer",
        "model",
        "build_height_mm",
        "source",
    }
    if not required <= card.keys():
        raise ScreenError("incomplete_machine_card")
    circular = "build_cylinder_diameter_mm" in card
    rectangular = {"build_width_mm", "build_depth_mm"} <= card.keys()
    if circular == rectangular:
        raise ScreenError("machine_card_requires_exactly_one_build_envelope_type")
    dimension_keys = ["build_height_mm"]
    dimension_keys += (
        ["build_cylinder_diameter_mm"]
        if circular
        else ["build_width_mm", "build_depth_mm"]
    )
    for key in dimension_keys:
        value = card[key]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ScreenError(f"invalid_machine_card:{key}")


def machine_fit(card: dict[str, Any], extents: np.ndarray) -> dict[str, Any]:
    values = np.asarray(extents, dtype=float)
    if values.shape != (3,) or not np.isfinite(values).all() or np.any(values <= 0):
        raise ScreenError("invalid_oriented_part_extents")
    height_margin = float(card["build_height_mm"] - values[2])
    common = {
        "part_extents_mm": [float(value) for value in values],
        "height_margin_mm": height_margin,
    }
    if "build_cylinder_diameter_mm" in card:
        required_diameter = float(math.hypot(float(values[0]), float(values[1])))
        diameter_margin = float(card["build_cylinder_diameter_mm"] - required_diameter)
        return {
            **common,
            "build_envelope_type": "circular_cylinder",
            "conservative_required_diameter_mm": required_diameter,
            "diametral_margin_mm": diameter_margin,
            "bare_part_nominal_fit": diameter_margin >= 0.0 and height_margin >= 0.0,
        }
    width_margin = float(card["build_width_mm"] - values[0])
    depth_margin = float(card["build_depth_mm"] - values[1])
    return {
        **common,
        "build_envelope_type": "rectangular_prism",
        "width_margin_mm": width_margin,
        "depth_margin_mm": depth_margin,
        "bare_part_nominal_fit": (
            width_margin >= 0.0 and depth_margin >= 0.0 and height_margin >= 0.0
        ),
    }


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render(path: Path, report: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    z = np.asarray([row["z_mm"] for row in rows])
    part = np.asarray([row["part_area_mm2"] for row in rows])
    unsupported = np.asarray([row["unsupported_area_mm2"] for row in rows])
    support = np.asarray([row["support_area_mm2"] for row in rows])
    figure, axes = plt.subplots(2, 2, figsize=(14, 9), facecolor="#08131d")
    figure.suptitle(
        f"{report['part_id']} — SIMULATION GEOMETRIQUE LPBF",
        color="white",
        fontsize=16,
        weight="bold",
    )
    for axis, values, title, color in (
        (axes[0, 0], part, "Section de pièce par couche", "#4cc9f0"),
        (axes[0, 1], unsupported, "Région nouvellement non soutenue", "#f77f00"),
        (axes[1, 0], support, "Enveloppe conservative de supports", "#90be6d"),
    ):
        axis.set_facecolor("#10212d")
        axis.plot(z, values, color=color, linewidth=1.0)
        axis.set_title(title, color="white", weight="bold")
        axis.set_xlabel("Hauteur de construction (mm)", color="#d7e4ec")
        axis.set_ylabel("mm²", color="#d7e4ec")
        axis.tick_params(colors="#d7e4ec")
        axis.grid(alpha=0.18)
    axis = axes[1, 1]
    axis.set_facecolor("#10212d")
    axis.axis("off")
    slicing = report["full_build_slicing"]
    thickness = report["thickness_screen"]
    powder = report["powder_escape_screen"]
    axis.text(
        0.04,
        0.95,
        "\n".join(
            (
                f"Orientation candidate : {report['selected_candidate_orientation']}",
                f"Couches calculées : {slicing['layer_count']:,}",
                f"Hauteur : {slicing['build_height_mm']:.3f} mm",
                f"Support proxy : {slicing['support_proxy_volume_cm3']:.2f} cm³",
                f"Épaisseur p01 : {thickness['p01_mm']:.3f} mm",
                f"Échantillons < 1,5 mm : {100*thickness['sample_fraction_below_1p5_mm']:.2f} %",
                f"Vide piégé détecté : {powder['trapped_void_volume_mm3']:.1f} mm³",
                "",
                "TRANCHAGE GEOMETRIQUE : TERMINE",
                "PROCEDE THERMIQUE CIBLE : BLOQUE",
                "IMPRESSION METAL : NON AUTORISEE",
            )
        ),
        transform=axis.transAxes,
        va="top",
        color="white",
        fontsize=11,
        linespacing=1.5,
    )
    figure.text(
        0.5,
        0.02,
        "Coupe réelle à chaque couche et support proxy; aucun parcours laser, fichier machine, CT ou corrélation fournisseur.",
        ha="center",
        color="#ffb4a2",
        fontsize=10,
    )
    figure.tight_layout(rect=(0.02, 0.05, 0.98, 0.94))
    figure.savefig(path, dpi=170, facecolor=figure.get_facecolor())
    plt.close(figure)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not PART_ID_PATTERN.fullmatch(args.part_id):
        raise ScreenError("invalid_part_id")
    for path in (args.master, args.surface, args.machine_card):
        if not path.is_file():
            raise ScreenError(f"missing_input:{path.name}")
    if sha256(args.master) != args.master_sha256:
        raise ScreenError("master_hash_mismatch")
    if sha256(args.surface) != args.surface_sha256:
        raise ScreenError("surface_hash_mismatch")

    machine = load_json(args.machine_card)
    validate_machine(machine)
    kernel = load_kernel()
    kernel.MACHINE = machine
    kernel.LAYER_MM = args.layer_thickness_mm
    kernel.OVERHANG_DEG = args.overhang_deg
    kernel.SUPPORT_RASTER_MM = args.support_raster_mm
    kernel.machine_fit = lambda extents: machine_fit(machine, extents)

    import trimesh

    mesh = trimesh.load_mesh(args.surface, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise ScreenError("surface_mesh_not_watertight")
    if len(mesh.split(only_watertight=False)) != 1:
        raise ScreenError("surface_mesh_not_single_component")
    expected = np.asarray(args.expected_envelope_mm, dtype=float)
    actual = np.asarray(mesh.extents, dtype=float)
    if not np.allclose(actual, expected, rtol=0.0, atol=args.envelope_tolerance_mm):
        raise ScreenError(f"surface_envelope_mismatch:{actual.tolist()}")

    orientations = kernel.orientation_screen(mesh)
    fitting = [item for item in orientations if item["bare_part_nominal_fit"]]
    if not fitting:
        raise ScreenError("no_orientation_fits_bare_machine_envelope")
    selected = min(fitting, key=lambda item: item["downward_projected_area_mm2"])[
        "orientation"
    ]
    rows, slicing = kernel.slice_build(mesh, selected)
    thickness = kernel.thickness_screen(mesh, args.thickness_samples)
    powder = kernel.trapped_void_screen(mesh, args.voxel_pitch_mm)

    args.output.mkdir(parents=True, exist_ok=False)
    slug = args.part_id.lower()
    csv_path = args.output / f"{slug}-layer-metrics.csv"
    report_path = args.output / f"{slug}-lpbf-geometry-report.json"
    image_path = args.output / f"{slug}-lpbf-geometry-screen.png"
    manifest_path = args.output / f"{slug}-lpbf-geometry-manifest.json"
    write_rows(csv_path, rows)
    report = {
        "schema_version": "1.0.0",
        "part_id": args.part_id,
        "classification": "actual_full_layer_geometric_slicing_and_support_proxy_not_process_qualification",
        "software": {
            "kernel": str(KERNEL_PATH.relative_to(ROOT)),
            "trimesh": trimesh.__version__,
        },
        "master": {"sha256": args.master_sha256, "format": args.master.suffix.lower()},
        "analysis_surface": {
            "sha256": args.surface_sha256,
            "format": args.surface.suffix.lower(),
            "vertices": int(len(mesh.vertices)),
            "triangles": int(len(mesh.faces)),
            "watertight": True,
            "single_component": True,
            "envelope_mm": [float(value) for value in actual],
            "envelope_tolerance_mm": args.envelope_tolerance_mm,
        },
        "machine_candidate": machine,
        "orientation_screen": orientations,
        "selected_candidate_orientation": selected,
        "orientation_selection_rule": "minimum downward projected area among bare-part envelope-fitting kernel candidates",
        "full_build_slicing": slicing,
        "thickness_screen": thickness,
        "powder_escape_screen": powder,
        "process_physics": {
            "additivefoam_executed": False,
            "target_material_card": args.material,
            "target_material_card_complete_and_calibrated": False,
            "reason": "No complete temperature-dependent and machine-calibrated material/process card is available for this exact route.",
        },
        "recoater_screen": {
            "collision_simulation_executed": False,
            "distortion_field_available": False,
            "blade_clearance_and_compliance_known": False,
            "pass": False,
        },
        "gates": {
            "master_hash_verified": True,
            "single_watertight_surface_mesh": True,
            "full_piece_layer_slicing_completed": True,
            "bare_part_machine_envelope_fit": slicing["bare_part_nominal_fit"],
            "candidate_orientation_engineering_reviewed": False,
            "supplier_supports_validated": False,
            "target_material_process_physics_correlated": False,
            "recoater_clearance_validated": False,
            "supplier_machine_file_signed": False,
            "physical_coupon_qualified": False,
            "metal_print_authorized": False,
        },
        "verdict": "geometric_print_simulation_completed_process_and_print_release_blocked",
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render(image_path, report, rows)
    manifest = {
        "schema_version": "1.0.0",
        "part_id": args.part_id,
        "artifacts": {
            "report": {"path": report_path.name, "sha256": sha256(report_path)},
            "layer_metrics": {"path": csv_path.name, "sha256": sha256(csv_path)},
            "image": {"path": image_path.name, "sha256": sha256(image_path)},
        },
        "gates": {
            "contains_machine_file": False,
            "contains_supplier_support_geometry": False,
            "metal_print_authorized": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part-id", required=True)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--master-sha256", required=True)
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--surface-sha256", required=True)
    parser.add_argument("--machine-card", type=Path, required=True)
    parser.add_argument("--material", required=True)
    parser.add_argument("--expected-envelope-mm", type=float, nargs=3, required=True)
    parser.add_argument("--envelope-tolerance-mm", type=float, default=0.05)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer-thickness-mm", type=float, default=0.05)
    parser.add_argument("--overhang-deg", type=float, default=45.0)
    parser.add_argument("--support-raster-mm", type=float, default=0.50)
    parser.add_argument("--thickness-samples", type=int, default=2000)
    parser.add_argument("--voxel-pitch-mm", type=float, default=1.0)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        result = run(parse_args())
    except (ScreenError, ValueError) as exc:
        raise SystemExit(f"METAL AM FAIL-CLOSED: {exc}") from exc
    print(json.dumps({"part_id": result["part_id"], "gates": result["gates"]}, sort_keys=True))
