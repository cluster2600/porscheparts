#!/usr/bin/env python3
"""Rend une page de description par piece, depuis la fiche du catalogue.

Le tableau du README renvoyait vers `catalog/parts/*.json` : lisible par un
outil, pas par un lecteur. Chaque piece a maintenant sa page dans `docs/pieces/`,
engendree depuis la meme fiche, avec ses sources, ses preuves et ses images.

    python3 scripts/render_part_pages.py --write   # (re)ecrit les pages
    python3 scripts/render_part_pages.py --check   # echoue si une page a derive

`--check` tourne dans `make check` : une page ne peut pas contredire sa fiche
plus longtemps qu'un commit. Rien n'est resume ni reformule : les valeurs sont
recopiees, et un champ absent est ecrit comme absent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_parts_table import PROCEDES, STATUTS  # noqa: E402

FICHES = ROOT / "catalog" / "parts"
PAGES = ROOT / "docs" / "pieces"
DOSSIERS = ROOT / "docs" / "993"
ENTETE = "<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->"


def lien(cible: Path, depuis: Path) -> str:
    """Chemin relatif de la page vers une cible du dépôt (les pages vivent dans docs/pieces/)."""
    remontee = [".."] * len(depuis.relative_to(ROOT).parts[:-1])
    return Path(*remontee).joinpath(cible.relative_to(ROOT)).as_posix()


def valeur(x) -> str:
    if x is None or x == [] or x == {}:
        return "non renseigné"
    if isinstance(x, bool):
        return "oui" if x else "non"
    if isinstance(x, list):
        return ", ".join(valeur(v) for v in x)
    if isinstance(x, dict):
        return " ; ".join(f"{k} : {valeur(v)}" for k, v in x.items())
    return str(x)


def tableau(page: Path, paires) -> list[str]:
    out = ["| champ | valeur |", "|---|---|"]
    for cle, brut in paires:
        texte = valeur(brut).replace("|", "\\|").replace("\n", " ")
        out.append(f"| {cle} | {texte} |")
    return out + [""]


def fichiers(page: Path, chemins, titre: str) -> list[str]:
    out = [f"**{titre}**", ""]
    if not chemins:
        return out + ["- aucun", ""]
    for rel in chemins:
        cible = ROOT / rel
        etat = "" if cible.exists() else " — *absent du dépôt*"
        out.append(f"- [`{rel}`]({lien(cible, page)}){etat}" if cible.exists() else f"- `{rel}`{etat}")
    return out + [""]


def images(part_id: str, page: Path) -> list[str]:
    dossier = ROOT / "parts" / part_id.lower()
    trouvees = sorted(dossier.rglob("*.png")) if dossier.is_dir() else []
    if not trouvees:
        return []
    out = ["## Images", ""]
    for img in trouvees[:6]:
        rel = img.relative_to(ROOT).as_posix()
        out += [f"![{img.stem}]({lien(img, page)})", "", f"*{rel}*", ""]
    return out


def dossiers_lies(part_id: str, page: Path) -> list[str]:
    if not DOSSIERS.is_dir():
        return []
    lies = [p for p in sorted(DOSSIERS.glob("*.md"))
            if part_id.lower() in p.read_text(encoding="utf-8", errors="replace").lower()]
    if not lies:
        return []
    return ["## Dossiers de conception", ""] + \
        [f"- [{p.stem}]({lien(p, page)})" for p in lies] + [""]


def page_markdown(fiche: dict, chemin_fiche: Path) -> str:
    part_id = fiche["part_id"]
    page = PAGES / f"{part_id.lower()}.md"
    classification = fiche.get("classification", {})
    fabrication = fiche.get("manufacturing", {})
    matiere = fabrication.get("material", {})
    geometrie = fiche.get("geometry", {})
    provenance = fiche.get("provenance", {})
    titane = fiche.get("titanium", {})
    validation = fiche.get("validation", {})
    statut = STATUTS.get(classification.get("safety_class"), classification.get("safety_class", "inconnu"))
    procede = fabrication.get("preferred_process", "inconnu")

    out = [ENTETE, "", f"# {fiche['name']}", "",
           f"**Statut : {statut}. Aucune pièce n'est libérée ; voir [SAFETY.md]({lien(ROOT / 'SAFETY.md', page)}).**", "",
           fiche.get("description", "").strip(), "",
           f"Fiche du catalogue : [`{chemin_fiche.relative_to(ROOT).as_posix()}`]({lien(chemin_fiche, page)})", ""]

    out += ["## Identité", ""]
    vehicule = fiche.get("vehicle", {})
    annees = vehicule.get("model_years", {})
    out += tableau(page, [
        ("identifiant", part_id),
        ("génération", vehicule.get("generation")),
        ("variantes", vehicule.get("variants")),
        ("années", f"{annees.get('from')} à {annees.get('to')}" if annees else None),
        ("références Porsche", vehicule.get("porsche_part_numbers")),
        ("catégorie", classification.get("category")),
        ("classe de sécurité", classification.get("safety_class")),
        ("usage prévu", classification.get("intended_use")),
    ])

    out += ["## Matière et fabrication", ""]
    out += tableau(page, [
        ("procédé préféré", PROCEDES.get(procede, procede)),
        ("procédés candidats", fabrication.get("candidate_processes")),
        ("famille de matière", matiere.get("family")),
        ("nuance", matiere.get("grade")),
        ("norme", matiere.get("standard")),
        ("exigences fournisseur", fabrication.get("supplier_requirements")),
        ("post-traitement", fabrication.get("post_processing")),
    ])
    if titane.get("applicable"):
        out += ["**Titane**", ""]
        out += tableau(page, [
            ("alliage", titane.get("alloy")),
            ("traitement thermique", titane.get("heat_treatment")),
            ("HIP", titane.get("hip_required")),
            ("surfaces usinées", titane.get("machined_surfaces")),
            ("inspection", titane.get("inspection")),
            ("isolation galvanique", titane.get("galvanic_isolation")),
            ("hypothèses de fatigue", titane.get("fatigue_assumptions")),
        ])

    out += ["## Géométrie", ""]
    out += tableau(page, [
        ("type de source", geometrie.get("source_type")),
        ("format du maître", geometrie.get("master_format")),
        ("unités", geometrie.get("units")),
        ("précision (mm)", geometrie.get("accuracy_mm")),
    ])
    maitre = geometrie.get("master_file")
    out += fichiers(page, [maitre] if maitre else [], "Fichier maître")
    out += fichiers(page, geometrie.get("derived_files") or [], "Fichiers dérivés")

    out += images(part_id, page)

    out += ["## Provenance et sources", ""]
    out += tableau(page, [("licence de la fiche", provenance.get("record_license"))])
    sources = provenance.get("sources") or []
    if sources:
        out += ["**Sources**", ""]
        for s in sources:
            titre = s.get("title") or s.get("id") or "source"
            url = s.get("url")
            note = s.get("note") or s.get("access") or ""
            ligne = f"- [{titre}]({url})" if url else f"- {titre}"
            out.append(f"{ligne}{' — ' + str(note) if note else ''}")
        out.append("")

    out += ["## Validation", ""]
    out += tableau(page, [
        ("statut", validation.get("status")),
        ("essais véhicule", validation.get("vehicle_tested")),
        ("revu par", validation.get("reviewed_by")),
        ("limites", validation.get("limitations") or validation.get("notes")),
    ])
    out += fichiers(page, validation.get("evidence") or [], "Preuves")

    out += dossiers_lies(part_id, page)

    out += ["---", "",
            "*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, "
            "vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*", ""]
    return "\n".join(out)


def attendues() -> dict[Path, str]:
    return {PAGES / f"{json.loads(c.read_text(encoding='utf-8'))['part_id'].lower()}.md":
            page_markdown(json.loads(c.read_text(encoding="utf-8")), c)
            for c in sorted(FICHES.glob("*.json"))}


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()

    pages = attendues()
    if a.write:
        PAGES.mkdir(parents=True, exist_ok=True)
        ecrites = 0
        for chemin, texte in pages.items():
            if not chemin.exists() or chemin.read_text(encoding="utf-8") != texte:
                chemin.write_text(texte, encoding="utf-8")
                ecrites += 1
        for orpheline in sorted(PAGES.glob("*.md")):
            if orpheline not in pages:
                orpheline.unlink()
                print(f"page orpheline supprimee : {orpheline.relative_to(ROOT)}")
        print(f"docs/pieces  {len(pages)} pages, {ecrites} reecrites")
        return 0

    manquantes = [c for c in pages if not c.exists()]
    derivees = [c for c, t in pages.items() if c.exists() and c.read_text(encoding="utf-8") != t]
    orphelines = [p for p in sorted(PAGES.glob("*.md")) if p not in pages] if PAGES.is_dir() else []
    if manquantes or derivees or orphelines:
        for chemin in manquantes:
            print(f"ECHEC  page absente : {chemin.relative_to(ROOT)}", file=sys.stderr)
        for chemin in derivees:
            print(f"ECHEC  page differente de sa fiche : {chemin.relative_to(ROOT)}", file=sys.stderr)
        for chemin in orphelines:
            print(f"ECHEC  page sans fiche : {chemin.relative_to(ROOT)}", file=sys.stderr)
        print("       relancer : python3 scripts/render_part_pages.py --write", file=sys.stderr)
        return 1
    print(f"OK   docs/pieces, {len(pages)} pages conformes aux fiches du catalogue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
