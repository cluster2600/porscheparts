"""Extract lossless native64 fields for a portable figure; no solve or mesh change."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
BUNDLE_SHA='5e87583ce00de4f98fccd745065d630e2ad69207baa1cc985890ab8a108b024b'


def load(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def main(bundle):
    bundle=Path(bundle);manifest=bundle/'bundle.json'
    if sha(manifest)!=BUNDLE_SHA:raise ValueError('Actual native64 bundle identity differs')
    files=json.loads(manifest.read_text())['files']
    for name,row in files.items():
        if sha(bundle/name)!=row['sha256']:raise ValueError('Actual bundle file differs')
    for name in ('plot-data.npz','evidence.json'):
        if(HERE/name).exists()or(HERE/name).is_symlink():raise FileExistsError('Preserve plot data')
    prepare=load(bundle/'prepare.py','_original_native64_prepare');reader=load(bundle/'read_double_frd.py','_native64_reader')
    nodes,cells=prepare.model(bundle/'prepared-001/mesh.inp');frames=reader.read(bundle/'prepared-001/wholepart-release.frd',nodes,cells,[1.,2.,3.,4.])
    tags=np.array(sorted(nodes),dtype=np.int64);xyz=np.array([nodes[int(i)]for i in tags],dtype=np.float64)
    mesh=prepare.MESH/'mesh.npz'
    if sha(mesh)!='b156b03ab99f65e534a024a63f9cec12529ce9eb6392b0579bf2c20f857a5119':raise ValueError('Original surface face-ID input differs')
    with np.load(mesh,allow_pickle=False)as z:raw_faces=z['faces'].copy()
    faces=np.searchsorted(tags,raw_faces)
    if not np.array_equal(tags[faces],raw_faces)or faces.shape!=(31408,3):raise ValueError('Original face IDs are not retained')
    u=np.array([[row[1:]for row in frames[t]]for t in [1.,2.,3.,4.]],dtype=np.float64)
    if u.shape!=(4,103534,3)or not np.isfinite(u).all():raise ValueError('Four complete native fields required')
    for t in [1.,2.,3.,4.]:
        if not np.array_equal([r[0]for r in frames[t]],tags):raise ValueError('Native node identity/order differs')
    summary=json.loads((bundle/'result-summary.json').read_text());assessment=json.loads((bundle/'execution-001/numerical-assessment.json').read_text())
    if not assessment['numeric_controls_passed']or summary['actual_pilot_returncode']!=0 or summary['physical_print_prediction']:raise ValueError('Numerical scope differs')
    measured=np.linalg.norm(u,axis=2).max(axis=1)
    expected=[f['displacement_max_mm']for c in assessment['cases'].values()for f in c['frames']]
    if not np.allclose(measured,expected,rtol=1e-14,atol=0):raise ValueError('Native field extrema do not bind the numerical receipt')
    np.savez_compressed(HERE/'plot-data.npz',tags=tags,xyz=xyz,faces=faces,u=u,times=np.array([1.,2.,3.,4.]))
    evidence=dict(status='lossless_native_four_fields_extracted_no_new_solve',bundle_sha256=BUNDLE_SHA,
        numerical_assessment_sha256=sha(bundle/'execution-001/numerical-assessment.json'),summary_sha256=sha(bundle/'result-summary.json'),
        source_FRD_sha256=sha(bundle/'prepared-001/wholepart-release.frd'),source_INP_sha256=sha(bundle/'prepared-001/mesh.inp'),surface_faces_NPZ_sha256=sha(mesh),
        plot_data_sha256=sha(HERE/'plot-data.npz'),tags=103534,surface_faces=31408,times=[1.,2.,3.,4.],maximum_u_mm=measured.tolist(),
        geometry='Original finite-element INP coordinates and provided surface triangle IDs. No triangles or nodes added/removed; no subdivision.',
        color='Face colour is mean of its three actual native nodal displacement magnitudes; global node extrema remain in the labels.',
        interpolation='The original 31408 provided surface facets are retained for display; no claim of exact curved quadratic face rendering.',
        summary=summary,numerical_frames={name:row['frames']for name,row in assessment['cases'].items()},global_admission=False,
        source_sha256=sha(__file__))
    with(HERE/'evidence.json').open('x')as f:json.dump(evidence,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(plot_data_sha256=evidence['plot_data_sha256'],plot_data_bytes=(HERE/'plot-data.npz').stat().st_size,surface_faces=31408,all_native_nodes=103534)))


if __name__=='__main__':main(sys.argv[1])
