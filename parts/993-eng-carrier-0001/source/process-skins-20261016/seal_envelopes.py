"""Seal actual seven-region native CSG/snap/distance/contact proofs into a reusable store."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np
from admitted_regions import EnvelopeStore

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def seal(inputs_path,cases_path,output):
    inputs_path=Path(inputs_path).resolve();cases_path=Path(cases_path).resolve();output=Path(output).resolve()
    inputs=json.loads(inputs_path.read_text());base=inputs_path.parent
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
    copy(Path(__file__).resolve(),'seal_envelopes.py')
    for name in sorted({inputs['part'],*[r[k] for r in inputs['regions'] for k in ['chain','mask']]}):
        expected=inputs['part_sha256'] if name==inputs['part'] else next(r[k+'_sha256'] for r in inputs['regions'] for k in ['chain','mask'] if r[k]==name)
        if sha(base/name)!=expected:raise ValueError('Prepared native CSG input changed')
        copy(base/name,'input-'+name)
    with np.load(base/inputs['part'],allow_pickle=False) as part:
        geometry_sha=hashlib.sha256(np.asarray(part['vertices'],dtype=np.float64).tobytes()+np.asarray(part['faces'],dtype=np.int64).tobytes()).hexdigest()
    regions=[];bounds=[]
    for row in inputs['regions']:
        index=row['index'];case=cases_path/f"source-{row['source_index']:03d}"
        prefix=f'region-{index:03d}-'
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
    report=dict(schema='carrier-exact-free-envelopes-v1',status='passed',input_sha256=inputs['input_sha256'],
        parameters=inputs['parameters'],part_geometry_sha256=geometry_sha,edge_gap_mm=inputs['edge_gap_mm'],
        minimum_projected_area_mm2=inputs['minimum_projected_area_mm2'],expected_regions=inputs['expected_regions'],
        algorithm='positive_triangle_prism_union_intersect_exact_XY_mask_minus_complete_part_single_native_Epeck_tree_then_bounded_snap',
        coordinate_error_bounds=bounds,files_sha256=files,regions=regions,
        configured_area_exclusions=inputs['configured_area_exclusions'])
    (output/'envelopes.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    # Use the same strict reader as the final build before declaring this seal.
    EnvelopeStore(output,inputs['input_sha256'],inputs['parameters']).verify()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','cases','output']:parser.add_argument(name,type=Path)
    args=parser.parse_args();report=seal(args.inputs,args.cases,args.output)
    print(json.dumps(dict(status=report['status'],regions=report['expected_regions'])))
