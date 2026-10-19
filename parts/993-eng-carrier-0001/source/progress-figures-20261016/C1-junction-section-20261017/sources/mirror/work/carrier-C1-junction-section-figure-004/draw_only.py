"""Validate the frozen003 extraction, then draw the one-literal presentation004."""
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = 'work/carrier-C1-junction-section-figure-003/figure.py'
PRODUCER_SHA = '284ebdcb1ef0a94c8fddbc1e51ebd38245c00c50649c2d4a9d5de44e3354d2f9'
RENDERER = 'work/carrier-C1-junction-section-figure-004/figure.py'

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def verify_sources(plan):
    require(plan['root'] == str(ROOT) and plan['extraction_producer'] == PRODUCER
        and plan['extraction_producer_sha256'] == PRODUCER_SHA
        and plan['presentation_renderer'] == RENDERER, 'Explicit original producer/presentation identity differs')
    before = {p: sha(ROOT/p) for p in plan['files_sha256']}
    require(before == plan['files_sha256'] and before.get(PRODUCER) == PRODUCER_SHA
        and before.get(RENDERER) == plan['presentation_renderer_sha256']
        and before.get(str(Path(__file__).relative_to(ROOT))) == sha(__file__)
        and all(before.get(p) == h for p,h in plan['runtime_sha256'].items()), 'A source/input/runtime changed')
    old=(ROOT/PRODUCER).read_text();new=(ROOT/RENDERER).read_text()
    require(new.count('top=.75,bottom=.31,wspace=.2') == 1
        and new.replace('top=.75,bottom=.31,wspace=.2','top=.75,bottom=.25,wspace=.2',1) == old,
        'Presentation must differ by the single bottom-margin literal only')
    return before

def run(plan_path, expected, output):
    plan_path=Path(plan_path);require(sha(plan_path)==expected, 'Actual draw plan hash required')
    plan=json.loads(plan_path.read_text())
    require(plan['launch_ready'] is True and plan['root_GO_sha256'] is not None, 'NON-ARMED: no drawing')
    require(sha(plan['root_GO'])==plan['root_GO_sha256'], 'Actual draw GO differs')
    require(plan['inner_wall_seconds']==95 and plan['outer_wall_seconds']==120 and plan['CPU_seconds']==[90,100]
        and plan['workers']==0 and plan['threads']==1 and plan['nice']==10, 'Owned draw bounds differ')
    require(Path(output).absolute()==(ROOT/plan['output_directory']).absolute(), 'Unexpected presentation output')
    before=verify_sources(plan)
    original=load(ROOT/PRODUCER,'_frozen003_native_section_authority')
    original.closed_extraction(plan)
    presentation=load(ROOT/RENDERER,'_presentation004_original_profiles')
    presentation.render(plan['data'],plan['data_sha256'],output,plan['runtime_sha256'])
    require(before=={p:sha(ROOT/p)for p in before} and sha(plan_path)==expected, 'Source/input/runtime/plan changed')
    original.write(Path(output)/'presentation-binding-receipt.json',dict(
        status='rendered_presentation004_from_closed_original003_extraction',
        extraction_producer=PRODUCER,extraction_producer_sha256=PRODUCER_SHA,
        presentation_renderer=RENDERER,presentation_renderer_sha256=before[RENDERER],
        data_sha256=plan['data_sha256'],extraction_receipt_sha256=plan['extraction_receipt_sha256'],
        extraction_supervision_sha256=plan['extraction_supervision_sha256'],
        render_receipt_sha256=sha(Path(output)/'render-receipt.json'),plan_sha256=expected,
        sources_before=before,sources_after={p:sha(ROOT/p)for p in before},
        single_layout_literal_changed=True,no_native_extraction=True,no_geometry_modified=True,no_FEA=True))

if __name__=='__main__':
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OSD_NUM_THREADS']:os.environ[name]='1'
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Bounded presentation draw wall cap')))
    signal.setitimer(signal.ITIMER_REAL,95);resource.setrlimit(resource.RLIMIT_CPU,(90,100))
    require(len(sys.argv)==4,'Use draw_only PLAN SHA FRESH_DIR')
    run(*sys.argv[1:])
