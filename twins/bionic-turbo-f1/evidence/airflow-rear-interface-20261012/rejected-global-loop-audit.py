#!/usr/bin/env python3
"""Verify a rear planar termination and a bounded-slope interface on unchanged CFD surfaces."""
import argparse
import json
import math
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import linprog
from audit_interface_corridor import read_patches, geometry
from prepare_case import sha


def cross2(a,b):
    return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def planar_annulus(triangles,z=-3.75,radius=32.):
    t=geometry.checked_triangles(triangles)
    selected=np.flatnonzero(np.all(t[:,:,2]==z,axis=1))
    if not len(selected):
        raise ValueError('No exactly planar stator facets')
    q=t[selected,:,:2]
    area=cross2(q[:,1]-q[:,0],q[:,2]-q[:,0])
    if not np.all(area<0):
        raise ValueError('Expected consistently downward planar facets')
    vertices,faces=np.unique(q.reshape(-1,2),axis=0,return_inverse=True)
    faces=faces.reshape(-1,3)
    directed=faces[:,[[0,1],[1,2],[2,0]]].reshape(-1,2)
    edges,inverse,counts=np.unique(np.sort(directed,axis=1),axis=0,return_inverse=True,return_counts=True)
    balance=np.bincount(inverse,weights=np.where(directed[:,0]<directed[:,1],1,-1))
    if np.any(counts>2) or np.any(balance[counts==2]!=0):
        raise ValueError('Nonmanifold or inconsistently directed planar edges')
    boundary=edges[counts==1]
    degree=np.bincount(boundary.ravel(),minlength=len(vertices))
    if not len(boundary) or np.any((degree!=0)&(degree!=2)):
        raise ValueError('Closed nonbranching planar boundary loops required')
    segments=vertices[boundary];delta=segments[:,1]-segments[:,0]
    fraction=np.clip(-np.einsum('ij,ij->i',segments[:,0],delta)/np.einsum('ij,ij->i',delta,delta),0,1)
    low=np.linalg.norm(segments[:,0]+fraction[:,None]*delta,axis=1)-geometry.MARGIN_MM
    high=np.linalg.norm(segments,axis=2).max(axis=1)+geometry.MARGIN_MM
    if np.any((low<=radius)&(high>=radius)) or not np.any(high<radius) or not np.any(low>radius):
        raise ValueError('No boundary-free annulus around the requested radius')
    inner=float(high[high<radius].max());outer=float(low[low>radius].min())
    point=radius*np.array([math.cos(.123456789),math.sin(.123456789)])
    signs=cross2(np.roll(q,-1,axis=1)-q,point-q)
    covered=np.flatnonzero((signs<0).all(axis=1))
    if len(covered)!=1 or np.min(np.abs(signs[covered[0]]))<=1e-10:
        raise ValueError('Strict single-coverage seed required')
    return dict(plane_z_mm=z,probe_radius_mm=radius,planar_facets=len(q),boundary_edges=len(boundary),
                boundary_vertex_degree_two=True,internal_edge_orientations_cancel=True,downward_orientation=True,
                annulus_inner_radius_mm=inner,annulus_outer_radius_mm=outer,coverage_seed_xy_mm=point.tolist(),
                seed_stator_face=int(selected[covered[0]]),seed_triangle_mm=t[selected[covered[0]]].tolist(),
                complete_angular_coverage=True,
                proof='All triangles have the same orientation; interior edges cancel; no boundary edge enters this connected open annulus. Single strict coverage at one point therefore extends over the entire annulus, without angular sampling.')


def bounded_profile(a,b):
    if len(a['bands'])!=len(b['bands']):
        raise ValueError('Matched axial bands required')
    indices=a['corridor']['open_profiles'][0]['band_indices']
    if indices!=b['corridor']['open_profiles'][0]['band_indices'] or indices!=list(range(3,359)):
        raise ValueError('Expected complete retained corridor from -3.5 to 32.1 mm')
    rows=[a['bands'][i] for i in indices];other=[b['bands'][i] for i in indices]
    z=np.array([r['z_low_mm'] for r in rows]+[rows[-1]['z_high_mm']])
    if np.any(np.diff(z)<=0) or any(r['z_low_mm']!=s['z_low_mm'] or r['z_high_mm']!=s['z_high_mm'] for r,s in zip(rows,other)):
        raise ValueError('Aligned increasing axial stations required')
    margin=math.floor(min(a['corridor']['open_profiles'][0]['minimum_radial_separation_bound_mm'],b['corridor']['open_profiles'][0]['minimum_radial_separation_bound_mm'])*1e6)/1e6
    cosine=math.cos(math.pi/128);limits=[]
    for j in range(len(z)):
        neighbours=range(max(0,j-1),min(len(rows),j+1))
        lo=max(max(rows[i]['rotor_upper_mm'],other[i]['rotor_upper_mm']) for i in neighbours)
        hi=min(min(rows[i]['stator_lower_mm'],other[i]['stator_lower_mm']) for i in neighbours)
        limits.append(((lo+margin+geometry.MARGIN_MM)/cosine,hi-margin-geometry.MARGIN_MM))
    if not limits[0][0]<32<limits[0][1]:
        raise ValueError('Rear radius outside retained corridor')
    limits[0]=(32,32);n=len(z);matrix=[]
    for i,dz in enumerate(np.diff(z)):
        for sign in (-1,1):
            row=np.zeros(n+1);row[i]=-sign;row[i+1]=sign;row[-1]=-dz;matrix.append(row)
    objective=np.zeros(n+1);objective[-1]=1
    solution=linprog(objective,A_ub=np.array(matrix),b_ub=np.zeros(len(matrix)),bounds=limits+[(0,None)],method='highs')
    if not solution.success or not np.isfinite(solution.x).all():
        raise ValueError('No bounded-slope feasible profile: '+solution.message)
    radii=solution.x[:-1];separations=[]
    for j,(r,s) in enumerate(zip(rows,other)):
        lo=max(r['rotor_upper_mm'],s['rotor_upper_mm']);hi=min(r['stator_lower_mm'],s['stator_lower_mm'])
        separations.append(min(min(radii[j:j+2])*cosine-lo,hi-max(radii[j:j+2])))
    if min(separations)<margin:
        raise ValueError('Independent full-band clearance check failed')
    return dict(nodes_z_radius_mm=[[-4.,32.],[-3.75,32.]]+np.column_stack((z,radii)).tolist()+[[33.,float(radii[-1])]],
                sectors=128,retained_radial_clearance_mm=margin,verified_radial_clearance_mm=min(separations),
                maximum_absolute_slope=float(np.max(np.abs(np.diff(radii)/np.diff(z)))),
                method='Minimize maximum absolute piecewise-linear slope within both frozen band bounds; retain prior proven clearance rounded down to 1e-6 mm; independently recheck every band. No solver tolerance changes.')


def crossing_facets(t,z0,z1,r0,r1):
    indices=np.flatnonzero((t[:,:,2].min(axis=1)<=z1+geometry.MARGIN_MM)&(t[:,:,2].max(axis=1)>=z0-geometry.MARGIN_MM))
    if not len(indices):
        return indices
    q=t[indices];low=geometry.projected_min_radius(q);high=np.linalg.norm(q[:,:,:2],axis=2).max(axis=1)+geometry.MARGIN_MM
    return indices[(low<=r1)&(high>=r0)]


def audit(cases,profile_paths):
    reports=[json.loads(p.read_text()) for p in profile_paths]
    for report in reports:
        if report['source_sha256']!=sha(Path(__file__).with_name('audit_interface_corridor.py')) or report['geometry_source_sha256']!=sha(Path(geometry.__file__)):
            raise ValueError('Changed corridor source')
    profile=bounded_profile(*reports);variants={}
    top_radius=profile['nodes_z_radius_mm'][-1][1];cosine=math.cos(math.pi/128)
    for label,case,report in zip(('baseline','candidate'),cases,reports):
        manifest=case/'case-manifest.json';info=json.loads(manifest.read_text())['surface']
        if sha(manifest)!=report['case_manifest_sha256'] or info['sha256']!=report['surface_sha256']:
            raise ValueError('Corridor and CFD case do not match')
        patches=read_patches(case/'constant/triSurface/domain.stl',info)
        annulus=planar_annulus(patches['stator'])
        if not annulus['annulus_inner_radius_mm']<32*cosine<32<annulus['annulus_outer_radius_mm']:
            raise ValueError('Faceted rear ring leaves the planar annulus')
        counts={}
        for name,t in patches.items():
            selected=crossing_facets(t,-4,-3.5,32*cosine,32)
            counts[name]=len(selected)
            if len(selected) and (name!='stator' or not np.all(t[selected,:,2]==-3.75)):
                raise ValueError('Rear side crosses an unexpected boundary')
            if len(crossing_facets(t,-4,-4,0,32)):
                raise ValueError('Bottom disk intersects CFD boundary')
            if len(crossing_facets(t,33,33,0,top_radius)):
                raise ValueError('Front disk intersects CFD boundary')
            if len(crossing_facets(t,32.1,33,top_radius*cosine,top_radius)):
                raise ValueError('Front extension intersects CFD boundary')
            if name in ('inlet','outlet') and len(crossing_facets(t,-4,33,0,max(r for _,r in profile['nodes_z_radius_mm']))):
                raise ValueError('Interface may cross a port')
        winding={}
        for label_point,point,expected in (('bottom_disk',[0,0,-4],0),('front_disk',[0,0,33],1),('rear_above',[32,0,-3.6],1),('rear_below',[32,0,-3.9],0)):
            value=sum(geometry.solid_winding_number(t,point) for t in patches.values())
            if abs(value-expected)>1e-6:
                raise ValueError('Closed-fluid-boundary containment failed at '+label_point)
            winding[label_point]=dict(point_mm=point,value=value,expected=expected)
        variants[label]=dict(surface_sha256=info['sha256'],case_manifest_sha256=sha(manifest),annulus=annulus,
                             rear_crossing_facet_counts=counts,closed_fluid_boundary_winding=winding)
    return dict(schema='bionic-turbo-rear-interface/v1',source_sha256=sha(Path(__file__)),
                geometry_source_sha256=sha(Path(geometry.__file__)),reader_source_sha256=sha(Path(__file__).with_name('audit_interface_corridor.py')),
                profile_input_sha256=[sha(p) for p in profile_paths],profile=profile,variants=variants,
                geometric_interface_candidate_verified=True,solver_admission_granted=False,performance_ranking_authorized=False,
                interpretation='Geometric candidate only. Rear side meets the exact planar stator annulus; lower closing disk is outside fluid, upper disk is inside fluid. Preserved full-band bounds exclude other side intersections. No volume mesh, wall layers, convergence or physical qualification is granted.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('candidate',type=Path)
    parser.add_argument('baseline_profile',type=Path);parser.add_argument('candidate_profile',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=audit([args.baseline,args.candidate],[args.baseline_profile,args.candidate_profile])
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
