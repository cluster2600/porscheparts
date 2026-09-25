#!/bin/sh
# Requires an already-armed external billing guard and an owned rental.
set -eu
cd /workspace/m64-g9
test ! -e venv
python3 -m venv venv
timeout 300 venv/bin/pip install --disable-pip-version-check \
  numpy==2.2.6 scipy==1.14.1 cupy-cuda12x==13.6.0 fastrlock==0.8.3 gmsh==4.12.1 \
  nvidia-cuda-runtime-cu12==12.8.90 nvidia-cuda-nvrtc-cu12==12.8.93 \
  nvidia-cublas-cu12==12.8.4.1 nvidia-cusparse-cu12==12.5.8.93 \
  nvidia-nvjitlink-cu12==12.8.93 nvidia-cuda-cccl-cu12==12.8.90
venv/bin/pip freeze > environment.txt
runtime_site=$(venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export LD_LIBRARY_PATH="$runtime_site/nvidia/cuda_runtime/lib:$runtime_site/nvidia/cuda_nvrtc/lib:$runtime_site/nvidia/cublas/lib:$runtime_site/nvidia/cusparse/lib:$runtime_site/nvidia/nvjitlink/lib"
export CUDA_PATH="$runtime_site/nvidia/cuda_runtime"
export PATH="/workspace/m64-g9/bin:$PATH"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
venv/bin/python tests/test_m64_g9_reference_campaign.py -v
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > hardware.csv
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,power.draw --format=csv -l 2 > gpu-activity.csv &
monitor_pid=$!
trap 'kill "$monitor_pid" 2>/dev/null || true' EXIT HUP INT TERM
timeout 7200 venv/bin/python twins/m64-cylinder-head/source/fourvalve/g9_reference_campaign.py \
  --legacy work/m64-g8-pilot/native --cad work/m64-g7-final --output results --backend cuda
