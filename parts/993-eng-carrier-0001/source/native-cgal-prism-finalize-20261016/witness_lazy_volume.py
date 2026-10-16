"""Reproduce linear lazy-volume stack failure versus balanced exact arithmetic."""
import argparse,hashlib,json,resource,subprocess
from fractions import Fraction
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary',type=Path);p.add_argument('output',type=Path);p.add_argument('--terms',type=int,default=254624);args=p.parse_args()
    out=args.output;assert not out.exists();out.mkdir(parents=True)
    before=hashlib.sha256(args.binary.read_bytes()).hexdigest();rows=[]
    for mode in ['naive','balanced']:
        def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        r=subprocess.run([str(args.binary),'--lazy-witness',mode,str(args.terms)],capture_output=True,text=True,timeout=20,preexec_fn=no_core)
        (out/(mode+'.stdout')).write_text(r.stdout);(out/(mode+'.stderr')).write_text(r.stderr)
        rows.append({'mode':mode,'returncode':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()})
    balanced=rows[1]['returncode']==0 and Fraction(rows[1]['stdout'])==Fraction(args.terms,3)
    result={'terms':args.terms,'each_term_exact':'1/3','trials':rows,'naive_SIGSEGV_reproduced':rows[0]['returncode']==-11,
      'balanced_exact_sum_pass':balanced,'binary_sha256':before,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'binary_unchanged':before==hashlib.sha256(args.binary.read_bytes()).hexdigest(),
      'scope':'Software reproducer of the same linear-lazy accumulation pattern. Historical geometry process signal was not retained; this does not retroactively prove its signal.'}
    (out/'witness.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return 0 if balanced and result['naive_SIGSEGV_reproduced'] else 2

if __name__=='__main__':raise SystemExit(main())
