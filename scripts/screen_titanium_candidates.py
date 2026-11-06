#!/usr/bin/env python3
"""Rank catalogue parts for a first titanium print run.

Decision 0005 showed what happens when a part is chosen by elimination rather
than by criterion. This script does the opposite: it mechanically applies the
written grid of `docs/TITANIUM.md` and the three families where additive wins
to **every** record in the catalogue, and publishes the ranking.

The inputs are judgements declared in the repository, not measurements.
Contradicting a cell changes the rank, and that is the point: the ranking is
falsifiable line by line.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Ti-6Al-4V service ceiling, limited by creep. Beyond it, the answer is not a
# different design but a different metal.
TI64_CREEP_CEILING_C = 400.0

# Near-alpha grade with a published LPBF route, kept as the screening's
# high-temperature escape hatch, not as a settled choice.
TI6242_CEILING_C = 550.0

# "When titanium is not relevant", docs/TITANIUM.md.
#
# Two of these conditions are physical impossibilities: if the part's function
# is to conduct heat, or if its bending must stay that of a steel part, no
# treatment changes anything.
ABSOLUTE_REFUSALS = {
    "needs_thermal_conductivity": (
        "la fonction demande de conduire la chaleur, ce que le titane fait mal"
    ),
    "must_match_steel_stiffness": (
        "la flexion doit rester celle d'une piece acier"
    ),
}

# The others are conditions to clear, and the grid text says so: "**untreated**
# sliding contact", "**uncontrolled** galvanic couple". Those two qualifiers are
# what matters, and SAFETY.md lists galling and galvanic-corrosion prevention
# among the metal's minimum requirements — so as work to do, not as a reason to
# abandon. A condition blocks while no mitigation is declared; a declared
# mitigation turns it into a requirement carried on the route.
MITIGABLE_CONDITIONS = {
    "galling_or_repeated_threads": (
        "contact glissant ou filetage repris a chaque depose : le titane grippe "
        "tant qu'aucun traitement de surface, insert acier ou bague n'est prevu"
    ),
    "uncontrolled_galvanic_couple": (
        "couple galvanique avec l'aluminium ou le magnesium, tant qu'aucune "
        "isolation, aucun revetement ni aucun mastic n'est prevu"
    ),
    "differential_expansion_with_alloy_mate": (
        "dilatation differentielle avec la piece sur laquelle celle-ci se "
        "boulonne, tant que la conception du plan de joint ne la reprend pas"
    ),
}

# Simple, easily machined shape: not an impossibility, a pointlessness. It
# lowers the score and prohibits nothing.
ECONOMIC_PENALTY = "simple_machinable_shape"

# Safety classes an unqualified first metal print run cannot target.
EXCLUDED_SAFETY_CLASSES = ("prohibited_pending_engineering", "safety_critical")


class ScreenError(RuntimeError):
    """Controlled screening error."""


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
    raw_temperature = judgement["peak_service_temperature_c"]
    temperature = None if raw_temperature is None else float(raw_temperature)
    if isinstance(raw_temperature, bool) or (temperature is not None and not math.isfinite(temperature)):
        raise ScreenError(f"{part_id}: temperature must be finite or explicitly unknown")

    relevance_count = sum(1 for value in relevance.values() if value)
    counter_count = sum(1 for value in counters.values() if value)

    disqualifiers: list[str] = []
    if temperature is None:
        disqualifiers.append("service temperature unknown: thermal screening remains blocked")
    if safety_class in EXCLUDED_SAFETY_CLASSES:
        disqualifiers.append(
            f"classe de securite {safety_class} : hors de portee d'un premier "
            "tirage metal non qualifie"
        )
    if not families:
        disqualifiers.append(
            "n'appartient a aucune des trois familles ou l'additif gagne"
        )
    if temperature is not None and temperature > TI6242_CEILING_C:
        disqualifiers.append(
            f"{temperature:.0f} C depasse meme le plafond quasi-alpha de "
            f"{TI6242_CEILING_C:.0f} C : cas nickel, pas titane"
        )
    # The five entries of "when titanium is not relevant" are refusals, not
    # penalties. Making only two of them disqualifying was unfaithful to the
    # written grid: galling and the galvanic couple rule titanium out as surely
    # as conductivity.
    for name, statement in ABSOLUTE_REFUSALS.items():
        if counters.get(name):
            disqualifiers.append(statement)

    mitigations = judgement.get("mitigations", {})
    carried: list[dict[str, str]] = []
    for name, statement in MITIGABLE_CONDITIONS.items():
        if not counters.get(name):
            continue
        parade = (mitigations.get(name) or "").strip()
        # A mitigation that admits it is unresolved ("non resolu") is not a
        # mitigation. It happened on the cover's titanium/magnesium couple: the
        # text described the problem and counted as its solution.
        if parade and "non resolu" in parade.lower():
            raise ScreenError(
                f"contradictory mitigation on {part_id}/{name}: a condition "
                "declared unresolved must not carry a mitigation, it must "
                "block"
            )
        if parade:
            carried.append({"condition": name, "mitigation": parade})
        else:
            disqualifiers.append(statement)

    # Criterion missing until 11 September 2026, and it was the one that really
    # decided. "Problematic corrosion **with the original material**": the grid
    # compares, it does not judge in the absolute. An aluminum intake manifold
    # at 80 C gains nothing from titanium, which is denser and more expensive
    # with no useful thermal or corrosion benefit. Without this question, the
    # screening scored words instead of comparing metals.
    incumbent = judgement.get("incumbent_material", {})
    if not incumbent.get("titanium_improves_on_it"):
        disqualifiers.append(
            "le titane n'ameliore pas la matiere d'origine"
            + (f" ({incumbent['reason']})" if incumbent.get("reason") else "")
        )

    alloy_note = ""
    if temperature is not None and temperature > TI64_CREEP_CEILING_C:
        alloy_note = (
            f"{temperature:.0f} C depasse le plafond de fluage du Ti-6Al-4V "
            f"({TI64_CREEP_CEILING_C:.0f} C) ; une nuance quasi-alpha serait "
            "necessaire"
        )

    # A cleared condition remains a requirement: it no longer costs score, but
    # it is carried on the route and must be met by the supplier.
    unresolved = counter_count - len(carried)
    score = relevance_count + len(families) - unresolved
    return {
        "part_id": part_id,
        "safety_class": safety_class,
        "score": score,
        "relevance_count": relevance_count,
        "counter_count": counter_count,
        "unresolved_counter_count": unresolved,
        "carried_requirements": carried,
        "additive_families": families,
        "peak_service_temperature_c": temperature,
        "temperature_basis": judgement["temperature_basis"],
        "interfaces_to_measure": judgement["interfaces_to_measure"],
        "eligible": not disqualifiers,
        "disqualifiers": disqualifiers,
        "alloy_note": alloy_note,
        "reason": judgement["reason"],
        "incumbent_material": incumbent,
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
            "unjudged records, the screening does not cover the catalogue: "
            + ", ".join(sorted(missing))
        )
    unknown = set(judgements) - set(records)
    if unknown:
        raise ScreenError("judgements without a record: " + ", ".join(sorted(unknown)))

    scored = [
        score_part(
            part_id,
            records[part_id]["classification"]["safety_class"],
            judgement,
        )
        for part_id, judgement in judgements.items()
    ]
    scored.sort(key=lambda entry: (entry["eligible"], entry["score"]), reverse=True)

    # A titanium record derived from another metal's record describes the same
    # geometry. In a titanium screening the titanium variant competes; the
    # original record stays in the ranking, flagged.
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
            "- contre-indications non levees, apres elimination par la classe de "
            "securite, l'absence de famille additive, la temperature, les deux "
            "impossibilites physiques et toute condition laissee sans parade"
        ),
        "scope_warning": (
            "Ce classement porte sur les fiches de catalog/parts, pas sur la "
            "voiture. Le catalogue d'usine 993 compte 6 259 references "
            "distinctes ; les fiches en couvrent une fraction de pourcent. "
            "Une piece absente d'ici n'a pas ete jugee, elle n'a pas ete vue. "
            "Le balayage large est le triage PET, pas ce criblage."
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
        print(f"titanium screening up to date: {report['selected']}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"{report['parts_screened']} records screened, {report['eligible_count']} eligible")
    for entry in report["ranking"][:6]:
        mark = "OK " if entry["eligible"] else "   "
        print(f"  {mark}{entry['score']:+d}  {entry['part_id']}")
    print(f"selected: {report['selected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
