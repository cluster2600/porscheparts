#!/usr/bin/env python3
"""Publie le sous-ensemble vérifiable du recalcul de refroidissement F38."""

from __future__ import annotations

import argparse
import gzip
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
    args = parser.parse_args()
    report_path = args.source / "f38-cooling-cross-check.json"
    image_path = args.source / "917-head-f38-cooling-section.png"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["decision"]["metal_print_authorized"] or report["decision"]["engine_start_authorized"]:
        raise SystemExit("refus de publier une autorisation F38 depuis ce criblage")
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    args.output.mkdir(parents=True)
    shutil.copy2(report_path, args.output / report_path.name)
    shutil.copy2(image_path, args.output / image_path.name)
    (args.output / "README.md").write_text(
        "# Refroidissement 917 F38 — preuves publiées\n\n"
        "Deux mailles OpenFOAM 14 d'un canal inter-ailettes sont comparées à une "
        "corrélation indépendante de Gnielinski avec efficacité d'ailette. Le canal "
        "n'est ni une CHT de culasse complète, ni une validation physique.\n\n"
        f"- `h` OpenFOAM fin : {report['openfoam']['cases'][-1]['effective_h_w_m2k']:.2f} W/m²K ;\n"
        f"- erreur de bilan énergétique fin : {100.0 * report['openfoam']['cases'][-1]['energy_balance_relative']:.2f} % ;\n"
        f"- température de pont projetée : {report['thermal_projection']['from_openfoam']['bridge_temperature_c']:.1f} à "
        f"{report['thermal_projection']['from_analytical']['bridge_temperature_c']:.1f} °C ;\n"
        "- CHT culasse entière : non exécutée ;\n"
        "- impression métal et démarrage moteur : interdits.\n",
        encoding="utf-8",
    )
    for case in report["openfoam"]["cases"]:
        case_source = args.source / "openfoam-cases" / case["case_id"]
        case_output = args.output / "openfoam" / case["case_id"]
        case_output.mkdir(parents=True)
        for filename in ("case-metadata.json", "log.blockMesh", "log.checkMesh", "log.foamRun", "log.sample"):
            source = case_source / filename
            if filename.endswith(".json"):
                shutil.copy2(source, case_output / filename)
            else:
                with source.open("rb") as input_stream, gzip.GzipFile(
                    filename=str(case_output / f"{filename}.gz"), mode="wb", mtime=0
                ) as output_stream:
                    shutil.copyfileobj(input_stream, output_stream)
        sample_files = sorted((case_source / "postProcessing/sampleDict").glob("*/centreLine*.xy"))
        if sample_files:
            shutil.copy2(sample_files[-1], case_output / "centreLine_T.xy")
        for function, filename in (
            ("finHeatFlux", "wallHeatFlux.dat"),
            ("inletMassFlow", "surfaceFieldValue.dat"),
            ("outletMassFlow", "surfaceFieldValue.dat"),
            ("outletTemperature", "surfaceFieldValue.dat"),
            ("inletPressure", "surfaceFieldValue.dat"),
            ("outletPressure", "surfaceFieldValue.dat"),
        ):
            matches = sorted((case_source / "postProcessing" / function).glob(f"*/{filename}"))
            if not matches:
                raise SystemExit(f"preuve OpenFOAM manquante: {case['case_id']}/{function}")
            shutil.copy2(matches[-1], case_output / f"{function}-{filename}")
    files = {}
    for path in sorted(item for item in args.output.rglob("*") if item.is_file()):
        relative = path.relative_to(args.output).as_posix()
        files[relative] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    manifest = {
        "schema_version": "1.0",
        "classification": "published_reproducible_F38_cooling_evidence_not_manufacturing_release",
        "files": files,
        "gates": {
            "absolute_scale_confirmed": False,
            "full_head_CHT_complete": False,
            "hot_material_coupon_card_qualified": False,
            "physical_correlation_complete": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    (args.output / "publication.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "published", "files": len(files), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
