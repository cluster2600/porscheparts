#!/bin/bash
# Disposable, owned Linux node only; independent billing guard is mandatory.
set -euo pipefail
cd /workspace/m64-wholebody
test ! -e results
mkdir results
sha256sum -c input-checksums.txt > results/input-verification.txt
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv > results/gpu.csv
lscpu > results/cpu.txt
head -3 /proc/meminfo > results/memory.txt
if test -f /sys/fs/cgroup/memory.max; then head -1 /sys/fs/cgroup/memory.max >> results/memory.txt; fi
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1
python=/opt/venv/bin/python
source_root=source
"$python" -m pip freeze > results/environment.txt
bop_status=0
timeout --kill-after=15 330 "$python" "$source_root/wholebody/audit_native_bop.py" \
  --input input/candidate.brep \
  --sha256 b2b48fe40edd1a20c8e6c0d20d77e6045931189f18330b441b09bcbf4618fc0a \
  --output results/bop.json > results/bop.log 2>&1 || bop_status=$?
printf '%s\n' "$bop_status" > results/bop.exit
# Import/topology gates are compulsory before volume meshing, not before the
# independent surface-library diagnostic. A valid tessellation is not a CFD mesh.
timeout --kill-after=15 300 "$python" "$source_root/wholebody/audit_surface_gpu.py" \
  --mesh input/surface.npz --sha256 9660e54dc3215bbdfd2a2710fff4108e65b2447d5642a0e583c06d86492281b2 \
  --output results/physicsnemo.json > results/physicsnemo.log 2>&1 &
gpu_pid=$!
if test "$bop_status" -eq 0 && "$python" -c 'import json; r=json.load(open("results/bop.json")); assert r["passed"] is True and r["inputs_unchanged"] is True'; then
  baseline_status=0
  timeout --kill-after=15 300 "$python" "$source_root/mesh_native_ported_head.py" \
    --mode baseline --input input/candidate.brep \
    --sha256 b2b48fe40edd1a20c8e6c0d20d77e6045931189f18330b441b09bcbf4618fc0a \
    --output results/baseline > results/baseline.log 2>&1 || baseline_status=$?
  printf '%s\n' "$baseline_status" > results/baseline.exit
  if test "$baseline_status" -eq 0; then
  for algorithm in 1 10; do
    status=0
    timeout --kill-after=15 600 "$python" "$source_root/mesh_native_ported_head.py" \
      --mode mesh --input input/candidate.brep \
      --sha256 b2b48fe40edd1a20c8e6c0d20d77e6045931189f18330b441b09bcbf4618fc0a \
      --baseline results/baseline/native-baseline.json --output "results/mesh-$algorithm" \
      --minimum 1 --maximum 6 --volume-algorithm "$algorithm" > "results/mesh-$algorithm.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "results/mesh-$algorithm.exit"
  done
  else
    printf '%s\n' 'Native baseline failed; volume meshing not launched.' > results/mesh-blocked.txt
  fi
else
  printf '%s\n' 'BOP rejected or incomplete; volume meshing not launched.' > results/mesh-blocked.txt
fi
gpu_status=0
wait "$gpu_pid" || gpu_status=$?
printf '%s\n' "$gpu_status" > results/physicsnemo.exit
sha256sum -c input-checksums.txt > results/input-reverification.txt
printf '%s\n' 'Diagnostics finished; inspect each verdict. No manufacturing approval.'
