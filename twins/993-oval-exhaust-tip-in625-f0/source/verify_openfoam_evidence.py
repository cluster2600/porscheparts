#!/usr/bin/env python3
"""Vérifie les traces brutes du criblage OpenFOAM de l'embout ovale."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


PART_ID = "993-EXH-OVAL-TIP-IN625-F0-0001"


class EvidenceError(RuntimeError):
    """Échec déterministe de la vérification des preuves."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "report_not_an_object")
    return value


def case_slug(mesh_size_mm: float) -> str:
    return f"mesh-{str(mesh_size_mm).replace('.', 'p')}"


def verify(args: argparse.Namespace) -> dict[str, Any]:
    report_path = args.report.resolve()
    source_path = args.source.resolve()
    raw_root = args.raw_root.resolve()
    require(report_path.is_file(), "missing_report")
    require(source_path.is_file(), "missing_source")
    require(raw_root.is_dir(), "missing_raw_root")
    report = load(report_path)
    require(report.get("part_id") == PART_ID, "wrong_part_id")
    runtime = report.get("runtime", {})
    require("@sha256:" in str(runtime.get("runtime_image_ref", "")), "runtime_image_not_digest_pinned")
    require(str(runtime.get("runtime_image_id", "")).startswith("sha256:"), "runtime_image_id_missing")

    cases = report.get("cases")
    require(isinstance(cases, list) and len(cases) == 3, "expected_three_cases")
    mesh_sizes = [float(case["mesh"]["mesh_size_mm"]) for case in cases]
    require(mesh_sizes == [6.0, 4.0, 3.0], "unexpected_mesh_sequence")
    verified_artifacts = 0
    artifact_digests: list[str] = []
    for case in cases:
        case_dir = (raw_root / case_slug(float(case["mesh"]["mesh_size_mm"]))).resolve()
        require(case_dir.parent == raw_root, "case_path_escapes_raw_root")
        require(case_dir.is_dir(), "missing_case_directory")
        artifacts = case.get("artifacts")
        require(isinstance(artifacts, dict) and len(artifacts) == 8, "expected_eight_case_artifacts")
        for name, expected in artifacts.items():
            require(isinstance(name, str) and Path(name).name == name, "invalid_artifact_name")
            path = (case_dir / name).resolve()
            require(path.parent == case_dir and path.is_file(), "missing_or_escaping_artifact")
            require(path.stat().st_size == expected.get("bytes"), f"artifact_size_mismatch:{name}")
            actual_digest = sha256(path)
            require(actual_digest == expected.get("sha256"), f"artifact_hash_mismatch:{name}")
            artifact_digests.append(actual_digest)
            verified_artifacts += 1
        residuals = case["solver"]["final_initial_residuals"]
        limits = case["solver"]["residual_limits"]
        require(set(residuals) == set(limits), "residual_field_mismatch")
        require(all(float(residuals[key]) <= float(limits[key]) for key in limits), "residual_limit_failed")
        require(case["solver"]["converged"] is True, "case_not_converged")

    previous = cases[-2]["results"]
    finest = cases[-1]["results"]
    pressure_change = abs(
        finest["bulk_total_pressure_drop_pa"] - previous["bulk_total_pressure_drop_pa"]
    ) / abs(finest["bulk_total_pressure_drop_pa"])
    velocity_change = abs(
        finest["outlet_area_average_speed_m_s"] - previous["outlet_area_average_speed_m_s"]
    ) / abs(finest["outlet_area_average_speed_m_s"])
    declared = report["grid_comparison_fine_vs_previous"]
    require(
        math.isclose(pressure_change, declared["bulk_total_pressure_drop_relative_change"], rel_tol=0.0, abs_tol=1e-14),
        "pressure_grid_change_mismatch",
    )
    require(
        math.isclose(velocity_change, declared["outlet_velocity_relative_change"], rel_tol=0.0, abs_tol=1e-14),
        "velocity_grid_change_mismatch",
    )
    threshold = float(declared["screening_threshold"])
    numerical = report["numerical_gates"]
    expected_numerical = {
        "all_cases_converged": True,
        "bulk_total_pressure_drop_grid_change_below_10_percent": pressure_change <= threshold,
        "outlet_velocity_grid_change_below_10_percent": velocity_change <= threshold,
        "all_extended_mesh_checks_passed": all(
            case["mesh_validation"]["extended_check_mesh_passed"] for case in cases
        ),
    }
    require(numerical == expected_numerical, "numerical_gate_mismatch")
    engineering = report.get("engineering_gates")
    require(isinstance(engineering, dict) and engineering, "missing_engineering_gates")
    require(not any(engineering.values()), "engineering_gate_open")
    require(report.get("release_authorized") is False, "release_gate_open")

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "classification": "raw_openfoam_artifacts_hash_verified_public_summary",
        "source_sha256": sha256(source_path),
        "report_sha256": sha256(report_path),
        "runtime_image_ref": runtime["runtime_image_ref"],
        "runtime_image_id": runtime["runtime_image_id"],
        "mesh_sizes_mm": mesh_sizes,
        "verified_raw_artifact_count": verified_artifacts,
        "unique_raw_artifact_digest_count": len(set(artifact_digests)),
        "recomputed_grid_change": {
            "bulk_total_pressure_drop_relative": pressure_change,
            "outlet_velocity_relative": velocity_change,
        },
        "numerical_gates": numerical,
        "engineering_gates_all_closed": True,
        "release_authorized": False,
        "raw_artifacts_published": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit("REFUS EVIDENCE: output_exists")
    summary = verify(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceError as exc:
        raise SystemExit(f"REFUS EVIDENCE: {exc}") from exc
