"""Independent acquired-face membership, baseline-parameter and refusal controls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('job','arrays','paper','baseline','cad-python','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise SystemExit('Existing evidence verification refused.')
    contract=json.loads((args.paper/'registered-contract.json').read_text())
    if sha(args.baseline/'refined-features/features.json')!=contract['baseline_inputs']['refined-features/features.json']:raise SystemExit('Frozen baseline parameter mismatch.')
    with np.load(args.arrays,allow_pickle=False) as a:v,f=a['vertices'],a['triangles']
    for name,values,dtype in [('vertices',v,'<f8'),('triangles',f,'<i8')]:
        if hashlib.sha256(np.asarray(values,dtype=dtype).tobytes()).hexdigest()!=contract['source_array_hashes'][name]:raise SystemExit('Decoded acquired array mismatch.')
    models=json.loads((args.job/'preparation-006/cad-domains.json').read_text())
    baseline=json.loads((args.baseline/'refined-features/features.json').read_text())['fits'];partitions=json.loads((args.paper/'registered-partitions.json').read_text())['partitions'];regions=[]
    for index,m in enumerate(models,1):
        with np.load(args.job/'preparation-006'/(m['id']+'-reference.npz'),allow_pickle=False) as a:
            ids=a['source_vertex_ids'];faces=a['source_face_ids'];original=a['vertices'];local=a['triangles']
        registered=next(x for x in partitions if x['id']==m['id']);partition=args.paper/registered['file']
        if sha(partition)!=registered['sha256']:raise SystemExit('Registered partition changed.')
        with np.load(partition,allow_pickle=False) as a:expected=a['selected_source_face_ids']
        parameters=next(x for x in baseline if x['id']==f'stud_passage_{index}_C_91');axis=np.asarray(parameters['axis_xyz']);axis/=np.linalg.norm(axis)
        checks={'source_vertices_exact':bool(np.array_equal(original,v[ids])),
            'source_connectivity_exact':bool(np.array_equal(ids[local],f[faces])),
            'registered_face_selection_exact':bool(np.array_equal(faces,expected)),
            'baseline_origin_unchanged':bool(np.array_equal(m['origin'],parameters['center_xyz_mm'])),
            'baseline_axis_unchanged':bool(np.array_equal(m['axis'],axis)),
            'baseline_radius_unchanged':m['radius']==parameters['diameter_mm']/2}
        if not all(checks.values()):raise SystemExit('Acquired membership or baseline parameters failed.')
        regions.append({'id':m['id'],'source_faces':len(faces),'checks':checks})
    source=Path(__file__).parent
    with tempfile.TemporaryDirectory(prefix='935-wall-controls-') as tmp:
        tmp=Path(tmp);(tmp/'registered-contract.json').write_text('{}');(tmp/'registered-partitions.json').write_text('{}')
        command=[sys.executable,str(source/'assess_wall_support.py'),'--preparation',str(args.job/'preparation-006'),'--cad',str(args.job/'cad-005'),
            '--arrays',str(args.arrays),'--paper',str(tmp),'--cad-python',str(args.cad_python),'--output',str(tmp/'refused')]
        bad=subprocess.run(command,capture_output=True,text=True)
        refusals={'altered_contract_refused':bad.returncode!=0 and 'Frozen source contract mismatch' in bad.stderr,
            'no_output_on_contract_failure':not (tmp/'refused').exists()}
    fixture=args.job/'oracle-control';fixture.mkdir(exist_ok=False)
    angle=np.linspace(.7,.9,37);vertices=np.column_stack((5.6*np.cos(angle),5.6*np.sin(angle),np.full(37,1.5)))
    np.savez_compressed(fixture/'points.npz',vertices=vertices);np.savez_compressed(fixture/'ids.npz',source_vertex_ids=np.arange(37))
    command=[str(args.cad_python),str(source/'native_wall_distances.py'),'--step',str(args.job/'cad-005/controls.step'),
        '--arrays',str(fixture/'points.npz'),'--reference',str(fixture/'ids.npz'),'--output',str(fixture/'native-distance.json')]
    with (fixture/'native.log').open('x') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    native=json.loads((fixture/'native-distance.json').read_text());refusals['known_0p6mm_radial_error_detected']=abs(native['max_mm']-.6)<1e-7 and not native['all_vertices_within_exploratory_0p4mm']
    if not all(refusals.values()):raise SystemExit('Refusal or native-distance oracle control failed.')
    result={'regions':regions,'negative_controls':refusals,'exact_reference_source_faces':sum(r['source_faces'] for r in regions),
        'axes_or_radii_refitted':False,'physical_acceptance':False}
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
