#!/usr/bin/env python3
"""Rend quatre vues et une coupe de la peau externe F43, sans arêtes affichées."""

from __future__ import annotations

import argparse
from pathlib import Path

import vtk


BACKGROUND = (0.025, 0.06, 0.085)
GOLD = (0.74, 0.43, 0.16)


def text_actor(text: str, x: int, y: int, size: int = 22) -> vtk.vtkTextActor:
    actor = vtk.vtkTextActor()
    actor.SetInput(text)
    actor.SetPosition(x, y)
    prop = actor.GetTextProperty()
    prop.SetFontFamilyToArial()
    prop.SetFontSize(size)
    prop.SetBold(True)
    prop.SetColor(0.94, 0.96, 0.97)
    return actor


def read_surface(path: Path) -> vtk.vtkPolyData:
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(path))
    reader.Update()
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(reader.GetOutputPort())
    normals.ComputePointNormalsOn()
    normals.ComputeCellNormalsOff()
    normals.SplittingOff()
    normals.ConsistencyOn()
    normals.AutoOrientNormalsOn()
    normals.Update()
    return normals.GetOutput()


def actor_for(polydata: vtk.vtkPolyData) -> vtk.vtkActor:
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(polydata)
    mapper.ScalarVisibilityOff()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*GOLD)
    actor.GetProperty().SetInterpolationToPBR()
    actor.GetProperty().SetMetallic(0.35)
    actor.GetProperty().SetRoughness(0.34)
    actor.GetProperty().EdgeVisibilityOff()
    return actor


def camera_for(renderer: vtk.vtkRenderer, polydata: vtk.vtkPolyData, direction: tuple[float, float, float]) -> None:
    bounds = polydata.GetBounds()
    center = tuple((bounds[axis] + bounds[axis + 1]) * 0.5 for axis in (0, 2, 4))
    diagonal = sum((bounds[axis + 1] - bounds[axis]) ** 2 for axis in (0, 2, 4)) ** 0.5
    norm = sum(value * value for value in direction) ** 0.5
    unit = tuple(value / norm for value in direction)
    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(*center)
    camera.SetPosition(*(center[index] + 1.55 * diagonal * unit[index] for index in range(3)))
    camera.SetViewUp(0.0, 0.0, 1.0)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(0.58 * max(bounds[3] - bounds[2], bounds[5] - bounds[4]))


def write_window(window: vtk.vtkRenderWindow, output: Path) -> None:
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.SetScale(2)
    capture.SetInputBufferTypeToRGB()
    capture.ReadFrontBufferOff()
    capture.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(output))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()


def render_four_views(polydata: vtk.vtkPolyData, output: Path) -> None:
    window = vtk.vtkRenderWindow()
    window.SetSize(1500, 1000)
    window.SetOffScreenRendering(1)
    views = (
        ((0.0, -1.0, 0.18), (0.0, 0.5, 0.5, 1.0), "Face admission"),
        ((0.0, 1.0, 0.18), (0.5, 0.5, 1.0, 1.0), "Face echappement"),
        ((1.0, 0.0, 0.12), (0.0, 0.0, 0.5, 0.5), "Profil lateral"),
        ((1.0, -1.0, 0.72), (0.5, 0.0, 1.0, 0.5), "Perspective"),
    )
    for index, (direction, viewport, title) in enumerate(views):
        renderer = vtk.vtkRenderer()
        renderer.SetViewport(*viewport)
        renderer.SetBackground(*BACKGROUND)
        renderer.SetUseDepthPeeling(True)
        renderer.AddActor(actor_for(polydata))
        renderer.AddActor2D(text_actor(title, 24, 25, 19))
        if index == 0:
            renderer.AddActor2D(
                text_actor("F43 — peau externe issue des contours du scan — zero ellipse globale", 24, 450, 18)
            )
        camera_for(renderer, polydata, direction)
        window.AddRenderer(renderer)
    write_window(window, output)


def render_section(polydata: vtk.vtkPolyData, output: Path) -> None:
    bounds = polydata.GetBounds()
    center = tuple((bounds[axis] + bounds[axis + 1]) * 0.5 for axis in (0, 2, 4))
    plane = vtk.vtkPlane()
    plane.SetOrigin(*center)
    plane.SetNormal(1.0, 0.0, 0.0)
    planes = vtk.vtkPlaneCollection()
    planes.AddItem(plane)
    clip = vtk.vtkClipClosedSurface()
    clip.SetInputData(polydata)
    clip.SetClippingPlanes(planes)
    clip.GenerateFacesOn()
    clip.Update()

    window = vtk.vtkRenderWindow()
    window.SetSize(1500, 950)
    window.SetOffScreenRendering(1)
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(*BACKGROUND)
    renderer.AddActor(actor_for(clip.GetOutput()))
    renderer.AddActor2D(text_actor("F43 — coupe de la reconstruction de peau", 35, 880, 28))
    renderer.AddActor2D(
        text_actor("BASELINE EXTERNE SEULEMENT — aucune chambre, conduit, siege ou galerie valide", 35, 35, 19)
    )
    renderer.AddActor2D(text_actor("Peau non ovale issue des contours du scan", 35, 835, 18))
    camera_for(renderer, clip.GetOutput(), (1.0, -0.08, 0.08))
    window.AddRenderer(renderer)
    write_window(window, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path, required=True)
    parser.add_argument("--four-views", type=Path, required=True)
    parser.add_argument("--section", type=Path, required=True)
    args = parser.parse_args()
    args.four_views.parent.mkdir(parents=True, exist_ok=True)
    args.section.parent.mkdir(parents=True, exist_ok=True)
    surface = read_surface(args.stl)
    render_four_views(surface, args.four_views)
    render_section(surface, args.section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
