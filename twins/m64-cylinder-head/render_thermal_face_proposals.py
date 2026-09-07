#!/usr/bin/env python3
"""Render source-bound candidate groups and a coloured diagnostic section."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


PALETTE = {
    "inherited_surface_review": ("#acb5bf", "Surface héritée F43 — à revoir"),
    "inherited_horizontal_surface_review": ("#acb5bf", "Surface horizontale F43 — à revoir"),
    "inherited_trimmed_surface_review": ("#7d98ad", "Surface F43 découpée — à revoir"),
    "inherited_trimmed_horizontal_review": ("#ca88a5", "Plan F43 découpé — fonction à définir"),
    "unresolved": ("#df4495", "Non résolu"),
    "bore_chamber_or_cylinder_interface": ("#ae7e42", "Chambre / registre candidat"),
    "intake_gas": ("#258ed1", "Admission candidate"),
    "exhaust_gas": ("#ef5b35", "Échappement candidat"),
    "seat_contact": ("#f0b928", "Logements de sièges candidats"),
    "spark_plug_contact": ("#7330a2", "Logement de bougie candidat"),
    "guide_contact_or_open_bore": ("#535ad0", "Guides / perçages candidats"),
    "oil_candidate": ("#3a987a", "Galerie huile candidate"),
    "oil_or_cleanout_plug": ("#3a987a", "Huile / bouchons candidats"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--helpers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cut-x", type=float, required=True)
    args = parser.parse_args()
    proposals = json.loads(args.proposals.read_text())
    if hashlib.sha256(args.step.read_bytes()).hexdigest() != proposals["source_sha256"]["step"]:
        raise ValueError("render_STEP_hash_mismatch")
    if args.output.exists():
        raise FileExistsError(args.output)
    sys.path.insert(0, str(args.helpers))
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgba
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Patch
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from audit_brep_f42 import read_step, indexed_shapes
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    shape = read_step(args.step)[0]
    mesher = BRepMesh_IncrementalMesh(shape, .15, False, .2, False)
    if not mesher.IsDone():
        raise RuntimeError("tessellation_failed")
    faces = indexed_shapes(shape, TopAbs_FACE)
    groups = {row["face_id"]: row["candidate_group"] for row in proposals["faces"]}
    if set(groups) != set(range(1, faces.Extent()+1)):
        raise ValueError("proposal_face_coverage_mismatch")
    triangles, colors, segments, section_colors = [], [], [], []
    for index in range(1, faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(index))
        location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh is None:
            raise RuntimeError("face_missing_tessellation")
        color = to_rgba(PALETTE.get(groups[index], ("#df4495", "Ambigu"))[0])
        for j in range(1, mesh.NbTriangles()+1):
            triangle = np.asarray([mesh.Node(node).Transformed(location.Transformation()).Coord()
                                   for node in mesh.Triangle(j).Get()])
            triangles.append(triangle)
            colors.append(color)
            distances = triangle[:, 0] - args.cut_x
            hits = []
            for a, b in ((0, 1), (1, 2), (2, 0)):
                if distances[a]*distances[b] < 0:
                    point = triangle[a] + (triangle[b]-triangle[a]) * (-distances[a])/(distances[b]-distances[a])
                    hits.append(point[1:])
            if len(hits) == 2:
                segments.append(hits)
                section_colors.append(color)
    triangles, colors = np.asarray(triangles), np.asarray(colors)
    if not segments:
        raise ValueError("empty_section")
    args.output.mkdir(parents=True)
    fig = plt.figure(figsize=(17, 9), facecolor="#f5f7fa")
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    normal = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], 1e-20)
    light = np.array([.3, -.4, .85]); light /= np.linalg.norm(light)
    colors[:, :3] *= (.5 + .5*np.abs(normal @ light))[:, None]
    ax.add_collection3d(Poly3DCollection(triangles, facecolors=colors, edgecolor="none"))
    bounds = np.stack((triangles.min(axis=(0, 1)), triangles.max(axis=(0, 1))))
    center = bounds.mean(axis=0); radius = max(bounds[1]-bounds[0])*.52
    ax.set_xlim(center[0]-radius, center[0]+radius)
    ax.set_ylim(center[1]-radius, center[1]+radius)
    ax.set_zlim(center[2]-radius, center[2]+radius)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=27, azim=-55)
    ax.set_axis_off(); ax.set_title("STEP F53 actuel — groupes proposés", fontsize=15)
    section = fig.add_subplot(1, 2, 2)
    section.add_collection(LineCollection(segments, colors=section_colors, linewidths=1.7))
    section.autoscale(); section.set_aspect("equal")
    section.set_xlabel("Y — unité du scan"); section.set_ylabel("Z — unité du scan")
    section.set_title(f"Coupe X = {args.cut_x:g} — groupes par face", fontsize=15)
    section.grid(alpha=.2)
    used = sorted(set(groups.values()))
    fig.legend(handles=[Patch(color=PALETTE.get(key, ("#df4495", "Ambigu"))[0],
                              label=PALETTE.get(key, ("#df4495", "Ambigu"))[1]) for key in used],
               loc="lower center", ncol=3, fontsize=10, bbox_to_anchor=(.5, .075))
    fig.suptitle("Référence 935 issue du scan — préparation des frontières thermiques", fontsize=19, weight="bold", y=.96)
    fig.text(.5, .035, "Couleurs = propositions de classification, PAS températures.\n"
             "Aucune condition thermique affectée — interfaces M64 et fabrication non validées.", ha="center", fontsize=11)
    fig.subplots_adjust(top=.86, bottom=.29, left=.02, right=.98, wspace=.07)
    path = args.output / "thermal-face-proposals-and-section.png"
    fig.savefig(path, dpi=125, facecolor=fig.get_facecolor()); plt.close(fig)
    report = {"source_step_sha256": proposals["source_sha256"]["step"],
              "proposals_sha256": hashlib.sha256(args.proposals.read_bytes()).hexdigest(),
              "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "triangle_count": len(triangles), "cut_x_scan_units": args.cut_x,
              "section_segment_count": len(segments), "tessellation_deflection_scan_units": .15,
              "colors_are_temperature": False, "geometry_modified": False}
    (args.output / "render-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
