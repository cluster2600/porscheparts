#!/usr/bin/env python3
"""Prepare conditional candidates from licensed historical train sources only.

Reads the existing source/paragraph manifests and the explicitly approved train
file. Does not open evaluation question/rubric files, run directories or gold.
"""
import argparse
import collections
import json
from pathlib import Path

from pipeline import SENSITIVE_CONTENT, audit, digest, encoded, normalized, read_jsonl, validate_messages, write_json, write_jsonl


def checked(path, expected):
    raw = Path(path).read_bytes()
    if digest(raw) != expected:
        raise ValueError("Frozen input hash mismatch: " + str(path))
    return raw


def prepare(root, contract_path, exclusions_path, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Output exists")
    contract = json.loads(Path(contract_path).read_text())
    for name in contract["protected_local_prefixes"]:
        boundary = Path(name).resolve()
        if root == boundary or boundary in root.parents or output == boundary or boundary in output.parents:
            raise ValueError("Protected root")
    exclusions = json.loads(Path(exclusions_path).read_text())
    policy = contract["source_family_policy"]
    admitted = set(policy["admitted_historical_train"])
    held_valid = set(policy["not_admitted_historical_valid"])
    old_dev = set(policy["not_admitted_historical_test_now_development"])
    if admitted & (held_valid | old_dev):
        raise ValueError("Contradictory family contract")
    package = root / "training/qwen-metal-additive-20261002"
    grounded = package / "grounded-v3"
    manifest_path = grounded / "manifest.json"
    parent = json.loads(manifest_path.read_text())
    frozen = {"manifest": digest(manifest_path.read_bytes())}
    for name in ("sources.json", "passages.jsonl"):
        checked(grounded / name, parent["output_hashes"][name])
        frozen[name] = parent["output_hashes"][name]
    source_data = json.loads((grounded / "sources.json").read_text())
    source_by_id = {s["source_id"]: s for s in source_data}
    attribution = []
    for source_id in sorted(admitted):
        source = source_by_id[source_id]
        if source["split"] != "train" or source["license"] != "CC BY 4.0" or not source.get("authors") or not source.get("url"):
            raise ValueError("Source gate failed: " + source_id)
        notice_path, artifact_path = source["license_evidence"], source["original_path"]
        # Relative source locators cannot escape the fixed package.
        for path in (notice_path, artifact_path):
            resolved = (package / path).resolve()
            if package not in resolved.parents:
                raise ValueError("Source locator escapes package")
        notice = checked(package / notice_path, parent["input_hashes"][notice_path])
        checked(package / artifact_path, source["snapshot_sha256"])
        if b"creativecommons.org/licenses/by/4.0" not in notice.lower() and b"cc by 4.0" not in notice.lower():
            raise ValueError("License notice does not establish declared reuse")
        attribution.append({**source, "license_evidence_sha256": digest(notice),
                            "source_metadata_sha256": frozen["sources.json"]})
    retired = {v for r in exclusions["retired_excerpts"] for k, v in r.items() if k.endswith("sha256")}
    paragraphs = read_jsonl(grounded / "passages.jsonl")
    allowed_passages, rejected, candidates, cpt = {}, [], [], []
    for passage in paragraphs:
        sid = passage["source_id"]
        if sid not in admitted:
            rejected.append({"source_id": sid, "passage_id": passage["passage_id"], "sha256": passage["text_sha256"],
                "reason": "validation_family" if sid in held_valid else "historical_test_family_now_dev" if sid in old_dev else "unadmitted_family"})
            continue
        text = passage["text"]
        if digest(text.encode()) != passage["text_sha256"]:
            raise ValueError("Paragraph hash mismatch")
        if {passage["text_sha256"], passage["original_sha256"], digest(normalized(text).encode())} & retired:
            rejected.append({"source_id": sid, "passage_id": passage["passage_id"], "sha256": passage["text_sha256"], "reason": "retired_paragraph_development_only"})
            continue
        if SENSITIVE_CONTENT.search(text):
            rejected.append({"source_id": sid, "passage_id": passage["passage_id"], "sha256": passage["text_sha256"], "reason": "sensitive_pattern"})
            continue
        allowed_passages[passage["passage_id"]] = passage
        source = source_by_id[sid]
        record = {"id": passage["passage_id"], "text": text, "sha256": digest(text.encode()),
            "families": [sid], "split": "train", "group_id": sid, "license": source["license"],
            "uses": ["cpt_text", "rag_context"], "evidence_status": "licensed_author_text_science_review_pending",
            "prior_exposure": "historical_prepared_train_not_a_blind_test", "expert_review": "pending",
            "source_id": sid, "passage_id": passage["passage_id"], "locator": {"paragraph": passage["paragraph"], "section": passage["section"]},
            "original_paragraph_sha256": passage["original_sha256"], "source_artifact_sha256": source["snapshot_sha256"],
            "transformation": passage["notation"], "attribution": source["authors"], "url": source["url"]}
        candidates.append(record)
        cpt.append({"text": text})
    historical = exclusions["historical_train"]
    train_path = root / historical["path"]
    checked(train_path, historical["sha256"])
    train_rows = read_jsonl(train_path)
    if len(train_rows) != historical["rows"]:
        raise ValueError("Historical roster changed")
    dialogs, records = [], []
    for row in train_rows:
        sid, pid = row["source_id"], row["passage_id"]
        if sid not in admitted or pid not in allowed_passages:
            rejected.append({"id": row["id"], "source_id": sid, "passage_id": pid, "reason": "historical_sft_passage_not_admitted"})
            continue
        passage = allowed_passages[pid]
        messages = row["messages"]
        validate_messages(messages)
        if passage["text"] not in "\n".join(m["content"] for m in messages if m["role"] == "user"):
            raise ValueError("Historical prompt lacks its exact paragraph")
        if row.get("evidence_quote") is not None and row["evidence_quote"] not in passage["text"]:
            raise ValueError("Historical supporting quote absent")
        payload = {"messages": messages}
        text = encoded(payload).decode()
        if SENSITIVE_CONTENT.search(text):
            raise ValueError("Sensitive historical dialogue")
        objective = row["id"].rsplit("-", 1)[0]
        record = {"id": row["id"], "source_id": sid, "passage_id": pid, "language": row["language"],
            "learning_objective": objective, "families": [sid], "split": "train", "group_id": sid,
            "text": text, "sha256": digest(text.encode()), "uses": ["sft_messages"],
            "excerpt": passage["text"], "excerpt_sha256": passage["text_sha256"],
            "raw_messages": None, "messages": messages,
            "message_expansion": "historical native conversation retained; no fabricated raw/task_routed_v14 expansion",
            "answer_origin": "existing_historical_synthetic_source_grounded_candidate_not_new_gold",
            "expert_review": row["expert_review"], "translation_review": "pending",
            "claim_support_review": "pending", "evidence_quote": row.get("evidence_quote"),
            "prior_exposure": "historical_train_used_for_selected_adapter", "provenance": {
                "historical_file": historical["path"], "historical_file_sha256": historical["sha256"],
                "source_artifact_sha256": source_by_id[sid]["snapshot_sha256"],
                "paragraph_file_sha256": frozen["passages.jsonl"], "paragraph": passage["paragraph"],
                "license_evidence": source_by_id[sid]["license_evidence"]}}
        candidates.append(record)
        records.append(record)
        dialogs.append(payload)
    output.mkdir(parents=True, mode=0o700)
    write_jsonl(output / "source-corpus.jsonl", candidates)
    write_jsonl(output / "train-records.jsonl", records)
    write_jsonl(output / "exclusions.jsonl", rejected)
    write_json(output / "attributions.json", attribution)
    for mode, rows in (("cpt_text", cpt), ("sft_messages", dialogs), ("rag_context", cpt), ("code_text", [])):
        folder = output / mode
        folder.mkdir()
        write_jsonl(folder / "train.jsonl", rows)
        write_jsonl(folder / "train-provenance.jsonl", ({"row": i, "source_id": r["source_id"], "passage_id": r["passage_id"], "sha256": r["sha256"]} for i, r in enumerate([r for r in candidates if mode in r["uses"]])))
        for split in ("valid", "dev"):
            write_jsonl(folder / (split + ".jsonl"), [])
    write_json(output / "readiness.json", {"status": "conditional_train_candidates_not_ready_for_new_training",
        "training_ready": False, "training_run": False, "frozen_experiment_modified": False,
        "prepared_cpt_paragraphs": len(cpt), "historical_sft_candidates": len(dialogs),
        "unique_sft_objectives": len({r["learning_objective"] for r in records}),
        "unique_sft_passages": len({r["passage_id"] for r in records}),
        "source_families": sorted(admitted), "historical_actually_trained_rows": historical["rows"],
        "current_correction_pack_prepared_rows": 20, "correction_pack_imported": False,
        "reason": ["expert_and_translation_review_pending", "new_experiment_registration_required", "exact_token_audit_required"],
        "old_valid_families": sorted(held_valid), "old_test_families_now_dev": sorted(old_dev),
        "retired_excerpt_hashes_count": len(retired), "raw_messages_missing_historically": True})
    write_json(output / "manifest.json", {"pipeline_version": "historical-reconciliation-1",
        "pipeline_sha256": digest(Path(__file__).read_bytes()), "frozen_inputs": frozen,
        "contract_sha256": digest(Path(contract_path).read_bytes()), "exclusions_sha256": digest(Path(exclusions_path).read_bytes()),
        "historical_train_sha256": historical["sha256"], "files": {p.relative_to(output).as_posix(): digest(p.read_bytes()) for p in sorted(output.rglob("*")) if p.is_file()}})
    return audit(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "contract", "exclusions", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.contract, args.exclusions, args.output), sort_keys=True))
