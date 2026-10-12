"""Exact-triangle whole-head views and section; private scan derivatives only."""
import argparse
import json
from pathlib import Path

import numpy as np
from audit import HERE, in_zones, mesh, validate_report


def run(inputs, directory, output):
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    if output.exists():
        raise FileExistsError(output)
    contract = json.loads((HERE/'contract.json').read_text())
    report = json.loads((directory/'integration.json').read_text())
    rows = {r['filename']: r for r in validate_report(report, contract)}
    output.mkdir(parents=True, mode=0o700)
    pins, models = {}, {}
    files = [('head', directory/'head-bionic.stl', rows['head-bionic.stl']['sha256'])]
    files += [(r['name'], inputs/r['filename'], r['sha256']) for r in report['reference_parts'] if r['name'] != 'head']
    for name, path, pin in files:
        if path.is_symlink() or mesh.sha256(path) != pin:
            raise ValueError('Render geometry hash mismatch')
        triangles = mesh.load_binary_stl(path).astype(np.float32)
        points = vtk.vtkPoints(); points.SetData(numpy_to_vtk(triangles.reshape(-1, 3), deep=True))
        cells = vtk.vtkCellArray()
        cells.SetData(numpy_to_vtkIdTypeArray(np.arange(len(triangles)+1, dtype=np.int64)*3, deep=True),
                      numpy_to_vtkIdTypeArray(np.arange(triangles.size//3, dtype=np.int64), deep=True))
        poly = vtk.vtkPolyData(); poly.SetPoints(points); poly.SetPolys(cells)
        if name == 'head':
            colors = np.tile(np.array([153, 165, 174], dtype=np.uint8), (len(triangles), 1))
            colors[in_zones(triangles.mean(axis=1), contract['modified_zones'], .6)] = [211, 126, 57]
            color_data = numpy_to_vtk(colors, deep=True); color_data.SetName('change_zone'); poly.GetCellData().SetScalars(color_data)
        models[name] = poly; pins[name] = pin
        del triangles

    def label(renderer, text, x, y, size):
        actor = vtk.vtkTextActor(); actor.SetInput(text); actor.SetPosition(x, y)
        actor.GetTextProperty().SetFontSize(size); actor.GetTextProperty().SetColor(.85, .89, .91); renderer.AddActor2D(actor)
    for title, camera in (('assembled', (250, -370, 230)), ('opposite', (-250, 370, 220))):
        renderer = vtk.vtkRenderer(); renderer.SetBackground(.055, .085, .11)
        for name, poly in models.items():
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(poly)
            if name == 'head':
                mapper.SetScalarModeToUseCellData(); mapper.SetColorModeToDirectScalars()
            else:
                mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor(); actor.SetMapper(mapper)
            color = (.40, .73, .78) if name.endswith('valve') else (.76, .57, .25) if name.endswith('seat') else (.61, .54, .76)
            if name != 'head': actor.GetProperty().SetColor(*color)
            actor.GetProperty().SetInterpolationToFlat(); renderer.AddActor(actor)
        window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1600, 1100); window.AddRenderer(renderer)
        renderer.ResetCamera(); renderer.GetActiveCamera().SetPosition(*camera); renderer.GetActiveCamera().SetFocalPoint(0, 12, 40)
        renderer.GetActiveCamera().SetViewUp(0, 0, 1); renderer.ResetCamera(); renderer.GetActiveCamera().Zoom(.84)
        label(renderer, 'M64 / 4 soupapes - ailettes bioniques integrees au corps candidat', 30, 1040, 27)
        subtitle = ('Profil PicoGK + ShapeKernel integre en CAO native - STEP et triangles reels'
                    if report.get('representation') == 'native_cad_with_analytic_picogk_profile_counterpart'
                    else f'PicoGK + ShapeKernel : triangles reels, pas {report["voxel_scan_units"]} unite du scan')
        label(renderer, subtitle, 30, 1000, 19)
        label(renderer, 'Orange : zones de refroidissement remodelees | Gris : corps conserve | Soupapes / sieges / guides : references', 30, 85, 18)
        label(renderer, '6 nervures ramifiees - modele de recherche : echelle, refroidissement, resistance et fabrication non qualifies', 30, 50, 18)
        window.Render()
        capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(output/(title+'.png'))); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
        window.Finalize()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    section = vtk.vtkPlane(); section.SetOrigin(0, 0, 0); section.SetNormal(0, 1, 0)
    fig, ax = plt.subplots(figsize=(12, 8))
    for name, path in (('baseline', directory/'baseline.stl'), ('bionic', directory/'head-bionic.stl')):
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(path)); reader.MergingOff(); reader.Update()
        cut = vtk.vtkCutter(); cut.SetCutFunction(section); cut.SetInputConnection(reader.GetOutputPort()); cut.Update()
        poly = cut.GetOutput()
        curves = [[(poly.GetCell(i).GetPoints().GetPoint(j)[0], poly.GetCell(i).GetPoints().GetPoint(j)[2])
                   for j in range(poly.GetCell(i).GetNumberOfPoints())] for i in range(poly.GetNumberOfCells())]
        ax.add_collection(LineCollection(curves, colors='#a8b4bc' if name == 'baseline' else '#b85d27', linewidths=1,
                                        linestyles='dashed' if name == 'baseline' else 'solid', label=name))
    ax.set(xlim=(-65, 65), ylim=(-3, 85), xlabel='X, unité du scan non étalonnée', ylabel='Z',
           title='Coupe réelle Y = 0 : culasse de référence et ailettes bioniques intégrées')
    ax.set_aspect('equal'); ax.grid(alpha=.2); ax.legend()
    fig.tight_layout(); fig.savefig(output/'section.png', dpi=150); plt.close(fig)
    result = dict(renderer_sha256=mesh.sha256(Path(__file__)), geometry_sha256=pins,
                  images_sha256={name: mesh.sha256(output/(name+'.png')) for name in ('assembled', 'opposite', 'section')},
                  vtk_version=vtk.vtkVersion.GetVTKVersion(), actual_triangles=True, decimation=False,
                  source_master_modified=False, manufacturing_authorized=False)
    with (output/'render-receipt.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('inputs', 'directory', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args(); run(args.inputs, args.directory, args.output)
