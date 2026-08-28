#!/usr/bin/env python3
"""Master geometry for 993-INT-SWITCH-BLANK-0001, driven by its measurements.

The model refuses to build from assumed numbers. Every dimension is read from
catalog/measurements/meas-993-int-switch-blank-0001.json, so a cote that was
never measured cannot silently enter the geometry: the script stops and names
what is missing.

  python3 parts/993-int-switch-blank-0001/source/switch_blank.py
  python3 .../switch_blank.py --measurements <file> --out <dir> --update-record

Requires the cadsim image, or a local environment with build123d installed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PART_ID = "993-INT-SWITCH-BLANK-0001"
DEFAULT_MEASUREMENTS = ROOT / "catalog" / "measurements" / "meas-993-int-switch-blank-0001.json"
DEFAULT_OUT = ROOT / "parts" / "993-int-switch-blank-0001" / "derived"

# Every dimension the geometry needs, and what it means on the real part.
NEEDED = {
    "D01": "largeur hors tout de la face visible",
    "D02": "hauteur hors tout de la face visible",
    "D03": "epaisseur de la face visible",
    "D04": "rayon des angles de la face visible",
    "D05": "longueur des pattes de clipsage",
    "D06": "epaisseur des pattes de clipsage",
    "D07": "entraxe des pattes de clipsage",
}


def load_dimensions(path: Path) -> tuple[dict[str, float], float]:
    if not path.exists():
        raise SystemExit(
            f"no measurement record at {path}.\n"
            "The geometry is defined by measurement, not by assumption. Measure the "
            "part first, for example:\n"
            "  python3 scripts/capture_caliper.py --record "
            f"{path} --dimension D01 --description '{NEEDED['D01']}' --values ...\n"
            "Dimensions required:\n"
            + "\n".join(f"  {key}  {label}" for key, label in NEEDED.items())
        )

    record = json.loads(path.read_text(encoding="utf-8"))
    readings = {item["dimension_id"]: item for item in record.get("readings", [])}
    missing = [key for key in NEEDED if key not in readings]
    if missing:
        raise SystemExit(
            "missing measurements: " + ", ".join(missing) + "\n"
            + "\n".join(f"  {key}  {NEEDED[key]}" for key in missing)
        )

    wrong_unit = [key for key in NEEDED if readings[key]["unit"] != "mm"]
    if wrong_unit:
        raise SystemExit("these readings are not in mm: " + ", ".join(wrong_unit))

    values = {key: float(readings[key]["value"]) for key in NEEDED}
    worst_uncertainty = max(float(readings[key]["uncertainty"]) for key in NEEDED)
    return values, worst_uncertainty


def build(dimensions: dict[str, float]):
    from build123d import (  # imported late so --help works without build123d
        Align,
        BuildPart,
        Box,
        Location,
        Mode,
        Plane,
        add,
        fillet,
    )

    width, height = dimensions["D01"], dimensions["D02"]
    face_thickness = dimensions["D03"]
    corner_radius = dimensions["D04"]
    tab_length, tab_thickness = dimensions["D05"], dimensions["D06"]
    tab_spacing = dimensions["D07"]

    if tab_spacing + tab_thickness > width:
        raise SystemExit(
            f"D07 ({tab_spacing}) plus D06 ({tab_thickness}) exceeds D01 ({width}): "
            "the clip tabs do not fit inside the face. Re-check the measurements."
        )

    with BuildPart() as part:
        Box(width, height, face_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
        if corner_radius > 0:
            vertical = [
                edge for edge in part.edges()
                if abs(edge.length - face_thickness) < 1e-6
            ]
            if vertical:
                fillet(vertical, radius=min(corner_radius, min(width, height) / 2 - 1e-3))
        for side in (-1, 1):
            with BuildPart(Location((side * tab_spacing / 2, 0, face_thickness))) as tab:
                Box(
                    tab_thickness,
                    height * 0.6,
                    tab_length,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                )
            add(tab.part, mode=Mode.ADD)
    return part.part


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--measurements", type=Path, default=DEFAULT_MEASUREMENTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--update-record", action="store_true", help="write accuracy and derived files back into the part record")
    args = parser.parse_args(argv)

    dimensions, worst_uncertainty = load_dimensions(args.measurements)
    solid = build(dimensions)

    from build123d import export_step, export_stl

    args.out.mkdir(parents=True, exist_ok=True)
    step_path = args.out / "switch_blank.step"
    stl_path = args.out / "switch_blank.stl"
    export_step(solid, str(step_path))
    export_stl(solid, str(stl_path))
    print(f"volume {solid.volume:.1f} mm3, worst measured uncertainty {worst_uncertainty} mm")
    print(f"wrote {step_path}")
    print(f"wrote {stl_path}")

    if args.update_record:
        record_path = ROOT / "catalog" / "parts" / f"{PART_ID.lower()}.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["geometry"]["accuracy_mm"] = worst_uncertainty
        record["geometry"]["derived_files"] = [
            str(step_path.relative_to(ROOT)),
            str(stl_path.relative_to(ROOT)),
        ]
        record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"updated {record_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
