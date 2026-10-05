#!/usr/bin/env python3
"""Regularize an original parametric surface or mesh its hypothetical test duct.

Outputs require independent surfaceCheck/checkMesh and surface-distance audits.
No private scan, physical interface or installed performance is inferred.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import trimesh


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closed(mesh):
    if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.body_count==1
            and mesh.volume>0 and np.isfinite(mesh.vertices).all() and (mesh.area_faces>0).all()):
        raise ValueError('Positive closed oriented connected surface required')


def remesh(source, output, edge, distance, iterations=1, design_revision=False):
    import pymeshlab
    original=trimesh.load_mesh(source,process=True)
    closed(original)
    if not 0<edge<=3 or not 0<distance<=(.25 if design_revision else .2) or not 1<=iterations<=5:
        raise ValueError('Surface regularization must use explicit bounded mm settings')
    output.mkdir(parents=True,exist_ok=False)
    ms=pymeshlab.MeshSet()
    ms.load_new_mesh(str(source))
    # The remesher's local operation limit is not a final surface-error bound.
    # Use a tighter internal limit and retain the independent final gate.
    operation_distance=.1 if design_revision else distance/5
    settings={'iterations':iterations,'targetlen':pymeshlab.PureValue(edge),'featuredeg':180,
              'checksurfdist':True,'maxsurfdist':pymeshlab.PureValue(operation_distance)}
    ms.apply_filter('meshing_isotropic_explicit_remeshing',**settings)
    surface=output/'rotor-mm.stl'
    ms.save_current_mesh(str(surface))
    reduced=trimesh.load_mesh(surface,process=True)
    closed(reduced)
    if reduced.euler_number != original.euler_number:
        raise ValueError('Surface topology changed; opening retention is unresolved')
    volume_error=abs(reduced.volume/original.volume-1)
    if volume_error>=.002:
        raise ValueError('Regularization volume error exceeds screening bound')
    deviations={}
    # Area-weighted sampled distance, not a Hausdorff bound or physical accuracy.
    for name,a,b in [('source_to_regularized',original,reduced),('regularized_to_source',reduced,original)]:
        points,_=trimesh.sample.sample_surface(a,5000,seed=993)
        _,errors,_=trimesh.proximity.closest_point(b,points)
        deviations[name]={'samples':len(errors),'rms_mm':float(np.sqrt(np.mean(errors**2))),
                          'p95_mm':float(np.quantile(errors,.95)),'max_sampled_mm':float(errors.max())}
    accepted=max(d['max_sampled_mm'] for d in deviations.values())<=distance*1.05
    metre=output/'rotor-metres.stl'
    reduced.apply_scale(.001);reduced.export(metre)
    result={'status':'regularized_requires_independent_surface_and_mesh_checks' if accepted else 'rejected_surface_distance',
            'source_sha256':sha(source),'surface_sha256':sha(surface),'metres_sha256':sha(metre),
            'pymeshlab_version':importlib.metadata.version('pymeshlab'),
            'design_revision':design_revision,
            'design_revision_id':'organic-e-r1' if design_revision else None,
            'source_and_result_euler_characteristic':[int(original.euler_number),int(reduced.euler_number)],
            'settings':{'target_edge_mm':edge,'distance_limit_mm':distance,'operation_distance_limit_mm':operation_distance,'iterations':iterations,'feature_angle_deg':180},
            'relative_volume_error':float(volume_error),'distance_to_source':deviations,
            'sampled_only_not_hausdorff':True,'physical_scale_or_fit_validated':False,
            'private_scan_used':False,'manufacturing_authorized':False}
    (output/'surface-preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    if not accepted:
        raise ValueError('Independent sampled deviation exceeds regularization setting')
    return result


def fluid_mesh(source, output, algorithm, netgen=False, relocate=False):
    import gmsh
    rotor=trimesh.load_mesh(source,process=True)
    closed(rotor)
    if not 240<rotor.extents[0]<246:
        raise ValueError('This explicit hypothetical duct requires the 245 mm model in mm')
    output.mkdir(parents=True,exist_ok=False)
    rotor.export(output/'rotor.stl')
    n=144
    theta=np.arange(n)*2*np.pi/n
    zs=np.linspace(-180,180,37)
    points=np.array([[124*np.cos(t),124*np.sin(t),z] for z in zs for t in theta])
    faces=[]
    for j in range(len(zs)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=b+n;d=a+n
            faces.extend([[a,b,c],[a,c,d]])
    trimesh.Trimesh(points,faces,process=False).export(output/'duct.stl')
    for name,z,reverse in [('inlet',-180,True),('outlet',180,False)]:
        radii=np.linspace(124/13,124,13)
        points=np.array([[0,0,z]]+[[r*np.cos(t),r*np.sin(t),z] for r in radii for t in theta])
        faces=[[0,1+i,1+(i+1)%n] for i in range(n)]
        for j in range(12):
            for i in range(n):
                a=1+j*n+i;b=1+j*n+(i+1)%n;c=b+n;d=a+n
                faces.extend([[a,b,c],[a,c,d]])
        if reverse:
            faces=np.array(faces)[:,::-1]
        trimesh.Trimesh(points,faces,process=False).export(output/f'{name}.stl')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads',2)
        patches={}
        for name in ['rotor','duct','inlet','outlet']:
            before=set(gmsh.model.getEntities(2));gmsh.merge(str(output/f'{name}.stl'))
            patches[name]=[tag for dim,tag in set(gmsh.model.getEntities(2))-before]
        gmsh.model.mesh.removeDuplicateNodes()
        outer=gmsh.model.geo.addSurfaceLoop(patches['duct']+patches['inlet']+patches['outlet'])
        inner=gmsh.model.geo.addSurfaceLoop(patches['rotor'])
        volume=gmsh.model.geo.addVolume([outer,inner]);gmsh.model.geo.synchronize()
        for name,tags in patches.items():
            gmsh.model.addPhysicalGroup(2,tags,name=name)
        gmsh.model.addPhysicalGroup(3,[volume],name='fluid')
        gmsh.option.setNumber('Mesh.MeshOnlyEmpty',1)
        gmsh.option.setNumber('Mesh.Algorithm3D',algorithm)
        # Avoid propagating a very short STL edge throughout the fluid volume.
        # Boundary facets remain unchanged and may still fail extended QA.
        gmsh.option.setNumber('Mesh.MeshSizeMin',.5)
        gmsh.option.setNumber('Mesh.MeshSizeMax',12)
        gmsh.model.mesh.generate(3)
        if netgen:
            gmsh.model.mesh.optimize('Netgen')
        if relocate:
            gmsh.model.mesh.optimize('Relocate3D',niter=5)
        types,tags,_=gmsh.model.mesh.getElements(3)
        if list(types)!=[4]:
            raise ValueError('Linear tetrahedral fluid mesh required')
        quality=gmsh.model.mesh.getElementQualities(tags[0],'minSICN')
        if not np.isfinite(quality).all() or quality.min()<=0:
            raise ValueError('Inverted/degenerate fluid tetrahedra; no handoff')
        gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
        gmsh.option.setNumber('Mesh.ScalingFactor',.001)
        gmsh.write(str(output/'fluid.msh'))
        report={'status':'volume_mesh_generated_requires_openfoam_extended_check',
                'gmsh_version':gmsh.__version__,'algorithm':algorithm,'threads':2,
                'netgen_optimization_requested':netgen,
                'relocate3d_optimization_requested':relocate,
                'volume_size_bounds_mm':[.5,12],
                'source_surface_sha256':sha(source),'mesh_sha256':sha(output/'fluid.msh'),
                'tetrahedra':len(tags[0]),'minimum_SICN':float(quality.min()),
                'output_units':'m','duct_radius_mm_assumed':124,'domain_length_mm_assumed':360,
                'minimum_vertex_radial_clearance_mm':float(124-np.linalg.norm(rotor.vertices[:,:2],axis=1).max()),
                'wall_layers':False,'installed_assembly_included':False,
                'physical_fit_verified':False,'manufacturing_authorized':False}
        (output/'mesh-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    finally:
        gmsh.finalize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['surface','design-surface','volume'])
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--edge-mm',type=float,default=1.5)
    p.add_argument('--distance-mm',type=float,default=.1)
    p.add_argument('--iterations',type=int,choices=range(1,6),default=1)
    p.add_argument('--algorithm',type=int,choices=[1,10],default=10)
    p.add_argument('--netgen',action='store_true')
    p.add_argument('--relocate',action='store_true')
    a=p.parse_args()
    report=fluid_mesh(a.source,a.output,a.algorithm,a.netgen,a.relocate) if a.stage=='volume' else remesh(a.source,a.output,a.edge_mm,a.distance_mm,a.iterations,a.stage=='design-surface')
    print(json.dumps(report,indent=2))
