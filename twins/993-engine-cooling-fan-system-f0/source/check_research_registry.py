#!/usr/bin/env python3
"""Check the research ledger without promoting literature into engineering evidence."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = Path(__file__).resolve().parents[1] / "program/research/dossier.json"


def validate(data):
    groups = ("sources", "claims", "parameters", "contradictions", "coverage")
    ids = [record["id"] for group in groups for record in data[group]]
    if len(set(ids)) != len(ids):
        raise ValueError("Research record IDs must be globally unique")
    sources = {source["id"]: source for source in data["sources"]}
    for source in sources.values():
        if source["source_kind"].startswith("project_") and source["independent_of_project"]:
            raise ValueError("Project-derived sources cannot independently corroborate the project")
        if not source.get("url") and not source.get("local_path"):
            raise ValueError("Research sources require a URL or local reference")
        if source.get("local_path") and not (ROOT / source["local_path"]).is_file():
            raise ValueError("Missing local research source")
        if source.get("origin_source_id") and source["origin_source_id"] not in sources:
            raise ValueError("Missing original source in a republication chain")
    for group in ("claims", "parameters", "coverage"):
        for record in data[group]:
            if any(source_id not in sources for source_id in record["source_ids"]):
                raise ValueError("Unknown research source reference")
    for claim in data["claims"]:
        if claim["engineering_validation"]:
            raise ValueError("A literature claim does not validate the engineering model")
        if not claim["source_ids"] and claim["status"] != "research_question":
            raise ValueError("Unsupported claims must remain explicit research questions")
    for parameter in data["parameters"]:
        value = parameter["value"]
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Research parameter values must be finite numbers or null")
            if not parameter["unit"] or not parameter["variant"] or not parameter["conditions"] or not parameter["source_ids"]:
                raise ValueError("Numerical parameters require units, variant, conditions and provenance")
        if parameter["engineering_use_approved"]:
            raise ValueError("This research ledger grants no engineering approval")
    for conflict in data["contradictions"]:
        if any(record_id not in ids for record_id in conflict["record_ids"]):
            raise ValueError("Unknown contradiction reference")
    return data


def check():
    data = validate(json.loads(REGISTRY.read_text()))
    from build_research_index import build
    index = json.loads((REGISTRY.parent / "source-index.json").read_text())
    if build() != index:
        raise ValueError("Research corpus index is stale")
    print(f"Research ledger references and scope passed: {len(data['sources'])} sources, "
          f"{len(data['claims'])} claims, {len(data['parameters'])} parameters")


if __name__ == "__main__":
    check()
