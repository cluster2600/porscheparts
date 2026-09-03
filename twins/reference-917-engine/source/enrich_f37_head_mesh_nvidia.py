#!/usr/bin/env python3
"""Enrichit atomiquement le rapport tête F37 avec une attestation NVIDIA.

Le compteur VG.007 est lu dans l'attestation hash-liée; aucune valeur NVIDIA
n'est codée en dur. Cette seconde passe ne modifie jamais le STL local. Elle
peut aussi régénérer le PNG de preuve à partir des mêmes entrées géométriques
pour éviter qu'un visuel « NON EXÉCUTÉ » contredise le rapport enrichi.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected_json_object:{path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def enrich_report(
    report_path: Path,
    head_path: Path,
    attestation_path: Path,
    output_path: Path,
    *,
    preview_path: Path | None = None,
    oil_core_path: Path | None = None,
    contract_path: Path | None = None,
    geometry_report_path: Path | None = None,
) -> dict[str, Any]:
    report = load_object(report_path)
    attestation = load_object(attestation_path)
    require(report.get("phase") == "F37", "head_report_phase_mismatch")
    require(
        report.get("status")
        == "local_mesh_boolean_proof_complete_physical_and_manufacturing_release_blocked",
        "head_report_status_mismatch",
    )

    head_sha256 = sha256(head_path)
    recorded_head = report.get("local_only_artifacts", {}).get(head_path.name)
    require(isinstance(recorded_head, dict), "head_artifact_record_missing")
    require(recorded_head.get("sha256") == head_sha256, "head_artifact_hash_mismatch")
    require(
        recorded_head.get("bytes") == head_path.stat().st_size,
        "head_artifact_size_mismatch",
    )

    require(
        attestation.get("phase") == "F37_nvidia_geometry_validation_attestation",
        "attestation_phase_mismatch",
    )
    source_stl = attestation.get("linkage", {}).get("source_stl", {})
    require(source_stl.get("sha256") == head_sha256, "attestation_head_hash_mismatch")
    require(
        source_stl.get("bytes") == head_path.stat().st_size,
        "attestation_head_size_mismatch",
    )
    require(
        attestation.get("gates", {}).get("nvidia_geometry_clear") is True,
        "attestation_geometry_not_clear",
    )
    count = attestation.get("result", {}).get(
        "source_official_conversion_vg007_non_manifold_vertices"
    )
    require(
        isinstance(count, int) and not isinstance(count, bool) and count >= 0,
        "attestation_vg007_count_invalid",
    )
    require(
        attestation.get("gates", {}).get(
            "source_official_conversion_vg007_observed"
        )
        is (count > 0),
        "attestation_vg007_gate_mismatch",
    )

    report["nvidia_asset_validator_observation"] = {
        "tool": "NVIDIA Asset Validator",
        "rule": "VG.007",
        "exact_stl_sha256": head_sha256,
        "status": "pass" if count == 0 else "warning",
        "non_manifold_vertex_count": count,
        "vg007_clear": count == 0,
        "evidence": {
            # Stable across checkout and work-directory locations.
            "path": attestation_path.name,
            "bytes": attestation_path.stat().st_size,
            "sha256": sha256(attestation_path),
        },
        "interpretation": (
            "Aucun avertissement VG.007 sur le STL exact."
            if count == 0
            else "VG.007 signale des sommets non-manifold; impression bloquée malgré l'audit local."
        ),
    }

    gates = report.get("gates", {})
    for gate in (
        "metal_printability_demonstrated",
        "metal_print_authorized",
        "engine_start_authorized",
    ):
        require(gates.get(gate) is False, f"release_gate_must_remain_false:{gate}")
    local_vertex_ok = bool(
        report.get("strict_vertex_manifold_audit", {}).get(
            "strict_vertex_manifold"
        )
    )
    independent_agreement = bool(local_vertex_ok and count == 0)
    gates["nvidia_asset_validator_vg007_clear"] = count == 0
    gates["independent_topology_validators_agree"] = independent_agreement
    gates["geometry_redesign_required"] = not (
        gates.get("all_declared_accesses_cross_parent_skin") is True
        and gates.get("all_four_mount_planes_detected") is True
        and gates.get("oil_to_gas_flow_collision_absent") is True
        and independent_agreement
    )

    preview_inputs = (
        preview_path,
        oil_core_path,
        contract_path,
        geometry_report_path,
    )
    if any(value is not None for value in preview_inputs):
        require(all(value is not None for value in preview_inputs), "preview_inputs_incomplete")
        assert preview_path is not None
        assert oil_core_path is not None
        assert contract_path is not None
        assert geometry_report_path is not None
        require(
            report.get("inputs", {}).get("oil_core", {}).get("sha256")
            == sha256(oil_core_path),
            "preview_oil_core_hash_mismatch",
        )
        require(
            report.get("inputs", {}).get("contract_sha256") == sha256(contract_path),
            "preview_contract_hash_mismatch",
        )
        require(
            report.get("inputs", {}).get("geometry_report_sha256")
            == sha256(geometry_report_path),
            "preview_geometry_report_hash_mismatch",
        )

        # Import tardif: l'enrichissement JSON reste testable sans la pile de
        # maillage; le rendu n'est chargé que lorsqu'il est explicitement demandé.
        from build_f37_printable_head_mesh import (  # type: ignore[import-not-found]
            create_head_pads,
            load_mesh,
            render,
        )

        contract = load_object(contract_path)
        geometry_report = load_object(geometry_report_path)
        head = load_mesh(head_path, "head_preview")
        oil = load_mesh(oil_core_path, "oil_preview")
        head_pads, _, _, _, _, _ = create_head_pads(geometry_report, contract, head)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        render(head, oil, head_pads, report, preview_path)
        report.setdefault("local_only_artifacts", {})[preview_path.name] = {
            "bytes": preview_path.stat().st_size,
            "sha256": sha256(preview_path),
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    try:
        os.replace(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--oil-core", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--geometry-report", type=Path)
    args = parser.parse_args()
    output = args.output or args.report
    report = enrich_report(
        args.report,
        args.head,
        args.attestation,
        output,
        preview_path=args.preview,
        oil_core_path=args.oil_core,
        contract_path=args.contract,
        geometry_report_path=args.geometry_report,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "nvidia_vg007_non_manifold_vertices": report[
                    "nvidia_asset_validator_observation"
                ]["non_manifold_vertex_count"],
                "report": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
