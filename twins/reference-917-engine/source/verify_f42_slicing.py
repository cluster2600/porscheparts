#!/usr/bin/env python3
"""Verify a future F42 supplier slicing export without granting release."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


REQUIRED_COLUMNS = (
    "layer_index",
    "z_mm",
    "part_exposure_area_mm2",
    "support_exposure_area_mm2",
    "scan_length_mm",
    "island_count",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_and_verify(base: Path, artifact: dict, label: str) -> Path:
    if not {"path", "sha256"}.issubset(artifact):
        raise ValueError(f"artefact_incomplet:{label}")
    path = Path(artifact["path"])
    if not path.is_absolute():
        path = base / path
    if not path.is_file():
        raise ValueError(f"artefact_absent:{label}:{path}")
    if sha256(path) != artifact["sha256"]:
        raise ValueError(f"empreinte_invalide:{label}:{path}")
    return path


def verify_layers(path: Path, expected_count: int, layer_height_mm: float, z_offset_mm: float) -> dict:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or any(column not in reader.fieldnames for column in REQUIRED_COLUMNS):
            raise ValueError("colonnes_tranchage_absentes")
        rows = list(reader)
    if len(rows) != expected_count:
        raise ValueError(f"nombre_couches_invalide:{len(rows)}:{expected_count}")

    total_part_area = 0.0
    total_support_area = 0.0
    total_scan_length = 0.0
    for expected_index, row in enumerate(rows):
        index = int(row["layer_index"])
        if index != expected_index:
            raise ValueError(f"index_couche_non_contigu:{expected_index}:{index}")
        z_mm = float(row["z_mm"])
        expected_z = z_offset_mm + expected_index * layer_height_mm
        if not math.isfinite(z_mm) or not math.isclose(z_mm, expected_z, abs_tol=1e-6):
            raise ValueError(f"z_couche_incoherent:{expected_index}:{z_mm}:{expected_z}")
        values = [
            float(row["part_exposure_area_mm2"]),
            float(row["support_exposure_area_mm2"]),
            float(row["scan_length_mm"]),
            float(row["island_count"]),
        ]
        if not all(math.isfinite(value) and value >= 0.0 for value in values):
            raise ValueError(f"metrique_couche_invalide:{expected_index}")
        if not values[3].is_integer():
            raise ValueError(f"nombre_ilots_non_entier:{expected_index}")
        total_part_area += values[0]
        total_support_area += values[1]
        total_scan_length += values[2]
    if total_part_area <= 0.0 or total_support_area <= 0.0 or total_scan_length <= 0.0:
        raise ValueError("tranchage_sans_exposition_piece_support_ou_balayage")
    return {
        "row_count": len(rows),
        "first_z_mm": float(rows[0]["z_mm"]),
        "last_z_mm": float(rows[-1]["z_mm"]),
        "total_part_exposure_area_mm2": total_part_area,
        "total_support_exposure_area_mm2": total_support_area,
        "total_scan_length_mm": total_scan_length,
    }


def verify(spec: dict, supplier_report: dict, base: Path) -> dict:
    slicing = spec["slicing_contract"]
    orientation = spec["orientation_and_support"]
    if supplier_report.get("orientation_id") != orientation["orientation_id"]:
        raise ValueError("orientation_tranchee_incorrecte")
    if not math.isclose(float(supplier_report.get("layer_height_um", -1)), 50.0, abs_tol=1e-12):
        raise ValueError("hauteur_couche_tranchee_incorrecte")
    if int(supplier_report.get("layer_count", -1)) != slicing["expected_layer_count_from_oriented_height"]:
        raise ValueError("decompte_couches_declare_incorrect")

    layers_path = resolve_and_verify(base, supplier_report["layers_csv"], "layers_csv")
    support_path = resolve_and_verify(base, supplier_report["support_geometry"], "support_geometry")
    recoater_path = resolve_and_verify(
        base, supplier_report["recoater_collision_report"], "recoater_collision_report"
    )
    machine_path = resolve_and_verify(base, supplier_report["machine_build_file"], "machine_build_file")
    recoater = json.loads(recoater_path.read_text(encoding="utf-8"))
    if recoater.get("collision_free") is not True:
        raise ValueError("collision_recoater_non_exclue")
    layer_metrics = verify_layers(
        layers_path,
        slicing["expected_layer_count_from_oriented_height"],
        slicing["layer_height_um"] / 1000.0,
        float(supplier_report.get("build_z_offset_mm", 0.0)),
    )
    return {
        "schema_version": "1.0.0",
        "phase": "F42",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "supplier_slicer_artifact_integrity_check_not_manufacturing_release",
        "artifacts": {
            "layers_csv": {"path": str(layers_path), "sha256": sha256(layers_path)},
            "support_geometry": {"path": str(support_path), "sha256": sha256(support_path)},
            "recoater_collision_report": {"path": str(recoater_path), "sha256": sha256(recoater_path)},
            "machine_build_file": {"path": str(machine_path), "sha256": sha256(machine_path)},
        },
        "layer_metrics": layer_metrics,
        "gates": {
            "layer_schedule_complete_and_contiguous": True,
            "support_geometry_present_and_hash_locked": True,
            "machine_build_file_present_and_hash_locked": True,
            "recoater_collision_report_declares_clear": True,
            "supplier_parameter_card_qualified": False,
            "physical_coupon_qualified": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "f42-lpbf-doe.json",
    )
    parser.add_argument("--supplier-slice-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    supplier = json.loads(args.supplier_slice_report.read_text(encoding="utf-8"))
    report = verify(spec, supplier, args.supplier_slice_report.parent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "gates": report["gates"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
