#!/usr/bin/env python3
"""Construit le prototype hybride F38 sans remplacer la peau issue du scan.

La sortie maitresse est un STL local qui conserve exactement la topologie F37
et decale chaque sommet de 0,45 mm sur sa normale. Le STEP est volontairement
un B-Rep facette, decime, destine au controle visuel et au round-trip OCCT. Il
ne constitue ni une CAO de production ni une autorisation d'impression.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pymeshlab
import trimesh
from build123d import import_step
from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeSolid,
    BRepBuilderAPI_Sewing,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise RuntimeError(f"maillage_absent:{path}")
    return mesh


def verify_source(path: Path, expected: str) -> None:
    observed = sha256(path)
    if observed != expected:
        raise RuntimeError(f"sha256_inattendu:{path}:{observed}")


def decimate(source: Path, destination: Path, target_faces: int) -> None:
    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(str(source))
    mesh_set.apply_filter(
        "meshing_decimation_quadric_edge_collapse",
        targetfacenum=target_faces,
        preservetopology=True,
        preserveboundary=True,
        optimalplacement=True,
        autoclean=True,
    )
    mesh_set.save_current_mesh(str(destination), binary=True)


def faceted_step(mesh: trimesh.Trimesh, destination: Path) -> None:
    sewing = BRepBuilderAPI_Sewing(0.05, True, True, True, False)
    for face in mesh.faces:
        polygon = BRepBuilderAPI_MakePolygon()
        for index in face:
            x, y, z = mesh.vertices[int(index)]
            polygon.Add(gp_Pnt(float(x), float(y), float(z)))
        polygon.Close()
        sewing.Add(BRepBuilderAPI_MakeFace(polygon.Wire(), True).Face())
    sewing.Perform()
    shell = TopoDS.Shell_s(sewing.SewedShape())
    solid_maker = BRepBuilderAPI_MakeSolid()
    solid_maker.Add(shell)
    solid = solid_maker.Solid()
    if not BRepCheck_Analyzer(solid).IsValid():
        raise RuntimeError("brep_facette_invalide_avant_export")
    writer = STEPControl_Writer()
    writer.Transfer(solid, STEPControl_AsIs)
    if writer.Write(str(destination)) != 1:
        raise RuntimeError("echec_export_step")


def mesh_metrics(mesh: trimesh.Trimesh) -> dict[str, object]:
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "euler_number": int(mesh.euler_number),
        "volume_mm3_if_scale_is_mm": float(mesh.volume),
        "surface_area_mm2_if_scale_is_mm": float(mesh.area),
        "bounds_mm_if_scale_is_mm": np.asarray(mesh.bounds).tolist(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--f37-head-stl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    verify_source(args.f37_head_stl, contract["parent"]["head_mesh_sha256"])
    output = args.output
    output.mkdir(parents=True, exist_ok=True)

    source = load_mesh(args.f37_head_stl)
    if not source.is_watertight:
        raise RuntimeError("source_F37_non_etanche")
    offset = float(contract["geometry_strategy"]["normal_offset_mm_if_scale_is_mm"])
    master = source.copy()
    master.vertices = master.vertices + offset * master.vertex_normals
    master_path = output / "917-head-f38-scan-offset-master.local.stl"
    master.export(master_path)

    proxy_stl = output / "917-head-f38-faceted-proxy.stl"
    decimate(master_path, proxy_stl, int(contract["geometry_strategy"]["faceted_brep_proxy_faces"]))
    proxy = load_mesh(proxy_stl)
    if not proxy.is_watertight:
        raise RuntimeError("proxy_decime_non_etanche")
    proxy_step = output / "917-head-f38-faceted-proxy.step"
    faceted_step(proxy, proxy_step)

    reopened = import_step(proxy_step)
    solids = list(reopened.solids())
    if len(solids) != 1 or not solids[0].is_valid or not solids[0].is_manifold:
        raise RuntimeError("roundtrip_step_invalide")

    report = {
        "schema_version": "1.0.0",
        "phase": "F38",
        "classification": "generation_only_not_release_evidence",
        "contract_sha256": sha256(args.contract),
        "source": {"path": str(args.f37_head_stl), "sha256": sha256(args.f37_head_stl)},
        "master": {"path": str(master_path), "sha256": sha256(master_path), **mesh_metrics(master)},
        "faceted_proxy": {
            "stl": {"path": str(proxy_stl), "sha256": sha256(proxy_stl), **mesh_metrics(proxy)},
            "step": {"path": str(proxy_step), "sha256": sha256(proxy_step)},
            "roundtrip": {
                "solid_count": 1,
                "valid": True,
                "manifold": True,
                "volume_mm3_if_scale_is_mm": float(solids[0].volume),
            },
        },
        "limitations": [
            "Le decalage normal ne reconstruit pas des surfaces fonctionnelles analytiques.",
            "Le B-Rep facette ne prouve pas la maillabilite volumique; Gmsh doit etre teste independamment.",
            "Ce rapport de generation ne remplace pas l'audit F38 publie et fail-closed.",
        ],
    }
    report_path = output / "f38-generation-report.local.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "generated_release_blocked", "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
