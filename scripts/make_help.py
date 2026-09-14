#!/usr/bin/env python3
"""Rend `make help` depuis les annotations du Makefile, et garde la liste honnete.

Le Makefile porte 210 cibles, dont la grande majorite pilote la ligne 917/935
qu'ARCHIVE.md declare retiree comme produit. Une liste ecrite a la main aurait
melange les deux et aurait vieilli au premier ajout de cible.

Chaque cible active porte donc une annotation, sur la ligne qui la precede :

    #> section | ce que fait la cible
    ma-cible:

    python3 scripts/make_help.py            # affiche l'aide
    python3 scripts/make_help.py --check    # echoue si une cible n'est pas annotee

`--check` tourne dans `make check` : une cible active ajoutee sans annotation
fait tomber la suite, ce qui est la seule facon qu'une aide reste complete.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"

# Ordre de lecture : ce qu'on fait tous les jours d'abord, l'archive a la fin.
SECTIONS = [
    ("verifier", "Verifier le depot"),
    ("catalogue", "Catalogue, fiches et jumeaux"),
    ("993", "993 : suralimentation et cas de calcul"),
    ("conteneurs", "Images de calcul reproductibles"),
    ("archive", "Ligne 917/935, archivee — voir ARCHIVE.md"),
]

CIBLE = re.compile(r"^([a-zA-Z0-9_.-]+):")
NOTE = re.compile(r"^#> *([^|]+?) *\| *(.+?) *$")
# Une cible 917-* est archivee par construction : elle n'a pas a etre annotee.
ARCHIVEE = re.compile(r"^917-")


def lire() -> tuple[dict[str, list[tuple[str, str]]], set[str], set[str]]:
    """Annotations par section, cibles annotees, cibles declarees .PHONY."""
    texte = MAKEFILE.read_text(encoding="utf-8")
    phony: set[str] = set()
    for ligne in re.sub(r"\\\n\s*", " ", texte).split("\n"):
        if ligne.startswith(".PHONY:"):
            phony |= set(ligne[len(".PHONY:"):].split())

    par_section: dict[str, list[tuple[str, str]]] = {c: [] for c, _ in SECTIONS}
    annotees: set[str] = set()
    note: tuple[str, str] | None = None
    for ligne in texte.split("\n"):
        if m := NOTE.match(ligne):
            note = (m.group(1), m.group(2))
            continue
        if note and (m := CIBLE.match(ligne)):
            section, desc = note
            if section not in par_section:
                raise SystemExit(
                    f"section inconnue « {section} » sur la cible {m.group(1)} ; "
                    f"sections admises : {', '.join(c for c, _ in SECTIONS)}"
                )
            par_section[section].append((m.group(1), desc))
            annotees.add(m.group(1))
        note = None
    return par_section, annotees, phony


def affiche() -> int:
    par_section, _, _ = lire()
    n917 = len(set(re.findall(r"^(917-[a-zA-Z0-9_.-]+):", MAKEFILE.read_text(
        encoding="utf-8"), re.M)))
    print("porscheparts — cibles documentees.  Detail : README.md\n")
    for cle, titre in SECTIONS:
        cibles = par_section[cle]
        if not cibles:
            continue
        print(f"  {titre}")
        for nom, desc in sorted(cibles):
            print(f"    {nom:<34} {desc}")
        print()
    print(f"  {n917} cibles nommees 917-* ne sont pas listees ici : elles pilotent")
    print("  un travail archive, retire comme produit et conserve comme regression")
    print("  numerique. Les lire : ARCHIVE.md. Les lister : make help-917")
    return 0


def verifie() -> int:
    _, annotees, phony = lire()
    manquantes = sorted(t for t in phony if not ARCHIVEE.match(t) and t not in annotees)
    if manquantes:
        print("ECHEC  cible(s) active(s) sans annotation « #> section | description » :",
              file=sys.stderr)
        for t in manquantes:
            print(f"       {t}", file=sys.stderr)
        print("       sans elle, la cible est invisible dans make help.", file=sys.stderr)
        return 1
    fantomes = sorted(t for t in annotees if t not in phony)
    if fantomes:
        print(f"ECHEC  cible(s) annotee(s) mais absente(s) de .PHONY : "
              f"{', '.join(fantomes)}", file=sys.stderr)
        return 1
    print(f"OK   Makefile, {len(annotees)} cibles actives annotees, aucune orpheline")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    return verifie() if ap.parse_args().check else affiche()


if __name__ == "__main__":
    raise SystemExit(main())
