#!/usr/bin/env python3
"""Opaque views of the actual native gear triangles, without point sampling."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
from render import capture, panel, read_surface, actor_for
import vtk


def run(directory,output):
    assembly=json.loads((directory/'assembly.json').read_text())
    report=json.loads((directory/'report.json').read_text())
    def actor(path,matrix=None):
        surface=read_surface(path);a=actor_for(surface)
        a.GetProperty().SetColor(.45,.69,.75);a.GetProperty().SetOpacity(1)
        a.GetProperty().SetRepresentationToSurface()
        if matrix is not None:
            m=vtk.vtkMatrix4x4()
            for i in range(4):
                for j in range(4):m.SetElement(i,j,matrix[i][j])
            a.SetUserMatrix(m)
        return a
    gears=[r for r in assembly['instances'] if r['family'].startswith(('drive_27_','drive_48_','drive_54_')) and r['matrix_mm'][0][3]==400]
    window=vtk.vtkRenderWindow();window.SetSize(2400,1200);window.SetOffScreenRendering(1)
    panel(window,'Distribution admission — rapport +1/2, géométrie froide', (0,0,.65,1),
          [actor(directory/'pieces'/(r['family']+'.stl'),r['matrix_mm']) for r in gears],(1,0,0))
    items=[]
    for index,(teeth,row) in enumerate(report['gears'].items()):
        m=[[1,0,0,0],[0,1,0,0],[0,0,1,index*95],[0,0,0,1]]
        items.append(actor(directory/'pieces'/(row['selected']+'.stl'),m))
    panel(window,'Moyeux ramifiés — hypothèses sans validation mécanique',(.65,0,1,1),items,(1,-.2,.3))
    capture(window,output)


if __name__=='__main__':run(Path(sys.argv[1]),Path(sys.argv[2]))
