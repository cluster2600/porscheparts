#!/usr/bin/env python3
"""Split multi-boundary tetrahedra at their centroid without changing surfaces.

This is a mesh experiment, not acceptance. Standard and extended independent
checks still apply. Input and output coordinates remain meters.
"""
import argparse
import hashlib
import json
from pathlib import Path

import gmsh
import numpy as np


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):digest.update(chunk)
    return digest.hexdigest()


def split(source,output):
    output.mkdir(parents=True,exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads',2)
        gmsh.open(str(source))
        volumes=gmsh.model.getEntities(3)
        if len(volumes)!=1:raise ValueError('One original fluid volume required')
        volume=volumes[0][1]
        types,tags,conn=gmsh.model.mesh.getElements(3,volume)
        if list(types)!=[4] or len(tags[0])>2000000:raise ValueError('Bounded linear tetrahedral input required')
        cells=np.asarray(conn[0]).reshape(-1,4)
        boundary=set()
        for _,surface in gmsh.model.getEntities(2):
            st,_,sc=gmsh.model.mesh.getElements(2,surface)
            if list(st)!=[2]:raise ValueError('Triangular original boundaries required')
            boundary.update(tuple(sorted(map(int,tri))) for tri in np.asarray(sc[0]).reshape(-1,3))
        selected=[]
        for index,cell in enumerate(cells):
            count=sum(tuple(sorted(map(int,cell[list(face)]))) in boundary for face in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)])
            if count>=2:selected.append(index)
        if not selected:raise ValueError('No multi-boundary cells; no change proposed')
        node_tags,xyz,_=gmsh.model.mesh.getNodes()
        xyz=np.asarray(xyz).reshape(-1,3)
        positions={int(tag):point for tag,point in zip(node_tags,xyz)}
        picked=cells[selected]
        centers=np.array([np.mean([positions[int(n)] for n in cell],axis=0) for cell in picked])
        new_tags=np.arange(int(node_tags.max())+1,int(node_tags.max())+1+len(selected),dtype=np.uint64)
        # Gmsh 4.12 lacks removeElements. Rebuild only the volume entity;
        # boundary-classified nodes and triangles stay intact.
        interior_tags,interior_xyz,_=gmsh.model.mesh.getNodes(3,volume)
        gmsh.model.mesh.clear([(3,volume)])
        gmsh.model.mesh.addNodes(3,volume,interior_tags,interior_xyz)
        gmsh.model.mesh.addNodes(3,volume,new_tags,centers.ravel())
        keep=np.ones(len(cells),dtype=bool);keep[selected]=False
        gmsh.model.mesh.addElementsByType(volume,4,np.asarray(tags[0])[keep],cells[keep].ravel())
        children=[]
        for (a,b,c,d),m in zip(picked,new_tags):
            children.extend([(a,b,c,m),(a,b,m,d),(a,m,c,d),(m,b,c,d)])
        ids=np.arange(int(tags[0].max())+1,int(tags[0].max())+1+len(children),dtype=np.uint64)
        gmsh.model.mesh.addElementsByType(volume,4,ids,np.asarray(children,dtype=np.uint64).ravel())
        _,final_tags,_=gmsh.model.mesh.getElements(3,volume)
        qualities=gmsh.model.mesh.getElementQualities(final_tags[0],'minSICN')
        if not np.isfinite(qualities).all() or qualities.min()<=0:raise ValueError('Nonpositive tetrahedron quality')
        gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
        gmsh.option.setNumber('Mesh.ScalingFactor',1)
        target=output/'fluid.msh';gmsh.write(str(target))
        result={'status':'split_generated_requires_independent_extended_mesh_checks',
                'input_mesh_sha256':sha(source),'output_mesh_sha256':sha(target),
                'input_tetrahedra':len(tags[0]),'split_tetrahedra':len(selected),
                'output_tetrahedra':len(final_tags[0]),'minimum_SICN':float(qualities.min()),
                'boundary_face_connectivity_and_original_nodes_unchanged':True,
                'surface_geometry_changed':False,'units':'m','gmsh_version':gmsh.__version__,
                'flow_solver_launched':False,'manufacturing_authorized':False}
        (output/'split-preparation.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:gmsh.finalize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(split(a.source,a.output),indent=2))
