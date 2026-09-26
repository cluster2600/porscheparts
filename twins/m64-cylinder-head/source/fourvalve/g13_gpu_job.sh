#!/bin/bash
# G13 reference repair, then CAD screening; independent billing guard required.
set -euo pipefail
cd /workspace/m64-g11
deadline=${1:?Pass compute deadline before collection and billing cleanup}
[[ "$deadline" =~ ^[0-9]+$ ]]
test "$((deadline - $(date +%s)))" -gt 1800
test ! -f /workspace/UNEXPECTED_LISTENER
test ! -e venv
sha256sum -c input-checksums.txt
tar -xzf inputs.tgz
mkdir ccx-runtime
tar -xzf ccx-runtime.tgz -C ccx-runtime
timeout 120 apt-get update
timeout 120 env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libglu1-mesa libxft2 libxrender1
dpkg-query -W libglu1-mesa libxft2 libxrender1 > gmsh-native-packages.txt
python3 -m venv venv
timeout 300 venv/bin/pip install --disable-pip-version-check \
  numpy==2.2.6 scipy==1.14.1 cupy-cuda12x==13.6.0 fastrlock==0.8.3 gmsh==4.12.1 \
  nvidia-cuda-runtime-cu12==12.8.90 nvidia-cuda-nvrtc-cu12==12.8.93 \
  nvidia-cublas-cu12==12.8.4.1 nvidia-cusparse-cu12==12.5.8.93 \
  nvidia-nvjitlink-cu12==12.8.93 nvidia-cuda-cccl-cu12==12.8.90
runtime_site=$(venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export LD_LIBRARY_PATH="$runtime_site/nvidia/cuda_runtime/lib:$runtime_site/nvidia/cuda_nvrtc/lib:$runtime_site/nvidia/cublas/lib:$runtime_site/nvidia/cusparse/lib:$runtime_site/nvidia/nvjitlink/lib"
export CUDA_PATH="$runtime_site/nvidia/cuda_runtime"
export PATH="/workspace/m64-g11/bin:$PATH"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
ccx -v > ccx-version.txt 2>&1 || test "$?" -eq 201
grep -q 'Version 2.21' ccx-version.txt
venv/bin/pip freeze > environment.txt
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv > hardware-gpu.csv
lscpu > hardware-cpu.txt
free -b > hardware-memory.txt
venv/bin/python -c 'import gmsh, cupy; from cupyx.scipy.sparse import eye; from cupyx.scipy.sparse.linalg import cg; a=eye(4,dtype=cupy.float64,format="csr"); x,status=cg(a,cupy.ones(4,dtype=cupy.float64)); assert status==0 and float(cupy.linalg.norm(x-1))<1e-12; gmsh.initialize(); gmsh.finalize(); print(gmsh.__version__,cupy.__version__)' > preflight.txt
venv/bin/python -m unittest discover -s tests -p 'test_m64_g13_*.py' -v > tests.log 2>&1
test ! -e results
mkdir -p results/provenance
cp -- "${BASH_SOURCE[0]}" results/provenance/g13_gpu_job.sh
cp -- serial-bin/ccx results/provenance/ccx-serial-v1
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,power.draw --format=csv -l 2 > telemetry.csv &
telemetry_pid=$!
trap 'kill "$telemetry_pid" 2>/dev/null || true; wait "$telemetry_pid" 2>/dev/null || true' EXIT
reference_status=0
remaining=$((deadline - $(date +%s)))
test "$remaining" -gt 60
timeout --signal=TERM --kill-after=30 "$remaining" venv/bin/python -u twins/m64-cylinder-head/source/fourvalve/g13_reference.py \
  --input reference-input --output results/g13-reference --deadline "$deadline" \
  --case-timeout 900 || reference_status=$?
# A normal diagnostic return may reject physics. Crashes cannot declare quiescence.
test "$reference_status" -eq 0 -o "$reference_status" -eq 2
cp results/g13-reference/summary-0001.json results/summary-0001.json
if venv/bin/python -c 'import json,sys; r=json.load(open("results/summary-0001.json")); serial=[v for v in r["rows"] if v["threads"]==1]; sys.exit(0 if r["complete"] is True and r["error"] is None and len(serial)==3 and all(v["passed"] is True for v in serial) else 1)'; then
  export PATH="/workspace/m64-g11/serial-bin:$PATH"
  remaining=$((deadline - $(date +%s)))
  test "$remaining" -gt 60
  timeout --signal=TERM --kill-after=30 "$remaining" venv/bin/python -u twins/m64-cylinder-head/source/fourvalve/g13_campaign.py \
    --cad work/m64-g13/cad/receipt.json \
    --outer-cad work/m64-g11/cad-v2/receipt.json \
    --reference results/g13-reference/summary-0001.json \
    --ccx-wrapper serial-bin/ccx --ccx-binary ccx-runtime/usr/bin/ccx \
    --deadline "$deadline" --case-timeout 1800 --output results/g13-campaign \
    --snapshots results --backend cuda
fi
