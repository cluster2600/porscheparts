#!/usr/bin/env python3
"""Render `make help` from the Makefile annotations, and keep the list honest.

The Makefile carries 210 targets, most of which drive the 917/935 line that
ARCHIVE.md declares retired as a product. A hand-written list would have mixed
the two and gone stale with the first new target.

Every active target therefore carries an annotation on the line above it:

    #> section | what the target does
    my-target:

    python3 scripts/make_help.py            # print the help
    python3 scripts/make_help.py --check    # fail if a target is not annotated

`--check` runs in `make check`: an active target added without an annotation
breaks the suite, which is the only way a help text stays complete.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"

# Reading order: what you do every day first, the archive last.
SECTIONS = [
    ("check", "Check the repository"),
    ("catalogue", "Catalogue, records and twins"),
    ("993", "993: forced induction and analysis cases"),
    ("containers", "Reproducible compute images"),
    ("archive", "917/935 line, archived — see ARCHIVE.md"),
]

CIBLE = re.compile(r"^([a-zA-Z0-9_.-]+):")
NOTE = re.compile(r"^#> *([^|]+?) *\| *(.+?) *$")
# A 917-* target is archived by construction: it need not be annotated.
ARCHIVEE = re.compile(r"^917-")


def lire() -> tuple[dict[str, list[tuple[str, str]]], set[str], set[str]]:
    """Annotations per section, annotated targets, targets declared .PHONY."""
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
                    f"unknown section \"{section}\" on target {m.group(1)}; "
                    f"allowed sections: {', '.join(c for c, _ in SECTIONS)}"
                )
            par_section[section].append((m.group(1), desc))
            annotees.add(m.group(1))
        note = None
    return par_section, annotees, phony


def affiche() -> int:
    par_section, _, _ = lire()
    n917 = len(set(re.findall(r"^(917-[a-zA-Z0-9_.-]+):", MAKEFILE.read_text(
        encoding="utf-8"), re.M)))
    print("porscheparts — documented targets.  Details: README.md\n")
    for cle, titre in SECTIONS:
        cibles = par_section[cle]
        if not cibles:
            continue
        print(f"  {titre}")
        for nom, desc in sorted(cibles):
            print(f"    {nom:<34} {desc}")
        print()
    print(f"  {n917} targets named 917-* are not listed here: they drive archived")
    print("  work, retired as a product and kept as a numerical regression.")
    print("  Read about them: ARCHIVE.md. List them: make help-917")
    return 0


def verifie() -> int:
    _, annotees, phony = lire()
    manquantes = sorted(t for t in phony if not ARCHIVEE.match(t) and t not in annotees)
    if manquantes:
        print("FAIL   active target(s) without a \"#> section | description\" annotation:",
              file=sys.stderr)
        for t in manquantes:
            print(f"       {t}", file=sys.stderr)
        print("       without it, the target is invisible in make help.", file=sys.stderr)
        return 1
    fantomes = sorted(t for t in annotees if t not in phony)
    if fantomes:
        print(f"FAIL   target(s) annotated but missing from .PHONY: "
              f"{', '.join(fantomes)}", file=sys.stderr)
        return 1
    print(f"OK   Makefile, {len(annotees)} active targets annotated, no orphans")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    return verifie() if ap.parse_args().check else affiche()


if __name__ == "__main__":
    raise SystemExit(main())
