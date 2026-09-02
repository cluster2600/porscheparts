#!/usr/bin/env python3
"""Conservatively separate the two cylinder rows from the central assembly."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import trimesh


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class InputError(ValueError):
    """Raised when an input cannot satisfy the segmentation contract."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(path: Path, expected: str | None, label: str) -> str:
    if expected is None or SHA256_PATTERN.fullmatch(expected) is None:
        raise InputError(f"{label} requires a lowercase 64-character SHA-256")
    actual = sha256(path)
    if actual != expected:
        raise InputError(f"{label} SHA-256 mismatch")
    return actual


def finite_array(value: object, shape: tuple[int, ...], pointer: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise InputError(f"{pointer} must contain finite numbers") from error
    if array.shape != shape:
        raise InputError(f"{pointer} must have shape {shape}")
    if not np.all(np.isfinite(array)):
        raise InputError(f"{pointer} must contain finite numbers")
    return array


def validate_interfaces(
    data: object, synthetic_fixture_mode: bool
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    if not isinstance(data, dict):
        raise InputError("interface document must be a JSON object")
    centroid = finite_array(
        data.get("centroid_scan_coordinates"), (3,), "/centroid_scan_coordinates"
    )
    frame = finite_array(
        data.get("frame_rows_longitudinal_bank_axis_vertical"),
        (3, 3),
        "/frame_rows_longitudinal_bank_axis_vertical",
    )
    if not np.allclose(frame @ frame.T, np.eye(3), rtol=0.0, atol=1e-6):
        raise InputError("/frame_rows_longitudinal_bank_axis_vertical must be orthonormal")
    determinant = float(np.linalg.det(frame))
    if not np.isclose(determinant, 1.0, rtol=0.0, atol=1e-6):
        raise InputError(
            "/frame_rows_longitudinal_bank_axis_vertical must be direct (determinant +1)"
        )

    banks = data.get("banks")
    if not isinstance(banks, dict) or set(banks) != {"positive", "negative"}:
        raise InputError("/banks must contain exactly positive and negative")
    expected_count = None if synthetic_fixture_mode else 6
    counts = {}
    for label in ("positive", "negative"):
        openings = banks[label]
        if not isinstance(openings, list):
            raise InputError(f"/banks/{label} must be an array")
        if expected_count is not None and len(openings) != expected_count:
            raise InputError(f"/banks/{label} must contain exactly six centres in canonical mode")
        if synthetic_fixture_mode and not openings:
            raise InputError(f"/banks/{label} must contain at least one synthetic centre")
        for index, opening in enumerate(openings):
            if not isinstance(opening, dict):
                raise InputError(f"/banks/{label}/{index} must be an object")
            finite_array(
                opening.get("center_longitudinal_vertical"),
                (2,),
                f"/banks/{label}/{index}/center_longitudinal_vertical",
            )
        counts[label] = len(openings)
    return centroid, frame, counts


def export_selection(mesh: trimesh.Trimesh, mask: np.ndarray, path: Path) -> dict[str, object]:
    part = mesh.submesh([mask], append=True, repair=False)
    part.export(path, file_type="ply", encoding="binary")
    return {
        "path": str(path.resolve()),
        "vertices": int(len(part.vertices)),
        "triangles": int(len(part.faces)),
        "watertight": bool(part.is_watertight),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("interfaces", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--input-sha256")
    parser.add_argument("--interfaces-sha256")
    parser.add_argument(
        "--synthetic-fixture-mode",
        action="store_true",
        help="allow reduced synthetic banks; never use for the canonical scan",
    )
    args = parser.parse_args()

    actual_input_sha256 = sha256(args.input)
    actual_interfaces_sha256 = sha256(args.interfaces)
    try:
        if not args.synthetic_fixture_mode:
            actual_input_sha256 = require_sha256(args.input, args.input_sha256, "input")
            actual_interfaces_sha256 = require_sha256(
                args.interfaces, args.interfaces_sha256, "interfaces"
            )
        data = json.loads(args.interfaces.read_text())
        centroid, frame, bank_counts = validate_interfaces(data, args.synthetic_fixture_mode)
    except (InputError, json.JSONDecodeError) as error:
        raise SystemExit(f"invalid interface contract: {error}") from error

    mesh = trimesh.load_mesh(args.input, process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise SystemExit("input must be one non-empty triangular mesh")
    if not np.all(np.isfinite(mesh.vertices)):
        raise SystemExit("input mesh vertices must be finite")
    args.output.mkdir(parents=True, exist_ok=True)
    centres = np.asarray(mesh.triangles_center)
    coordinates = (centres - centroid) @ frame.T

    bank_masks = {}
    for label, sign in (("positive", 1), ("negative", -1)):
        mask = np.zeros(len(mesh.faces), dtype=bool)
        for opening in data["banks"][label]:
            longitudinal, vertical = opening["center_longitudinal_vertical"]
            radial = np.linalg.norm(coordinates[:, [0, 2]] - [longitudinal, vertical], axis=1)
            mask |= (radial < 72.0) & (sign * coordinates[:, 1] > 115.0)
        bank_masks[label] = mask

    central_mask = np.abs(coordinates[:, 1]) <= 115.0
    classified = central_mask | bank_masks["positive"] | bank_masks["negative"]
    unclassified_mask = ~classified
    report = {
        "input": str(args.input.resolve()),
        "method": f"validated-frame spatial masks around {sum(bank_counts.values())} opening centres",
        "interface_validation": {
            "mode": "synthetic_fixture" if args.synthetic_fixture_mode else "canonical",
            "finite_values": True,
            "frame_orthonormal_direct": True,
            "bank_center_counts": bank_counts,
            "input_sha256": actual_input_sha256,
            "interfaces_sha256": actual_interfaces_sha256,
            "provenance_hashes_matched_external_expectations": not args.synthetic_fixture_mode,
        },
        "classification_confidence": "medium_for_rows_low_for_remaining_semantics",
        "parts": {
            "central_crankcase_envelope_uncapped": export_selection(
                mesh, central_mask, args.output / "central-crankcase-envelope-uncapped.ply"
            ),
            "positive_six_cylinders_uncapped": export_selection(
                mesh, bank_masks["positive"], args.output / "positive-six-cylinders-uncapped.ply"
            ),
            "negative_six_cylinders_uncapped": export_selection(
                mesh, bank_masks["negative"], args.output / "negative-six-cylinders-uncapped.ply"
            ),
            "external_unclassified": export_selection(
                mesh, unclassified_mask, args.output / "external-unclassified.ply"
            ),
        },
        "limitations": [
            "Parts are spatial review regions, not manufacturing bodies.",
            "Cut boundaries are intentionally left open.",
            "The central region may include accessories and the outer region may include crankcase surfaces.",
            "No surface is deleted from the source or accepted reference mesh.",
        ],
    }
    (args.output / "segmentation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
