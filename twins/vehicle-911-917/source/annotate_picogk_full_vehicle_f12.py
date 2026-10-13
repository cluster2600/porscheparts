#!/usr/bin/env python3
"""Convertit les captures PicoGK F12 en une planche d'encombrement lisible."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from annotate_picogk_visualization_f11 import cropped_capture, font, sha256


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "work" / "911-917-picogk-f12"
REPORT = OUTPUT / "picogk-full-vehicle-report-f12.json"
VIEWS = (
    ("side", "VUE LATÉRALE — moteur devant l'essieu arrière"),
    ("top", "VUE DE DESSUS — admissions et échangeur d'aileron"),
    ("powertrain", "GROUPE MOTOPROPULSEUR — coque masquée"),
    ("isometric", "VUE ISOMÉTRIQUE — maquette d'encombrement complète"),
)
LEGEND = (
    ("#e5e7eb", "scan moteur observé"),
    ("#f59e0b", "enveloppe moteur hypothétique"),
    ("#4f78a8", "coque documentaire / profil hypothétique"),
    ("#ef4444", "structure et cloison"),
    ("#8b5cf6", "réserve boîte historique, non sélectionnée"),
    ("#f97316", "turbos et échappements hypothétiques"),
    ("#06b6d4", "admissions et refroidissement hypothétiques"),
    ("#10b981", "aileron 930, plénum et échangeur hypothétiques"),
    ("#1f2937", "roues et essieux de réservation"),
)


def make_view(name: str, title: str, report: dict) -> Path:
    capture = cropped_capture(OUTPUT / f"picogk-full-vehicle-f12-{name}.tga")
    canvas = Image.new("RGB", (1600, 1200), "#f8fafc")
    draw = ImageDraw.Draw(canvas)
    draw.text((55, 34), "PORSCHE 911 / 917 — PICO GK F12", fill="#0f172a", font=font(34, bold=True))
    draw.text((55, 84), title, fill="#334155", font=font(24, bold=True))
    fitted = ImageOps.contain(capture, (1490, 760), Image.Resampling.LANCZOS)
    canvas.paste(fitted, ((1600 - fitted.width) // 2, 125 + (760 - fitted.height) // 2))

    checks = report["checks"]
    draw.text(
        (55, 910),
        f"PicoGK {report['kernel']['package_version']} • voxel {report['kernel']['voxel_size_mm']} mm • "
        f"scan {report['scope']['scan_triangle_count']:,} triangles • 9 couches VDB",
        fill="#334155",
        font=font(21, bold=True),
    )
    draw.text(
        (55, 950),
        f"Marge cloison: {checks['firewall_residual_above_requirement_mm']:.0f} mm au-delà de l'exigence — "
        "NON RÉSOLUE au voxel choisi",
        fill="#991b1b",
        font=font(21, bold=True),
    )
    for index, (colour, label) in enumerate(LEGEND):
        x = 55 + (index % 3) * 510
        y = 995 + (index // 3) * 44
        draw.rounded_rectangle((x, y, x + 25, y + 25), radius=4, fill=colour, outline="#334155")
        draw.text((x + 36, y - 2), label, fill="#334155", font=font(16))
    draw.text(
        (55, 1158),
        "TOUS LES SYSTÈMES SONT REPRÉSENTÉS • SEUL LE SCAN EST OBSERVÉ • AUCUN MONTAGE NI USAGE VALIDÉ",
        fill="#7f1d1d",
        font=font(17, bold=True),
    )
    destination = OUTPUT / f"picogk-full-vehicle-f12-{name}.png"
    canvas.save(destination, optimize=True)
    return destination


def make_board(images: list[Path], report: dict) -> Path:
    canvas = Image.new("RGB", (2400, 1820), "#0f172a")
    draw = ImageDraw.Draw(canvas)
    draw.text((60, 36), "911 / 917 — MAQUETTE D'ENCOMBREMENT COMPLÈTE PICO GK F12", fill="white", font=font(38, bold=True))
    draw.text(
        (60, 88),
        "Moteur central arrière • cloison droite • custodes d'admission • réserve boîte chevauchant l'essieu • échangeur dans l'aileron",
        fill="#cbd5e1",
        font=font(22),
    )
    positions = ((60, 145), (1220, 145), (60, 875), (1220, 875))
    for index, path in enumerate(images):
        image = Image.open(path).convert("RGB").crop((35, 115, 1565, 895))
        fitted = ImageOps.fit(image, (1120, 640), Image.Resampling.LANCZOS)
        x, y = positions[index]
        canvas.paste(fitted, (x, y))
        draw.text((x, y + 651), VIEWS[index][1], fill="white", font=font(18, bold=True))

    checks = report["checks"]
    draw.rounded_rectangle((60, 1610, 2340, 1765), radius=16, fill="#1e293b", outline="#ef4444", width=3)
    draw.text((90, 1630), "STATUT TECHNIQUE", fill="#fecaca", font=font(22, bold=True))
    draw.text(
        (90, 1670),
        f"Scan sans collision détectée avec la structure à {report['kernel']['voxel_size_mm']} mm; "
        f"marge cloison {checks['firewall_residual_above_requirement_mm']:.0f} mm non résolue. "
        "Boîte: simple réserve F1, capacité 1 600 ch non démontrée.",
        fill="#fecaca",
        font=font(20, bold=True),
    )
    draw.text(
        (90, 1715),
        "Échelle/orientation du scan, moteur complet, caisse, interfaces, charges, thermique et aérodynamique restent à mesurer.",
        fill="#fecaca",
        font=font(20, bold=True),
    )
    destination = OUTPUT / "picogk-full-vehicle-engineering-board-f12.png"
    canvas.save(destination, optimize=True)
    return destination


def main() -> int:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report["phase"] != "F12" or report["release_gates"]["physical_fit_verified"]:
        raise SystemExit("rapport PicoGK F12 invalide ou promu à tort")
    images = [make_view(name, title, report) for name, title in VIEWS]
    images.append(make_board(images, report))
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F12",
        "status": "annotated_from_native_picogk_screenshots",
        "images": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)} for path in images
        ],
        "claim_limits": [
            "All current packaging systems have PicoGK geometry; most dimensions remain hypotheses.",
            "The transaxle is a historical reservation volume, not a selected or rated unit.",
            "The model does not verify physical fit, strength, thermal capacity, aerodynamics or safety.",
        ],
    }
    (OUTPUT / "image-manifest-f12.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(*(path.relative_to(ROOT) for path in images), sep="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
