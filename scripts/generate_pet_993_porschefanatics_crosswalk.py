#!/usr/bin/env python3
"""Link exact PorscheFanatics replacement claims to PET 993 part masters.

Only explicit ``replacesOem`` references are eligible. General 993 fitment,
category similarity, names and search text never create a part-master link.
Detailed commercial records remain in ignored ``work/`` output; the tracked
manifest contains aggregate counts and source/output digests only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT.parent / "porschefanatics.com"
READINESS_INDEX = ROOT / "twins" / "pet-993" / "engineering-readiness-f0.json"
OUTPUT = ROOT / "twins" / "pet-993" / "porschefanatics-crosswalk-f0.json"
WORK_OUTPUT = ROOT / "work" / "pet-993" / "porschefanatics-crosswalk-f0.jsonl"
QUALIFIED_MATERIAL_BASES = {"stated-in-listing", "manufacturer-specification"}


class ContractError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def normalize_oem_reference(value: Any) -> str:
    return "".join(character for character in str(value).upper() if character.isalnum())


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def render_jsonl(values: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n"
        for value in values
    )


def pet_master_map() -> dict[str, dict[str, str]]:
    index = load_json(READINESS_INDEX)
    if not isinstance(index, dict):
        raise ContractError("readiness_index_not_object")
    result: dict[str, dict[str, str]] = {}
    for shard in index.get("output", {}).get("shards", []):
        path = ROOT / str(shard.get("path", ""))
        if not path.is_file() or sha256_file(path) != shard.get("sha256"):
            raise ContractError(f"readiness_shard_digest:{shard.get('shard_id')}")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            task = json.loads(line)
            reference = str(task.get("subject", {}).get("normalized_oem_reference", ""))
            twin_id = str(task.get("part_master_twin_id", ""))
            engineering_task_id = str(task.get("engineering_task_id", ""))
            if not reference or not twin_id or reference in result:
                raise ContractError(f"pet_master_identity:{reference}")
            result[reference] = {
                "part_master_twin_id": twin_id,
                "engineering_task_id": engineering_task_id,
            }
    if len(result) != 6013:
        raise ContractError("pet_master_count")
    return result


def source_paths(source_root: Path) -> list[Path]:
    paths = sorted((source_root / "data" / "parts").glob("*.json"))
    if not paths:
        raise ContractError(f"missing_porschefanatics_part_shards:{source_root}")
    return paths


def direct_993_fitment(part: dict[str, Any]) -> bool:
    return any(
        isinstance(item, dict) and item.get("generationId") == "993"
        for item in part.get("fitment", [])
    )


def source_records(part: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for source in part.get("sources", []):
        if not isinstance(source, dict):
            continue
        records.append(
            {
                "url": source.get("url"),
                "publisher": source.get("publisher"),
                "title": source.get("title"),
                "accessed": source.get("accessed"),
            }
        )
    return records


def build(source_root: Path) -> tuple[dict[str, Any], str]:
    masters = pet_master_map()
    paths = source_paths(source_root)
    links: list[dict[str, Any]] = []
    total_records = 0
    direct_993_records = 0
    records_with_replaces_oem = 0
    for path in paths:
        payload = load_json(path)
        if not isinstance(payload, list):
            raise ContractError(f"part_shard_not_array:{path.name}")
        for part in payload:
            if not isinstance(part, dict):
                raise ContractError(f"part_record_not_object:{path.name}")
            total_records += 1
            fits_993 = direct_993_fitment(part)
            direct_993_records += int(fits_993)
            replaces = part.get("replacesOem", [])
            if not isinstance(replaces, list):
                raise ContractError(f"replaces_oem_not_array:{part.get('id')}")
            records_with_replaces_oem += int(bool(replaces))
            for raw_reference in replaces:
                normalized = normalize_oem_reference(raw_reference)
                master = masters.get(normalized)
                if master is None:
                    continue
                manufacturing = part.get("manufacturing", {})
                if not isinstance(manufacturing, dict):
                    manufacturing = {}
                material_ids = [
                    str(value) for value in manufacturing.get("materialIds", [])
                ]
                material_basis = manufacturing.get("materialBasis")
                qualified_material_ids = (
                    material_ids
                    if material_basis in QUALIFIED_MATERIAL_BASES
                    else []
                )
                unqualified_material_ids = (
                    []
                    if material_basis in QUALIFIED_MATERIAL_BASES
                    else material_ids
                )
                performance = part.get("performance", {})
                if not isinstance(performance, dict):
                    performance = {}
                links.append(
                    {
                        "link_id": (
                            "PF-XWALK-"
                            + hashlib.sha256(
                                f"{part.get('id')}|{normalized}".encode("utf-8")
                            ).hexdigest()[:20].upper()
                        ),
                        "part_master_twin_id": master["part_master_twin_id"],
                        "engineering_task_id": master["engineering_task_id"],
                        "normalized_oem_reference": normalized,
                        "link_method": "exact_normalized_replacesOem",
                        "porschefanatics_record": {
                            "record_id": part.get("id"),
                            "source_shard": f"data/parts/{path.name}",
                            "direct_993_fitment": fits_993,
                            "manufacturing_process_id": manufacturing.get("processId"),
                            "additive": manufacturing.get("additive"),
                            "material_ids_with_qualified_basis": qualified_material_ids,
                            "material_ids_without_qualified_basis": unqualified_material_ids,
                            "material_basis": material_basis,
                            "published_weight_kg": performance.get("weightKg"),
                            "published_oem_weight_kg": performance.get("oemWeightKg"),
                            "performance_claim_basis": performance.get("claimBasis"),
                            "sources": source_records(part),
                        },
                        "evidence_boundary": {
                            "commercial_record_is_exact_oem_replacement_claim": True,
                            "commercial_record_proves_original_oem_geometry": False,
                            "commercial_record_proves_original_oem_material": False,
                            "commercial_process_is_selected_reproduction_route": False,
                            "commercial_fitment_is_complete_vehicle_bom_evidence": False,
                            "alternative_is_functionally_equivalent": False,
                            "manufacturing_release_authorized": False,
                        },
                    }
                )
    links.sort(key=lambda item: (item["part_master_twin_id"], item["link_id"]))
    link_text = render_jsonl(links)
    linked_masters = {item["part_master_twin_id"] for item in links}
    linked_references = {item["normalized_oem_reference"] for item in links}
    by_master = Counter(item["part_master_twin_id"] for item in links)
    by_process = Counter(
        str(item["porschefanatics_record"]["manufacturing_process_id"])
        for item in links
    )
    manifest = {
        "$comment": (
            "Crosswalk F0 des seules revendications replacesOem exactes de "
            "PorscheFanatics vers les maitres PET. Les details commerciaux sont "
            "en sortie de travail; aucune geometrie, matiere OEM ou equivalence "
            "fonctionnelle n'est promue."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "expected_source_root": "../porschefanatics.com",
            "part_shards": [
                {
                    "path": f"data/parts/{path.name}",
                    "sha256": sha256_file(path),
                }
                for path in paths
            ],
            "engineering_readiness_index": relative(READINESS_INDEX),
            "engineering_readiness_index_sha256": sha256_file(READINESS_INDEX),
            "eligible_link_field": "replacesOem",
            "prohibited_link_methods": [
                "name_similarity",
                "description_similarity",
                "category_similarity",
                "generation_fitment_without_oem_reference",
                "llm_inference",
            ],
        },
        "scope": {
            "porschefanatics_part_records": total_records,
            "direct_993_fitment_records": direct_993_records,
            "records_with_replaces_oem": records_with_replaces_oem,
            "exact_pet_replacement_links": len(links),
            "linked_pet_part_masters": len(linked_masters),
            "linked_normalized_oem_references": len(linked_references),
            "links_with_qualified_material_basis": sum(
                bool(
                    item["porschefanatics_record"][
                        "material_ids_with_qualified_basis"
                    ]
                )
                for item in links
            ),
            "links_with_unqualified_material_labels": sum(
                bool(
                    item["porschefanatics_record"][
                        "material_ids_without_qualified_basis"
                    ]
                )
                for item in links
            ),
            "links_with_published_part_weight": sum(
                isinstance(
                    item["porschefanatics_record"]["published_weight_kg"],
                    (int, float),
                )
                for item in links
            ),
            "promoted_oem_geometry_material_process_or_validation_claims": 0,
        },
        "coverage": {
            "links_per_linked_master": dict(sorted(Counter(by_master.values()).items())),
            "links_by_commercial_process_id": dict(sorted(by_process.items())),
        },
        "output": {
            "tracked": False,
            "detailed_crosswalk": relative(WORK_OUTPUT),
            "record_count": len(links),
            "sha256": sha256_bytes(link_text.encode("utf-8")),
        },
        "rights_boundary": {
            "tracked_manifest_contains_commercial_descriptions": False,
            "tracked_manifest_contains_commercial_images": False,
            "tracked_manifest_contains_oem_reference_values": False,
            "source_urls_remain_in_work_output": True,
        },
        "claim_boundary": {
            "commercial_alternative_is_oem_geometry": False,
            "commercial_material_is_oem_material": False,
            "commercial_process_is_selected_manufacturing_route": False,
            "replacement_claim_proves_functional_equivalence": False,
            "generation_fitment_is_part_master_link": False,
            "llm_or_lexical_matching_enabled": False,
            "manufacturing_release_authorized": False,
        },
        "next_gate": (
            "review_each_exact_replacement_source_then_acquire_authorized_dimensions_"
            "interfaces_material_basis_and_test_evidence_before_any_engineering_promotion"
        ),
    }
    validate(manifest, links)
    return manifest, link_text


def validate(manifest: dict[str, Any], links: list[dict[str, Any]]) -> None:
    scope = manifest.get("scope", {})
    if scope.get("porschefanatics_part_records") != 109316:
        raise ContractError("source_part_record_count")
    if scope.get("direct_993_fitment_records") != 29400:
        raise ContractError("direct_993_fitment_count")
    if scope.get("exact_pet_replacement_links") != 6:
        raise ContractError("exact_replacement_link_count")
    if scope.get("linked_pet_part_masters") != 2:
        raise ContractError("linked_master_count")
    if scope.get("linked_normalized_oem_references") != 2:
        raise ContractError("linked_reference_count")
    if scope.get("links_with_qualified_material_basis") != 0:
        raise ContractError("qualified_material_basis_overclaim")
    if len(links) != 6 or len({item["link_id"] for item in links}) != 6:
        raise ContractError("detailed_link_identity")
    for link in links:
        if link.get("link_method") != "exact_normalized_replacesOem":
            raise ContractError("non_exact_link_method")
        evidence = link.get("evidence_boundary", {})
        if evidence.get("commercial_record_is_exact_oem_replacement_claim") is not True:
            raise ContractError("replacement_claim_missing")
        if any(
            value is not False
            for key, value in evidence.items()
            if key != "commercial_record_is_exact_oem_replacement_claim"
        ):
            raise ContractError("evidence_boundary_overclaim")
        record = link.get("porschefanatics_record", {})
        if record.get("material_ids_with_qualified_basis"):
            raise ContractError("material_promotion_overclaim")
    if scope.get("promoted_oem_geometry_material_process_or_validation_claims") != 0:
        raise ContractError("aggregate_promotion_overclaim")
    if any(value is not False for value in manifest.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")


def validate_index() -> None:
    manifest = load_json(OUTPUT)
    if not isinstance(manifest, dict):
        raise ContractError("tracked_manifest_not_object")
    sources = manifest.get("source_boundary", {})
    if sources.get("engineering_readiness_index_sha256") != sha256_file(READINESS_INDEX):
        raise ContractError("readiness_index_digest")
    if len(sources.get("part_shards", [])) != 11:
        raise ContractError("tracked_source_shard_count")
    scope = manifest.get("scope", {})
    if scope.get("exact_pet_replacement_links") != 6 or scope.get("linked_pet_part_masters") != 2:
        raise ContractError("tracked_crosswalk_counts")
    if manifest.get("output", {}).get("record_count") != 6:
        raise ContractError("tracked_output_count")
    if manifest.get("output", {}).get("tracked") is not False:
        raise ContractError("tracked_output_boundary")
    if any(value is not False for value in manifest.get("claim_boundary", {}).values()):
        raise ContractError("tracked_claim_boundary")


def run(source_root: Path, *, write: bool) -> int:
    manifest, work_text = build(source_root)
    expected = render_json(manifest)
    if write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        WORK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(expected, encoding="utf-8")
        WORK_OUTPUT.write_text(work_text, encoding="utf-8")
        print(f"wrote {relative(OUTPUT)} and {relative(WORK_OUTPUT)}")
        return 0
    if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
        print(f"stale generated crosswalk: {relative(OUTPUT)}", file=sys.stderr)
        return 1
    if not WORK_OUTPUT.is_file() or WORK_OUTPUT.read_text(encoding="utf-8") != work_text:
        print(f"stale generated crosswalk: {relative(WORK_OUTPUT)}", file=sys.stderr)
        return 1
    print(f"current {relative(OUTPUT)} and {relative(WORK_OUTPUT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_index()
            print(f"valid {relative(OUTPUT)}")
            return 0
        return run(args.source_root, write=args.write)
    except ContractError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
