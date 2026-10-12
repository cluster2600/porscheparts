#!/usr/bin/env python3
"""Inspectable opaque native triangles; physical materials are not assigned."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
from render import capture,panel as basic_panel,read_surface,actor_for
import vtk


def material(actor,name):
    prop=vtk.vtkProperty();prop.SetInterpolationToPhong();prop.SetAmbient(.25);prop.SetDiffuse(.6);prop.SetSpecular(.35);prop.SetSpecularPower(25)
    color=(.57,.60,.63)
    if name in {'cylinder','crankcase_negative','crankcase_positive'}:color=(.30,.33,.36)
    if name=='individual_head':color=(.65,.68,.70)
    if name.startswith(('exhaust','turbo_')):color=(.40,.34,.29)
    if name in {'ecu','oil_hose'} or name.startswith('outer_valve_spring'):color=(.11,.13,.15)
    if 'gas_domain' in name:color=(.23,.61,.70)
    if 'bracket' in name or name=='drive_bionic_frame':color=(.49,.57,.62)
    prop.SetColor(*color);prop.SetOpacity(1);prop.SetRepresentationToSurface()
    actor.GetMapper().ScalarVisibilityOff();actor.SetProperty(prop)


def panel(window,title,viewport,actors,direction):
    renderer=basic_panel(window,title,viewport,actors,direction)
    # Reset after attachment so the camera fits the actual viewport aspect.
    renderer.ResetCamera();renderer.GetActiveCamera().SetParallelScale(renderer.GetActiveCamera().GetParallelScale()*1.06)
    renderer.ResetCameraClippingRange();return renderer


def engine(directory,path):
    rows=json.loads((directory/'assembly.json').read_text())['instances'];mapped={r['instance_id']:r for r in rows}
    window=vtk.vtkRenderWindow();window.SetSize(3200,1700);window.SetOffScreenRendering(1)
    importer=vtk.vtkGLTFImporter();importer.SetFileName(str(directory/'engine-4v-biturbo-concept.glb'));importer.SetRenderWindow(window)
    if not importer.Update():raise ValueError('GLB import failed')
    actors=list(importer.GetImportedActors());tree=ET.fromstring(importer.GetSceneHierarchy().SerializeToXML(vtk.vtkIndent()))
    all_parts=[];opened=[];seen=set()
    hide={'valve_cover','drive_housing','drive_cover','ecu','alternator','oil_tank','oil_filter','oil_thermostat','oil_cooler_core','oil_cooler_tank','intercooler_core','intercooler_tank'}
    for node in tree.iter():
        if 'flat_actor_id' not in node.attrib:continue
        row=mapped[node.attrib['parent_node_name']];name=row['family'];actor=actors[int(node.attrib['flat_actor_id'])]
        if name!=node.attrib['label']:raise ValueError('Wrong surface family')
        poly=actor.GetMapper().GetInput()
        if not poly.GetNumberOfPolys() or poly.GetNumberOfVerts() or poly.GetNumberOfLines():raise ValueError('Expected triangles')
        for i in range(4):
            for j in range(4):
                wanted=row['matrix_mm'][i][j]*(.001 if j==3 and i<3 else 1)
                if abs(actor.GetMatrix().GetElement(i,j)-wanted)>1e-6:raise ValueError('Pose transport mismatch')
        material(actor,name);all_parts.append(actor);seen.add(row['instance_id'])
        if name not in hide:opened.append(actor)
    if seen!=set(mapped):raise ValueError('Missing surfaces')
    window.RemoveRenderer(importer.GetRenderer())
    panel(window,f'Flat-12 4V biturbo — {len(rows)} occurrences, surfaces opaques',(0,0,.54,1),all_parts,(1,-1.8,1.0))
    panel(window,'Lecture mécanique — capots et échangeurs masqués',(.54,0,1,1),opened,(1,-1.8,.7))
    capture(window,path)


def details(directory,path):
    native=directory/'native-0.5'
    def actor(name,rotation=False):
        a=actor_for(read_surface(native/(name+'.stl')));material(a,name)
        if rotation:a.RotateZ(180)
        return a
    window=vtk.vtkRenderWindow();window.SetSize(2800,1150);window.SetOffScreenRendering(1)
    panel(window,'Échangeur : passages et réservoirs ramifiés',(0,0,.36,1),[actor('intercooler_core'),actor('intercooler_tank'),actor('intercooler_tank',True)],(1,-1,.8))
    panel(window,'Volume gaz : 18 passages réunis aux réservoirs',(.36,0,.66,1),[actor('intercooler_gas_domain')],(1,-1,.8))
    panel(window,'Support des axes : branches, alésages et ancrages',(.66,0,1,1),[actor('drive_bionic_frame')],(1,-.1,.1))
    capture(window,path)


if __name__=='__main__':
    p=Path(sys.argv[1]);engine(p,p/'engine-surfaces.png');details(p,p/'mechanical-details.png')
