#!/bin/bash
# Run only on an owned instance with an independently armed billing guard.
set -euo pipefail
cd /workspace/m64-g11
deadline=${1:?Pass the computation deadline, before collection and guard cleanup}
[[ "$deadline" =~ ^[0-9]+$ ]]
test "$((deadline - $(date +%s)))" -gt 1800
test ! -f /workspace/UNEXPECTED_LISTENER
test ! -e venv
sha256sum -c input-checksums.txt
tar -xzf inputs.tgz
mkdir ccx-runtime
tar -xzf ccx-runtime.tgz -C ccx-runtime
# The smaller approved PicoGK runtime needs these Gmsh shared libraries.
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
venv/bin/python -m unittest discover -s tests -p test_m64_g11_campaign.py -v > tests.log 2>&1
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,power.draw --format=csv -l 2 > telemetry.csv &
telemetry_pid=$!
trap 'kill "$telemetry_pid" 2>/dev/null || true' EXIT
remaining=$((deadline - $(date +%s)))
test "$remaining" -gt 1200
timeout --signal=TERM --kill-after=30 "$remaining" venv/bin/python -u \
  twins/m64-cylinder-head/source/fourvalve/g11_campaign.py \
  --cad work/m64-g11/cad-v2/receipt.json --output results --backend cuda \
  --deadline "$deadline" --case-timeout 900 --reserve-seconds 180
