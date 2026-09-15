#!/usr/bin/env bash
# Noeud calcul : tunnel vers le LLM, agents CAO, puis jobs CFD/FEA.
# Arguments : LLM_SSH (user@host:port) DEADLINE_EPOCH
set -euo pipefail
LLM_SSH="$1"
DEADLINE="$2"
REPO=/workspace/repo
OUT=/workspace/out/m64-engine-twin-20260915
PARAMS="$REPO/twins/m64-cylinder-head/evidence/g1-four-valve-20260914/parameters-resolved.json"
mkdir -p "$OUT" /workspace/logs

host="${LLM_SSH%:*}"; port="${LLM_SSH##*:}"
# Cle de session ephemere, autorisee uniquement sur le noeud LLM ; jamais commitee.
ssh -i /workspace/session_key -o StrictHostKeyChecking=accept-new -o ExitOnForwardFailure=yes \
    -N -L 8000:127.0.0.1:8000 -p "$port" "$host" &
for _ in $(seq 1 30); do curl -fsS http://127.0.0.1:8000/v1/models >/dev/null && break; sleep 5; done
curl -fsS http://127.0.0.1:8000/v1/models >/dev/null

docker pull "$(python3 -c "import json;print(json.load(open('$REPO/twins/m64-engine-twin/session-20260915.json'))['nodes']['compute']['images']['cad'])")"

python3 "$REPO/twins/m64-engine-twin/source/orchestrate_agents.py" \
  --params "$PARAMS" --out "$OUT/agents" --deadline-epoch "$DEADLINE" --concurrency 32 \
  2>&1 | tee /workspace/logs/agents.log

# Jobs existants a GPU, en parallele des agents s'ils sont lances a part (voir README).
touch /workspace/DONE
