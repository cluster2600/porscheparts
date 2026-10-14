#!/usr/bin/env python3
"""Opaque triangle-surface previews; no sampled points or geometry reduction."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[2]/'twins/reference-917-engine/source'))
from render_scan_contour_patch_reconstruction_f43 import actor_for, read_surface, text_actor
import vtk


def capture(window,path):
    window.Render()
    image=vtk.vtkWindowToImageFilter();image.SetInput(window);image.ReadFrontBufferOff();image.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(path));writer.SetInputConnection(image.GetOutputPort());writer.Write()
    if not path.is_file():raise ValueError('PNG capture failed')
    window.Finalize()


def panel(window,title,viewport,actors,direction=(1,-1,.8)):
    renderer=vtk.vtkRenderer();renderer.SetViewport(*viewport);renderer.SetBackground(.035,.065,.085)
    for actor in actors:renderer.AddActor(actor)
    renderer.AddViewProp(text_actor(title,22,24,22))
    camera=renderer.GetActiveCamera();camera.SetPosition(*direction);camera.SetFocalPoint(0,0,0);camera.SetViewUp(0,0,1)
    camera.ParallelProjectionOn();renderer.ResetCamera();renderer.ResetCameraClippingRange();window.AddRenderer(renderer)
    return renderer


def head(native,config,search,output):
    import numpy as np
    from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray
    import study
    import cams
    cycle=next(c for c in cams.cycles() if c['bank']==1 and c['pair_index']==0)
    window=vtk.vtkRenderWindow();window.SetSize(2400,1100);window.SetOffScreenRendering(1)
    def actor(name,matrix=None,color=(.35,.67,.77),clip=False):
        poly=read_surface(native/(name+'.stl'))
        if clip:
            plane=vtk.vtkPlane();plane.SetOrigin(0,0,0);plane.SetNormal(1,0,0)
            cut=vtk.vtkClipPolyData();cut.SetInputData(poly);cut.SetClipFunction(plane);cut.Update();poly=cut.GetOutput()
        a=actor_for(poly);a.GetProperty().SetColor(*color);a.GetProperty().SetOpacity(1)
        if matrix is not None:
            m=vtk.vtkMatrix4x4()
            for i in range(4):
                for j in range(4):m.SetElement(i,j,matrix[i,j])
            a.SetUserMatrix(m)
        return a
    panel(window,'Corps bionique PicoGK — hypothèse 85 mm', (0,0,1/3,1),[actor('head_bionic_2_0')],(1,-1,1))
    gas=actor('gas_domain',color=(.88,.49,.2));oil=actor('oil_domain',color=(.76,.82,.22))
    panel(window,'Conduits gaz et huile — volumes de calcul', (1/3,0,2/3,1),[gas,oil],(1,-1,1))
    parts=[actor('head_bionic_2_0',clip=True)]
    for name,m in study.local_components(config,search,cycle):
        if name in {'individual_head','valve_cover','head_stud','head_nut','location_dowel','head_gasket','cam_cap_bolt'}:continue
        parts.append(actor(name,m,(.68,.73,.76)))
    for role,sign in (('intake',1),('exhaust',-1)):
        polygon,_=cams.section(role,search['timing']['roles'][role],1,cycle['overlap_tdc_deg'])
        for side in (-1,1):
            x=side*config['pair_half_pitch_mm'];mesh=cams.extrude(polygon,x-5,x+5)
            h=study.head_transform(0,1,211.25);cam=np.eye(4)
            import math
            cam[:3,3]=[0,211.25+config['face_z_mm']+164.1*math.cos(math.radians(8)),sign*(config['row_offset_mm']+164.1*math.sin(math.radians(8)))]
            mesh.apply_transform(np.linalg.inv(h)@cam)
            pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(mesh.vertices,deep=True))
            cells=vtk.vtkCellArray();cells.SetCells(len(mesh.faces),numpy_to_vtkIdTypeArray(np.column_stack((np.full(len(mesh.faces),3),mesh.faces)).ravel(),deep=True))
            poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells)
            a=actor_for(poly);a.GetProperty().SetColor(.88,.49,.2);parts.append(a)
    panel(window,'Coupe de lecture — 4 soupapes et cames à rouleaux', (2/3,0,1,1),parts,(1,-1,.6))
    capture(window,output)


def engine(directory,output):
    rows=json.loads((directory/'assembly.json').read_text())['instances'];mapped={r['instance_id']:r for r in rows}
    window=vtk.vtkRenderWindow();window.SetSize(2800,1600);window.SetOffScreenRendering(1)
    importer=vtk.vtkGLTFImporter();importer.SetFileName(str(directory/'engine-4v-biturbo-concept.glb'));importer.SetRenderWindow(window)
    if not importer.Update():raise ValueError('GLB import failed')
    actors=list(importer.GetImportedActors());hierarchy=ET.fromstring(importer.GetSceneHierarchy().SerializeToXML(vtk.vtkIndent()))
    selected=[];all_parts=[];seen=set()
    for node in hierarchy.iter():
        if 'flat_actor_id' not in node.attrib:continue
        row=mapped[node.attrib['parent_node_name']];name=row['family']
        if name!=node.attrib['label']:raise ValueError('Surface family mismatch')
        actor=actors[int(node.attrib['flat_actor_id'])];seen.add(row['instance_id'])
        data=actor.GetMapper().GetInput()
        if not data.GetNumberOfPolys() or data.GetNumberOfVerts() or data.GetNumberOfLines():raise ValueError('Expected surfaces')
        for i in range(4):
            for j in range(4):
                expected=row['matrix_mm'][i][j]*(.001 if j==3 and i<3 else 1)
                if abs(actor.GetMatrix().GetElement(i,j)-expected)>1e-6:raise ValueError('GLB pose mismatch')
        prop=actor.GetProperty();prop.SetColor(*((.72,.4,.19) if name.startswith('turbo') else (.15,.52,.65) if name=='individual_head' else (.57,.65,.69)))
        prop.SetRepresentationToSurface();prop.SetOpacity(1);prop.SetInterpolationToPhong();prop.SetAmbient(.25)
        all_parts.append(actor)
        if name in {'individual_head','crankshaft','cylinder','piston','rod','rocker','rocker_carrier','cam_cap_bolted','cam_roller','cam_roller_pin','upper_spring_retainer'} or name.startswith(('head_component_','camshaft_','outer_valve_spring_','inner_valve_spring_')):selected.append(actor)
    if seen!=set(mapped):raise ValueError('Missing surface actors')
    window.RemoveRenderer(importer.GetRenderer())
    panel(window,f'Flat-12 / 4V / biturbo — {len(rows)} occurrences', (0,0,.5,1),all_parts,(1,-1.8,1))
    panel(window,'Mécanisme — géométrie froide sous hypothèses', (.5,0,1,1),selected,(1,-1.8,1))
    capture(window,output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);args=parser.parse_args()
    config=json.loads((args.directory/'config.json').read_text());search=json.loads((args.directory/'search.json').read_text())
    head(args.directory/'native-0.5',config,search,args.directory/'head-surfaces.png')
    engine(args.directory,args.directory/'engine-surfaces.png')
