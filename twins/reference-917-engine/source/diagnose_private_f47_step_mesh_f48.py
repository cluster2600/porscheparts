#!/usr/bin/env python3
"""Diagnose localement les STEP F47 sans publier géométrie ni coordonnées.

Le même programme s'exécute en mode ``occt`` dans l'image CAO et en mode
``gmsh`` dans l'image de maillage. Chaque sortie est volontairement privée et
porteuse d'indices/coordonnées; elle doit rester hors du dépôt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


STEMS = tuple(
    f"917-head-{variant}-f47-{role}"
    for variant in ("2v", "4v")
    for role in ("gas-core", "oil-core", "head")
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_output(project_root: Path, output: Path) -> Path:
    root = project_root.resolve()
    resolved = output.resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError("private_coordinate_output_must_be_outside_repository")
    if resolved.suffix.lower() != ".json":
        raise ValueError("private_output_must_be_json")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def required_step(root: Path, stem: str) -> Path:
    path = root / f"{stem}.step"
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing_or_symlink_private_STEP:{stem}")
    return path


def run_occt(private_root: Path) -> dict[str, Any]:
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.Bnd import Bnd_Box
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape

    def read_step(path: Path):
        reader = STEPControl_Reader()
        if reader.ReadFile(str(path)) != IFSelect_RetDone or reader.TransferRoots() < 1:
            raise RuntimeError(f"STEP_read_failed:{path.name}")
        shape = reader.OneShape()
        if shape.IsNull():
            raise RuntimeError(f"STEP_is_null:{path.name}")
        return shape

    def indexed(shape, kind):
        result = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, kind, result)
        return result

    def bounds(shape) -> list[float]:
        box = Bnd_Box()
        BRepBndLib.AddOptimal_s(shape, box, True, False)
        return [float(value) for value in box.Get()]

    files: dict[str, Any] = {}
    for stem in STEMS:
        path = required_step(private_root, stem)
        shape = read_step(path)
        faces = indexed(shape, TopAbs_FACE)
        edges = indexed(shape, TopAbs_EDGE)
        analyzer = BOPAlgo_ArgumentAnalyzer()
        analyzer.SetShape1(shape)
        analyzer.SelfInterMode = True
        analyzer.SmallEdgeMode = True
        analyzer.RebuildFaceMode = True
        analyzer.ContinuityMode = True
        analyzer.CurveOnSurfaceMode = True
        analyzer.Perform()
        counts: Counter[str] = Counter()
        results = []
        for result in analyzer.GetCheckResult():
            status = str(result.GetCheckStatus()).split(".")[-1]
            counts[status] += 1
            faulty = []
            for item in result.GetFaultyShapes1():
                if item.ShapeType() == TopAbs_FACE:
                    kind, index = "face", faces.FindIndex(item)
                elif item.ShapeType() == TopAbs_EDGE:
                    kind, index = "edge", edges.FindIndex(item)
                else:
                    kind, index = str(item.ShapeType()).split(".")[-1], None
                faulty.append({"kind": kind, "private_index": index, "bbox": bounds(item)})
            results.append({"status": status, "faulty_shapes": faulty})
        files[stem] = {
            "step_sha256": sha256(path),
            "step_bytes": path.stat().st_size,
            "BRepCheck_exact_valid": bool(BRepCheck_Analyzer(shape, True).IsValid()),
            "BOPAlgo_result_count": int(sum(counts.values())),
            "BOPAlgo_status_counts": dict(sorted(counts.items())),
            "results_with_private_coordinates": results,
        }
    return {"schema": "porsche-917-f48-private-occt-diagnostic/v1", "files": files}


def run_gmsh(private_root: Path, algorithm: int) -> dict[str, Any]:
    import gmsh

    files: dict[str, Any] = {}
    for variant in ("2v", "4v"):
        stem = f"917-head-{variant}-f47-head"
        path = required_step(private_root, stem)
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("Mesh.MeshSizeMin", 4.0)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 12.0)
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.option.setNumber("Mesh.Algorithm3D", algorithm)
        gmsh.logger.start()
        surface_ok = False
        volume_ok = False
        error = None
        try:
            gmsh.open(str(path))
            gmsh.model.mesh.generate(2)
            surface_ok = True
            gmsh.model.mesh.generate(3)
            volume_ok = True
        except Exception as exc:  # valeur enregistrée, porte fermée
            error = str(exc)
        logs = gmsh.logger.get()
        gmsh.logger.stop()
        gmsh.finalize()
        files[stem] = {
            "step_sha256": sha256(path),
            "gmsh_version": gmsh.__version__,
            "algorithm_3d": algorithm,
            "surface_mesh_completed": surface_ok,
            "volume_mesh_completed": volume_ok,
            "error": error,
            "intersection_log_lines_private": [
                line for line in logs if "PLC" in line or "intersect" in line.lower()
            ],
        }
    return {"schema": "porsche-917-f48-private-gmsh-diagnostic/v1", "files": files}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("occt", "gmsh"), required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--gmsh-algorithm", type=int, default=1)
    args = parser.parse_args()
    private_root = args.private_root.resolve()
    if not private_root.is_dir():
        raise ValueError("private_root_not_a_directory")
    output = safe_output(args.project_root, args.private_output)
    if args.mode == "occt":
        payload = run_occt(private_root)
    else:
        payload = run_gmsh(private_root, args.gmsh_algorithm)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"mode": args.mode, "private_output_written": True, "sha256": sha256(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
