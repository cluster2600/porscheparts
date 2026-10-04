#!/usr/bin/env python3
"""Audit an actual mesh boundary against its original meter-unit source."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def extract_rotor(path):
    points=[];faces=[];group=None
    with path.open() as stream:
        for line in stream:
            fields=line.split()
            if not fields:continue
            if fields[0]=='v':points.append(list(map(float,fields[1:4])))
            elif fields[0]=='g':group=fields[1]
            elif fields[0]=='f' and group=='rotor':
                if len(fields)!=4:raise ValueError('Native triangular rotor boundary required')
                ids=[int(item.split('/')[0])-1 for item in fields[1:]]
                if min(ids)<0 or max(ids)>=len(points):raise ValueError('Native OBJ vertex IDs invalid')
                faces.append(ids)
    if not faces:raise ValueError('Native rotor group missing')
    mesh=trimesh.Trimesh(points,faces,process=False);mesh.remove_unreferenced_vertices()
    # Fluid-domain normals point into the solid; invert the entire patch only.
    if mesh.volume<0:mesh.invert()
    return mesh


def audit(source,boundary,output):
    original=trimesh.load_mesh(source,process=True);mesh=extract_rotor(boundary)
    if max(np.linalg.norm(original.vertices,axis=1))>.5:raise ValueError('Explicit meter source required')
    deviations={}
    for name,a,b in [('source_to_mesh',original,mesh),('mesh_to_source',mesh,original)]:
        points,_=trimesh.sample.sample_surface(a,5000,seed=993)
        nearest,errors,_=trimesh.proximity.closest_point(b,points);errors*=1000
        index=int(np.argmax(errors))
        deviations[name]={'samples':len(errors),'rms_mm':float(np.sqrt(np.mean(errors**2))),
                          'p95_mm':float(np.quantile(errors,.95)),'max_sampled_mm':float(errors.max()),
                          'samples_above_0p2mm':int((errors>.2).sum()),
                          'maximum_error_sample_mm':(points[index]*1000).tolist(),
                          'nearest_point_at_maximum_error_mm':(nearest[index]*1000).tolist()}
    volume_error=float(abs(mesh.volume/original.volume-1))
    edge_counts=np.bincount(mesh.edges_unique_inverse)
    bad_edges=mesh.edges_unique[edge_counts!=2]
    bad_centres=mesh.vertices[bad_edges].mean(axis=1)*1000
    gates={'closed_oriented_connected':bool(mesh.is_watertight and mesh.is_winding_consistent and mesh.body_count==1 and mesh.volume>0),
           'original_euler_retained':mesh.euler_number==original.euler_number,
           'all_triangles_positive_area':bool((mesh.area_faces>0).all()),
           'sampled_bidirectional_distance_le_0p2mm':max(r['max_sampled_mm'] for r in deviations.values())<=.2,
           'relative_volume_error_lt_0p002':volume_error<.002}
    result={'status':'passed_numerical_surface_representation' if all(gates.values()) else 'rejected_numerical_surface_representation',
            'gates':gates,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'native_boundary_sha256':hashlib.sha256(boundary.read_bytes()).hexdigest(),
            'units':'m','reported_distance_units':'mm','source_and_mesh_euler':[int(original.euler_number),int(mesh.euler_number)],
            'rotor_triangles':len(mesh.faces),'rotor_vertices':len(mesh.vertices),
            'rotor_zero_area_triangles':int((mesh.area_faces<=0).sum()),
            'rotor_watertight':bool(mesh.is_watertight),'rotor_winding_consistent':bool(mesh.is_winding_consistent),
            'rotor_components':int(mesh.body_count),'relative_volume_error':volume_error,'distances':deviations,
            'edge_incidence_histogram':{str(int(i)):int((edge_counts==i).sum()) for i in np.unique(edge_counts)},
            'nonmanifold_edge_centres_mm':bad_centres.tolist(),
            'sampled_only_not_hausdorff':True,'physical_geometry_validated':False,'flow_solver_launched':False,'manufacturing_authorized':False}
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','boundary','output']:p.add_argument(name,type=Path)
    a=p.parse_args();print(json.dumps(audit(a.source,a.boundary,a.output),indent=2))
