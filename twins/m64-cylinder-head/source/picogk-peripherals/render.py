#!/usr/bin/env python3
"""Actual assembly and section views; never a generative image or physics result."""
import argparse
import json
from pathlib import Path

from audit import checked_parts, load_topology
from prepare import sha, write_json

COLORS = {'head': '#9facb6', 'seat': '#d2a656', 'guide': '#b095da',
          'extended_valve_hypothesis': '#67c5cd', 'spring_seat_hypothesis': '#7ba76e',
          'retainer_without_keeper': '#dadde4', 'keepout_not_spring': '#ebaa43',
          'veined_cover_without_mounts': '#7496ba', 'branched_oil_hypothesis': '#e46e4f'}


def run(inputs, directory, output):
    if output.exists():
        raise FileExistsError(output)
    import vtk
    import numpy as np
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    report, paths = checked_parts(inputs, directory)
    output.mkdir(parents=True, exist_ok=False)
    meshes = {}
    topology, _ = load_topology()
    for name, path in paths.items():
        triangles, _ = topology.load_binary_stl(path)
        if not np.isfinite(triangles).all():
            raise ValueError('Nonfinite display coordinates')
        # Render original triangles even when a degenerate face has an invalid STL normal.
        points = vtk.vtkPoints(); points.SetData(numpy_to_vtk(triangles.reshape(-1,3),deep=True))
        ids=np.column_stack((np.full(len(triangles),3),np.arange(triangles.size//3).reshape(-1,3))).astype(np.int64)
        cells=vtk.vtkCellArray();cells.SetCells(len(triangles),numpy_to_vtkIdTypeArray(ids.ravel(),deep=True))
        poly=vtk.vtkPolyData();poly.SetPoints(points);poly.SetPolys(cells);meshes[name]=poly
    def rgb(color):
        return tuple(int(color[i:i+2], 16)/255 for i in (1, 3, 5))
    def label(renderer, text, x, y, size=20, color='#e8eef2'):
        actor = vtk.vtkTextActor(); actor.SetInput(text); actor.SetPosition(x, y)
        actor.GetTextProperty().SetFontSize(size); actor.GetTextProperty().SetColor(*rgb(color))
        renderer.AddViewProp(actor)
    generated = []
    for mode in ('assembled', 'exploded'):
        renderer = vtk.vtkRenderer(); renderer.SetBackground(*rgb('#12212c'))
        window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1500, 1050)
        window.SetMultiSamples(0); window.AddRenderer(renderer)
        for row in report['parts']:
            role = row['role']; mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(meshes[row['name']])
            actor = vtk.vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetColor(*rgb(COLORS[role]))
            actor.GetProperty().SetInterpolationToFlat()
            if role == 'keepout_not_spring':
                actor.GetProperty().SetRepresentationToWireframe(); actor.GetProperty().SetOpacity(.10)
            if role == 'veined_cover_without_mounts' and mode == 'assembled':
                actor.GetProperty().SetOpacity(.32)
            if mode == 'exploded':
                lift = {'veined_cover_without_mounts': 85, 'branched_oil_hypothesis': 50,
                        'retainer_without_keeper': 30, 'keepout_not_spring': 20,
                        'spring_seat_hypothesis': 10, 'extended_valve_hypothesis': 0}.get(role, 0)
                actor.SetPosition(0, 0, lift)
            renderer.AddActor(actor)
        camera = renderer.GetActiveCamera(); camera.SetPosition(250, -330, 260)
        camera.SetFocalPoint(0, 10, 75 if mode == 'assembled' else 110); camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn(); renderer.ResetCamera(); camera.Zoom(.86)
        label(renderer, 'M64 / 4 soupapes - assemblage PicoGK de recherche', 30, 1000, 28)
        label(renderer, 'Positions du modele' if mode == 'assembled' else 'Vue eclatee : translations d\'affichage uniquement', 30, 965, 20)
        label(renderer, f'Pas PicoGK : {report["voxel_world_units"]} unite du scan - triangles bruts, defauts conserves', 30, 935, 16)
        label(renderer, 'Gris : corps conserve  |  Bleu : capots nervures  |  Rouge : distributeur d\'huile', 30, 90, 19)
        label(renderer, 'Orange : volumes reserves aux ressorts, PAS des ressorts fabriques', 30, 60, 19, '#ebaa43')
        label(renderer, 'INCOMPLET : fixations, commande, etancheite et essais non qualifies - NON AUTORISE A FABRIQUER', 30, 30, 18, '#eea88f')
        window.Render()
        capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
        target = output / (mode + '.png')
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(target)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
        if not target.is_file() or target.stat().st_size < 10000:
            raise ValueError('Render output missing')
        generated.append(target); window.Finalize()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    fig, ax = plt.subplots(figsize=(11, 8))
    for row in report['parts']:
        plane = vtk.vtkPlane(); plane.SetOrigin(22.5, 0, 0); plane.SetNormal(1, 0, 0)
        cut = vtk.vtkCutter(); cut.SetCutFunction(plane); cut.SetInputData(meshes[row['name']]); cut.Update()
        result = cut.GetOutput()
        curves = [[result.GetCell(i).GetPoints().GetPoint(j)[1:] for j in range(result.GetCell(i).GetNumberOfPoints())]
                  for i in range(result.GetNumberOfCells())]
        role = row['role']
        ax.add_collection(LineCollection(curves, colors=COLORS[role], linewidths=1,
                                        linestyles='dashed' if role == 'keepout_not_spring' else 'solid'))
    ax.set(xlim=(-100, 120), ylim=(-10, 145), xlabel='Y, unité du scan non étalonnée', ylabel='Z',
           title='Coupe réelle des STL à X = 22,5 — aucune translation')
    ax.set_aspect('equal'); ax.grid(alpha=.2)
    fig.text(.5, .035, 'Gris : corps conservé. Orange pointillé : place des ressorts. Fixations et commande manquantes.', ha='center')
    fig.text(.5, .01, 'Assemblage de recherche incomplet — ni validation thermique, ni autorisation d’impression.', ha='center')
    fig.tight_layout(rect=(0,.07,1,1)); target=output/'section.png'; fig.savefig(target,dpi=160); plt.close(fig)
    generated.append(target)
    checked_parts(inputs, directory)
    write_json(output/'render-receipt.json', dict(assembly_sha256=sha(directory/'assembly.json'),
               renderer_sha256=sha(__file__), geometry_sha256={n:sha(p) for n,p in paths.items()},
               images_sha256={p.name:sha(p) for p in generated}, actual_STL_used=True,
               smoothing_or_decimation=False, STL_normals_not_used_for_display=True,
               degenerate_triangles_not_removed=True, manufacturing_authorized=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('inputs', 'directory', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args(); run(args.inputs, args.directory, args.output)
