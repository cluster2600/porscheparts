#!/usr/bin/env python3
"""Rend le tableau des pieces du README depuis les fiches du catalogue.

La page d'accueil annoncait 31 fiches sans en nommer une seule : il fallait
ouvrir `catalog/parts/` pour savoir ce que le depot contient. Un tableau ecrit
a la main aurait derive des la fiche suivante, alors celui-ci est engendre.

    python3 scripts/render_parts_table.py --write   # reecrit le bloc du README
    python3 scripts/render_parts_table.py --check   # echoue s'il a derive

`--check` tourne dans `make check` : le tableau ne peut pas mentir sur le
statut d'une piece plus longtemps qu'un commit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FICHES = ROOT / "catalog" / "parts"
README = ROOT / "README.md"

DEBUT = "<!-- pieces:debut - engendre par scripts/render_parts_table.py -->"
FIN = "<!-- pieces:fin -->"

# Ordre de lecture, pas ordre alphabetique : on descend du moteur vers les
# accessoires, parce que c'est la ou le depot a mis son travail.
SYSTEMES = [
    ("ENG", "Moteur, admission et refroidissement"),
    ("TURBOCHARGER", "Turbocompresseur"),
    ("EXH", "Échappement"),
    ("BODY", "Carrosserie"),
    ("INT", "Habitacle"),
    ("ELEC", "Éclairage"),
    ("WHL", "Roues"),
]

STATUTS = {
    "prohibited_pending_engineering": "**interdit en l'état**",
    "safety_critical": "**critique pour la sécurité**",
    "functional": "fonctionnel",
    "non_critical": "non critique",
}

PROCEDES = {"undecided": "à décider"}


def court(texte: str, limite: int) -> str:
    """Coupe sans mentir : on prefere une troncature visible a un resume."""
    texte = texte.strip()
    return texte if len(texte) <= limite else texte[: limite - 1].rstrip(" ,;") + "…"


def matiere(fiche: dict) -> str:
    m = fiche["manufacturing"]["material"]
    valeur = m.get("grade") or m.get("family") or "non déterminée"
    # Le premier point-virgule separe la nuance de ses reserves ; la colonne
    # « statut » porte deja le fait que rien n'est qualifie.
    return court(valeur.split(";")[0], 40)


def lignes() -> list[str]:
    fiches = []
    for chemin in sorted(FICHES.glob("*.json")):
        d = json.loads(chemin.read_text(encoding="utf-8"))
        fiches.append((chemin, d))

    connus = {cle for cle, _ in SYSTEMES}
    inconnus = sorted({d["part_id"].split("-")[1] for _, d in fiches} - connus)
    if inconnus:
        raise SystemExit(
            f"systeme(s) sans intitule dans SYSTEMES : {', '.join(inconnus)}"
        )

    out = [DEBUT, ""]
    for cle, intitule in SYSTEMES:
        groupe = [(c, d) for c, d in fiches if d["part_id"].split("-")[1] == cle]
        if not groupe:
            continue
        out += [f"**{intitule}**", "",
                "| pièce | matière candidate | procédé | statut |",
                "|---|---|---|---|"]
        for chemin, d in groupe:
            nom = court(d["name"].split(",")[0], 46)
            rel = chemin.relative_to(ROOT).as_posix()
            proc = d["manufacturing"]["preferred_process"]
            out.append(f"| [{nom}]({rel}) | {matiere(d)} | "
                       f"{PROCEDES.get(proc, proc)} | "
                       f"{STATUTS[d['classification']['safety_class']]} |")
        out.append("")

    compte = len(fiches)
    interdites = sum(
        1 for _, d in fiches
        if d["classification"]["safety_class"] == "prohibited_pending_engineering"
    )
    out += [f"*{compte} fiches, dont {interdites} interdites en l'état et aucune "
            "libérée. Les dossiers de conception correspondants sont dans "
            "[`docs/993/`](docs/993/). Tableau engendré par "
            "`scripts/render_parts_table.py`, vérifié par `make check`.*",
            "", FIN]
    return out


def bloc() -> str:
    return "\n".join(lignes())


def remplace(texte: str, neuf: str) -> str:
    if DEBUT not in texte or FIN not in texte:
        raise SystemExit(f"marqueurs {DEBUT} / {FIN} absents de README.md")
    avant = texte.split(DEBUT)[0]
    apres = texte.split(FIN, 1)[1]
    return avant + neuf + apres


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()

    texte = README.read_text(encoding="utf-8")
    attendu = remplace(texte, bloc())

    if a.write:
        if attendu != texte:
            README.write_text(attendu, encoding="utf-8")
            print("README.md  tableau des pieces reecrit")
        else:
            print("README.md  tableau des pieces deja a jour")
        return 0

    if attendu != texte:
        print("ECHEC  le tableau des pieces du README ne correspond plus aux "
              "fiches de catalog/parts/.\n"
              "       relancer : python3 scripts/render_parts_table.py --write",
              file=sys.stderr)
        return 1
    print("OK   README.md, tableau des pieces conforme aux fiches du catalogue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
