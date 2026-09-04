#!/usr/bin/env python3
"""Produit un candidat F37 soudé/indexé sans remplacer le STL canonique.

Le problème visé est la divergence entre un audit local manifold sur le STL
et la règle NVIDIA Asset Validator VG.007 après conversion USD. Le script garde
le STL source intact, effectue un aller-retour Manifold déterministe, exporte
un STL candidat et un USDA explicitement indexé, puis mesure les dérives et
les interfaces. Il refuse le rapport final sans une revalidation NVIDIA externe
liée par empreinte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from manifold3d import Manifold, Mesh
import numpy as np
from scipy.spatial import cKDTree
import trimesh

from build_f37_printable_head_mesh import (
    audit_planar_pads,
    create_head_pads,
    intersection_volume,
    load_flow_mesh,
    load_mesh,
    strict_vertex_manifold_audit,
    topology,
)


NVIDIA_RULE = "VG.007"
MAX_VOLUME_RELATIVE_DELTA = 1.0e-7
MAX_VERTEX_SET_HAUSDORFF_MM = 1.0e-5
MAX_BOUNDS_DELTA_MM = 1.0e-5


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_validation_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    issue_counts = report.get("issue_counts", {})
    vg007 = [item for item in report.get("issues", []) if "VG.007" in str(item.get("requirement", ""))]
    count = 0
    if vg007:
        match = re.search(r"(\d+) vertices are non-manifold", str(vg007[0].get("message", "")))
        if match is None:
            raise SystemExit(f"compteur VG.007 illisible dans {path}")
        count = int(match.group(1))
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "status": report.get("status"),
        "passed": bool(report.get("passed", False)),
        "issue_counts": issue_counts,
        "vg007_non_manifold_vertex_count": count,
        "geometry_clear": bool(
            report.get("status") == "PASS"
            and all(int(issue_counts.get(level, 0)) == 0 for level in ("ERROR", "FAILURE", "INFO", "WARNING"))
        ),
    }


def clean_and_roundtrip(source: trimesh.Trimesh) -> tuple[trimesh.Trimesh, str]:
    """Reconstruit l'indexation via Manifold sans lissage ni voxelisation."""

    clean = source.copy()
    clean.update_faces(clean.nondegenerate_faces())
    clean.update_faces(clean.unique_faces())
    clean.remove_unreferenced_vertices()
    clean.merge_vertices()
    trimesh.repair.fix_normals(clean, multibody=True)
    manifold = Manifold(
        mesh=Mesh(
            vert_properties=np.asarray(clean.vertices, dtype=np.float32),
            tri_verts=np.asarray(clean.faces, dtype=np.uint32),
        )
    )
    status = str(manifold.status())
    result = manifold.to_mesh()
    candidate = trimesh.Trimesh(
        vertices=np.asarray(result.vert_properties[:, :3], dtype=np.float64),
        faces=np.asarray(result.tri_verts, dtype=np.int64),
        process=False,
    )
    candidate.remove_unreferenced_vertices()
    candidate.merge_vertices()
    trimesh.repair.fix_normals(candidate, multibody=True)
    return candidate, status


def indexed_edge_audit(mesh: trimesh.Trimesh) -> dict[str, Any]:
    edges = np.asarray(mesh.edges_sorted, dtype=np.int64)
    unique_edges, counts = np.unique(edges, axis=0, return_counts=True)
    border = unique_edges[counts == 1]
    overused = unique_edges[counts > 2]
    border_degree = np.bincount(border.reshape(-1), minlength=len(mesh.vertices)) if len(border) else np.zeros(len(mesh.vertices), dtype=np.int64)
    return {
        "method": "explicit_index_edge_incidence",
        "unique_edge_count": int(len(unique_edges)),
        "border_edge_count": int(len(border)),
        "edge_count_above_two_faces": int(len(overused)),
        "vertices_with_more_than_two_border_edges": int(np.count_nonzero(border_degree > 2)),
        "maximum_border_edge_degree": int(border_degree.max(initial=0)),
        "nvidia_vg007_proxy_pass": bool(len(overused) == 0 and np.count_nonzero(border_degree > 2) == 0),
    }


def symmetric_vertex_set_hausdorff(first: trimesh.Trimesh, second: trimesh.Trimesh) -> dict[str, float]:
    """Distance de Hausdorff des ensembles de sommets, pas de toute la surface."""

    first_vertices = np.asarray(first.vertices, dtype=np.float64)
    second_vertices = np.asarray(second.vertices, dtype=np.float64)
    first_to_second = cKDTree(second_vertices).query(first_vertices, workers=-1)[0]
    second_to_first = cKDTree(first_vertices).query(second_vertices, workers=-1)[0]
    return {
        "first_to_second_max_mm": float(first_to_second.max(initial=0.0)),
        "second_to_first_max_mm": float(second_to_first.max(initial=0.0)),
        "symmetric_max_mm": float(max(first_to_second.max(initial=0.0), second_to_first.max(initial=0.0))),
        "p99_mm": float(max(np.quantile(first_to_second, 0.99), np.quantile(second_to_first, 0.99))),
        "limitation": "Hausdorff des ensembles de sommets; le volume, l'aire et les limites complètent le contrôle, sans constituer une métrologie CMM/CT.",
    }


def write_indexed_usda(path: Path, mesh: trimesh.Trimesh) -> None:
    """Écrit un Mesh USD dont les points partagés ont un indice unique."""

    bounds = np.asarray(mesh.bounds, dtype=np.float64)
    with path.open("w", encoding="utf-8") as stream:
        stream.write("#usda 1.0\n(\n    defaultPrim = \"F37Head\"\n    metersPerUnit = 0.001\n    upAxis = \"Z\"\n)\n\n")
        stream.write('def Xform "F37Head"\n{\n    def Mesh "Head"\n    {\n')
        stream.write(
            "        float3[] extent = "
            f"[({bounds[0, 0]:.9g}, {bounds[0, 1]:.9g}, {bounds[0, 2]:.9g}), "
            f"({bounds[1, 0]:.9g}, {bounds[1, 1]:.9g}, {bounds[1, 2]:.9g})]\n"
        )
        stream.write("        int[] faceVertexCounts = [")
        for start in range(0, len(mesh.faces), 8192):
            if start:
                stream.write(", ")
            stream.write(", ".join("3" for _ in mesh.faces[start : start + 8192]))
        stream.write("]\n        int[] faceVertexIndices = [")
        flattened = np.asarray(mesh.faces, dtype=np.int64).reshape(-1)
        for start in range(0, len(flattened), 8192):
            if start:
                stream.write(", ")
            stream.write(", ".join(str(int(value)) for value in flattened[start : start + 8192]))
        stream.write("]\n        point3f[] points = [\n")
        for index, point in enumerate(np.asarray(mesh.vertices, dtype=np.float64)):
            suffix = "," if index + 1 < len(mesh.vertices) else ""
            stream.write(f"            ({point[0]:.9g}, {point[1]:.9g}, {point[2]:.9g}){suffix}\n")
        stream.write("        ]\n        normal3f[] normals = [\n")
        for index, normal in enumerate(np.asarray(mesh.face_normals, dtype=np.float64)):
            suffix = "," if index + 1 < len(mesh.face_normals) else ""
            stream.write(f"            ({normal[0]:.9g}, {normal[1]:.9g}, {normal[2]:.9g}){suffix}\n")
        stream.write(
            '        ] (\n            interpolation = "uniform"\n        )\n'
            '        uniform token subdivisionScheme = "none"\n    }\n}\n'
        )


def render_comparison(source: trimesh.Trimesh, candidate: trimesh.Trimesh, report: dict[str, Any], output: Path) -> None:
    figure = plt.figure(figsize=(15, 7.8), facecolor="#08131c")
    figure.suptitle("F37 — candidat soudé/indexé pour contre-validation NVIDIA", color="white", fontsize=20, fontweight="bold")
    sample_count = min(85000, len(candidate.vertices))
    indices = np.linspace(0, len(candidate.vertices) - 1, sample_count, dtype=np.int64)
    points = np.asarray(candidate.vertices)[indices]
    for position, (elev, azim, title) in enumerate(((24, -56, "Candidat Manifold"), (88, -90, "Vue des quatre appuis")), start=1):
        axis = figure.add_subplot(1, 3, position, projection="3d", facecolor="#101c25")
        axis.scatter(points[:, 0], points[:, 1], points[:, 2], s=0.18, c="#c9974d", alpha=0.78)
        centre = candidate.bounds.mean(axis=0)
        radius = float(max(candidate.extents)) * 0.57
        axis.set_xlim(centre[0] - radius, centre[0] + radius)
        axis.set_ylim(centre[1] - radius, centre[1] + radius)
        axis.set_zlim(centre[2] - 0.55 * radius, centre[2] + 0.55 * radius)
        axis.set_box_aspect((1.0, 1.0, 0.8))
        axis.view_init(elev=elev, azim=azim)
        axis.set_axis_off()
        axis.set_title(title, color="white", fontsize=11, fontweight="bold")

    axis = figure.add_subplot(1, 3, 3, facecolor="#101c25")
    axis.axis("off")
    comparison = report["comparison_to_source"]
    candidate_topology = report["candidate"]["topology"]
    pad_count = sum(item["planar_surface_detected"] for item in report["interfaces"]["mount_pad_planes"])
    rows = [
        ("Triangles", f"{candidate_topology['triangles']:,}".replace(",", " ")),
        ("Sommets indexés", f"{candidate_topology['vertices']:,}".replace(",", " ")),
        ("Étanche / corps", f"{candidate_topology['watertight']} / {candidate_topology['body_count']}"),
        ("Arêtes de bord", str(report["candidate"]["indexed_edge_audit"]["border_edge_count"])),
        ("Audit local sommets", str(report["candidate"]["strict_vertex_manifold_audit"]["non_manifold_vertex_count"])),
        ("Hausdorff sommets", f"{comparison['vertex_set_hausdorff']['symmetric_max_mm']:.3g} mm"),
        ("Δ volume", f"{comparison['relative_volume_delta']:.3e}"),
        ("Δ limites", f"{comparison['maximum_bounds_delta_mm']:.3g} mm"),
        ("Huile ↔ gaz", f"{report['interfaces']['oil_to_gas_collision_mm3']:.4f} mm³"),
        ("Huile ↔ solide", f"{report['interfaces']['oil_to_candidate_solid_collision_mm3']:.4f} mm³"),
        ("Plans d'appui", f"{pad_count}/4"),
        ("Gate dérive", str(report["gates"]["bounded_geometry_drift"])),
        (
            "NVIDIA STL / OBJ",
            f"{report['inputs']['nvidia_evidence']['official_stl_conversion']['vg007_non_manifold_vertex_count']} / "
            f"{report['inputs']['nvidia_evidence']['official_obj_conversion']['vg007_non_manifold_vertex_count']}",
        ),
        ("NVIDIA USDA direct", "GEOMETRY OK"),
        ("Impression métal", "NON AUTORISÉE"),
    ]
    y = 0.94
    for label, value in rows:
        axis.text(0.04, y, label, color="#9db0bc", fontsize=10.2, transform=axis.transAxes)
        axis.text(0.54, y, value, color="white", fontsize=10.2, fontweight="bold", transform=axis.transAxes)
        y -= 0.058
    axis.text(
        0.04,
        0.015,
        "USDA direct : Geometry propre; conversions officielles STL/OBJ : VG.007.\n"
        "Candidat non promu : échelle, matière, LPBF, fatigue et essais restent ouverts.",
        color="#f2c465",
        fontsize=7.6,
        wrap=True,
        transform=axis.transAxes,
    )
    figure.subplots_adjust(left=0.012, right=0.988, bottom=0.04, top=0.90, wspace=0.025)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-head", type=Path, required=True)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--flow-core", type=Path, required=True)
    parser.add_argument("--oil-core", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--usd-topology-analysis", type=Path, required=True)
    parser.add_argument("--official-stl-geometry-report", type=Path, required=True)
    parser.add_argument("--official-obj-geometry-report", type=Path, required=True)
    parser.add_argument("--direct-usda-geometry-report", type=Path, required=True)
    parser.add_argument("--validation-attestation", type=Path, required=True)
    parser.add_argument("--validated-usda-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=False)
    source_report = json.loads(args.source_report.read_text(encoding="utf-8"))
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    geometry_report = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    topology_analysis = json.loads(args.usd_topology_analysis.read_text(encoding="utf-8"))
    stl_validation = load_validation_report(args.official_stl_geometry_report)
    obj_validation = load_validation_report(args.official_obj_geometry_report)
    usda_validation = load_validation_report(args.direct_usda_geometry_report)
    validation_attestation = json.loads(args.validation_attestation.read_text(encoding="utf-8"))
    if sha256(args.source_head) != source_report["local_only_artifacts"][args.source_head.name]["sha256"]:
        raise SystemExit("le STL source ne correspond pas au rapport F37")

    source = load_mesh(args.source_head, "source_head")
    flow, _ = load_flow_mesh(args.flow_core)
    oil = load_mesh(args.oil_core, "oil_core")
    candidate, manifold_status = clean_and_roundtrip(source)
    candidate_topology = topology(candidate)
    candidate_vertex_audit = strict_vertex_manifold_audit(candidate)
    candidate_edge_audit = indexed_edge_audit(candidate)
    if not candidate_topology["watertight"] or candidate_topology["body_count"] != 1:
        raise SystemExit("le candidat réparé n'est pas un solide étanche mono-corps")

    output_stl = args.output / "917-head-f37-nvidia-welded-candidate.local.stl"
    output_obj = args.output / "917-head-f37-nvidia-welded-candidate.local.obj"
    output_usda = args.output / "917-head-f37-nvidia-welded-candidate.local.usda"
    output_png = args.output / "917-head-f37-nvidia-welded-candidate.png"
    output_report = args.output / "f37-nvidia-mesh-repair-report.json"
    candidate.export(output_stl)
    candidate.export(output_obj)
    # Recharger le STL binaire avant d'ecrire l'USD. L'exporteur STL peut
    # canonicaliser l'ordre des facettes; utiliser exactement ce maillage
    # recharge lie l'USD a l'artefact livre et rend l'indexation reproductible
    # entre arm64 emule et x86 natif.
    reloaded = load_mesh(output_stl, "candidate_stl")
    write_indexed_usda(output_usda, reloaded)
    if sha256(output_usda) != args.validated_usda_sha256:
        raise SystemExit("le USDA produit ne correspond pas au SHA-256 revalidé par NVIDIA")
    if validation_attestation["linkage"]["asset"]["sha256"] != sha256(output_usda):
        raise SystemExit("l'attestation ne référence pas le USDA produit")
    if validation_attestation["linkage"]["source_stl"]["sha256"] != sha256(args.source_head):
        raise SystemExit("l'attestation ne référence pas le STL tête source exact")
    if validation_attestation["linkage"]["normalized_report"]["sha256"] != sha256(
        args.direct_usda_geometry_report
    ):
        raise SystemExit("l'attestation ne référence pas le rapport NVIDIA fourni")
    if not validation_attestation["linkage"].get("command_matches_report_asset_path", False):
        raise SystemExit("la commande attestée ne cible pas l'asset du rapport NVIDIA")
    if not validation_attestation["gates"].get("container_image_digest_pinned", False):
        raise SystemExit("l'image NVIDIA attestée n'est pas verrouillée par digest")
    if not validation_attestation["result"].get("geometry_clear", False):
        raise SystemExit("l'attestation ne porte pas un PASS Geometry sans issue")
    source_vg007 = source_report["nvidia_asset_validator_observation"]["non_manifold_vertex_count"]
    if source_vg007 != validation_attestation["result"].get(
        "source_official_conversion_vg007_non_manifold_vertices"
    ):
        raise SystemExit("le compteur VG.007 du rapport tête diverge de l'attestation")
    if source_vg007 != stl_validation["vg007_non_manifold_vertex_count"]:
        raise SystemExit("les deux routes STL NVIDIA ne reproduisent pas le même compteur VG.007")
    source_topology = topology(source)
    reloaded_topology = topology(reloaded)
    hausdorff = symmetric_vertex_set_hausdorff(source, reloaded)
    relative_volume_delta = abs(reloaded.volume - source.volume) / abs(source.volume)
    maximum_bounds_delta = float(np.max(np.abs(np.asarray(reloaded.bounds) - np.asarray(source.bounds))))
    oil_gas_volume, oil_gas_method, _ = intersection_volume(oil, flow)
    oil_solid_volume, oil_solid_method, _ = intersection_volume(oil, reloaded)
    _, _, stud_centres, pad_radius, pad_plane_z, _ = create_head_pads(geometry_report, contract, source)
    pad_planes = audit_planar_pads(reloaded, stud_centres, pad_radius, pad_plane_z)

    bounded_geometry_drift = bool(
        relative_volume_delta <= MAX_VOLUME_RELATIVE_DELTA
        and hausdorff["symmetric_max_mm"] <= MAX_VERTEX_SET_HAUSDORFF_MM
        and maximum_bounds_delta <= MAX_BOUNDS_DELTA_MM
    )
    interface_geometry_preserved = bool(
        math.isfinite(oil_gas_volume)
        and oil_gas_volume <= 0.01
        and math.isfinite(oil_solid_volume)
        and oil_solid_volume <= 0.01
        and all(item["planar_surface_detected"] for item in pad_planes)
    )
    local_topology_pass = bool(
        reloaded_topology["watertight"]
        and reloaded_topology["body_count"] == 1
        and candidate_vertex_audit["strict_vertex_manifold"]
        and candidate_edge_audit["nvidia_vg007_proxy_pass"]
    )

    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "phase": "F37_nvidia_mesh_repair_candidate",
        "status": "nvidia_direct_usda_geometry_pass_official_conversion_and_manufacturing_release_blocked",
        "cause_analysis": {
            "source_local_strict_vertex_audit_count": source_report["strict_vertex_manifold_audit"]["non_manifold_vertex_count"],
            "source_nvidia_vg007_count": source_report["nvidia_asset_validator_observation"]["non_manifold_vertex_count"],
            "nvidia_definition": "VG.007 ManifoldChecker compte notamment les sommets portant plus de deux arêtes de bord.",
            "working_hypothesis": "La conversion STL vers USD a conservé ou créé des coutures d'indexation invisibles après le process=True de Trimesh.",
            "hypothesis_confirmed": bool(topology_analysis["conclusion"]["conversion_indexing_cause_confirmed"]),
            "confirmation": topology_analysis["conclusion"]["explanation"],
            "cross_conversion_observation": {
                "official_stl_vg007": stl_validation["vg007_non_manifold_vertex_count"],
                "official_obj_vg007": obj_validation["vg007_non_manifold_vertex_count"],
                "direct_indexed_usda_geometry_clear": usda_validation["geometry_clear"],
            },
        },
        "inputs": {
            "source_head": {"path": args.source_head.name, "bytes": args.source_head.stat().st_size, "sha256": sha256(args.source_head)},
            "source_report": {"path": args.source_report.name, "bytes": args.source_report.stat().st_size, "sha256": sha256(args.source_report)},
            "flow_core": {"path": args.flow_core.name, "sha256": sha256(args.flow_core)},
            "oil_core": {"path": args.oil_core.name, "sha256": sha256(args.oil_core)},
            "contract_sha256": sha256(args.contract),
            "geometry_report_sha256": sha256(args.geometry_report),
            "nvidia_evidence": {
                "usd_topology_analysis": {
                    "path": args.usd_topology_analysis.name,
                    "bytes": args.usd_topology_analysis.stat().st_size,
                    "sha256": sha256(args.usd_topology_analysis),
                },
                "official_stl_conversion": stl_validation,
                "official_obj_conversion": obj_validation,
                "direct_indexed_usda": usda_validation,
                "geometry_validation_attestation": {
                    "path": args.validation_attestation.name,
                    "bytes": args.validation_attestation.stat().st_size,
                    "sha256": sha256(args.validation_attestation),
                },
                "validated_usda_sha256": args.validated_usda_sha256,
            },
        },
        "method": {
            "repair": "remove degenerate/duplicate faces, weld, fix normals, Manifold float32 identity roundtrip, weld, export",
            "smoothing": False,
            "voxelization": False,
            "manifold_status": manifold_status,
            "usd_companion": "explicit unique point array, shared faceVertexIndices and uniform per-face normals; bypasses STL triangle-soup ambiguity",
        },
        "source": {"topology": source_topology},
        "candidate": {
            "topology": reloaded_topology,
            "strict_vertex_manifold_audit": candidate_vertex_audit,
            "indexed_edge_audit": candidate_edge_audit,
        },
        "comparison_to_source": {
            "vertex_set_hausdorff": hausdorff,
            "relative_volume_delta": float(relative_volume_delta),
            "absolute_volume_delta_mm3": float(abs(reloaded.volume - source.volume)),
            "relative_surface_area_delta": float(abs(reloaded.area - source.area) / source.area),
            "maximum_bounds_delta_mm": maximum_bounds_delta,
            "limits": {
                "maximum_relative_volume_delta": MAX_VOLUME_RELATIVE_DELTA,
                "maximum_vertex_set_hausdorff_mm": MAX_VERTEX_SET_HAUSDORFF_MM,
                "maximum_bounds_delta_mm": MAX_BOUNDS_DELTA_MM,
            },
        },
        "interfaces": {
            "oil_to_gas_collision_mm3": float(oil_gas_volume),
            "oil_to_gas_method": oil_gas_method,
            "oil_to_candidate_solid_collision_mm3": float(oil_solid_volume),
            "oil_to_candidate_solid_method": oil_solid_method,
            "mount_pad_planes": pad_planes,
            "source_opening_proof_preserved_by_bounded_geometry_gate": bool(
                bounded_geometry_drift and source_report["gates"]["all_declared_accesses_cross_parent_skin"]
            ),
        },
        "gates": {
            "bounded_geometry_drift": bounded_geometry_drift,
            "local_watertight_single_body_and_manifold": local_topology_pass,
            "oil_gas_and_mount_interfaces_preserved": interface_geometry_preserved,
            "nvidia_asset_validator_vg007_candidate_clear": stl_validation["vg007_non_manifold_vertex_count"] == 0,
            "nvidia_explicit_index_usda_geometry_clear": usda_validation["geometry_clear"],
            "official_stl_or_obj_conversion_geometry_clear": bool(
                stl_validation["geometry_clear"] or obj_validation["geometry_clear"]
            ),
            "candidate_promotion_authorized": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "limitations": [
            "Le STL ne stocke pas une table de sommets indexée; le USDA/OBJ compagnon est la preuve d'indexation explicite.",
            "Le USDA indexé direct passe Geometry, mais les routes officielles STL et OBJ restent en avertissement VG.007; leur conversion doit être corrigée avant promotion.",
            "L'attestation lie par SHA-256 le USDA et le rapport NVIDIA normalisé du run déclaré; elle ne conserve pas le rapport brut temporaire et ne signe pas la machine Vast.",
            "Les rapports normalisés des routes officielles STL/OBJ ne consignent pas le SHA de leur fichier source; leurs résultats restent un diagnostic de conversion et non une preuve de fabrication.",
            "La distance de Hausdorff calculée porte sur les ensembles de sommets et ne remplace pas une métrologie surfacique CMM/CT.",
            "Aucune correction topologique ne lève les blocages d'échelle, matière, LPBF, fatigue ou essais physiques.",
        ],
        "local_only_artifacts": {},
    }
    render_comparison(source, reloaded, report, output_png)
    for artifact in (output_stl, output_obj, output_usda, output_png):
        report["local_only_artifacts"][artifact.name] = {
            "bytes": artifact.stat().st_size,
            "sha256": sha256(artifact),
        }
    save_json(output_report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
