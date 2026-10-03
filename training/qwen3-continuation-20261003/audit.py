"""Fail-closed preparation and paired assistant-review audits, using only stdlib.

Hashes of objects use canonical UTF-8 JSON (sorted keys, compact separators).
Hashes named *_file_sha256 and protocol/reservation pins hash file bytes.
This program establishes package integrity and registered model thresholds;
it does not establish scientific, human engineering or manufacturing validity.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import importlib
import json
from math import comb
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVIEW_FLAGS = ("acceptable", "unbacked_citation", "unit_condition_failure",
                "causal_failure", "critical_failure")
ROSTER_FIELDS = ("id", "suite", "critical", "input_sha256", "source_family")
PROFILE_FILES = ("task-routed-profile.json", "task_routed_profile.py",
                 "source-precision-profile.json", "source_precision_profile.py",
                 "condition-fidelity-profile.json", "condition_fidelity_profile.py",
                 "verify_grounded.py")
RETIRED_FILES = ("fidelity-final-test.jsonl", "fidelity-domain-benchmark.jsonl")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def object_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def text_sha256(value):
    if not isinstance(value, str):
        raise ValueError("Expected text to hash")
    return hashlib.sha256(value.encode()).hexdigest()


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative_file(root, relative):
    require(isinstance(relative, str) and relative, "Missing relative path")
    path = Path(relative)
    require(not path.is_absolute() and ".." not in path.parts, "Unsafe relative path")
    resolved = (Path(root) / path).resolve()
    require(resolved.is_relative_to(Path(root).resolve()), "Path escapes package root")
    require(resolved.is_file(), "Missing pinned file: " + relative)
    return resolved


def verify_file_hashes(root, hashes, required=()):
    require(isinstance(hashes, dict) and hashes, "Missing file hashes")
    require(set(required).issubset(hashes), "Required file hashes are missing")
    for name, expected in hashes.items():
        require(file_sha256(relative_file(root, name)) == expected, "Changed pinned file: " + name)


def verify_profile(root, protocol):
    profile = protocol["profile"]
    require(profile["name"] == protocol["inference_profile"] == "task_routed_v14",
            "Unexpected inference profile")
    historical = Path(root) / profile["historical_root"]
    require(historical.resolve().is_relative_to(Path(root).resolve()), "Historical root escapes repository")
    verify_file_hashes(historical, profile["input_files_sha256"], PROFILE_FILES)
    require(load(historical / "task-routed-profile.json")["name"] == "task_routed_v14",
            "Pinned profile name differs")
    return historical


@contextmanager
def historical_profile(historical):
    """Load pinned stdlib helpers without retaining historical sys.path changes."""
    names = ("verify_grounded", "source_precision_profile", "condition_fidelity_profile",
             "task_routed_profile")
    saved = {name: sys.modules.pop(name) for name in names if name in sys.modules}
    sys.path.insert(0, str(historical))
    try:
        helper = importlib.import_module("task_routed_profile")
        for name in names:
            module = sys.modules[name]
            require(Path(module.__file__).resolve().parent == historical.resolve(),
                    "Historical helper resolved outside pinned root")
        yield helper
    finally:
        sys.path.remove(str(historical))
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(saved)


def expanded_messages(historical, row):
    raw = dict(row)
    raw["messages"] = row["raw_messages"]
    with historical_profile(historical) as helper:
        expanded = helper.questions_with_profile([raw])[0]
    return expanded["messages"], expanded["inference_task_route"]


def no_holdout_claim(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("unseen", "is_test", "test_claim", "heldout_claim", "unseen_test",
                       "unseen_test_claimed", "used_for_test", "independent_expert_validated",
                       "scientific_or_manufacturing_validation_claim"):
                require(child is False, "Unsupported unseen/test or validation claim")
            if key == "split":
                require(child in ("train", "development"), "Nontraining split in candidate data")
            no_holdout_claim(child)
    elif isinstance(value, list):
        for child in value:
            no_holdout_claim(child)


def verify_data(root=ROOT, directory=HERE):
    """Validate candidate provenance and profile equivalence; do not grade answers."""
    root, directory = Path(root), Path(directory)
    protocol = load(directory / "protocol.json")
    historical = verify_profile(root, protocol)
    historical_relative = str(historical.relative_to(root))
    required_inputs = [historical_relative + "/grounded-v3/" + name
                       for name in ("sources.json", "passages.jsonl", "manifest.json")]
    required_inputs += [historical_relative + "/" + name for name in RETIRED_FILES]
    verify_file_hashes(root, protocol["data_inputs_sha256"], required_inputs)
    data = directory / "data"
    manifest = load(data / "manifest.json")
    no_holdout_claim(manifest)
    require(manifest.get("status") == "prepared_candidate_corrections_not_trained_not_independently_validated",
            "Unsupported preparation status claim")
    require(manifest.get("heldout_claim") is False and manifest.get("training_source_splits_only") is True,
            "Candidate data must be training/development only")
    require(manifest.get("historical_files_modified") is False, "Historical data changes are forbidden")
    require(manifest["model_family"] == protocol["model_id"] and
            manifest["base_revision"] == protocol["revision"] and
            manifest["warm_start_adapter_sha256"] == protocol["initial_adapter_sha256"],
            "Candidate model lineage differs")
    require(manifest["inference_profile"] == protocol["inference_profile"] and
            manifest["profile_sha256"] == file_sha256(historical / "task-routed-profile.json") and
            manifest["profile_helper_sha256"] == file_sha256(historical / "task_routed_profile.py"),
            "Candidate profile pin differs")
    verify_file_hashes(data, manifest["files_sha256"],
                       ("train-records.jsonl", "source-ledger.json", "LICENSE-NOTICES.md"))
    require(set(manifest["excluded_test_files_sha256"]) ==
            {historical_relative + "/" + name for name in RETIRED_FILES},
            "Missing retired fidelity exclusions")
    verify_file_hashes(root, manifest["excluded_test_files_sha256"])
    retired = {row["passage_id"] for name in RETIRED_FILES for row in rows(historical / name)}
    require(set(manifest["retired_fidelity_passages_excluded"]) == retired,
            "Retired passage exclusion roster differs")
    sources = {source["source_id"]: source for source in load(historical / "grounded-v3/sources.json")}
    passages = {passage["passage_id"]: passage for passage in rows(historical / "grounded-v3/passages.jsonl")}
    ledger_rows = load(data / "source-ledger.json")["training_sources"]
    require(len({source["source_id"] for source in ledger_rows}) == len(ledger_rows), "Duplicate ledger source")
    ledger = {source["source_id"]: source for source in ledger_rows}
    selected = {}
    for source in ledger_rows:
        sid = source["source_id"]
        require(sid in sources and source["id"] == sid, "Unknown training source")
        original = sources[sid]
        require(source["split"] == original["split"] == "train", "Source is not assigned to training")
        require(source.get("scientific_approval") is False and source.get("expert_review") == "pending",
                "Unsupported source scientific validation claim")
        require(source["license"] == original["license"] == "CC BY 4.0", "Unsupported or changed training licence")
        for field in ("authors", "title", "doi", "url", "license_url", "snapshot_sha256"):
            require(source[field] == original[field], "Source metadata differs: " + field)
        require(source["original_path"] == historical_relative + "/" + original["original_path"],
                "Source snapshot path differs")
        require(source["license_evidence"] == historical_relative + "/" + original["license_evidence"],
                "Source licence evidence path differs")
        require(file_sha256(relative_file(root, source["original_path"])) == source["snapshot_sha256"],
                "Source snapshot hash differs")
        require(file_sha256(relative_file(root, source["license_evidence"])) == source["license_evidence_sha256"],
                "Licence evidence hash differs")
        require("creativecommons.org/licenses/by/4.0/" in relative_file(root, source["license_evidence"]).read_text(encoding="utf-8"),
                "Licence evidence does not retain the licence")
        require(isinstance(source.get("passages"), list) and source["passages"], "No selected source passages")
        for passage in source["passages"]:
            pid = passage["id"]
            require(pid not in selected and pid not in retired and pid in passages,
                    "Duplicate, retired or unknown selected passage")
            original_passage = passages[pid]
            require(original_passage["source_id"] == sid and original_passage["split"] == "train",
                    "Selected passage source or split differs")
            require(isinstance(passage["text"], str) and passage["text"] and
                    passage["text"] in original_passage["text"], "Excerpt differs from frozen passage")
            require(text_sha256(passage["text"]) == passage["excerpt_sha256"], "Ledger excerpt hash differs")
            selected[pid] = passage
    records = rows(data / "train-records.jsonl")
    require(records and len(records) <= protocol["training"]["max_rows"], "Invalid training row count")
    require(len({row["id"] for row in records}) == len(records), "Duplicate training row ID")
    require(set(manifest["row_sha256"]) == {row["id"] for row in records}, "Row hash coverage differs")
    pairs = set()
    for row in records:
        no_holdout_claim(row)
        require(object_sha256(row) == manifest["row_sha256"][row["id"]], "Training row hash differs")
        require(row.get("prior_exposure") == "historical_development_or_training", "Unseen/test claim in training data")
        require(row.get("answer_origin") == "assistant_authored_source_grounded", "Unrecorded answer authorship")
        require(row.get("expert_review") == "pending", "Unsupported expert validation claim")
        sid, pid = row["source_id"], row["passage_id"]
        require(sid in ledger and pid in selected and pid not in retired, "Unregistered or retired training passage")
        source, passage, original = ledger[sid], selected[pid], passages[pid]
        require(original["source_id"] == sid and sources[sid]["split"] == "train", "Training source leakage")
        require(row["excerpt"] == passage["text"] and row["excerpt_sha256"] == passage["excerpt_sha256"],
                "Training excerpt mismatch")
        provenance = row["provenance"]
        require(provenance["excerpt_sha256"] == row["excerpt_sha256"], "Provenance excerpt mismatch")
        for field in ("authors", "title", "doi", "url", "license", "license_url", "license_evidence_sha256"):
            require(provenance[field] == source[field], "Row source metadata differs: " + field)
        require(provenance["source_path"] == source["original_path"] and
                provenance["source_file_sha256"] == source["snapshot_sha256"] and
                provenance["license_evidence_path"] == source["license_evidence"], "Row source file provenance differs")
        require(provenance["passages_path"] == historical_relative + "/grounded-v3/passages.jsonl" and
                provenance["passages_file_sha256"] == file_sha256(historical / "grounded-v3/passages.jsonl"),
                "Row passage file provenance differs")
        locator = provenance["locator"]
        require(locator["paragraph_index"] == original["paragraph"] and locator["section"] == original["section"] and
                locator["parent_text_sha256"] == text_sha256(original["text"]), "Original paragraph locator differs")
        notice = relative_file(root, provenance["retained_license_notice"])
        require(notice.resolve().is_relative_to(data.resolve()), "Retained licence notice is outside data package")
        require(file_sha256(notice) == provenance["license_evidence_sha256"], "Retained licence notice changed")
        require(str(notice.relative_to(data.resolve())) in manifest["files_sha256"], "Licence notice is not manifest-pinned")
        expected_raw = [{"role": "user", "content": "QUESTION: " + row["question"] + "\nEXCERPT " + pid + ": " + row["excerpt"]}]
        require(row["raw_messages"] == expected_raw, "Raw training question or excerpt changed")
        expanded, route = expanded_messages(historical, row)
        require(row["messages"] == expanded + [{"role": "assistant", "content": row["response"]}] and
                row["inference_task_route"] == route, "Training/inference messages differ")
        require(isinstance(row["response"], str) and row["response"].strip() and pid in row["response"],
                "Missing authored response or source attribution")
        pair = object_sha256(row["messages"])
        require(pair not in pairs, "Duplicate training message pair")
        pairs.add(pair)
    require(set(ledger) == {row["source_id"] for row in records}, "Unused or missing training source ledger")
    require(set(selected) == {row["passage_id"] for row in records}, "Unused or missing passage ledger")
    for field, actual in (("train_rows", len(records)), ("unique_passage_ids", len(selected)),
                          ("language_counts", dict(Counter(row["language"] for row in records))),
                          ("source_counts", dict(Counter(row["source_id"] for row in records))),
                          ("route_counts", dict(Counter(row["inference_task_route"] for row in records)))):
        require(manifest[field] == actual, "Manifest count differs: " + field)
    return {"status": "pass", "train_rows": len(records), "unique_passages": len(selected),
            "source_families": len(ledger), "profile": protocol["inference_profile"],
            "manifest_sha256": file_sha256(data / "manifest.json"),
            "protocol_sha256": file_sha256(directory / "protocol.json"),
            "heldout_claim": False, "independent_expert_validated": False,
            "scope": "Preparation integrity only; no training or scientific performance claim"}


def audit_data(directory=HERE, root=ROOT):
    return verify_data(root, directory)


def _validate_roster(roster):
    require(isinstance(roster, list) and roster, "Empty evaluation roster")
    require(len({r["id"] for r in roster}) == len(roster), "Duplicate evaluation item")
    for row in roster:
        require(set(row) == set(ROSTER_FIELDS), "Invalid reservation roster fields")
        require(isinstance(row["id"], str) and row["id"], "Missing item ID")
        require(isinstance(row["critical"], bool), "Critical flag must be boolean")
        require(isinstance(row["suite"], str) and row["suite"], "Missing suite")
        require(isinstance(row["source_family"], str) and row["source_family"], "Missing source family")
        require(isinstance(row["input_sha256"], str) and len(row["input_sha256"]) == 64,
                "Invalid input hash")


def _run_roster(run):
    return [{key: row[key] for key in ROSTER_FIELDS} for row in run["rows"]]


def mcnemar_exact(gains, losses):
    """Exact two-sided conditional binomial probability; descriptive diagnostic."""
    discordant = gains + losses
    if not discordant:
        return 1.0
    tail = sum(comb(discordant, k) for k in range(min(gains, losses) + 1))
    return min(1.0, 2 * tail / (2 ** discordant))


def _reviewed_decisions(run, reviews, count):
    matches = [review for review in reviews if review.get("run_sha256") == object_sha256(run)]
    require(len(matches) == count, "Missing or excess independent reviews")
    require(len({review["reviewer_id"] for review in matches}) == count,
            "Reviewers are not distinct")
    indexed = []
    for review in matches:
        require(review.get("assistant_independent") is True, "Review independence not declared")
        require(isinstance(review["reviewer_id"], str) and review["reviewer_id"], "Missing reviewer ID")
        require([row["id"] for row in review["rows"]] == [row["id"] for row in run["rows"]],
                "Incomplete or reordered review")
        for decision, generated in zip(review["rows"], run["rows"]):
            require(decision["response_sha256"] == generated["response_sha256"],
                    "Review refers to another response")
            require(all(isinstance(decision.get(flag), bool) for flag in REVIEW_FLAGS),
                    "Incomplete scientific review flags")
            require(isinstance(decision.get("reason"), str) and decision["reason"].strip(),
                    "Missing scientific review reason")
            require(not decision["critical_failure"] or generated["critical"],
                    "Critical failure assigned to a noncritical item")
        indexed.append(review["rows"])
    decisions = []
    for index, generated in enumerate(run["rows"]):
        votes = [review[index] for review in indexed]
        agreement = all(tuple(vote[flag] for flag in REVIEW_FLAGS) ==
                        tuple(votes[0][flag] for flag in REVIEW_FLAGS) for vote in votes)
        flags = {flag: any(vote[flag] for vote in votes) for flag in REVIEW_FLAGS[1:]}
        acceptable = agreement and all(vote["acceptable"] for vote in votes) and not any(flags.values())
        decisions.append({"id": generated["id"], "critical": generated["critical"],
                          "acceptable": acceptable, "agreement": agreement,
                          **flags, "reviews": votes})
    return decisions


def aggregate(protocol, reservation, base, adapter, reviews, *, protocol_sha256,
              reservation_sha256, reservation_amendment=None, reservation_amendment_sha256=None):
    """Validate complete evidence before applying pre-registered acceptance gates."""
    evaluation = protocol["evaluation"]
    for key, value in evaluation.items():
        if key.startswith("minimum_") or key.startswith("maximum_") or key == "reviewers_per_response":
            require(type(value) is int and value >= 0, "Invalid numeric protocol requirement: " + key)
    require(evaluation["reviewers_per_response"] == 2, "Protocol requires exactly two reviewers")
    require(evaluation["disagreement_policy"] == "conservative_failure", "Unsupported disagreement policy")
    require(evaluation["reserved_required"] is True and evaluation["paired_input_hash_required"] is True,
            "Independent paired reservation is required")
    require(reservation.get("schema_version") == 1 and reservation.get("suite") == "reserved",
            "Evaluation is not independently reserved")
    require(reservation.get("independent_custodian") is True and reservation.get("custodian_id"),
            "Independent custodian is missing")
    if reservation["experiment_id"] != protocol["experiment_id"]:
        require(isinstance(reservation_amendment, dict) and
                isinstance(reservation_amendment_sha256, str) and len(reservation_amendment_sha256) == 64,
                "Reservation belongs to another experiment without a pinned amendment")
        expected = {"original_reservation_sha256": reservation_sha256,
                    "protocol_sha256": protocol_sha256,
                    "experiment_id": protocol["experiment_id"],
                    "roster_sha256": reservation["roster_sha256"],
                    "questions_sha256": reservation["questions_sha256"],
                    "acceptance_rules_sha256": object_sha256(evaluation)}
        require(all(reservation_amendment.get(key) == value for key, value in expected.items()),
                "Reservation amendment changed inputs, experiment or acceptance rules")
        runner = reservation_amendment.get("runner_sha256")
        require(isinstance(runner, str) and len(runner) == 64, "Amendment runner pin is missing")
        require(all(run.get("runner_sha256") == runner and
                    run.get("reservation_amendment_sha256") == reservation_amendment_sha256
                    for run in (base, adapter)), "Run differs from reservation amendment")
    roster = reservation["roster"]
    _validate_roster(roster)
    roster_hash = object_sha256(roster)
    require(reservation["roster_sha256"] == roster_hash, "Reservation roster hash differs")
    require(set(evaluation["required_suites"]).issubset({row["suite"] for row in roster}),
            "Required supplemental or primary suite is missing")
    require(set(row["suite"] for row in roster).issubset(evaluation["required_suites"]),
            "Unregistered evaluation suite")
    require(isinstance(reviews, list) and reviews, "Empty independent review evidence")
    require(len(reviews) == 2 * evaluation["reviewers_per_response"], "Unexpected review count")
    for run, role in ((base, "base"), (adapter, "adapter")):
        require(run.get("schema_version") == 1 and run.get("status") == "completed", "Incomplete generation run")
        require(run.get("model_role") == role and run.get("suite") == "reserved", "Wrong model role or suite")
        require(run.get("model_id") == protocol["model_id"] and run.get("revision") == protocol["revision"],
                "Different base model or revision")
        require(run.get("profile_name") == protocol["inference_profile"], "Inference profile differs")
        require(run.get("decoding") == protocol["decoding"], "Decoding differs from registration")
        require(run.get("protocol_sha256") == protocol_sha256, "Run used another protocol")
        require(run.get("reservation_sha256") == reservation_sha256, "Run used another reservation")
        require(run.get("roster_sha256") == roster_hash and _run_roster(run) == roster,
                "Run roster is incomplete, reordered or differs from reservation")
        require(isinstance(run.get("runtime_sha256"), str) and len(run["runtime_sha256"]) == 64,
                "Runtime identity is missing")
        require(isinstance(run.get("model_files_sha256"), dict) and run["model_files_sha256"] and
                all(isinstance(name, str) and name and isinstance(digest, str) and len(digest) == 64
                    for name, digest in run["model_files_sha256"].items()), "Model file identity is missing")
        for field in ("adapter_sha256", "selection_receipt_sha256"):
            require(isinstance(run.get(field), str) and len(run[field]) == 64,
                    "Missing reserved weight/selection pin: " + field)
        for row in run["rows"]:
            require(isinstance(row.get("budget_hit"), bool), "Missing generation-budget flag")
            require(isinstance(row.get("response"), str) and row["response"].strip(), "Empty generated response")
            require(text_sha256(row["response"]) == row["response_sha256"], "Generated response hash differs")
            require(isinstance(row.get("messages"), list) and row["messages"], "Missing executed messages")
            require(all(set(message) == {"role", "content"} and
                        message["role"] in ("system", "user") and
                        isinstance(message["content"], str) for message in row["messages"]),
                    "Invalid executed evaluation messages")
            require(object_sha256(row["messages"]) == row["input_sha256"], "Executed input hash differs")
            references = re.findall(r"\[([\w]+):p\d+\]", "\n".join(message["content"] for message in row["messages"]))
            require(row.get("source_id") == row["source_family"] and row["source_family"] in references,
                    "Source family is not bound to supplied evidence")
    require(base["runtime_sha256"] == adapter["runtime_sha256"], "Paired runtime differs")
    for field in ("model_files_sha256", "adapter_sha256", "selection_receipt_sha256"):
        require(base[field] == adapter[field], "Paired weight/selection identity differs: " + field)
    require(all(b["messages"] == a["messages"] for b, a in zip(base["rows"], adapter["rows"])),
            "Paired executed messages differ")
    base_decisions = _reviewed_decisions(base, reviews, evaluation["reviewers_per_response"])
    adapter_decisions = _reviewed_decisions(adapter, reviews, evaluation["reviewers_per_response"])
    n = len(roster)
    gains = sum(not b["acceptable"] and a["acceptable"] for b, a in zip(base_decisions, adapter_decisions))
    losses = sum(b["acceptable"] and not a["acceptable"] for b, a in zip(base_decisions, adapter_decisions))
    critical_regressions = sum(b["acceptable"] and not a["acceptable"] and a["critical"]
                               for b, a in zip(base_decisions, adapter_decisions))
    counts = {
        "rows": n, "critical_rows": sum(row["critical"] for row in roster),
        "base_acceptable": sum(row["acceptable"] for row in base_decisions),
        "candidate_acceptable": sum(row["acceptable"] for row in adapter_decisions),
        "gains": gains, "losses": losses, "ties": n - gains - losses, "net_gain": gains - losses,
        "critical_regressions": critical_regressions,
        "critical_failures": sum(row["critical"] and not row["acceptable"] for row in adapter_decisions),
        "unsupported_citations": sum(row["unbacked_citation"] for row in adapter_decisions),
        "unit_condition_failures": sum(row["unit_condition_failure"] for row in adapter_decisions),
        "causal_failures": sum(row["causal_failure"] for row in adapter_decisions),
        "budget_hits": sum(row["budget_hit"] for run in (base, adapter) for row in run["rows"]),
        "base_review_disagreements": sum(not row["agreement"] for row in base_decisions),
        "candidate_review_disagreements": sum(not row["agreement"] for row in adapter_decisions),
    }
    subgroups = {}
    for generated, b, a in zip(roster, base_decisions, adapter_decisions):
        group = subgroups.setdefault(generated["source_family"],
                                     {"rows": 0, "base_acceptable": 0, "candidate_acceptable": 0, "gains": 0, "losses": 0})
        group["rows"] += 1
        group["base_acceptable"] += b["acceptable"]
        group["candidate_acceptable"] += a["acceptable"]
        group["gains"] += not b["acceptable"] and a["acceptable"]
        group["losses"] += b["acceptable"] and not a["acceptable"]
    for group in subgroups.values():
        group["net_gain"] = group["gains"] - group["losses"]
        group["mcnemar_exact_two_sided_p"] = mcnemar_exact(group["gains"], group["losses"])
    failures = []
    for field, minimum in (("rows", "minimum_rows"), ("critical_rows", "minimum_critical_rows"),
                           ("candidate_acceptable", "minimum_candidate_acceptable"), ("net_gain", "minimum_net_gain")):
        if counts[field] < evaluation[minimum]:
            failures.append(minimum)
    numerator = evaluation["minimum_acceptable_fraction_numerator"]
    denominator = evaluation["minimum_acceptable_fraction_denominator"]
    require(isinstance(numerator, int) and isinstance(denominator, int) and 0 < numerator <= denominator,
            "Invalid acceptable fraction")
    if counts["candidate_acceptable"] * denominator < n * numerator:
        failures.append("minimum_acceptable_fraction")
    for field in ("critical_regressions", "critical_failures", "unsupported_citations", "budget_hits",
                  "unit_condition_failures", "causal_failures"):
        if counts[field] > evaluation["maximum_" + field]:
            failures.append("maximum_" + field)
    return {
        "status": "accepted_registered_model_thresholds" if not failures else "rejected_registered_model_thresholds",
        "accepted": not failures, "failures": failures, "counts": counts,
        "suite_counts": dict(Counter(row["suite"] for row in roster)),
        "source_family_counts": subgroups,
        "roster_sha256": roster_hash, "protocol_sha256": protocol_sha256,
        "reservation_sha256": reservation_sha256,
        "run_sha256": {"base": object_sha256(base), "adapter": object_sha256(adapter)},
        "adapter_sha256": adapter["adapter_sha256"],
        "selection_receipt_sha256": adapter["selection_receipt_sha256"],
        "mcnemar_exact_two_sided_p": mcnemar_exact(gains, losses),
        "mcnemar_scope": "Descriptive diagnostic only; no statistically significant benefit claim",
        "decisions": {"base": base_decisions, "adapter": adapter_decisions},
        "independent_expert_validated": False, "scientific_or_manufacturing_validation_claim": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    data = subparsers.add_parser("data", help="Verify the training/development package")
    data.add_argument("--directory", type=Path, default=HERE)
    data.add_argument("--root", type=Path, default=ROOT)
    paired = subparsers.add_parser("evaluate", help="Aggregate completed independent reserved evidence")
    paired.add_argument("--protocol", type=Path, default=HERE / "protocol.json")
    paired.add_argument("--reservation", type=Path, required=True)
    paired.add_argument("--reservation-amendment", type=Path)
    paired.add_argument("--base", type=Path, required=True)
    paired.add_argument("--adapter", type=Path, required=True)
    paired.add_argument("--review", type=Path, action="append", required=True)
    args = parser.parse_args()
    try:
        if args.command == "data":
            result = verify_data(args.root, args.directory)
        else:
            verify_profile(ROOT, load(args.protocol))
            result = aggregate(load(args.protocol), load(args.reservation), load(args.base), load(args.adapter),
                               [load(path) for path in args.review], protocol_sha256=file_sha256(args.protocol),
                               reservation_sha256=file_sha256(args.reservation),
                               reservation_amendment=load(args.reservation_amendment) if args.reservation_amendment else None,
                               reservation_amendment_sha256=file_sha256(args.reservation_amendment) if args.reservation_amendment else None)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if result.get("accepted", True) else 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({"status": "failed_closed", "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
