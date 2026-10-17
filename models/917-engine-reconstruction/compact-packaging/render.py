#!/usr/bin/env python3
"""Render actual exported triangles with house VTK helpers; colors are illustrative."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
import study
from engine_layout import module
base=module('frozen_detail_render',HERE.parent/'mechanical-detail/render.py')
import vtk


def engine(directory,path):
    rows=json.loads((directory/'assembly.json').read_text())['instances'];mapped={r['instance_id']:r for r in rows}
    window=vtk.vtkRenderWindow();window.SetSize(3200,1700);window.SetOffScreenRendering(1)
    importer=vtk.vtkGLTFImporter();importer.SetFileName(str(directory/'engine-4v-biturbo-concept.glb'));importer.SetRenderWindow(window)
    if not importer.Update():raise ValueError('GLB import failed')
    actors=list(importer.GetImportedActors());tree=ET.fromstring(importer.GetSceneHierarchy().SerializeToXML(vtk.vtkIndent()))
    complete=[];opened=[];seen=set()
    hide={'drive_housing','drive_cover','ecu','alternator','oil_tank','oil_filter','oil_thermostat','oil_cooler_core','oil_cooler_tank','intercooler_core','intercooler_tank'}
    for node in tree.iter():
        if 'flat_actor_id' not in node.attrib:continue
        row=mapped[node.attrib['parent_node_name']];name=row['family'];actor=actors[int(node.attrib['flat_actor_id'])]
        if name!=node.attrib['label']:raise ValueError('Wrong family')
        poly=actor.GetMapper().GetInput()
        if not poly.GetNumberOfPolys() or poly.GetNumberOfVerts() or poly.GetNumberOfLines():raise ValueError('Expected triangles')
        for i in range(4):
            for j in range(4):
                wanted=row['matrix_mm'][i][j]*(.001 if j==3 and i<3 else 1)
                if abs(actor.GetMatrix().GetElement(i,j)-wanted)>1e-6:raise ValueError('Pose transport mismatch')
        base.material(actor,name);complete.append(actor);seen.add(row['instance_id'])
        if name not in hide and not name.startswith(('bank_valve_cover_','bank_adapter_')):opened.append(actor)
    if seen!=set(mapped):raise ValueError('Missing surfaces')
    window.RemoveRenderer(importer.GetRenderer())
    base.panel(window,'Flat-12 4V biturbo — carters longitudinaux, conduits abaissés',(0,0,.54,1),complete,(1,-1.8,1))
    base.panel(window,'Mécanisme hérité — carters et échangeurs masqués',(.54,0,1,1),opened,(1,-1.8,.7))
    base.capture(window,path)


if __name__=='__main__':
    p=Path(sys.argv[1]);engine(p,p/'engine-surfaces.png')
