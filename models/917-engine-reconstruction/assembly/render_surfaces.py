#!/usr/bin/env python3
"""Render the existing GLB as opaque surfaces, without changing its geometry."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "models/917-engine-reconstruction/source"))
sys.path.insert(0, str(ROOT / "twins/reference-917-engine/source"))
from reconstruct import check_output, save, sha256

MECHANISM = {"cylinder", "piston", "rod", "pin", "crankshaft", "main_bearing",
             "rod_bearing", "piston_ring", "camshaft", "rocker", "rocker_carrier",
             "individual_head", "outer_valve_spring", "inner_valve_spring"}


def render_scene(glb, instances, output):
    import vtk
    from render_scan_contour_patch_reconstruction_f43 import text_actor

    window = vtk.vtkRenderWindow()
    window.SetSize(3200, 2000)
    window.SetOffScreenRendering(1)
    importer = vtk.vtkGLTFImporter()
    importer.SetFileName(str(glb))
    importer.SetRenderWindow(window)
    if not importer.Update():
        raise ValueError("GLB import failed")
    actors = list(importer.GetImportedActors())
    hierarchy = ET.fromstring(importer.GetSceneHierarchy().SerializeToXML(vtk.vtkIndent()))
    rows = {row["instance_id"]: row for row in instances}
    mapped, surfaces = {}, {}
    max_transform_error = 0.0
    for node in hierarchy.iter():
        if "flat_actor_id" not in node.attrib:
            continue
        row = rows[node.attrib["parent_node_name"]]
        name = node.attrib["label"]
        if name != row["family"] or row["instance_id"] in mapped:
            raise ValueError("GLB instance/family mismatch")
        actor = actors[int(node.attrib["flat_actor_id"])]
        for i in range(4):
            for j in range(4):
                expected = row["matrix_mm"][i][j] * (.001 if i < 3 and j == 3 else 1)
                max_transform_error = max(max_transform_error, abs(actor.GetMatrix().GetElement(i, j) - expected))
        if max_transform_error > 1e-6:
            raise ValueError("GLB placement differs from assembly in metres")
        data = actor.GetMapper().GetInput()
        if data.GetNumberOfPolys() == 0 or data.GetNumberOfVerts() or data.GetNumberOfLines():
            raise ValueError("Expected polygon surfaces, not points or lines")
        if name not in surfaces:
            normals = vtk.vtkPolyDataNormals()
            normals.SetInputData(data)
            normals.SplittingOff()
            normals.ConsistencyOff()
            normals.ComputeCellNormalsOff()
            normals.Update()
            surface = normals.GetOutput()
            if (surface.GetNumberOfPoints(), surface.GetNumberOfPolys()) != (
                    data.GetNumberOfPoints(), data.GetNumberOfPolys()):
                raise ValueError("Normal generation changed geometry counts")
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(surface)
            mapper.ScalarVisibilityOff()
            surfaces[name] = mapper
        actor.SetMapper(surfaces[name])
        prop = actor.GetProperty()
        color = (.72, .40, .19) if name.startswith("turbo") else (
            (.15, .52, .65) if name == "individual_head" else (.57, .65, .69))
        prop.SetColor(*color)
        prop.SetInterpolationToPhong()
        prop.SetAmbient(.28)
        prop.SetDiffuse(.75)
        prop.SetSpecular(.25)
        prop.SetSpecularPower(30)
        prop.SetOpacity(1)
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOff()
        mapped[row["instance_id"]] = actor
    if set(mapped) != set(rows) or len(actors) != len(rows):
        raise ValueError("Incomplete imported assembly")
    window.RemoveRenderer(importer.GetRenderer())
    mechanism = MECHANISM | {name for name in surfaces if name.startswith("head_component_")}
    plans = [
        ("Assemblage complet — 12 culasses 4V / 2 turbos", set(surfaces), (0, .5, .5, 1)),
        ("Mécanisme et culasses — carters et services masqués", mechanism, (.5, .5, 1, 1)),
        ("Demi-carter à nervures ramifiées et vilebrequin", {"crankcase_positive", "crankshaft"}, (0, 0, .5, .5)),
    ]
    counts = {}
    for title, families, viewport in plans:
        renderer = vtk.vtkRenderer()
        renderer.SetViewport(*viewport)
        renderer.SetBackground(.035, .065, .085)
        selected = [mapped[row["instance_id"]] for row in instances if row["family"] in families]
        for actor in selected:
            renderer.AddActor(actor)
        renderer.AddViewProp(text_actor(title, 35, 935, 30))
        camera = renderer.GetActiveCamera()
        camera.SetPosition(.9, -1.6, 1.1)
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        renderer.ResetCamera()
        renderer.ResetCameraClippingRange()
        window.AddRenderer(renderer)
        counts[title] = len(selected)
    renderer = vtk.vtkRenderer()
    renderer.SetViewport(.5, 0, 1, .5)
    renderer.SetBackground(.035, .065, .085)
    renderer.AddViewProp(text_actor(
        f"PicoGK — conception inspirée de la 917\n\n{len(surfaces)} définitions / {len(rows)} occurrences\n"
        "Surfaces opaques, ombrées — triangles complets\nAucune simplification des maillages\n\n"
        "Bleu : culasses héritées / cuivre : turbos\nCouleurs de lecture, matériaux non qualifiés\n\n"
        "Alésage/course FIA : 85 / 66 mm\nInterfaces modernes : hypothèses\n"
        "Culasses/alésage : incompatibilité détectée\n\nCONCEPT NON QUALIFIÉ POUR FABRICATION", 45, 110, 30))
    window.AddRenderer(renderer)
    try:
        # Native resolution avoids tiled capture moving text over the geometry.
        window.Render()
        capture = vtk.vtkWindowToImageFilter()
        capture.SetInput(window)
        capture.ReadFrontBufferOff()
        capture.Update()
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(output))
        writer.SetInputConnection(capture.GetOutputPort())
        writer.Write()
    finally:
        window.Finalize()
    if not output.is_file() or output.stat().st_size == 0:
        raise ValueError("Missing rendered PNG")
    return {"prototypes": len(surfaces), "instances": len(rows), "view_instances": counts,
            "prototype_triangles": sum(m.GetInput().GetNumberOfPolys() for m in surfaces.values()),
            "representation": "opaque_shaded_polygon_surfaces", "opacity": 1,
            "max_actor_transform_error_m": max_transform_error,
            "point_sampling": False, "decimation": False, "vtk_version": vtk.vtkVersion.GetVTKVersion()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = check_output(args.output)
    glb = args.delivery / "engine-4v-biturbo-concept.glb"
    assembly = args.delivery / "assembly.json"
    receipt = json.loads((HERE / "execution-20261011.json").read_text())
    before = sha256(glb)
    if before != receipt["glb_roundtrip"]["sha256"]:
        raise ValueError("GLB differs from the geometry execution receipt")
    instances = json.loads(assembly.read_text())["instances"]
    output.mkdir(parents=True, mode=0o700)
    image = output / "engine-4v-biturbo-surfaces.png"
    report = render_scene(glb, instances, image)
    if sha256(glb) != before or (report["prototypes"], report["instances"]) != (119, 1129):
        raise ValueError("Geometry changed or assembly incomplete")
    report.update({"glb_sha256_before_and_after": before, "assembly_sha256": sha256(assembly),
                   "image_sha256": sha256(image), "source_sha256": {
                       str(p.relative_to(ROOT)): sha256(p) for p in (
                           Path(__file__).resolve(), ROOT / "twins/reference-917-engine/source/render_scan_contour_patch_reconstruction_f43.py",
                           ROOT / "models/917-engine-reconstruction/source/reconstruct.py")},
                   "manufacturing_authorized": False, "physical_fit_verified": False,
                   "material_qualification": False})
    save(output / "render-report.json", report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
