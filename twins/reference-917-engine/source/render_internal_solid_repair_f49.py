#!/usr/bin/env python3
"""Produit deux planches F49 honnêtes depuis les vues publiques F47.

Les vues de géométrie restent celles des candidats F47 soumis à l'audit F49;
aucun STEP privé n'est importé et aucune géométrie de substitution n'est créée.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def make_plate(source: Path, target: Path, title: str, details: list[str]) -> None:
    image = Image.open(source).convert("RGB")
    top, bottom = 150, 150
    canvas = Image.new("RGB", (image.width, image.height + top + bottom), "#101820")
    canvas.paste(image, (0, top))
    draw = ImageDraw.Draw(canvas)
    draw.text((70, 30), title, font=font(48, True), fill="#f2f5f7")
    draw.text((70, 92), "CANDIDATS STEP REJETES — BOP non nul — AUCUNE IMPRESSION AUTORISEE", font=font(26, True), fill="#ff6b5f")
    y = image.height + top + 28
    for line in details:
        draw.text((70, y), line, font=font(24), fill="#d6dde2")
        y += 34
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.project_root.resolve()
    source = root / "twins/reference-917-engine/evidence/f47-internal-brep"
    target = root / "twins/reference-917-engine/evidence/f49-solid"
    make_plate(
        source / "917-head-f47-2v-4v-four-views.png",
        target / "917-head-f49-scan-derived-exterior-four-views.png",
        "F49 · SCAN-DERIVED EXTERIOR · AUDIT 2V / 4V",
        [
            "Peau extérieure F43 non ovale : source privée SHA-256 38f8ed... inchangée.",
            "Ces vues montrent la géométrie F47 auditée, pas une nouvelle pièce libérée.",
            "2V : 8 défauts p-curve après STEP · 4V : 32 défauts de référence.",
        ],
    )
    make_plate(
        source / "917-head-f47-2v-4v-sections.png",
        target / "917-head-f49-2v-4v-sections.png",
        "F49 · COUPES 2V / 4V · CERCLES FONCTIONNELS",
        [
            "Coupes F47 utilisées pour localiser les fonctions; peau F43 non modifiée.",
            "Alésage, sièges, guides, bougie, conduits et huile restent des hypothèses F45/F47.",
            "Épaisseur globale, fatigue, thermique, fitment et évacuation poudre : non validés.",
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
