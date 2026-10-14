#!/usr/bin/env python3
"""935-only full-surface review; preserve all native PicoGK triangles."""
import argparse
import json
from pathlib import Path
import sys

from run_reconstruction import ROOT, fresh, save, sha
from export_inspection_assembly import COLORS


def render(native, exports, output):
    import vtk
    sys.path.insert(0,str(ROOT/'twins/reference-917-engine/source'))
    from render_scan_contour_patch_reconstruction_f43 import text_actor
    native, exports = Path(native), Path(exports)
    receipt = json.loads((native/'receipt.json').read_text())
    report = json.loads((exports/'report.json').read_text())
    if (receipt['target'] != '935' or receipt['engine_cylinders'] != 6
            or report['native_receipt_sha256'] != sha(native/'receipt.json') or receipt['manufacturing_authorized']):
        raise ValueError('Audited six-cylinder 935 assembly required')
    out = fresh(output); actors = {}; counts = {}
    for row in receipt['components']:
        p = native/row['file']
        if sha(p) != row['sha256']: raise ValueError('Native geometry changed')
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(p)); reader.MergingOff(); reader.Update()
        data = reader.GetOutput()
        if data.GetNumberOfPolys() != row['triangles']: raise ValueError('Renderer lost triangles')
        mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(data); mapper.ScalarVisibilityOff()
        actor = vtk.vtkActor(); actor.SetMapper(mapper); prop = actor.GetProperty()
        prop.SetColor(*COLORS[row['id']]); prop.SetOpacity(1); prop.SetAmbient(.25); prop.SetDiffuse(.75)
        actors[row['id']] = actor; counts[row['id']] = data.GetNumberOfPolys()
    window = vtk.vtkRenderWindow(); window.SetSize(2800,1800); window.SetOffScreenRendering(1)
    views = [('935 — 6 cylindres, enveloppes moteur a calibrer',set(actors),(1,-1.7,1.2)),
             ('935 — deux banques de trois cylindres, carenage masque',set(actors)-{'provisional_shroud'},(0,-.01,2)),
             ('Rotor depuis les sections du scan — PicoGK',{'rotor_candidate','drive_observed'},(-1,-1.5,1.2)),
             ('Admission et guide vers les deux banques — hypotheses',{'rotor_candidate','drive_observed','provisional_shroud'},(1,-1.5,1.3))]
    for i,(title,names,direction) in enumerate(views):
        renderer = vtk.vtkRenderer(); x=(i%2)*.5; y=.5 if i<2 else 0
        renderer.SetViewport(x,y,x+.5,y+.5); renderer.SetBackground(.035,.065,.085)
        for name in names: renderer.AddActor(actors[name])
        renderer.AddViewProp(text_actor(title,25,850,25))
        renderer.AddViewProp(text_actor('Echelles et interfaces non confirmees — aucune validation physique',25,18,18))
        camera = renderer.GetActiveCamera(); camera.SetPosition(*direction); camera.SetFocalPoint(0,0,0)
        camera.SetViewUp(*((0,1,0) if i==1 else (0,0,1))); camera.ParallelProjectionOn()
        renderer.ResetCamera(); renderer.ResetCameraClippingRange(); window.AddRenderer(renderer)
    path = out/'935-assembly-review.png'
    try:
        window.Render(); capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
        writer = vtk.vtkPNGWriter(); writer.SetFileName(str(path)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
    finally: window.Finalize()
    if not path.is_file() or path.stat().st_size == 0: raise ValueError('Missing rendered image')
    for row in receipt['components']:
        if sha(native/row['file']) != row['sha256']: raise ValueError('Rendering changed native geometry')
    save(out/'report.json',{'target':'935','engine_cylinders':6,'geometry_triangles':counts,
        'native_receipt_sha256':sha(native/'receipt.json'),'image_sha256':sha(path),
        'decimation':False,'opacity':1,'vtk_version':vtk.vtkVersion.GetVTKVersion(),
        'exact_historical_engine_reconstructed':False,'physical_validation':False})
    print(str(path))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native');p.add_argument('exports');p.add_argument('new_output')
    a=p.parse_args();render(a.native,a.exports,a.new_output)
