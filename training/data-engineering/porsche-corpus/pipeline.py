#!/usr/bin/env python3
"""Offline, immutable Git-snapshot corpus preparation. Never trains a model."""
import argparse
import collections
import fnmatch
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

VERSION = "1.0.0"
TEXT = {".md", ".txt", ".py", ".cs", ".cpp", ".c", ".hpp", ".js", ".mjs", ".ts", ".astro", ".scad", ".usda", ".json", ".jsonl", ".csv"}
CODE = {".py", ".cs", ".cpp", ".c", ".hpp", ".js", ".mjs", ".ts", ".scad"}
PRIVATE = re.compile(r"(^|/)(?:\.env(?:\..*)?|\.aws|\.codex|\.agents|\.serena|secrets?|credentials?|openbao|accounts?|users?|messages?|sessions?|raw|scans?)([/.]|$)|(?:token|credential|private.key|customer|accidentee|instagram)", re.I)
RESERVED = re.compile(r"(^|/)(?:tests?|training|evaluation|holdout|gold|benchmark)(/|$)|(?:evaluation|holdout|gold)(?:[._-])", re.I)
SENSITIVE_CONTENT = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})\b|\b[A-HJ-NPR-Z0-9]{17}\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
FAILURE = re.compile(r"rejected|failed|unvalidated|not[_ -]validated|non[_ -]converg|diverg|hypothes|assum|surrogate|concept|screening", re.I)
KNOWN_LICENSES = {"CC-BY-4.0", "CC0-1.0", "MIT", "Apache-2.0", "BSD-3-Clause", "owner-local-preparation"}
FIELDS = {
    "variant": {"generation", "generationId", "variants", "variant", "model", "models", "model_years", "modelYears"},
    "material": {"material", "materials", "alloy", "grade", "material_family", "materialIds", "materialId"},
    "process": {"process", "processes", "processId", "preferred_process", "candidate_processes", "build_process", "manufacturingProcess"},
    "temperature": {"temperature", "temperature_C", "temperatureC", "temperature_K", "temperatureK", "operating_temperature", "service_temperature_c"},
    "units": {"units", "unit", "metersPerUnit"},
    "evidence_level": {"evidence_level", "evidenceLevel"},
    "catalogue_confidence": {"confidence"},
    "qualification": {"claimBasis", "materialBasis", "evidenceBasis", "review_status", "scientific_approval", "fitment_status", "training_authorized", "manufacturing_authorized"},
    "validation_status": {"status", "reviewStatus", "validation_status", "depth", "source_type"},
    "timestamps": {"accessed_on", "accessed", "reviewedOn", "checkedOn", "updatedAt", "date", "timestamp", "retrieved_at"},
    "licenses": {"license", "record_license", "redistribution"},
}
SOURCE_KEYS = {"url", "sourceUrl", "source_url", "evidenceUrl", "petSourceId", "source_id", "sourceId", "source_ids", "sourceIds", "summarySourceIds", "engineSourceIds"}
UNIT_SUFFIXES = {"Nm": "N*m", "FtLb": "ft*lb", "Kg": "kg", "Mm": "mm", "Hp": "hp", "Celsius": "degC", "Degrees": "deg", "Mpa": "MPa"}
PII_KEYS = {"author", "authors", "user", "users", "username", "owner", "email", "contact", "address", "phone", "account", "accounts", "message", "messages", "customer", "vin", "vehicleIdentificationNumber"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def write_jsonl(path, rows):
    with path.open("w") as handle:
        for row in rows:
            handle.write(encoded(row).decode() + "\n")


def safe_url(value):
    try:
        u = urlsplit(value)
        if u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password:
            return None
        if PRIVATE.search(u.path) or re.search(r"/(?:profile|members?|user|messages?|login|admin)(?:/|$)", u.path, re.I):
            return None
        # Query/fragment can carry tracking or credentials. Do not preserve them.
        return urlunsplit((u.scheme.lower(), u.hostname.lower().removeprefix("www."), u.path.rstrip("/"), "", ""))
    except ValueError:
        return None


def family(value):
    low = value.lower()
    generations = sorted(set(re.findall(r"(?<![a-z0-9])(?:993|964|917|935|991|987|986)(?![a-z0-9])", low)))
    generation = generations[0] if len(generations) == 1 else "multiple" if generations else "unspecified"
    # Mirrors and our own transcriptions do not add independent PET evidence.
    # A carpet product slug and digits inside part numbers/opaque IDs are not
    # evidence of a PET source or a Porsche generation.
    if re.search(r"(?<![a-z0-9])pet(?:[-_/]|$)", low) or "original-parts-catalogue" in low:
        return "porsche-pet:" + generation
    if re.search(r"(?<![a-z0-9])katalog(?![a-z0-9])", low) and "porsche" in low:
        return "porsche-pet:" + generation
    if "workshop-manual" in low or "993/manual" in low or "993/technical-data" in low or "993/torques" in low:
        return "porsche-workshop-manual:" + generation
    if "porschefanatics" in low:
        return "project-mirror:porschefanatics"
    url = safe_url(value)
    if url:
        return "publisher:" + urlsplit(url).hostname
    return "source:" + value.lower()


def projection(obj):
    """Whitelist technical metadata; never export prose, contacts or forum users."""
    values = {k: [] for k in FIELDS}
    sources = set()

    def visit(value, depth=0):
        if depth > 16:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in PII_KEYS:
                    continue
                if key in SOURCE_KEYS:
                    for candidate in child if isinstance(child, list) else [child]:
                        if isinstance(candidate, str) and len(candidate) < 1500:
                            url = safe_url(candidate)
                            if url:
                                sources.add(url)
                            elif re.fullmatch(r"[A-Za-z0-9_.:-]+", candidate) and not PRIVATE.search(candidate):
                                sources.add(candidate)
                if isinstance(child, (int, float)) and not isinstance(child, bool):
                    for suffix, unit in UNIT_SUFFIXES.items():
                        if re.search(re.escape(suffix) + r"(?:Max|Min|From|To)?$", key):
                            values["units"].append(key + ":" + unit + " (declared_by_field_name)")
                for field, keys in FIELDS.items():
                    if key in keys:
                        candidates = child if isinstance(child, list) else [child]
                        for c in candidates:
                            if isinstance(c, (str, int, float, bool)) and len(str(c)) < 250 and not SENSITIVE_CONTENT.search(str(c)):
                                values[field].append(c)
                visit(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                visit(child, depth + 1)

    visit(obj)
    result = {k: sorted(set(v), key=str) for k, v in values.items()}
    result["sources"] = sorted(sources)
    result["missing"] = [k for k in FIELDS if not result[k]]
    return result


def objects(data):
    if isinstance(data, list):
        return "root", data
    if isinstance(data, dict):
        for key in ("listings", "entries", "parts", "procedures", "torques", "builds", "files", "sources", "records", "items", "manufacturers", "vendors", "tracks", "articles"):
            if isinstance(data.get(key), list):
                return key, data[key]
    return "record", [data]


def kind(path):
    ext = Path(path).suffix.lower()
    if ext in {".step", ".stp", ".fcstd", ".scad"}:
        return "editable_geometry"
    if ext in {".stl", ".3mf", ".glb", ".obj"}:
        return "derived_mesh"
    if ext in {".usd", ".usda", ".usdc", ".usdz"}:
        return "openusd"
    if ext in {".json", ".jsonl", ".csv", ".xlsx", ".npz"}:
        return "structured"
    if ext in CODE:
        return "code"
    if ext in {".md", ".txt", ".pdf", ".docx", ".html"}:
        return "documentation"
    if ext in {".log", ".dat", ".xy"} or re.search(r"(^|/)log\.", path):
        return "solver_or_runtime_output"
    if ext in {".safetensors", ".bin", ".pt"}:
        return "model_weights"
    return "other_asset"


def topic(path):
    low = path.lower()
    if "training/" in low:
        return "existing_corpus_or_experiment"
    if any(k in low for k in ("picogk", "openusd", "omniverse")):
        return "picogk_or_openusd"
    if any(k in low for k in ("impeller", "cooling-fan", "fan-")):
        return "impeller"
    if any(k in low for k in ("simulation", "cfd", "cht", "solver", "doe", "physics", "thermal")):
        return "simulation_and_experiments"
    if any(k in low for k in ("source", "research", "reference", "literature")):
        return "sources_and_research"
    if any(k in low for k in ("manual", "torque", "technical", "specs")):
        return "workshop_and_specifications"
    if any(k in low for k in ("catalog", "data/parts", "oem", "pet-")):
        return "catalogue"
    if any(k in low for k in ("guide", "docs/", "articles/")):
        return "guides_and_articles"
    return "project_tooling_or_other"


def project(path):
    low = path.lower()
    return next(("vehicle:" + g for g in ("993", "964", "917", "935", "991", "987", "986") if g in low), "project:shared")


class Union:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def normalized(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def shingles(text):
    words = re.findall(r"\w+", normalized(text).lower())
    return {tuple(words[i:i + 5]) for i in range(max(0, len(words) - 4))}


def link_candidates(rows, threshold=0.85):
    """Conservative lexical proximity, not a claim of multilingual semantics."""
    uf, links = Union(), []
    for row in rows:
        nodes = row["families"]
        for n in nodes:
            uf.join(row["id"], n)
    signatures = {}
    grams = {}
    for row in rows:
        sig = digest(normalized(row["text"]).encode())
        if sig in signatures:
            other = signatures[sig]
            uf.join(row["id"], other)
            links.append({"child": row["id"], "parent": other, "relation": "exact_normalized", "similarity": 1.0})
        else:
            signatures[sig] = row["id"]
        current = shingles(row["text"])
        for other, previous in grams.items():
            if not current or not previous:
                continue
            score = len(current & previous) / len(current | previous)
            if threshold <= score < 1:
                uf.join(row["id"], other)
                links.append({"child": row["id"], "parent": other, "relation": "near_lexical", "similarity": round(score, 6)})
        grams[row["id"]] = current
    return uf, links


def parse_tree(root, commit):
    raw = git(root, "ls-tree", "-r", "-z", "--long", commit)
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, name = item.split(b"\t", 1)
        mode, typ, blob, size = meta.decode().split()
        yield name.decode("utf-8", errors="strict"), mode, typ, blob, int(size) if size != "-" else 0


def snapshot(spec):
    root = Path(spec["root"]).resolve()
    commit = git(root, "rev-parse", spec["commit"] + "^{commit}").decode().strip()
    if commit != spec["commit"] or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Use an exact, verified 40-character source commit")
    url = git(root, "remote", "get-url", "origin").decode().strip()
    if url.rstrip("/").removesuffix(".git") != spec["repository_url"].rstrip("/"):
        raise ValueError("Source remote mismatch")
    stamp = git(root, "show", "-s", "--format=%cI", commit).decode().strip()
    count = int(git(root, "rev-list", "--count", commit))
    return root, {"id": spec["id"], "commit": commit, "commit_timestamp": stamp,
                  "repository_url": spec["repository_url"], "visibility": spec["visibility"],
                  "history_commit_count": count, "history_content_ingested": False,
                  "working_tree_content_ingested": False}


def build(config_path, output):
    config_path, output = Path(config_path), Path(output)
    config = json.loads(config_path.read_text())
    if output.exists():
        raise ValueError("Output exists; choose a new directory (no replacement)")
    # Never walk a source directory or a protected sibling; only fixed Git blobs.
    for spec in config["sources"]:
        root = Path(spec["root"]).resolve()
        for protected in config.get("protected_roots", []):
            boundary = Path(protected).resolve()
            if root == boundary or boundary in root.parents:
                raise ValueError("Protected source root")
            target = output.resolve()
            if target == boundary or boundary in target.parents:
                raise ValueError("Protected output root")
    inventory, structured, candidates, sources, coverage = [], [], [], [], {}
    aggregate_metadata = collections.defaultdict(collections.Counter)
    published_equivalence = config.get("public_site_observations", [])
    allowed = {(x["source"], x["path"]): x for x in config.get("reviewed_items", [])}
    for spec in config["sources"]:
        root, source = snapshot(spec)
        sources.append(source)
        counts = collections.defaultdict(collections.Counter)
        for path, mode, typ, blob, size in parse_tree(root, source["commit"]):
            filetype, theme = kind(path), topic(path)
            counts["type_files"][filetype] += 1
            counts["type_bytes"][filetype] += size
            counts["theme_files"][theme] += 1
            counts["theme_bytes"][theme] += size
            counts["root_files"][path.split("/")[0]] += 1
            counts["root_bytes"][path.split("/")[0]] += size
            rule = allowed.get((spec["id"], path))
            reasons = []
            if mode in {"120000", "160000"} or typ != "blob":
                reasons.append("symlink_or_submodule_not_followed")
            if PRIVATE.search(path):
                reasons.append("privacy_or_restricted_location_no_content_read")
            if RESERVED.search(path) and not (rule and rule.get("existing_split_reviewed")):
                reasons.append("reserved_existing_corpus_or_tests_metadata_only")
            if any(path.startswith(prefix) for prefix in config.get("protected_repository_prefixes", [])):
                reasons.append("sealed_repository_prefix_no_content_read")
            if Path(path).suffix.lower() == ".log" or re.search(r"(^|/)log\.", path):
                reasons.append("runtime_logs_not_ingested")
            if size > config.get("max_json_bytes", 60000000):
                reasons.append("above_bounded_content_limit")
            ext = Path(path).suffix.lower()
            relevant_json = ext == ".json" and any(fnmatch.fnmatchcase(path, g) for g in spec.get("metadata_json_globs", []))
            row = {"id": spec["id"] + ":" + path, "source": spec["id"], "path": path,
                   "commit": source["commit"], "git_blob": blob, "bytes": size,
                   "snapshot_timestamp": source["commit_timestamp"], "last_modified_timestamp": None,
                   "type": filetype, "theme": theme, "project_family": project(path),
                   "visibility": spec["visibility"], "site_public_equivalence": "not_established",
                   "sha256": None, "content_read": False, "disposition": "reference_metadata_only",
                   "reasons": reasons, "technical_metadata": None}
            if not reasons and (relevant_json or rule):
                raw = git(root, "cat-file", "blob", blob)
                row.update(sha256=digest(raw), content_read=True)
                if relevant_json:
                    try:
                        data = json.loads(raw)
                        collection, records = objects(data)
                        stats = collections.defaultdict(collections.Counter)
                        # Root metadata (license/source) is inherited without inventing facts.
                        rootmeta = projection({k: v for k, v in data.items() if not isinstance(v, list)}) if isinstance(data, dict) else projection({})
                        all_sources, all_licenses, qualifiers = set(rootmeta["sources"]), set(rootmeta["licenses"]), set()
                        reference_ids = set()
                        for item in records:
                            if not isinstance(item, dict):
                                stats["row_types"][type(item).__name__] += 1
                                continue
                            meta = projection(item)
                            for key in FIELDS:
                                if not meta[key]:
                                    meta[key] = rootmeta[key]
                                for v in meta[key]:
                                    stats[key][str(v)] += 1
                                if not meta[key]:
                                    stats["missing"][key] += 1
                            all_sources.update(meta["sources"])
                            all_licenses.update(meta["licenses"])
                            qualifiers.update(meta["validation_status"])
                            if "oemReference" in item:
                                reference_ids.add(re.sub(r"\s", "", str(item["oemReference"])))
                            for s in meta["sources"]:
                                stats["source_families"][family(s)] += 1
                            for g in meta["variant"]:
                                aggregate_metadata[spec["id"] + ":variant"][str(g)] += 1
                        rec = {"file_id": row["id"], "collection": collection, "records": len(records),
                               "distinct_oem_references": len(reference_ids) if reference_ids else None,
                               "counts": {k: dict(sorted(v.items())) for k, v in stats.items()},
                               "source_origins": sorted(all_sources), "declared_licenses": sorted(all_licenses, key=str),
                               "declared_qualifiers": sorted(qualifiers, key=str), "interpretation": "declared_metadata_not_validated_facts"}
                        structured.append(rec)
                        row["technical_metadata"] = {"root": rootmeta, "records": len(records),
                            "source_families": sorted({family(s) for s in all_sources}),
                            "declared_licenses": sorted(all_licenses, key=str), "declared_qualifiers": sorted(qualifiers, key=str)}
                        row["reasons"].append("third_party_rights_and_record_review_required")
                    except (ValueError, TypeError, RecursionError):
                        row["reasons"].append("json_parse_failed_no_export")
                if rule:
                    if digest(raw) != rule["sha256"]:
                        raise ValueError("Reviewed input hash changed: " + row["id"])
                    if rule["license"] not in KNOWN_LICENSES or not rule.get("rights_evidence"):
                        raise ValueError("Reviewed item lacks an explicit supported rights grant")
                    if rule.get("third_party") and not rule.get("attribution"):
                        raise ValueError("Third-party item lacks attribution")
                    text = raw.decode("utf-8")
                    if SENSITIVE_CONTENT.search(text):
                        row["reasons"].append("sensitive_content_detected_no_text_export")
                    else:
                        modes = rule["uses"]
                        if rule.get("evidence_status") not in {"original_process_policy", "reviewed_code", "source_grounded_reviewed"}:
                            raise ValueError("Unsupported evidence status for text inclusion")
                        families = sorted(set(rule["families"]))
                        if not families:
                            raise ValueError("Every included item needs a source/project family")
                        candidates.append({"id": row["id"], "text": text, "sha256": row["sha256"],
                            "families": families, "uses": modes, "license": rule["license"],
                            "rights_evidence": rule["rights_evidence"], "attribution": rule.get("attribution"),
                            "evidence_status": rule["evidence_status"], "declared_split": rule.get("split", "dev"),
                            "visibility": spec["visibility"], "source_commit": source["commit"]})
                        row["disposition"] = "reviewed_local_candidate"
            inventory.append(row)
            counts["content_read_files"][str(row["content_read"]).lower()] += 1
            counts["disposition_files"][row["disposition"]] += 1
        coverage[spec["id"]] = {k: dict(sorted(v.items())) for k, v in counts.items()}
    uf, lineage = link_candidates(candidates)
    blob_origins = {}
    for row in inventory:
        if row["git_blob"] in blob_origins:
            lineage.append({"child": row["id"], "parent": blob_origins[row["git_blob"]], "relation": "exact_git_blob_metadata_only", "similarity": 1.0})
        else:
            blob_origins[row["git_blob"]] = row["id"]
    groups = collections.defaultdict(list)
    for row in candidates:
        groups[uf.find(row["id"])].append(row)
    holdout_pending = not config.get("reviewer_boundary_metadata_complete", False)
    ledger = []
    for members in groups.values():
        families = sorted({f for row in members for f in row["families"]})
        anchors = {config.get("family_splits", {}).get(f) for f in families} - {None}
        splits = anchors or {row["declared_split"] for row in members}
        # Historical test/valid/seen evaluation never becomes a fresh test.
        splits = {"dev" if s in {"test", "seen_test"} else "valid" if s == "validation" else s for s in splits}
        split = "dev" if holdout_pending else (next(iter(splits)) if len(splits) == 1 else "quarantine")
        if "sealed" in splits or any(f in config.get("sealed_families", []) for f in families):
            split = "quarantine"
        if split not in {"train", "valid", "dev", "quarantine"}:
            raise ValueError("Invalid source-family partition")
        group_id = digest(encoded(families))[:20]
        for row in members:
            row.update(split=split, group_id=group_id)
        ledger.append({"group_id": group_id, "families": families, "members": sorted(r["id"] for r in members),
                       "split": split, "reason": "reviewer_boundaries_pending" if holdout_pending else "family_connected_component"})
    # Preserve all ancestry, export a single exact-normalized representative per use.
    output.mkdir(parents=True, mode=0o700)
    write_jsonl(output / "inventory.jsonl", inventory)
    write_jsonl(output / "structured-audit.jsonl", structured)
    write_jsonl(output / "source-corpus.jsonl", candidates)
    write_jsonl(output / "lineage.jsonl", lineage)
    origin_index = collections.defaultdict(set)
    for record in structured:
        for origin in record["source_origins"]:
            origin_index[family(origin)].add(origin)
    write_json(output / "source-lineage.json", {"policy": "mirrors and declared shared origins are one family, not independent corroboration; missing origin remains unknown", "families": {k: sorted(v) for k, v in sorted(origin_index.items())}})
    write_jsonl(output / "quarantine.jsonl", (r for r in inventory if r["disposition"] != "reviewed_local_candidate" or r["reasons"]))
    write_json(output / "split-ledger.json", sorted(ledger, key=lambda x: x["group_id"]))
    # Reference-only RAG metadata never includes protected source bodies.
    write_jsonl(output / "rag-references.jsonl", ({k: r[k] for k in ("id", "source", "path", "commit", "git_blob", "sha256", "visibility", "technical_metadata", "reasons")} for r in inventory if r["technical_metadata"]))
    counts = {}
    for mode in ("cpt_text", "code_text", "rag_context", "sft_messages"):
        folder = output / mode
        folder.mkdir()
        for split in ("train", "valid", "dev"):
            exported, seen = [], set()
            for row in candidates:
                key = digest(normalized(row["text"]).encode())
                if row["split"] != split or mode not in row["uses"] or key in seen:
                    continue
                seen.add(key)
                if mode == "sft_messages":
                    # Import reviewed source-grounded dialogues only. No automatic gold creation.
                    dialogue = json.loads(row["text"])
                    if not isinstance(dialogue, dict) or set(dialogue) != {"messages"}:
                        raise ValueError("Reviewed dialogue needs exactly messages")
                    validate_messages(dialogue["messages"])
                    payload = dialogue
                else:
                    payload = {"text": row["text"]}
                exported.append({"id": row["id"], "group_id": row["group_id"], "payload": payload})
            write_jsonl(folder / (split + ".jsonl"), (r["payload"] for r in exported))
            write_jsonl(folder / (split + "-provenance.jsonl"), ({"row": i, "source_id": r["id"], "group_id": r["group_id"]} for i, r in enumerate(exported)))
            counts[mode + ":" + split] = len(exported)
    write_json(output / "coverage.json", {"sources": sources, "coverage": coverage,
        "structured_files_inspected": len(structured), "structured_rows_counted": sum(r["records"] for r in structured),
        "included_source_documents": len(candidates), "exports": counts,
        "site_observations": published_equivalence, "production_equivalence": "not_established",
        "semantic_coverage": "exact normalization, reviewed origin aliases, lexical 5-gram proximity on admitted texts only; no embedding model or multilingual semantic audit",
        "scope": "All tracked file metadata at frozen commits; selected technical JSON field projections; explicit reviewed texts only. No ignored/untracked private trees, logs, raw scans or reserved test content."})
    write_json(output / "readiness.json", {"training_ready": False, "preparation_complete": True,
        "reasons": ["no_training_authorized", "exact_model_tokenization_required"] + (["reviewer_family_boundaries_pending"] if holdout_pending else []),
        "unreviewed_content_admitted": False, "gold_answers_generated": False,
        "scientific_surrogate_ready": False, "rejected_cfd_promoted": False,
        "redistribution": "private_local_outputs_only; never publish mixed private/third-party exports",
        "profiles": config.get("model_profiles", {}), "existing_corpus_imports": config.get("existing_corpus_status", "pending lead split review")})
    manifest = {"pipeline_version": VERSION, "pipeline_sha256": digest(Path(__file__).read_bytes()),
        "config_sha256": digest(config_path.read_bytes()), "sources": sources,
        "timestamp": config["observed_at"], "files": {p.relative_to(output).as_posix(): digest(p.read_bytes()) for p in sorted(output.rglob("*")) if p.is_file()}}
    write_json(output / "manifest.json", manifest)
    audit(output)
    return {"inventory_files": len(inventory), "structured_rows": sum(r["records"] for r in structured), "included_documents": len(candidates), "training_ready": False}


def validate_messages(messages):
    if not isinstance(messages, list) or len(messages) < 2 or messages[-1].get("role") != "assistant":
        raise ValueError("Dialogue must end in an assistant answer")
    for m in messages:
        if set(m) != {"role", "content"} or m["role"] not in {"system", "user", "assistant"} or not isinstance(m["content"], str) or not m["content"].strip():
            raise ValueError("Unsupported dialogue schema")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def audit(output):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text())
    actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()} - {"manifest.json"}
    if actual != set(manifest["files"]):
        raise ValueError("Output file set changed")
    for name, expected in manifest["files"].items():
        if digest((output / name).read_bytes()) != expected:
            raise ValueError("Output hash mismatch: " + name)
    rows = read_jsonl(output / "source-corpus.jsonl")
    family_split, seen = {}, {}
    for r in rows:
        if digest(r["text"].encode()) != r["sha256"]:
            raise ValueError("Source text hash mismatch")
        for f in r["families"]:
            if f in family_split and family_split[f] != r["split"]:
                raise ValueError("Family leakage")
            family_split[f] = r["split"]
        sig = digest(normalized(r["text"]).encode())
        if sig in seen and seen[sig] != r["split"]:
            raise ValueError("Duplicate leakage")
        seen[sig] = r["split"]
        if SENSITIVE_CONTENT.search(r["text"]):
            raise ValueError("Sensitive text in candidate export")
    return {"ok": True, "verified_files": len(actual), "source_documents": len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("build")
    prepare.add_argument("--config", required=True)
    prepare.add_argument("--output", required=True)
    verify = sub.add_parser("audit")
    verify.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build(args.config, args.output) if args.command == "build" else audit(args.output)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
