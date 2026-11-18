#!/usr/bin/env python3
"""Sourced comparison basis and interface ledger of the bionic turbo F1 (issue #396).

This tool is read-only with respect to the turbo. It hashes committed files,
derives a documentary corpus from an allowlist of exact source spans, indexes
it with the unchanged free-tools SQLite FTS5 module, and validates the
interface ledger, the quantity conventions and the gate ledger revision. It
never runs OpenFOAM, Docker, SSH, CloudCompare, a mesher, a solver or a turbo
case, and it grants no engineering authority: retrieval is not measurement.

Commands, from the repository root:

    python3 twins/bionic-turbo-f1/basis-20261112/basis.py check
    python3 twins/bionic-turbo-f1/basis-20261112/basis.py corpus
    python3 twins/bionic-turbo-f1/basis-20261112/basis.py index --output <new dir outside Git>
    python3 twins/bionic-turbo-f1/basis-20261112/basis.py retrieval --database <index.sqlite>
    python3 twins/bionic-turbo-f1/basis-20261112/basis.py gate

`check` exits non-zero on any stale hash, moved span, unsourced value or
field promoted to measured status without an admitted measurement. `gate`
prints the verdict of the unchanged `baseline.py` evaluator for G03.
"""
from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import importlib.util
import json
import math
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TWIN = "twins/bionic-turbo-f1"
REVISION = TWIN + "/basis-20261112"
PARENT_LEDGER = TWIN + "/recovery-20261106/gate-ledger.json"
MATRIX = TWIN + "/baseline-20261106-mac/runtime-matrix.json"
KNOWLEDGE = "benchmarks/free-tools/knowledge.py"
GATE = "G03-measured-interfaces-and-basis"
PREREQUISITES = ("G01-baseline-frozen", "G01-execution-contract", "G02-evidence-recoverable")

FILES = {
    "allowlist": "source-allowlist.json",
    "corpus": "turbo-corpus.json",
    "cases": "turbo-retrieval-cases.json",
    "citations": "known-citations.json",
    "interfaces": "interface-ledger.json",
    "conventions": "conventions.json",
    "ledger": "gate-ledger.json",
    "attestation": "G03-attestation.json",
    "evaluation": "G03-evaluation.json",
    "prerequisites": "prerequisites.json",
    "retrieval": "retrieval-receipt.json",
    "host": "host-observations-20261112.json",
}

AUTHORIZATION = "owner_authored_or_approved_export"
SOURCE_KINDS = {
    "twin_generator", "twin_record", "twin_evidence", "twin_gate_ledger",
    "research_register", "catalogue_record",
}
# Deliberately no "measured" status: no admitted turbo measurement exists. Admitting
# one needs a new revision with a measurement record under decision 0019.
EVIDENCE_SCOPE = {
    "study_assumption": "study_assumption_not_measurement",
    "model_derived": "computed_from_concept_geometry_not_measurement",
    "numerical_construct": "numerical_idealisation_not_a_physical_interface",
    "published_other_variant": "published_for_another_variant_not_transferable",
    "published_method": "method_reference_not_turbo_data",
    "documented_unknown": "documented_unknown_no_value",
    "contract_null": "contract_field_null_no_value",
    "comparison_contract": "prescribed_comparison_contract_not_a_result",
    "synthetic_control": "synthetic_adversarial_control",
}
UNKNOWN_STATUSES = {"documented_unknown", "contract_null"}
# Carrier documents are the corpus of another part; they are never turbo evidence.
REQUIRED_EXCLUSIONS = {
    "benchmarks/free-tools/corpus.json",
    "benchmarks/free-tools/retrieval-cases.json",
    "catalog/parts/993-eng-carrier-0001.json",
    "docs/reports/",
    "parts/993-eng-carrier-0001/",
    "twins/993-engine-mount-system-f0/",
    "training/",
}
LEDGER_GROUPS = (
    "reference_identity", "rotor_stator", "nut", "ports", "mrf_interface", "clearances",
    "shaft_speed", "pressure_temperature_boundary_conditions", "reference_geometry",
)
APPLIES_TO = {"reference", "bionic", "physical_turbo"}
STUDY_STATUSES = {"assumed", "model_derived", "numerical_construct"}
GATE_ROUTES = {
    "contributor_request_adr_0019", "documentary_search", "owner_scope_decision",
    "numerical_sensitivity_downstream",
}
REQUIRED_QUANTITIES = {
    "mass_flow", "corrected_mass_flow", "corrected_speed", "total_pressure_ratio",
    "inlet_total_temperature", "outlet_total_temperature", "shaft_torque", "shaft_power",
    "isentropic_efficiency_tt",
}
SELECTOR = re.compile(r"^\[([A-Za-z_]+)=(.+)\]$")


class BasisError(Exception):
    """Raised when a span, an allowlist entry or a convention input is malformed."""


# --------------------------------------------------------------------------
# Files, hashes and the two unchanged modules this revision relies on
# --------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def load(name: str, base: Path = HERE):
    return load_json(base / FILES[name])


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=None)
def parent():
    """The unchanged gate evaluator of the 2026-11-06 baseline."""
    return _module("turbo_basis_parent_baseline", REPO / TWIN / "baseline-20261106/baseline.py")


@functools.lru_cache(maxsize=None)
def measurements():
    """The repository's unchanged measurement-record validator."""
    return _module("turbo_basis_measurements", REPO / "scripts/validate_measurements.py")


@functools.lru_cache(maxsize=None)
def knowledge():
    """The unchanged free-tools FTS5 module; its helper is imported by bare name."""
    tools = REPO / "benchmarks/free-tools"
    prior = sys.path[:]
    sys.path.insert(0, str(tools))
    try:
        return _module("turbo_basis_knowledge", tools / "knowledge.py")
    finally:
        sys.path[:] = prior


def repo_file(repo: Path, relative: str) -> Path:
    if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
        raise BasisError(f"path {relative!r} must be repository-relative")
    target = repo / relative
    if not target.is_file() or target.is_symlink():
        raise BasisError(f"{relative} is not a regular committed file")
    return target


# --------------------------------------------------------------------------
# Exact source spans
# --------------------------------------------------------------------------

def resolve_pointer(document, pointer: str):
    """JSON pointer with one extension: `[key=value]` selects the unique list member."""
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise BasisError(f"pointer {pointer!r} must be empty or start with '/'")
    node = document
    for token in pointer[1:].split("/"):
        selector = SELECTOR.match(token)
        if isinstance(node, list) and selector:
            hits = [item for item in node
                    if isinstance(item, dict) and str(item.get(selector[1])) == selector[2]]
            if len(hits) != 1:
                raise BasisError(f"pointer {pointer!r}: {token} matches {len(hits)} members")
            node = hits[0]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        elif isinstance(node, dict) and token in node:
            node = node[token]
        else:
            raise BasisError(f"pointer {pointer!r}: {token!r} not found")
    return node


def span_node(repo: Path, path: str, span: dict):
    if "pointer" not in span:
        return None
    return resolve_pointer(load_json(repo_file(repo, path)), span["pointer"])


def span_text(repo: Path, path: str, span: dict) -> str:
    """The exact text of a span: verbatim lines, or the canonical JSON of a pointed node."""
    if ("lines" in span) == ("pointer" in span):
        raise BasisError(f"span of {path} needs exactly one of lines or pointer")
    if "pointer" in span:
        return json.dumps(span_node(repo, path, span), ensure_ascii=False, sort_keys=True)
    first, last = span["lines"]
    lines = repo_file(repo, path).read_text(encoding="utf-8").split("\n")
    if not (isinstance(first, int) and isinstance(last, int) and 1 <= first <= last <= len(lines)):
        raise BasisError(f"span {span['lines']} is outside {path}")
    return "\n".join(lines[first - 1:last])


def span_locator(span: dict) -> str:
    if "lines" in span:
        return f"L{span['lines'][0]}-L{span['lines'][1]}"
    return span["pointer"] or "/"


def upstream_rights(repo: Path, source_id: str) -> dict:
    """Licence of a third-party source as its catalogue source record states it."""
    record_path = repo / "catalog/sources" / (source_id.lower() + ".json")
    if not record_path.is_file():
        raise BasisError(f"upstream source {source_id} has no catalogue source record")
    record = load_json(record_path)
    if record.get("source_id") != source_id:
        raise BasisError(f"{record_path.name} does not declare {source_id}")
    rights = record.get("rights") or {}
    if not str(rights.get("license", "")).strip():
        raise BasisError(f"upstream source {source_id} records no licence")
    return {
        "source_id": source_id,
        "license": rights["license"],
        "redistribution": rights.get("redistribution"),
        "evidence_level": (record.get("quality") or {}).get("evidence_level"),
    }


# --------------------------------------------------------------------------
# Allowlist and corpus
# --------------------------------------------------------------------------

def excluded_reason(allowlist: dict, path: str):
    for rule in allowlist.get("excluded", []):
        target = rule.get("path")
        if target and (path == target or (target.endswith("/") and path.startswith(target))):
            return rule.get("reason", "excluded")
    return None


def check_allowlist(allowlist: dict, repo: Path = REPO) -> list[str]:
    errors = []
    if allowlist.get("authorization") != AUTHORIZATION:
        errors.append("allowlist is not an owner-authored or approved export")
    excluded = {rule.get("path") for rule in allowlist.get("excluded", [])}
    missing = REQUIRED_EXCLUSIONS - excluded
    if missing:
        errors.append(f"allowlist no longer excludes carrier documents {sorted(missing)}")
    for rule in allowlist.get("excluded", []):
        if not str(rule.get("reason", "")).strip():
            errors.append(f"exclusion {rule.get('path')} states no reason")
    variants = allowlist.get("variants", {})
    paths, span_ids = set(), set()
    for source in allowlist.get("sources", []):
        path = source.get("path")
        label = f"allowlist source {path}"
        if path in paths:
            errors.append(f"{label}: listed twice")
        paths.add(path)
        reason = excluded_reason(allowlist, str(path))
        if reason:
            errors.append(f"{label}: excluded ({reason})")
            continue
        try:
            actual = sha256_file(repo_file(repo, path))
        except BasisError as error:
            errors.append(f"{label}: {error}")
            continue
        if actual != source.get("sha256"):
            errors.append(f"{label}: stale, pinned {source.get('sha256')}, found {actual}")
        if source.get("kind") not in SOURCE_KINDS:
            errors.append(f"{label}: kind {source.get('kind')!r} is not allowed")
        if not str(source.get("rights", "")).strip():
            errors.append(f"{label}: rights are not stated")
        if source.get("variant") not in variants:
            errors.append(f"{label}: variant {source.get('variant')!r} is not declared")
        if not source.get("spans"):
            errors.append(f"{label}: no span selected")
        for span in source.get("spans", []):
            sid = span.get("id")
            if sid in span_ids:
                errors.append(f"span id {sid} is not unique")
            span_ids.add(sid)
            if span.get("evidence_status") not in EVIDENCE_SCOPE or span.get("evidence_status") == "synthetic_control":
                errors.append(f"span {sid}: evidence status {span.get('evidence_status')!r} is not allowed")
            if span.get("variant", source.get("variant")) not in variants:
                errors.append(f"span {sid}: variant is not declared")
            if not isinstance(span.get("units"), list) or not all(isinstance(u, str) for u in span["units"]):
                errors.append(f"span {sid}: units must be a list of unit strings (possibly empty)")
            if not str(span.get("title", "")).strip():
                errors.append(f"span {sid}: no retrieval title")
            try:
                text = span_text(repo, path, span)
                phrases = span.get("must_contain")
                if not isinstance(phrases, list) or not phrases:
                    errors.append(f"span {sid}: no phrase anchors the span to its text")
                for phrase in phrases or []:
                    if not isinstance(phrase, str) or phrase not in text:
                        errors.append(f"span {sid}: {phrase!r} is not in {path}#{span_locator(span)}")
                for source_id in span_upstream(repo, path, span):
                    upstream_rights(repo, source_id)
            except (BasisError, ValueError) as error:
                errors.append(f"span {sid}: {error}")
    for control in allowlist.get("synthetic_controls", []):
        if control.get("id") in span_ids:
            errors.append(f"control id {control.get('id')} is not unique")
        span_ids.add(control.get("id"))
        if (control.get("evidence_status") != "synthetic_control"
                or not str(control.get("source", "")).startswith("synthetic:")):
            errors.append(f"control {control.get('id')} is not labelled synthetic")
    return errors


def span_upstream(repo: Path, path: str, span: dict) -> list[str]:
    """Third-party source ids a span rests on: declared, or carried by the pointed record."""
    declared = list(span.get("upstream_source_ids", []))
    node = span_node(repo, path, span)
    if isinstance(node, dict):
        declared += [sid for sid in node.get("source_ids", []) if sid not in declared]
    return declared


def build_corpus(allowlist: dict, repo: Path = REPO, allowlist_sha256: str | None = None) -> dict:
    """Derive the documentary snapshot from the allowlist; nothing else enters it."""
    variants = allowlist["variants"]
    rows = []
    for source in allowlist["sources"]:
        path = source["path"]
        if excluded_reason(allowlist, path):
            raise BasisError(f"{path} is excluded from turbo evidence")
        for span in source["spans"]:
            text = span_text(repo, path, span)
            status = span["evidence_status"]
            variant = span.get("variant", source["variant"])
            row = {
                "id": span["id"],
                "title": span["title"],
                "text": text,
                "source": f"{path}#{span_locator(span)}",
                "rights": source["rights"],
                "scope": EVIDENCE_SCOPE[status],
                "evidence_status": status,
                "variant": variant,
                "variant_identity": variants[variant],
                "units": span["units"],
                "source_sha256": source["sha256"],
                "span": {"path": path,
                         **({"lines": span["lines"]} if "lines" in span else {"pointer": span["pointer"]}),
                         "text_sha256": sha256_text(text)},
                "upstream": [upstream_rights(repo, sid) for sid in span_upstream(repo, path, span)],
            }
            if span.get("conflict_group"):
                row["conflict_group"] = span["conflict_group"]
            rows.append(row)
    for control in allowlist.get("synthetic_controls", []):
        row = copy.deepcopy(control)
        row["scope"] = EVIDENCE_SCOPE["synthetic_control"]
        rows.append(row)
    return {
        "authorization": allowlist["authorization"],
        "schema": "bionic-turbo-corpus/v1",
        "generator": REVISION + "/basis.py",
        "allowlist_sha256": allowlist_sha256 or sha256_file(HERE / FILES["allowlist"]),
        "scope": ("Exact spans of allowlisted turbo sources plus labelled synthetic controls. "
                  "Titles are authored retrieval labels; every text is the exact span. "
                  "Documentary context only: no measurement, no engineering authority."),
        "documents": rows,
    }


def check_corpus(corpus: dict, allowlist: dict, repo: Path = REPO,
                 allowlist_sha256: str | None = None) -> list[str]:
    errors = []
    try:
        fresh = build_corpus(allowlist, repo, allowlist_sha256)
    except (BasisError, KeyError, ValueError) as error:
        return [f"corpus cannot be rebuilt from the allowlist: {error}"]
    if fresh != corpus:
        old = {row.get("id"): row for row in corpus.get("documents", [])}
        new = {row["id"]: row for row in fresh["documents"]}
        changed = sorted(name for name in set(old) | set(new) if old.get(name) != new.get(name))
        errors.append("corpus differs from the allowlist spans"
                      + (f": {changed}" if changed else " (header)"))
    allowed = {source["path"] for source in allowlist.get("sources", [])}
    for row in corpus.get("documents", []):
        rid = row.get("id")
        for key in ("id", "title", "text", "source", "rights", "scope"):
            if not (isinstance(row.get(key), str) and row[key].strip()):
                errors.append(f"corpus row {rid}: {key} is missing")
        if len(str(row.get("text", ""))) > 16000:
            errors.append(f"corpus row {rid}: excerpt is not bounded")
        status = row.get("evidence_status")
        if status not in EVIDENCE_SCOPE:
            errors.append(f"corpus row {rid}: evidence status {status!r} is not allowed")
        if status == "synthetic_control":
            if not str(row.get("source", "")).startswith("synthetic:"):
                errors.append(f"corpus row {rid}: control without a synthetic source")
            continue
        path = (row.get("span") or {}).get("path")
        if path not in allowed:
            errors.append(f"corpus row {rid}: {path} is not an allowlisted turbo source")
        elif excluded_reason(allowlist, path):
            errors.append(f"corpus row {rid}: {path} is an excluded document")
        if not isinstance(row.get("units"), list) or not row.get("variant"):
            errors.append(f"corpus row {rid}: units or variant identity missing")
    return errors


# --------------------------------------------------------------------------
# Retrieval: the unchanged frozen evaluation plus known citations
# --------------------------------------------------------------------------

def check_cases(cases: list, citations: dict, corpus: dict) -> list[str]:
    errors = []
    rows = {row["id"]: row for row in corpus.get("documents", [])}
    for case in cases:
        cid, kind, expected = case.get("id"), case.get("kind"), case.get("expected_sources", [])
        for name in expected:
            if name not in rows:
                errors.append(f"case {cid}: expected source {name} is not in the corpus")
        found = [rows[name] for name in expected if name in rows]
        if kind in {"reference", "unknown", "hostile"} and not expected:
            errors.append(f"case {cid}: a {kind} case must name the document it expects")
        if kind == "unknown" and any(row["evidence_status"] not in UNKNOWN_STATUSES for row in found):
            errors.append(f"case {cid}: an unknown must resolve to a documented unknown or a null contract field")
        if kind == "conflict" and (len(found) < 2 or len({row.get("conflict_group") for row in found}) != 1
                                   or not found[0].get("conflict_group")):
            errors.append(f"case {cid}: a conflict needs two sources of one conflict group")
        if kind == "hostile" and any(row["evidence_status"] != "synthetic_control" for row in found):
            errors.append(f"case {cid}: hostile fixtures must be synthetic controls")
    seen = set()
    for citation in citations.get("citations", []):
        cid = citation.get("id")
        if cid in seen:
            errors.append(f"citation {cid} is not unique")
        seen.add(cid)
        row = rows.get(citation.get("expected_id"))
        if row is None:
            errors.append(f"citation {cid}: document {citation.get('expected_id')} is not in the corpus")
        elif citation.get("exact_phrase") not in row["text"]:
            errors.append(f"citation {cid}: the exact phrase is not in the cited span")
    return errors


def check_citation(citation: dict, brief: dict, repo: Path = REPO) -> tuple[int | None, list[str]]:
    ids = [row["id"] for row in brief["sources"]]
    if brief.get("engineering_authorized") is not False or brief.get("unknowns_must_remain_unknown") is not True:
        return None, ["retrieval context claims authority"]
    if citation["expected_id"] not in ids:
        return None, ["expected citation was not retrieved"]
    rank = ids.index(citation["expected_id"]) + 1
    row = brief["sources"][rank - 1]
    failures = []
    span = row.get("span") or {}
    if citation["exact_phrase"] not in row["text"]:
        failures.append("exact phrase is absent from the retrieved span")
    if row["source"] != citation["source"]:
        failures.append(f"span locator {row['source']} differs from the known citation")
    if row["variant"] != citation["variant"]:
        failures.append("variant identity differs from the known citation")
    if row["evidence_status"] != citation["evidence_status"]:
        failures.append("evidence status differs from the known citation")
    if not set(citation["units"]) <= set(row["units"]):
        failures.append("units of the known citation are not carried by the span")
    if not str(row.get("rights", "")).strip():
        failures.append("rights are not carried by the span")
    try:
        if sha256_file(repo_file(repo, span["path"])) != row["source_sha256"]:
            failures.append("cited file changed since the corpus was built")
        elif span_text(repo, span["path"], span) != row["text"]:
            failures.append("span no longer matches the cited file")
    except (BasisError, KeyError) as error:
        failures.append(f"span cannot be read back: {error}")
    return rank, failures


def evaluate_retrieval(database: Path, base: Path = HERE, repo: Path = REPO) -> dict:
    """Run the unchanged 30-case evaluation, then check every known citation span."""
    module = knowledge()
    corpus_path = base / FILES["corpus"]
    cases_path = base / FILES["cases"]
    frozen = module.evaluate(database, corpus_path, cases_path)
    citations = load_json(base / FILES["citations"])
    results = []
    for citation in citations["citations"]:
        rank, failures = check_citation(citation, module.context(database, corpus_path, citation["question"]), repo)
        results.append({"id": citation["id"], "expected_id": citation["expected_id"],
                        "rank": rank, "passed": not failures, "failures": failures})
    # The unchanged evaluation tolerates one missed reference; known citations may not.
    passed = (frozen["status"] == "passed" and all(item["passed"] for item in results)
              and frozen["passed"] == {"reference": 10, "unknown": 10, "conflict": 5, "hostile": 5})
    return {
        "schema": "bionic-turbo-retrieval-receipt/v1",
        "status": "passed" if passed else "failed",
        "frozen_evaluation": frozen,
        "known_citations": {"count": len(results),
                            "passed": sum(item["passed"] for item in results),
                            "first_rank": sum(item["rank"] == 1 for item in results),
                            "results": results},
        "corpus_sha256": sha256_file(corpus_path),
        "cases_sha256": sha256_file(cases_path),
        "citations_sha256": sha256_file(base / FILES["citations"]),
        "knowledge_sha256": sha256_file(repo / KNOWLEDGE),
        "scope": "Documentary retrieval and authority boundary only; retrieval is not measurement.",
    }


def run_retrieval(base: Path = HERE, repo: Path = REPO) -> dict:
    """Build the index in a private temporary directory, evaluate it, and discard it."""
    with tempfile.TemporaryDirectory(prefix="turbo-basis-") as scratch:
        database = knowledge().build(base / FILES["corpus"], Path(scratch) / "index")
        return evaluate_retrieval(database, base, repo)


# --------------------------------------------------------------------------
# Interface and operating-condition ledger
# --------------------------------------------------------------------------

def check_source(source, allowlist: dict, repo: Path, label: str) -> list[str]:
    """Cited spans: allowlisted file, one of its selected spans, pinned hash, literals present.

    A value whose literals sit in two selected spans of a file cites both, as a list."""
    if isinstance(source, list) and source:
        return [error for item in source for error in check_source(item, allowlist, repo, label)]
    if not isinstance(source, dict):
        return [f"{label}: no source"]
    pins = {item["path"]: item["sha256"] for item in allowlist.get("sources", [])}
    path = source.get("path")
    if path not in pins:
        return [f"{label}: {path} is not an allowlisted turbo source"]
    errors = []
    selected = next(item for item in allowlist["sources"] if item["path"] == path).get("spans", [])
    locator = ("lines", source["lines"]) if "lines" in source else ("pointer", source.get("pointer"))
    if not any(locator[0] in span and span[locator[0]] == locator[1] for span in selected):
        errors.append(f"{label}: {path}#{locator[1]} is not one of the allowlisted spans of that file")
    if source.get("sha256") != pins[path]:
        errors.append(f"{label}: hash of {path} differs from the allowlist pin")
    try:
        if sha256_file(repo_file(repo, path)) != source.get("sha256"):
            errors.append(f"{label}: {path} changed since it was cited")
        text = span_text(repo, path, source)
    except BasisError as error:
        return errors + [f"{label}: {error}"]
    literals = source.get("literals")
    if not isinstance(literals, list) or not literals:
        errors.append(f"{label}: no literal ties the value to the span")
    for literal in literals or []:
        if not isinstance(literal, str) or literal not in text:
            errors.append(f"{label}: literal {literal!r} is not in {path}#{span_locator(source)}")
    return errors


def check_measurement(entry: dict, repo: Path) -> list[str]:
    """What a field needs before it may carry a measured value (decision 0019)."""
    label = f"ledger entry {entry.get('id')}"
    measured = entry.get("measured")
    if not isinstance(measured, dict):
        return [f"{label}: a measured value must be a measurement object, never a bare figure"]
    errors = []
    for key in ("value", "unit", "instrument", "method", "datum", "specimen_id", "licence", "repeats", "dimension_id"):
        if measured.get(key) in (None, "", []):
            errors.append(f"{label}: measured without {key}")
    uncertainty = entry.get("uncertainty")
    if not (isinstance(uncertainty, dict) and type(uncertainty.get("value")) in (int, float)
            and math.isfinite(uncertainty["value"]) and uncertainty["value"] > 0 and uncertainty.get("unit")):
        errors.append(f"{label}: measured without a stated numeric uncertainty")
    record = measured.get("record") or {}
    path = record.get("path", "")
    if not str(path).startswith("catalog/measurements/"):
        errors.append(f"{label}: measured without an admitted measurement record")
    else:
        try:
            if sha256_file(repo_file(repo, path)) != record.get("sha256"):
                errors.append(f"{label}: measurement record hash mismatch")
            else:
                errors += check_measurement_record(load_json(repo_file(repo, path)), measured, uncertainty, repo, label)
        except BasisError as error:
            errors.append(f"{label}: {error}")
    if measured.get("independent_review") in (None, "", False):
        errors.append(f"{label}: measured without a review independent of its contributor")
    return errors


def check_measurement_record(record: dict, measured: dict, uncertainty, repo: Path, label: str) -> list[str]:
    """The linked record must be a valid physical measurement whose reading is the ledger's value.

    A documented specification, a record of another specimen or a reading that differs from
    the field is not a measurement of this interface."""
    invalid = measurements().validate_measurement(record)
    if invalid:
        return [f"{label}: measurement record is not valid: {invalid[0]}"]
    errors = []
    if record.get("record_kind", "physical_measurement") != "physical_measurement":
        errors.append(f"{label}: the linked record is a {record.get('record_kind')}, not a physical measurement")
    subject = record.get("subject") or {}
    if measured.get("specimen_id") not in {subject.get("part_id"), subject.get("part_reference")} - {None, ""}:
        errors.append(f"{label}: specimen {measured.get('specimen_id')!r} is not the subject of the linked record")
    reading = next((item for item in record.get("readings", [])
                    if item.get("dimension_id") == measured.get("dimension_id")), None)
    if reading is None:
        return errors + [f"{label}: the linked record has no reading {measured.get('dimension_id')!r}"]
    expected = {"value": reading.get("value"), "unit": reading.get("unit"), "method": reading.get("method"),
                "instrument": reading.get("instrument_id"), "repeats": len(reading.get("samples") or [])}
    for key, value in expected.items():
        if measured.get(key) != value:
            errors.append(f"{label}: measured {key} {measured.get(key)!r} differs from the record's {value!r}")
    if isinstance(uncertainty, dict) and (uncertainty.get("value") != reading.get("uncertainty")
                                          or uncertainty.get("unit") != reading.get("unit")):
        errors.append(f"{label}: uncertainty differs from the record's reading")
    return errors


def ledger_summary(ledger: dict) -> dict:
    entries = ledger.get("entries", [])
    by_group = {group: sum(entry.get("group") == group for entry in entries) for group in LEDGER_GROUPS}
    by_status = {status: sum((entry.get("study_value") or {}).get("status") == status for entry in entries)
                 for status in sorted(STUDY_STATUSES)}
    return {
        "entries": len(entries),
        "measured": sum(entry.get("measured") is not None for entry in entries),
        "with_missing_data_gate": sum(bool(entry.get("missing_data_gate")) for entry in entries),
        "with_study_value": sum(entry.get("study_value") is not None for entry in entries),
        "null_without_study_value": sum(entry.get("study_value") is None and entry.get("measured") is None
                                        for entry in entries),
        "study_values_by_status": by_status,
        "entries_by_group": by_group,
    }


def check_interface_ledger(ledger: dict, allowlist: dict, corpus: dict, gate_ledger: dict | None = None,
                           repo: Path = REPO) -> list[str]:
    errors = []
    gates = {gate.get("id"): gate for gate in ledger.get("missing_data_gates", [])}
    if len(gates) != len(ledger.get("missing_data_gates", [])):
        errors.append("missing-data gate ids are not unique")
    blockers = None
    if gate_ledger is not None:
        g03 = next(gate for gate in gate_ledger["gates"] if gate["id"] == GATE)
        blockers = {blocker["id"] for blocker in g03.get("blockers", [])}
    for gid, gate in gates.items():
        if gate.get("route") not in GATE_ROUTES:
            errors.append(f"missing-data gate {gid}: route {gate.get('route')!r} is not allowed")
        if not gate.get("required_evidence"):
            errors.append(f"missing-data gate {gid}: required evidence is not stated")
        if blockers is not None and gate.get("gate_blocker") is not None and gate["gate_blocker"] not in blockers:
            errors.append(f"missing-data gate {gid}: {gate.get('gate_blocker')} is not a G03 blocker")
    rows = {row["id"]: row for row in corpus.get("documents", [])}
    ids, used = set(), set()
    for entry in ledger.get("entries", []):
        eid = entry.get("id")
        label = f"ledger entry {eid}"
        if eid in ids:
            errors.append(f"{label}: id is not unique")
        ids.add(eid)
        if entry.get("group") not in LEDGER_GROUPS:
            errors.append(f"{label}: group {entry.get('group')!r} is not allowed")
        applies = entry.get("applies_to")
        if not applies or not set(applies) <= APPLIES_TO:
            errors.append(f"{label}: applies_to must name reference, bionic or physical_turbo")
        if not str(entry.get("quantity", "")).strip():
            errors.append(f"{label}: quantity is not named")
        if entry.get("measured") is not None:
            errors += check_measurement(entry, repo)
        else:
            if entry.get("uncertainty") is not None:
                errors.append(f"{label}: an uncertainty is stated without a measurement")
            if entry.get("missing_data_gate") not in gates:
                errors.append(f"{label}: neither measured nor bound to a missing-data gate")
            used.add(entry.get("missing_data_gate"))
        study = entry.get("study_value")
        if study is not None:
            if study.get("status") not in STUDY_STATUSES:
                errors.append(f"{label}: study value status {study.get('status')!r} is not allowed")
            if "value" not in study or "unit" not in study:
                errors.append(f"{label}: study value needs value and unit")
            if not str(study.get("uncertainty_statement", "")).strip():
                errors.append(f"{label}: study value states no uncertainty position")
            errors += check_source(study.get("source"), allowlist, repo, label)
        for context in entry.get("published_context", []):
            row = rows.get(context.get("corpus_id"))
            if row is None:
                errors.append(f"{label}: published context {context.get('corpus_id')} is not in the corpus")
            elif row["evidence_status"] not in {"published_other_variant", "published_method", "documented_unknown"}:
                errors.append(f"{label}: {context.get('corpus_id')} is not a published or unknown record")
            if context.get("transferable") is not False:
                errors.append(f"{label}: a published value for another variant is never transferable")
    for group in LEDGER_GROUPS:
        if not any(entry.get("group") == group for entry in ledger.get("entries", [])):
            errors.append(f"interface ledger does not cover {group}")
    for gid in sorted(set(gates) - used):
        errors.append(f"missing-data gate {gid} is bound to no entry")
    if ledger.get("summary") != ledger_summary(ledger):
        errors.append("interface ledger summary is stale")
    verdict = ledger.get("scope_verdict") or {}
    if ledger_summary(ledger)["measured"] == 0 and verdict.get("justified_scope") != "provisional_synthetic_comparison_only":
        errors.append("with no measured entry the only justified scope is a provisional synthetic comparison")
    return errors


# --------------------------------------------------------------------------
# Quantities and conventions
# --------------------------------------------------------------------------

def _positive(*values):
    for value in values:
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise BasisError("finite positive value required")


def _finite(*values):
    for value in values:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise BasisError("finite value required")


def corrected_mass_flow(mass_flow_kg_s, inlet_total_temperature_k, inlet_total_pressure_pa,
                        reference_temperature_k, reference_pressure_pa):
    """m_corr = m * sqrt(T01 / T_ref) / (p01 / p_ref); the reference is never implicit."""
    _finite(mass_flow_kg_s)
    _positive(inlet_total_temperature_k, inlet_total_pressure_pa, reference_temperature_k, reference_pressure_pa)
    return (mass_flow_kg_s * math.sqrt(inlet_total_temperature_k / reference_temperature_k)
            / (inlet_total_pressure_pa / reference_pressure_pa))


def corrected_speed(speed_rpm, inlet_total_temperature_k, reference_temperature_k):
    """N_corr = N / sqrt(T01 / T_ref)."""
    _finite(speed_rpm)
    _positive(inlet_total_temperature_k, reference_temperature_k)
    return speed_rpm / math.sqrt(inlet_total_temperature_k / reference_temperature_k)


def total_pressure_ratio(outlet_total_pressure_pa, inlet_total_pressure_pa):
    """pi_tt = p02 / p01, absolute total pressures; not the outlet-static/inlet-total ratio."""
    _positive(outlet_total_pressure_pa, inlet_total_pressure_pa)
    return outlet_total_pressure_pa / inlet_total_pressure_pa


def angular_velocity(speed_rpm, rotation_sign=1):
    """omega = sign * 2 pi N / 60, in rad/s about +Z."""
    _finite(speed_rpm)
    if rotation_sign not in (-1, 1):
        raise BasisError("rotation sign is +1 or -1")
    return rotation_sign * speed_rpm * math.pi / 30


def shaft_power(omega_rad_s, shaft_torque_n_m):
    """P = omega * torque, torque being the shaft-on-rotor moment about +Z."""
    _finite(omega_rad_s, shaft_torque_n_m)
    return omega_rad_s * shaft_torque_n_m


def compressor_power_from_fluid_moment(omega_rad_s, fluid_on_rotor_moment_z_n_m):
    """P = -omega * M_z; the sign is kept, so a negative result exposes an inversion."""
    _finite(omega_rad_s, fluid_on_rotor_moment_z_n_m)
    return -omega_rad_s * fluid_on_rotor_moment_z_n_m


def isentropic_efficiency_tt(pressure_ratio_tt, inlet_total_temperature_k, outlet_total_temperature_k, gamma):
    """eta_tt = (pi_tt^((gamma-1)/gamma) - 1) / (T02/T01 - 1), constant-gamma perfect gas."""
    _positive(pressure_ratio_tt, inlet_total_temperature_k, outlet_total_temperature_k, gamma)
    if gamma <= 1 or outlet_total_temperature_k <= inlet_total_temperature_k:
        raise BasisError("efficiency needs gamma > 1 and a total-temperature rise")
    ideal = pressure_ratio_tt ** ((gamma - 1) / gamma) - 1
    return ideal / (outlet_total_temperature_k / inlet_total_temperature_k - 1)


def check_conventions(conventions: dict, allowlist: dict, repo: Path = REPO) -> list[str]:
    errors = []
    quantities = {item.get("id"): item for item in conventions.get("quantities", [])}
    missing = REQUIRED_QUANTITIES - set(quantities)
    if missing:
        errors.append(f"conventions lack {sorted(missing)}")
    for qid, item in quantities.items():
        label = f"convention {qid}"
        for key in ("symbol", "unit", "definition"):
            if not str(item.get(key, "")).strip():
                errors.append(f"{label}: {key} is missing")
        basis = item.get("basis") or {}
        if basis.get("kind") == "repository_source":
            errors += check_source(basis.get("source"), allowlist, repo, label)
        elif basis.get("kind") != "definition_adopted_in_this_revision":
            errors.append(f"{label}: basis is neither a repository source nor an adopted definition")
    reference = conventions.get("reference_conditions") or {}
    errors += check_source(reference.get("source"), allowlist, repo, "reference conditions")
    for key in ("temperature_k", "pressure_pa"):
        if type(reference.get(key)) not in (int, float) or reference[key] <= 0:
            errors.append(f"reference conditions: {key} is missing")
    if reference.get("status") != "convention_not_measurement":
        errors.append("reference conditions must be labelled a convention, not a measurement")
    for constant in conventions.get("model_constants", []):
        errors += check_source(constant.get("source"), allowlist, repo, f"model constant {constant.get('id')}")
        if constant.get("status") != "assumed":
            errors.append(f"model constant {constant.get('id')} must stay labelled assumed")
    return errors


# --------------------------------------------------------------------------
# Prerequisites and the gate ledger revision
# --------------------------------------------------------------------------

def verify_prerequisites(repo: Path = REPO) -> dict:
    """Re-run the unchanged evaluator on the recorded attestations of G01 and G02."""
    base = parent()
    matrix = load_json(repo / MATRIX)
    recovery = load_json(repo / PARENT_LEDGER)
    mac = load_json(repo / TWIN / "baseline-20261106-mac/gate-ledger.json")
    evaluations = {}
    for gate_id in PREREQUISITES[:2]:
        attestation = load_json(repo / TWIN / f"baseline-20261106-mac/{gate_id}-attestation.json")
        accepted, reasons = base.evaluate_gate(gate_id, mac, matrix, attestation, repo)
        evaluations[gate_id] = {"may_open": accepted, "reasons": reasons}
    # A passed gate refuses a new attestation, so G02 is re-evaluated in the state it had
    # before acceptance, exactly as tests/test_bionic_turbo_recovery.py does.
    before = copy.deepcopy(recovery)
    next(gate for gate in before["gates"] if gate["id"] == PREREQUISITES[2])["state"] = "investigated"
    attestation = load_json(repo / TWIN / "recovery-20261106/G02-attestation.json")
    accepted, reasons = base.evaluate_gate(PREREQUISITES[2], before, matrix, attestation, repo)
    evaluations[PREREQUISITES[2]] = {"may_open": accepted, "reasons": reasons}
    states = {gate["id"]: gate["state"] for gate in recovery["gates"]}
    return {
        "parent_ledger": PARENT_LEDGER,
        "parent_ledger_sha256": sha256_file(repo / PARENT_LEDGER),
        "parent_ledger_errors": base.check_ledger(recovery, matrix, repo),
        "gate_states": {gate_id: states[gate_id] for gate_id in PREREQUISITES},
        "evaluations": evaluations,
    }


def check_prerequisites(recorded: dict, repo: Path = REPO) -> list[str]:
    fresh = verify_prerequisites(repo)
    errors = [f"prerequisites: recorded {key} differs from the current evaluation"
              for key in fresh if recorded.get(key) != fresh[key]]
    if fresh["parent_ledger_errors"]:
        errors.append("prerequisites: the parent ledger no longer validates")
    for gate_id in PREREQUISITES:
        if fresh["gate_states"][gate_id] != "engineering_passed" or not fresh["evaluations"][gate_id]["may_open"]:
            errors.append(f"prerequisite {gate_id} is not engineering_passed by the unchanged evaluator")
    if recorded.get("downstream_geometry_solver_and_release_authorized") is not False:
        errors.append("prerequisites: downstream execution must stay unauthorised")
    return errors


def check_gate_ledger(ledger: dict, repo: Path = REPO) -> list[str]:
    """Only G03 changes, it carries blockers, and the unchanged validator accepts the ledger."""
    base = parent()
    matrix = load_json(repo / MATRIX)
    previous = load_json(repo / PARENT_LEDGER)
    errors = base.check_ledger(ledger, matrix, repo)
    if ledger.get("parent_ledger_sha256") != sha256_file(repo / PARENT_LEDGER):
        errors.append("gate ledger does not pin its parent ledger")
    for key in ("schema", "roadmap", "states", "opening_rule", "release_separation", "paired_comparison_contract"):
        if ledger.get(key) != previous.get(key):
            errors.append(f"gate ledger changed {key}; the opening rule and the contract are inherited")
    if [gate["id"] for gate in ledger.get("gates", [])] != [gate["id"] for gate in previous["gates"]]:
        errors.append("gate ledger changed the gate list")
        return errors
    for old, new in zip(previous["gates"], ledger["gates"]):
        if old["id"] != GATE and old != new:
            errors.append(f"gate {old['id']} changed; this revision only records G03")
    gate = next(gate for gate in ledger["gates"] if gate["id"] == GATE)
    old = next(gate for gate in previous["gates"] if gate["id"] == GATE)
    if gate.get("state") not in {"investigated", "blocked"}:
        errors.append(f"G03 state {gate.get('state')!r}: an investigation records blockers, it cannot pass the gate")
    if {b["id"] for b in old.get("blockers", [])} - {b["id"] for b in gate.get("blockers", [])}:
        errors.append("G03 dropped an inherited blocker without measured evidence")
    for key in ("kind", "prerequisites", "issue", "title", "required_bindings"):
        if gate.get(key) != old.get(key):
            errors.append(f"G03 changed {key}")
    return errors


def evaluate_gate(base: Path = HERE, repo: Path = REPO) -> dict:
    """The verdict of the unchanged evaluator on the G03 attestation of this revision."""
    ledger = load("ledger", base)
    accepted, reasons = parent().evaluate_gate(
        GATE, ledger, load_json(repo / MATRIX), load("attestation", base), repo)
    return {"gate": GATE, "may_open": accepted, "reasons": reasons,
            "ledger_sha256": sha256_file(base / FILES["ledger"]),
            "attestation_sha256": sha256_file(base / FILES["attestation"]),
            "evaluator": TWIN + "/baseline-20261106/baseline.py",
            "evaluator_sha256": sha256_file(repo / TWIN / "baseline-20261106/baseline.py")}


def check_all(base: Path = HERE, repo: Path = REPO, retrieval: bool = True) -> list[str]:
    allowlist, corpus = load("allowlist", base), load("corpus", base)
    ledger = load("ledger", base)
    errors = check_allowlist(allowlist, repo)
    errors += check_corpus(corpus, allowlist, repo, sha256_file(base / FILES["allowlist"]))
    errors += check_cases(load("cases", base), load("citations", base), corpus)
    errors += check_interface_ledger(load("interfaces", base), allowlist, corpus, ledger, repo)
    errors += check_conventions(load("conventions", base), allowlist, repo)
    errors += check_prerequisites(load("prerequisites", base), repo)
    errors += check_gate_ledger(ledger, repo)
    if not load("host", base).get("skipped_steps"):
        errors.append("host observations do not state which optional steps were skipped")
    if evaluate_gate(base, repo) != load("evaluation", base):
        errors.append("recorded G03 evaluation differs from the unchanged evaluator's verdict")
    if retrieval:
        fresh = run_retrieval(base, repo)
        recorded = load("retrieval", base)
        if fresh["status"] != "passed":
            errors.append("FTS5 retrieval of the known citations failed")
        for key in ("status", "frozen_evaluation", "corpus_sha256", "cases_sha256",
                    "citations_sha256", "knowledge_sha256"):
            if fresh[key] != recorded.get(key):
                errors.append(f"retrieval receipt is stale: {key}")
        # Ranks inside the five excerpts are an observation of one SQLite build, not a criterion.
        for key in ("count", "passed"):
            if fresh["known_citations"][key] != (recorded.get("known_citations") or {}).get(key):
                errors.append(f"retrieval receipt is stale: known_citations.{key}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("check", help="verify the committed basis (default)")
    corpus = sub.add_parser("corpus", help="rebuild the corpus from the allowlist")
    corpus.add_argument("--write", action="store_true")
    index = sub.add_parser("index", help="build the FTS5 index in a new directory outside Git")
    index.add_argument("--output", type=Path, required=True)
    retrieval = sub.add_parser("retrieval", help="evaluate retrieval against the known citations")
    retrieval.add_argument("--database", type=Path)
    sub.add_parser("gate", help="print the unchanged evaluator's verdict for G03")
    args = parser.parse_args(argv)
    command = args.command or "check"
    if command == "check":
        errors = check_all()
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print("bionic turbo basis 2026-11-12: " + ("FAILED" if errors else "OK"))
        return 1 if errors else 0
    if command == "corpus":
        text = dump_json(build_corpus(load("allowlist")))
        if args.write:
            (HERE / FILES["corpus"]).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    if command == "index":
        if REPO in args.output.resolve().parents:
            parser.error("the index is a rebuildable private output; choose a directory outside Git")
        print(knowledge().build(HERE / FILES["corpus"], args.output))
        return 0
    if command == "retrieval":
        result = evaluate_retrieval(args.database) if args.database else run_retrieval()
        sys.stdout.write(dump_json(result))
        return 0 if result["status"] == "passed" else 1
    verdict = evaluate_gate()
    for reason in verdict["reasons"]:
        print(f"REFUSED {reason}")
    print(f"gate {GATE}: " + ("may open" if verdict["may_open"] else "stays closed"))
    return 0 if verdict["may_open"] else 1


if __name__ == "__main__":
    sys.exit(main())
