#!/usr/bin/env python3
"""Bounded native-CAD surface-meshing trials; no BRep edits or relaxed gates.

Reuses the frozen full-body mesh auditor. The mandatory companion records
every temporary API hook, local size override and surface-node CAD check.
"""
import argparse
import json
import math
from pathlib import Path
import resource
import signal

import run_local_surface_trial as previous

native=previous.native
RESIDUAL_SHA='3174c8df6b091821d0c7b097cd6309a796294bcbead456d37f72475ef684b27d'


def source_selection(original,residual):
    def poor(document,count):
        rows=document['surface_quality_by_source_face_private']
        if len(rows)!=4918 or {r['source_face_index'] for r in rows}!=set(range(1,4919)):
            raise ValueError('complete_native_face_index_required')
        result={r['source_face_index'] for r in rows if r['minSICN_below_0p1']>0}
        if len(result)!=count: raise ValueError('bound_poor_face_count_changed')
        return result
    initial=poor(original,155); remaining=poor(residual,30)
    if len(initial|remaining)!=159: raise ValueError('bound_face_union_changed')
    return initial|remaining,remaining


def run(args):
    import gmsh
    pins={args.input:previous.BODY_SHA,args.baseline:previous.BASELINE_SHA,
          args.quality:previous.QUALITY_SHA,args.residual:RESIDUAL_SHA,
          Path(native.__file__):previous.HELPER_SHA,
          Path(previous.__file__):'1ef987d833125281899776542ef99f4701d3f958552dde59883456db0aabe488',
          Path(__file__):native.sha256(__file__)}
    def unchanged(): return all(not p.is_symlink() and native.sha256(p)==h for p,h in pins.items())
    if args.output.exists() or not unchanged() or gmsh.__version__!='4.15.2':
        raise ValueError('fresh_output_exact_inputs_and_Gmsh_required')
    baseline=json.loads(args.baseline.read_text())
    selected,remaining=source_selection(json.loads(args.quality.read_text()),json.loads(args.residual.read_text()))
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    receipt={'schema':'m64-CAD-constrained-surface-trial/v1','status':'incomplete',
             'source_sha256':pins[Path(__file__)],'helper_sha256':previous.HELPER_SHA,
             'native_BRep_sha256':previous.BODY_SHA,'residual_sha256':RESIDUAL_SHA,
             'source_faces_MeshAdapt':sorted(selected),'residual_source_faces':sorted(remaining),
             'local_size':args.local_size,'relocate2D':args.relocate,'calls':[],
             'geometry_modified':False,'manufacturing_authorized':False,
             'installed_library_files_modified':False,'temporary_API_hooks':True}
    target=args.output/'trial-receipt.json'; native.save(target,receipt)
    generate=gmsh.model.mesh.generate; optimize=gmsh.model.mesh.optimize
    groups={}
    def generated(dimension=3):
        receipt['calls'].append(dimension)
        if dimension==1:
            descriptors=[{'tag':tag,'area':gmsh.model.occ.getMass(2,tag),
                          'centre':list(gmsh.model.occ.getCenterOfMass(2,tag))} for _,tag in gmsh.model.getEntities(2)]
            binding=native.match_faces(baseline['face_descriptors_private'],descriptors)
            if not binding['descriptor_bijection_verified']: raise ValueError('native_face_bijection_failed')
            tags={r['source_face_index']:r['gmsh_face_tag'] for r in binding['matches_private']}
            chosen=[(2,tags[i]) for i in sorted(selected)]; groups['selected']=chosen
            residual=[(2,tags[i]) for i in sorted(remaining)]
            curves=sorted({(1,abs(t)) for d,t in gmsh.model.getBoundary(residual,combined=False,oriented=False) if d==1})
            vertices=sorted({(0,abs(t)) for d,t in gmsh.model.getBoundary(curves,combined=False,oriented=False) if d==0})
            local=set(residual+curves+vertices)
            for _,tag in chosen: gmsh.model.mesh.setAlgorithm(2,tag,1)
            receipt['local_entity_counts']={str(d):sum(pair[0]==d for pair in local) for d in (0,1,2)}
            receipt['source_to_gmsh_private']={str(i):tags[i] for i in sorted(selected)}
            if args.local_size:
                gmsh.option.setNumber('Mesh.MeshSizeMin',args.local_size)
                def sizing(dim,tag,x,y,z,lc):
                    if not math.isfinite(lc) or lc<=0: raise ValueError('invalid_mesh_size_callback')
                    # Keep the previous floor outside the residual entities.
                    return args.local_size if (dim,tag) in local else max(1.,lc)
                gmsh.model.mesh.setSizeCallback(sizing)
                receipt['size_callback']='fixed_local_size_on_30_faces_and_their_edges_vertices; original_floor_1_elsewhere'
            native.save(target,receipt)
        result=generate(dimension)
        if dimension==2:
            def surface_quality():
                types,tags,_=gmsh.model.mesh.getElements(2)
                if list(map(int,types))!=[2]: raise ValueError('linear_triangles_required')
                q=list(map(float,gmsh.model.mesh.getElementQualities(tags[0],'minSICN')))
                return {'triangles':len(q),'minimum_minSICN':min(q),'below_0p1':sum(v<.1 for v in q)}
            receipt['surface_before_relocation']=surface_quality()
            if args.relocate: optimize('Relocate2D',force=False,niter=5,dimTags=groups['selected'])
            receipt['surface_after_relocation']=surface_quality()
            maximum=0.; count=0
            for _,tag in groups['selected']:
                nt,coords,uv=gmsh.model.mesh.getNodes(2,tag,includeBoundary=False,returnParametricCoord=True)
                if not len(nt): continue
                if len(uv)!=2*len(nt): raise ValueError('surface_node_parameters_missing')
                actual=gmsh.model.getValue(2,tag,uv)
                for k in range(len(nt)):
                    maximum=max(maximum,math.dist(coords[3*k:3*k+3],actual[3*k:3*k+3]))
                count+=len(nt)
            receipt['surface_parametric_node_check']={'nodes':count,'maximum_distance':maximum,
                'tolerance':1e-6,'passed':count>0 and math.isfinite(maximum) and maximum<=1e-6,
                'not_a_continuous_surface_deviation_bound':True}
            native.save(target,receipt)
            if not receipt['surface_parametric_node_check']['passed']: raise ValueError('surface_node_CAD_check_failed')
        return result
    ns=argparse.Namespace(input=args.input,sha256=previous.BODY_SHA,baseline=args.baseline,output=args.output/'mesh',
        minimum=1.,maximum=6.,optimizer='netgen',volume_algorithm=1,maximum_tetrahedra=1500000,
        preserved_skin_meshadapt_evidence=None)
    ns.output.mkdir(mode=0o700)
    gmsh.model.mesh.generate=generated
    result=2
    try:
        result=native.mesh(ns)
        helper=json.loads((ns.output/'mesh-report.json').read_text())
        receipt.update(helper_report_sha256=native.sha256(ns.output/'mesh-report.json'),helper_status=helper['status'],
            hook_complete=receipt['calls']==[1,2,3] and receipt.get('surface_parametric_node_check',{}).get('passed') is True)
        receipt['status']='completed' if receipt['hook_complete'] and helper['status']!='failed' else 'failed'
    finally:
        gmsh.model.mesh.generate=generate
        receipt['inputs_and_sources_unchanged']=unchanged()
        if not receipt['inputs_and_sources_unchanged']: receipt['status']='failed_input_changed'
        native.save(target,receipt)
    return result if receipt['status']=='completed' else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('input','baseline','quality','residual','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--local-size',type=float,choices=(0.,.5,.25),default=0.)
    parser.add_argument('--relocate',action='store_true')
    resource.setrlimit(resource.RLIMIT_CPU,(540,550)); signal.alarm(600)
    raise SystemExit(run(parser.parse_args()))
