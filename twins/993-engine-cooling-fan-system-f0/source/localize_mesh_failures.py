#!/usr/bin/env python3
"""Locate actual native bad cells/faces in an original linear-tet mesh (meters).

Cell ordering is the sequential type-4 record order used by Foundation 13
gmshToFoam. Surface VTKs are exported by checkMesh, never synthesized fields.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read_set(path):
    text=path.read_text();match=re.search(r'\n\s*(\d+)\s*\n\(\s*([^)]*)\)',text)
    if not match:raise ValueError('Native ASCII mesh set required')
    values=list(map(int,match[2].split()))
    if len(values)!=int(match[1]) or len(set(values))!=len(values):raise ValueError('Mesh set coverage invalid')
    return set(values)


def vtk_faces(path):
    tokens=path.read_text().split()
    if tokens[:5]!=['#','vtk','DataFile','Version','2.0'] or 'ASCII' not in tokens[:12]:raise ValueError('Native ASCII legacy VTK required')
    index=tokens.index('POINTS');count=int(tokens[index+1]);start=index+3
    points=np.array(list(map(float,tokens[start:start+3*count]))).reshape(-1,3)
    index=tokens.index('POLYGONS');number=int(tokens[index+1]);index+=3;centres=[]
    for _ in range(number):
        n=int(tokens[index]);ids=list(map(int,tokens[index+1:index+1+n]));index+=1+n
        centres.append(points[ids].mean(axis=0))
    return points,np.array(centres)


def bands(points):
    radius=np.linalg.norm(points[:,:2],axis=1)
    return {name:int(np.count_nonzero((radius>=low)&(radius<high))) for name,low,high in
            [('r_0_17p35_mm',0,17.35),('r_17p35_82p5_mm',17.35,82.5),('r_82p5_120_mm',82.5,120),('r_above_120_mm',120,np.inf)]}


def analyze(mesh,sets,vtk,output):
    output.mkdir(parents=True,exist_ok=False)
    bad=read_set(sets/'underdeterminedCells');two=read_set(sets/'twoInternalFacesCells')
    nodes={};boundaries={};physical={};rows=[];cell_index=0
    with mesh.open() as stream:
        for line in stream:
            if line.strip()=='$PhysicalNames':
                count=int(next(stream))
                for _ in range(count):
                    fields=next(stream).split();physical[int(fields[0]),int(fields[1])]=fields[2].strip('"')
            elif line.strip()=='$Nodes':
                count=int(next(stream))
                for _ in range(count):
                    fields=next(stream).split();nodes[int(fields[0])]=np.array(list(map(float,fields[1:])))
            elif line.strip()=='$Elements':
                count=int(next(stream))
                for _ in range(count):
                    fields=list(map(int,next(stream).split()));tag,kind,n=fields[:3];conn=fields[3+n:]
                    if kind==2:boundaries[tuple(sorted(conn))]=physical[2,fields[3]]
                    elif kind==4:
                        if cell_index in bad:
                            points=np.array([nodes[i] for i in conn]);centre=points.mean(axis=0)*1000
                            wall=[boundaries[tuple(sorted(conn[i] for i in face))] for face in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)] if tuple(sorted(conn[i] for i in face)) in boundaries]
                            rows.append({'foam_cell_id':cell_index,'gmsh_element_id':tag,'x_mm':float(centre[0]),'y_mm':float(centre[1]),'z_mm':float(centre[2]),'radius_mm':float(np.linalg.norm(centre[:2])),
                                         'boundary_faces':len(wall),'touching_patches':'|'.join(sorted(set(wall))),'native_two_internal_faces_set':cell_index in two})
                        cell_index+=1
    if {r['foam_cell_id'] for r in rows}!=bad:raise ValueError('Native bad-cell labels could not be mapped to input mesh')
    if max(np.linalg.norm(x) for x in nodes.values())>.5:raise ValueError('Expected explicitly meter-unit input receipt')
    with (output/'underdetermined-cell-centres.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    points=np.array([[r['x_mm'],r['y_mm'],r['z_mm']] for r in rows])
    face_reports={}
    for name in ['skewFaces','lowWeightFaces','lowVolRatioFaces']:
        _,centres=vtk_faces(vtk/f'{name}.vtk');centres*=1000
        face_reports[name]={'native_rejected_faces':len(centres),'centres_mm':centres.tolist(),'radial_bands':bands(centres),'vtk_sha256':digest(vtk/f'{name}.vtk')}
    result={'status':'native_failure_localization_not_mesh_acceptance','mesh_sha256':digest(mesh),'input_units':'m','reported_coordinates':'mm, parametric assumption',
            'native_tetrahedra':cell_index,'underdetermined_cells':len(rows),'two_internal_face_cells':len(two),'two_internal_face_cells_in_underdetermined_set':len(two&bad),
            'boundary_face_count_histogram':{str(i):sum(r['boundary_faces']==i for r in rows) for i in range(5)},
            'patch_contact_histogram':{name:sum(name in r['touching_patches'].split('|') for r in rows) for name in ['rotor','duct','inlet','outlet']},
            'underdetermined_cell_radial_bands':bands(points),'underdetermined_cell_bounds_mm':[points.min(axis=0).tolist(),points.max(axis=0).tolist()],
            'face_reports':face_reports,'native_set_sha256':{n:digest(sets/n) for n in ['underdeterminedCells','twoInternalFacesCells','skewFaces','lowWeightFaces','lowVolRatioFaces']},
            'flow_solver_launched':False,'physical_geometry_validated':False,'manufacturing_authorized':False}
    (output/'localization.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mesh',type=Path);p.add_argument('sets',type=Path);p.add_argument('vtk',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(analyze(a.mesh,a.sets,a.vtk,a.output),indent=2))
