#!/usr/bin/env python3
"""Verdict sur les designations retenues par le triage du catalogue d'usine.

Le triage lexical retient des mots. Ce script leur applique un jugement declare,
et surtout **il ne fait pas confiance au jugement**. Le verdict est derive des
entrees, puis confronte a celui que le fichier annonce : toute divergence est une
erreur, pas une nuance. C'est la garde qui manquait aux criblages precedents, ou
un verdict pouvait rester ecrit apres que ses raisons avaient change.

Trois conditions pour qu'une designation merite une fiche :

1. le titane doit ameliorer la matiere d'origine — la grille compare, elle ne
   juge pas dans l'absolu ;
2. la piece ne doit pas tomber dans un domaine presume critique ;
3. elle doit appartenir a au moins une des trois familles ou l'additif gagne.

Aucune n'est suffisante seule, et la premiere est celle qu'on oublie.
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
    """Erreur controlee du verdict."""


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

    # Le triage lexical ne retient que ce que son vocabulaire reconnait. La
    # disposition, elle, couvre les 1 026 designations : c'est elle qui porte le
    # denombrement de reference pour tout ce qui a ete juge a la main, `muffler`
    # et `y-piece` compris, que le vocabulaire avait manques.
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
            "designations retenues non jugees, le verdict ne couvre pas le "
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
            "verdict declare incoherent avec ses entrees: " + " ; ".join(disagreements)
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
        print(f"verdict a jour: {report['designations_to_open']} fiches a ouvrir")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(
        f"{report['designations_judged']} designations jugees, "
        f"{report['designations_to_open']} meritent une fiche "
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
