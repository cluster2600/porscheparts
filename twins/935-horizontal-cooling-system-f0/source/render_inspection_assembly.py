#!/usr/bin/env python3
"""Render full inspection meshes with the existing native VTK runtime."""
import argparse
import json
from pathlib import Path
import sys

from run_reconstruction import ROOT, fresh, save, sha
from export_inspection_assembly import COLORS


def render(native, audited, output):
    import vtk
    sys.path.insert(0, str(ROOT/'twins/reference-917-engine/source'))
    from render_scan_contour_patch_reconstruction_f43 import text_actor
    native, audited = Path(native), Path(audited)
    receipt = json.loads((native/'receipt.json').read_text())
    report = json.loads((audited/'report.json').read_text())
    if report['native_receipt_sha256'] != sha(native/'receipt.json') or report['manufacturing_authorized'] is not False:
        raise ValueError('Matching inspection audit required')
    out = fresh(output); actors = {}; records = {}
    for row in receipt['components']:
        path = native/row['file']
        if sha(path) != row['sha256']:
            raise ValueError('Geometry changed before rendering')
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(path)); reader.MergingOff(); reader.Update()
        mesh = reader.GetOutput()
        if mesh.GetNumberOfPolys() != row['triangles']:
            raise ValueError('Renderer lost triangles in '+row['id'])
        mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(mesh); mapper.ScalarVisibilityOff()
        actor = vtk.vtkActor(); actor.SetMapper(mapper)
        prop = actor.GetProperty(); prop.SetColor(*COLORS[row['id']]); prop.SetOpacity(1)
        prop.SetAmbient(.25); prop.SetDiffuse(.75); prop.SetSpecular(.15)
        actors[row['id']] = actor; records[row['id']] = {'source_triangles':row['triangles'], 'display_triangles':mesh.GetNumberOfPolys()}
    window = vtk.vtkRenderWindow(); window.SetSize(2800, 1800); window.SetOffScreenRendering(1)
    views = [('Contexte moteur 917 — assemblage comparatif', set(COLORS), (1,-1.7,1.2)),
             ('Vue de dessus — placements supposes', set(COLORS), (0,-.01,2)),
             ('935 : entrainement, rotor, carenage provisoire', set(COLORS)-{'engine_context'}, (1,-1.5,1.3)),
             ('Rotor et support — carenage masque', {'rotor_candidate','drive_observed'}, (-1,-1.5,1.2))]
    for index, (title, names, direction) in enumerate(views):
        renderer = vtk.vtkRenderer(); x=(index%2)*.5; y=.5 if index<2 else 0
        renderer.SetViewport(x,y,x+.5,y+.5); renderer.SetBackground(.035,.065,.085)
        for name in names: renderer.AddActor(actors[name])
        renderer.AddViewProp(text_actor(title, 25, 850, 26))
        renderer.AddViewProp(text_actor('Echelle/montage non confirmes — aucune validation physique', 25, 18, 18))
        camera = renderer.GetActiveCamera(); camera.SetPosition(*direction); camera.SetFocalPoint(0,0,0)
        camera.SetViewUp(*((0,1,0) if index == 1 else (0,0,1)))
        camera.ParallelProjectionOn(); renderer.ResetCamera(); renderer.ResetCameraClippingRange()
        window.AddRenderer(renderer)
    image = out/'assembly-review.png'
    try:
        window.Render(); capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(image)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
    finally: window.Finalize()
    if not image.is_file() or image.stat().st_size == 0:
        raise ValueError('Missing rendered PNG')
    for row in receipt['components']:
        if sha(native/row['file']) != row['sha256']: raise ValueError('Renderer changed the source')
    save(out/'render-report.json', {'status':'inspection_surfaces_only', 'native_receipt_sha256':sha(native/'receipt.json'),
        'audit_sha256':sha(audited/'report.json'), 'components':records, 'source_geometry_changed':False,
        'display_decimation':False, 'opacity':1, 'vtk_version':vtk.vtkVersion.GetVTKVersion(),
        'image_sha256':sha(image), 'physical_fit_verified':False})
    print(str(image))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_output'); parser.add_argument('audited_exports'); parser.add_argument('new_private_output')
    args = parser.parse_args(); render(args.native_output, args.audited_exports, args.new_private_output)
