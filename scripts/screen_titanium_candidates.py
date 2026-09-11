#!/usr/bin/env python3
"""Classement des pieces du catalogue pour un premier tirage titane.

La decision 0005 a montre ce qui arrive quand une piece est retenue par
elimination plutot que par critere. Ce script fait l'inverse : il applique
mecaniquement la grille ecrite de `docs/TITANIUM.md` et les trois familles ou
l'additif gagne, a **toutes** les fiches du catalogue, et publie le classement.

Les entrees sont des jugements declares du depot, pas des mesures. Contredire
une case change le rang, et c'est le but : le classement est refutable ligne a
ligne.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Plafond de service du Ti-6Al-4V, limite par le fluage. Au-dela, la reponse
# n'est plus un autre dessin mais un autre metal.
TI64_CREEP_CEILING_C = 400.0

# Nuance quasi-alpha a route LPBF publiee, retenue comme echappatoire haute
# temperature du criblage et non comme choix acquis.
TI6242_CEILING_C = 550.0

# Classes de securite qu'un premier tirage metal non qualifie ne peut pas viser.
EXCLUDED_SAFETY_CLASSES = ("prohibited_pending_engineering", "safety_critical")


class ScreenError(RuntimeError):
    """Erreur controlee du criblage."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_part(
    part_id: str,
    safety_class: str,
    judgement: dict[str, Any],
) -> dict[str, Any]:
    relevance = judgement["titanium_relevance"]
    counters = judgement["titanium_counter_indications"]
    families = judgement["additive_families"]
    temperature = float(judgement["peak_service_temperature_c"])

    relevance_count = sum(1 for value in relevance.values() if value)
    counter_count = sum(1 for value in counters.values() if value)

    disqualifiers: list[str] = []
    if safety_class in EXCLUDED_SAFETY_CLASSES:
        disqualifiers.append(
            f"classe de securite {safety_class} : hors de portee d'un premier "
            "tirage metal non qualifie"
        )
    if not families:
        disqualifiers.append(
            "n'appartient a aucune des trois familles ou l'additif gagne"
        )
    if temperature > TI6242_CEILING_C:
        disqualifiers.append(
            f"{temperature:.0f} C depasse meme le plafond quasi-alpha de "
            f"{TI6242_CEILING_C:.0f} C : cas nickel, pas titane"
        )
    if counters.get("needs_thermal_conductivity"):
        disqualifiers.append(
            "la fonction demande de conduire la chaleur, ce que le titane fait mal"
        )
    if counters.get("must_match_steel_stiffness"):
        disqualifiers.append(
            "la flexion doit rester celle d'une piece acier"
        )

    alloy_note = ""
    if temperature > TI64_CREEP_CEILING_C:
        alloy_note = (
            f"{temperature:.0f} C depasse le plafond de fluage du Ti-6Al-4V "
            f"({TI64_CREEP_CEILING_C:.0f} C) ; une nuance quasi-alpha serait "
            "necessaire"
        )

    score = relevance_count + len(families) - counter_count
    return {
        "part_id": part_id,
        "safety_class": safety_class,
        "score": score,
        "relevance_count": relevance_count,
        "counter_count": counter_count,
        "additive_families": families,
        "peak_service_temperature_c": temperature,
        "temperature_basis": judgement["temperature_basis"],
        "interfaces_to_measure": judgement["interfaces_to_measure"],
        "eligible": not disqualifiers,
        "disqualifiers": disqualifiers,
        "alloy_note": alloy_note,
        "reason": judgement["reason"],
        "variant_of": judgement.get("variant_of"),
    }


def run(inputs: Path, catalog: Path) -> dict[str, Any]:
    screen = load_json(inputs)
    judgements = screen["parts"]

    records = {}
    for path in sorted(catalog.glob("*.json")):
        record = load_json(path)
        records[record["part_id"]] = record

    missing = set(records) - set(judgements)
    if missing:
        raise ScreenError(
            "fiches non jugees, le criblage ne couvre pas le catalogue: "
            + ", ".join(sorted(missing))
        )
    unknown = set(judgements) - set(records)
    if unknown:
        raise ScreenError("jugements sans fiche: " + ", ".join(sorted(unknown)))

    scored = [
        score_part(
            part_id,
            records[part_id]["classification"]["safety_class"],
            judgement,
        )
        for part_id, judgement in judgements.items()
    ]
    scored.sort(key=lambda entry: (entry["eligible"], entry["score"]), reverse=True)

    # Une fiche titane derivee d'une fiche d'un autre metal decrit la meme
    # geometrie. Dans un criblage titane, c'est la variante titane qui
    # concourt ; la fiche d'origine reste au classement, signalee.
    superseded = {
        entry["variant_of"] for entry in scored if entry.get("variant_of")
    }
    for entry in scored:
        if entry["part_id"] in superseded:
            entry["eligible"] = False
            entry["disqualifiers"].append(
                "une variante titane de la meme geometrie est fichee separement "
                "et concourt a sa place"
            )

    eligible = [entry for entry in scored if entry["eligible"]]
    winner = eligible[0] if eligible else None
    contested = (
        len(eligible) > 1 and eligible[0]["score"] == eligible[1]["score"]
    )

    return {
        "schema_version": "1.0.0",
        "screen_id": screen["screen_id"],
        "authority": screen["authority"],
        "grid_source": screen["grid_source"],
        "parts_screened": len(scored),
        "eligible_count": len(eligible),
        "selected": winner["part_id"] if winner else None,
        "selection_is_contested": contested,
        "selection_rule": (
            "score = criteres de pertinence titane + familles additives "
            "- contre-indications, apres elimination par la classe de securite, "
            "l'absence de famille additive, la temperature et les deux "
            "contre-indications redhibitoires"
        ),
        "ranking": scored,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs",
        type=Path,
        default=ROOT / "catalog/manufacturing/titanium-am-screen-inputs.json",
    )
    parser.add_argument("--catalog", type=Path, default=ROOT / "catalog/parts")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = run(args.inputs, args.catalog)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not args.output.exists():
            raise SystemExit(f"absent:{args.output}")
        if args.output.read_text(encoding="utf-8") != text:
            raise SystemExit(f"perime:{args.output}")
        print(f"criblage titane a jour: {report['selected']}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"{report['parts_screened']} fiches criblees, {report['eligible_count']} eligibles")
    for entry in report["ranking"][:6]:
        mark = "OK " if entry["eligible"] else "   "
        print(f"  {mark}{entry['score']:+d}  {entry['part_id']}")
    print(f"retenue: {report['selected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
