"""Standard-library-only input equivalence and load-path check; never runs CCX."""
import argparse
from collections import Counter
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time
import tempfile

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cards(text):
    result=[]
    for line in text.splitlines():
        if not line.strip() or line.startswith('**'):continue
        if line.startswith('*'):result.append([line,[]])
        else:result[-1][1].append(line)
    return result


def check_deck(old,new):
    before=old.splitlines(keepends=True);after=new.splitlines(keepends=True)
    if len(before)!=len(after):raise ValueError('Deck line count changed')
    static=[i+1 for i,line in enumerate(before) if line.strip()=='*STATIC,SOLVER=SPOOLES']
    if len(static)!=2:raise ValueError('Expected two static steps')
    changes=[]
    for i,(a,b) in enumerate(zip(before,after)):
        if i in static:
            if a!='0.125,1,0.001,0.125\n' or b!='0.0625,1,0.001,0.0625\n':
                raise ValueError('Unexpected static-step change')
            changes.append({'line':i+1,'old':a.strip(),'new':b.strip()})
        elif a!=b:raise ValueError('A non-increment deck line changed')
    parsed=cards(new);counts=Counter(k for k,_ in parsed)
    if counts['*STEP,NLGEOM,INC=100']!=2 or counts['*END STEP']!=2:raise ValueError('Step structure changed')
    if any(k.startswith('*AMPLITUDE') for k,_ in parsed):raise ValueError('Unexpected amplitude override')
    load_cards=[(k,rows) for k,rows in parsed if k.startswith('*CLOAD')]
    if [k for k,_ in load_cards]!=['*CLOAD','*CLOAD,OP=NEW']:raise ValueError('Load operation changed')
    first,second=(rows for _,rows in load_cards)
    first_pairs=[tuple(row.split(',')[:2]) for row in first]
    second_pairs=[tuple(row.split(',')[:2]) for row in second]
    if first_pairs!=second_pairs or any(Decimal(row.split(',')[2])!=0 for row in second):
        raise ValueError('The unload path does not reset exactly the same DOFs to zero')
    nominal=[]
    for i in range(1,33):
        t=Fraction(i,16);factor=t if t<=1 else 2-t
        nominal.append({'total_time':str(t),'load_factor':str(factor)})
    return {'only_two_static_increment_lines_changed':True,'changed_lines':changes,
        'all_other_deck_bytes_identical':True,'load_rows_per_step':[len(first),len(second)],
        'spring_card_count':sum(k.startswith('*SPRING,') for k,_ in parsed),
        'material_cards_unchanged':True,'loads_springs_boundaries_sections_output_cards_unchanged':True,
        'step_durations':['1','1'],'full_load_at_total_time':'1','zero_load_at_total_time':'2',
        'default_ramp_same_as_retained_case':True,'nominal_output_states':32,
        'nominal_load_path':nominal,
        'actual_native_state_count':None,'actual_state_scope':'No new solve exists. Cutbacks may add states; retained auditors accept arbitrary frame counts.'}


def check_sta(path):
    rows=[];previous_total=Decimal(0);previous_step=1;previous_increment=0;previous_local=Decimal(0)
    for line in Path(path).read_text().splitlines():
        f=line.split()
        if len(f)!=7 or not f[0].isdigit():continue
        step,increment,attempt,iterations=map(int,f[:4]);total,local,delta=map(Decimal,f[4:])
        if step not in (1,2) or total!=Decimal(step-1)+local or not Decimal(0)<local<=Decimal(1) or not Decimal(0)<delta<=Decimal('0.0625'):
            raise ValueError('Native STA does not follow the refined two-step path')
        if total<=previous_total or total-previous_total!=delta:
            raise ValueError('Native STA times are not strictly increasing and contiguous')
        if step==previous_step:
            if increment!=previous_increment+1:raise ValueError('Native STA increment order differs')
        elif not (previous_step==1 and step==2 and previous_local==1 and increment==1):
            raise ValueError('Native STA step transition differs')
        previous_total,previous_step,previous_increment,previous_local=total,step,increment,local
        factor=total if step==1 else Decimal(2)-total
        if not Decimal(0)<=factor<=Decimal(1):raise ValueError('Native load factor is outside the retained amplitude')
        rows.append({'step':step,'increment':increment,'total_time':str(total),'load_factor':str(factor),'iterations':iterations})
    if not rows or rows[-1]['step']!=2 or Decimal(rows[-1]['total_time'])!=2:
        raise ValueError('Native refined path is incomplete')
    if not any(r['step']==1 and Decimal(r['total_time'])==1 for r in rows):raise ValueError('Full loading state is absent')
    return {'states':rows,'state_count':len(rows),'full_load_then_zero_load':True}


def sta_selfcheck():
    # Synthetic path checks only, never represented as new native output.
    rows=[]
    for step in [1,2]:
        for i in range(1,17):
            local=Decimal(i)/16;total=Decimal(step-1)+local
            rows.append(f'{step} {i} 1 2 {total} {local} 0.0625')
    valid='\n'.join(rows)+'\n';rejected=[]
    corruptions={
        'duplicate_row':rows[:2]+[rows[1]]+rows[2:],
        'reversed_rows':[rows[1],rows[0]]+rows[2:],
        'missing_row':rows[:1]+rows[2:],
        'wrong_delta':[rows[0].rsplit(' ',1)[0]+' 0.03125']+rows[1:],
        'wrong_increment':[rows[0].replace('1 1 1 2','1 2 1 2')]+rows[1:],
        'step_without_full_loading':rows[:15]+rows[16:],
        'incomplete_unloading':rows[:-1]}
    with tempfile.TemporaryDirectory(prefix='sta-selfcheck-',dir=HERE) as directory:
        path=Path(directory)/'synthetic.sta';path.write_text(valid)
        if check_sta(path)['state_count']!=32:raise ValueError('Synthetic positive STA check failed')
        for label,values in corruptions.items():
            path.write_text('\n'.join(values)+'\n')
            try:check_sta(path)
            except ValueError:rejected.append(label)
            else:raise ValueError('A corrupt synthetic STA was accepted: '+label)
    return {'scope':'Synthetic stdlib checker tests, no CCX execution','positive_32_state_path':True,'rejected_corruptions':rejected}


def verify(sta=None):
    manifest_path=HERE/'preparation-manifest.json';manifest_sha=sha(manifest_path)
    manifest=json.loads(manifest_path.read_text());pins=manifest['files_sha256']
    if any(sha(p)!=v for p,v in pins.items()):raise ValueError('A preparation or retained input hash changed')
    old_path=Path(manifest['baseline_folder']);case=HERE/'case';name=manifest['case_name']
    old=(old_path/(name+'.inp')).read_text();new=(case/(name+'.inp')).read_text()
    result=check_deck(old,new)
    old_plan=json.loads((old_path/'plan.json').read_text());plan=json.loads((case/'plan.json').read_text())
    expected=json.loads(json.dumps(old_plan))
    for key in ['step','unload_step']:
        expected[key]['initial_increment']=0.0625;expected[key]['maximum_increment']=0.0625
    expected['step']['timeout_seconds']=3600
    expected['frozen_at_UTC']=plan['frozen_at_UTC']
    if plan!=expected:raise ValueError('An unapproved plan field changed')
    for name in manifest['copied_inputs']:
        if (case/name).read_bytes()!=(old_path/name).read_bytes():raise ValueError('A copied mesh/material input changed')
    # Negative controls remain in memory; no old or prepared deck is modified.
    mutations={
      'first_force_changed':new.replace('*CLOAD\n177,1,-1.07736931914','*CLOAD\n177,1,-1.07736931915',1),
      'spring_stiffness_changed':new.replace('0.7082152974504249','0.7082152974504250',1),
      'material_modulus_changed':new.replace('*ELASTIC\n106000,0.31','*ELASTIC\n106001,0.31',1),
      'end_duration_changed':new.replace('0.0625,1,0.001,0.0625','0.0625,0.125,0.001,0.0625',1),
      'output_changed':new.replace('S,PEEQ,ENER','S,PEEQ',1)}
    rejected=[]
    for label,mutant in mutations.items():
        if mutant==new:raise ValueError('A negative control did not mutate its intended input: '+label)
        try:check_deck(old,mutant)
        except ValueError:rejected.append(label)
        else:raise ValueError('A corrupted deck was accepted: '+label)
    if any(sha(p)!=v for p,v in pins.items()) or sha(manifest_path)!=manifest_sha:
        raise ValueError('Evidence changed during stdlib verification')
    result.update(status='prepared_inputs_verified_no_solver_execution',manifest_sha256=manifest_sha,
        pinned_files=len(pins),all_input_source_hashes_unchanged=True,negative_controls_rejected=rejected,
        plan_changed_fields=['frozen_at_UTC','step.initial_increment','step.maximum_increment','step.timeout_seconds','unload_step.initial_increment','unload_step.maximum_increment'],
        copied_inputs_byte_identical=manifest['copied_inputs'],ENER_relative_tolerance=0.001,Piola_relative_tolerance=0.0001)
    result['STA_checker_selfcheck']=sta_selfcheck()
    if sta is not None:result['new_native_STA_readonly_check']=check_sta(sta)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sta',type=Path)
    args=parser.parse_args();print(json.dumps(verify(args.sta),indent=2,allow_nan=False))
