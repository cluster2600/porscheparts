#!/bin/sh
# Explicit G13 runtime policy: override the frozen helpers' four-thread settings.
set -eu
export OMP_NUM_THREADS=1 CCX_NPROC_EQUATION_SOLVER=1 CCX_NPROC_STIFFNESS=1 CCX_NPROC_RESULTS=1 NUMBER_OF_CPUS=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
runtime=/workspace/m64-g11/ccx-runtime
exec "$runtime/lib64/ld-linux-x86-64.so.2" --library-path "$runtime/lib/x86_64-linux-gnu" "$runtime/usr/bin/ccx" "$@"
