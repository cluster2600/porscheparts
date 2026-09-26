#!/bin/bash
# PRIVATE diagnostic only. Root must first verify the original collected archive.
# Launch with: setsid bash /workspace/g12_equilibrium_audit.sh
# Existing independent rental guard remains authoritative; no lease extension.
set -euo pipefail
umask 077
cd /workspace/m64-g11
audit_root=/workspace/m64-g12-equilibrium-audit
mkdir -m 700 "$audit_root"
mkdir "$audit_root/results" "$audit_root/results/provenance"
cp -- "${BASH_SOURCE[0]}" "$audit_root/results/provenance/g12_equilibrium_audit.sh"
runtime_site=$(venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export LD_LIBRARY_PATH="$runtime_site/nvidia/cuda_runtime/lib:$runtime_site/nvidia/cuda_nvrtc/lib:$runtime_site/nvidia/cublas/lib:$runtime_site/nvidia/cusparse/lib:$runtime_site/nvidia/nvjitlink/lib"
export CUDA_PATH="$runtime_site/nvidia/cuda_runtime"
export PATH="/workspace/m64-g11/bin:$PATH"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
set +e
timeout --signal=TERM --kill-after=15 300 venv/bin/python -u - >"$audit_root/results/diagnostic.log" 2>&1 <<'PY'
import json, signal, shutil, sys, time
from pathlib import Path
import hashlib
root = Path('/workspace/m64-g12-equilibrium-audit/results')
source = Path('/workspace/m64-g11')
folder = source/'twins/m64-cylinder-head/source/fourvalve'
original = source/'results/centre_w11_local28_foot30_h50-1.5-attempt1'
case = root/'centre_w11_local28_foot30_h50-1.5-diagnostic'
pins = {'x.inp': 'd51f1343152d49bafef796cd257210c82dd6dc891df7d29e898528a0c9b94c84',
        'x.dat': 'b44e5f0916dec97181ba6d1e0f799757ec67b0a418693b1ee731a2afd823e520',
        'minus_z.inp': 'd5e2d625ec1f65f56e9a0f8896a43505ccec1a474f887dfd2400dc96bb09dc08',
        'minus_z.dat': '88cedaec685532ed97aa50e697f4f3987635251c5970f32b1edc6bf19fabe703'}
sources = {folder/'g8_pilot.py': 'f6f3d1fe77c0a701bb1f75926cd4ac8cba3ee6cc9c3337967740d30ad85fee92',
           folder/'g9_reference_campaign.py': 'ed6a2b21d89030ba39fc393f8a218bbbf328eceda49ce6bed361273bd2d8170b',
           folder/'g8_matrix_benchmark.py': '4a98a110df2c4698b3ac0a74fb0dd1cb200c946fd9fa9a8748f6bd0e10c981cd',
           folder/'g8_iterative_retry.py': '8600f234e60036668dc3a8f7f005c570638ea4cfc7a60c1327b86a534fa01963',
           source/'twins/reference-917-engine/source/run_f37_carrier_calculix.py': '54e3478e219875872092cacb281dd12e640126cbed9273e8d82cd46d36fa2b13'}
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def interrupted(signum, frame):
    raise TimeoutError('external bounded diagnostic interrupted')
signal.signal(signal.SIGTERM, interrupted)
report = dict(classification='failed_G12_DAT_vs_fresh_K_CUDA_diagnostic_not_replacement',
              original_failure_preserved=True, manufacturing_authorized=False,
              engine_start_authorized=False, diagnostic_rows_complete=False,
              original_input_sha256=pins, source_sha256={str(p.relative_to(source)): h for p,h in sources.items()},
              started_epoch=time.time(), rows=[], error=None)
status = 2
try:
    for path, expected in sources.items():
        if sha(path) != expected:
            raise ValueError('frozen source mismatch: '+path.name)
    for name, expected in pins.items():
        if sha(original/name) != expected:
            raise ValueError('original file mismatch: '+name)
    case.mkdir()
    for name, expected in pins.items():
        shutil.copyfile(original/name, case/name)
        if sha(case/name) != expected:
            raise ValueError('copied file mismatch: '+name)
    sys.path.insert(0, str(folder))
    import g9_reference_campaign as g9
    if any((case.name,n) in g9.HISTORICAL for n in ('x','minus_z')):
        raise ValueError('diagnostic aliases historical evidence')
    # Frozen audit is fail-fast. An unexpected +x failure leaves this incomplete.
    report['rows'] = g9.audit(case, ('x','minus_z'), root, 'cuda')
    report['diagnostic_rows_complete'] = len(report['rows']) == 2
    status = 0 if report['diagnostic_rows_complete'] else 2
except BaseException as exc:
    report['error'] = type(exc).__name__+': '+str(exc)
finally:
    report['finished_epoch'] = time.time()
    with (root/'diagnostic.json').open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
print(json.dumps({'diagnostic_rows_complete':report['diagnostic_rows_complete'],'error':report['error']}),flush=True)
raise SystemExit(status)
PY
job_status=$?
set -e
# Runs after timeout/worker termination, never upgrades the original failed case.
venv/bin/python - "$job_status" <<'PY'
import hashlib, json, sys, time
from pathlib import Path
root=Path('/workspace/m64-g12-equilibrium-audit/results')
files={}
for path in sorted(root.rglob('*')):
    if path.is_file():
        with path.open('rb') as stream:
            files[str(path.relative_to(root))]={'bytes':path.stat().st_size,'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}
receipt={'classification':'diagnostic_execution_receipt_only','worker_exit_code':int(sys.argv[1]),
         'worker_external_timeout_seconds':300,'kill_grace_seconds':15,'finished_epoch':time.time(),
         'original_failure_preserved':True,'manufacturing_authorized':False,'artifacts':files}
with (root/'execution.json').open('x') as stream:
    json.dump(receipt,stream,indent=2,allow_nan=False)
print(json.dumps({'worker_exit_code':receipt['worker_exit_code'],'artifacts':len(files)}))
PY
exit "$job_status"
