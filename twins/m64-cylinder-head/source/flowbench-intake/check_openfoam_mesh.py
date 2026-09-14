#!/usr/bin/env python3
"""Convert and inspect an exact reviewed head mesh; this program has no solver stage."""
import argparse
import json
from pathlib import Path
import subprocess
import time

import run_openfoam_pilot as pilot


def validate_review(manifest, review):
    if (manifest.get('purpose')!='head_pilot' or
            review.get('schema')!='m64-intake-pilot-review/v1' or
            review.get('approved_for_mesh_diagnostic') is not True or
            review.get('boundary_assignment_accepted') is not True or
            review.get('mesh_sha256')!=manifest.get('mesh_sha256') or
            not pilot.re.fullmatch(r'[a-f0-9]{64}',review.get('native_domain_sha256',''))):
        raise ValueError('independent_exact_mesh_review_for_conversion_only_required')


def commands():
    return [('gmshToFoam',['gmshToFoam','input.msh']),
            ('transformPoints',['transformPoints','scale=(0.001 0.001 0.001)']),
            ('createPatch',['createPatch','-overwrite']),
            ('checkMesh',['checkMesh','-allTopology','-allGeometry'])]


def main(args):
    if not 10<=args.timeout_seconds<=300:raise ValueError('bounded_mesh_stage_timeout_required')
    case=args.case_dir.resolve();receipt=args.review_receipt.resolve()
    manifest_path=case/'case-manifest.json';manifest=json.loads(manifest_path.read_text())
    review=json.loads(receipt.read_text());validate_review(manifest,review)
    output=case/'mesh-diagnostic.json'
    if output.exists() or (case/'constant/polyMesh').exists():raise ValueError('new_unconverted_case_required')
    expected={case/'input.msh':manifest['mesh_sha256'],manifest_path:pilot.sha(manifest_path),
              receipt:pilot.sha(receipt),Path(__file__):pilot.sha(Path(__file__)),
              Path(pilot.__file__):pilot.sha(Path(pilot.__file__))}
    expected.update({case/name:value for name,value in manifest['file_sha256'].items()})
    if any(pilot.sha(path)!=value for path,value in expected.items()):raise ValueError('case_input_changed')
    report={'schema':'m64-openfoam-mesh-diagnostic/v1','status':'running','stages':[],
            'mesh_sha256':manifest['mesh_sha256'],'native_domain_sha256':review['native_domain_sha256'],
            'case_manifest_sha256':expected[manifest_path],'review_sha256':expected[receipt],
            'source_sha256':expected[Path(__file__)],'pilot_helper_sha256':expected[Path(pilot.__file__)],
            'solver_executed':False,'CFD_qualified':False,'manufacturing_authorized':False,
            'meters_per_scan_unit_unverified_hypothesis':.001,'scale_applications':0}
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for name,cmd in commands():
            if name=='checkMesh':
                boundary=case/'constant/polyMesh/boundary'
                geometry=[case/'constant/polyMesh'/n for n in ('points','faces','owner','neighbour')]
                before={p.name:pilot.sha(p) for p in geometry}
                report['boundary_before_wall_type_sha256']=pilot.sha(boundary)
                boundary.write_text(pilot.set_wall_patch_type(boundary.read_text()))
                report['boundary_after_wall_type_sha256']=pilot.sha(boundary)
                report['wall_type_change_geometry_unchanged']=before=={p.name:pilot.sha(p) for p in geometry}
                report['boundary']=pilot.boundary_contract(boundary.read_text())
            started=time.monotonic();log=case/('log.'+name)
            stage={'name':name,'argv':cmd,'exit_code':None,'timed_out':False}
            with log.open('wb') as stream:
                try:
                    stage['exit_code']=subprocess.run(cmd,cwd=case,stdout=stream,stderr=subprocess.STDOUT,
                        timeout=args.timeout_seconds,check=False).returncode
                except subprocess.TimeoutExpired:stage['timed_out']=True
            stage.update(elapsed_seconds=time.monotonic()-started,log_sha256=pilot.sha(log))
            report['stages'].append(stage);save()
            if stage['exit_code']!=0:raise ValueError(name+'_failed_or_timed_out')
            if name=='transformPoints':report['scale_applications']+=1
        report['checkMesh_passed']=pilot.mesh_ok((case/'log.checkMesh').read_text())
        if not report['checkMesh_passed']:raise ValueError('checkMesh_did_not_report_Mesh_OK')
        report['status']='mesh_diagnostic_completed_no_solver'
    except (OSError,ValueError) as exc:
        report['status']='mesh_rejected_or_diagnostic_incomplete';report['error']=str(exc)
    report['all_original_inputs_unchanged']=all(pilot.sha(path)==value for path,value in expected.items())
    if not report['all_original_inputs_unchanged']:report['status']='input_integrity_failed'
    save();print(json.dumps({'status':report['status'],'solver_executed':False}),flush=True)
    return 0 if report['status']=='mesh_diagnostic_completed_no_solver' else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-dir',type=Path,required=True)
    parser.add_argument('--review-receipt',type=Path,required=True)
    parser.add_argument('--timeout-seconds',type=int,default=120)
    raise SystemExit(main(parser.parse_args()))
