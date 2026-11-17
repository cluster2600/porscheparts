#!/usr/bin/env bash
# Node B bring-up, run as root on the rented VM by `vast_deploy.sh up` (over SSH, after the inputs
# are copied). Order matters: the dead-man switch first, results home after every step.
#
# Reads /root/session/session.env, written by vast_deploy.sh:
#   DEADLINE_EPOCH  SESSION  REPO_URL  REPO_COMMIT  LLM_SSH_HOST  LLM_SSH_PORT  VLLM_API_KEY
#   OPENCLAW_GATEWAY_TOKEN  OPENCLAW_VERSION  [RCLONE_REMOTE]
set -euo pipefail
. /root/session/session.env
: "${DEADLINE_EPOCH:?}" "${SESSION:?}" "${REPO_URL:?}" "${REPO_COMMIT:?}" "${LLM_SSH_HOST:?}" "${LLM_SSH_PORT:?}"
W=/workspace; mkdir -p $W/logs $W/work $W/scan $W/jobs
exec > >(tee -a $W/logs/onstart-cae.log) 2>&1
echo "== onstart-cae $(date -u +%FT%TZ) session $SESSION"

# 1. Dead-man switch. On a Vast VM an in-guest shutdown stops GPU billing (storage still bills);
#    the per-instance key, when the VM has one, then destroys it outright.
minutes=$(( (DEADLINE_EPOCH - $(date +%s)) / 60 ))
[ "$minutes" -gt 5 ] || { echo "deadline already too close: $minutes min"; exit 1; }
shutdown -h "+$minutes" "porscheparts 935 session $SESSION deadline"
if [ -n "${CONTAINER_API_KEY:-}" ] && [ -n "${CONTAINER_ID:-}" ]; then
  pip3 install --quiet vastai==1.11.0 || true
  nohup setsid bash -c "while [ \$(date +%s) -lt $((DEADLINE_EPOCH - 120)) ]; do sleep 30; done; \
    $W/repo/deploy/vast/935-twin-openclaw/sync-hook.sh || true; \
    vastai destroy instance $CONTAINER_ID -y --api-key $CONTAINER_API_KEY" >> $W/logs/deadman.log 2>&1 &
fi

# 2. The repository at the commit under work (public, no credential on this machine).
[ -d $W/repo/.git ] || git clone --filter=blob:none --no-checkout "$REPO_URL" $W/repo
# Always (re)applied: `vast_deploy.sh up` clones with the deploy folder only, to start this script.
git -C $W/repo sparse-checkout set --no-cone /AGENTS.md /docs/ /deploy/vast/935-twin-openclaw/ \
  /twins/935-cylinder-head-cad-twin/ /benchmarks/scan-primitive-fitting/ /benchmarks/fatigue-postprocessor/ \
  /outils/benchmarks/openfoam-poiseuille-f25/ /containers/free-tools-cloudcompare.Dockerfile /benchmarks/free-tools/ \
  /twins/engine-simulation-contracts/ /tests/test_m64_valvetrain_v1.py
git -C $W/repo fetch --depth 1 origin "$REPO_COMMIT" && git -C $W/repo checkout --detach "$REPO_COMMIT"
D=$W/repo/deploy/vast/935-twin-openclaw
chown -R 1000:1000 $W/work $W/jobs

# 3. Tunnel to Node A's vLLM, restarted if it drops. The key may only forward to 127.0.0.1:8000.
cat > /etc/systemd/system/vllm-tunnel.service <<EOF
[Unit]
Description=SSH tunnel to Node A vLLM
After=network-online.target
[Service]
ExecStart=/usr/bin/ssh -N -i /root/session/tunnel_key -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -o StrictHostKeyChecking=accept-new -p $LLM_SSH_PORT -L 127.0.0.1:8000:127.0.0.1:8000 root@$LLM_SSH_HOST
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now vllm-tunnel.service

# 4. Tool images, then the smoke check on this GPU. The smoke's receipt goes home before anything else.
cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d .)
cat > $D/.env <<EOF
REPO_DIR=$W/repo
WORK_DIR=$W/work
SCAN_DIR=$W/scan
CUDA_ARCH=$cap
EOF
( cd $D && docker compose build cae openfoam cloudcompare ) 2>&1 | tee $W/logs/build.log
docker image inspect porscheparts/cae-935:dev --format '{{.Id}}' > $W/work/receipts-image-id.txt
( cd $D && docker compose run --rm cae ) 2>&1 | tee $W/logs/smoke.log
$D/sync-hook.sh || true

# 5. The model must answer before any agent starts.
for _ in $(seq 1 120); do
  curl -fsS -H "Authorization: Bearer $VLLM_API_KEY" http://127.0.0.1:8000/v1/models | grep -q nemotron && break
  sleep 15
done
curl -fsS -H "Authorization: Bearer $VLLM_API_KEY" http://127.0.0.1:8000/v1/models | grep -q nemotron

# 6. OpenClaw for an unprivileged user, gateway on loopback only. Node from the official tarball,
#    checked against the published SHASUMS256.
id agent >/dev/null 2>&1 || useradd -m -s /bin/bash agent
usermod -aG docker agent      # the sandbox backend starts containers; agents themselves get no socket
NODE_DIR=/opt/node
if [ ! -x $NODE_DIR/bin/node ]; then
  base=https://nodejs.org/dist/latest-v24.x
  file=$(curl -fsS $base/SHASUMS256.txt | awk '/linux-x64.tar.xz$/ {print $2}')
  curl -fsSO "$base/$file" && curl -fsS "$base/SHASUMS256.txt" | grep " $file\$" | sha256sum -c -
  mkdir -p $NODE_DIR && tar -xJf "$file" -C $NODE_DIR --strip-components 1 && rm -f "$file"
fi
sudo -u agent -H bash -lc "export PATH=$NODE_DIR/bin:\$PATH; npm install -g --prefix ~/.npm-global openclaw@${OPENCLAW_VERSION:-2026.11.4}"
A=/home/agent
sudo -u agent mkdir -p $A/.openclaw
for ag in orchestrator cad-geometry am-print engine-sim visual-qa; do
  sudo -u agent mkdir -p $A/.openclaw/workspace-$ag
  sudo -u agent cp $D/openclaw/agents/AGENTS.md $A/.openclaw/workspace-$ag/AGENTS.md
done
install -o agent -g agent -m 600 $D/openclaw/openclaw.json $A/.openclaw/openclaw.json
install -o agent -g agent -m 600 /dev/null $A/.openclaw/env
printf 'VLLM_API_KEY=%s\nOPENCLAW_GATEWAY_TOKEN=%s\nTWIN_WORK=%s\nTWIN_REPO=%s\nTWIN_SCAN=%s\nTWIN_JOBS=%s\n' \
  "$VLLM_API_KEY" "$OPENCLAW_GATEWAY_TOKEN" $W/work $W/repo $W/scan $W/jobs > $A/.openclaw/env

cat > /etc/systemd/system/openclaw-gateway.service <<EOF
[Unit]
Description=OpenClaw gateway (loopback only)
After=vllm-tunnel.service docker.service
[Service]
User=agent
EnvironmentFile=$A/.openclaw/env
Environment=PATH=$A/.npm-global/bin:$NODE_DIR/bin:/usr/bin:/bin
ExecStart=$A/.npm-global/bin/openclaw gateway run --bind loopback --port 18789
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/twin-jobrunner.service <<EOF
[Unit]
Description=935 twin job runner (agents' only path to tool images)
After=docker.service
[Service]
Environment=MAX_TIMEOUT=21600
ExecStart=$D/jobrunner.sh $W/jobs $D/docker-compose.yml
Restart=always
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now twin-jobrunner.service openclaw-gateway.service
sudo -u agent -H bash -lc "export PATH=$A/.npm-global/bin:$NODE_DIR/bin:\$PATH; set -a; . $A/.openclaw/env; openclaw doctor; openclaw security audit" \
  | tee $W/logs/openclaw-audit.log || true
$D/sync-hook.sh || true
echo "== Node B ready $(date -u +%FT%TZ): dashboard on 127.0.0.1:18789 (forward it over SSH)"
