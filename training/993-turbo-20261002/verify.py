#!/usr/bin/env python3
"""Check the committed dataset's provenance, hashes, schemas and split isolation."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root=ROOT, check_input_hashes=True):
    repo = root.parents[1]
    manifest = read_json(root / "manifest.json")
    require(not manifest["training_run"] and not manifest["tokenized"], "Unexpected training/tokenization claim")
    require(manifest["token_count"] is None, "Unaudited token count")
    for entry in manifest["outputs"]:
        path = root / entry["path"]
        require(path.is_file(), f"Missing output: {entry['path']}")
        require(digest(path.read_bytes()) == entry["sha256"], f"Output hash mismatch: {entry['path']}")
    require(digest((root / "prepare.py").read_bytes()) == manifest["builder_sha256"], "Builder hash mismatch")
    if check_input_hashes:
        for entry in manifest["inputs"]:
            path = repo / entry["path"]
            require(path.is_file(), f"Missing catalog input: {entry['path']}")
            require(digest(path.read_bytes()) == entry["sha256"], f"Input hash mismatch: {entry['path']}")

    provenance = read_jsonl(root / "provenance.jsonl")
    passages = {p["id"]: p for p in read_jsonl(root / "passages.jsonl")}
    ledger = read_json(root / "split-ledger.json")
    passage_ids = [entry["record_id"] for entry in ledger["records"]]
    require(len(passage_ids) == len(set(passage_ids)), "Duplicate passage in split ledger")
    require(set(passage_ids) == set(passages), "Passage/ledger coverage mismatch")
    partition_sets = {"source": defaultdict(set), "family": defaultdict(set), "claim": defaultdict(set),
                      "record": defaultdict(set), "component": defaultdict(set)}
    ledger_by_id = {entry["record_id"]: entry for entry in ledger["records"]}
    for entry in ledger["records"]:
        split = entry["split"]
        for field, label in (("source_ids", "source"), ("source_families", "family"), ("claim_ids", "claim")):
            for value in entry[field]:
                partition_sets[label][value].add(split)
        partition_sets["record"][entry["record_id"]].add(split)
        partition_sets["component"][entry["component"]].add(split)
    for label, values in partition_sets.items():
        require(all(len(splits) == 1 for splits in values.values()), f"Cross-partition {label} leakage")

    rows, counts = {}, {}
    for dataset, directory in (("cpt", "cpt_text"), ("sft", "sft_messages")):
        counts[dataset] = {}
        for split in ("train", "valid", "test"):
            content = read_jsonl(root / directory / f"{split}.jsonl")
            require(content, f"Empty {dataset}/{split}")
            rows[(dataset, split)] = content
            counts[dataset][split] = len(content)
            require(len(content) == manifest["counts"][dataset][split], f"Count mismatch: {dataset}/{split}")
            for row in content:
                if dataset == "cpt":
                    require(set(row) == {"text"} and isinstance(row["text"], str), "Invalid CPT schema")
                else:
                    require(set(row) == {"messages"}, "Invalid SFT fields")
                    messages = row["messages"]
                    require([message.get("role") for message in messages] == ["system", "user", "assistant"],
                            "Invalid native message roles")
                    require(all(set(message) == {"role", "content"} and isinstance(message["content"], str)
                                and message["content"] for message in messages), "Invalid message content")
    seen = set()
    text_split = defaultdict(set)
    for record in provenance:
        key = (record["dataset"], record["split"], record["row_index"])
        require(key not in seen, "Repeated provenance row")
        seen.add(key)
        require(record["record_id"] in passages, "Unknown provenance passage")
        require(record["training_eligibility"] != "exclude_unvalidated_hypothesis", "Excluded hypothesis included")
        expected = ledger_by_id[record["record_id"]]
        for field in ("split", "source_ids", "source_families", "claim_ids", "component"):
            require(record[field] == expected[field], f"Provenance/ledger mismatch: {field}")
        require(record["source_ids"] and len(record["source_ids"]) == len(record["source_paths"])
                == len(record["source_urls"]), "Incomplete provenance")
        for source_path in record["source_paths"]:
            source = read_json(repo / source_path) if check_input_hashes else None
            if source is not None:
                require(source.get("source_id", source.get("id", source.get("dataset_id"))) in record["source_ids"],
                        "Source ID closure failure")
        content = rows[(record["dataset"], record["split"])][record["row_index"]]
        require(digest(canonical(content)) == record["content_sha256"], "Provenance content hash mismatch")
        require(record["synthetic"] and record.get("synthetic_scope"), "Authored wording disclosure missing")
        if record["dataset"] == "sft":
            citation = f"[{record['record_id']}]"
            require(citation in content["messages"][1]["content"] and citation in content["messages"][2]["content"],
                    "Grounded SFT citation missing")
        text_split[record["content_sha256"]].add(record["split"])
    require(len(seen) == sum(sum(value.values()) for value in counts.values()), "Provenance row coverage mismatch")
    require(all(len(splits) == 1 for splits in text_split.values()), "Exact duplicate content across partitions")

    # Inspect data only, not code/docs where forbidden-field names are policy descriptions.
    payload = "\n".join((root / path["path"]).read_text(encoding="utf-8") for path in manifest["outputs"])
    for forbidden in ("/workspace/", "/tmp/", "porschefanatics.com", "engine-reference-data.json", '"exact_quotes"'):
        require(forbidden not in payload, f"Private/raw source content marker: {forbidden}")
    require(not re.search(r"W(?:P0|P1|09)[A-HJ-NPR-Z0-9]{14}", payload), "Potential complete vehicle identifier")
    return {"status": "ok", "counts": counts, "source_families": len(partition_sets["family"]),
            "reviewed_claims": len(partition_sets["claim"]), "input_hashes_checked": check_input_hashes,
            "tokenization_or_model_quality_assessed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--skip-input-hashes", action="store_true", help="For a standalone data export without catalog files")
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.root.resolve(), not arguments.skip_input_hashes), indent=2))
