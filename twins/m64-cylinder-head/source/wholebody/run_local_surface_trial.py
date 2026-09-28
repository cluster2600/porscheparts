#!/usr/bin/env python3
"""One explicit Gmsh surface-algorithm experiment; reuse frozen volume audits.

A temporary generation hook applies MeshAdapt only to hash-bound poor faces.
The companion receipt is mandatory: the frozen helper alone does not record
this runtime hook. Neither library files nor CAD geometry are modified.
"""
import argparse
import json
from pathlib import Path
import resource
import signal
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mesh_native_ported_head as native

BODY_SHA = 'b2b48fe40edd1a20c8e6c0d20d77e6045931189f18330b441b09bcbf4618fc0a'
HELPER_SHA = '7171d7b1da250d63086b7fac1e5e1617190ec26f45f2928e729d60582a1d1c04'
QUALITY_SHA = '9803fe77186ea2096da80add6e4ba3cca75cd666841cbf311d73e1d3ac86fd52'
BASELINE_SHA = 'b9e3e80e7873540f5ab2ca456f0b9295783d9cd539247098b8d7308df26c1dd5'


def assignments(quality, binding):
    rows = quality['surface_quality_by_source_face_private']
    if (len(rows)!=4918 or {r['source_face_index'] for r in rows}!=set(range(1,4919))
            or binding.get('descriptor_bijection_verified') is not True):
        raise ValueError('complete_bound_faces_and_bijection_required')
    selected = {r['source_face_index'] for r in rows if r['minSICN_below_0p1']>0}
    if len(selected)!=155:raise ValueError('exact_poor_face_selection_required')
    mapping = binding['matches_private']
    result = [dict(source_face_index=r['source_face_index'],gmsh_face_tag=r['gmsh_face_tag'],algorithm=1)
              for r in mapping if r['source_face_index'] in selected]
    if (len(result)!=155 or {r['source_face_index'] for r in result}!=selected
            or len({r['gmsh_face_tag'] for r in result})!=155):
        raise ValueError('selected_faces_not_bijective')
    return sorted(result,key=lambda r:r['source_face_index'])


def main(args):
    import gmsh
    pins={args.input:BODY_SHA,args.baseline:BASELINE_SHA,args.quality:QUALITY_SHA,
          Path(native.__file__):HELPER_SHA,Path(__file__):native.sha256(__file__)}
    def unchanged():return all(not p.is_symlink() and native.sha256(p)==h for p,h in pins.items())
    if args.output.exists() or not unchanged() or gmsh.__version__!='4.15.2':
        raise ValueError('fresh_output_and_exact_inputs_runtime_required')
    baseline=json.loads(args.baseline.read_text());quality=json.loads(args.quality.read_text())
    if baseline['native_BRep_sha256']!=BODY_SHA or baseline['source_unchanged'] is not True:
        raise ValueError('native_baseline_binding_failed')
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    receipt={'schema':'m64-local-surface-trial/v1','status':'incomplete',
             'source_sha256':pins[Path(__file__)], 'helper_sha256':HELPER_SHA,
             'input_sha256':BODY_SHA,'baseline_sha256':BASELINE_SHA,'quality_sha256':QUALITY_SHA,
             'temporary_generation_hook':True,'installed_library_files_modified':False,
             'selection':'all_155_CAD_faces_with_surface_triangles_below_minSICN_0.1_in_bound_receipt',
             'default_surface_algorithm':6,'selected_surface_algorithm':1,
             'geometry_modified':False,'manufacturing_authorized':False,'calls':[]}
    target=args.output/'trial-receipt.json';native.save(target,receipt)
    generate=gmsh.model.mesh.generate
    def selected_generate(dimension=3):
        receipt['calls'].append(dimension)
        if dimension==2:
            if 'assignments_private' in receipt:raise ValueError('surface_hook_called_twice')
            descriptors=[{'tag':tag,'area':gmsh.model.occ.getMass(2,tag),
                          'centre':list(gmsh.model.occ.getCenterOfMass(2,tag))} for _,tag in gmsh.model.getEntities(2)]
            binding=native.match_faces(baseline['face_descriptors_private'],descriptors)
            chosen=assignments(quality,binding)
            for row in chosen:gmsh.model.mesh.setAlgorithm(2,row['gmsh_face_tag'],1)
            receipt['assignments_private']=chosen
            native.save(target,receipt)
        return generate(dimension)
    ns=argparse.Namespace(input=args.input,sha256=BODY_SHA,baseline=args.baseline,output=args.output/'mesh',
        minimum=1.,maximum=6.,optimizer='netgen',volume_algorithm=1,maximum_tetrahedra=1500000,
        preserved_skin_meshadapt_evidence=None)
    ns.output.mkdir(mode=0o700)
    gmsh.model.mesh.generate=selected_generate
    result=2
    try:
        result=native.mesh(ns)
        receipt['helper_report_sha256']=native.sha256(ns.output/'mesh-report.json')
        receipt['helper_verdict']=json.loads((ns.output/'mesh-report.json').read_text())['status']
        receipt['hook_complete']=receipt['calls']==[1,2,3] and len(receipt.get('assignments_private',[]))==155
        receipt['status']='completed' if receipt['hook_complete'] else 'failed_hook'
    except Exception as error:
        receipt.update(status='failed',error_type=type(error).__name__)
    finally:
        gmsh.model.mesh.generate=generate
        receipt['inputs_and_sources_unchanged']=unchanged()
        if not receipt['inputs_and_sources_unchanged']:receipt['status']='failed_input_changed'
        native.save(target,receipt)
    return result if receipt['status']=='completed' else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('input','baseline','quality','output'):parser.add_argument('--'+name,type=Path,required=True)
    resource.setrlimit(resource.RLIMIT_CPU,(270,275));signal.alarm(360)
    raise SystemExit(main(parser.parse_args()))
