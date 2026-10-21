"""Artificial black-box coverage witnesses; no carrier input is used."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runtime',type=Path);args=p.parse_args();r=args.runtime.resolve()
    folder=r/'inputs/witnesses-001';folder.mkdir(parents=True,exist_ok=False)
    cases={}
    def flatrect(x0,x1,y0,y1,z):
        return [[(x0,y0,z),(x1,y0,z),(x1,y1,z)],[(x0,y0,z),(x1,y1,z),(x0,y1,z)]]
    square=flatrect(0,4,0,4,2)
    cases['covered-union']=(square+[
        [(0.5,0.5,0.5),(3.5,0.5,1),(0.5,3.5,1.5)],
        [(3.5,3.5,1),(5,3.5,1.2),(3.5,4,1.5)],
        [(0.5,0.5,1),(1.5,0.5,3),(0.5,1.5,1)],
        [(1,1,1),(2,1,1),(1,2,1)],
        [(1,1,2),(2,1,2),(1,2,2)],
        [(0,0,0.5),(1,1,1),(2,2,1.5)]],{2,5},True)
    ring=flatrect(0,6,0,2,5)+flatrect(0,6,4,6,5)+flatrect(0,2,2,4,5)+flatrect(4,6,2,4,5)
    cases['hole']=(ring+[
        [(1,1,1),(5,1,2),(3,5,3)],
        [(0.25,0.25,0.5),(1.75,0.25,1),(1,0.75,2)]],{9},True)
    lshape=flatrect(0,4,0,1,5)+flatrect(0,1,1,4,5)
    cases['nonconvex']=(lshape+[[ (0.5,3.5,1),(3.5,0.5,1.1),(0.5,0.5,0.1)]],set(),True)
    cases['strict-height-chain']=([
        [(0,0,1),(2,0,1),(0,2,1)],[(0,0,2),(2,0,2),(0,2,2)],[(0,0,3),(2,0,3),(0,2,3)],
        [(0,0,0.5),(2,0,2),(0,2,1)]],{0,1,3},True)
    ulp=float(np.spacing(1.))
    cases['positive-area-outside-one-ulp']=(flatrect(0,1,0,1,2)+[
        [(1-ulp,0,1),(1+ulp,0,0.5),(1-ulp,1,0.75)]],set(),True)
    cases['below-floor']=([[(0,0,-0.1),(1,0,1),(0,1,1)]],set(),False)
    plan={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'common_floor_z_mm':0,'cases':{name:{'expected_removed_indices':sorted(drop),'expected_execution_success':ok} for name,(_,drop,ok) in cases.items()},'scope':'Artificial mathematical witnesses only; all three hole-triangle vertices lie in the patch but its interior crosses the hole.'}
    (folder/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');results={}
    for name,(triangles,expected,okay) in cases.items():
        v=np.asarray(triangles,dtype=np.float64).reshape(-1,3);f=np.arange(len(v),dtype=np.int64).reshape(-1,3)
        source=folder/(name+'.npz');np.savez_compressed(source,vertices=v,faces=f,source_face_ids=np.arange(1000,1000+len(f),dtype=np.int64))
        out=r/'jobs'/('witness-'+name+'-001')
        run=subprocess.run(['python3',str(r/'run.py'),str(source),str(out),'--floor-z-mm','0'],capture_output=True,text=True,timeout=650)
        audit=json.loads((out/'audit.json').read_text());execution=json.loads((out/'execution-receipt.json').read_text())
        assert bool(run.returncode==0)==okay and execution['owned_scope_inactive'] and execution['identities_unchanged']
        if okay:
            observed={c['input_face_index'] for c in audit['native']['certificates']};assert observed==expected
            assert audit['coordinates_unchanged'] and audit['retained_face_indices_unchanged']
        else:observed=set();assert audit['status']=='rejected_native_failure'
        results[name]={'expected_removed_indices':sorted(expected),'observed_removed_indices':sorted(observed),'execution_success':run.returncode==0,'witness_pass':True,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'audit_sha256':hashlib.sha256((out/'audit.json').read_bytes()).hexdigest()}
    (r/'software-witness-results.json').write_text(json.dumps({'status':'software_witnesses_pass','plan_sha256':hashlib.sha256((folder/'plan.json').read_bytes()).hexdigest(),'cases':results},indent=2)+'\n');print(json.dumps(results))
if __name__=='__main__':main()
