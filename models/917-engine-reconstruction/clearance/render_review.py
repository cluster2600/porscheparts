#!/usr/bin/env python3
"""Render the real comparison GLB and sampled contact-volume curves."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "models/917-engine-reconstruction/source"))
sys.path.insert(0, str(ROOT / "twins/reference-917-engine/source"))
from reconstruct import check_output, save, sha256


def render(run, output):
    import vtk
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from render_scan_contour_patch_reconstruction_f43 import text_actor
    output = check_output(output)
    report = json.loads((run / "contact-report.json").read_text())
    if report["manufacturing_authorized"] is not False or len(report["records"]) != 384:
        raise ValueError("Wrong contact report")
    glb = run / "head-interface-comparison.glb"
    before = sha256(glb)
    output.mkdir(parents=True, mode=0o700)
    window = vtk.vtkRenderWindow()
    window.SetSize(2400, 1400)
    window.SetOffScreenRendering(1)
    importer = vtk.vtkGLTFImporter()
    importer.SetFileName(str(glb))
    importer.SetRenderWindow(window)
    if not importer.Update():
        raise ValueError("GLB import failed")
    actors = list(importer.GetImportedActors())
    if len(actors) != 12:
        raise ValueError("Incomplete comparison")
    names = {int(n.attrib["flat_actor_id"]): n.attrib["label"] for n in ET.fromstring(
        importer.GetSceneHierarchy().SerializeToXML(vtk.vtkIndent())).iter() if "flat_actor_id" in n.attrib}
    window.RemoveRenderer(importer.GetRenderer())
    for i, (variant, title, tint) in enumerate((
            ("inherited", "Soupapes héritées : contacts cylindre et piston", (.73, .42, .22)),
            ("compact_candidate", "Silhouettes compactes 34 / 29 mm : implantation candidate", (.15, .58, .67)))):
        renderer = vtk.vtkRenderer()
        renderer.SetViewport(i * .5, 0, (i + 1) * .5, 1)
        renderer.SetBackground(.035, .065, .085)
        for index, actor in enumerate(actors):
            if not names[index].startswith(variant + "_"):
                continue
            actor.GetMapper().ScalarVisibilityOff()
            prop = actor.GetProperty()
            prop.SetColor(*tint)
            prop.SetInterpolationToPhong()
            prop.SetAmbient(.3)
            prop.SetOpacity(1)
            prop.SetRepresentationToSurface()
            if names[index].endswith(("_cylinder", "_piston")):
                plane = vtk.vtkPlane(); plane.SetOrigin(0, 0, -.035); plane.SetNormal(0, 0, 1)
                actor.GetMapper().AddClippingPlane(plane)
                prop.SetColor(.60, .67, .69)
            if names[index].endswith("_cylinder"):
                plane = vtk.vtkPlane(); plane.SetOrigin(0, 0, 0); plane.SetNormal(0, 1, 0)
                actor.GetMapper().AddClippingPlane(plane)
            renderer.AddActor(actor)
        renderer.AddViewProp(text_actor(title, 28, 1330, 28))
        renderer.AddViewProp(text_actor("Piston au PMH / levée 2 mm — pose diagnostique\nCylindre en demi-coupe ; bas masqué à z = -35 mm\nSurfaces opaques ; maillages source conservés\nSilhouettes sans définition de siège, tulipe ni congé\nCONCEPT NON QUALIFIÉ — aucun calage validé", 28, 70, 24))
        camera = renderer.GetActiveCamera()
        camera.SetPosition(.8, -1.6, .8); camera.SetFocalPoint(0, 0, 0); camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn(); renderer.ResetCamera()
        window.AddRenderer(renderer)
    try:
        window.Render()
        capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(output / "head-interface-surfaces.png"))
        writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
    finally:
        window.Finalize()
    fig, panels = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for panel, domain, title in zip(panels, ("valve_cylinder", "valve_piston"), ("Soupapes / cylindre", "Soupapes / piston au PMH")):
        for variant, label, color in (("inherited", "Héritées", "#b7743a"), ("compact_candidate", "Silhouettes compactes", "#168aa0")):
            for grid, style in ((1, "--"), (.5, "-")):
                rows = [r for r in report["records"] if r["variant"] == variant and r["grid_mm"] == grid and r["crank_angle_deg"] == 0]
                lifts = sorted({r["lift_mm"] for r in rows})
                values = [sum(r[domain]["volume_mm3_hypothesis"] for r in rows if r["lift_mm"] == lift) for lift in lifts]
                panel.plot(lifts, values, style, marker="o", color=color, label=f"{label} — grille {grid:g} mm")
        panel.set_title(title); panel.set_xlabel("Levée diagnostique (mm supposés)")
        panel.set_ylabel("Somme des intersections par soupape (mm³ supposés)")
        panel.grid(alpha=.2); panel.legend(fontsize=8)
    fig.suptitle("Contacts de maillages — poses échantillonnées, sans loi de came ni qualification physique")
    fig.savefig(output / "contact-volumes.png", dpi=180); plt.close(fig)
    if sha256(glb) != before:
        raise ValueError("GLB changed during render")
    save(output / "render-report.json", {"glb_sha256_before_and_after": before, "source_sha256": sha256(Path(__file__)),
         "files": {p.name: sha256(p) for p in output.glob("*.png")}, "representation": "opaque_surfaces_with_display_clipping_only",
         "point_sampling": False, "geometry_modified": False, "manufacturing_authorized": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.run, args.output)
