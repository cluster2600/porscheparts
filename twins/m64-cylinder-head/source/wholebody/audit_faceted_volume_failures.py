#!/usr/bin/env python3
"""Locate and render actual rejected tetrahedra, not physical cracks or stress."""
import argparse
import json
from pathlib import Path
import signal

import numpy as np
from trial_meshers_2026 import native, read_gmsh
from trial_audited_discrete_volume import ARRAY_SHA


def boundary_contacts(cells, faces):
    if (cells.ndim != 2 or cells.shape[1] != 4 or faces.ndim != 2 or faces.shape[1] != 3
            or cells.dtype.kind not in 'iu' or faces.dtype.kind not in 'iu'
            or not len(faces) or len(cells)>100000 or min(cells.min(initial=0),faces.min())<0):
        raise ValueError('bounded_indexed_cells_and_boundary_required')
    vertices = np.isin(cells,np.unique(faces)).sum(axis=1)
    tf = np.sort(np.concatenate([cells[:,p] for p in ((1,2,3),(0,3,2),(0,1,3),(0,2,1))]),axis=1)
    _, ids = np.unique(np.vstack([tf,np.sort(faces,axis=1)]),axis=0,return_inverse=True)
    on_boundary = np.isin(ids[:len(tf)],ids[len(tf):]).reshape(4,len(cells)).sum(axis=0)
    return dict(boundary_vertex_count_histogram=np.bincount(vertices,minlength=5).tolist(),
        boundary_face_count_histogram=np.bincount(on_boundary,minlength=5).tolist())


def run(args):
    import gmsh
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    paths = (args.mesh,args.receipt,Path(__file__),Path(native.__file__),Path(__file__).with_name('trial_meshers_2026.py'))
    pins = {p:native.sha256(p) for p in paths}
    record = json.loads(args.receipt.read_text())
    if (args.output.exists() or args.output.is_symlink() or any(p.is_symlink() for p in paths)
            or gmsh.__version__!='4.15.2' or record.get('schema')!='m64-audited-discrete-volume/v1'
            or record.get('status')!='completed_faceted_diagnostic_only' or record.get('inputs_unchanged') is not True
            or record.get('volume_audit',{}).get('sha256')!=pins[args.mesh]
            or ARRAY_SHA not in record.get('source_hashes',{}).values()):
        raise ValueError('fresh_output_and_bound_completed_faceted_diagnostic_required')
    gmsh.initialize(['rejected-volume','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try:
        points,cells,faces,tags=read_gmsh(args.mesh)
        if len(cells)>3000000: raise ValueError('bounded_volume_required')
        q=np.asarray(gmsh.model.mesh.getElementQualities(tags,'minSICN'))
        if not np.isfinite(q).all(): raise ValueError('finite_qualities_required')
        bad=cells[q<.1]
        if len(bad)!=record['volume_audit']['quality']['quality_distribution']['minSICN_below_0p1']:
            raise ValueError('recomputed_rejection_count_must_match_receipt')
    finally: gmsh.finalize()
    contacts=boundary_contacts(bad,faces)
    args.output.mkdir(mode=0o700)
    cloud=vtk.vtkPoints(); cloud.SetData(numpy_to_vtk(points,deep=True))
    def connectivity(rows):
        data=vtk.vtkCellArray()
        data.ImportLegacyFormat(numpy_to_vtkIdTypeArray(np.c_[np.full(len(rows),rows.shape[1]),rows].ravel().astype(np.int64),deep=True))
        return data
    skin=vtk.vtkPolyData(); skin.SetPoints(cloud); skin.SetPolys(connectivity(faces))
    rejected=vtk.vtkUnstructuredGrid(); rejected.SetPoints(cloud); rejected.SetCells(vtk.VTK_TETRA,connectivity(bad))
    renderer=vtk.vtkRenderer(); renderer.SetBackground(.07,.10,.14)
    window=vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(1400,1100); window.AddRenderer(renderer)
    for data,colour,opacity in ((skin,(.7,.78,.83),.20),(rejected,(1.,.23,.12),1.)):
        mapper=vtk.vtkDataSetMapper(); mapper.SetInputData(data)
        actor=vtk.vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetColor(*colour)
        actor.GetProperty().SetOpacity(opacity); actor.GetProperty().SetInterpolationToFlat(); renderer.AddActor(actor)
    centre=(points.min(0)+points.max(0))/2; span=max(np.ptp(points,axis=0))
    camera=renderer.GetActiveCamera(); camera.SetPosition(*(centre+span*np.array([1.5,-2.,-1.3])))
    camera.SetFocalPoint(*centre); camera.SetViewUp(0,0,-1); camera.ParallelProjectionOn(); camera.SetParallelScale(.62*span)
    renderer.ResetCameraClippingRange()
    label=vtk.vtkTextActor(); label.SetInput(f'M64 research mesh | {len(bad):,} rejected tetrahedra\nRed: minSICN < 0.1. Not cracks, temperature or stress.\nUnqualified native creases / interfaces. NOT FOR MANUFACTURE.')
    label.SetPosition(25,25); label.GetTextProperty().SetFontSize(20); label.GetTextProperty().SetColor(1,.85,.75)
    renderer.AddViewProp(label); window.Render()
    capture=vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
    image=args.output/'rejected-tetrahedra.png'; writer=vtk.vtkPNGWriter(); writer.SetFileName(str(image))
    writer.SetInputConnection(capture.GetOutputPort()); writer.Write(); window.Finalize(); image.chmod(0o600)
    unchanged=all(native.sha256(p)==h for p,h in pins.items())
    native.save(args.output/'report.json',dict(schema='m64-faceted-rejection-location/v1',
        source_hashes={str(p):h for p,h in pins.items()},tetrahedra=len(cells),rejected=len(bad),
        minimum_minSICN=float(q.min()),contacts=contacts,
        rejected_element_tags_private=tags[q<.1].tolist(),image_sha256=native.sha256(image),
        vtk_version=vtk.vtkVersion.GetVTKVersion(),gmsh_version=gmsh.__version__,
        inputs_unchanged=unchanged,geometry_modified=False,generative_image=False,manufacturing_authorized=False))
    if not unchanged: raise ValueError('input_changed')
    print(json.dumps(dict(rejected=len(bad),contacts=contacts,image=str(image))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('mesh','receipt','output'): parser.add_argument('--'+key,type=Path,required=True)
    signal.alarm(180); run(parser.parse_args())
