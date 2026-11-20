#!/usr/bin/env python3
"""The standing of each of the 32 machined features after the first check and the declared re-fit (#696).

Reads the first check, the re-fits, the check of the re-fits and the declaration, and states for every feature
whether it is confirmed (and by which check) or why it is not confirmable from this scan, using only the reason
classes the declaration fixed before the re-fits were checked. Every feature not confirmed needs a contributed
measurement of the specimen. Nothing is measured here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twin_common import sha256_file, write_json  # noqa: E402

SCHEMA = "935-cad-twin-feature-confirmation/1"


def standing(first_check: dict, refits: dict, refit_check: dict, declaration: dict) -> list:
    """One row per feature, in the order of the first check."""

    min_share = refit_check["acceptance"]["min_share"]
    refit = {r["id"]: r for r in refits["regions"]}
    checked = {r["id"]: r for r in refit_check["regions"]}
    reasons = declaration["reasons_if_not_confirmed"]
    rows = []
    for first in first_check["regions"]:
        rid = first["id"]
        row = {"id": rid, "first_check_share": first.get("share_within_tolerance")}
        if first["confirmed"]:
            rows.append({**row, "status": "confirmed", "by": "first check"})
            continue
        r, c = refit[rid], checked[rid]
        row["refit_check_share"] = c.get("share_within_tolerance")
        row["fitted_half_share_with_a_richer_surface"] = r["fitted_half"]["share_with_a_richer_surface"]
        if c["confirmed"]:
            rows.append({**row, "status": "confirmed", "by": "declared re-fit"})
        elif not r["guard_passed"]:
            # the guard either rejected a drifting re-fit or found too few vertices to refit at all
            drifted = r["refit_attempt"] is not None
            rows.append({**row, "status": "not confirmable from this scan", "reason_class": "guard",
                         "reason": reasons["guard"] if drifted else r["reason"]})
        elif r["fitted_half"]["share_with_a_richer_surface"] < min_share:
            rows.append({**row, "status": "not confirmable from this scan", "reason_class": "unresolved",
                         "reason": reasons["unresolved"]})
        else:
            rows.append({**row, "status": "not confirmable from this scan", "reason_class": "shape",
                         "reason": reasons["shape"]})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--first-check", type=Path, required=True)
    ap.add_argument("--refits", type=Path, required=True)
    ap.add_argument("--refit-check", type=Path, required=True)
    ap.add_argument("--declaration", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    first_check, refits, refit_check, declaration = (json.loads(p.read_text()) for p in
                                                     (args.first_check, args.refits, args.refit_check, args.declaration))
    if refits["declaration_sha256"] != sha256_file(args.declaration) or refit_check["fits_sha256"] != sha256_file(args.refits):
        raise SystemExit("the re-fits, their check and the declaration do not belong together")
    if refits["first_check_sha256"] != sha256_file(args.first_check):
        raise SystemExit("the re-fits were not made from this first check")
    if refit_check["acceptance"] != first_check["acceptance"]:
        raise SystemExit("the acceptance changed between the two checks")
    rows = standing(first_check, refits, refit_check, declaration)
    confirmed = [r["id"] for r in rows if r["status"] == "confirmed"]
    write_json(args.out, {
        "schema": SCHEMA,
        "issue": declaration["issue"],
        "first_check_sha256": sha256_file(args.first_check),
        "refits_sha256": sha256_file(args.refits),
        "refit_check_sha256": sha256_file(args.refit_check),
        "declaration_sha256": sha256_file(args.declaration),
        "acceptance": first_check["acceptance"],
        "claims": "a confirmed feature is a primitive that describes the acquired surface within the tolerance on "
                  "held-out vertices; it is not a dimension of the specimen, whose scale is an owner instruction",
        "confirmed": len(confirmed),
        "features": len(rows),
        "confirmed_by_first_check": [r["id"] for r in rows if r.get("by") == "first check"],
        "confirmed_by_declared_refit": [r["id"] for r in rows if r.get("by") == "declared re-fit"],
        "need_a_contributed_measurement": [r["id"] for r in rows if r["status"] != "confirmed"],
        "rows": rows,
    })
    print(f"{len(confirmed)} of {len(rows)} features confirmed")


if __name__ == "__main__":
    main()
