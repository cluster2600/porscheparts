#!/usr/bin/env python3
"""Exact local-only Qwen token audit/export, with no model loading or training."""
import argparse
import importlib.metadata
import json
from pathlib import Path

from pipeline import audit, digest, read_jsonl, validate_messages, write_json, write_jsonl


def bind_tokenizer(path, profile):
    path = Path(path)
    for name, expected in profile["tokenizer_files_sha256"].items():
        if digest((path / name).read_bytes()) != expected:
            raise ValueError("Tokenizer asset hash mismatch: " + name)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
    template = tokenizer.chat_template
    if not isinstance(template, str) or digest(template.encode()) != profile["chat_template_sha256"]:
        raise ValueError("Exact chat template hash mismatch")
    if tokenizer.eos_token_id is None:
        raise ValueError("Tokenizer has no EOS")
    return tokenizer


def assistant_labels(tokenizer, messages, template_kwargs):
    """Offset-proven mask over native ChatML, including assistant EOS only.

    Verify the complete rendered transcript. This rejects alternate role wrappers,
    template-added thinking prefixes and special-token injection instead of guessing.
    Canonical messages and templates stay unchanged.
    """
    validate_messages(messages)
    full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False, **template_kwargs)
    expected = "".join("<|im_start|>" + m["role"] + "\n" + m["content"] + "<|im_end|>\n" for m in messages)
    if full != expected:
        raise ValueError("Unsupported template expansion; require a separately verified mask adapter")
    if any("<|im_start|>" in m["content"] or "<|im_end|>" in m["content"] for m in messages):
        raise ValueError("Role token injection")
    encoded = tokenizer(full, add_special_tokens=False, return_offsets_mapping=True)
    ids, offsets = encoded["input_ids"], encoded["offset_mapping"]
    spans, position = [], 0
    for message in messages:
        header = "<|im_start|>" + message["role"] + "\n"
        start = position + len(header)
        end = start + len(message["content"]) + len("<|im_end|>")
        if message["role"] == "assistant":
            spans.append((start, end))
        position = end + 1
    labels = []
    for token, (start, end) in zip(ids, offsets):
        active = end > start and any(left <= start and end <= right for left, right in spans)
        if any(start < left < end or start < right < end for left, right in spans):
            raise ValueError("Token crosses supervision boundary")
        labels.append(token if active else -100)
    if not any(x != -100 for x in labels):
        raise ValueError("No assistant loss tokens")
    for left, right in spans:
        eos = [i for i, (start, end) in enumerate(offsets) if start == right - len("<|im_end|>") and end == right]
        if len(eos) != 1 or ids[eos[0]] != tokenizer.eos_token_id or labels[eos[0]] == -100:
            raise ValueError("Assistant EOS is not supervised exactly once")
    return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels}


def run(corpus, profile_path, tokenizer_path, output):
    corpus, output = Path(corpus), Path(output)
    audit(corpus)
    if output.exists():
        raise ValueError("Output exists")
    profile = json.loads(Path(profile_path).read_text())
    if not profile.get("model_id") or not profile.get("revision") or not profile.get("chat_template_sha256"):
        raise ValueError("Unbound model profile")
    tokenizer = bind_tokenizer(tokenizer_path, profile)
    kwargs = profile.get("template_kwargs", {})
    # Qwen3 Instruct-2507 is non-thinking; do not add enable_thinking=False.
    if "Instruct-2507" in profile["model_id"] and "enable_thinking" in kwargs:
        raise ValueError("Instruct-2507 does not accept a thinking switch")
    output.mkdir(parents=True, mode=0o700)
    summary = {}
    rejected = []
    for dataset in ("cpt_text", "code_text", "sft_messages"):
        limit = profile["limits"]["sft" if dataset == "sft_messages" else "cpt"]
        for split in ("train", "valid", "dev"):
            path = corpus / dataset / (split + ".jsonl")
            result, provenance = [], []
            lengths, supervised = [], 0
            for i, row in enumerate(read_jsonl(path)):
                if dataset == "sft_messages":
                    tokens = assistant_labels(tokenizer, row["messages"], kwargs)
                else:
                    ids = tokenizer(row["text"], add_special_tokens=False)["input_ids"]
                    if tokenizer.eos_token_id in ids:
                        raise ValueError("CPT already contains EOS; source must be reviewed")
                    ids.append(tokenizer.eos_token_id)
                    tokens = {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": ids.copy()}
                n = len(tokens["input_ids"])
                lengths.append(n)
                if n > limit:
                    rejected.append({"dataset": dataset, "split": split, "row": i, "tokens": n, "limit": limit, "reason": "over_length_no_truncation"})
                    continue
                result.append(tokens)
                provenance.append({"token_row": len(result) - 1, "source_row": i, "dataset": dataset, "split": split})
                supervised += sum(x != -100 for x in tokens["labels"])
            write_jsonl(output / (dataset + "-" + split + ".jsonl"), result)
            write_jsonl(output / (dataset + "-" + split + "-provenance.jsonl"), provenance)
            summary[dataset + ":" + split] = {"source_rows": len(lengths), "accepted": len(result), "maximum_tokens": max(lengths, default=0), "total_source_tokens": sum(lengths), "accepted_loss_tokens": supervised}
    write_jsonl(output / "quarantine.jsonl", rejected)
    write_json(output / "audit.json", {"model_id": profile["model_id"], "revision": profile["revision"],
        "tokenizer_files_sha256": profile["tokenizer_files_sha256"], "chat_template_sha256": profile["chat_template_sha256"],
        "limits": profile["limits"], "template_kwargs": kwargs, "summary": summary,
        "packing": "none", "padding": "none", "truncation": "forbidden", "assistant_loss": "content_and_EOS_only",
        "corpus_manifest_sha256": digest((corpus / "manifest.json").read_bytes()),
        "libraries": {k: importlib.metadata.version(k) for k in ("transformers", "tokenizers", "jinja2")},
        "training_run": False, "training_ready": False})
    write_json(output / "manifest.json", {"profile_sha256": digest(Path(profile_path).read_bytes()),
        "formatter_sha256": digest(Path(__file__).read_bytes()), "files": {p.name: digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()}})
    return {"model_id": profile["model_id"], "quarantined_over_length": len(rejected), "training_run": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("corpus", "profile", "tokenizer", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.corpus, args.profile, args.tokenizer, args.output), sort_keys=True))
