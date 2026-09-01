#!/usr/bin/env python3
"""Consolide le contexte local NVIDIA avec les preuves F10 déjà versionnées."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON objet attendu: {path}")
    return payload


def source_catalog(project_root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted((project_root / "catalog/sources").glob("src-*.json")):
        payload = load_json(path)
        source_id = payload.get("source_id")
        if isinstance(source_id, str) and source_id:
            result[source_id] = payload
    return result


def evidence_ids(variant: dict[str, Any]) -> list[str]:
    identifiers: set[str] = set()
    fields = variant.get("geometry", {}).get("field_evidence", {})
    if isinstance(fields, dict):
        for values in fields.values():
            if isinstance(values, list):
                identifiers.update(str(value) for value in values if value)
    return sorted(identifiers)


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Contexte d'actif Porsche 917 F10",
        "",
        f"- Statut : `{payload['status']}`",
        f"- Variante : `{payload['variant_id']}`",
        f"- Actif source : `{payload['source_asset_path']}`",
        f"- Confiance : `{payload['confidence']['level']}`",
        f"- Recherche web : `{payload['web_research']['status']}`",
        "",
        "## Identité",
        "",
        payload["likely_identity"],
        "",
        "## Preuves dimensionnelles déclarées",
        "",
    ]
    for field, item in payload["documented_geometry"].items():
        lines.append(f"- `{field}` : `{item['value']}` — sources `{', '.join(item['source_ids'])}`")
    lines.extend(["", "## Limites", ""])
    lines.extend(f"- {item}" for item in payload["limitations"])
    lines.extend(["", "## Prompt Material/Physics", "", payload["material_physics_prompt"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", required=True, type=Path)
    parser.add_argument("--local-report", required=True, type=Path)
    parser.add_argument("--variant-manifest", required=True, type=Path)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--markdown-report", required=True, type=Path)
    args = parser.parse_args()

    asset = args.asset.resolve(strict=True)
    local = load_json(args.local_report.resolve(strict=True))
    manifest = load_json(args.variant_manifest.resolve(strict=True))
    variants = [item for item in manifest.get("variants", []) if item.get("variant_id") == args.variant]
    if len(variants) != 1:
        raise SystemExit("variante absente ou ambiguë dans le manifeste F10")
    variant = variants[0]
    geometry = variant.get("geometry", {})
    field_evidence = geometry.get("field_evidence", {})
    documented: dict[str, dict[str, Any]] = {}
    for field in ("cylinder_count", "bore_mm", "stroke_mm", "documented_displacement_cm3"):
        sources = field_evidence.get(field, []) if isinstance(field_evidence, dict) else []
        if field not in geometry or not isinstance(sources, list) or not sources:
            raise SystemExit(f"champ F10 sans preuve explicite: {field}")
        documented[field] = {"value": geometry[field], "source_ids": sorted(map(str, sources))}

    catalog = source_catalog(args.project_root.resolve(strict=True))
    ids = evidence_ids(variant)
    missing = [source_id for source_id in ids if source_id not in catalog]
    if missing:
        raise SystemExit(f"sources de contexte absentes: {missing}")
    evidence = [
        {
            "source_id": source_id,
            "title": catalog[source_id].get("title"),
            "url": catalog[source_id].get("url"),
            "source_type": catalog[source_id].get("source_type"),
            "quality": catalog[source_id].get("quality"),
            "rights": catalog[source_id].get("rights"),
        }
        for source_id in ids
    ]
    release = manifest.get("release_gates", {})
    if any(release.get(key) is not False for key in (
        "measured_variant_geometry_ready",
        "physical_kinematics_ready",
        "manufacturing_geometry_ready",
        "combustion_simulation_ready",
        "performance_claim_authorized",
    )):
        raise SystemExit("les limites de publication F10 attendues ne sont pas bloquées")

    prompt = (
        f"Contexte attesté: {variant['display_name']} ({variant['architecture']}), "
        f"{geometry['cylinder_count']} cylindres, alésage déclaré {geometry['bore_mm']} mm, "
        f"course déclarée {geometry['stroke_mm']} mm et cylindrée déclarée "
        f"{geometry['documented_displacement_cm3']} cm3. Les preuves sont limitées aux IDs "
        f"{', '.join(ids)}. Le stage est une géométrie visuelle F10: dimensions non sourcées, "
        "matières, masses, inerties, jeux, tolérances, frottements, températures et charges restent "
        "inconnus. Affecter uniquement des matériaux visuels conservateurs selon le prompt opérateur; "
        "pour la physique, conserver des corps/colliders diagnostiques et ne revendiquer ni fabrication, "
        "cinématique physique, puissance 1600 ch, combustion, durabilité, thermique ou sécurité."
    )
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "status": "passed",
        "passed": True,
        "source_asset_path": str(asset),
        "source_format": local.get("source_format"),
        "local_identifiers": local.get("local_identifiers", []),
        "variant_id": variant["variant_id"],
        "likely_identity": f"Moteur Porsche 917, branche {variant['display_name']}, proxy numérique F10",
        "manufacturer": "Porsche",
        "product_family": "Porsche 917",
        "application": "jumeau numérique exploratoire et diagnostic SimReady",
        "documented_geometry": documented,
        "evidence": evidence,
        "web_research": {
            "status": "pre_sourced_in_versioned_repository",
            "network_used_by_remote_phase": False,
            "recommended_queries": local.get("recommended_web_queries", []),
        },
        "material_hints": ["aucune matière mesurée ou certifiée dans le contrat F10"],
        "physics_hints": [
            "corps rigides et colliders uniquement diagnostiques",
            "cinématique physique et interfaces de charge non libérées",
        ],
        "confidence": {
            "level": "medium",
            "reason": "identité et quelques valeurs déclarées sourcées; matières et comportement physique non mesurés",
        },
        "release_gates": release,
        "limitations": [
            "géométrie F10 visuelle, non mesurée pour fabrication",
            "aucune validation de jeux, tolérances, matériaux ou fatigue",
            "aucune preuve de puissance, de combustion ou de fonctionnement moteur",
        ],
        "material_physics_prompt": prompt,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_report.write_text(markdown(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
