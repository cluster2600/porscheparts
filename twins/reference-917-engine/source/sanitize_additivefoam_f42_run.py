#!/usr/bin/env python3
"""Publish path-free AdditiveFOAM run provenance from a private manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize(manifest: dict, results_path: Path, provenance: dict) -> dict:
    configured = []
    for case in manifest.get("configured_cases", []):
        clean = {key: value for key, value in case.items() if key != "case_path"}
        configured.append(clean)

    solver_results = {}
    for key, result in sorted(manifest.get("solver_results", {}).items()):
        layer_checks = []
        for layer in result.get("layer_log_checks", []):
            layer_checks.append(
                {
                    name: layer.get(name)
                    for name in (
                        "fatal_error",
                        "final_simulation_time_s",
                        "sha256",
                        "solver_end_marker",
                    )
                }
            )
        solver_results[key] = {
            name: result.get(name)
            for name in (
                "completed",
                "fatal_error",
                "layer_log_count",
                "return_code",
                "run_log_sha256",
                "vtk_file_count",
            )
        }
        solver_results[key]["layer_log_checks"] = layer_checks

    specification = manifest.get("specification", {})
    artifacts = manifest.get("artifacts", {})
    return {
        "schema_version": "1.0.0",
        "phase": "F42.2",
        "classification": "sanitized_solver_provenance_not_machine_qualification",
        "generated_at": manifest.get("generated_at"),
        "provenance": provenance,
        "specification_sha256": specification.get("sha256"),
        "results_sha256": sha256(results_path),
        "design": manifest.get("design"),
        "configured_cases": configured,
        "solver_results": solver_results,
        "source_artifacts": {
            name: value
            for name, value in artifacts.items()
            if isinstance(value, dict) and "sha256" in value
        },
        "gates": manifest.get("gates"),
        "privacy": {
            "absolute_paths_removed": True,
            "instance_identifiers_removed": True,
            "raw_solver_fields_published": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hardware-label", required=True)
    parser.add_argument("--container-digest", required=True)
    parser.add_argument("--openfoam-commit", required=True)
    parser.add_argument("--additivefoam-commit", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    provenance = {
        "hardware_label": args.hardware_label,
        "container_digest": args.container_digest,
        "openfoam_commit": args.openfoam_commit,
        "additivefoam_commit": args.additivefoam_commit,
        "source_commit": args.source_commit,
    }
    payload = sanitize(manifest, args.results, provenance)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if "/workspace/" in serialized or "case_path" in serialized:
        raise SystemExit("chemin_prive_detecte_dans_le_manifeste_public")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(json.dumps({"output": str(args.output), "runs": len(payload["solver_results"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
