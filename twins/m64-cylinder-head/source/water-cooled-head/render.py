"""Private triangle views of coolant routing and containment diagnostics."""
import argparse
import json
from pathlib import Path

from audit import HERE, surface, validate_report


def run(inputs, directory, output):
    import vtk
    if output.exists(): raise FileExistsError(output)
    contract=json.loads((HERE/'contract.json').read_text())
    report=json.loads((directory/'generation.json').read_text())
    rows={r['filename']:r for r in validate_report(report,contract)}
    if surface.mesh.sha256(HERE/'contract.json') != report['contract_sha256']:
        raise ValueError('Different routing contract')
    manifest=json.loads((inputs/'inputs.json').read_text())
    if surface.mesh.sha256(inputs/'inputs.json') != contract['input_manifest_sha256']:
        raise ValueError('Different retained inputs')
    models=[(r['name'],inputs/r['filename'],r['sha256']) for r in manifest['parts']]
    models += [(n,directory/n,rows[n]['sha256']) for n in rows if rows[n]['triangles']]
    pins={}
    readers={}
    for name,path,pin in models:
        if path.is_symlink() or surface.mesh.sha256(path) != pin: raise ValueError('Geometry hash mismatch')
        reader=vtk.vtkSTLReader();reader.SetFileName(str(path));reader.MergingOff();reader.Update()
        readers[name]=reader;pins[name]=pin
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(1800,1000)
    for index,title in enumerate(('Routage eau propose','Zones hors du noyau avec marge de paroi')):
        renderer=vtk.vtkRenderer();renderer.SetBackground(.055,.085,.11)
        renderer.SetViewport(index*.5,0,(index+1)*.5,1);window.AddRenderer(renderer)
        for name,reader in readers.items():
            if name=='routing-plus-wall-margin.stl' or (name=='outside-eroded-head.stl' and index==0):continue
            mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(reader.GetOutputPort());mapper.ScalarVisibilityOff()
            actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetInterpolationToFlat()
            color=(.2,.66,1) if name=='coolant-routing.stl' else (1,.24,.12) if name=='outside-eroded-head.stl' else (.67,.72,.75) if name=='head' else (.85,.64,.3) if name.endswith('seat') else (.64,.73,.71)
            actor.GetProperty().SetColor(*color)
            actor.GetProperty().SetOpacity(.12 if name=='head' else 1)
            renderer.AddActor(actor)
        renderer.GetActiveCamera().SetPosition(240,-350,250);renderer.GetActiveCamera().SetFocalPoint(0,10,40)
        renderer.GetActiveCamera().SetViewUp(0,0,1);renderer.ResetCamera();renderer.GetActiveCamera().Zoom(.88)
        for text,y,size in ((title,945,23),('Culasse source intacte / 4 soupapes / triangles reels',910,16),
            ('Bleu : eau proposee / Rouge : defaut de confinement',65,16),
            ('Recherche : chemise etanche et interfaces non qualifiees',35,16)):
            label=vtk.vtkTextActor();label.SetInput(text);label.SetPosition(20,y);label.GetTextProperty().SetFontSize(size)
            label.GetTextProperty().SetColor(.9,.93,.95);renderer.AddViewProp(label)
    window.Render();capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.ReadFrontBufferOff();capture.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(output));writer.SetInputConnection(capture.GetOutputPort());writer.Write();window.Finalize()
    result=dict(renderer_sha256=surface.mesh.sha256(Path(__file__)),image_sha256=surface.mesh.sha256(output),
                geometry_sha256=pins,vtk_version=vtk.vtkVersion.GetVTKVersion(),decimation=False,
                source_master_modified=False,pressure_boundary_qualified=False,manufacturing_authorized=False)
    with output.with_suffix('.receipt.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('inputs','directory','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();run(args.inputs,args.directory,args.output)
