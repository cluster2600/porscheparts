#!/usr/bin/env python3
"""Exécute le témoin rigide du crochet F0 avec ovstage et ovphysx."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import ovphysx
import ovstage
from ovphysx import PhysX
from ovphysx.types import ObjectScope, SimObjectType


PART_ID = "993-ELEC-HEADLAMP-SPRING-HOOK-F0-0001"
TWIN_ID = "TWIN-993-HEADLAMP-SPRING-HOOK-ALSI10MG-F0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_vectors(physx: PhysX, attribute: str) -> np.ndarray:
    columns: list[np.ndarray] = []
    with physx.read(
        SimObjectType.RIGID_BODY, [attribute], ObjectScope.ALL
    ) as result:
        for group in result.groups:
            if not group.is_delete and not group.is_array and group.tensors:
                columns.append(np.asarray(group.tensors[0], dtype=np.float64))
    if not columns:
        raise RuntimeError(f"Aucune sortie de corps rigide pour {attribute}.")
    return np.concatenate(columns, axis=0)


def attach_scene(physx: PhysX, usd_path: Path) -> ovstage.Stage:
    if not ovstage.population.available():
        raise RuntimeError("Le pont de population ovstage est indisponible.")
    stage = ovstage.Stage("993-headlamp-hook-rigid-screen")
    try:
        ovstage.population.open_usd(
            stage,
            str(usd_path),
            ordinal=1,
            domains=ovstage.PopulationDomain.PHYSICS,
        )
        stage.advance_write_floor(ordinal=1).wait()
        physx.attach_ovstage(stage, read_ordinal=1)
        return stage
    except Exception:
        stage.destroy()
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--runtime-image-id", required=True)
    parser.add_argument("--steps", type=int, default=240)
    parser.add_argument("--dt", type=float, default=1.0 / 240.0)
    args = parser.parse_args()
    if args.steps <= 0 or args.dt <= 0.0:
        raise SystemExit("steps et dt doivent être positifs.")
    if not args.runtime_image_id.startswith("sha256:"):
        raise SystemExit("runtime-image-id doit être une empreinte sha256.")

    scene = args.scene.resolve()
    asset = args.asset.resolve()
    args.report.parent.mkdir(parents=True, exist_ok=True)

    PhysX.set_cpu_mode(True)
    physx = PhysX()
    stage = None
    try:
        stage = attach_scene(physx, scene)
        physx.wait_all()
        initial_position = read_vectors(physx, "position")
        initial_velocity = read_vectors(physx, "linearVelocity")
        if initial_position.shape != (1, 3):
            raise RuntimeError(
                f"Un seul témoin rigide était attendu, reçu {initial_position.shape}."
            )
        for _ in range(args.steps):
            physx.step_sync(args.dt)
        physx.wait_all()
        final_position = read_vectors(physx, "position")
        final_velocity = read_vectors(physx, "linearVelocity")
    finally:
        if stage is not None:
            physx.detach_ovstage()
            stage.destroy()
        physx.release()

    vertical_drop = float(initial_position[0, 2] - final_position[0, 2])
    rested_on_hook = 16.0 <= float(final_position[0, 2]) <= 18.5
    finite = bool(
        np.isfinite(initial_position).all()
        and np.isfinite(final_position).all()
        and np.isfinite(final_velocity).all()
    )
    passed = finite and vertical_drop > 1.0 and rested_on_hook

    report = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "status": "PASS" if passed else "FAIL",
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "ovphysx": ovphysx.__version__,
            "ovstage": ovstage.__version__,
            "device": "cpu",
            "image_id": args.runtime_image_id,
        },
        "inputs": {
            "scene": {"path": scene.name, "sha256": sha256(scene)},
            "asset": {"path": asset.name, "sha256": sha256(asset)},
        },
        "integration_sequence": [
            "create_physx",
            "populate_ovstage_from_usd",
            "seal_ordinal_1",
            "attach_ovstage",
            "step_sync",
            "read_rigid_body_outputs",
            "detach_destroy_release",
        ],
        "synthetic_case": {
            "steps": args.steps,
            "dt_s": args.dt,
            "simulated_duration_s": args.steps * args.dt,
            "rigid_body_count": int(initial_position.shape[0]),
            "initial_position_mm": initial_position[0].tolist(),
            "initial_velocity_mm_s": initial_velocity[0].tolist(),
            "final_position_mm": final_position[0].tolist(),
            "final_velocity_mm_s": final_velocity[0].tolist(),
            "vertical_drop_mm": vertical_drop,
            "rested_on_hook_height_screen": rested_on_hook,
        },
        "gates": {
            "software_integration": passed,
            "functional_headlamp_assembly": False,
            "engineering_validation": False,
            "manufacturing_release": False,
        },
        "limits": [
            "La sphère témoin, sa masse et la gravité ne représentent pas le ressort du phare.",
            "Le contact rigide ne calcule ni contraintes, ni échauffement, ni adhésif.",
            "Le test confirme seulement l'exécution OpenUSD-ovstage-ovphysx sur le maillage importé.",
        ],
    }
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
