"""Run finite known-solid witnesses; retain every experimental API failure."""
import argparse,hashlib,json,subprocess
from fractions import Fraction
from pathlib import Path
import numpy as np

def tetra(v):
    v=np.array(v,dtype=np.float64);faces=[]
    for t,opposite in [([0,1,2],3),([0,1,3],2),([0,2,3],1),([1,2,3],0)]:
        if np.dot(np.cross(v[t[1]]-v[t[0]],v[t[2]]-v[t[0]]),v[opposite]-v[t[0]])>0:t[0],t[1]=t[1],t[0]
        faces.append(t)
    return v,np.array(faces,dtype=np.int64)

def prism(height):
    v=np.array([[0,0,0],[20,0,0],[0,20,0],[0,0,height],[20,0,height],[0,20,height]],dtype=np.float64)
    f=np.array([[0,2,1],[3,4,5],[0,1,4],[0,4,3],[1,2,5],[1,5,4],[2,0,3],[2,3,5]],dtype=np.int64)
    return v,f

def box(lo,hi):
    v=np.array([[lo[0],lo[1],lo[2]],[hi[0],lo[1],lo[2]],[hi[0],hi[1],lo[2]],[lo[0],hi[1],lo[2]],
      [lo[0],lo[1],hi[2]],[hi[0],lo[1],hi[2]],[hi[0],hi[1],hi[2]],[lo[0],hi[1],hi[2]]],dtype=np.float64)
    f=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=np.int64)
    return v,f

def soup(*meshes):
    vs=[];fs=[];n=0
    for v,f in meshes:vs.append(v);fs.append(f+n);n+=len(v)
    return np.vstack(vs),np.vstack(fs)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runtime',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    out=args.output.resolve();runtime=args.runtime.resolve();assert not out.exists();out.mkdir(parents=True)
    base=tetra([[0,0,0],[1,0,0],[0,1,0],[0,0,1]])
    face=tetra([[0,0,0],[1,0,0],[0,1,0],[0,0,-1]])
    point=(base[0]+[1,0,0],base[1]);overlap=(base[0]+[.5,0,0],base[1]);disjoint=(base[0]+[3,0,0],base[1])
    cases=[
      ('self-clean-tetra','self_union',base,None,Fraction(1,6),True),
      ('self-face-touch','self_union',soup(base,face),None,Fraction(1,3),True),
      ('self-overlap-tetra','self_union',soup(base,overlap),None,Fraction(5,16),True),
      ('self-point-touch','self_union',soup(base,point),None,Fraction(1,3),False),
      ('self-disjoint-tetra','self_union',soup(base,disjoint),None,Fraction(1,3),True),
      ('self-nested-prisms','self_union',soup(prism(10),prism(20)),None,Fraction(4000),True),
      ('union-prisms','union',prism(10),prism(20),Fraction(4000),True),
      ('intersection-prisms','intersection',prism(10),prism(20),Fraction(2000),True),
      ('difference-prism-gap','difference',prism(20),box([-1,-1,8],[21,21,12]),Fraction(3200),True)]
    results=[]
    for name,mode,a,b,volume,topology_expected in cases:
        inputs=[]
        for role,mesh in [('A',a),('B',b)]:
            if mesh is None:continue
            path=out/f'{name}-{role}.npz';np.savez_compressed(path,vertices=mesh[0],faces=mesh[1],source_face=np.arange(len(mesh[1]),dtype=np.int64))
            inputs.append(path)
        job=runtime/'jobs'/name
        command=['python3',str(runtime/'run.py'),mode,str(inputs[0]),str(job)]
        if b is not None:command+=['--second-input',str(inputs[1])]
        executed=subprocess.run(command,capture_output=True,text=True)
        (out/f'{name}-client.log').write_text(executed.stdout+executed.stderr)
        audit=json.loads((job/'audit.json').read_text()) if (job/'audit.json').is_file() else {}
        native=audit.get('native',{});actual=native.get('exact_signed_volume_mm3')
        exact_volume_pass=actual is not None and Fraction(actual)==volume
        observed_topology=audit.get('output_topology',{}).get('pass',False)
        expectation_pass=exact_volume_pass and observed_topology==topology_expected and native.get('source_face_lineage_complete',False)
        row=dict(name=name,mode=mode,client_returncode=executed.returncode,job=str(job),expected_exact_volume_mm3=str(volume),
          actual_exact_volume_mm3=actual,exact_volume_pass=exact_volume_pass,expected_manifold_topology=topology_expected,
          actual_topology=audit.get('output_topology'),native_exact_gate_pass=audit.get('native_exact_gate_pass',False),
          local_geometry_gates_pass=audit.get('local_geometry_gates_pass',False),expectation_pass=expectation_pass)
        results.append(row);print(json.dumps(row),flush=True)
    receipt={'CGAL_commit':'b4e8c1887ce6a0abeb618634125e5cfcd301ce16','experimental':True,'cases':results,
      'self_union_all_required_witnesses_pass':all(r['expectation_pass'] for r in results if r['mode']=='self_union'),
      'binary_boolean_all_required_witnesses_pass':all(r['expectation_pass'] for r in results if r['mode']!='self_union'),
      'witness_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'scope':'Known-solid software witnesses only. All failures retained; no carrier data processed.'}
    (out/'witness-results.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
