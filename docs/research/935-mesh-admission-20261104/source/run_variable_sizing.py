"""Qualify the sizing field and run one bounded full-parent study trial."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import numpy as np
from trial_planar_flips import sha, save_json, write_off
from trial_masked_isotropic_v2 import triangle_keys
from run_constraint_controls import read_off


def bounded(command, log, seconds, rss_limit=12*1024**3):
    start=time.monotonic(); peak=0; reason=None
    with log.open('x') as stream:
        p=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        save_json(log.with_suffix('.process.json'),{'pid':p.pid,'argv':list(map(str,command))})
        while p.poll() is None:
            sample=subprocess.run(['ps','-p',str(p.pid),'-o','rss='],capture_output=True,text=True)
            if sample.stdout.strip(): peak=max(peak,int(sample.stdout.strip())*1024)
            if time.monotonic()-start>seconds: reason='wall_timeout'
            elif peak>rss_limit: reason='rss_limit'
            if reason:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                break
            time.sleep(.5)
    receipt={'argv':list(map(str,command)),'exit_code':p.returncode,'termination_reason':reason,
             'elapsed_seconds':time.monotonic()-start,'sampled_peak_rss_bytes':peak,
             'rss_limit_bytes':rss_limit,'wall_limit_seconds':seconds}
    save_json(log.with_suffix('.execution.json'),receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel','constraints-job','reference','inspector','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Existing output refused.')
    reference=json.loads(args.reference.read_text())
    if sha(args.constraints_job/'manifest.json')!=reference['private_manifest_sha256']:
        raise SystemExit('Qualified constraints manifest mismatch.')
    manifest=json.loads((args.constraints_job/'manifest.json').read_text())['files']
    for name in ('argv.json','controls-001/head-mask.txt'):
        if sha(args.constraints_job/name)!=manifest[name]['sha256']:raise SystemExit('Prior input mismatch: '+name)
    prior=json.loads((args.constraints_job/'argv.json').read_text())
    parent=Path(prior[prior.index('--parent-off')+1]);mask=args.constraints_job/'controls-001/head-mask.txt'
    if sha(parent)!=reference['full_parent_roundtrip']['off_sha256']:raise SystemExit('Parent OFF mismatch.')
    args.output.mkdir(parents=True)
    save_json(args.output/'plan.json',{'kernel_sha256':sha(args.kernel),'source_sha256':sha(Path(__file__)),
        'qualified_reference_sha256':sha(args.reference),'parent_off_sha256':sha(parent),'mask_sha256':sha(mask),
        'sizing':{'locked_target_mm':.7,'free_target_min_mm':.2,'transition_graph_distance_mm':1.,'split_vertex_update':'arithmetic mean of edge endpoint sizes'},
        'head_wall_limit_seconds':900,'head_rss_limit_bytes':12*1024**3,
        'head_gates':{'exact_protected_triangles':True,'native_intersections':0,'parent_sampled_max_mm':.01,
                      'relative_volume_change_max':.0001,'bad_triangle_reduction_min_fraction':.5,'topology_unchanged':True},
        'upstream_admissibility':'Closed reconstructed assembly under hypotheses; no anatomical or physical acceptance.'})
    n=17;v=np.array([[x*.5,y*.5,.005*np.sin(x*y*.25)] for y in range(n) for x in range(n)],float);f=[]
    for y in range(n-1):
        for x in range(n-1):
            a=y*n+x;f.extend([[a,a+1,a+n+1],[a,a+n+1,a+n]])
    f=np.asarray(f,np.int64);protected=np.array([238,239])
    write_off(args.output/'witness.off',v,f)
    witness_mask=args.output/'witness-mask.txt';np.savetxt(witness_mask,protected,fmt='%d')
    command=[str(args.kernel),str(args.output/'witness.off'),str(witness_mask),str(args.output/'witness-output.off'),str(args.output/'witness-native.json')]
    receipt=bounded(command,args.output/'witness.log',120)
    if receipt['exit_code']!=0:raise SystemExit('Sizing witness process failed.')
    native=json.loads((args.output/'witness-native.json').read_text());v2,f2=read_off(args.output/'witness-output.off')
    keys=triangle_keys(v2,f2);original=triangle_keys(v,f)
    check=subprocess.run([str(args.inspector),str(args.output/'witness-output.off')],capture_output=True,text=True,timeout=120)
    inspected=json.loads(check.stdout)
    checks={'exact_protected_triangles':bool(np.isin(original[protected],keys).all()),
        'unprotected_geometry_actually_changed':bool((~np.isin(original,keys)).any()),
        'zero_intersections':inspected.get('intersection_pairs')==0,
        'zero_degeneracies':inspected.get('degenerate_faces')==0,
        'native_precondition_passed':native['oversize_locked_edges']==0,
        'field_reaches_fine_target':abs(native['initial_target_min_mm']-.2)<1e-12,
        'final_field_bounds':native['final_target_min_mm']>=.2-1e-12 and native['final_target_max_mm']<=.7+1e-12,
        'witness_refined':len(f2)>len(f)}
    save_json(args.output/'witness-assessment.json',{'checks':checks,'input_faces':len(f),'output_faces':len(f2),'native_geometry':inspected})
    if not all(checks.values()):raise SystemExit('Variable sizing witness rejected.')
    preflight=bounded([str(args.kernel),str(parent),str(mask),str(args.output/'unused.off'),str(args.output/'head-preflight.json'),'--preflight-only'],args.output/'head-preflight.log',180)
    if preflight['exit_code']!=0:raise SystemExit('Full-parent variable field preflight failed.')
    prepared=json.loads((args.output/'head-preflight.json').read_text())
    if prepared['oversize_locked_edges']!=0 or prepared['locked_edges']!=492169 or prepared['locked_vertices']!=342090:
        raise SystemExit('Unexpected full-parent constraint classification.')
    vm=subprocess.check_output(['vm_stat'],text=True);page=int(re.search(r'page size of (\d+) bytes',vm).group(1))
    counters={k:int(v) for k,v in re.findall(r'^(Pages free|Pages inactive|Pages speculative):\s+(\d+)\.',vm,re.M)}
    reclaimable=page*sum(counters.values())
    save_json(args.output/'resource-preflight.json',{'mac_free_inactive_speculative_bytes':reclaimable,
        'minimum_required_bytes':18*1024**3,'scope':'Approximate current reclaimable pages, not a guarantee of available RAM.'})
    if reclaimable<18*1024**3:raise SystemExit('Insufficient local reclaimable-memory estimate for the bounded full run.')
    head=bounded([str(args.kernel),str(parent),str(mask),str(args.output/'candidate.off'),str(args.output/'head-native.json')],args.output/'head.log',900)
    print(json.dumps(head))
    if head['exit_code']!=0:raise SystemExit(1)


if __name__=='__main__':
    main()
