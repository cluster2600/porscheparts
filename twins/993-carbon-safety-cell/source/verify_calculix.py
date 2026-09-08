#!/usr/bin/env python3
"""Compare la réponse CalculiX au solveur treillis Python F1."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TWIN_ROOT = ROOT / "twins" / "993-carbon-safety-cell"


def parse_front_displacements(path: Path) -> dict[int, tuple[float, float, float]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        r"displacements \(vx,vy,vz\) for set FRONT_READ.*?\n\s*\n(?P<table>(?:\s*\d+\s+[+\-0-9.E]+\s+[+\-0-9.E]+\s+[+\-0-9.E]+\s*\n)+)",
        text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"table FRONT_READ absente de {path}")
    values: dict[int, tuple[float, float, float]] = {}
    for line in match.group("table").splitlines():
        fields = line.split()
        if not fields:
            continue
        values[int(fields[0])] = tuple(float(value) for value in fields[1:4])
    if len(values) != 2:
        raise ValueError(f"deux nœuds FRONT_READ attendus, obtenu {len(values)}")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dat", type=Path, default=TWIN_ROOT / "derived" / "selected-torsion.dat")
    parser.add_argument("--screening", type=Path, default=TWIN_ROOT / "derived" / "structural-screening.json")
    parser.add_argument("--config", type=Path, default=TWIN_ROOT / "design-space.json")
    parser.add_argument("--output", type=Path, default=TWIN_ROOT / "derived" / "calculix-verification.json")
    parser.add_argument("--solver-version", default="2.21")
    args = parser.parse_args()

    displacements = parse_front_displacements(args.dat.resolve())
    screening = json.loads(args.screening.read_text(encoding="utf-8"))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    selected_id = screening["selection"]["architecture_id"]
    selected = next(item for item in screening["architectures"] if item["architecture_id"] == selected_id)
    # La génération de deck numérote F_L_FLOOR puis F_R_FLOOR 1 et 3.
    left_z = displacements[1][2]
    right_z = displacements[3][2]
    track_mm = 2.0 * float(config["screening_geometry_mm"]["front_half_track"])
    force_n = float(config["load_cases"]["torsion_screening"]["opposed_vertical_force_per_side_N"])
    twist_rad = abs(left_z - right_z) / track_mm
    stiffness = force_n * track_mm / twist_rad / 1000.0 * math.pi / 180.0
    reference = float(selected["torsion"]["stiffness_Nm_per_deg"])
    relative_error = abs(stiffness - reference) / reference
    passed = relative_error <= 1.0e-4
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if passed else "failed",
        "comparison_scope": "même modèle treillis linéaire, assemblages numériques indépendants",
        "calculix": {
            "version": args.solver_version,
            "input": str((TWIN_ROOT / "derived" / "selected-torsion.inp").relative_to(ROOT)),
            "raw_result": str(args.dat.resolve().relative_to(ROOT)),
            "front_left_displacement_mm": list(displacements[1]),
            "front_right_displacement_mm": list(displacements[3]),
            "torsional_stiffness_Nm_per_deg": round(stiffness, 1),
        },
        "python_reference": {
            "report": str(args.screening.resolve().relative_to(ROOT)),
            "torsional_stiffness_Nm_per_deg": reference,
        },
        "relative_error": relative_error,
        "tolerance": 1.0e-4,
        "passed": passed,
        "claim_limits": [
            "Cette concordance vérifie l'implémentation du treillis, pas sa fidélité à une coque composite.",
            "Les deux solveurs utilisent les mêmes nœuds, barres, propriétés équivalentes et conditions aux limites.",
            "Aucun matériau, joint, stratifié, flambement, fatigue, impact ou crash réel n'est corrélé.",
        ],
        "road_or_track_release": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
