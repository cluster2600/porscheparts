"""Assess retained directed intervals against the unchanged frozen gates."""
import argparse
import json
import math
from pathlib import Path

from audit_quality_distance import ROOT, digest, save


def assess(directory):
    contract_path = directory/"frozen-execution-contract.json"
    contract = json.loads(contract_path.read_text())
    summary = json.loads((directory/"execution-summary.json").read_text())
    if (summary["contract_sha256"] != digest(contract_path) or
            summary["native_queries_completed"] is not True or
            summary["all_bound_inputs_unchanged"] is not True):
        raise ValueError("Complete unchanged native query set required")
    all_pins = dict(contract["input_hashes"], **contract["query_config_hashes"])
    if not all(digest(ROOT/path) == sha for path, sha in all_pins.items()):
        raise ValueError("Frozen source/input/runtime changed")
    intervals = {}; rows = []
    for path in contract["queries"]:
        config = json.loads((ROOT/path).read_text()); folder = directory/config["id"]
        execution_path = folder/"execution-receipt.json"
        execution = json.loads(execution_path.read_text())
        if (digest(execution_path) != summary["execution_receipt_sha256"][str(execution_path.relative_to(directory))]
                or execution["returncode"] != 0 or execution["stopped_by_watchdog"] is not None
                or execution["all_bound_inputs_unchanged"] is not True
                or execution["contract_sha256"] != digest(contract_path)
                or execution["config_sha256"] != digest(ROOT/path)
                or execution["maximum_observed_worker_RSS_bytes"] > contract["resources"]["rss_stop_bytes"]
                or execution["wall_seconds"] > contract["resources"]["process_group_deadline_seconds"]+3):
            raise ValueError("Bound completed native process and approved controls required")
        if not all(digest(folder/name) == sha for name, sha in execution["artifact_sha256"].items()):
            raise ValueError("Native artifacts changed")
        report = json.loads((folder/"worker-report.json").read_text())
        distance = report["distance"]; low, high = distance["lower"], distance["upper"]
        if (any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                for x in (low, high)) or not 0 <= low <= high or
                high-low > contract["absolute_gap_tolerance_mm"] or
                report["status"] != "completed" or report["all_bound_inputs_unchanged"] is not True
                or report["contract_sha256"] != digest(contract_path)
                or report["config_sha256"] != digest(ROOT/path)
                or distance["target_faces"] != report["complete_target_faces"]
                or distance["target_is_complete"] is not True):
            raise ValueError("Finite completed directed interval and full target required")
        if contract["kind"] == "fixtures":
            expected = contract["expected_analytic_mm"][config["id"]]
            if not low <= expected <= high or distance["target_faces"] != 2 or distance["source_faces"] != (1 if config["partition"] else 2):
                raise ValueError("Frozen independent analytic reference or source/target coverage failed")
        rows.append(dict(id=config["id"], lower_mm=low, upper_mm=high,
            gap_mm=high-low, full_target_faces=distance["target_faces"],
            query_source_faces=distance["source_faces"],
            expected_analytic_mm=contract.get("expected_analytic_mm", {}).get(config["id"]),
            maximum_observed_worker_RSS_bytes=execution["maximum_observed_worker_RSS_bytes"],
            wall_seconds=execution["wall_seconds"],
            native_report_sha256=digest(folder/"worker-report.json")))
        intervals[config["id"]] = (low, high)
    if contract["kind"] == "fixtures":
        for name, (low, high) in intervals.items():
            if name.endswith("-full"):
                other = intervals[name[:-4]+"reduced"]
                if max(low, other[0]) > min(high, other[1]):
                    raise ValueError("Full and exactly reduced directed intervals disagree")
    upper = max(row["upper_mm"] for row in rows)
    head_gate = contract["kind"] == "reviewed_head" and upper <= contract["envelope_limit_mm"]
    return dict(schema="962-directed-cub-assessment/v1", kind=contract["kind"],
        status="analytic_directed_reduction_fixtures_passed_head_query_held" if contract["kind"] == "fixtures" else
            ("polygon_envelope_distance_gate_passed_only" if head_gate else "polygon_envelope_distance_gate_rejected"),
        contract_sha256=digest(contract_path), assessor_sha256=digest(Path(__file__)),
        directions=rows, maximum_upper_mm=upper,
        all_bound_artifact_hashes_verified=True, absolute_gap_tolerance_mm=contract["absolute_gap_tolerance_mm"],
        analytic_fixtures_passed=contract["kind"] == "fixtures",
        independent_polygon_distance_gate_passed=head_gate,
        native_CAD_deviation_certified=False, rounding_error_certificate=False,
        feature_channel_BCC_review_completed=False, solver_admission_established=False,
        engineering_accepted=False, manufacturing_authorized=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path); parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink():
        raise ValueError("Existing assessment preserved")
    result = assess(args.directory); save(args.report, result)
    print(json.dumps(result, indent=2))
