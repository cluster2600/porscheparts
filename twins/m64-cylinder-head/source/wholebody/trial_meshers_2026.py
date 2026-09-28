#!/usr/bin/env python3
"""Isolated 2026 mesher trials; reuse the existing Gmsh quality/topology gates.

Private output only. A polygon-conforming mesh is not native-CAD conformance.
Neither a completed solver nor a passing coarse check authorizes CAE or AM.
"""
import argparse
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import sys
import subprocess
import time

from run_local_surface_trial import BODY_SHA, HELPER_SHA, native

MESH_SHA='965de13aefda6f5a314c9edee295578b4f638d58c173dfe2098d77ae21e4e7af'


def read_inner_tets(path):
    """CLI includes inner/outer counts; the 1.0.1 Python API loses that split."""
    import numpy as np
    with path.open() as stream:
        header=[stream.readline().split() for _ in range(3)]
        if [row[1:] for row in header]!=[['vertices'],['inner','tets'],['outer','tets']]:
            raise ValueError('classified_CDT_header_required')
        nv,ni,no=[int(row[0]) for row in header]
        if not (0<nv<=3000000 and 0<ni<=3000000 and 0<=no<=10000000):
            raise ValueError('classified_mesh_count_out_of_bounds')
        points=np.array([[float(v) for v in stream.readline().split()] for _ in range(nv)])
        cells=[]
        for index in range(ni+no):
            row=[int(v) for v in stream.readline().split()]
            if len(row)!=5 or row[0]!=4: raise ValueError('invalid_tetra_record')
            if min(row[1:])<0 or max(row[1:])>=nv: raise ValueError('invalid_node_index')
            if index<ni: cells.append(row[1:])
        if stream.read().strip(): raise ValueError('unexpected_extra_mesh_records')
    return points,np.array(cells,dtype=np.int64),{'inner_tetrahedra':ni,'outer_tetrahedra_excluded':no}


def normalize_convention(points, cells):
    import numpy as np
    if (points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all()
            or cells.ndim!=2 or cells.shape[1]!=4 or not len(cells)
            or cells.min()<0 or cells.max()>=len(points)):
        raise ValueError('invalid_tetra_arrays')
    xyz=points[cells]; determinants=np.linalg.det(xyz[:,1:]-xyz[:,[0]])
    if not np.isfinite(determinants).all(): raise ValueError('nonfinite_determinants')
    # Only a UNIFORM library convention is converted; never repair mixed signs.
    reverse=bool((determinants<0).all())
    if not reverse and not (determinants>0).all(): raise ValueError('mixed_or_zero_tetra_orientation')
    return cells[:,[0,2,1,3]].copy() if reverse else cells.copy(), reverse


def boundary(cells):
    import numpy as np
    faces=np.concatenate([cells[:,ids] for ids in ((1,2,3),(0,3,2),(0,1,3),(0,2,1))])
    _,indices,counts=np.unique(np.sort(faces,axis=1),axis=0,return_index=True,return_counts=True)
    if (counts>2).any(): raise ValueError('nonmanifold_tetra_faces')
    return faces[indices[counts==1]]


def read_gmsh(path):
    import gmsh
    import numpy as np
    gmsh.clear(); gmsh.open(str(path))
    tags,xyz,_=gmsh.model.mesh.getNodes(); order=np.argsort(tags); tags=tags[order]
    points=np.asarray(xyz,dtype=np.float64).reshape(-1,3)[order]
    types,element_tags,nodes=gmsh.model.mesh.getElements(3)
    stypes,_,snodes=gmsh.model.mesh.getElements(2)
    if list(types)!=[4] or list(stypes)!=[2]: raise ValueError('linear_tets_and_triangles_required')
    arrays=[]
    for flat,width in ((nodes[0],4),(snodes[0],3)):
        indices=np.searchsorted(tags,flat)
        if indices.max()>=len(tags) or not np.array_equal(tags[indices],flat):
            raise ValueError('invalid_mesh_node_reference')
        arrays.append(indices.reshape(-1,width).astype(np.int64))
    return points,*arrays,element_tags[0]


def audit_output(points,cells,faces,path):
    import gmsh
    import numpy as np
    if len(cells)>3000000: raise ValueError('three_million_tetra_audit_cap')
    cells,reversed_convention=normalize_convention(points,cells)
    gmsh.clear(); gmsh.model.add('private_diagnostic_not_CAE_ready')
    gmsh.model.addDiscreteEntity(2,1); gmsh.model.addDiscreteEntity(3,1,[1])
    gmsh.model.mesh.addNodes(3,1,np.arange(1,len(points)+1),points.ravel())
    gmsh.model.mesh.addElementsByType(1,2,[],(faces+1).ravel())
    gmsh.model.mesh.addElementsByType(1,4,[],(cells+1).ravel())
    gmsh.option.setNumber('Mesh.Binary',1); gmsh.option.setNumber('Mesh.SaveAll',1)
    gmsh.write(str(path)); path.chmod(0o600)
    rp,rc,rf,tags=read_gmsh(path)
    roundtrip=bool(np.array_equal(points,rp) and np.array_equal(cells,rc) and np.array_equal(faces,rf))
    qualities=list(map(float,gmsh.model.mesh.getElementQualities(tags,'minSICN')))
    determinants=list(map(float,gmsh.model.mesh.getElementQualities(tags,'minDetJac')))
    quality=native.reread_quality_gate(qualities,determinants,len(cells))
    connectivity=native.connectivity_metrics(dict(enumerate(tuple(map(float,p)) for p in rp)),rc.tolist(),rf.tolist())
    # Independent divergence-theorem sum, translated to reduce cancellation.
    xyz=rp[rf]-rp.mean(0)
    flux=np.einsum('ij,ij->i',xyz[:,0],np.cross(xyz[:,1],xyz[:,2]))/6
    flux_volume=math.fsum(map(float,flux))
    oriented_volume=connectivity['signed_volume_sum']
    result={'sha256':native.sha256(path),'uniform_orientation_permutation':reversed_convention,
        'roundtrip_exact':roundtrip,'quality':quality,'connectivity':connectivity,
        'boundary_flux_volume':flux_volume,'tetra_volume':oriented_volume,
        'flux_relative_difference':abs(abs(flux_volume)/oriented_volume-1)}
    result['coarse_checks_passed']=bool(roundtrip and quality['passed']
        and connectivity['boundary_matches'] and connectivity['tetra_connected_components']==1
        and not connectivity['count_negative'] and not connectivity['count_zero']
        and result['flux_relative_difference']<=1e-10)
    return result


def run(args):
    import gmsh
    import numpy as np
    expected=MESH_SHA if args.engine=='delmesher' else BODY_SHA
    pins={args.input:expected,Path(native.__file__):HELPER_SHA,Path(__file__):native.sha256(__file__)}
    if (args.output.exists() or any(p.is_symlink() or native.sha256(p)!=s for p,s in pins.items())
            or gmsh.__version__!='4.15.2' or np.__version__!='2.2.6'):
        raise ValueError('fresh_output_exact_inputs_and_runtime_required')
    args.output.mkdir(mode=0o700,parents=True); started=time.monotonic()
    report={'schema':'m64-2026-mesher-trial/v1','engine':args.engine,'status':'incomplete',
        'input_sha256':expected,'source_sha256':pins[Path(__file__)],'helper_sha256':HELPER_SHA,
        'gmsh_version':gmsh.__version__,'numpy_version':np.__version__,
        'native_CAD_conformance_certified':False,'boundary_roles_transferred':False,
        'CAE_authorized':False,'manufacturing_authorized':False}
    target=args.output/'report.json'; native.save(target,report)
    gmsh.initialize(['trial','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try:
        if args.engine=='delmesher':
            import delmesher
            report['engine_version']=metadata.version('delmesher')
            if report['engine_version']!='1.0.1': raise ValueError('delmesher_version')
            p,c,f,_=read_gmsh(args.input)
            c,reverse=normalize_convention(p,c)
            if reverse: raise ValueError('reference_mesh_orientation_changed')
            bf=boundary(c)
            if set(map(tuple,np.sort(f,axis=1)))!=set(map(tuple,np.sort(bf,axis=1))):
                raise ValueError('input_surface_is_not_volume_boundary')
            used,inverse=np.unique(bf,return_inverse=True)
            vertices=p[used]; triangles=inverse.reshape(-1,3).astype(np.uint32)
            options=dict(enriched_cdt=True,sliver_removal=True,lfs_exponent=None,
                         max_vertices=args.max_vertices,compute_lfs=False,verbose=True)
            report.update(options=options,refinement_capped=args.max_vertices is not None,
                          input_surface_vertices=len(vertices),input_surface_triangles=len(triangles))
            native.save(target,report)
            if not args.delmesher_cli: raise ValueError('classified_CLI_output_required')
            executable=args.delmesher_cli.resolve()
            report['executable_sha256']=native.sha256(executable)
            off=args.output/'input-private.off'; delmesher.write_off(off,vertices,triangles)
            command=[str(executable),'-d','-z','-v']
            if args.max_vertices is not None: command+=['-m',str(args.max_vertices)]
            command.append(str(off.resolve())); report['command']=command
            native.save(target,report)
            with (args.output/'delmesher.log').open('x') as log:
                subprocess.run(command,cwd=args.output,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
            points,cells,classification=read_inner_tets(args.output/'enrichedCDT_mesh.tet')
            report['classification']=classification
            if native.sha256(executable)!=report['executable_sha256']: raise ValueError('executable_changed')
            report['polygon_conformance_claim']='library_claim_pending_independent_geometric_check'
            normalized,_=normalize_convention(points,cells); faces=boundary(normalized)
        else:
            from netgen.occ import OCCGeometry
            report['engine_version']=metadata.version('netgen-mesher')
            if report['engine_version']!='6.2.2607': raise ValueError('netgen_version')
            geo=OCCGeometry(str(args.input))
            report.update(imported_faces=len(geo.shape.faces),imported_solids=len(geo.shape.solids),
                          imported_volume=geo.shape.mass,options={'maxh':6.,'minh':1.,'grading':.3})
            if report['imported_faces']!=4918 or report['imported_solids']!=1:
                raise ValueError('native_import_topology_changed')
            native.save(target,report)
            mesh=geo.GenerateMesh(**report['options'])
            mesh.Save(str(args.output/'netgen-private.vol'))
            points=np.array([tuple(p.p) for p in mesh.Points()],dtype=np.float64)
            cells=np.array([[v.nr-1 for v in e.vertices] for e in mesh.Elements3D()],dtype=np.int64)
            faces=np.array([[v.nr-1 for v in e.vertices] for e in mesh.Elements2D()],dtype=np.int64)
            report['surface_region_indices_private']=sorted({e.index for e in mesh.Elements2D()})
        native.save(target,report)
        report['mesh']=audit_output(points,cells,faces,args.output/'result-private.msh')
        if args.engine=='delmesher':
            xyz=p[c]; reference_volume=math.fsum(map(float,np.linalg.det(xyz[:,1:]-xyz[:,[0]])/6))
            report['input_polyhedral_volume']=reference_volume
            report['polyhedral_volume_relative_difference']=abs(report['mesh']['tetra_volume']/reference_volume-1)
            report['mesh']['coarse_checks_passed'] &= report['polyhedral_volume_relative_difference']<=1e-10
        report['status']='completed_diagnostic_only'
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__,error=str(exc))
    finally:
        gmsh.finalize(); report['elapsed_seconds']=time.monotonic()-started
        report['inputs_and_sources_unchanged']=all(native.sha256(p)==s for p,s in pins.items())
        native.save(target,report)
    print(json.dumps(report),flush=True)
    return 0 if report['status']=='completed_diagnostic_only' else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',choices=('delmesher','netgen'),required=True)
    parser.add_argument('--max-vertices',type=int,default=None)
    parser.add_argument('--delmesher-cli',type=Path)
    for name in ('input','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.max_vertices is not None and args.max_vertices<1: parser.error('positive_refinement_cap_required')
    sys.exit(run(args))
