#!/bin/sh
set -eu
# The scoped OpenBao deployment hook writes this runtime-only token over SSH.
# Read it only in the Qwen process, never in supervisor or the Kit environment.
token_file=/run/station-secrets/hf_token
if [ -e "$token_file" ] || [ -L "$token_file" ]; then
    test "$(id -u)" -eq 0
    test -d /run/station-secrets && test ! -L /run/station-secrets
    test "$(stat -c '%u:%g:%a' /run/station-secrets)" = 0:0:700
    test -f "$token_file" && test ! -L "$token_file"
    test "$(stat -c '%u:%g:%a' "$token_file")" = 0:0:600
    HF_TOKEN=$(cat "$token_file")
    export HF_TOKEN
fi
export CUDA_VISIBLE_DEVICES=0,1
export MAX_MODEL_LEN=262144 MAX_NUM_SEQS=4 TENSOR_PARALLEL_SIZE=2 DATA_PARALLEL_SIZE=1
export MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306
exec /opt/qwen/start.sh
