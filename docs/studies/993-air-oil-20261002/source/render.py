#!/usr/bin/env python3
"""Render the exported geometry faithfully; colours are labels, never fields."""
import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont


NAVY = "#101e30"
MUTED = "#9eacc1"
CYAN = "#39d7db"
GOLD = "#e4b26a"
FONT_DIR = Path("/System/Library/Fonts/Supplemental")


def font(size, bold=False):
    p = FONT_DIR / ("Arial Bold.ttf" if bold else "Arial.ttf")
    return ImageFont.truetype(str(p), size) if p.exists() else ImageFont.load_default(size=size)


def text(draw, at, value, size=30, fill="white", bold=False):
    draw.text(at, value, font=font(size, bold), fill=fill)


def render_scene(meshes, camera, size=(1500, 1080)):
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background(NAVY)
    for mesh, colour, opacity in meshes:
        pl.add_mesh(mesh, color=colour, opacity=opacity, smooth_shading=False,
                    ambient=0.28, diffuse=0.7, specular=0.22, specular_power=22)
    pl.camera_position = camera
    pl.camera.parallel_projection = True
    pl.reset_camera()
    # Preserve the explicit orientation after fitting the bounds.
    pl.camera_position = camera
    pl.enable_anti_aliasing("ssaa")
    pixels = pl.screenshot(return_img=True)
    pl.close()
    return Image.fromarray(pixels).convert("RGB")


def read(cad, name):
    return pv.read(cad / f"{name}-concept-only.stl")


def canvas(title, eyebrow, subtitle, size=(2400, 1600)):
    image = Image.new("RGB", size, NAVY)
    d = ImageDraw.Draw(image)
    d.rectangle((70, 55, 120, 62), fill=CYAN)
    text(d, (140, 42), eyebrow.upper(), 25, CYAN, True)
    text(d, (70, 110), title, 68, bold=True)
    text(d, (72, 205), subtitle, 28, MUTED)
    d.line((70, size[1] - 130, size[0] - 70, size[1] - 130), fill="#31415a", width=2)
    text(d, (70, size[1] - 100), "PROTOTYPE • NON PRÊT AU MONTAGE • Aucune validation thermique ou mécanique", 26, GOLD, True)
    text(d, (70, size[1] - 54), "3dprinting993  /  Lot privé du 2 octobre 2026  /  Couleurs de repérage, pas champs physiques", 22, MUTED)
    return image


def head_image(cad, out, report):
    body = read(cad, "head-4v-air-oil-proposal")
    fluid = read(cad, "head-fluid-domain")
    scene = [(body, "#c5cbd4", 0.23), (fluid, CYAN, 1)]
    colours = ["#ae9ae8", GOLD, "#70bcb3"]
    for i in range(1, 13):
        scene.append((pv.read(cad / f"component-{i:02d}-context.stl"), colours[(i - 1) % 3], 1))
    image = canvas("Quatre soupapes. Air + huile.", "M64 · proposition de géométrie",
                   "Corps issu du scan 935 ; interfaces 993 et échelle physique à mesurer.")
    image.paste(render_scene(scene, [(260, -330, 215), (0, 10, 38), (0, 0, 1)], (1550, 1080)), (0, 270))
    d = ImageDraw.Draw(image)
    x = 1600
    for y, number, title, detail in [
        (330, "01", "Silhouette à ailettes conservée", "Reprise d’une CAO existante, sans nouvelle coque."),
        (530, "02", "Une galerie continue proposée", "Section goutte : rayon 3, toit à 45°, deux accès visés."),
        (730, "03", "Douze composants hérités", "4 soupapes, 4 sièges et 4 guides ; serrages non qualifiés."),
        (930, "04", "Validation qui reste ouverte", "Chambre, conduits, piston, bougie et distribution à définir."),
    ]:
        text(d, (x, y), number, 28, CYAN, True)
        text(d, (x, y + 48), title, 29, bold=True)
        # Deliberate manual wraps keep the technical plate readable.
        words, lines, line = detail.split(), [], ""
        for w in words:
            trial = (line + " " + w).strip()
            if d.textlength(trial, font=font(25)) > 710:
                lines.append(line); line = w
            else:
                line = trial
        lines.append(line)
        for j, l in enumerate(lines):
            text(d, (x, y + 94 + j * 34), l, 25, MUTED)
    text(d, (170, 1350), "Vue transparente des exports CAO réels — aucune texture de résultat simulé", 26, MUTED)
    image.save(out / "01-head-air-oil.png")


def coupon_image(cad, out):
    body, fluid = read(cad, "oil-gallery-coupon"), read(cad, "coupon-fluid-domain")
    image = canvas("Le coupon qui rend la galerie inspectable.", "Procédé · démonstrateur indépendant",
                   "Une géométrie originale pour préparer le nettoyage et les essais ; aucun raccord moteur défini.")
    scene = [(body, "#aebbc9", 0.16), (fluid, CYAN, 1)]
    image.paste(render_scene(scene, [(-140, -145, 110), (0, 0, 11), (0, 0, 1)], (1500, 1040)), (10, 280))
    d = ImageDraw.Draw(image)
    text(d, (1620, 350), "100 × 50 × 24 mm", 48, bold=True)
    text(d, (1620, 450), "2 ports ouverts · aucun cul-de-sac", 29, CYAN, True)
    text(d, (1620, 520), "Toit tangent à 45°", 29)
    text(d, (1620, 580), "Rayon de virage : 12 mm", 29)
    text(d, (1620, 640), "Ligament nominal minimal : 5 mm", 29)
    # Actual profile construction, drawn to scale, with its declared dimensions.
    r, sc, ox, oz = 3, 54, 1900, 1010
    theta = np.linspace(3 * np.pi / 4, 9 * np.pi / 4, 100)
    pts = [(ox + r * sc * np.cos(t), oz - r * sc * np.sin(t)) for t in theta]
    pts += [(ox, oz - r * np.sqrt(2) * sc)]
    d.polygon(pts, fill=CYAN, outline="white", width=3)
    text(d, (1620, 1240), "Section de conception, pas une cote OEM", 25, MUTED)
    image.save(out / "02-oil-gallery-coupon.png")


def stand_image(cad, out):
    stand = read(cad, "turbo-valve-inspection-stand")
    image = canvas("Un support d’inspection pour la Turbo.", "Atelier · pièce hors moteur",
                   "Queue de soupape déclarée Ø8 mm ; alésage de support Ø8,6 mm choisi pour cette étude.")
    image.paste(render_scene([(stand, "#cfaa78", 1)], [(100, -130, 105), (0, 0, 6), (0, 0, 1)], (1500, 1050)), (0, 290))
    d = ImageDraw.Draw(image)
    for y, title, detail in [(360, "Donnée sourcée", "Diamètre de queue : 8 mm (catalogue fournisseur)."),
                             (560, "Choix de conception", "Socle 64 × 42 mm ; jeu diamétral de 0,6 mm."),
                             (760, "Trou traversant", "Accès de nettoyage et contrôle visuel conservés."),
                             (960, "Usage prévu", "Présentation et préparation d’inspection sur établi.")]:
        text(d, (1570, y), title, 31, CYAN, True)
        words = detail.split(); split = len(words) // 2
        text(d, (1570, y + 55), " ".join(words[:split]), 27, MUTED)
        text(d, (1570, y + 95), " ".join(words[split:]), 27, MUTED)
    image.save(out / "03-turbo-valve-stand.png")


def hydraulic_plot(report, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7))
    rows = report["hydraulics"]["cases"]
    for mu, color in zip([0.006, 0.012, 0.03], ["#0f8b8d", "#4f5ba5", "#bd703d"]):
        points = [r for r in rows if r["viscosity_Pa_s"] == mu]
        axes[0].plot([r["flow_L_min"] for r in points], [r["total_pressure_drop_bar"] for r in points], "o-", label=f"μ = {mu:g} Pa·s", color=color)
    p = [r for r in rows if r["viscosity_Pa_s"] == .012]
    axes[1].plot([r["flow_L_min"] for r in p], [r["enthalpy_transport_capacity_W_at_assumed_delta_T"] for r in p], "o-", color="#0f8b8d")
    axes[0].set_ylabel("Perte de charge approchée (bar)")
    axes[1].set_ylabel("Transport d’enthalpie (W), ΔT huile = 20 K")
    for a in axes:
        a.set_xlabel("Débit hypothétique par culasse (L/min)"); a.grid(alpha=.2)
    axes[0].legend()
    fig.suptitle("Sensibilité géométrique air/huile — aucune température métal calculée", fontweight="bold")
    fig.text(.5, .012, "Modèle laminaire équivalent ; propriétés huile et K = 2 supposés. Le transport d’enthalpie n’est pas le refroidissement obtenu.", ha="center", fontsize=9)
    fig.tight_layout(rect=[0, .05, 1, .94])
    fig.savefig(out / "04-hydraulic-sensitivity.png", dpi=220)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    out = args.output or args.run / "renders"
    if out.exists():
        raise ValueError("render_directory_must_be_new")
    out.mkdir()
    report = json.loads((args.run / "verification.json").read_text())
    cad = args.run / "cad"
    if (cad / "head-fluid-domain-concept-only.stl").exists():
        head_image(cad, out, report)
    coupon_image(cad, out)
    stand_image(cad, out)
    hydraulic_plot(report, out)
    print(out, flush=True)


if __name__ == "__main__":
    main()
