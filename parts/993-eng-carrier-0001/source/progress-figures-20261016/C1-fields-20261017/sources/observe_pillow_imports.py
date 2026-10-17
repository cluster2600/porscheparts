"""Import-only observation of existing Pillow preinit; no image open/save/render."""
import hashlib,json,os
from pathlib import Path
import resource,signal,sys,time
HERE=Path(__file__).resolve().parent
resource.setrlimit(resource.RLIMIT_CPU,(5,6));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('10s import-only observation')));signal.setitimer(signal.ITIMER_REAL,10)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
original=json.loads((HERE/'payload/work/carrier-process-20261017/bounded-webs-C1-fields-figure-preparation-001/plan-002.json').read_text())
started=time.monotonic()
from PIL import Image
import PIL
before={str(Path(m.__file__).resolve()):sha(m.__file__)for n,m in list(sys.modules.items())if n.split('.')[0]=='PIL'and getattr(m,'__file__',None)and Path(m.__file__).is_file()}
Image.preinit()
after={str(Path(m.__file__).resolve()):sha(m.__file__)for n,m in list(sys.modules.items())if n.split('.')[0]=='PIL'and getattr(m,'__file__',None)and Path(m.__file__).is_file()}
extra={p:h for p,h in after.items()if p not in original['runtime_sha256']}
assert all(sha(p)==h for p,h in before.items())
report=dict(status='existing_Pillow_preinit_imports_observed_NO_image_or_render',python=sys.version,python_executable=str(Path(sys.executable).resolve()),Pillow_version=PIL.__version__,source_sha256=sha(__file__),Image_source_sha256=sha(Image.__file__),operation='Image.preinit()',modules_before=before,modules_after=after,additional_to_frozen211=extra,runtime_before_after_unchanged=True,image_opened=False,image_saved=False,render_executed=False,CAD_mesh_FEA_called=False,wall_seconds=time.monotonic()-started)
with(HERE/'pillow-preinit-import-observation.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(status=report['status'],additional_to_frozen211=extra,receipt_sha256=sha(HERE/'pillow-preinit-import-observation.json'))),flush=True)
