#!/usr/bin/env python3
"""Lie par SHA-256 un asset F37 et son rapport NVIDIA normalisé.

Cette attestation est un manifeste reproductible, pas une signature distante.
Elle consigne l'image, la commande déclarée par le rapport et la couche de
normalisation. Elle ne transforme jamais une validation Geometry en
autorisation de fabrication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def vg007_count(report: dict[str, Any]) -> int:
    issues = [item for item in report.get("issues", []) if "VG.007" in str(item.get("requirement", ""))]
    if len(issues) != 1:
        raise SystemExit("le rapport NVIDIA source doit contenir exactement une issue VG.007")
    match = re.search(r"(\d+) vertices are non-manifold", str(issues[0].get("message", "")))
    if match is None:
        raise SystemExit("le compteur VG.007 source est illisible")
    return int(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--normalized-report", type=Path, required=True)
    parser.add_argument("--source-stl", type=Path, required=True)
    parser.add_argument("--source-converted-usd", type=Path, required=True)
    parser.add_argument("--source-geometry-report", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--normalization-layer", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.normalized_report.read_text(encoding="utf-8"))
    source_report = json.loads(args.source_geometry_report.read_text(encoding="utf-8"))
    command = report.get("command")
    if not isinstance(command, list) or not command:
        raise SystemExit("commande absente du rapport NVIDIA normalisé")
    asset_path = Path(str(report.get("asset_path", "")))
    command_asset_path = Path(str(command[-1]))
    same_basename = asset_path.name == args.asset.name
    command_matches_report_asset = command_asset_path == asset_path
    image_digest_pinned = "@sha256:" in args.image
    categories = report.get("categories", [])
    command_category_geometry = bool(
        "Geometry" in categories
        and "--category" in command
        and command.index("--category") + 1 < len(command)
        and command[command.index("--category") + 1] == "Geometry"
    )
    source_usd_path = Path(str(source_report.get("asset_path", "")))
    source_vg007 = vg007_count(source_report)
    source_report_matches_usd = source_usd_path.name == args.source_converted_usd.name
    issue_counts = report.get("issue_counts", {})
    geometry_clear = bool(
        report.get("status") == "PASS"
        and report.get("passed") is True
        and all(int(issue_counts.get(level, 0)) == 0 for level in ("ERROR", "FAILURE", "INFO", "WARNING"))
    )
    payload = {
        "schema_version": "1.0.0",
        "phase": "F37_nvidia_geometry_validation_attestation",
        "status": "hash_linked_geometry_pass_manufacturing_release_blocked",
        "linkage": {
            "asset": file_record(args.asset),
            "normalized_report": file_record(args.normalized_report),
            "report_asset_path": str(asset_path),
            "report_asset_basename_matches": same_basename,
            "command_asset_path": str(command_asset_path),
            "command_matches_report_asset_path": command_matches_report_asset,
            "source_stl": file_record(args.source_stl),
            "source_converted_usd": file_record(args.source_converted_usd),
            "source_geometry_report": file_record(args.source_geometry_report),
            "source_report_asset_path": str(source_usd_path),
            "source_report_matches_converted_usd": source_report_matches_usd,
        },
        "execution": {
            "image": args.image,
            "vast_instance_id": args.instance_id,
            "coexecution_claim": "operator_recorded_same_run_context",
            "command_from_normalized_report": command,
            "validator_tool": report.get("validator_tool"),
            "validator_skill": report.get("validator_skill"),
            "normalization_layer": args.normalization_layer,
        },
        "result": {
            "status": report.get("status"),
            "passed": report.get("passed"),
            "issue_counts": issue_counts,
            "geometry_clear": geometry_clear,
            "source_official_conversion_vg007_non_manifold_vertices": source_vg007,
        },
        "gates": {
            "asset_report_hashes_recorded": True,
            "report_names_same_asset": same_basename,
            "command_targets_report_asset": command_matches_report_asset,
            "container_image_digest_pinned": image_digest_pinned,
            "geometry_category_requested": command_category_geometry,
            "source_geometry_report_matches_converted_usd": source_report_matches_usd,
            "source_official_conversion_vg007_observed": source_vg007 > 0,
            "nvidia_geometry_clear": geometry_clear,
            "production_brep_validated": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "limitations": [
            "Le wrapper de compétence a normalisé le rapport brut; le rapport brut temporaire n'a pas été conservé dans cette attestation.",
            "Le STL source, le USDC officiel et son rapport VG.007 sont liés par empreinte, mais le rapport normalisé ne prouve pas cryptographiquement que le convertisseur a consommé ce STL.",
            "L'image et l'instance sont consignées depuis le contexte opérateur du même run; elles ne sont pas attestées indépendamment par le rapport normalisé.",
            "Les SHA-256 lient les deux fichiers enregistrés et leur contexte déclaré, mais ne constituent pas une signature cryptographique de la machine Vast.",
            "Un PASS Geometry sur un USDA diagnostic ne remplace ni CAO B-Rep de production, ni qualification LPBF, ni CT/CMM, ni validation fabrication.",
        ],
    }
    if not (
        same_basename
        and command_matches_report_asset
        and image_digest_pinned
        and command_category_geometry
        and source_report_matches_usd
        and source_vg007 > 0
        and geometry_clear
    ):
        raise SystemExit("le rapport ne prouve pas un PASS Geometry pour cet asset")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
