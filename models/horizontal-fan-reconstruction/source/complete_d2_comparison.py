#!/usr/bin/env python3
"""Analyse actual final20 only, then compose an explicitly derived60-row view."""
import hashlib,json,math,re,shutil
from pathlib import Path
import numpy as np
from summarize_reference_flow import summarize
from analyze_d2_result import analyze,native_table
from d2_completion_guards import merge_native_rows
from prepare_d2_restart1000 import identity


def audit_final(case):
    seeds=json.loads((case/'restart-preparation-receipt.json').read_text())
    record={'iteration':1020,'all32_native_files_complete_finite':True,'files':{}}
    for rank,cells in enumerate([122709,167115,208232,182540]):
        directory=case/f'processor{rank}'/'1020'
        oldfaces=[243383,351463,448842,385969][rank]
        for name in ['p','U','k','omega','nut','phi','Uf']:
            f=directory/name;text=f.read_text();m=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
            count=oldfaces if name in ['phi','Uf'] else cells;components=3 if name in ['U','Uf'] else 1
            numbers=re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',m[3]) if m else []
            if not m or int(m[2])!=count or m[1]!=('vector' if components==3 else 'scalar') or len(numbers)!=count*components or not all(math.isfinite(float(x)) for x in numbers) or re.search(r'(?i)\b(?:nan|inf)\b',text):
                raise ValueError('Incomplete/nonfinite native processor1020 field')
            record['files'][str(f.relative_to(case))]=identity(f)
        f=directory/'uniform/time';text=f.read_text()
        values={key:re.search(r'\b'+key+r'\s+([^;]+);',text)[1].strip().strip('"') for key in ['value','name','index','deltaT','deltaT0']}
        if values!={'value':'1020','name':'1020','index':'1020','deltaT':'1','deltaT0':'1'}:raise ValueError('Native checkpoint1020 time mismatch')
        record['files'][str(f.relative_to(case))]=identity(f)
    (case/'native1020-checkpoint-verification.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def complete(case,previous,selections,capsule,root):
    audit_final(case)
    summary=summarize(case,case/'flow-summary.json')
    # Raw old log (including partial1001) is never appended or rewritten.
    root.mkdir(exist_ok=False);(root/'current').symlink_to(previous/'current',target_is_directory=True)
    (root/'common-selections-private.npz').symlink_to(selections)
    extended=root/'extended';extended.mkdir()
    for name in ['1000','1020','constant','private-maps.npz','flow-summary.json']:
        (extended/name).symlink_to(case/name,target_is_directory=(case/name).is_dir())
    sources={}
    for function in ['commonOutletFlux','commonPressureBandMean','rotorForces']:
        old=list((previous/'extended/postProcessing'/function).glob('*/*.dat'))
        new=list((case/'postProcessing'/function).glob('*/*.dat'))
        if len(old)!=1 or len(new)!=1:raise ValueError('One raw native table per stage required')
        parser=lambda text:np.asarray([list(map(float,re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',line))) for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')])
        merged=merge_native_rows(old[0].read_text(),new[0].read_text(),parser)
        target=extended/'postProcessing'/function/'derived960-to1020'/old[0].name
        target.parent.mkdir(parents=True);target.write_text(merged)
        sources[function]={'original':identity(old[0]),'continuation':identity(new[0]),'derived_view':identity(target)}
        custody=case/'prior-native-tables'/function;custody.mkdir(parents=True)
        shutil.copyfile(old[0],custody/old[0].name)
    result=analyze(root,capsule/'configs/original-D2-protocol.json',case/'comparison.json')
    provenance={'status':'derived_analysis_view_not_single_native_execution',
                'control_reused_complete60_no_solver_replay':True,
                'extended_original_complete_iterations':40,'extended_new_complete_iterations':20,
                'old_partial1001_not_used_as_complete_or_checkpoint':True,'raw_native_logs_not_concatenated':True,
                'tables':sources,'continuation_summary_sha256':identity(case/'flow-summary.json')['sha256'],
                'comparison_sha256':identity(case/'comparison.json')['sha256'],
                'same_original_numeric_stationarity_and_domain_criteria':True,
                'restart_pressure_nonstationarity_still_rejects_admission':True,
                'comparison_status':result['status'],'physical_validation_established':False}
    (case/'comparison-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    return provenance


if __name__=='__main__':
    complete(Path('/run/extended'),Path('/previous'),Path('/selections.npz'),Path('/capsule'),Path('/run/analysis'))
