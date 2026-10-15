#!/usr/bin/env python3
"""Convertit les captures PicoGK F11 en planches d'ingénierie annotées."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "work" / "911-917-picogk-f11"
REPORT = OUTPUT / "picogk-visualization-report-f11.json"
VIEWS = {
    "side": "VUE LATÉRALE — moteur devant l'essieu arrière",
    "engine-bay": "COUPE AGRANDIE — compartiment moteur et pare-feu",
    "top": "VUE DE DESSUS — largeur et zones interdites",
    "isometric": "VUE ISOMÉTRIQUE — coque hypothétique transparente",
}
LEGEND = [
    ("#d9dee5", "scan partiel 917"),
    ("#f59e0b", "enveloppe moteur complet — hypothèse"),
    ("#ef4444", "pare-feu + dégagement"),
    ("#22d3ee", "limite arrière occupants"),
    ("#4f78a8", "coque 911 allongée — hypothèse"),
    ("#a855f7", "plan d'essieu arrière"),
]


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    path = Path("/System/Library/Fonts/Supplemental") / name
    return ImageFont.truetype(path, size) if path.exists() else ImageFont.load_default()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cropped_capture(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    background = Image.new("RGB", image.size, image.getpixel((0, 0)))
    bounds = ImageChops.difference(image, background).getbbox()
    if bounds is None:
        raise ValueError(f"capture PicoGK vide: {path}")
    left, top, right, bottom = bounds
    margin = 70
    return image.crop(
        (
            max(0, left - margin),
            max(0, top - margin),
            min(image.width, right + margin),
            min(image.height, bottom + margin),
        )
    )


def annotated_view(name: str, title: str, report: dict) -> Path:
    capture = cropped_capture(OUTPUT / f"picogk-packaging-f11-{name}.tga")
    canvas = Image.new("RGB", (1600, 1200), "#f8fafc")
    draw = ImageDraw.Draw(canvas)
    draw.text((55, 36), "PORSCHE 911 / 917 — PICO GK F11", fill="#0f172a", font=font(34, bold=True))
    draw.text((55, 86), title, fill="#334155", font=font(25, bold=True))
    fitted = ImageOps.contain(capture, (1490, 800), Image.Resampling.LANCZOS)
    canvas.paste(fitted, ((1600 - fitted.width) // 2, 135 + (800 - fitted.height) // 2))

    clearance = report["firewall_clearance"]
    draw.text(
        (55, 955),
        f"Voxel 5 mm | scan {report['geometry']['scan_triangle_count']:,} triangles | "
        f"marge pare-feu: {clearance['residual_above_requirement_mm']:.0f} mm — NON RÉSOLUE",
        fill="#991b1b",
        font=font(23, bold=True),
    )
    for index, (colour, label) in enumerate(LEGEND):
        x = 55 + (index % 3) * 500
        y = 1010 + (index // 3) * 42
        draw.rounded_rectangle((x, y, x + 25, y + 25), radius=4, fill=colour, outline="#334155")
        draw.text((x + 36, y - 2), label, fill="#334155", font=font(18))
    draw.text(
        (55, 1157),
        "SCAN NON CALIBRÉ • ENVELOPPE ET COQUE HYPOTHÉTIQUES • AUCUNE VALIDATION DE MONTAGE OU D'USAGE",
        fill="#7f1d1d",
        font=font(17, bold=True),
    )
    destination = OUTPUT / f"picogk-packaging-f11-{name}.png"
    canvas.save(destination, optimize=True)
    return destination


def board(images: list[Path], report: dict) -> Path:
    canvas = Image.new("RGB", (2400, 1780), "#0f172a")
    draw = ImageDraw.Draw(canvas)
    draw.text((60, 38), "911 / 917 — CONTRÔLE D'ENCOMBREMENT PICO GK F11", fill="white", font=font(38, bold=True))
    draw.text(
        (60, 91),
        "Moteur central arrière • empattement +450 mm • pare-feu x=1420 mm • boîte non modélisée",
        fill="#cbd5e1",
        font=font(23),
    )
    positions = ((60, 155), (1220, 155), (60, 890), (1220, 890))
    for index, path in enumerate(images):
        image = Image.open(path).convert("RGB").crop((35, 125, 1565, 940))
        fitted = ImageOps.fit(image, (1120, 640), Image.Resampling.LANCZOS)
        x, y = positions[index]
        canvas.paste(fitted, (x, y))
        draw.text((x, y + 655), list(VIEWS.values())[index], fill="white", font=font(19, bold=True))

    clearance = report["firewall_clearance"]
    draw.rounded_rectangle((60, 1640, 2340, 1740), radius=16, fill="#1e293b", outline="#ef4444", width=3)
    draw.text(
        (90, 1660),
        f"RÉSULTAT: aucune intersection détectée sur le scan partiel; marge hypothétique "
        f"{clearance['residual_above_requirement_mm']:.0f} mm < voxel 5 mm, donc non résolue. "
        "Échelle, orientation, moteur complet et boîte non vérifiés.",
        fill="#fecaca",
        font=font(21, bold=True),
    )
    destination = OUTPUT / "picogk-packaging-engineering-board-f11.png"
    canvas.save(destination, optimize=True)
    return destination


def main() -> int:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report["phase"] != "F11" or report["release_gates"]["physical_fit_verified"]:
        raise SystemExit("rapport PicoGK F11 invalide ou promu à tort")
    images = [annotated_view(name, title, report) for name, title in VIEWS.items()]
    images.append(board(images, report))
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F11",
        "status": "annotated_from_native_picogk_screenshots",
        "images": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
            }
            for path in images
        ],
        "claim_limits": [
            "PicoGK screenshots visualize screening geometry; they do not verify physical fit.",
            "Body shell and complete-engine envelope are hypotheses, not measured CAD.",
            "No transaxle is shown because no unit or manufacturer GA is selected.",
        ],
    }
    (OUTPUT / "image-manifest-f11.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(*(path.relative_to(ROOT) for path in images), sep="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
