#!/bin/bash
set -euo pipefail
cd /workspace/m64-g10
test ! -f /workspace/UNEXPECTED_LISTENER
test ! -e output
sha256sum -c archive-checksums.txt
tar -xzf source.tgz
tar -xzf g8-receipt.tgz
tar -xzf first-results.tgz results/carrier_base_p-2.0
tar -xzf final-results.tgz results-final/carrier_base_p-1.5
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
/opt/venv/bin/python -m pip install --no-deps --no-cache-dir --target /workspace/m64-g10/cuda-extra cupy-cuda12x==13.6.0 fastrlock==0.8.3 > cupy-install.log 2>&1
export PYTHONPATH=/workspace/m64-g10/cuda-extra
export LD_LIBRARY_PATH=/opt/venv/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:/opt/venv/lib/python3.12/site-packages/nvidia/cuda_nvrtc/lib:/opt/venv/lib/python3.12/site-packages/nvidia/nvjitlink/lib:/opt/venv/lib/python3.12/site-packages/nvidia/cublas/lib:/opt/venv/lib/python3.12/site-packages/nvidia/cusparse/lib:${LD_LIBRARY_PATH:-}
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv > hardware-gpu.csv
lscpu > hardware-cpu.txt
free -b > hardware-memory.txt
/opt/venv/bin/python -m pip freeze > environment.txt
/opt/venv/bin/python -c 'import torch,physicsnemo,cupy; from physicsnemo.models.mlp import FullyConnected; assert physicsnemo.__version__=="2.2.0"; assert torch.cuda.is_available(); m=FullyConnected(in_features=3,out_features=6,layer_size=128,num_layers=4).cuda(); m(torch.ones((2,3),device="cuda")).sum().backward(); assert cupy.linalg.norm(cupy.ones(3))>0; print(torch.__version__,physicsnemo.__version__,cupy.__version__,torch.cuda.get_device_name(0))' > preflight.txt
/opt/venv/bin/python -m unittest discover -s tests -p test_m64_g10_physicsnemo_field.py -v > tests.log 2>&1
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,power.draw --format=csv -l 2 > telemetry.csv &
telemetry_pid=$!
trap 'kill "$telemetry_pid" 2>/dev/null || true' EXIT
timeout --signal=TERM --kill-after=20 1800 /opt/venv/bin/python -u twins/m64-cylinder-head/source/fourvalve/g10_physicsnemo_field.py --train results/carrier_base_p-2.0 --test results-final/carrier_base_p-1.5 --campaign twins/m64-cylinder-head/evidence/g9-reference-requalification-20260925/campaign.json --out output
