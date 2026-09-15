#!/usr/bin/env bash
# Noeud LLM : vLLM sur 127.0.0.1:8000, poids publics a revision epinglee, aucun jeton.
set -euo pipefail
MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
REVISION=dcaee4d4dfc5ee71ad501f01f530e5652438fde0
rm -f /workspace/READY
mkdir -p /workspace/logs
nohup vllm serve "$MODEL" --revision "$REVISION" --served-model-name "$MODEL" \
  --host 127.0.0.1 --port 8000 --max-model-len 65536 --max-num-seqs 64 \
  --gpu-memory-utilization 0.92 --enable-prefix-caching \
  > /workspace/logs/vllm.log 2>&1 &
for _ in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:8000/v1/models | grep -q "$MODEL"; then
    touch /workspace/READY
    exit 0
  fi
  sleep 10
done
echo "vllm_not_ready_after_30min" >&2
exit 1
