"""Qualify explicit constraints on a witness and audit actual head edge lengths."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from trial_planar_flips import sha, save_json, write_off
from trial_masked_isotropic_v2 import triangle_keys


def read_off(path):
    with path.open() as stream:
        if stream.readline().strip() != 'OFF': raise ValueError('Expected OFF')
        line = stream.readline()
        while not line.strip(): line = stream.readline()
        nv, nf, _ = map(int, line.split())
        v = np.loadtxt(stream, max_rows=nv)
        faces = np.loadtxt(stream, dtype=np.int64)
    if faces.ndim != 2 or faces.shape != (nf,4) or not (faces[:,0] == 3).all():
        raise ValueError('Nontriangular output')
    return v, faces[:,1:]


def run(kernel, mesh, mask, target, output, report, preflight=False):
    command = [str(kernel),str(mesh),str(mask),str(target),str(output),str(report)]
    if preflight: command.append('--preflight-only')
    p = subprocess.run(command, capture_output=True, text=True, timeout=180)
    return {'argv': command, 'exit_code':p.returncode,'stderr':p.stderr}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel','inspector','parent-off','protected-npy','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--parent-off-sha256',required=True)
    parser.add_argument('--protected-sha256',required=True)
    args=parser.parse_args()
    if args.output.exists(): raise SystemExit('Existing output refused.')
    if sha(args.parent_off) != args.parent_off_sha256 or sha(args.protected_npy) != args.protected_sha256:
        raise SystemExit('Input hash mismatch.')
    args.output.mkdir(parents=True)
    save_json(args.output/'plan.json',{'kernel_sha256':sha(args.kernel),
        'inspector_sha256':sha(args.inspector),'source_sha256':sha(Path(__file__)),
        'parent_off_sha256':args.parent_off_sha256,'mask_sha256':args.protected_sha256,
        'positive_witness_target_mm':.7,'negative_witness_target_mm':.2,
        'head_preflight_targets_mm':[.5,.7],
        'expected':'Positive witness changes geometry outside an exact protected patch; short constraints fail before writing a mesh. Full head is preflight-only.'})
    v=np.array([[x*.5,y*.5,.005*np.sin(x*y*.25)] for y in range(5) for x in range(5)],float)
    f=[]
    for y in range(4):
        for x in range(4):
            a=y*5+x;f.extend([[a,a+1,a+6],[a,a+6,a+5]])
    f=np.asarray(f,np.int64);write_off(args.output/'control.off',v,f)
    mask=args.output/'control-mask.txt';mask.write_text('10\n11\n')
    receipts={}
    for name,target in [('positive',.7),('too-short',.2)]:
        receipts[name]=run(args.kernel,args.output/'control.off',mask,target,args.output/(name+'.off'),args.output/(name+'.json'))
    if receipts['positive']['exit_code'] != 0: raise SystemExit('Positive constraint witness failed.')
    v2,f2=read_off(args.output/'positive.off')
    exact=bool(np.isin(triangle_keys(v,f[10:12]),triangle_keys(v2,f2)).all())
    native=subprocess.run([str(args.inspector),str(args.output/'positive.off')],capture_output=True,text=True,timeout=60)
    inspection=json.loads(native.stdout);save_json(args.output/'positive-native.json',inspection)
    checks={'positive_protected_oriented_triangles_exact':exact,
        'positive_output_changed':not (v.shape==v2.shape and f.shape==f2.shape and np.array_equal(v,v2) and np.array_equal(f,f2)),
        'positive_no_intersections':inspection.get('intersection_pairs')==0,
        'positive_no_degeneracies':inspection.get('degenerate_faces')==0,
        'positive_valid_polygon_mesh':inspection.get('valid_polygon_mesh') is True,
        'short_constraint_rejected':receipts['too-short']['exit_code']==5,
        'short_constraint_no_mesh':not (args.output/'too-short.off').exists()}
    if not all(checks.values()): raise SystemExit('Constraint controls failed: '+json.dumps(checks))
    protected=np.load(args.protected_npy,allow_pickle=False)
    head_mask=args.output/'head-mask.txt';np.savetxt(head_mask,protected,fmt='%d')
    head={}
    for name,target in [('head-0p5',.5),('head-0p7',.7)]:
        receipts[name]=run(args.kernel,args.parent_off,head_mask,target,args.output/(name+'.off'),args.output/(name+'.json'),True)
        head[name]=json.loads((args.output/(name+'.json')).read_text())
    checks['head_0p5_refused_before_remeshing']=receipts['head-0p5']['exit_code']==5 and not (args.output/'head-0p5.off').exists()
    checks['head_0p7_length_check_passes_only']=receipts['head-0p7']['exit_code']==0 and not (args.output/'head-0p7.off').exists()
    checks['inputs_unchanged']=sha(args.parent_off)==args.parent_off_sha256 and sha(args.protected_npy)==args.protected_sha256
    save_json(args.output/'execution-receipts.json',receipts)
    result={'controls':checks,'all_checks_passed':all(checks.values()),'head_preflight':head,
        'witness_before':{'vertices':len(v),'faces':len(f)},'witness_after':{'vertices':len(v2),'faces':len(f2)},
        'full_head_remesher_executed':False,'full_head_accepted':False,'manufacturing_authorized':False,
        'scope':'Exact-protection runtime witness and real-data length admission, not a qualified head mesh.'}
    save_json(args.output/'report.json',result);print(json.dumps(result))


if __name__=='__main__':
    main()
