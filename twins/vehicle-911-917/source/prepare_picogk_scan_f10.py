#!/usr/bin/env python3
"""Convertit le scan OBJ F21 en STL binaire orienté pour le contrôle PicoGK F10."""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
from pathlib import Path
import struct
from typing import Callable


ROOT = Path(__file__).resolve().parents[3]
OBJ = ROOT / "raw-scans" / "917-engine" / "original" / "917-engine-case-with-cylinders.obj"
INTERFACES = ROOT / "work" / "917-engine" / "scan-metrology-f13-report.json"
PACKAGING = ROOT / "work" / "911-917-packaging-f1" / "packaging-report-f1.json"
OUTPUT = ROOT / "work" / "911-917-picogk-f10"
STL = OUTPUT / "917-engine-oriented-f10.stl"
REPORT = OUTPUT / "scan-preparation-report-f10.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def convert_obj_to_binary_stl(
    source: Path,
    destination: Path,
    transform: Callable[[float, float, float], tuple[float, float, float]],
) -> tuple[int, int]:
    vertices = array("f")
    triangle_count = 0
    buffer = bytearray()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")

    with source.open("r", encoding="utf-8", errors="ignore") as obj, temporary.open("w+b") as stl:
        stl.write(b"911-917 F10 PicoGK input; units=mm".ljust(80, b"\0"))
        stl.write(struct.pack("<I", 0))
        for line in obj:
            if line.startswith("v "):
                fields = line.split()
                vertices.extend(transform(float(fields[1]), float(fields[2]), float(fields[3])))
                continue
            if not line.startswith("f "):
                continue
            indexes = [int(field.split("/", 1)[0]) for field in line.split()[1:]]
            indexes = [index - 1 if index > 0 else len(vertices) // 3 + index for index in indexes]
            for offset in range(1, len(indexes) - 1):
                points = []
                for index in (indexes[0], indexes[offset], indexes[offset + 1]):
                    base = 3 * index
                    points.extend((vertices[base], vertices[base + 1], vertices[base + 2]))
                buffer.extend(struct.pack("<12fH", 0.0, 0.0, 0.0, *points, 0))
                triangle_count += 1
                if len(buffer) >= 8 * 1024 * 1024:
                    stl.write(buffer)
                    buffer.clear()
        stl.write(buffer)
        stl.seek(80)
        stl.write(struct.pack("<I", triangle_count))
    temporary.replace(destination)
    return len(vertices) // 3, triangle_count


def context() -> tuple[Callable[[float, float, float], tuple[float, float, float]], dict]:
    packaging = json.loads(PACKAGING.read_text(encoding="utf-8"))
    interfaces = json.loads(INTERFACES.read_text(encoding="utf-8"))["interface_registry"]
    frame = packaging["scan_screening"]["screening_frame"]
    centres = [item["center_scan_coordinates_obj_units"] for item in interfaces]
    origin = [sum(point[axis] for point in centres) / len(centres) for axis in range(3)]
    basis_rows = frame["basis_columns_in_scan_coordinates"]
    oriented_min = frame["oriented_bounds_obj_units"]["minimum"]
    size = frame["screening_size_mm"]
    scale = float(frame["scale_mm_per_obj_unit"])
    layouts = packaging["layout_screening"]
    selected = next(item for item in layouts["trials"] if item["layout_id"] == layouts["selected_layout_id"])
    scan_start = float(selected["engine_scan_bounds_x_mm"][0])

    def transform(x: float, y: float, z: float) -> tuple[float, float, float]:
        delta = (x - origin[0], y - origin[1], z - origin[2])
        local = [sum(delta[index] * row[index] for index in range(3)) for row in basis_rows]
        return (
            scan_start + (local[0] - oriented_min[0]) * scale,
            (local[1] - oriented_min[1]) * scale - size[1] / 2.0,
            300.0 + (local[2] - oriented_min[2]) * scale,
        )

    return transform, {
        "scan_start_x_mm": scan_start,
        "scan_vertical_offset_mm": 300.0,
        "scale_mm_per_obj_unit": scale,
        "scale_verified": False,
        "orientation_verified": False,
        "transform_basis_source": "packaging-report-f1.json screening_frame",
    }


def build() -> None:
    transform_inputs = {name: sha256(path) for name, path in (("PACKAGING", PACKAGING), ("INTERFACES", INTERFACES))}
    transform, transform_report = context()
    vertex_count, triangle_count = convert_obj_to_binary_stl(OBJ, STL, transform)
    report = {
        "schema_version": "1.0.0",
        "phase": "F10",
        "status": "picogk_input_prepared_from_unverified_scan_frame",
        "source_obj_sha256": sha256(OBJ),
        "output_stl_sha256": sha256(STL),
        "transform_inputs_sha256": transform_inputs,
        "vertex_count": vertex_count,
        "triangle_count": triangle_count,
        "transform": transform_report,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    check()
    print(STL.relative_to(ROOT))


def check() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("transform_inputs_sha256") != {
        name: sha256(path) for name, path in (("PACKAGING", PACKAGING), ("INTERFACES", INTERFACES))
    }:
        raise SystemExit("F10 transform inputs changed or are unrecorded; rebuild the prepared scan")
    if report["source_obj_sha256"] != sha256(OBJ):
        raise SystemExit("le scan source F10 a changé")
    if report["output_stl_sha256"] != sha256(STL):
        raise SystemExit("le STL préparé F10 a changé")
    if report["transform"]["scale_verified"] or report["transform"]["orientation_verified"]:
        raise SystemExit("F10 ne doit pas promouvoir l'échelle ou l'orientation")
    print("911-917 PicoGK scan preparation F10: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("build", "check"), default="build")
    args = parser.parse_args()
    build() if args.mode == "build" else check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
