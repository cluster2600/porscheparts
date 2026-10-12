#!/usr/bin/env python3
"""Planche de contrôle issue exclusivement des captures géométriques PicoGK F13."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from annotate_picogk_visualization_f11 import cropped_capture, font, sha256

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "work/911-917-picogk-f13"
VIEWS = {
    "top": "01 / DESSUS — axe moteur corrigé",
    "isometric": "02 / ASSEMBLAGE — cloche, boîte-pont, turbos, cardans",
    "full-top": "03 / ESSIEUX — moyeux avant indépendants ; transmission arrière",
    "side": "04 / PROFIL — position dans la caisse hypothétique",
}


def validate_report(report):
    if report["phase"] != "F13" or any(report["release_gates"].values()):
        raise ValueError("rapport F13 attendu, sans validation physique déclarée")
    if report["scope"]["turbo_count"] != 2 or report["scope"]["rear_halfshaft_count"] != 2:
        raise ValueError("deux turbos et deux demi-arbres requis")


def panel(name, width, height):
    capture = cropped_capture(OUTPUT / f"picogk-mechanical-f13-{name}.tga")
    result = Image.new("RGB", (width, height), "#f8fafc")
    fitted = ImageOps.contain(capture, (width - 20, height - 20), Image.Resampling.LANCZOS)
    result.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    return result


def main():
    report = json.loads((OUTPUT / "picogk-mechanical-report-f13.json").read_text())
    validate_report(report)
    paths = []
    for name, title in VIEWS.items():
        canvas = Image.new("RGB", (1800, 1360), "#f8fafc")
        draw = ImageDraw.Draw(canvas)
        draw.text((55, 30), "911 / 917 — ASSEMBLAGE PICO GK F13", fill="#0f172a", font=font(34, bold=True))
        draw.text((55, 82), title, fill="#334155", font=font(25, bold=True))
        canvas.paste(panel(name, 1700, 1050), (50, 125))
        draw.text((55, 1190), "GRIS : scan moteur    VIOLET : boîte-pont    ORANGE : 2 turbos    VERT : demi-arbres + joints", fill="#334155", font=font(23, bold=True))
        draw.text((55, 1235), "ROUGE : interférences berceau/cardans et lignes de référence des axes", fill="#b91c1c", font=font(23, bold=True))
        draw.text((55, 1292), "Boîte, turbos et trains : schémas d'implantation. Interfaces, échelle du scan et tenue à 1 600 ch non validées.", fill="#475569", font=font(21))
        destination = OUTPUT / f"picogk-mechanical-f13-{name}.png"
        canvas.save(destination)
        paths.append(destination)

    board = Image.new("RGB", (2400, 2090), "#0f172a")
    draw = ImageDraw.Draw(board)
    angle = report["alignment"]["old_axis_deviation_deg"]
    draw.text((55, 34), "911 / 917 — IMPLANTATION MÉCANIQUE CORRIGÉE", fill="white", font=font(41, bold=True))
    draw.text((55, 93), f"PicoGK F13   /   rotation parasite corrigée : {angle:.2f}°   /   moteur aligné sur X véhicule", fill="#cbd5e1", font=font(27))
    for name, x in (("top", 55), ("isometric", 1230)):
        draw.text((x, 165), VIEWS[name], fill="white", font=font(23, bold=True))
        board.paste(panel(name, 1115, 925), (x, 210))
    legend = [("#94a3b8", "SCAN MOTEUR ALIGNÉ"), ("#7c3aed", "BOÎTE + DIFFÉRENTIEL"),
              ("#ea580c", "DEUX TURBOS"), ("#16a34a", "DEMI-ARBRES + JOINTS")]
    for index, (colour, label) in enumerate(legend):
        x = 60 + index * 585
        draw.rectangle((x, 1170, x + 30, 1200), fill=colour)
        draw.text((x + 42, 1171), label, fill="white", font=font(22, bold=True))
    draw.text((55, 1252), VIEWS["full-top"], fill="white", font=font(25, bold=True))
    board.paste(panel("full-top", 2290, 570), (55, 1300))
    draw.rounded_rectangle((55, 1900, 2345, 2045), radius=14, fill="#1e293b", outline="#ef4444", width=3)
    draw.text((80, 1920), "INTERFÉRENCE À TRAITER : les demi-arbres recoupent les corridors de structure F12.", fill="#fecaca", font=font(26, bold=True))
    draw.text((80, 1965), "Boîte et turbos schématiques : produit, interfaces et capacité 1 600 ch à définir. Suspension détaillée absente.", fill="#cbd5e1", font=font(24))
    draw.text((80, 2005), "Recalage géométrique du scan vérifié ; échelle et repère mécanique physique encore à mesurer.", fill="#cbd5e1", font=font(24))
    destination = OUTPUT / "picogk-mechanical-engineering-board-f13.png"
    board.save(destination)
    paths.append(destination)
    manifest = {"phase": "F13", "status": "native_picogk_captures_with_text_only_annotation",
                "images": [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path)} for path in paths],
                "vdb": [{"file": p.name, "sha256": sha256(p)} for p in sorted(OUTPUT.glob("*-f13.vdb"))]}
    (OUTPUT / "image-manifest-f13.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(destination.relative_to(ROOT))


if __name__ == "__main__":
    main()
