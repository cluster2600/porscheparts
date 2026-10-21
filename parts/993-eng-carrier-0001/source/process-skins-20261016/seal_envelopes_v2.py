"""Seal a mixed seven-region store from historical and positive-prism proofs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np
from admitted_regions_v2 import EnvelopeStore
from native_prism_case import load_case,_evidence_path

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def case_records(path,inputs,inputs_sha256):
    path=Path(path).resolve()
    if path.is_file():return json.loads(path.read_text()),{},[path]
    if not path.is_dir():raise ValueError('Native case records are missing')
    prisms={};legacy={};receipts=[]
    for row in inputs['regions']:
        source=row['source_index'];record=path/f'source-{source:03d}/case.json'
        data=json.loads(record.read_text());receipts.append(record)
        if (data.get('schema')!='native-envelope-case-v2' or data.get('status')!='executed' or
            data.get('source_index')!=source or data.get('input_manifest_sha256')!=inputs_sha256):
            raise ValueError('Native case was rejected or belongs to another prepared input')
        if not isinstance(data.get('files_sha256'),dict) or not data['files_sha256']:
            raise ValueError('Native terminal case has no bound payload')
        def terminal_path(name):
            if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Native terminal paths must stay inside their case')
            return _evidence_path(name,record)
        for name,digest in data['files_sha256'].items():
            if sha(terminal_path(name))!=digest:raise ValueError('Native terminal case output changed')
        if data['backend']=='cgal-positive-roof-prisms-v4':
            if source not in (0,2):raise ValueError('Native backend differs from the declared source profile')
            reference=data['native_audit'];audit=terminal_path(reference['path'])
            if (data['files_sha256'].get(reference['path'])!=reference['sha256'] or
                    sha(audit)!=reference['sha256']):raise ValueError('Native prism terminal audit identity differs')
            prisms[str(source)]=str(audit)
        elif data['backend']=='pymesh-csgtree-explicit-order':
            if source in (0,2):raise ValueError('Native backend differs from the declared source profile')
            directory=terminal_path(data['legacy_case_directory']['path'])
            if not directory.is_dir():raise ValueError('Historical case output directory is missing')
            legacy[source]=directory
        else:raise ValueError('Unknown native case backend')
    return prisms,legacy,receipts


def seal(inputs_path,cases_path,prism_cases_path,output):
    inputs_path=Path(inputs_path).resolve();cases_path=Path(cases_path).resolve();output=Path(output).resolve()
    inputs_identity=sha(inputs_path);inputs=json.loads(inputs_path.read_text());base=inputs_path.parent
    prism_cases_path=Path(prism_cases_path).resolve()
    prism_cases,legacy_directories,terminal_receipts=case_records(prism_cases_path,inputs,sha(inputs_path))
    terminal_identities={p:sha(p) for p in terminal_receipts}
    expected_sources={row['source_index'] for row in inputs['regions']}
    if not {int(k) for k in prism_cases}.issubset(expected_sources):raise ValueError('Unknown native prism region')
    if not inputs.get('sources_and_input_unchanged') or len(inputs['regions'])!=inputs['expected_regions']:
        raise ValueError('Prism input preparation is incomplete')
    output.mkdir(parents=True,exist_ok=False);files={}
    def copy(path,name):
        path=Path(path);destination=output/name
        if destination.exists():raise ValueError('Store payload filenames must be unique')
        shutil.copy2(path,destination);files[name]=sha(destination)
        return dict(receipt=name,receipt_sha256=files[name])
    def write(value,name):
        path=output/name
        if path.exists():raise ValueError('Store receipt filename collision')
        path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');files[name]=sha(path)
        return dict(receipt=name,receipt_sha256=files[name])
    copy(inputs_path,'prism-inputs.json')
    copy(Path(__file__).resolve(),'seal_envelopes_v2.py')
    for number,path in enumerate(terminal_receipts):copy(path,f'native-terminal-input-{number:03d}.json')
    write(dict(prism_cases=prism_cases,legacy_case_directories={str(k):str(v) for k,v in legacy_directories.items()},
        terminal_receipts_sha256={str(p):sha(p) for p in terminal_receipts}),'prism-case-inputs.json')
    for name in sorted({inputs['part'],*[r[k] for r in inputs['regions'] for k in ['chain','mask','roofs'] if k in r]}):
        expected=inputs['part_sha256'] if name==inputs['part'] else next(r[k+'_sha256'] for r in inputs['regions'] for k in ['chain','mask','roofs'] if k in r and r[k]==name)
        if sha(base/name)!=expected:raise ValueError('Prepared native CSG input changed')
        copy(base/name,'input-'+name)
    with np.load(base/inputs['part'],allow_pickle=False) as part:
        geometry_sha=hashlib.sha256(np.asarray(part['vertices'],dtype=np.float64).tobytes()+np.asarray(part['faces'],dtype=np.int64).tobytes()).hexdigest()
    regions=[];bounds=[]
    for row in inputs['regions']:
        index=row['index'];case=legacy_directories.get(row['source_index'],cases_path/f"source-{row['source_index']:03d}")
        prefix=f'region-{index:03d}-'
        if str(row['source_index']) in prism_cases:
            audit_path=Path(prism_cases[str(row['source_index'])]).resolve()
            native_case=load_case(audit_path);native_case.verify()
            native=json.loads(audit_path.read_text())
            evidence=json.loads(audit_path.with_name('local-evidence-map.json').read_text())
            if (native_case.source_index!=row['source_index'] or
                native_case.boolean_audit['input_sha256']!=[row['roofs_sha256'],row['mask_sha256'],inputs['part_sha256']]):
                raise ValueError('Prism case inputs differ from the frozen prepared leaves')
            mapped={}
            for number,(origin,item) in enumerate(sorted(evidence['files'].items())):
                evidence_path=_evidence_path(item['path'],audit_path.with_name('local-evidence-map.json'))
                ref=copy(evidence_path,prefix+f'prism-proof-{number:03d}-'+evidence_path.name)
                if ref['receipt_sha256']!=item['sha256']:raise ValueError('Prism evidence changed while packaging')
                mapped[origin]=dict(path=ref['receipt'],sha256=ref['receipt_sha256'])
            audit_ref=copy(audit_path,prefix+'prism-native-audit.json')
            map_ref=write(dict(native_audit_sha256=audit_ref['receipt_sha256'],all_references_copied=True,files=mapped),prefix+'prism-evidence-map.json')
            envelope=Path(mapped[native['final_npz']['path']]['path']).name
            regions.append(dict(row,envelope=envelope,status='passed',backend='positive_prism_native_v2',
                prism_native_audit=audit_ref,prism_evidence_map=map_ref,
                all_vertical_intervals_retained=True,body_subtracted_in_same_coordinates=True))
            bounds.append(dict(region=index,finite_sample_limit_mm=native['frozen_bound_mm'],
                maximum_composed_finite_sample_bound_mm=native['maximum_composed_bound_mm_approx'],
                scope='Exact radical bound on both finite vertex/barycentre sample sets; no continuous Hausdorff bound is claimed.'))
            native_case.verify()
            continue
        read=lambda name:json.loads((case/name).read_text())
        csg=read('csg/receipt.json');execution=read('csg/execution-receipt.json')
        raw_sha=sha(case/'csg/result.npz');final_sha=sha(case/'snap/result.npz')
        if (csg.get('status')!='executed' or execution.get('status')!='executed' or execution.get('returncode')!=0 or
                not execution.get('sources_and_inputs_unchanged') or not execution.get('owned_scope_inactive') or
                csg['result_sha256']!=raw_sha or csg['input_sha256']!=dict(chain=row['chain_sha256'],mask=row['mask_sha256'],part=inputs['part_sha256']) or
                csg.get('intermediate_double_exports')!=0):
            raise ValueError('Native CSG execution is missing, changed or belongs to different inputs')
        snap=read('snap/audit.json');distance=read('distance/audit.json');independent=read('independent/assessment.json')
        if snap['input_sha256']!=raw_sha or snap['result_sha256']!=final_sha:
            raise ValueError('Snap geometry is not bound to the actual CSG result')
        if (distance['input_sha256']!=raw_sha or distance['result_sha256']!=final_sha or not distance.get('pass') or
                independent.get('status')!='passed' or independent['input_sha256']!=final_sha):
            raise ValueError('Exact distance/topology/contact proofs are missing or rejected')
        references={}
        paths={'csg_receipt':'csg/receipt.json','csg_execution':'csg/execution-receipt.json',
            'native_execution':'snap/execution-receipt.json','native_audit':'snap/audit.json','native_geometry':'snap/native.json',
            'exact_distance_execution':'distance/execution-receipt.json','exact_distance_audit':'distance/audit.json',
            'topology':'independent/topology/assessment.json','exact_contacts':'independent/exact-contacts.json'}
        for key,name in paths.items():references[key]=copy(case/name,prefix+key+'.json')
        copy(case/'independent/topology/pairs.npz',prefix+'detector-pairs.npz')
        copy(case/'csg/result.npz',prefix+'csg-result.npz')
        if 'clip_bbox' in csg:
            bbox=case/'csg/clip-bbox.npz'
            if not csg['clip_bbox'].get('all_chain_vertices_strictly_inside') or sha(bbox)!=csg['clip_bbox']['bbox_npz_sha256']:
                raise ValueError('The exact local cutter lacks its enclosing-box proof')
            copy(bbox,prefix+'clip-bbox.npz')
        copy(case/'distance/exact-distance.json',prefix+'exact-distance-native.json')
        # Retain the original execution plans, workers and installation identities
        # when available; every retained payload is covered by the store seal.
        for stage in ['csg','snap','distance']:
            for name in ['execution-plan.json','installation-receipt.json','runner.py','worker.py']:
                path=case/stage/name
                if path.is_file():copy(path,prefix+stage+'-'+name)
        envelope=f'envelope-{index:03d}.npz';copy(case/'snap/result.npz',envelope)
        steps=snap['native']['grid_step_mm'];bound=5*math.sqrt(sum(s*s for s in steps))/2
        measurement=distance['exact_distance'];measured=max(measurement[k]['maximum_mm'] for k in ['input_to_output','output_to_input'])
        repair=write(dict(status='passed',final_mesh_sha256=final_sha,
            parameters=dict(snap_grid_size=51,number_of_iterations=5),snap_step_mm_xyz=steps,
            cumulative_displacement_bound_mm=bound,returned_intersection_free=True,
            measured_bidirectional_deviation_max_mm=measured,
            **{key:references[key] for key in ['native_execution','native_audit','native_geometry','exact_distance_execution','exact_distance_audit']}),prefix+'repair.json')
        native=write(dict(status='passed',final_mesh_sha256=final_sha,topology=references['topology'],
            exact_contacts=references['exact_contacts'],repair=repair,
            csg_execution=references['csg_execution'],csg_receipt=references['csg_receipt']),prefix+'native-audit.json')
        bounds.append(dict(region=index,cumulative_rounding_budget_mm=bound,measured_bidirectional_upper_bound_mm=measured))
        regions.append(dict(row,envelope=envelope,status='passed',native_audit=native,
            all_vertical_intervals_retained=True,body_subtracted_in_same_coordinates=True))
    report=dict(schema='carrier-exact-free-envelopes-v2',status='passed',input_sha256=inputs['input_sha256'],
        parameters=inputs['parameters'],part_geometry_sha256=geometry_sha,edge_gap_mm=inputs['edge_gap_mm'],
        minimum_projected_area_mm2=inputs['minimum_projected_area_mm2'],expected_regions=inputs['expected_regions'],
        algorithm='sealed_historical_CSGTree_and_verified_positive_prism_native_cases_with_explicit_parent_maps',
        coordinate_error_bounds=bounds,files_sha256=files,regions=regions,
        configured_area_exclusions=inputs['configured_area_exclusions'])
    (output/'envelopes.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    # Use the same strict reader as the final build before declaring this seal.
    EnvelopeStore(output,inputs['input_sha256'],inputs['parameters']).verify()
    if sha(inputs_path)!=inputs_identity or any(sha(p)!=digest for p,digest in terminal_identities.items()):
        raise ValueError('Native case terminal or input preparation changed during sealing')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','cases','prism_cases','output']:parser.add_argument(name,type=Path)
    args=parser.parse_args();report=seal(args.inputs,args.cases,args.prism_cases,args.output)
    print(json.dumps(dict(status=report['status'],regions=report['expected_regions'])))
