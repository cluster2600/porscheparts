"""Draw frozen presentation004 from copied, closed historical003 native profiles."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys

PRODUCER='work/carrier-C1-junction-section-figure-003/figure.py'
DATA='work/carrier-C1-junction-section-figure-003/data-001/section-data.json'
RENDERER='work/carrier-C1-junction-section-figure-004/figure.py'
PRODUCER_SHA='284ebdcb1ef0a94c8fddbc1e51ebd38245c00c50649c2d4a9d5de44e3354d2f9'

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def safe(root,name):
    p=Path(name);require(not p.is_absolute()and '..'not in p.parts and bool(p.parts),'Relative copied path required')
    path=root/p;require(not any(q.is_symlink()for q in [path,*path.parents]),'Symlink copy refused');return path
def copied_identities(root,pins):
    actual={name:sha(safe(root,name))for name in pins};require(actual==pins,'Copied payload changed');return actual

def run(plan_path,expected,output):
    plan_path=Path(plan_path);require(sha(plan_path)==expected,'Actual replay plan hash required');p=json.loads(plan_path.read_text())
    require(p['launch_ready']is True and p['root_GO_sha256']is not None,'NON-ARMED: no replay')
    require(sha(p['root_GO'])==p['root_GO_sha256'],'Actual replay GO differs')
    require(p['root_visual_QA_sha256']is not None and sha(p['root_visual_QA'])==p['root_visual_QA_sha256'],'Actual PNG/PDF root QA required')
    require(p['workers']==0 and p['threads']==1 and p['nice']==10 and p['inner_wall_seconds']==95 and p['outer_wall_seconds']==120
        and p['CPU_seconds']==[90,100],'Owned replay bounds differ')
    out=Path(output);require(out.absolute()==Path(p['output_directory']).absolute()and not out.exists()
        and not any(q.is_symlink()for q in [out,*out.parents]),'Fresh exact output required')
    root=Path(p['capsule_root']);manifest_path=Path(p['manifest'])
    require(sha(manifest_path)==p['manifest_sha256'],'Copied manifest changed');pins=json.loads(manifest_path.read_text())['files_sha256']
    before=copied_identities(root,pins)
    require(before[PRODUCER]==PRODUCER_SHA and before[RENDERER]==p['presentation_renderer_sha256'],'Producer/renderer identity differs')
    require(p['historical_producer']==str(Path(p['historical_root'])/PRODUCER)
        and p['historical_data']==str(Path(p['historical_root'])/DATA),'Explicit historical paths differ')
    require(Path(p['data'])==safe(root,DATA),'Copied data path differs')
    old=safe(root,PRODUCER).read_text();new=safe(root,RENDERER).read_text()
    require(new.count('top=.75,bottom=.31,wspace=.2')==1 and new.replace('top=.75,bottom=.31,wspace=.2','top=.75,bottom=.25,wspace=.2',1)==old,
        'Presentation differs beyond the single margin literal')
    authority=load(Path(__file__).with_name('historical_closure.py'),'_portable_closed_original003')
    require(sha(Path(__file__).with_name('historical_closure.py'))==p['closure_source_sha256']and sha(__file__)==p['replay_source_sha256'],'Replay/closure source changed')
    authority.closed_extraction(p)
    require(all(sha(k)==v for k,v in p['runtime_sha256'].items()),'Pinned runtime changed')
    renderer=load(safe(root,RENDERER),'_portable_presentation004')
    renderer.render(p['data'],p['data_sha256'],out,p['runtime_sha256'])
    r=json.loads((out/'render-receipt.json').read_text());reference=json.loads(safe(root,p['reference_render_receipt']).read_text())
    keys=['data_sha256','source_sha256','common_axes_and_aspect','checks','annotation_ray_actual_XYZ_mm','coarse_source_peak','h2_peak_plotted','runtime_files_sha256','no_geometry_modified','no_FEA']
    require(all(r[k]==reference[k]for k in keys),'Whole scientific render records differ')
    actual={name:sha(out/name)for name in p['expected_exports_sha256']}
    require(actual==p['expected_exports_sha256'],'Whole export bytes differ')
    require(before==copied_identities(root,pins)and all(sha(k)==v for k,v in p['runtime_sha256'].items())
        and sha(plan_path)==expected and sha(manifest_path)==p['manifest_sha256']
        and sha(__file__)==p['replay_source_sha256']
        and sha(Path(__file__).with_name('historical_closure.py'))==p['closure_source_sha256'],
        'Copied payload/runtime/plan/source changed after drawing')
    renderer.write(out/'portable-replay-receipt.json',dict(status='portable_presentation004_replayed_from_copied_closed003_profiles',
        plan_sha256=expected,manifest_sha256=p['manifest_sha256'],copied_payloads=len(pins),
        historical_extraction_producer_sha256=PRODUCER_SHA,presentation_renderer_sha256=p['presentation_renderer_sha256'],
        data_sha256=p['data_sha256'],whole_scientific_record_keys_equal=keys,whole_exports_sha256=actual,
        runtime_authority_files=len(p['runtime_sha256']),runtime_imported_files_after_exports=len(r['runtime_files_sha256']),
        no_native_extraction=True,no_geometry_modified=True,no_FEA=True,
        scope='Replay of previously sampled native section points; CAD parents linked by SHA, not included.'))

if __name__=='__main__':
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OSD_NUM_THREADS']:os.environ[name]='1'
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Bounded portable draw wall cap')))
    signal.setitimer(signal.ITIMER_REAL,95);resource.setrlimit(resource.RLIMIT_CPU,(90,100))
    require(len(sys.argv)==4,'Use replay PLAN SHA FRESH_DIR');run(*sys.argv[1:])
