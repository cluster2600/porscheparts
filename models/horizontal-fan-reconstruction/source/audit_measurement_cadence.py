#!/usr/bin/env python3
"""Audit native measurement cadence without rewriting historical calculation reports."""
import argparse,hashlib,json,re
from pathlib import Path


def audit(study,native,output):
    records={}
    pairs=[('R0-common-h7','cfd-R0-common-h7','R0-common-h7-flow-summary.json'),('V2-common-h7','cfd-V2-short-edge-resolution-run2','V2-common-h7-flow-summary.json')]
    pairs += [(v+'-fine-150steps-phase'+str(t),'cfd-'+v+'-fine-150steps-phase'+str(t),v+'-fine-150steps-phase'+str(t)+'-summary.json') for v in ['R0','V2'] for t in [150,300,450,600]]
    pairs += [(label,'cfd-'+label,label+'-summary.json') for label in ['V2-fine-continuation750','R0-fine-pressure015-750','V2-fine-pressure015-900']]
    for label,case,summary_name in pairs:
        p=study/'results/cfd'/summary_name;r=json.loads(p.read_text());tables={}
        expected=list(range(int(r['iterations_completed'])-r['window_size']+1,int(r['iterations_completed'])+1))
        for name,digest in r['file_sha256'].items():
            if not name.startswith('postProcessing/'):continue
            source=native/case/name
            if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('Original table hash differs: '+label+'/'+name)
            times=[float(re.match(r'\s*([-+0-9.eE]+)',line)[1]) for line in source.read_text().splitlines() if line.strip() and not line.startswith('#')]
            tables[name]={'bytes':source.stat().st_size,'sha256':digest,'native_sample_count':len(times),'first_sample_iteration':times[0],'last_sample_iteration':times[-1],'last_required_sample_iterations':times[-r['window_size']:],'last_required_samples_match_every_solver_iteration':len(times)>=r['window_size'] and times[-r['window_size']:]==expected}
        valid=len(tables)==3 and all(t['last_required_samples_match_every_solver_iteration'] for t in tables.values())
        records[label]={'historical_summary_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'historical_status':r['status'],'required_measurement_window':r['window_size'],'final_iteration':r['iterations_completed'],'tables':tables,'contiguous_measurement_window_valid':valid,'current_numerical_admission_supported':valid and all(r['criteria_checks'].values()),'historical_admission_withdrawn':r['status']=='reference_pilot_admitted_numerically' and not valid,'original_table_hashes_preserved':True}
    result={'status':'native_measurement_cadence_audited_historical_fine_admission_withdrawn','cause':'Global writeInterval substitution in continuation helpers changed checkpoint and function-object telemetry cadence from 1 to 150. The summarizer did not require 20 contiguous native samples.','postprocessing_overwrite_claim_corrected':True,'original_records_not_rewritten':True,'records':records,'physical_validation_established':False,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.write_text(json.dumps(result,indent=2)+'\n');print('Native tables audited:',len(records),'valid windows:',sum(r['contiguous_measurement_window_valid'] for r in records.values()))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('native_tables',type=Path);p.add_argument('output',type=Path);a=p.parse_args();audit(a.study,a.native_tables,a.output)
