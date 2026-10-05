#!/usr/bin/env python3
"""Dependency-complete Python units from already reviewed original source code."""
import argparse
import ast
import json
from pathlib import Path

from format_tokens import bind_tokenizer
from pipeline import audit, digest, encoded, read_jsonl, write_json, write_jsonl


def bound_names(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return {a.asname or a.name.split(".")[0] for a in node.names}
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return {n.id for target in targets for n in ast.walk(target) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    return set()


def units(text):
    tree = ast.parse(text)
    nodes, lines = tree.body, text.splitlines(keepends=True)
    if any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in nodes):
        raise ValueError("Wildcard imports prevent a proven dependency closure")
    for index, node in enumerate(nodes):
        docstring = index == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        main_guard = isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__" and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq) and len(node.test.comparators) == 1 and isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value == "__main__"
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not docstring and not main_guard:
            raise ValueError("Module initialization effects require manual context review")
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and not bound_names(node):
            raise ValueError("Module attribute mutation requires manual context review")
    bindings = {}
    for i, node in enumerate(nodes):
        for name in bound_names(node):
            if name in bindings:
                raise ValueError("Rebound module names need a manual semantic review")
            bindings[name] = i
    future = {i for i, n in enumerate(nodes) if isinstance(n, ast.ImportFrom) and n.module == "__future__"}
    doc = {0} if nodes and isinstance(nodes[0], ast.Expr) and isinstance(nodes[0].value, ast.Constant) and isinstance(nodes[0].value.value, str) else set()
    for i, target in enumerate(nodes):
        if not isinstance(target, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        selected, pending = set(future | doc), [i]
        while pending:
            index = pending.pop()
            if index in selected:
                continue
            selected.add(index)
            node = nodes[index]
            loaded = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            if loaded & {"eval", "exec", "globals", "locals", "__import__"}:
                raise ValueError("Dynamic namespace access requires manual context review")
            pending.extend(bindings[name] for name in loaded if name in bindings and bindings[name] not in selected)
        spans, parts = [], []
        for index in sorted(selected):
            node = nodes[index]
            start = min([node.lineno, *[d.lineno for d in getattr(node, "decorator_list", [])]])
            previous_end = nodes[index - 1].end_lineno if index else 0
            # Retain leading comments as well as the entire AST node/decorators.
            while start > previous_end + 1 and (not lines[start - 2].strip() or lines[start - 2].lstrip().startswith("#")):
                start -= 1
            section = "".join(lines[start - 1:node.end_lineno])
            spans.append({"start_line": start, "end_line": node.end_lineno,
                          "sha256": digest(section.encode()), "role": "target" if index == i else "dependency_context"})
            parts.append(section.rstrip("\n"))
        body = "\n\n".join(parts) + "\n"
        # No statement/body/constraint is synthesized or shortened.
        compile(body, "<source-unit>", "exec")
        yield {"unit": target.name, "text": body, "source_ranges": spans,
               "context_bindings": sorted({name for index in selected - {i} for name in bound_names(nodes[index])}),
               "execution_scope": "original module/repository context; syntax and dependency closure checked, no portability or physical validation claimed"}


def prepare(corpus, profile_path, tokenizer_path, output):
    corpus, output = Path(corpus), Path(output)
    audit(corpus)
    if output.exists():
        raise ValueError("Output exists")
    profile = json.loads(Path(profile_path).read_text())
    tokenizer = bind_tokenizer(tokenizer_path, profile)
    limit = profile["limits"]["cpt"]
    candidates, rejected = [], []
    for parent in read_jsonl(corpus / "source-corpus.jsonl"):
        if "code_text" not in parent["uses"]:
            continue
        if parent["evidence_status"] != "reviewed_code":
            raise ValueError("Code source is not explicitly reviewed")
        try:
            parsed = list(units(parent["text"]))
        except (ValueError, SyntaxError) as error:
            rejected.append({"source_id": parent["id"], "source_sha256": parent["sha256"], "reason": str(error)})
            continue
        for unit in parsed:
            ids = tokenizer(unit["text"], add_special_tokens=False)["input_ids"]
            if tokenizer.eos_token_id in ids:
                raise ValueError("Embedded EOS in code source")
            length = len(ids) + 1
            record = {**parent, **unit, "id": parent["id"] + "::" + unit["unit"],
                "parent_id": parent["id"], "parent_sha256": parent["sha256"],
                "sha256": digest(unit["text"].encode()), "uses": ["code_text"], "tokens_including_eos": length,
                "transformation": "AST units plus transitive module dependencies, original source ranges in original order; bodies/constraints unchanged",
                "context_repetition": "dependency context can occur in several units; units are not independent source examples"}
            if length > limit:
                rejected.append({k: record[k] for k in ("id", "parent_id", "parent_sha256", "source_ranges", "tokens_including_eos") } | {"reason": "dependency_complete_unit_exceeds_budget_no_truncation", "limit": limit})
            else:
                candidates.append(record)
    output.mkdir(parents=True, mode=0o700)
    write_jsonl(output / "source-corpus.jsonl", candidates)
    write_jsonl(output / "quarantine.jsonl", rejected)
    for mode in ("cpt_text", "code_text", "sft_messages"):
        folder = output / mode
        folder.mkdir()
        for split in ("train", "valid", "dev"):
            rows = [r for r in candidates if mode == "code_text" and r["split"] == split]
            write_jsonl(folder / (split + ".jsonl"), ({"text": r["text"]} for r in rows))
            write_jsonl(folder / (split + "-provenance.jsonl"), ({"row": i, "source_id": r["id"], "parent_id": r["parent_id"], "parent_sha256": r["parent_sha256"], "source_ranges": r["source_ranges"], "families": r["families"], "split": r["split"]} for i, r in enumerate(rows)))
    write_json(output / "readiness.json", {"training_ready": False, "training_run": False,
        "accepted_units": len(candidates), "quarantined_units": len(rejected), "token_limit": limit,
        "maximum_accepted_tokens": max((r["tokens_including_eos"] for r in candidates), default=0),
        "families_and_splits_inherited": True, "scientific_validation": False,
        "reasons": ["source remains in development", "new experiment and code-task review required"]})
    write_json(output / "manifest.json", {"pipeline_sha256": digest(Path(__file__).read_bytes()),
        "parent_manifest_sha256": digest((corpus / "manifest.json").read_bytes()),
        "profile_sha256": digest(Path(profile_path).read_bytes()), "files": {p.relative_to(output).as_posix(): digest(p.read_bytes()) for p in sorted(output.rglob("*")) if p.is_file()}})
    return audit(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("corpus", "profile", "tokenizer", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.corpus, args.profile, args.tokenizer, args.output), sort_keys=True))
