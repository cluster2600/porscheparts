#!/usr/bin/env python3
"""Mesh a study rotor STEP or its isolated shrouded fluid domain with Gmsh OCC."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time


def build(run, output, mode, size_mm=4.5, rpm=6000):
    import gmsh
    import numpy as np
    p=json.loads((run/'parameters.json').read_text())
    geometry=json.loads((run/'geometry-report.json').read_text())
    step=run/'rotor.step'
    if hashlib.sha256(step.read_bytes()).hexdigest()!=geometry['components']['rotor']['step_sha256']:
        raise ValueError('Rotor STEP does not match its geometry receipt')
    output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads',1)
        gmsh.option.setNumber('Mesh.MaxNumThreads1D',1)
        gmsh.option.setNumber('Mesh.MaxNumThreads2D',1)
        gmsh.option.setNumber('Mesh.MaxNumThreads3D',1)
        gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
        gmsh.model.add(p['configuration_id']+'_'+mode)
        rotor=gmsh.model.occ.importShapes(str(step),highestDimOnly=True)
        if len(rotor)!=1 or rotor[0][0]!=3:raise ValueError('Expected one rotor solid')
        R=p['diameter_mm']/2;gap=R*p['tip_gap_ratio'];barrel=p['diameter_mm']*.18
        if mode=='fluid':
            # OCC STEP import is in millimetres; explicit SI conversion before domain creation.
            gmsh.model.occ.dilate(rotor,0,0,0,.001,.001,.001)
            R*=.001;gap*=.001;barrel*=.001;lip=p['diameter_mm']*.0001
            cylinder=gmsh.model.occ.addCylinder(0,0,-barrel,0,0,2*barrel,R+gap)
            cone=gmsh.model.occ.addCone(0,0,barrel,0,0,lip,R+gap,(R+gap)*1.13)
            envelope,_=gmsh.model.occ.fuse([(3,cylinder)],[(3,cone)])
            volumes,_=gmsh.model.occ.cut(envelope,rotor)
            size=size_mm*.001;inlet_z=barrel+lip;outlet_z=-barrel
        else:
            volumes=rotor;size=size_mm
        gmsh.model.occ.synchronize()
        if len(volumes)!=1 or volumes[0][0]!=3:raise ValueError('Expected one connected volume')
        vtag=volumes[0][1];cad_volume=gmsh.model.occ.getMass(3,vtag)
        if cad_volume<=0:raise ValueError('Nonpositive CAD volume')
        group=gmsh.model.addPhysicalGroup(3,[vtag]);gmsh.model.setPhysicalName(3,group,'FLUID' if mode=='fluid' else 'ROTOR')
        boundaries={}
        if mode=='fluid':
            boundaries={key:[] for key in ['inlet','outlet','shroud','rotor']}
            for dim,tag in gmsh.model.getBoundary(volumes,oriented=False):
                xmin,ymin,zmin,xmax,ymax,zmax=gmsh.model.getBoundingBox(dim,tag)
                if abs(zmin-inlet_z)<1e-6 and abs(zmax-inlet_z)<1e-6:key='inlet'
                elif abs(zmin-outlet_z)<1e-6 and abs(zmax-outlet_z)<1e-6:key='outlet'
                elif xmax-xmin>=2*(R+gap)-1e-6 and ymax-ymin>=2*(R+gap)-1e-6:key='shroud'
                else:key='rotor'
                boundaries[key].append(tag)
            for key,tags in boundaries.items():
                if not tags:raise ValueError('Missing boundary '+key)
                physical=gmsh.model.addPhysicalGroup(2,tags);gmsh.model.setPhysicalName(2,physical,key)
        gmsh.option.setNumber('Mesh.MeshSizeMin',size*.12)
        gmsh.option.setNumber('Mesh.MeshSizeMax',size)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',12)
        gmsh.option.setNumber('Mesh.Algorithm',6)
        gmsh.option.setNumber('Mesh.Algorithm3D',1)
        gmsh.option.setNumber('Mesh.Optimize',1)
        gmsh.option.setNumber('Mesh.OptimizeThreshold',.3)
        gmsh.model.mesh.generate(3)
        if mode=='structural':gmsh.model.mesh.setOrder(2)
        etype=11 if mode=='structural' else 4
        types=list(gmsh.model.mesh.getElementTypes(3))
        if types!=[etype]:raise ValueError('Unexpected volume element types '+str(types))
        tags,connectivity=gmsh.model.mesh.getElementsByType(etype)
        points,weights=gmsh.model.mesh.getIntegrationPoints(etype,'Gauss4')
        _,determinants,_=gmsh.model.mesh.getJacobians(etype,points)
        determinants=np.asarray(determinants).reshape(len(tags),len(weights))
        if not np.isfinite(determinants).all() or determinants.min()<=0:raise ValueError('Nonpositive integration Jacobian')
        mesh_volume=float((determinants*np.asarray(weights)).sum())
        volume_error=abs(mesh_volume/cad_volume-1)
        if volume_error>.02:raise ValueError('Integrated mesh volume differs from CAD by over 2%')
        qualities=gmsh.model.mesh.getElementQualities(tags,'minSICN')
        if min(qualities)<=0:raise ValueError('Nonpositive element quality')
        ntags,coords,_=gmsh.model.mesh.getNodes();xyz=np.asarray(coords).reshape(-1,3)
        gmsh.write(str(output/'volume.msh'))
        report={'status':'positive_jacobian_volume_mesh','configuration_id':p['configuration_id'],
                'mode':mode,'units':'mm-N-s-tonne' if mode=='structural' else 'm-kg-s',
                'gmsh_version':gmsh.__version__,'source_step_sha256':hashlib.sha256(step.read_bytes()).hexdigest(),
                'mesher_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'size_mm_requested':size_mm,'nodes':len(ntags),'volume_elements':len(tags),
                'element_type':'C3D10' if mode=='structural' else 'linear_tetrahedron',
                'minimum_Gauss4_jacobian':float(determinants.min()),'minimum_scaled_jacobian':float(min(qualities)),
                'cad_volume':cad_volume,'integrated_mesh_volume':mesh_volume,'relative_volume_error':volume_error,
                'boundaries':boundaries,'physical_validation_established':False,'manufacturing_authorized':False}
        if mode=='structural':
            bore=R*p['bore_radius_ratio']
            fixed=[int(tag) for tag,v in zip(ntags,xyz) if abs(math.hypot(v[0],v[1])-bore)<.0005]
            if len(fixed)<8:raise ValueError('Insufficient bore restraint nodes')
            # Gmsh's final two tetrahedral edge nodes are reversed relative to C3D10.
            # Discover mapping from reference coordinates instead of assuming a version ordering.
            local=np.array(gmsh.model.mesh.getElementProperties(etype)[4]).reshape(10,3)
            target=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[.5,0,0],[.5,.5,0],[0,.5,0],[0,0,.5],[.5,0,.5],[0,.5,.5]])
            order=[int(np.argmin(np.linalg.norm(local-v,axis=1))) for v in target]
            if len(set(order))!=10 or not np.allclose(local[order],target):raise ValueError('Unknown C3D10 node order')
            lines=['*HEADING','Exploratory rotor; assumed aluminium and fully fixed bore; no qualification','*NODE']
            lines += [str(int(tag))+','+','.join(format(float(x),'.12g') for x in v) for tag,v in zip(ntags,xyz)]
            lines += ['*ELEMENT,TYPE=C3D10,ELSET=ROTOR']
            elements=np.asarray(connectivity).reshape(-1,10)[:,order]
            lines += [str(int(tag))+','+','.join(str(int(n)) for n in row) for tag,row in zip(tags,elements)]
            lines+=['*NSET,NSET=FIXED_BORE']+[','.join(str(n) for n in fixed[i:i+16]) for i in range(0,len(fixed),16)]
            lines+=['*MATERIAL,NAME=ASSUMED_ALUMINIUM','*ELASTIC','70000,0.33','*DENSITY','2.7e-9',
                    '*SOLID SECTION,ELSET=ROTOR,MATERIAL=ASSUMED_ALUMINIUM','*BOUNDARY','FIXED_BORE,1,3']
            base='\n'.join(lines)+'\n'
            omega=rpm*math.pi/30
            rotation='*STEP\n*STATIC\n*DLOAD\nROTOR,CENTRIF,'+format(omega*omega,'.12g')+',0,0,0,0,0,1\n*NODE FILE\nU\n*EL FILE\nS\n*NODE PRINT,NSET=FIXED_BORE,TOTALS=YES\nRF\n*END STEP\n'
            (output/'rotation.inp').write_text(base+rotation)
            (output/'modal.inp').write_text(base+'*STEP\n*FREQUENCY\n12\n*END STEP\n')
            report.update({'rpm_assumed':rpm,'restraint':'All translations fixed on hypothetical through-bore',
                           'fixed_bore_nodes':len(fixed),'material_assumed':{'E_MPa':70000,'nu':.33,'density_tonne_mm3':2.7e-9},
                           'modal_scope':'unprestressed; no gyroscopic terms, contact or measured bearings',
                           'gmsh_to_C3D10_node_permutation':order,'aerodynamic_or_thermal_load_included':False})
        report['elapsed_seconds']=time.monotonic()-start
        (output/'mesh-report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report));return report
    finally:gmsh.finalize()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--mode',choices=['structural','fluid'],required=True)
    parser.add_argument('--size-mm',type=float,default=4.5);parser.add_argument('--rpm',type=float,default=6000)
    args=parser.parse_args();build(args.run,args.output,args.mode,args.size_mm,args.rpm)
