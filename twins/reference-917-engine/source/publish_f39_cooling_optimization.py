#!/usr/bin/env python3
"""Publie les résultats reproductibles de l'optimisation thermique F39."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replace-existing", action="store_true")
    args = parser.parse_args()
    report_path = args.source / "f39-cooling-optimization-report.json"
    csv_path = args.source / "f39-cooling-candidates.csv"
    image_path = args.source / "917-head-f39-cooling-optimization.png"
    sensitivity_image_path = args.source / "917-head-f39-cooling-envelope.png"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    decision = report["decision"]
    if decision["metal_print_authorized"] or decision["engine_start_authorized"]:
        raise SystemExit("refus de publier une autorisation depuis le criblage F39")
    if args.output.exists() and not args.replace_existing:
        raise SystemExit(f"output exists: {args.output}")
    args.output.mkdir(parents=True, exist_ok=args.replace_existing)
    for path in (report_path, csv_path, image_path, sensitivity_image_path):
        shutil.copy2(path, args.output / path.name)

    selected = report["optimization"]["selected_candidate"]
    oil_counts = report["optimization"]["passing_combinations_by_local_oil_heat_w"]
    (args.output / "README.md").write_text(
        "# Refroidissement 917 F39 — optimisation paramétrique publiée\n\n"
        "Le calcul balaye deux modèles indépendants dans leurs équations primaires : "
        "(A) une loi d'échelle ancrée sur le canal OpenFOAM F38 et (B) Gnielinski–Darcy "
        "avec efficacité d'ailette. Il ne s'agit ni d'une nouvelle CFD par candidat ni "
        "d'une CHT de culasse complète.\n\n"
        f"- combinaisons évaluées : {report['optimization']['combinations_evaluated']} ;\n"
        f"- combinaisons passant l'écran nominal : {report['optimization']['numerical_screen_passing_combinations']} ;\n"
        f"- candidat : {selected['parameters']['fin_levels']} niveaux, ailettes "
        f"{selected['parameters']['fin_thickness_mm']:.1f} mm, jeu "
        f"{selected['parameters']['clear_gap_mm']:.1f} mm, rayon de pied "
        f"{selected['parameters']['root_radius_mm']:.1f} mm, déflecteur "
        f"`{selected['parameters']['duct']}` ;\n"
        f"- `T_pont,max` nominale : {selected['maximum_bridge_temperature_c']:.1f} °C ;\n"
        f"- `Δp_max` nominale : {selected['maximum_pressure_drop_pa']/1000:.2f} kPa ;\n"
        f"- écart relatif `h` : {100*selected['h_cross_method_relative_difference']:.1f} % ;\n"
        f"- passages sans huile 1 200 W : {oil_counts['0.0'] + oil_counts['600.0']} ;\n"
        "- aire mouillée F39 : proxy extrapolé de la surface scan F37, pas mesurée sur un B-Rep accepté ;\n"
        "- géométrie d'huile, carte matière à chaud, fan map, CHT complète et corrélation physique : non validées ;\n"
        "- impression métal et démarrage moteur : interdits.\n",
        encoding="utf-8",
    )
    files = {}
    for path in sorted(
        item
        for item in args.output.rglob("*")
        if item.is_file() and item.name != "publication.json"
    ):
        relative = path.relative_to(args.output).as_posix()
        files[relative] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    manifest = {
        "schema_version": "1.0",
        "classification": "published_F39_scan_only_parametric_cooling_screen_not_manufacturing_release",
        "files": files,
        "gates": {
            "absolute_scale_confirmed": False,
            "accepted_F39_BRep_and_wetted_area_available": False,
            "full_head_CHT_complete": False,
            "oil_gallery_geometry_and_heat_transfer_validated": False,
            "hot_material_coupon_card_qualified": False,
            "physical_correlation_complete": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    (args.output / "publication.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "published", "files": len(files), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
