#!/usr/bin/env python3
"""Smoke hors ligne du vrai pipeline F15 sur un OBJ synthétique."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any


PIPELINE = Path(
    "/opt/3dprinting993/twins/reference-917-engine/source/build_scan_segmentation_f15.py"
)
CONTRACT = Path(
    "/opt/3dprinting993/twins/reference-917-engine/scan-segmentation-f15.json"
)
EXPECTED_OUTPUTS = {
    "boundary-components-f15.csv",
    "obj-declarations-f15.json",
    "scan-segmentation-f15-report.json",
    "surface-components-f15.csv",
}
FIXTURE_OBJ = """\
v 0 0 0
v 1 0 0
v 0 1 0
v 0 0 1
v 10 0 0
v 11 0 0
v 10 1 0
v 10 0 1
f 1 3 2
f 1 2 4
f 2 3 4
f 3 1 4
f 5 7 6
f 5 6 8
f 6 7 8
f 7 5 8
"""


def run_smoke(
    *, pipeline: Path = PIPELINE, contract: Path = CONTRACT
) -> dict[str, Any]:
    """Exécute le pipeline embarqué; aucun substitut de maillage n'est utilisé."""

    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(f"Python 3.12 requis, trouvé {sys.version.split()[0]}")
    if os.geteuid() == 0:
        raise RuntimeError("le smoke test doit s'exécuter sans privilèges root")
    if not pipeline.is_file() or not contract.is_file():
        raise RuntimeError("pipeline ou contrat F15 absent de l'image")

    with TemporaryDirectory(prefix="obj-metrology-f15-") as temporary:
        temporary_path = Path(temporary)
        fixture = temporary_path / "two-components.obj"
        output = temporary_path / "output"
        fixture.write_text(FIXTURE_OBJ, encoding="ascii")
        completed = subprocess.run(
            [
                sys.executable,
                str(pipeline),
                "--contract",
                str(contract),
                "--source",
                str(fixture),
                "--output",
                str(output),
                "--synthetic-fixture-mode",
            ],
            check=False,
            capture_output=True,
            env={**os.environ, "PYTHONHASHSEED": "0"},
            text=True,
            timeout=120,
        )
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).strip()
            raise RuntimeError(f"pipeline F15 en échec: {detail}")
        pipeline_report = json.loads(completed.stdout)
        produced = {path.name for path in output.iterdir() if path.is_file()}

    if pipeline_report.get("report_status") != "passed_synthetic_fixture_only":
        raise RuntimeError(f"statut F15 inattendu: {pipeline_report.get('report_status')!r}")
    if pipeline_report.get("execution_scope") != "synthetic_fixture":
        raise RuntimeError("le pipeline n'a pas conservé la portée synthetic_fixture")
    if produced != EXPECTED_OUTPUTS:
        raise RuntimeError(f"sorties F15 inattendues: {sorted(produced)!r}")
    topology = pipeline_report.get("topology", {})
    if topology.get("surface_component_count") != 2:
        raise RuntimeError(f"segmentation inattendue: {topology!r}")
    if topology.get("boundary_edges") != 0 or topology.get("non_manifold_edges") != 0:
        raise RuntimeError(f"topologie de fixture inattendue: {topology!r}")
    custody = pipeline_report.get("source_custody", {})
    if custody.get("expected_sha256_matches") is not False:
        raise RuntimeError("la fixture a été confondue avec le scan canonique")
    if custody.get("raw_geometry_in_report") is not False:
        raise RuntimeError("le pipeline a copié de la géométrie brute dans le rapport")
    release = pipeline_report.get("release", {})
    if not release or any(value is not False for value in release.values()):
        raise RuntimeError("une autorité de release a été ouverte par la fixture")

    return {
        "schema_version": "1.0.0",
        "status": "passed",
        "offline_smoke": True,
        "platform_contract": "linux/amd64-cpu",
        "python_version": sys.version.split()[0],
        "pipeline": {
            "implementation": "python_standard_library_only",
            "report_status": pipeline_report["report_status"],
            "surface_components": topology["surface_component_count"],
            "output_files": sorted(produced),
        },
        "non_root": True,
        "gpu_required": False,
        "bundled_assets": {
            "raw_scans": False,
            "datasets": False,
            "model_weights": False,
            "secrets": False,
        },
        "claim_scope": (
            "execution du parseur F15 sur fixture synthetique seulement; aucune "
            "preuve d'identite, d'echelle, de semantique, de simulation, de "
            "fonctionnement ou d'imprimabilite"
        ),
    }


def main() -> int:
    try:
        report = run_smoke()
    except Exception as exc:
        print(json.dumps({"schema_version": "1.0.0", "status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
