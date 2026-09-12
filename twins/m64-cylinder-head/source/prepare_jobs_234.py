#!/usr/bin/env python3
"""Snapshot the trusted preparation plan and pinned PUBLIC receipts, never run it.

No SSH, Docker, rental, solver, geometry editing or promotion of a physics gate.
This is an offline handoff packet, not a runtime/billing or validation controller.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


JOB_IDS = {"2-geometry-mesh", "3-operating-cycle", "3-thermal", "3-structure",
           "4-coupon", "4-build-distortion"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_file(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink_input_refused")
    if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("input_missing_or_too_large")
    return path.read_bytes()


def prepare(root, plan_path, output):
    root, plan_path, output = Path(root), Path(plan_path), Path(output)
    if not all(p.is_absolute() for p in (root, plan_path, output)):
        raise ValueError("absolute_paths_required")
    raw = read_file(plan_path)
    plan = json.loads(raw)
    if (plan.get("schema") != "m64-jobs-234-preparation/v1"
            or plan.get("mode") != "prepare_only"
            or any(plan.get(key) is not False for key in ("rental_enabled", "manufacturing_authorized"))
            or plan.get("preserve_master_contour") is not True):
        raise ValueError("preparation_only_required")
    jobs = plan["jobs"]
    if len(jobs) != len(JOB_IDS) or {j["id"] for j in jobs} != JOB_IDS:
        raise ValueError("unexpected_jobs")
    for job in jobs:
        if (job.get("ready_for_execution") is not False or not job.get("missing")
                or not set(job["depends_on"]) <= JOB_IDS):
            raise ValueError("unreviewed_job_admission")
    budget = plan["budget"]
    for key in ("user_total_ceiling", "campaign_working_allocation", "campaign_reserve",
                "first_wave_ceiling", "paid_pilot_ceiling_each",
                "paid_pilot_wall_seconds_including_setup_and_cleanup",
                "max_rental_usd_per_hour", "max_concurrent_paid_instances"):
        value = budget[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("budget_plan_invalid_number")
    ceilings = [j["rental_budget_usd"] for j in jobs]
    if any(type(n) not in (int, float) or not 0 <= n <= 4 for n in ceilings):
        raise ValueError("invalid_job_budget")
    if (sum(ceilings) > budget["first_wave_ceiling"]
            or not 0 <= budget["first_wave_ceiling"] <= budget["campaign_working_allocation"]
            or budget["campaign_working_allocation"] + budget["campaign_reserve"] > 38
            or budget["user_total_ceiling"] != 38
            or not 0 < budget["paid_pilot_ceiling_each"] <= 4
            or not 0 < budget["max_rental_usd_per_hour"] <= 0.8
            or not 0 < budget["paid_pilot_wall_seconds_including_setup_and_cleanup"] <= 10800
            or budget["max_concurrent_paid_instances"] != 1
            or budget["automatic_retry"] is not False
            or budget["automatic_recharge"] is not False):
        raise ValueError("budget_plan_inconsistent")
    payloads, receipts = {}, {}
    if set(plan["evidence"]) != {"interfaces", "native_mesh", "thermal_inventory", "f58_refinement"}:
        raise ValueError("unexpected_evidence_names")
    for name, item in plan["evidence"].items():
        relative = Path(item["path"])
        if (relative.is_absolute() or ".." in relative.parts
                or not re.fullmatch(r"[a-z][a-z0-9_]*", name)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise ValueError("invalid_evidence_identity")
        data = read_file(root / relative)
        if digest(data) != item["sha256"]:
            raise ValueError("evidence_hash_mismatch")
        receipts[name], payloads[name] = json.loads(data), data
    interfaces = receipts["interfaces"]
    report = {
        "schema": "m64-jobs-234-preparation-receipt/v1",
        "packet_prepared": True,
        "plan_sha256": digest(raw),
        "pinned_receipts_sha256": {k: digest(v) for k, v in payloads.items()},
        "selected_variant": interfaces["selected_variant"],
        "missing_interfaces": [k for k, v in interfaces["critical_interfaces"].items()
                               if any(v.get(f) is None for f in ("nominal", "tolerance", "source"))],
        "native_failed_checks": receipts["native_mesh"]["failed_checks"],
        "thermal_partition_complete": receipts["thermal_inventory"]["boundary_partition_complete"],
        "coupon_cap_persists": receipts["f58_refinement"]["common_parameters"]["cap_hit_both"],
        "jobs_missing_prerequisites": {j["id"]: j["missing"] for j in jobs},
        "ready_for_remote_execution": False,
        "new_rental": False,
        "solver_executed": False,
        "manufacturing_authorized": False,
    }
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("symlink_output_refused")
    output.mkdir()  # Existing output is never overwritten, including a prior failed packet.
    (output / "plan.json").write_bytes(raw)
    for name, data in payloads.items():
        (output / (name + ".json")).write_bytes(data)
    (output / "preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "plan", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    report = prepare(args.root, args.plan, args.output)
    print(json.dumps({"packet_prepared": report["packet_prepared"],
                      "plan_sha256": report["plan_sha256"],
                      "ready_for_remote_execution": False,
                      "manufacturing_authorized": False}))


if __name__ == "__main__":
    main()
