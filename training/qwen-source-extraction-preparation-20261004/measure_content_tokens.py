"""Count pinned local content tokens offline; never import or run a model."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
TOKENIZER_SHA = "06b9509352d2af50381ab2247e083b80d32d5c0aba91c272ca9ff729b6a0e523"


def measure(tokenizer_path):
    start = time.perf_counter()
    if hashlib.sha256(tokenizer_path.read_bytes()).hexdigest() != TOKENIZER_SHA:
        raise ValueError("Unadmitted tokenizer bytes")
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)
    system = (HERE / "system_prompt.txt").read_text(encoding="utf-8")
    lines = (HERE / "corpus/inputs.jsonl").read_text(encoding="utf-8").splitlines()
    gold_lines = (HERE / "gold/expected.jsonl").read_text(encoding="utf-8").splitlines()
    rows = []
    for line, gold_line in zip(lines, gold_lines, strict=True):
        source, gold = json.loads(line), json.loads(gold_line)
        if source["id"] != gold["case_id"]:
            raise ValueError("Input/gold roster mismatch")
        user = json.dumps({"case_id": source["id"], "parser_kind": source["parser_kind"],
                           "excerpt": source["excerpt"]}, ensure_ascii=False,
                          sort_keys=True, separators=(",", ":"))
        candidate = count(gold_line)
        rows.append({"case_id": source["id"], "excerpt_content_tokens": count(source["excerpt"]),
            "prospective_user_content_tokens": count(user), "system_content_tokens": count(system),
            "canonical_gold_content_tokens": candidate,
            "canonical_gold_plus_one_eos_fits_512": candidate + 1 <= 512})
    return {"schema_version": 1, "kind": "offline_local_content_token_audit", "rows": rows,
        "tokenizer_repository": "mlx-community/Qwen3.8-27B-4bit",
        "tokenizer_revision": "10c35caafbb80f7dc6a7a432cdd11af10a6d4818",
        "tokenizer_sha256": TOKENIZER_SHA, "tokenizers_version": importlib.metadata.version("tokenizers"),
        "chat_template_or_special_tokens_measured": False, "model_calls": 0,
        "gold_access_scope": "Owner offline length audit only; never a model input.",
        "cloud_billed_tokens": None, "cloud_tokens_avoided": None,
        "actual_human_correction_seconds": None, "cloud_cost_avoided_eur": None,
        "elapsed_seconds": time.perf_counter() - start,
        "limit": "Content lengths only. Alternative serialization and actual decoding may differ; no cloud billing or future runtime admission is established."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = measure(args.tokenizer)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": "content_only", "rows": len(result["rows"]),
                      "model_calls": 0, "elapsed_seconds": result["elapsed_seconds"]}))
