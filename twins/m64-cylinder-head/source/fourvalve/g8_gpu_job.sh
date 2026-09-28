#!/bin/sh
# Execute only inside an already guarded, uniquely owned Vast rental.
set -eu
cd /workspace/m64-g8-gpu
test ! -e bench-venv
python3 -m venv bench-venv
timeout 300 bench-venv/bin/pip install --disable-pip-version-check \
  numpy==2.2.6 scipy==1.14.1 cupy-cuda12x==13.6.0 fastrlock==0.8.3 \
  nvidia-cuda-runtime-cu12==12.8.90 nvidia-cuda-nvrtc-cu12==12.8.93 \
  nvidia-cublas-cu12==12.8.4.1 nvidia-cusparse-cu12==12.5.8.93 \
  nvidia-nvjitlink-cu12==12.8.93 nvidia-cuda-cccl-cu12==12.8.90
bench-venv/bin/pip freeze > environment.txt
bench_site=$(bench-venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export LD_LIBRARY_PATH="$bench_site/nvidia/cuda_runtime/lib:$bench_site/nvidia/cuda_nvrtc/lib:$bench_site/nvidia/cublas/lib:$bench_site/nvidia/cusparse/lib:$bench_site/nvidia/nvjitlink/lib"
export CUDA_PATH="$bench_site/nvidia/cuda_runtime"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
bench-venv/bin/python tests/test_m64_g8_matrix_benchmark.py -v
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > hardware.csv
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,power.draw --format=csv -l 1 > gpu-activity.csv &
monitor_pid=$!
trap 'kill "$monitor_pid" 2>/dev/null || true' EXIT HUP INT TERM
for backend in cpu cuda; do
  for trial in 1 2 3; do
    output="${backend}-${trial}.json"
    # Exit 1 with a written receipt means legacy-reference rejection, preserved
    # deliberately. It is NOT a successful G8 qualification.
    timeout 360 bench-venv/bin/python twins/m64-cylinder-head/source/fourvalve/g8_matrix_benchmark.py \
      work/m64-g8-pilot/native/carrier_base_p-3.0 work/m64-gpu-benchmark/coarse \
      --backend "$backend" --output "$output" \
      --comparison-dat work/m64-gpu-benchmark/kali-one.dat \
      --comparison-dat work/m64-gpu-benchmark/mac-direct/x.dat || test "$?" -eq 1
    test -s "$output"
  done
done
