#!/usr/bin/env python3
"""Freeze and check the bionic turbo F1 baseline of 2026-11-06 (issue #394).

This tool is read-only with respect to the turbo: it hashes committed files,
compares JSON records and evaluates whether an execution attestation may open a
gate. It never runs OpenFOAM, Docker, SSH, a mesher, a solver or a turbo case.

Commands, from the repository root:

    python3 twins/bionic-turbo-f1/baseline-20261106/baseline.py check
    python3 twins/bionic-turbo-f1/baseline-20261106/baseline.py check --history
    python3 twins/bionic-turbo-f1/baseline-20261106/baseline.py inventory \
        --releases <github-releases.json> --write
    python3 twins/bionic-turbo-f1/baseline-20261106/baseline.py evaluate \
        --gate G04-native-fp-execution --attestation <attestation.json>

`check` exits non-zero on any stale or mismatched hash. `evaluate` exits 0 only
when the attestation may open the gate; otherwise it prints every reason.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TWIN = "twins/bionic-turbo-f1"
EVIDENCE = TWIN + "/evidence"
BASELINE = TWIN + "/baseline-20261106"

FILES = {
    "manifest": "baseline-manifest.json",
    "matrix": "runtime-matrix.json",
    "ledger": "gate-ledger.json",
    "inventory": "evidence-inventory.json",
    "host": "host-observations-20261106.json",
}

SHA = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
DIGEST_REF = re.compile(r"^[a-z0-9][a-z0-9./:_-]*@sha256:[0-9a-f]{64}$")
UNKNOWN = "unknown"

GATE_STATES = {"not_started", "blocked", "unknown", "failed", "investigated", "engineering_passed"}
GATE_KINDS = {"documentary", "software", "geometry", "numerical", "physical_correlation", "manufacturing_release"}
REVIEW_KINDS = {"physical_correlation", "manufacturing_release"}

REQUIRED_PROHIBITIONS = {
    "never-execute-pr229-blockmeshdict",
    "never-touch-case-084",
    "do-not-replay-pr238-256-traversals",
    "keep-recurring-automation-paused",
    "no-paid-compute",
    "no-deletion",
    "preserve-153-boxes-and-two-undecided-determinants",
    "retain-writeprecision-16",
    "preserve-bionic-native-source-20261012",
    "no-silent-openfoam-substitution",
    "representations-not-interchangeable",
}

RUNTIME_FIELDS = {
    "id", "tool", "variant", "version", "source_commit", "platform", "identity",
    "executables", "availability", "io_contract", "turbo_role", "qualification",
}


class BaselineError(Exception):
    """Raised when the committed baseline is stale or malformed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_baseline(base: Path = HERE) -> dict:
    return {key: load_json(base / name) for key, name in FILES.items()}


def dump_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


# --------------------------------------------------------------------------
# Receipts and claims
# --------------------------------------------------------------------------

def verify_receipt(receipt, repo: Path = REPO) -> list[str]:
    """A receipt is a committed file with a pinned SHA-256, or a remote URL with a digest."""
    if not isinstance(receipt, dict):
        return [f"receipt is not an object: {receipt!r}"]
    digest = receipt.get("sha256")
    if not isinstance(digest, str) or not SHA.match(digest):
        return [f"receipt {receipt.get('path') or receipt.get('url')!r} lacks a lowercase SHA-256"]
    if "path" in receipt:
        rel = receipt["path"]
        if not isinstance(rel, str) or rel.startswith("/") or ".." in Path(rel).parts:
            return [f"receipt path {rel!r} must be repository-relative"]
        target = repo / rel
        if not target.is_file():
            return [f"receipt {rel} is missing"]
        actual = sha256_file(target)
        if actual != digest:
            return [f"receipt {rel} is stale: pinned {digest}, found {actual}"]
        return []
    if "url" in receipt:
        if not str(receipt["url"]).startswith("https://"):
            return [f"remote receipt {receipt['url']!r} must use https"]
        return []
    return ["receipt has neither path nor url"]


def iter_claims(node, where="$"):
    if isinstance(node, dict):
        if "claim" in node:
            yield where, node
        for key, value in node.items():
            yield from iter_claims(value, f"{where}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_claims(value, f"{where}[{index}]")


def check_claims(document, label: str, repo: Path = REPO) -> list[str]:
    """Every claim links to at least one verified receipt or is explicitly unknown."""
    errors = []
    for where, claim in iter_claims(document):
        receipts = claim.get("receipts") or []
        unknown = claim.get("unknown")
        if receipts and unknown:
            errors.append(f"{label}{where}: a claim cannot be both receipted and unknown")
        if not receipts:
            if not (isinstance(unknown, dict) and str(unknown.get("reason", "")).strip()):
                errors.append(f"{label}{where}: claim has no receipt and is not explicitly unknown")
            continue
        for receipt in receipts:
            errors += [f"{label}{where}: {e}" for e in verify_receipt(receipt, repo)]
    return errors


def check_context_links(document, label: str, repo: Path = REPO) -> list[str]:
    errors = []
    def walk(node, where):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "context" and isinstance(value, list):
                    for rel in value:
                        if not (repo / rel).exists():
                            errors.append(f"{label}{where}.context: {rel} is missing")
                else:
                    walk(value, f"{where}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{where}[{index}]")
    walk(document, "$")
    return errors


# --------------------------------------------------------------------------
# Evidence inventory
# --------------------------------------------------------------------------

def tracked_files(repo: Path, prefix: str) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "--", prefix],
                             check=True, capture_output=True).stdout
        files = sorted(p for p in out.decode("utf-8").split("\0") if p)
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    root = repo / prefix
    return sorted(str(p.relative_to(repo)) for p in root.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")


def release_index(releases) -> dict:
    """Map an asset digest to the release tag that carries it."""
    index = {}
    for release in releases:
        for asset in release.get("assets", []):
            digest = asset.get("digest")
            if digest:
                index.setdefault(digest, []).append(release["tag_name"])
    return index


def load_releases(path: Path) -> list:
    text = Path(path).read_text(encoding="utf-8")
    # `gh api --paginate` concatenates one JSON array per page.
    pages = json.loads("[" + re.sub(r"\]\s*\[", "],[", text.strip()) + "]")
    return [release for page in pages for release in page]


def build_inventory(repo: Path = REPO, releases=None, previous=None, merges=None) -> dict:
    evidence = repo / EVIDENCE
    files = tracked_files(repo, EVIDENCE)
    lines = [f"{sha256_file(repo / rel)}  {rel}" for rel in files]
    aggregate = hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()
    index = release_index(releases) if releases is not None else None
    old = {p["package"]: p for p in (previous or {}).get("packages", [])}
    packages, without = [], []
    for directory in sorted(p for p in evidence.iterdir() if p.is_dir()):
        receipt_path = directory / "archive-receipt.json"
        if not receipt_path.is_file():
            without.append(directory.name)
            continue
        receipt = load_json(receipt_path)
        manifest_path = directory / "file-manifest.json"
        entry = {
            "package": directory.name,
            "archive_receipt_sha256": sha256_file(receipt_path),
            "file_manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
            "archive_sha256": receipt["archive_sha256"],
            "manifest_sha256": receipt["manifest_sha256"],
            "files": receipt.get("files"),
            "performance_ranking_authorized": receipt.get("performance_ranking_authorized"),
            "performance_accepted": sorted({bool(s.get("performance_accepted"))
                                            for s in receipt.get("scopes", [])}) or None,
        }
        if index is not None:
            tags = sorted(set(index.get("sha256:" + receipt["manifest_sha256"], [])))
            entry["release_tags"] = tags
            entry["remote_manifest_digest_match"] = bool(tags)
            entry["remote_archive_single_asset_match"] = bool(index.get("sha256:" + receipt["archive_sha256"]))
        elif directory.name in old:
            for key in ("release_tags", "remote_manifest_digest_match", "remote_archive_single_asset_match"):
                if key in old[directory.name]:
                    entry[key] = old[directory.name][key]
        packages.append(entry)
    inventory = {
        "schema": "bionic-turbo-evidence-inventory/v1",
        "generator": BASELINE + "/baseline.py",
        "evidence_root": EVIDENCE,
        "evidence_tree": {"tracked_files": len(files), "aggregate_sha256": aggregate,
                          "aggregate_rule": "sha256 of '<sha256>  <path>' lines, sorted by path, newline-terminated"},
        "packages_with_archive_receipt": len(packages),
        "directories_without_archive_receipt": without,
        "packages": packages,
    }
    if merges is not None:
        inventory["merge_packages"] = merges
    elif previous and "merge_packages" in previous:
        inventory["merge_packages"] = previous["merge_packages"]
    if index is not None:
        inventory["remote_check"] = {
            "source": "GitHub REST API repos/cluster2600/porscheparts/releases (read-only)",
            "releases_listed": len(releases),
            "manifest_digest_matches": sum(p["remote_manifest_digest_match"] for p in packages),
            "single_asset_archive_digest_matches": sum(p["remote_archive_single_asset_match"] for p in packages),
            "scope": "Committed file-manifest digests compared with live release asset digests; no archive was downloaded or restored.",
        }
    elif previous and "remote_check" in previous:
        inventory["remote_check"] = previous["remote_check"]
    return inventory


def merge_packages(repo: Path, merges: dict) -> dict:
    """Evidence packages whose README.md each merge commit added (needs full history)."""
    result = {}
    for pr, commit in sorted(merges.items(), key=lambda item: int(item[0])):
        out = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", "--diff-filter=A",
                              f"{commit}^1", commit, "--", EVIDENCE],
                             check=True, capture_output=True, text=True).stdout.split()
        names = sorted({Path(p).parent.name for p in out
                        if p.endswith("/README.md") and Path(p).parent.parent.name == "evidence"})
        result[pr] = {"merge_commit": commit, "packages_added": names}
    return result


def check_inventory(inventory: dict, repo: Path = REPO) -> list[str]:
    fresh = build_inventory(repo, previous=inventory)
    errors = []
    if fresh["evidence_tree"] != inventory.get("evidence_tree"):
        errors.append("evidence inventory is stale: the tracked evidence tree changed "
                      f"(now {fresh['evidence_tree']['tracked_files']} files, aggregate "
                      f"{fresh['evidence_tree']['aggregate_sha256']}); evidence/** is immutable")
    if fresh["packages"] != inventory.get("packages"):
        old = {p["package"]: p for p in inventory.get("packages", [])}
        new = {p["package"]: p for p in fresh["packages"]}
        for name in sorted(set(old) | set(new)):
            if old.get(name) != new.get(name):
                errors.append(f"evidence inventory is stale for package {name}")
    if fresh["directories_without_archive_receipt"] != inventory.get("directories_without_archive_receipt"):
        errors.append("evidence directories without archive receipt changed")
    for package in inventory.get("packages", []):
        if package.get("remote_manifest_digest_match") is not True:
            errors.append(f"package {package['package']} has no recorded release digest match")
    return errors


# --------------------------------------------------------------------------
# Runtime matrix
# --------------------------------------------------------------------------

def field(row: dict, dotted: str):
    node = row
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def identity_is_pinned(value) -> bool:
    return isinstance(value, str) and bool(SHA.match(value) or DIGEST_REF.match(value) or COMMIT.match(value))


def python_constant(path: Path, name: str):
    match = re.search(rf"^{name}\s*=\s*\"([^\"]+)\"", path.read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else None


def check_matrix(matrix: dict, repo: Path = REPO) -> list[str]:
    errors = []
    rows = matrix.get("rows", [])
    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("runtime matrix ids are not unique")
    by_id = {row.get("id"): row for row in rows}
    for row in rows:
        missing = RUNTIME_FIELDS - set(row)
        if missing:
            errors.append(f"runtime row {row.get('id')}: missing fields {sorted(missing)}")
        for key, value in (row.get("identity") or {}).items():
            if value != UNKNOWN and not identity_is_pinned(value):
                errors.append(f"runtime row {row.get('id')}: identity {key} is neither pinned nor unknown")
        for key, value in (row.get("executables") or {}).items():
            if value != UNKNOWN and not SHA.match(str(value)):
                errors.append(f"runtime row {row.get('id')}: executable {key} is neither a SHA-256 nor unknown")
        for host, state in (row.get("availability") or {}).items():
            if not isinstance(state, dict) or "claim" not in state:
                errors.append(f"runtime row {row.get('id')}: availability on {host} is not a claim")
    historical = by_id.get(matrix.get("turbo_historical_runtime"))
    if not historical:
        errors.append("runtime matrix does not name the historical turbo runtime")
    else:
        image = python_constant(repo / TWIN / "cfd/prepare_case.py", "IMAGE")
        if image != field(historical, "identity.image"):
            errors.append(f"cfd/prepare_case.py IMAGE {image!r} differs from the pinned historical runtime")
        if historical.get("variant") != "OpenCFD" or "v2406" not in historical.get("version", ""):
            errors.append("historical turbo runtime must be OpenCFD v2406")
        runner = (repo / TWIN / "cfd/run_case.py").read_text(encoding="utf-8")
        if f'"--platform","{historical.get("platform")}"' not in runner:
            errors.append("cfd/run_case.py platform differs from the pinned historical runtime")
    for row in rows:
        if row.get("variant") == "OpenFOAM Foundation" and not str(row.get("qualification", "")).startswith("prohibited_for_turbo"):
            errors.append(f"runtime row {row.get('id')}: Foundation OpenFOAM must be prohibited for turbo substitution")
    errors += check_claims(matrix, "runtime-matrix", repo)
    errors += check_context_links(matrix, "runtime-matrix", repo)
    return errors


# --------------------------------------------------------------------------
# Gate ledger and gate evaluation
# --------------------------------------------------------------------------

def check_ledger(ledger: dict, matrix: dict, repo: Path = REPO) -> list[str]:
    errors = []
    gates = ledger.get("gates", [])
    by_id = {gate.get("id"): gate for gate in gates}
    if len(by_id) != len(gates):
        errors.append("gate ids are not unique")
    rows = {row["id"]: row for row in matrix.get("rows", [])}
    kinds = {gate.get("kind") for gate in gates}
    for required in ("numerical", "physical_correlation", "manufacturing_release"):
        if required not in kinds:
            errors.append(f"gate ledger lacks a separate {required} gate")
    for gate in gates:
        gid = gate.get("id")
        if gate.get("state") not in GATE_STATES:
            errors.append(f"gate {gid}: state {gate.get('state')!r} is not allowed")
        if gate.get("kind") not in GATE_KINDS:
            errors.append(f"gate {gid}: kind {gate.get('kind')!r} is not allowed")
        for prerequisite in gate.get("prerequisites", []):
            if prerequisite not in by_id:
                errors.append(f"gate {gid}: unknown prerequisite {prerequisite}")
        for binding in gate.get("required_bindings", []):
            row = rows.get(binding.get("runtime"))
            if row is None:
                errors.append(f"gate {gid}: binding to unknown runtime {binding.get('runtime')}")
            elif field(row, binding.get("field", "")) is None:
                errors.append(f"gate {gid}: runtime {row['id']} has no field {binding.get('field')}")
        for pin in gate.get("config_pins", []):
            errors += [f"gate {gid}: config pin {e}" for e in verify_receipt(pin, repo)]
        if gate.get("state") == "engineering_passed":
            if gate.get("blockers"):
                errors.append(f"gate {gid}: engineering_passed with open blockers")
            if not gate.get("receipts"):
                errors.append(f"gate {gid}: engineering_passed without receipts")
            if gate.get("kind") in REVIEW_KINDS and not gate.get("review"):
                errors.append(f"gate {gid}: engineering_passed without professional review receipt")
            for prerequisite in gate.get("prerequisites", []):
                if by_id.get(prerequisite, {}).get("state") != "engineering_passed":
                    errors.append(f"gate {gid}: engineering_passed before prerequisite {prerequisite}")
        if gate.get("state") in {"blocked", "failed", "investigated"} and not gate.get("blockers"):
            errors.append(f"gate {gid}: state {gate.get('state')} must name its blockers")
    errors += check_claims(ledger, "gate-ledger", repo)
    errors += check_context_links(ledger, "gate-ledger", repo)
    return errors


def evaluate_gate(gate_id: str, ledger: dict, matrix: dict, attestation: dict, repo: Path = REPO):
    """Return (may_open, reasons). Any stale, missing or mismatched identity refuses."""
    reasons = []
    gates = {gate["id"]: gate for gate in ledger.get("gates", [])}
    rows = {row["id"]: row for row in matrix.get("rows", [])}
    gate = gates.get(gate_id)
    if gate is None:
        return False, [f"unknown gate {gate_id}"]
    if attestation.get("gate") != gate_id:
        reasons.append(f"attestation names gate {attestation.get('gate')!r}, not {gate_id}")
    if gate.get("state") == "failed":
        reasons.append("a failed gate stays failed; record a new gate revision instead")
    if gate.get("state") == "engineering_passed":
        reasons.append("gate is already engineering_passed; a new attestation cannot reopen it")
    for blocker in gate.get("blockers", []):
        reasons.append(f"open blocker: {blocker.get('id', blocker) if isinstance(blocker, dict) else blocker}")
    for prerequisite in gate.get("prerequisites", []):
        state = gates.get(prerequisite, {}).get("state")
        if state != "engineering_passed":
            reasons.append(f"prerequisite {prerequisite} is {state}, not engineering_passed")
    observed_rows = attestation.get("runtime") or {}
    bound_rows = sorted({b["runtime"] for b in gate.get("required_bindings", [])})
    for row_id in bound_rows:
        row = rows.get(row_id)
        observed = observed_rows.get(row_id)
        if row is None:
            reasons.append(f"runtime {row_id} is not in the matrix")
            continue
        if str(row.get("qualification", "")).startswith("prohibited"):
            reasons.append(f"runtime {row_id} is prohibited for turbo use")
        if not isinstance(observed, dict):
            reasons.append(f"runtime {row_id} is not attested")
            continue
        for key in ("variant", "version", "platform"):
            if observed.get(key) != row.get(key):
                reasons.append(f"runtime {row_id} {key} substituted: pinned {row.get(key)!r}, attested {observed.get(key)!r}")
    for binding in gate.get("required_bindings", []):
        row = rows.get(binding["runtime"])
        if row is None:
            continue
        name = f"{binding['runtime']}.{binding['field']}"
        pinned = field(row, binding["field"])
        if not identity_is_pinned(pinned):
            reasons.append(f"{name} pinned identity is {pinned!r}; an unpinned identity cannot open a gate")
            continue
        observed = field(observed_rows.get(binding["runtime"]) or {}, binding["field"])
        if observed is None:
            reasons.append(f"{name} is not attested")
        elif observed != pinned:
            reasons.append(f"{name} mismatch: pinned {pinned}, attested {observed}")
    attested_config = attestation.get("config_sha256") or {}
    for pin in gate.get("config_pins", []):
        rel = pin["path"]
        target = repo / rel
        current = sha256_file(target) if target.is_file() else None
        if current != pin["sha256"]:
            reasons.append(f"config {rel} is stale: pinned {pin['sha256']}, repository now {current}")
        if attested_config.get(rel) is None:
            reasons.append(f"config {rel} is not attested")
        elif attested_config[rel] != pin["sha256"]:
            reasons.append(f"config {rel} mismatch: pinned {pin['sha256']}, attested {attested_config[rel]}")
    receipts = attestation.get("receipts") or []
    if not receipts:
        reasons.append("attestation carries no execution receipt")
    for receipt in receipts:
        reasons += verify_receipt(receipt, repo)
    if gate.get("kind") in REVIEW_KINDS:
        review = attestation.get("review")
        if not review:
            reasons.append("documented professional engineering review is required")
        else:
            reasons += verify_receipt(review, repo)
    return not reasons, reasons


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

def check_manifest(manifest: dict, inventory: dict, repo: Path = REPO) -> list[str]:
    errors = []
    packages = {p["package"]: p for p in inventory.get("packages", [])}
    current = manifest.get("current_reference_package", {})
    if current.get("package") not in packages:
        errors.append("current reference package is not in the inventory")
    elif packages[current["package"]]["archive_sha256"] != current.get("archive_sha256"):
        errors.append("current reference archive digest differs from its receipt")
    for item in manifest.get("superseded_packages", []):
        if item.get("package") not in packages:
            errors.append(f"superseded package {item.get('package')} is not in the inventory")
    prohibitions = {p.get("id"): p for p in manifest.get("prohibitions", [])}
    missing = REQUIRED_PROHIBITIONS - set(prohibitions)
    if missing:
        errors.append(f"manifest lacks prohibitions {sorted(missing)}")
    block = prohibitions.get("never-execute-pr229-blockmeshdict", {})
    member = block.get("archive_member", {})
    package = block.get("package")
    if package in packages:
        listed = load_json(repo / EVIDENCE / package / "file-manifest.json")
        entries = listed.get("files", listed if isinstance(listed, list) else [])
        hit = [e for e in entries if isinstance(e, dict) and e.get("path") == member.get("path")]
        if not hit or hit[0].get("sha256") != member.get("sha256"):
            errors.append("PR229 blockMeshDict hash differs from its committed file manifest")
        if packages[package]["archive_sha256"] != block.get("archive_sha256"):
            errors.append("PR229 archive digest differs from its receipt")
    else:
        errors.append("PR229 package is not in the inventory")
    case = prohibitions.get("never-touch-case-084", {})
    if packages.get(case.get("package"), {}).get("archive_sha256") != case.get("archive_sha256"):
        errors.append("case 084 archive digest differs from its receipt")
    traversals = prohibitions.get("do-not-replay-pr238-256-traversals", {})
    merges = inventory.get("merge_packages", {})
    for pr in traversals.get("pull_requests", []):
        added = merges.get(str(pr), {}).get("packages_added")
        if not added:
            errors.append(f"PR{pr} has no recorded evidence package")
        for name in added or []:
            if name not in packages:
                errors.append(f"PR{pr} package {name} is not in the inventory")
    for key in ("issue_snapshot_commit", "baseline_commit"):
        if not COMMIT.match(str(manifest.get("git", {}).get(key, ""))):
            errors.append(f"manifest git.{key} is not a full commit id")
    errors += check_claims(manifest, "baseline-manifest", repo)
    errors += check_context_links(manifest, "baseline-manifest", repo)
    return errors


def check_history(manifest: dict, inventory: dict, repo: Path = REPO) -> list[str]:
    """Re-derive the PR-to-package map from Git history (requires a full clone)."""
    merges = {pr: entry["merge_commit"] for pr, entry in inventory.get("merge_packages", {}).items()}
    fresh = merge_packages(repo, merges)
    return [] if fresh == inventory.get("merge_packages") else ["PR-to-package map differs from Git history"]


def check_all(base: Path = HERE, repo: Path = REPO, history: bool = False) -> list[str]:
    data = load_baseline(base)
    errors = []
    errors += check_inventory(data["inventory"], repo)
    errors += check_matrix(data["matrix"], repo)
    errors += check_ledger(data["ledger"], data["matrix"], repo)
    errors += check_manifest(data["manifest"], data["inventory"], repo)
    errors += check_claims(data["host"], "host-observations", repo)
    if history:
        errors += check_history(data["manifest"], data["inventory"], repo)
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command")
    check = sub.add_parser("check", help="verify the committed baseline (default)")
    check.add_argument("--history", action="store_true", help="also re-derive the PR map from Git history")
    inventory = sub.add_parser("inventory", help="rebuild the evidence inventory")
    inventory.add_argument("--releases", type=Path, help="saved `gh api --paginate repos/.../releases` output")
    inventory.add_argument("--merges", type=Path, help="JSON {pr: merge_commit} to map packages from history")
    inventory.add_argument("--write", action="store_true")
    evaluate = sub.add_parser("evaluate", help="decide whether an attestation may open a gate")
    evaluate.add_argument("--gate", required=True)
    evaluate.add_argument("--attestation", type=Path, required=True)
    args = parser.parse_args(argv)
    command = args.command or "check"
    if command == "check":
        errors = check_all(history=getattr(args, "history", False))
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print("bionic turbo baseline 2026-11-06: " + ("FAILED" if errors else "OK"))
        return 1 if errors else 0
    if command == "inventory":
        previous = load_json(HERE / FILES["inventory"]) if (HERE / FILES["inventory"]).is_file() else None
        releases = load_releases(args.releases) if args.releases else None
        merges = merge_packages(REPO, load_json(args.merges)) if args.merges else None
        text = dump_json(build_inventory(REPO, releases, previous, merges))
        if args.write:
            (HERE / FILES["inventory"]).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    data = load_baseline()
    may_open, reasons = evaluate_gate(args.gate, data["ledger"], data["matrix"], load_json(args.attestation))
    for reason in reasons:
        print(f"REFUSED {reason}")
    print(f"gate {args.gate}: " + ("may open" if may_open else "stays closed"))
    return 0 if may_open else 1


if __name__ == "__main__":
    sys.exit(main())
