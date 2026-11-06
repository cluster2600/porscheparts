#!/usr/bin/env python3
"""Verdict on the designations retained by the factory-catalogue triage.

The lexical triage retains words. This script applies a declared judgement to
them, and above all **it does not trust the judgement**. The verdict is derived
from the inputs, then compared with the one the file announces: any divergence
is an error, not a nuance. That is the guard earlier screenings lacked, where a
verdict could stay written after its reasons had changed.

Three conditions for a designation to deserve a record:

1. titanium must improve on the original material — the grid compares, it does
   not judge in the absolute;
2. the part must not fall in a presumed safety-critical domain;
3. it must belong to at least one of the three families where additive wins.

None is sufficient alone, and the first is the one people forget.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_SAFETY_CLASSES = ("prohibited_pending_engineering", "safety_critical")
OPEN = "open_a_fiche"
REJECT = "reject"


class JudgementError(RuntimeError):
    """Controlled verdict error."""


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def derive(judgement: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if not judgement["titanium_improves_on_it"]:
        blockers.append("le titane n'ameliore pas la matiere d'origine")
    if judgement["presumed_safety_class"] in EXCLUDED_SAFETY_CLASSES:
        blockers.append(
            f"classe presumee {judgement['presumed_safety_class']}"
        )
    if not judgement["additive_families"]:
        blockers.append("aucune des trois familles ou l'additif gagne")
    return (REJECT if blockers else OPEN), blockers


def run(triage_path: Path, judgements_path: Path, disposition_path: Path) -> dict[str, Any]:
    triage = load(triage_path)
    judgements = load(judgements_path)["parts"]

    # The lexical triage retains only what its vocabulary recognizes. The
    # disposition covers all 1,026 designations: it carries the reference count
    # for everything judged by hand, including `muffler` and `y-piece`, which the
    # vocabulary had missed.
    retained = {item["description"]: item for item in triage["shortlist"]}
    if disposition_path.exists():
        for row in load(disposition_path)["rows"]:
            description = row["description"]
            if description in judgements and description not in retained:
                retained[description] = {
                    "description": description,
                    "reference_count": row["reference_count"],
                    "illustrations": [],
                }
    missing = sorted(set(retained) - set(judgements))
    if missing:
        raise JudgementError(
            "retained designations not judged, the verdict does not cover the "
            "triage: " + ", ".join(missing)
        )

    rows = []
    disagreements = []
    for description, item in retained.items():
        judgement = judgements[description]
        verdict, blockers = derive(judgement)
        if verdict != judgement["verdict"]:
            disagreements.append(
                f"{description}: declare {judgement['verdict']}, derive {verdict}"
            )
        rows.append(
            {
                "description": description,
                "reference_count": item["reference_count"],
                "illustrations": item["illustrations"],
                "incumbent_material": judgement["incumbent_material"],
                "titanium_improves_on_it": judgement["titanium_improves_on_it"],
                "presumed_safety_class": judgement["presumed_safety_class"],
                "additive_families": judgement["additive_families"],
                "verdict": verdict,
                "blockers": blockers,
                "reason": judgement["reason"],
            }
        )

    if disagreements:
        raise JudgementError(
            "declared verdict incoherent with its inputs: " + " ; ".join(disagreements)
        )

    rows.sort(
        key=lambda row: (row["verdict"] == OPEN, row["reference_count"]), reverse=True
    )
    to_open = [row for row in rows if row["verdict"] == OPEN]

    return {
        "schema_version": "1.0.0",
        "screen_id": "PET-CANDIDATE-VERDICT",
        "authority": "derived_from_declared_judgements_not_from_measurement",
        "rule": (
            "merite une fiche si le titane ameliore la matiere d'origine, si la "
            "piece n'est pas d'un domaine presume critique, et si elle appartient "
            "a une des trois familles additives"
        ),
        "designations_judged": len(rows),
        "designations_to_open": len(to_open),
        "references_under_designations_to_open": sum(
            row["reference_count"] for row in to_open
        ),
        "scope_warning": triage["limits"],
        "backlog": to_open,
        "ranking": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--triage",
        type=Path,
        default=ROOT
        / "twins/993-exhaust-tip-ti-f0/evidence/selection/pet-part-titanium-triage.json",
    )
    parser.add_argument(
        "--judgements",
        type=Path,
        default=ROOT / "catalog/manufacturing/pet-candidate-judgements.json",
    )
    parser.add_argument(
        "--disposition",
        type=Path,
        default=ROOT
        / "twins/993-exhaust-tip-ti-f0/evidence/selection/pet-full-disposition.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = run(args.triage, args.judgements, args.disposition)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not args.output.exists():
            raise SystemExit(f"absent:{args.output}")
        if args.output.read_text(encoding="utf-8") != text:
            raise SystemExit(f"perime:{args.output}")
        print(f"verdict up to date: {report['designations_to_open']} records to open")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(
        f"{report['designations_judged']} designations judged, "
        f"{report['designations_to_open']} deserve a record "
        f"({report['references_under_designations_to_open']} references)"
    )
    for row in report["backlog"]:
        print(
            f"  {row['reference_count']:3d}x  {row['description']:22s} "
            f"{row['incumbent_material']:20s} {','.join(row['illustrations'][:3])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
