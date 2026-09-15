"""Criblage d'impression LPBF de toutes les pieces 993 qui ont un maitre STEP.

Pour chaque piece : le STEP est tessele en STL d'analyse (build123d, meme
tolerance que le levier de porte), puis `run_metal_am_geometry_screen.py`
tranche la piece sur toute sa hauteur a l'epaisseur de couche de la route
EOS M 290 de sa matiere. Les pieces passent **une par une**, dans le conteneur
cadsim, avec un plafond memoire et CPU : WSL ne doit pas tomber.

L'enveloppe attendue est la boite englobante du B-rep, lue avant tesselation.
Le controle compare donc le maitre a sa surface derivee ; il ne dit rien de la
conformite a une piece d'origine.

Un echec est ecrit tel quel dans `print-screen-status.json` ; il n'est jamais
maquille en reussite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "3dprinting993-cadsim:dev"
MACHINE = "catalog/manufacturing/machines/eos-m290.json"

# epaisseur de couche publiee par EOS pour chaque matiere sur M 290
LAYER_MM = {
    "AlSi10Mg": (0.03, "EOS Aluminium AlSi10Mg / M290 30 um"),
    "IN625": (0.04, "EOS NickelAlloy IN625 / M290 40 um"),
    "IN718": (0.04, "EOS NickelAlloy IN718 / M290 40 um"),
    "Ti64": (0.03, "EOS Titanium Ti64 / M290 30 um"),
    "Al2139": (0.06, "EOS Aluminium Al2139 AM / M290 60 um"),
}

PARTS = {
    "993-body-front-impact-support-alsi10mg-f0-0001": "AlSi10Mg",
    "993-eng-connecting-rod-ti64-f0-0001": "Ti64",
    "993-eng-cooling-impeller-alsi10mg-f0-0001": "AlSi10Mg",
    "993-eng-exhaust-manifold-in625-f0-0001": "IN625",
    "993-eng-fan-housing-alsi10mg-f0-0001": "AlSi10Mg",
    "993-eng-intake-valve-ti64-hollow-f0-0001": "Ti64",
    "993-eng-intercooler-bracket-ti-f0-0001": "Ti64",
    "993-eng-intercooler-end-tank-alsi10mg-f0-0001": "AlSi10Mg",
    "993-eng-k16-compressor-wheel-al2139-f1-0001": "Al2139",
    "993-eng-k16-compressor-wheel-alsi10mg-f0-0001": "AlSi10Mg",
    "993-eng-k16-turbine-wheel-in718-f0-0001": "IN718",
    "993-eng-oil-filter-console-alsi10mg-f0-0001": "AlSi10Mg",
    "993-eng-three-runner-intake-alsi10mg-f0-0001": "AlSi10Mg",
    "993-eng-turbo-heat-shield-in625-f0-0001": "IN625",
    "993-eng-turbo-oil-return-line-in625-f0-0001": "IN625",
    "993-eng-upper-valve-cover-alsi10mg-f0-0001": "AlSi10Mg",
    "993-whl-center-cap-alsi10mg-f0-0001": "AlSi10Mg",
    # criblees au 03 sans STL publie : on derive la surface pour l'etape 04
    "993-elec-headlamp-spring-hook-f0-0001": "AlSi10Mg",
    "993-exh-oval-tip-in625-f0-0001": "IN625",
}

TESSELLATE = r"""
import json, sys
from build123d import import_step, export_stl
step, stl = sys.argv[1], sys.argv[2]
shape = import_step(step)
box = shape.bounding_box()
export_stl(shape, stl, tolerance=0.03, angular_tolerance=0.08)
print(json.dumps([box.size.X, box.size.Y, box.size.Z]))
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def docker(args: list[str], memory: str, cpus: str, timeout: int) -> subprocess.CompletedProcess:
    command = [
        "docker", "run", "--rm", f"--memory={memory}", f"--memory-swap={memory}",
        f"--cpus={cpus}", "--user", f"{os.getuid()}:{os.getgid()}",
        "-e", "MPLCONFIGDIR=/tmp", "-e", "OMP_NUM_THREADS=2", "-e", "OPENBLAS_NUM_THREADS=2",
        "-e", "PYTHONPATH=/pylib", "-v", f"{ROOT}:/repo", "-v", f"{PYLIB}:/pylib:ro",
        "-w", "/repo", "--entrypoint", "python3", IMAGE, *args,
    ]
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def screen(slug: str, material: str, memory: str, cpus: str, pitch: float) -> dict:
    step = next((ROOT / f"parts/{slug}/derived").glob("*.step"))
    stl = step.with_suffix(".stl")
    layer, label = LAYER_MM[material]
    status = {"part": slug, "material": material, "layer_thickness_mm": layer}
    started = time.time()
    result = docker(["-c", TESSELLATE, str(step.relative_to(ROOT)), str(stl.relative_to(ROOT))],
                    memory, cpus, 900)
    if result.returncode != 0:
        return status | {"status": "failed_tessellation", "error": result.stderr[-600:]}
    envelope = json.loads(result.stdout.strip().splitlines()[-1])
    part_id = json.loads((ROOT / f"catalog/parts/{slug}.json").read_text())["part_id"]
    output = f"parts/{slug}/evidence/lpbf-f0"
    result = docker([
        "scripts/run_metal_am_geometry_screen.py", "--part-id", part_id,
        "--master", str(step.relative_to(ROOT)), "--master-sha256", sha256(step),
        "--surface", str(stl.relative_to(ROOT)), "--surface-sha256", sha256(stl),
        "--machine-card", MACHINE, "--material", label,
        "--expected-envelope-mm", *[f"{v:.6f}" for v in envelope],
        "--envelope-tolerance-mm", "0.1", "--layer-thickness-mm", str(layer),
        "--voxel-pitch-mm", str(pitch), "--output", output,
    ], memory, cpus, 5400)
    status |= {"envelope_mm": envelope, "seconds": round(time.time() - started, 1),
               "output": output, "stdout": result.stdout[-400:]}
    status["returncode"] = result.returncode
    if result.returncode == 137:
        # le conteneur a atteint son plafond memoire : ce n'est pas un verdict geometrique
        return status | {"status": "failed_memory_cap", "error": f"conteneur tue au plafond {memory}"}
    if result.returncode != 0:
        return status | {"status": "failed_closed", "error": (result.stderr or result.stdout)[-600:]}
    return status | {"status": "screened"}


def main() -> int:
    global PYLIB
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pylib", type=Path, required=True, help="shapely+rtree installes pour le conteneur")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--memory", default="6g")
    parser.add_argument("--cpus", default="4")
    parser.add_argument("--voxel-pitch-mm", type=float, default=1.0)
    parser.add_argument("--status", type=Path, required=True)
    args = parser.parse_args()
    PYLIB = args.pylib.resolve()
    rows = json.loads(args.status.read_text()) if args.status.exists() else {}
    for slug, material in PARTS.items():
        if args.only and slug not in args.only:
            continue
        if rows.get(slug, {}).get("status") == "screened":
            continue
        print(f"-> {slug}", flush=True)
        try:
            row = screen(slug, material, args.memory, args.cpus, args.voxel_pitch_mm)
        except subprocess.TimeoutExpired:
            row = {"part": slug, "status": "failed_timeout"}
        rows[slug] = row
        args.status.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
        print(f"   {row['status']} {row.get('seconds', '')}s {row.get('error', '')[-200:]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
