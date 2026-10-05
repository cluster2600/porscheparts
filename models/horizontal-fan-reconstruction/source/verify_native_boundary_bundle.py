#!/usr/bin/env python3
"""Check real boundary topology/orientation and tessellation volume against CAD."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np


def verify(bundle,geometry,output):
    receipt=json.loads(bundle.with_suffix('.json').read_text());cad=json.loads(geometry.read_text())
    if hashlib.sha256(bundle.read_bytes()).hexdigest()!=receipt['field_bundle_sha256'] or receipt['source_step_sha256']!=cad['components']['rotor']['step_sha256']:raise ValueError('Bundle/CAD identity')
    f=np.load(bundle);x=f['xyz_mm'];u=f['released_displacement_mm'];tri=f['triangles'];ids=f['solver_node_id']
    if len(x)!=receipt['boundary_nodes'] or len(tri)!=receipt['linear_subtriangles'] or len(set(ids.tolist()))!=len(x) or not all(np.isfinite(v).all() for v in [x,u]):raise ValueError('Native boundary field coverage')
    if tri.min()<0 or tri.max()>=len(x):raise ValueError('Boundary index outside nodes')
    edges=Counter((int(a),int(b)) for t in tri for a,b in zip(t,np.roll(t,-1)))
    if any(edges[(b,a)]!=1 or count!=1 for (a,b),count in edges.items()):raise ValueError('Boundary oriented manifold failed')
    points=x[tri];area=np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]),axis=1)*.5
    volume=lambda p:float(np.einsum('ij,ij->i',p[:,0],np.cross(p[:,1],p[:,2])).sum()/6)
    v=volume(points);released=volume((x+u)[tri]);target=cad['components']['rotor']['volume_mm3'];error=abs(v-target)/target
    if area.min()<=0 or v<=0 or released<=0 or error>.02:raise ValueError('Boundary area/orientation/CAD-volume check')
    r={'status':'native_boundary_orientation_topology_and_volume_passed','field_bundle_sha256':receipt['field_bundle_sha256'],'geometry_report_sha256':hashlib.sha256(geometry.read_bytes()).hexdigest(),'all_boundary_nodes':len(x),'all_subtriangles':len(tri),'every_edge_has_two_opposite_orientations':True,'minimum_subtriangle_area_mm2':float(area.min()),'undeformed_signed_boundary_volume_mm3':v,'CAD_volume_mm3':target,'relative_linearized_boundary_volume_error':error,'volume_representation_bound_relative':.02,'released_signed_boundary_volume_mm3':released,'released_volume_change_percent':100*(released/v-1),'physical_validation_established':False,'manufacturing_acceptance_limit_defined':False}
    output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('geometry',type=Path);p.add_argument('output',type=Path);a=p.parse_args();verify(a.bundle,a.geometry,a.output)
