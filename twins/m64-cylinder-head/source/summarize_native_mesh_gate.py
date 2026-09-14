#!/usr/bin/env python3
"""Reduce two pinned private receipts to a small, non-geometric batch gate.

This re-reads evidence; it does not execute checkMesh, re-audit geometry, or
authorize CFD/manufacturing. Hashes identify evidence, not its correctness.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


SETS = {
    "highAspectRatioCells", "underdeterminedCells", "nonOrthoFaces",
    "lowWeightFaces", "lowVolRatioFaces", "skewFaces", "shortEdges",
    "oneInternalFaceCells", "twoInternalFacesCells",
}


def read_pinned(path, expected):
    path = Path(path)
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or path.is_symlink():
        raise ValueError("invalid_evidence_identity")
    if not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("invalid_evidence_size")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("evidence_hash_mismatch")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("evidence_not_object")
    return data


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError("invalid_count")
    return value


def summarize(native, comparison, native_sha, comparison_sha):
    if comparison.get("candidate_report_sha256") != native_sha:
        raise ValueError("unpaired_receipts")
    for obj, flags in (
        (native, ("process_completed", "stages_completed", "inputs_unchanged",
                  "independent_PL_geometry_accepted")),
        (comparison, ("comparison_completed", "all_inputs_unchanged",
                      "baseline34_components_exactly_preserved",
                      "extra_groups_parent_disjoint_from_protected",
                      "no_new_native_defects_vs_34_verified")),
    ):
        if any(obj.get(key) is not True for key in flags):
            raise ValueError("incomplete_or_regressed_evidence")
    if (comparison.get("unresolved_sets") != []
            or comparison.get("new_failed_families") != []
            or count(comparison.get("unidentified_failed_families_after")) != 0
            or count(comparison.get("newly_flagged_total")) != 0):
        raise ValueError("unresolved_or_new_defects")
    sets = comparison.get("comparisons", {})
    if set(sets) != SETS:
        raise ValueError("unexpected_defect_sets")
    counts = {}
    for name, item in sets.items():
        if count(item.get("newly_flagged_count")) != 0:
            raise ValueError("new_defect_in_set")
        counts[name] = [count(item.get("source_flag_count")),
                        count(item.get("candidate_flag_count"))]
    failed = count(native.get("failed_check_count"))
    if count(comparison.get("failed_checks_after")) != failed:
        raise ValueError("failed_check_count_mismatch")
    if native.get("mesh_quality_accepted") is not (failed == 0):
        raise ValueError("native_quality_flag_inconsistent")
    if comparison.get("native_mesh_quality_accepted") is not (failed == 0):
        raise ValueError("comparison_quality_flag_inconsistent")
    return {
        "schema": "m64-native-mesh-gate/v1",
        "status": "mesh_quality_accepted_only" if failed == 0 else "mesh_quality_rejected",
        "evidence_identity_checked": True,
        "native_report_sha256": native_sha,
        "comparison_report_sha256": comparison_sha,
        "comparison_basis": "preserved_34_groups_to_expanded_533_groups",
        "defect_counts_before_after": counts,
        "failed_checks": failed,
        "newly_flagged_total": 0,
        "mesh_quality_accepted": failed == 0,
        "native_executed_by_this_summary": False,
        "CFD_authorized": False,
        "manufacturing_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native-report", "native-sha256", "comparison-report",
                 "comparison-sha256", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    data = summarize(read_pinned(args.native_report, args.native_sha256),
                     read_pinned(args.comparison_report, args.comparison_sha256),
                     args.native_sha256, args.comparison_sha256)
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
    if len(encoded.encode()) > 4096:
        raise ValueError("summary_too_large")
    with Path(args.output).open("x") as stream:
        stream.write(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
