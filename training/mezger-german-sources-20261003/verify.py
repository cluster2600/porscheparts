#!/usr/bin/env python3
"""Verify the German-source increment against both frozen research packs."""
from __future__ import annotations

import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SPEC = importlib.util.spec_from_file_location("mezger_german_builder", ROOT / "prepare.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify():
    manifest = BUILD.read_json(ROOT / "manifest.json")
    require(not manifest["training_run"] and not manifest["tokenized"] and not manifest["model_weights_produced"],
            "Unsupported execution claim")
    require(manifest["token_count"] is None and not manifest["context_fit_verified"], "Unaudited token/context claim")
    require(manifest["cpt_wording_synthetic"] and manifest["sft_synthetic"] and not manifest["source_facts_synthetic"],
            "Authored-wording disclosure missing")
    require(manifest["evaluation_scope"] == "supplied_record_extraction_not_independent_reasoning", "Evaluation scope missing")
    require(manifest["source_family_aliases"] == BUILD.SOURCE_FAMILY_ALIASES,
            "Source-family alias policy differs from builder")
    require(manifest["source_family_alias_policy_sha256"] == BUILD.digest(BUILD.canonical(BUILD.SOURCE_FAMILY_ALIASES)),
            "Source-family alias policy hash mismatch")
    for kind, base in (("inputs", REPO), ("outputs", ROOT)):
        require(len({entry["path"] for entry in manifest[kind]}) == len(manifest[kind]), f"Repeated {kind} hash path")
        for entry in manifest[kind]:
            path = base / entry["path"]
            require(path.resolve().is_relative_to(base.resolve()), f"Escaping {kind} path")
            require(path.is_file(), f"Missing {kind} file: {entry['path']}")
            require(BUILD.digest(path.read_bytes()) == entry["sha256"], f"{kind} hash mismatch: {entry['path']}")
    require(BUILD.digest((ROOT / "prepare.py").read_bytes()) == manifest["builder_sha256"], "Builder hash mismatch")

    facts_list = BUILD.read_json(BUILD.FACTS)["records"]
    require(len({fact["id"] for fact in facts_list}) == len(facts_list), "Duplicate curated fact ID")
    facts = {fact["id"]: fact for fact in facts_list if fact["training_eligibility"] != "exclude"}
    excluded = BUILD.read_json(ROOT / "excluded.json")["records"]
    require({record["record_id"] for record in excluded} == {fact["id"] for fact in facts_list if fact["training_eligibility"] == "exclude"},
            "Excluded-reference coverage mismatch")
    require(len(facts_list) == manifest["counts"]["reference_records"], "Reference count mismatch")
    ledger = BUILD.read_json(ROOT / "split-ledger.json")
    require(ledger["empty_partitions_allowed"], "Empty-partition policy missing")
    require(ledger["source_family_aliases"] == BUILD.SOURCE_FAMILY_ALIASES, "Ledger source-family alias policy mismatch")
    require(len({record["record_id"] for record in ledger["records"]}) == len(ledger["records"]), "Repeated new ledger record")
    require({record["record_id"] for record in ledger["records"]} == set(facts), "New ledger/fact coverage mismatch")
    new_by_id = {record["record_id"]: record for record in ledger["records"]}
    prior_records, prior_ids = BUILD.prior_records_and_ids()
    require({fact["id"] for fact in facts_list}.isdisjoint(prior_ids), "New ID collides with frozen prior pack")
    require(ledger["prior_ledgers"] == [str((directory / "split-ledger.json").relative_to(REPO)) for directory in BUILD.PRIORS],
            "Frozen prior ledger dependency mismatch")
    combined = BUILD.constraints(prior_records + ledger["records"])
    # constraints() fails if a source, family or exact reviewed claim crosses partitions.
    component_partitions = defaultdict(set)
    sources, policy = BUILD.source_index(), BUILD.prior_policy()
    input_hash_paths = {entry["path"] for entry in manifest["inputs"]}
    require({str(path.relative_to(REPO)) for path in BUILD.prior_inputs()}.issubset(input_hash_paths),
            "Frozen prior dependency absent from input hashes")
    graph, first_claim = BUILD.Components(), {}
    for entry in ledger["records"]:
        families = entry["source_families"]
        require(families and families == sorted(set(families)), "Missing or repeated source family")
        for family in families:
            graph.union(families[0], family)
        for claim in entry["claim_ids"]:
            if claim in first_claim:
                graph.union(families[0], first_claim[claim])
            first_claim[claim] = families[0]
    expected_inherited = defaultdict(set)
    frozen_constraints = BUILD.constraints(prior_records)
    for entry in ledger["records"]:
        component = graph.find(entry["source_families"][0])
        require(entry["component"] == component, "Reviewed claim connected component mismatch")
        for kind in ("source_ids", "source_families", "claim_ids"):
            for key in entry[kind]:
                expected_inherited[component].update(frozen_constraints[kind].get(key, set()))
    for entry in ledger["records"]:
        inherited = expected_inherited[entry["component"]]
        require(len(inherited) <= 1, "Conflicting frozen component partitions")
        expected_split = next(iter(inherited), "train")
        require(entry["split"] == expected_split, "Unexpected new or changed partition assignment")
    for entry in ledger["records"]:
        fact = facts[entry["record_id"]]
        expected_sources = sorted(fact["source_ids"])
        require(expected_sources and expected_sources == entry["source_ids"], "Ledger source closure failure")
        expected_families = sorted({BUILD.source_family(sources[sid]["data"], policy) for sid in expected_sources})
        require(expected_families == entry["source_families"], "Source-family policy mismatch")
        claim = "fact:" + BUILD.digest(BUILD.canonical([fact["application"], fact["parameter"], fact["value"], fact.get("unit", "")]))
        require(entry["claim_ids"] == [claim], "Reviewed claim key mismatch")
        require(entry["split"] in BUILD.SPLITS, "Unknown partition")
        component_partitions[entry["component"]].add(entry["split"])
        if any("mahle" in family or family == "porsche-factory-and-archive" for family in expected_families):
            require(entry["split"] == "train", "Porsche/MAHLE source in holdout")
        for sid in expected_sources:
            require(str(sources[sid]["path"].relative_to(REPO)) in input_hash_paths, "Source file absent from input hashes")
    require(all(len(splits) == 1 for splits in component_partitions.values()), "Connected component split leakage")
    # Families connected by one record must remain one component, not merely one partition.
    family_components = defaultdict(set)
    for entry in ledger["records"]:
        for family in entry["source_families"]:
            family_components[family].add(entry["component"])
    require(all(len(components) == 1 for components in family_components.values()), "Document family split into components")
    expected_inputs = {str(BUILD.FACTS.relative_to(REPO))}
    expected_inputs.update(str(path.relative_to(REPO)) for path in BUILD.prior_inputs())
    expected_inputs.update(str(sources[sid]["path"].relative_to(REPO))
                           for fact in facts.values() for sid in fact["source_ids"])
    require(input_hash_paths == expected_inputs, "Input closure differs from curated sources and frozen dependencies")

    passages = jsonl(ROOT / "passages.jsonl")
    require(len({passage["id"] for passage in passages}) == len(passages) and {p["id"] for p in passages} == set(facts),
            "Passage coverage/identity mismatch")
    for passage in passages:
        fact = facts[passage["id"]]
        require(passage["text"] == BUILD.record_text(fact), "Authored passage differs from curated metadata")
        require(passage["training_eligibility"] == fact["training_eligibility"], "Passage eligibility mismatch")
        require(passage["source_locator"] == fact.get("locator", ""), "Passage source locator mismatch")
    rows = {}
    for dataset, directory in (("cpt", "cpt_text"), ("sft", "sft_messages")):
        for split in BUILD.SPLITS:
            rows[(dataset, split)] = jsonl(ROOT / directory / f"{split}.jsonl")
            require(len(rows[(dataset, split)]) == manifest["counts"][dataset][split], "Dataset count mismatch")
    provenance = jsonl(ROOT / "provenance.jsonl")
    row_keys, fact_datasets = set(), defaultdict(set)
    for record in provenance:
        key = (record["dataset"], record["split"], record["row_index"])
        require(key not in row_keys, "Repeated provenance row")
        row_keys.add(key)
        require(record["record_id"] in facts, "Unknown provenance fact")
        entry = new_by_id[record["record_id"]]
        for field in ("source_ids", "source_families", "claim_ids", "component", "split"):
            require(record[field] == entry[field], f"Provenance/ledger mismatch: {field}")
        fact = facts[record["record_id"]]
        require(record["synthetic"] and record["synthetic_scope"] and not record["raw_document_text"], "Authorship disclosure missing")
        require(record["training_eligibility"] == fact["training_eligibility"], "Provenance eligibility changed")
        require(record["source_locator"] == fact.get("locator", ""), "Provenance source locator changed")
        require(len(record["source_ids"]) == len(record["source_paths"]) == len(record["source_urls"]), "Incomplete source provenance")
        for sid, path, url in zip(record["source_ids"], record["source_paths"], record["source_urls"]):
            require(path == str(sources[sid]["path"].relative_to(REPO)), "Canonical source path mismatch")
            require(url == sources[sid]["data"]["url"], "Source URL mismatch")
        require(key[:2] in rows and 0 <= key[2] < len(rows[key[:2]]), "Provenance row address invalid")
        row = rows[key[:2]][key[2]]
        require(BUILD.digest(BUILD.canonical(row)) == record["content_sha256"], "Provenance content hash mismatch")
        text = BUILD.record_text(fact)
        citation = f"[{fact['id']}]"
        if record["dataset"] == "cpt":
            require(row == {"text": text + f" Research record: {citation}."}, "CPT content or schema mismatch")
        else:
            require(set(row) == {"messages"}, "Unexpected SFT fields")
            messages = row["messages"]
            require([message.get("role") for message in messages] == ["system", "user", "assistant"], "Invalid native message roles")
            require(all(set(message) == {"role", "content"} and isinstance(message["content"], str) for message in messages),
                    "Invalid native message schema")
            require(messages[0]["content"] == BUILD.SYSTEM, "System evidence policy mismatch")
            require(citation in messages[1]["content"] and text in messages[1]["content"], "Supplied evidence missing")
            require(messages[2]["content"] == text + " " + citation, "SFT answer alters factual metadata or qualification")
        fact_datasets[record["record_id"]].add(record["dataset"])
    expected_keys = {(dataset, split, index) for (dataset, split), items in rows.items() for index in range(len(items))}
    require(row_keys == expected_keys, "Provenance row coverage mismatch")
    require(set(fact_datasets) == set(facts) and all(value == {"cpt", "sft"} for value in fact_datasets.values()),
            "Each accepted fact must have CPT and SFT provenance")

    payload = "\n".join((ROOT / entry["path"]).read_text(encoding="utf-8") for entry in manifest["outputs"])
    for marker in ("/workspace/", "/tmp/", "porschefanatics.com", "engine-reference-data.json", '"exact_quotes"'):
        require(marker not in payload, f"Prohibited source/private content marker: {marker}")
    require(not re.search(r"W(?:P0|P1|09)[A-HJ-NPR-Z0-9]{14}", payload), "Potential vehicle identifier")
    return {"status": "ok", "counts": manifest["counts"], "combined_prior_partition_isolation": True,
            "frozen_prior_packs": [directory.name for directory in BUILD.PRIORS],
            "model_or_token_quality_assessed": False}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
