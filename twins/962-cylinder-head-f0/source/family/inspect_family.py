"""Inspect actual family meshes without transferring the old 4 L thermal budget."""
import hashlib
import importlib.util
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_libraries(installation):
    for directory, reference, pattern in (
        ("LEAP71_ShapeKernel", "architecture/references.json", "ShapeKernel/**/*.cs"),
        ("LEAP71_LatticeLibrary", "bionic/references.json", "LatticeLibrary/**/*.cs"),
    ):
        folder = installation / "libraries" / directory
        data = json.loads((SOURCE.parent / reference).read_text())
        data = data.get("library", data)
        if ({str(p.relative_to(folder)): sha(p) for p in folder.glob(pattern)} != data["source_hashes"]
                or sha(folder / "LICENSE") != data["license_sha256"]):
            raise ValueError("Library differs from the retained source: " + directory)


def render(polys, config, output):
    import vtk
    closed = load("family_closed_cut", SOURCE.parent / "enclosed/render_enclosed.py")
    output.mkdir()
    scenes = (
        ("exterior", [("solid", (.72, .75, .78), 1)]),
        ("cutaway", [("solid", (.72, .75, .78), 1), ("coolant", (.08, .55, .95), 1),
                     ("dry-passages", (.95, .48, .14), .45)]),
        ("coolant", [("solid", (.65, .70, .75), .10), ("coolant", (.08, .55, .95), 1)]),
        ("chamber", [("solid", (.72, .75, .78), 1)]),
    )
    for name, components in scenes:
        window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1400, 1050)
        renderer = vtk.vtkRenderer(); renderer.SetBackground(.035, .05, .075)
        renderer.SetBackground2(.10, .14, .19); renderer.GradientBackgroundOn(); window.AddRenderer(renderer)
        for part, colour, opacity in components:
            poly = closed.cut_left(polys[part]) if name == "cutaway" and part == "solid" else polys[part]
            normals = vtk.vtkPolyDataNormals(); normals.SetInputData(poly); normals.SetFeatureAngle(45)
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort()); mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor(); actor.SetMapper(mapper)
            prop = actor.GetProperty(); prop.SetColor(*colour); prop.SetOpacity(opacity)
            prop.SetInterpolationToPhong(); prop.SetSpecular(.35); prop.SetSpecularPower(30); renderer.AddActor(actor)
        label = vtk.vtkTextActor()
        label.SetInput(f"962 C / DERIVE BIONIQUE / ALESAGE {config['geometry']['bore_mm']:g} mm\n"
                       f"{name.upper()} / SOUPAPES 35 et 30.5 mm / ETUDE 0.5 mm\n"
                       "Dimensions publiees + hypotheses - interfaces non mesurees")
        label.SetPosition(30, 30); label.GetTextProperty().SetFontSize(20)
        label.GetTextProperty().SetColor(.90, .94, .98); renderer.AddViewProp(label)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(*((180, -210, -210) if name == "chamber" else (235, -270, 220)))
        camera.SetFocalPoint(0, 0, 30); camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn(); renderer.ResetCamera(); camera.SetParallelScale(125)
        renderer.ResetCameraClippingRange(); window.Render()
        capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.Update()
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(output / (name + ".png")))
        writer.SetInputConnection(capture.GetOutputPort()); writer.Write(); window.Finalize()


def inspect(native, config_path, output):
    if output.exists():
        raise ValueError("Output must be new; retain rejected runs")
    config = json.loads(config_path.read_text())
    fields = json.loads((native / "native-fields-report.json").read_text())
    if fields["variant_id"] != config["id"] or fields["geometry_assumptions_mm"] != config["geometry"]:
        raise ValueError("Native export does not match the supplied variant geometry")
    import numpy as np
    import trimesh
    import vtk
    old = load("family_mesh_checks", SOURCE.parent / "inspect_study.py")
    boundary = load("family_boundary_checks", SOURCE.parent / "audit_coolant_boundaries.py")
    output.mkdir(parents=True)
    polys, meshes, distances, metrics = {}, {}, {}, {}
    for name in ("solid", "coolant", "dry-passages"):
        raw, cleaned = native / (name + ".stl"), output / (name + ".stl")
        removed = old.mesh_tools.remove_degenerate_faces(raw, cleaned)
        mesh = trimesh.load_mesh(cleaned, process=True)
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(cleaned)); reader.Update()
        polys[name], meshes[name] = reader.GetOutput(), mesh
        connectivity = vtk.vtkPolyDataConnectivityFilter(); connectivity.SetInputData(polys[name])
        connectivity.SetExtractionModeToAllRegions(); connectivity.Update()
        metrics[name] = dict(raw_sha256=sha(raw), sha256=sha(cleaned), triangles=len(mesh.faces),
                             volume_mm3=float(mesh.volume), bounds_mm=mesh.bounds.tolist(),
                             watertight=bool(mesh.is_watertight), consistent_winding=bool(mesh.is_winding_consistent),
                             surface_components=connectivity.GetNumberOfExtractedRegions(),
                             finite_vertices=bool(np.isfinite(mesh.vertices).all()), removed_zero_area_faces=removed)
        distance = vtk.vtkImplicitPolyDataDistance(); distance.SetInput(polys[name]); distances[name] = distance
    (output / "mesh-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    if any(not m["watertight"] or not m["consistent_winding"] or not m["finite_vertices"]
           or m["volume_mm3"] <= 0 or m["surface_components"] != 1 for m in metrics.values()):
        raise ValueError("Invalid or disconnected surface; preserve rejected meshes and metrics")
    water = meshes["coolant"]
    samples = np.vstack((water.vertices, water.triangles_center))
    clearance = old.water_dry_clearance(samples, polys["dry-passages"])
    if clearance < 4:
        raise ValueError("Sampled water/dry separation below the unchanged 4 mm screen")
    g = config["geometry"]
    openings = [(x, side * (g["valve_y_mm"] + 3 + (g["guide_top_y_mm"] - g["valve_y_mm"] - 3) * 33 / 75), 58)
                for x in (-g["valve_x_mm"], g["valve_x_mm"]) for side in (-1, 1)]
    openings += [(0, 0, 58), (38, 0, 58), (0, -74, 43), (0, 74, 43)]
    for point in openings:
        if distances["dry-passages"].EvaluateFunction(point) >= 0 or distances["solid"].EvaluateFunction(point) <= 0:
            raise ValueError("Blocked dry opening: " + str(point))
    ports = [boundary.section(polys["coolant"], x)[1] for x in (-75.5, 75.5)]
    rows, _, excluded = boundary.probes(water.triangles_center, water.face_normals,
        distances["solid"].EvaluateFunction, distances["coolant"].EvaluateFunction, (-76, 76))
    if not fields["vdb_domains_equal"] or not fields["all_active_values_checked_bidirectionally"]:
        raise ValueError("Native VDB roundtrip failed")
    render(polys, config, output / "views")
    sources = [p for p in SOURCE.iterdir() if p.is_file()]
    sources += [SOURCE.parent / "inspect_study.py", SOURCE.parent / "audit_coolant_boundaries.py",
                SOURCE.parent / "enclosed/render_enclosed.py"]
    result = dict(status="published_dimensions_and_assumed_bionic_geometry", config=config,
                  config_sha256=sha(config_path), mesh_metrics=metrics, sampled_water_dry_clearance_mm=clearance,
                  clearance_samples=len(samples), dry_opening_probes_mm=openings, coolant_terminal_sections=ports,
                  boundary_probes=rows, excluded_terminal_samples=excluded, native_fields_report=fields,
                  vdb_sha256=sha(native / "head-fields.vdb"),
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in sources},
                  qualification=dict(fitment_validated=False, wall_thickness_qualified=False,
                      historical_fidelity_validated=False, interface_conformity_validated=False,
                      hydraulic_performance_validated=False, thermal_performance_validated=False,
                      strength_validated=False, material_process_qualified=False, manufacturing_authorized=False),
                  images={p.name: sha(p) for p in (output / "views").glob("*.png")})
    (output / "study-report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
