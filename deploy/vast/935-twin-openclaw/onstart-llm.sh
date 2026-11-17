#!/usr/bin/env bash
# Node A on-start (vllm/vllm-openai image): arm the dead-man switch, then serve Nemotron 3.5 Super VL
# on 127.0.0.1:8000 only. Node B reaches it through an SSH tunnel; nothing listens publicly.
#
# Environment (passed by vast_deploy.sh with --env):
#   DEADLINE_EPOCH   UTC epoch at which this instance destroys itself, whatever else happens
#   VLLM_API_KEY     random per session; also required by the tunnel's client
#   MAX_MODEL_LEN    default 1048576 (the model card's 1M); lower it if KV memory does not fit 128 seqs
#   TUNNEL_PUBKEY_B64  the session's public key, base64 (Vast's --env splits on spaces); the only
#                      key that may open the tunnel
set -euo pipefail
MODEL=nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4
REVISION=3acb09951cff50cda7be0200ebbad2c15a3e63ba      # model repo head on 2026-11-16 (licence OpenMDW-1.1)
mkdir -p /workspace/logs
rm -f /workspace/READY

# 1. Dead-man switch first: it survives the owner's PC sleeping. The per-instance key Vast injects
#    (CONTAINER_API_KEY) may only start, stop or destroy this instance.
pip install --quiet vastai==1.11.0 >/workspace/logs/vastai-install.log 2>&1 || true
cat > /workspace/deadman.sh <<'EOF'
#!/usr/bin/env bash
while [ "$(date +%s)" -lt "$DEADLINE_EPOCH" ]; do sleep 30; done
echo "deadline reached $(date -u +%FT%TZ)" >> /workspace/logs/deadman.log
if [ -n "${CONTAINER_API_KEY:-}" ] && [ -n "${CONTAINER_ID:-}" ]; then
  vastai destroy instance "$CONTAINER_ID" -y --api-key "$CONTAINER_API_KEY" >> /workspace/logs/deadman.log 2>&1 \
    || python3 -c "import os, urllib.request as u; u.urlopen(u.Request('https://console.vast.ai/api/v0/instances/%s/' % os.environ['CONTAINER_ID'], method='DELETE', headers={'Authorization': 'Bearer ' + os.environ['CONTAINER_API_KEY']}), timeout=60)" >> /workspace/logs/deadman.log 2>&1
fi
# Last resort: stop the container. A stopped container is not proof that billing ended; the local
# guard and `vast_deploy.sh down` still check that the instance is gone.
kill -9 1
EOF
chmod +x /workspace/deadman.sh
: "${DEADLINE_EPOCH:?}" "${VLLM_API_KEY:?}" "${TUNNEL_PUBKEY_B64:?}"
[ -n "${CONTAINER_API_KEY:-}" ] || echo "no CONTAINER_API_KEY: the dead-man switch can only stop the container" >> /workspace/logs/deadman.log
nohup setsid /workspace/deadman.sh >/dev/null 2>&1 &

# 2. The tunnel key: port forwarding to 127.0.0.1:8000 only, no shell, no other forward.
mkdir -p /root/.ssh && chmod 700 /root/.ssh
printf 'restrict,port-forwarding,permitopen="127.0.0.1:8000",command="/bin/false" %s\n' "$(echo "$TUNNEL_PUBKEY_B64" | base64 -d)" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# 3. vLLM: the model card's 1x H200 command (2x H100: --tensor-parallel-size 2), bound to loopback,
#    with an API key, a pinned revision, and prefix caching stated explicitly.
TP=$(nvidia-smi -L | wc -l)
nohup vllm serve "$MODEL" --revision "$REVISION" \
  --served-model-name nemotron-3.5-super-vl \
  --host 127.0.0.1 --port 8000 --api-key "$VLLM_API_KEY" \
  --tensor-parallel-size "$TP" \
  --max-model-len "${MAX_MODEL_LEN:-1048576}" \
  --max-num-seqs 128 \
  --enable-prefix-caching \
  --trust-remote-code \
  --gpu-memory-utilization 0.89 \
  --max-num-batched-tokens 16384 \
  --block-size 64 \
  --prefix-match-unit 64 \
  --compilation_config.max_cudagraph_capture_size 256 \
  --mamba-backend flashinfer \
  --mamba-ssm-cache-dtype float16 \
  --enable-mamba-cache-stochastic-rounding \
  --mamba-cache-philox-rounds 5 \
  --enable-mamba-shared-prefix-checkpoint \
  --mamba-cache-mode align \
  --speculative-config.method mtp \
  --speculative-config.num_speculative_tokens 3 \
  --limit-mm-per-prompt '{"image": 8, "video": 0}' \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser nemotron_v3 \
  > /workspace/logs/vllm.log 2>&1 &

for _ in $(seq 1 180); do
  if python3 -c "import os, urllib.request as u; r = u.urlopen(u.Request('http://127.0.0.1:8000/v1/models', headers={'Authorization': 'Bearer ' + os.environ['VLLM_API_KEY']}), timeout=10); assert b'nemotron-3.5-super-vl' in r.read()" 2>/dev/null; then
    touch /workspace/READY; exit 0
  fi
  sleep 10
done
echo "vllm_not_ready_after_30min" | tee -a /workspace/logs/deadman.log >&2
exit 1
