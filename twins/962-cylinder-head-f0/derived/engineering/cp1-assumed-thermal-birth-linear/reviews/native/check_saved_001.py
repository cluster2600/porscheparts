"""Stdlib stopped-file/history association check; never import/run the energy assessor."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import struct

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
E='work/962-engineering/'
OUT=E+'cp1-assumed-thermal-birth-linear-001/'
RUN=E+'cp1-assumed-thermal-birth-linear-root-execution-001/'
ACTUAL=E+'cp1-assumed-thermal-birth-linear-execution-prep-001/actual-contract.json'
CHILD=E+'cp1-assumed-thermal-birth-linear-child-peer-001/review.json'
EXPECTED={ACTUAL:'547ee8df69ecb45d87cb7f68dbe5ff522f85b79c019fa20c19c8fe9335e13f68',
 CHILD:'aa4a4eac0e34c9667f012eb57919b5aff6d92bcd8ab38e1e0f592aa93724ac63',
 RUN+'closed-result.json':'a63dfb7699212c4782aa6de8b54d12a0530cf67f73a19878f1bd1847d6ed5f58',
 OUT+'native-execution.json':'a210f0ef6d41686ce795b76d7d43fc17aa320038cfabd601d0250ae8feb2b673',
 OUT+'native.log':'e4e3c72bda327a4ac687dc89bd8241d277292f12d1174016bf490c5b242d44a3'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(name):return json.loads((ROOT/name).read_text())
def need(value,label):
    if not value:raise AssertionError(label)
def words(value):return struct.pack('>d',value)
def rows(name,fields):
    with (ROOT/OUT/name).open(newline='') as stream:
        reader=csv.DictReader(stream);need(reader.fieldnames==fields,'CSV fields '+name)
        values=[{k:float(v) for k,v in row.items()} for row in reader]
    need(values and all(math.isfinite(v) for row in values for v in row.values()),'finite CSV '+name)
    return values

def main():
    actual=load(ACTUAL);closed=load(RUN+'closed-result.json');receipt=load(OUT+'native-execution.json')
    pins=dict(actual['input_sha256']);need(len(pins)==98,'98 inputs')
    pins.update(EXPECTED)
    for name,identity in closed['output_files'].items():pins[OUT+name]=identity['sha256']
    for name in ['launch.json','result-review.json','stdout.log','stderr.log']:
        pins[RUN+name]=sha(ROOT/RUN/name)
    pins[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    before={}
    for name,digest in pins.items():
        p=ROOT/name;need(p.is_file() and not p.is_symlink() and p.suffix not in ['.dylib','.so','.msh','.bin'],'regular saved file')
        before[name]=sha(p);need(before[name]==digest,'digest '+name)
    inventory=closed['output_files'];observed={str(p.relative_to(ROOT/OUT)) for p in (ROOT/OUT).rglob('*') if p.is_file()}
    need(observed==set(inventory) and len(inventory)==502,'complete502')
    need(all(not p.is_symlink() for p in (ROOT/OUT).rglob('*')),'no output symlinks')
    need(sum(i['bytes'] for i in inventory.values())==5881859,'original total bytes')
    for name,identity in inventory.items():need((ROOT/OUT/name).stat().st_size==identity['bytes'],'output size')
    need(receipt['complete_artifact_sha256']=={n:r['sha256'] for n,r in inventory.items() if n!='native-execution.json'},'complete501 map')
    need(receipt['artifact_sha256']=={n:r['sha256'] for n,r in inventory.items() if n!='native-execution.json' and not n.startswith('source-snapshots/')},'flat492 map')
    need(len(receipt['input_sha256'])==15,'input15 map')
    for name,digest in receipt['input_sha256'].items():need(inventory[name]['sha256']==digest,'snapshot/input map')
    for name in inventory:
        if name.startswith('source-snapshots/'):
            need(sha(ROOT/name[len('source-snapshots/'):])==inventory[name]['sha256'],'executed source copy')
    need(inventory['actual-contract.json']['sha256']==EXPECTED[ACTUAL] and receipt['contract_sha256']==EXPECTED[ACTUAL]==receipt['actual_contract_sha256'],'actual/mirror')
    contract=load(OUT+'frozen-contract.json');card=load(OUT+'card.json')
    need(contract['card']==card and contract['card_sha256']==inventory['card.json']['sha256'],'card/reference')
    need(contract['assessor_sha256']==inventory['assess.py']['sha256']=='0548fcbf6eba737aaaf816abbfbfd0511b5b8fb266aa10c34a1f5817eef0e338','unchanged assessor')
    need(receipt['physics_contract_sha256']==inventory['frozen-contract.json']['sha256']==actual['numerical_reference_sha256'],'reference roles')
    need(contract['input_sha256']['thermal-birth.i']==inventory['thermal-birth.i']['sha256'] and contract['level_input_sha256']['2']==inventory['time-level.i']['sha256'],'deck/time-level')
    need(receipt['level']==2 and receipt['returncode']==0 and receipt['native_execution_completed'] is True and receipt['passed'] is False and receipt['independent_assessment_performed'] is False,'completion distinct assessment')
    need(receipt['stop_reason'] is None and receipt['controller_error'] is None and receipt['process_reaped'] is True and receipt['jobs']==[dict(name='native',returncode=0,process_reaped=True)],'receipt lifecycle')
    need(closed['actual_sha256']==EXPECTED[ACTUAL] and closed['child_peer_sha256']==EXPECTED[CHILD] and closed['returncode']==0 and closed['controller_reaped'] is True and closed['root_stop_reason'] is None,'root lifecycle')
    need(closed['all98_inputs19files13links_actual_peer_python_before_after_unchanged'] is True,'root freshness')
    launch=load(RUN+'launch.json');need(sha(ROOT/RUN/'launch.json')==closed['root_launch_sha256'],'root launch')
    need(launch['actual_sha256']==EXPECTED[ACTUAL] and launch['child_peer_sha256']==EXPECTED[CHILD] and launch['source_sha256']==actual['source_sha256'],'launch source')
    native=closed['observed_native_direct_children'];need(len(native)==1,'one observed native child')
    child=native[0];need(child['ppid']==closed['controller_pid'] and child['pgid']==child['pid'] and child['observed_comm']==str(ROOT/E/'moose-local-installed-002/bin/combined-opt'),'owned PPID/group/comm association')
    absence=closed['individual_observed_leaders_absent'];need(set(map(int,absence))=={closed['controller_pid'],child['pid']} and all(absence.values()),'individual observed absence')
    samples=closed['native_owned_metadata_samples'];need(samples and all(r['pid']==child['pid'] and r['ppid']==child['ppid'] and r['pgid']==child['pgid'] and r['observed_comm']==child['observed_comm'] for r in samples),'native samples association')
    need(closed['universal_descendant_absence_claimed'] is False,'limited absence')
    need(actual['runtime_sha256s']==receipt['runtime_sha256s'] and len(receipt['runtime_sha256s'])==19 and actual['runtime_symlinks']==receipt['runtime_symlinks'] and len(receipt['runtime_symlinks'])==13,'runtime metadata joins')
    rss=receipt['RSS_samples'];need(len(rss)==54 and max(r['RSS_bytes'] for r in rss)==receipt['max_observed_RSS_bytes']==152092672,'saved RSS counts/max')
    for name in ['stdout','stderr']:need(sha(ROOT/RUN/(name+'.log'))==closed[name+'_sha256'],'root stream')

    log=(ROOT/OUT/'native.log').read_text();clean=re.sub(r'\x1b\[[0-9;]*m','',log)
    steps=re.findall(r'^Time Step (\d+), time = ([^,\n]+), dt = ([^\n]+)',clean,re.M)
    need([int(r[0]) for r in steps]==list(range(1,161)) and all(float(r[2])==.0025 for r in steps),'exact160 log steps')
    need(log.count('Solve Converged!')==160 and 'DIVERGED_' not in log and 'Solver Mode:             Linear' in log,'completed LINEAR history')
    need('Option left: name:-skip_petscrc (no value) source: command line' in clean,'retained unused option warning')
    for stem in ['thermal_begin','thermal_end','thermal_properties']:
        need({n for n in observed if n.startswith(stem+'_')}=={f'{stem}_{i:04d}.csv' for i in range(161)},'complete frames '+stem)
    time_rows=rows('thermal.csv',['time','source_power']);need(len(time_rows)==161 and time_rows[0]['time']==0 and all(round(r['time']/.0025)==i and r['source_power']>0 for i,r in enumerate(time_rows)),'time/power row associations')
    need(all(time_rows[i]['time']>time_rows[i-1]['time'] for i in range(1,161)),'strict ordered time history')
    complete_nodes=set(itertools.product([i/8 for i in range(17)],[i/4 for i in range(5)],[i/4 for i in range(5)]))
    old_nodes={p for p in complete_nodes if p[0]<=1}
    node_ids={};element_ids={};previous=None;max_history=0.;max_cp=0.;max_k=0.;extrema=[math.inf,-math.inf];frame_summary=[];shared_history=None
    for step in range(161):
        full=step>=80;expected_nodes=complete_nodes if full else old_nodes
        frames={}
        for stem in ['begin','end']:
            data=rows(f'thermal_{stem}_{step:04d}.csv',['id','temperature','x','y','z'])
            points={(r['x'],r['y'],r['z']):r for r in data}
            need(len(points)==len(data) and set(points)==expected_nodes,'complete active coordinate grid')
            need(len({r['id'] for r in data})==len(data) and all(r['id'].is_integer() for r in data),'unique integer node ids')
            for p,r in points.items():
                if p in node_ids:need(node_ids[p]==r['id'],'persistent coordinate-node id association')
                node_ids[p]=r['id'];extrema=[min(extrema[0],r['temperature']),max(extrema[1],r['temperature'])]
            frames[stem]={p:r['temperature'] for p,r in points.items()}
        if step==0:need(all(v==400 for field in frames.values() for v in field.values()),'initial400K')
        else:
            differences=[abs(frames['begin'][p]-v) for p,v in previous.items()];max_history=max(max_history,max(differences));need(max(differences)<=card['predeclared_tolerances']['node_history_K'],'stored begin/previous-end association')
            added=set(frames['begin'])-set(previous)
            if step==80:
                need(added==complete_nodes-old_nodes and len(added)==200 and all(frames['begin'][p]==350 for p in added),'only200 new active nodes350K')
                shared=[p for p in old_nodes if p[0]==1];need(len(shared)==25,'25 interface nodes')
                shared_history=dict(shared_interface_nodes=25,all_existing225_preserved_within_card_tolerance=True,shared25_binary64_words_preserved=all(words(frames['begin'][p])==words(previous[p]) for p in shared),added200_exact350=True)
            else:need(not added,'only one declared birth transition')
        previous=frames['end']
        properties=rows(f'thermal_properties_{step:04d}.csv',['cp_seen','id','k_seen','q_seen','x','y','z'])
        expected_centers=set(itertools.product([(i+.5)/8 for i in range(16 if full else 8)],[(i+.5)/4 for i in range(4)],[(i+.5)/4 for i in range(4)]))
        observed_centers={(r['x'],r['y'],r['z']):r for r in properties};need(len(observed_centers)==len(properties) and set(observed_centers)==expected_centers,'complete active element-center grid')
        need(len({r['id'] for r in properties})==len(properties) and all(r['id'].is_integer() for r in properties),'unique integer cell ids')
        for p,r in observed_centers.items():
            if p in element_ids:need(element_ids[p]==r['id'],'persistent cell-center/id association')
            element_ids[p]=r['id'];max_cp=max(max_cp,abs(r['cp_seen']-900));max_k=max(max_k,abs(r['k_seen']-187));need(r['q_seen']>0,'positive finite recorded source sample')
        frame_summary.append(dict(index=step,active_nodes=len(expected_nodes),element_samples=len(properties)))
    need(max_cp<=card['predeclared_tolerances']['material_property_absolute'] and max_k<=card['predeclared_tolerances']['material_property_absolute'],'unchanged material sample tolerance')
    after={name:sha(ROOT/name) for name in pins};need(after==before,'all stopped inputs unchanged')
    result=dict(schema='962-cp1-LINEAR-independent-stopped-association-check/v1',status='PASS_NATIVE_HISTORY_ASSOCIATIONS_ONLY',input_sha256=before,input_sha256_after=after,all_bound_saved_inputs_unchanged=True,full502_output_inventory=inventory,
      counts=dict(output_files=502,output_bytes=5881859,actual_inputs=98,native_inputs=15,complete_artifact_map=501,flat_artifact_map=492,field_CSVs=483,positive_time_field_CSVs=480,thermal_time_rows=161,steps=160),
      all161_frame_associations=frame_summary,initial_active_nodes=225,post_birth_active_nodes=425,initial_element_samples=128,post_birth_element_samples=256,birth_index80=shared_history,
      maximum_saved_existing_node_history_error_K=max_history,maximum_saved_cp_deviation=max_cp,maximum_saved_k_deviation=max_k,all_saved_temperature_extrema_K=extrema,
      time_row_maximum_product_vs_saved_deviation_s=max(abs(r['time']-i*.0025) for i,r in enumerate(time_rows)),
      unused_PETSc_option_warning_preserved='-skip_petscrc',warning_does_not_prove_option_suppression_or_cause=True,
      lifecycle_root_attribution=dict(returncode=0,controller_reaped=True,one_native_direct_child_PPId_group_comm_associated=True,observed_native_samples=len(samples),observed_controller_and_native_individually_absent=True,universal_absence_claimed=False,root_wall_seconds=closed['wall_seconds'],controller_wall_seconds=receipt['wall_seconds'],RSS_samples=len(rss),maximum_sampled_owned_leader_RSS_bytes=receipt['max_observed_RSS_bytes'],true_peak=False),
      scope='CSV finite row/grid/ID/history/birth/material-sample association and source/contract/byte closure only. No Gaussian source formula, energy/enthalpy/refinement acceptance, assembled residual or PDE replay. The unchanged0548 assessor is read as source only, never imported or invoked.',
      original_Newton_nonlinear_criterion_not_checked=True,independent_assessment_performed=False,energy_acceptance=False,engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False)
    path=HERE/'independent-saved-check.json';need(not path.exists(),'fresh check output');path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'],files=502,steps=160,checked_saved_files=len(pins),field_CSVs=483,assessor_invoked=False)))

if __name__=='__main__':main()
