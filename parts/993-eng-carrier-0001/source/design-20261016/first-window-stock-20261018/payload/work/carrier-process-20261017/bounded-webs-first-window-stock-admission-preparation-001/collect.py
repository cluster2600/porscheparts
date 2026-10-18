"""Read-only closure of the one owned saved-stock local admission."""
import copy
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import time
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[2]
GO = '9f09027936527b98949868b36c75a290e9f90ba2a69771365f5d4785817a139b'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''): digest.update(block)
    return digest.hexdigest()

def read(path): return json.loads(path.read_bytes())

def encoded(value): return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()

def rel(path): return str(path.relative_to(R))

def inverses():
    pp, pl, pc = (H / n for n in ('pending-plan.json', 'pending-launch-plan.json', 'pending-command.json'))
    ap, al, ac = (H / n for n in ('plan.json', 'launch-plan.json', 'command.json'))
    p, launch, command = read(ap), read(al), read(ac)
    go_name = rel(H / 'root-GO-001.json')
    assert sha(R / go_name) == p['root_GO_sha256'] == launch['root_GO_sha256'] == command['root_GO_sha256'] == GO
    assert p['root_GO'] == launch['root_GO'] == command['root_GO'] == go_name
    assert p['launch_ready'] is launch['launch_ready'] is command['launch_ready'] is True
    back = copy.deepcopy(p); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None); del back['files_sha256'][go_name]
    assert back == read(pp) and encoded(back) == pp.read_bytes()
    back = copy.deepcopy(launch); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None)
    back['command'][5:7] = [str(pp), sha(pp)]; del back['inputs_sha256'][go_name]
    back['inputs_sha256'] = {rel(pp) if key == rel(ap) else key: sha(pp) if key == rel(ap) else value for key, value in back['inputs_sha256'].items()}
    assert back == read(pl) and encoded(back) == pl.read_bytes()
    back = copy.deepcopy(command); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None)
    back['argv'][4], back['argv'][6] = str(pl), sha(pl)
    assert back == read(pc) and encoded(back) == pc.read_bytes()
    assert launch['command'][5:7] == [str(ap), sha(ap)] and command['argv'][4] == str(al) and command['argv'][6] == sha(al)
    return p, launch, command

def absent(flag, pid):
    result = subprocess.run(['/bin/ps', flag, str(pid), '-o', 'pid=,ppid=,pgid=,stat='], capture_output=True, text=True, timeout=2)
    assert result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip()
    return True

def whole_outputs(output, execution):
    rows = {}
    for directory in (output, execution):
        for path in sorted(directory.rglob('*')):
            assert not path.is_symlink()
            if not path.is_file(): continue
            before = path.stat(); digest = sha(path); after = path.stat()
            assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            rows[rel(path)] = dict(sha256=digest, bytes=after.st_size)
    return rows

def collect():
    began=time.monotonic();p,launch,command=inverses();tool=read(H/'actual-tool-terminal.json')
    assert tool['session_id']==13305 and tool['initial_chunk']=='a3543a' and type(tool['actual_tool_returncode'])is int
    output,execution=R/p['output_directory'],R/p['execution_directory'];supervision=read(execution/'execution-receipt.json');started=read(execution/'started.json')
    pins={**launch['source_sha256'],**launch['inputs_sha256']}
    assert {name:sha(R/name)for name in pins}==pins==supervision['sources_before']==supervision['sources_after']
    assert supervision['sources_and_plan_unchanged'] and supervision['plan_sha256']==started['plan_sha256']==sha(H/'launch-plan.json')
    assert supervision['command']==launch['command'] and supervision['cwd']==command['cwd']==str(R)
    assert supervision['pid']==started['pid']==started['pgid']==11235
    assert supervision['direct_child_reaped'] and supervision['no_non_zombie_group_members'] and supervision['final_group_members']==[] and supervision['cleanup_error']is None
    assert absent('-p',11235) and absent('-g',11235)
    assert tool['actual_tool_returncode']==(0 if supervision['status']=='executed'else 1)
    for name,digest in supervision['logs_sha256'].items():assert sha(execution/name)==digest
    assessment_path=output/'assessment.json';assessment=read(assessment_path)if assessment_path.exists()else None
    events=[json.loads(line)for line in (output/'events.jsonl').read_text().splitlines()]if(output/'events.jsonl').exists()else[]
    assert [r['seconds']for r in events]==sorted(r['seconds']for r in events)
    spec=importlib.util.spec_from_file_location('_stock_local_collector_stdlib',H/'admit.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=module.RECORDS.closed_stock();summary={}
    if assessment is not None:
        assert assessment['schema']=='first-window-stock-native-local-admission-1' and assessment['candidate_version']=='first-window-stock-alone-v1'
        assert assessment['candidate_BREP_sha256']==p['candidate_BREP_sha256']==module.RECORDS.BREP_SHA
        assert assessment['sources_before']==assessment['sources_after']==p['files_sha256'] and assessment['sources_unchanged']
        assert assessment['candidate_qualified']is assessment['failed_union_used']is assessment['current07b_subset_required']is assessment['old_complete7_law_inherited']is assessment['FEA_executed']is False
        assert assessment['failed_union_preserved']is True and assessment['downstream_checks']=={key:'PENDING'for key in module.GATE.PENDING}
        printed=[]
        for line in(execution/'stdout.log').read_text().splitlines():
            try:row=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(row,dict)and row.get('assessment_sha256')==sha(assessment_path):printed.append(row)
        assert len(printed)==1 and printed[0]['status']==assessment['status']
        if 'whole_candidate'in assessment:assert read(output/'candidate-native-summary.json')==assessment['whole_candidate']
        observation=assessment.get('volume_observation')
        if observation is not None:
            assert read(output/'native-volume-overloads.json')==observation
            assert observation['candidate_BREP_sha256']==p['candidate_BREP_sha256'] and observation['Gmsh_getMass_mm3']is None
            assert observation['operator_source_sha256']==p['files_sha256'][p['volume_observer_source']]
            rows=observation['methods'];assert len(rows)==3
            assert [r['method']for r in rows]==['Gmsh_boolean_F_F_F','boolean_OnlyClosed_T_F_F','adaptive_1e-10_T_F']
            assert [r['arguments']for r in rows]==[[False,False,False],[True,False,False],[1e-10,True,False]]
            assert rows[0]['returned_error_estimate']is rows[1]['returned_error_estimate']is None
            assert all(math.isfinite(r['signed_mass_mm3'])and r['signed_mass_mm3']>0 and r['signed_mass_mm3'].hex()==r['mass_binary64_hex']for r in rows)
            assert type(rows[2]['returned_error_estimate'])is float and math.isfinite(rows[2]['returned_error_estimate'])
        measured=assessment.get('measurements')
        if measured is not None:
            assert read(output/'local-measurements-before-gates.json')==measured
            study=read(R/p['study']);assert study['material']['density_tonne_mm3']==4.42e-9
            assert measured['mass_kg']==measured['native_adaptive_volume_mm3']*study['material']['density_tonne_mm3']*1000
            assert measured['native_adaptive_volume_mm3']==observation['methods'][2]['signed_mass_mm3']
            assert measured['native_FFF_volume_mm3']==observation['methods'][0]['signed_mass_mm3']
            assert measured['construction_reference_mm3']==source['original_native_construction']['volume_mm3']
            assert measured['relative_reread_difference']==measured['native_adaptive_volume_mm3']/measured['construction_reference_mm3']-1 and measured['existing_readback_relative_limit']==1e-8
        cuts=assessment.get('native_Cut_summaries',{})
        for name,row in assessment.get('raw_Cut_preservation',{}).items():
            assert read(output/(name+'-raw-preservation.json'))==row
            if row['path']is None:assert row['sha256']is None and row['reason']=='completed_native_Cut_returned_a_null_shape'
            else:assert row['reason']is None and sha(output/row['path'])==row['sha256']
        for name,row in cuts.items():assert read(output/(name+'.json'))==row
        if supervision['actual_returncode']==0:
            assert supervision['status']=='executed' and not supervision['timeout'] and not supervision['interrupted'] and supervision['failure']is None
            assert assessment['status']=='saved_first_window_stock_local_gates_complete_downstream_PENDING' and 'failure'not in assessment
            assert list(cuts)==['baseline-minus-stock','stock-minus-baseline']
            module.strict_empty(cuts['baseline-minus-stock']);added=cuts['stock-minus-baseline']
            assert not added['native_topologically_empty'] and added['native_valid'] and added['material_solid_volume_mm3']>0 and all(r['native_valid']and r['volume_mm3']>0 for r in added['solids'])
            assert assessment['whole_candidate']['native_valid']and assessment['whole_candidate']['counts']['solids']==1
            assert observation['same_Solid_native_identity']and observation['one_reloaded_valid_native_Solid']and measured['same_Solid_native_identity']and measured['native_valid_after_volume']
            assert abs(measured['relative_reread_difference'])<1e-8
            module.GATE.local_gate_flags(cuts['baseline-minus-stock'],True,1,measured['mass_kg'],measured['bounds_mm'],p)
        summary=dict(status=assessment['status'],whole_candidate=assessment.get('whole_candidate'),same_Solid_volume_observation=observation,measurements=measured,native_Cut_summaries=cuts,raw_Cut_preservation=assessment.get('raw_Cut_preservation',{}),failure=assessment.get('failure'))
    outputs=whole_outputs(output,execution)
    return dict(schema='owned-first-window-stock-local-terminal-1',status='closed_actual_RC0_saved_stock_local_geometry_only'if supervision['actual_returncode']==0 else'closed_actual_stock_local_refusal_preserved',
        actual_tool=tool,actual_child_returncode=supervision['actual_returncode'],direct_child_reaped=True,owned_group_empty=True,fresh_PID_and_PGID_absent=True,pid=11235,pgid=11235,
        root_GO_sha256=GO,assessment_sha256=sha(assessment_path)if assessment_path.exists()else None,supervision_sha256=sha(execution/'execution-receipt.json'),
        all_pins_before_after_current_equal=True,merged_pins=len(pins),three_whole_object_and_stored_byte_inverses=True,all_outputs=outputs,output_count=len(outputs),total_output_bytes=sum(row['bytes']for row in outputs.values()),
        candidate_version='first-window-stock-alone-v1',candidate_BREP_sha256=p['candidate_BREP_sha256'],source_construction_ROOT_sha256=module.RECORDS.ROOT_SHA,actual_source_window_ledgers=source['actual_window_branch_ledgers'],
        native=summary,timeout=supervision['timeout'],signals=supervision['signals_to_owned_group_only'],cleanup_error=supervision['cleanup_error'],supervised_elapsed_seconds=supervision['elapsed_seconds'],
        candidate_qualified=False,current07b_subset_required=False,old_complete7_law_inherited=False,failed_union_repaired=False,no_downstream_science=True,collection_elapsed_seconds=time.monotonic()-began)

if __name__=='__main__':
    result=collect();target=H/'terminal-collection.json'
    with target.open('xb')as stream:stream.write(encoded(result));stream.flush();os.fsync(stream.fileno())
    print(json.dumps(dict(status=result['status'],actual_child_returncode=result['actual_child_returncode'],terminal_sha256=sha(target),assessment_sha256=result['assessment_sha256'],outputs=result['output_count'],merged_pins=result['merged_pins'],measurements=result['native'].get('measurements'),failure=result['native'].get('failure'))))

