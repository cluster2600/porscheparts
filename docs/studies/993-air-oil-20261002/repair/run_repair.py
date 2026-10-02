#!/usr/bin/env python3
"""Replay bounded, pcurve-only repair with strict rejection gates."""
import argparse,json,subprocess,sys,shutil
from pathlib import Path
from diagnose import sha

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--max-iterations',type=int,default=3);a=ap.parse_args();a.output.mkdir()
    current=a.input.resolve();original=sha(current);r={'original_input_sha256':original,'iterations':[],'status':'unqualified','manufacturing_authorized':False}
    for i in range(1,a.max_iterations+1):
        trial=a.output/f'iteration-{i:02d}'
        p=subprocess.run([sys.executable,'-B','-u',str(Path(__file__).with_name('reproject.py')),str(current),str(trial),'--nodes','1025'],timeout=180)
        if p.returncode:raise ValueError('worker_repair_failed')
        result=json.loads((trial/'report.json').read_text())
        if not result['input_unchanged'] or not result['all_tolerances_unchanged'] or not result['serialized_3D_geometry_unchanged']:
            raise ValueError('3D_geometry_or_tolerance_changed')
        r['iterations'].append({'iteration':i,'report':str(trial/'report.json'),'accepted':result['accepted'],'changes':result['changes']})
        if not (trial/'corrected.step').exists():raise ValueError('STEP_export_failed')
        current=trial/'corrected.step'
        if result['accepted']:
            shutil.copy2(current,a.output/'corrected.step');r.update(status='curve_on_surface_roundtrip_passed_requires_full_native_BOP',corrected_sha256=sha(current))
            break
    r['original_input_unchanged']=sha(a.input)==original
    (a.output/'replay-report.json').write_text(json.dumps(r,indent=2)+'\n')
    if 'corrected_sha256' not in r:raise ValueError('repair_did_not_converge')
    print(json.dumps(r),flush=True)
