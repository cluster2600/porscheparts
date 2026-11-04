"""Assess actual reopened wall CAD against immutable acquired face masks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import igl


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def sample(v,f,seed):
    rng=np.random.default_rng(seed);p=v[f];weights=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
    picked=rng.choice(len(f),10000,p=weights/weights.sum());q=rng.random((10000,2));s=np.sqrt(q[:,0]);bary=np.column_stack((1-s,s*(1-q[:,1]),s*q[:,1]))
    return np.einsum('ij,ijk->ik',bary,p[picked])


def distance(points,v,f):
    squared,_,_=igl.point_mesh_squared_distance(points,v,f);d=np.sqrt(np.maximum(squared,0))
    return {'samples':len(d),'p95_mm':float(np.quantile(d,.95)),'sampled_max_mm':float(d.max())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('preparation','cad','arrays','paper','cad-python','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Existing support assessment refused.')
    contract_path=args.paper/'registered-contract.json';partition_path=args.paper/'registered-partitions.json'
    if sha(contract_path)!='49fc806e1f9d6f129892d1cdd15505b4ed304a68ee84f37bcbf1fd1c8461f779' or sha(partition_path)!='bca11c2633ed6fae331b9bd47d420f07f170b6f34d4ba232d68c87f37f1aa824':raise SystemExit('Frozen source contract mismatch.')
    contract=json.loads(contract_path.read_text());partitions=json.loads(partition_path.read_text())['partitions']
    with np.load(args.arrays,allow_pickle=False) as a:v,f=a['vertices'],a['triangles']
    for name,values,dtype in [('vertices',v,'<f8'),('triangles',f,'<i8')]:
        if hashlib.sha256(np.asarray(values,dtype=dtype).tobytes()).hexdigest()!=contract['source_array_hashes'][name]:raise SystemExit('Original acquired array mismatch.')
    args.output.mkdir(parents=True);step_hashes={p.name:sha(p) for p in args.cad.glob('*.step')};array_sha=sha(args.arrays)
    source=Path(__file__).parent
    plan={'actual_step_sha256':step_hashes,'arrays_sha256':array_sha,'source_sha256':sha(Path(__file__)),
        'inspector_source_sha256':sha(source/'inspect_wall_step.py'),'native_distance_source_sha256':sha(source/'native_wall_distances.py'),
        'source_support_limit_mm':.4,'reference_roundtrip_limit_mm':1e-6,'sampling_seeds':[9351104,9351105],
        'scope':'Conditional within-scan partial-fit study, not functional replica acceptance.'}
    (args.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    command=[str(args.cad_python),str(source/'inspect_wall_step.py'),'--preparation',str(args.preparation),'--cad',str(args.cad),'--output',str(args.output/'step')]
    with (args.output/'step-reload.log').open('x') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
    models=json.loads((args.preparation/'cad-domains.json').read_text());records=[]
    for model in models:
        if not model['admitted']:continue
        ident=model['id'];part=next(p for p in partitions if p['id']==ident);path=args.paper/part['file']
        if sha(path)!=part['sha256']:raise SystemExit('Source face partition changed.')
        with np.load(path,allow_pickle=False) as a:source_faces=a['selected_source_face_ids']
        with np.load(args.preparation/(ident+'-reference.npz'),allow_pickle=False) as a:
            if not np.array_equal(a['source_face_ids'],source_faces) or not np.array_equal(a['source_vertex_ids'],np.unique(f[source_faces])):raise SystemExit('Source mask reference mismatch.')
        with np.load(args.output/'step'/(ident+'-actual-step-mesh.npz'),allow_pickle=False) as a:cv,cf=a['vertices'],a['triangles']
        source_to_cad=distance(sample(v,f[source_faces],9351104),cv,cf)
        cad_to_source=distance(sample(cv,cf,9351105),v,f[source_faces])
        exact_report=args.output/(ident+'-native-distance.json')
        command=[str(args.cad_python),str(source/'native_wall_distances.py'),'--step',str(args.cad/(ident+'-analytic.step')),
            '--arrays',str(args.arrays),'--reference',str(args.preparation/(ident+'-reference.npz')),'--output',str(exact_report)]
        with (args.output/(ident+'-native-distance.log')).open('x') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
        native=json.loads(exact_report.read_text());checks={'native_source_vertices':native['all_vertices_within_exploratory_0p4mm'],
            'sampled_source_to_export':source_to_cad['sampled_max_mm']<=.4,'sampled_export_to_source':cad_to_source['sampled_max_mm']<=.4}
        records.append({'id':ident,'source_faces':len(source_faces),'native_source_vertices':native,
            'source_to_actual_step_mesh':source_to_cad,'actual_step_mesh_to_source':cad_to_source,'checks':checks,
            'accepted_as_partial_scan_fit':all(checks.values()),'physical_acceptance':False})
    if any(sha(args.cad/name)!=digest for name,digest in step_hashes.items()) or sha(args.arrays)!=array_sha:raise SystemExit('Input changed during independent assessment.')
    report={'regions':records,'actual_step_files_unchanged':True,'original_source_unchanged':True,'full_head_created':False,'manufacturing_authorized':False}
    (args.output/'support-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
