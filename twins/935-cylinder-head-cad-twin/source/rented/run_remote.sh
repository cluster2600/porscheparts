#!/usr/bin/env bash
# Runs on the rented machine, inside the pinned DOLFINx image (the instance image itself).
# Layout: /root/src/build_sim_dolfinx.py, /root/bs/<level>/{mesh.npz,case.json,level.txt,prepare.json,thermal-end-of-lump.npy}
# Usage: run_remote.sh witness            -> /root/dx/witness/witness.json
#        run_remote.sh run LEVEL NPROC    -> /root/dx/LEVEL-blr-NPROCp/, exit code in LEVEL-blr-NPROCp.exit
set -uo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HOME=/root/dx/cache XDG_CACHE_HOME=/root/dx/cache
mkdir -p /root/dx/cache /root/dx/receipts
cd /root/dx
{
  echo "date $(date -u +%FT%TZ)"
  echo "script_sha256 $(sha256sum /root/src/build_sim_dolfinx.py | cut -d' ' -f1)"
  echo "nproc $(nproc)"; grep -m1 'model name' /proc/cpuinfo
  echo "cgroup_cpu $(cat /sys/fs/cgroup/cpu.max 2>/dev/null)"
  echo "cgroup_mem $(cat /sys/fs/cgroup/memory.max 2>/dev/null)"
  python3 -c "import dolfinx, petsc4py; print('dolfinx', dolfinx.__version__)"
  mpirun --version 2>&1 | head -2
} > "/root/dx/receipts/env-$1-${2:-}-$(date +%s).txt" 2>&1
case "$1" in
  witness)
    mkdir -p /root/dx/witness
    mpirun -n 4 python3 /root/src/build_sim_dolfinx.py witness /root/dx/witness/witness.json > /root/dx/witness.log 2>&1
    echo $? > /root/dx/witness.exit ;;
  run)
    level=$2 n=$3 name="$2-blr-$3p"
    sha256sum /root/src/build_sim_dolfinx.py > "/root/dx/$name.script.sha256"
    mpirun -n "$n" python3 /root/src/build_sim_dolfinx.py mechanics "/root/bs/$level" "/root/dx/$name" --solver blr > "/root/dx/$name.log" 2>&1
    echo $? > "/root/dx/$name.exit" ;;
  memlog)   # whole-container memory every minute: memory.current and memory.peak (cgroup v2) or v1 usage
    while true; do
      cur=$(cat /sys/fs/cgroup/memory.current 2>/dev/null || cat /sys/fs/cgroup/memory/memory.usage_in_bytes 2>/dev/null)
      peak=$(cat /sys/fs/cgroup/memory.peak 2>/dev/null || cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes 2>/dev/null)
      echo "$(date -u +%FT%TZ) current=$cur peak=$peak $(ps -eo rss,args --sort=-rss | awk '/build_sim_dolfinx/ && match($0, /\/root\/dx\/[^ ]+/) {k=substr($0, RSTART+9, RLENGTH-9); s[k]+=$1} END {for (k in s) printf "%s=%dMiB ", k, s[k]/1024}')" >> /root/dx/memlog.txt
      sleep 60
    done ;;
esac
