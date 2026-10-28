#!/usr/bin/env python3
"""Check exact native triangle transport, export and render the refreshed 935 study."""
import argparse
import json
from pathlib import Path
import struct

import numpy as np
from export_inspection_assembly import COLORS, export, triangles
from run_reconstruction import fresh, save, sha
from stl_moments import DTYPE


def review(native, expected_receipt, output):
    native,output=Path(native),Path(output)
    if sha(native/'receipt.json')!=expected_receipt:
        raise ValueError('Pinned native receipt required')
    receipt=json.loads((native/'receipt.json').read_text())
    if receipt['stage']!='assembly_refresh':raise ValueError('Refreshed native assembly required')
    combined=native/'assembly-inspection.stl';expected=sum(row['triangles'] for row in receipt['components'])
    with combined.open('rb') as stream:header=stream.read(84)
    if (not 1<=expected<=16_000_000 or len(header)!=84 or struct.unpack('<I',header[80:])[0]!=expected
            or combined.stat().st_size!=84+50*expected):
        raise ValueError('Bounded complete binary assembly STL required')
    assembled=np.memmap(combined,mode='r',dtype=DTYPE,offset=84,shape=(expected,))['vertices'];offset=0
    for row in receipt['components']:
        part=triangles(native/row['file'])
        for start in range(0,len(part),100000):
            block=part[start:start+100000]
            if not np.array_equal(block,assembled[offset+start:offset+start+len(block)]):
                raise ValueError('Native Append changed triangle coordinates or order')
        offset+=len(part)
    if offset!=len(assembled) or sha(native/'assembly-inspection.stl')!=receipt['assembly_sha256']:
        raise ValueError('Native combined mesh count or hash mismatch')
    export(native,output)
    report=json.loads((output/'report.json').read_text())
    report.update(native_concatenation_coordinates_and_order_exact=True,native_combined_triangles=offset,
                  current_rotor_geometry_sha256=next(r['sha256'] for r in receipt['components'] if r['id']=='rotor_candidate'),
                  component_source_receipts=receipt['component_source_receipts'],
                  source_coordinate_unit='uncalibrated_scan_unit',
                  export_scale_to_metres_is_assumption=True,
                  note='Legacy *_mm_hypothesis field names retain the assumed scale. No calibration evidence was added.')
    save(output/'report.json',report)
    return report


def render(native, exports, output):
    import vtk
    native,exports=Path(native),Path(exports)
    report=json.loads((exports/'report.json').read_text());receipt=json.loads((native/'receipt.json').read_text())
    if (report['native_receipt_sha256']!=sha(native/'receipt.json') or
            report['native_concatenation_coordinates_and_order_exact'] is not True):
        raise ValueError('Independent triangle transport audit required')
    out=fresh(output);actors={};counts={}
    for row in receipt['components']:
        p=native/row['file']
        if sha(p)!=row['sha256']:raise ValueError('Native component changed')
        reader=vtk.vtkSTLReader();reader.SetFileName(str(p));reader.MergingOff();reader.Update()
        data=reader.GetOutput()
        if data.GetNumberOfPolys()!=row['triangles']:raise ValueError('Render lost triangles')
        mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(data);mapper.ScalarVisibilityOff()
        actor=vtk.vtkActor();actor.SetMapper(mapper)
        prop=actor.GetProperty();prop.SetColor(*COLORS[row['id']]);prop.SetOpacity(1);prop.SetAmbient(.25);prop.SetDiffuse(.75)
        actors[row['id']]=actor;counts[row['id']]=data.GetNumberOfPolys()
    window=vtk.vtkRenderWindow();window.SetSize(2400,1600);window.SetOffScreenRendering(1)
    views=[('935 horizontal cooling assembly - packaging study',set(actors),(1,-1.7,1.2)),
           ('Two banks of three cylinders - shroud hidden',set(actors)-{'provisional_shroud'},(0,-.01,2)),
           ('Corrected scan-based rotor and observed drive',{'rotor_candidate','drive_observed'},(-1,-1.5,1.2)),
           ('Rotor, admission and distribution envelope',set(actors)-{'engine_context'},(1,-1.5,1.3))]
    for i,(title,names,direction) in enumerate(views):
        renderer=vtk.vtkRenderer();x=(i%2)*.5;y=.5 if i<2 else 0
        renderer.SetViewport(x,y,x+.5,y+.5);renderer.SetBackground(.035,.065,.085)
        for name in names:renderer.AddActor(actors[name])
        for label,pos,size in [(title,(20,755),21),('Uncalibrated scale; unresolved interfaces; inspection only',(20,18),16)]:
            text=vtk.vtkTextActor();text.SetInput(label);text.SetPosition(*pos)
            text.GetTextProperty().SetFontSize(size);text.GetTextProperty().SetColor(.95,.96,.98);renderer.AddActor2D(text)
        camera=renderer.GetActiveCamera();camera.SetPosition(*direction);camera.SetFocalPoint(0,0,0)
        camera.SetViewUp(*((0,1,0) if i==1 else (0,0,1)));camera.ParallelProjectionOn()
        renderer.ResetCamera();renderer.ResetCameraClippingRange();window.AddRenderer(renderer)
    path=out/'935-assembly-review.png'
    try:
        window.Render();capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.ReadFrontBufferOff();capture.Update()
        writer=vtk.vtkPNGWriter();writer.SetFileName(str(path));writer.SetInputConnection(capture.GetOutputPort());writer.Write()
    finally:window.Finalize()
    if not path.is_file() or not path.stat().st_size:raise ValueError('Missing rendered image')
    if any(sha(native/r['file'])!=r['sha256'] for r in receipt['components']):raise ValueError('Rendering changed geometry')
    save(out/'report.json',dict(target='935',engine_cylinders=6,geometry_triangles=counts,
        native_receipt_sha256=sha(native/'receipt.json'),export_report_sha256=sha(exports/'report.json'),
        image_sha256=sha(path),vtk_version=vtk.vtkVersion.GetVTKVersion(),decimation=False,opacity=1,
        exact_historical_engine_reconstructed=False,physical_validation=False,manufacturing_authorized=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='operation',required=True)
    p=sub.add_parser('review');p.add_argument('native',type=Path);p.add_argument('receipt_sha256');p.add_argument('new_output',type=Path)
    p=sub.add_parser('render');p.add_argument('native',type=Path);p.add_argument('exports',type=Path);p.add_argument('new_output',type=Path)
    args=parser.parse_args()
    if args.operation=='review':review(args.native,args.receipt_sha256,args.new_output)
    else:render(args.native,args.exports,args.new_output)
