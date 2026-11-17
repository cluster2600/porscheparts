#!/usr/bin/env bash
# Two-node Vast.ai session for the 935 head twin: Node A serves Nemotron 3.5 Super VL with vLLM,
# Node B runs the CAE images, the job runner and OpenClaw. Run it ATTENDED, from home (outbound SSH to
# Vast's high ports is blocked from the owner's daytime network), and never across a pause.
#
#   vast_deploy.sh preflight                      account, credit, key, tools, commit on GitHub
#   vast_deploy.sh offers                         cheapest admissible offers for both roles
#   vast_deploy.sh up OFFER_A OFFER_B INPUTS.txt  rent both, arm both dead-man switches, bring up B
#   vast_deploy.sh sync   [SESSION]               pull B's outputs home and rehash them here
#   vast_deploy.sh status [SESSION]               the session's instances and cost so far
#   vast_deploy.sh down   [SESSION] [--no-sync]   final sync, destroy both, check they are gone
#   vast_deploy.sh guard  [SESSION]               local loop: sync every 10 min, `down` at the deadline
#
# Guards, in order of trust: (1) on Node A a process that destroys the instance with Vast's
# per-instance key at the deadline; (2) on Node B `shutdown -h` at the deadline (stops GPU billing on a
# VM; storage still bills) plus the same self-destroy when the VM has the key; (3) `guard` here, which
# dies when this PC sleeps. Test `down` on a throwaway rental before relying on any of them.
#
# Settings (environment): HOURS=3  BUDGET_USD=10  MAX_DPH_LLM=4.00  MAX_DPH_CAE=0.80
#   LLM_QUERY / CAE_QUERY (vast search syntax)  MAX_MODEL_LEN=1048576  VASTAI=vastai
#   SESSIONS_DIR=~/.local/state/porscheparts-vast  LOCAL_WORK=<repo>/work/935-cad-twin/vast-sessions
#   REPO_URL=https://github.com/cluster2600/porscheparts.git  REPO_COMMIT=$(git rev-parse HEAD)
#   RCLONE_REMOTE + RCLONE_CONF (optional push from B, a credential scoped to one bucket)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
VASTAI=${VASTAI:-vastai}
HOURS=${HOURS:-3}
BUDGET_USD=${BUDGET_USD:-10}
MAX_DPH_LLM=${MAX_DPH_LLM:-4.00}
MAX_DPH_CAE=${MAX_DPH_CAE:-0.80}
STORAGE_GB=${STORAGE_GB:-250}
SESSIONS_DIR=${SESSIONS_DIR:-$HOME/.local/state/porscheparts-vast}
LOCAL_WORK=${LOCAL_WORK:-$REPO_ROOT/work/935-cad-twin/vast-sessions}
REPO_URL=${REPO_URL:-https://github.com/cluster2600/porscheparts.git}
REPO_COMMIT=${REPO_COMMIT:-$(git -C "$REPO_ROOT" rev-parse HEAD)}
LLM_IMAGE=vllm/vllm-openai@sha256:befccf0e7e4089aa23926bb6f887a85c0d46c2a99e6de5c5ffdf5cb7957c5b34   # v0.32.0
VM_IMAGE=docker.io/vastai/kvm:ubuntu_cli_22.04-2025-11-21      # Docker 29 + NVIDIA runtime (2026-11-15 run)
LLM_QUERY=${LLM_QUERY:-"gpu_name in [H200,H200_NVL] num_gpus=1 reliability>=0.98 inet_down>=1000 disk_space>=$STORAGE_GB direct_port_count>=1 verified=true rentable=true"}
CAE_QUERY=${CAE_QUERY:-"gpu_name in [RTX_4090,RTX_3090] num_gpus=1 cpu_ram>=64 cpu_cores_effective>=16 vms_enabled=true reliability>=0.98 inet_down>=500 disk_space>=$STORAGE_GB direct_port_count>=1 verified=true rentable=true"}
SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -o ServerAliveInterval=30)

die() { echo "vast_deploy: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "missing tool: $1"; }
now() { date -u +%s; }
session_dir() { local s=${1:-$(cat "$SESSIONS_DIR/current" 2>/dev/null || true)}; [ -n "$s" ] || die "no session"; echo "$SESSIONS_DIR/$s"; }
manifest() { jq -r "$1" "$(session_dir "${2:-}")/manifest.json"; }
ssh_target() {   # role -> "host port" from Vast's own record of the instance
  local id; id=$(manifest ".instances.$1.id" "${2:-}")
  "$VASTAI" ssh-url "$id" | sed -E 's#ssh://root@([^:]+):([0-9]+)#\1 \2#'
}
on_b() { local hp; read -r -a hp <<< "$(ssh_target cae "${SESSION:-}")"; ssh "${SSH_OPTS[@]}" -p "${hp[1]}" "root@${hp[0]}" "$@"; }

credit() { "$VASTAI" show user --raw | jq -r '.credit'; }

cmd_preflight() {
  need "$VASTAI"; need jq; need ssh; need rsync; need ssh-keygen; need sha256sum
  "$VASTAI" show user --raw >/dev/null || die "vastai is not authenticated (vastai set api-key, or VASTAI=openbao-vastai)"
  local c; c=$(credit)
  echo "credit: $c USD (shared with every other session on this account)"
  awk -v c="$c" -v b="$BUDGET_USD" 'BEGIN { exit !(c >= b) }' || die "credit $c below BUDGET_USD $BUDGET_USD"
  "$VASTAI" show ssh-keys --raw | jq -e 'length > 0' >/dev/null || die "no SSH key on the account (vastai create ssh-key)"
  git -C "$REPO_ROOT" fetch -q origin && git -C "$REPO_ROOT" branch -r --contains "$REPO_COMMIT" | grep -q . \
    || die "commit $REPO_COMMIT is not on GitHub: Node B clones it, so push it first"
  local mine; mine=$("$VASTAI" show instances --raw | jq '[.[] | select((.label // "") | startswith("porscheparts-935twin-"))] | length')
  [ "$mine" = 0 ] || die "$mine instance(s) with a porscheparts-935twin- label already exist: run status/down first"
  echo "preflight ok: commit $REPO_COMMIT, budget $BUDGET_USD USD over $HOURS h"
}

offers() {  # query maxdph
  "$VASTAI" search offers "$1 dph_total<=$2" --storage "$STORAGE_GB" -o dph_total --raw \
    | jq -r '.[:5][] | [.id, .gpu_name, .num_gpus, .cpu_cores_effective, (.cpu_ram/1000|floor), (.dph_total*1000|round/1000), .reliability, .geolocation] | @tsv'
}
cmd_offers() {
  echo "Node A (vLLM) <= $MAX_DPH_LLM USD/h:   id gpu n cores ramGB dph rel geo"; offers "$LLM_QUERY" "$MAX_DPH_LLM"
  echo "Node B (CAE, VM) <= $MAX_DPH_CAE USD/h: id gpu n cores ramGB dph rel geo"; offers "$CAE_QUERY" "$MAX_DPH_CAE"
}

offer_dph() { "$VASTAI" search offers "id=$1" --storage "$STORAGE_GB" --raw | jq -r '.[0].dph_total // empty'; }

wait_running() {  # id -> waits until actual_status == running (20 min max)
  for _ in $(seq 1 80); do
    [ "$("$VASTAI" show instance "$1" --raw | jq -r '.actual_status // ""')" = running ] && return 0
    sleep 15
  done
  return 1
}

cmd_up() {
  [ $# -eq 3 ] || die "usage: up OFFER_A OFFER_B INPUTS.txt"
  local offer_a=$1 offer_b=$2 inputs=$3
  cmd_preflight
  local dph_a dph_b cost deadline sess sd
  dph_a=$(offer_dph "$offer_a"); dph_b=$(offer_dph "$offer_b")
  [ -n "$dph_a" ] && [ -n "$dph_b" ] || die "offer no longer listed"
  cost=$(awk -v a="$dph_a" -v b="$dph_b" -v h="$HOURS" 'BEGIN { printf "%.2f", (a + b) * h }')
  awk -v c="$cost" -v b="$BUDGET_USD" 'BEGIN { exit !(c <= b) }' || die "estimated $cost USD above BUDGET_USD $BUDGET_USD"
  awk -v a="$dph_a" -v m="$MAX_DPH_LLM" 'BEGIN { exit !(a <= m) }' || die "Node A at $dph_a USD/h above $MAX_DPH_LLM"
  awk -v a="$dph_b" -v m="$MAX_DPH_CAE" 'BEGIN { exit !(a <= m) }' || die "Node B at $dph_b USD/h above $MAX_DPH_CAE"

  # The private inputs: listed, sized and hashed here, confirmed by the owner, rehashed on B.
  [ -r "$inputs" ] || die "inputs list $inputs unreadable (one absolute path per line)"
  echo "Private inputs to copy to Node B (read-only there, never committed). The scan's licence is"
  echo "still open (issue #462): copying it to a rented machine is the owner's decision for each run."
  while read -r f; do [ -n "$f" ] && du -h "$f"; done < "$inputs"
  read -r -p "Rent A ($dph_a USD/h) and B ($dph_b USD/h) for $HOURS h, about $cost USD, and copy these? [y/N] " ok
  [ "$ok" = y ] || die "not confirmed"

  sess=$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 4); sd=$SESSIONS_DIR/$sess
  mkdir -p "$sd" && chmod 700 "$sd" && echo "$sess" > "$SESSIONS_DIR/current"
  deadline=$(( $(now) + HOURS * 3600 ))
  ssh-keygen -q -t ed25519 -N '' -C "tunnel-$sess" -f "$sd/tunnel_key"
  ( umask 077
    printf 'SESSION=%s\nDEADLINE_EPOCH=%s\nREPO_URL=%s\nREPO_COMMIT=%s\nVLLM_API_KEY=%s\nOPENCLAW_GATEWAY_TOKEN=%s\nOPENCLAW_VERSION=2026.11.4\nRCLONE_REMOTE=%s\n' \
      "$sess" "$deadline" "$REPO_URL" "$REPO_COMMIT" "$(openssl rand -hex 24)" "$(openssl rand -hex 24)" "${RCLONE_REMOTE:-}" > "$sd/session.env" )
  # Hashes by file name: inputs land flat in /workspace/scan, so no local path travels to the rental.
  : > "$sd/inputs.sha256"
  while read -r f; do
    [ -n "$f" ] || continue
    [ -f "$f" ] || die "input $f is not a file"
    grep -q "  $(basename "$f")\$" "$sd/inputs.sha256" && die "two inputs named $(basename "$f")"
    printf '%s  %s\n' "$(sha256sum < "$f" | cut -d' ' -f1)" "$(basename "$f")" >> "$sd/inputs.sha256"
  done < "$inputs"
  . "$sd/session.env"
  jq -n --arg s "$sess" --argjson d "$deadline" --arg c "$REPO_COMMIT" --arg cost "$cost" \
    '{schema: "porscheparts-935twin-vast-session/1", session: $s, deadline_epoch: $d, repo_commit: $c,
      estimated_cost_usd: ($cost|tonumber), instances: {}}' > "$sd/manifest.json"

  # Node A: the vLLM container. Its on-start arms the self-destroy before it downloads 66 GB of weights.
  local la=porscheparts-935twin-llm-${sess##*-} lb=porscheparts-935twin-cae-${sess##*-} ida idb
  ida=$("$VASTAI" create instance "$offer_a" --image "$LLM_IMAGE" --disk "$STORAGE_GB" --ssh --direct \
          --label "$la" --onstart "$HERE/onstart-llm.sh" \
          --env "-e DEADLINE_EPOCH=$deadline -e VLLM_API_KEY=$VLLM_API_KEY -e MAX_MODEL_LEN=${MAX_MODEL_LEN:-1048576} -e TUNNEL_PUBKEY_B64=$(base64 -w0 < "$sd/tunnel_key.pub")" \
          --raw | jq -r '.new_contract')
  [[ "$ida" =~ ^[0-9]+$ ]] || die "Node A creation returned no contract: check 'vastai show instances' by hand"
  jq --arg id "$ida" --arg l "$la" --arg o "$offer_a" --arg p "$dph_a" '.instances.llm = {id: ($id|tonumber), label: $l, offer: $o, dph: ($p|tonumber)}' \
    "$sd/manifest.json" > "$sd/m.tmp" && mv "$sd/m.tmp" "$sd/manifest.json"
  echo "Node A: instance $ida ($la)"

  # Node B: a VM, because the compose services and the OpenClaw sandboxes need Docker.
  idb=$("$VASTAI" create instance "$offer_b" --image "$VM_IMAGE" --disk "$STORAGE_GB" --ssh --direct \
          --label "$lb" --raw | jq -r '.new_contract') || true
  if ! [[ "$idb" =~ ^[0-9]+$ ]]; then
    echo "Node B creation failed: destroying Node A" >&2; SESSION=$sess cmd_down "$sess" --no-sync; exit 1
  fi
  jq --arg id "$idb" --arg l "$lb" --arg o "$offer_b" --arg p "$dph_b" '.instances.cae = {id: ($id|tonumber), label: $l, offer: $o, dph: ($p|tonumber)}' \
    "$sd/manifest.json" > "$sd/m.tmp" && mv "$sd/m.tmp" "$sd/manifest.json"
  echo "Node B: instance $idb ($lb)"

  wait_running "$ida" || { echo "Node A not running after 20 min" >&2; cmd_down "$sess" --no-sync; exit 1; }
  wait_running "$idb" || { echo "Node B not running after 20 min" >&2; cmd_down "$sess" --no-sync; exit 1; }
  local a b; read -r -a a <<< "$(ssh_target llm "$sess")"; read -r -a b <<< "$(ssh_target cae "$sess")"
  printf 'LLM_SSH_HOST=%s\nLLM_SSH_PORT=%s\n' "${a[0]}" "${a[1]}" >> "$sd/session.env"
  for _ in $(seq 1 40); do ssh "${SSH_OPTS[@]}" -p "${b[1]}" "root@${b[0]}" true 2>/dev/null && break; sleep 15; done

  # Session files, then the inputs, rehashed on B before anything uses them.
  SESSION=$sess on_b "mkdir -p /root/session /workspace/scan && chmod 700 /root/session"
  rsync -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" -a "$sd/session.env" "$sd/tunnel_key" "root@${b[0]}:/root/session/"
  [ -n "${RCLONE_CONF:-}" ] && rsync -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" -a "$RCLONE_CONF" "root@${b[0]}:/root/session/rclone.conf"
  while read -r f; do
    [ -n "$f" ] && rsync -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" -a --chmod=F444 "$f" "root@${b[0]}:/workspace/scan/$(basename "$f")"
  done < "$inputs"
  SESSION=$sess on_b "cd /workspace/scan && sha256sum -c --quiet -" < "$sd/inputs.sha256" \
    || { echo "inputs differ after the copy" >&2; cmd_down "$sess" --no-sync; exit 1; }
  SESSION=$sess on_b "chmod -R a-w /workspace/scan"

  # Bring-up on B, from the commit on GitHub (the script arms B's shutdown before anything else).
  SESSION=$sess on_b "git clone -q --filter=blob:none --no-checkout '$REPO_URL' /workspace/repo && \
    git -C /workspace/repo sparse-checkout set --no-cone /deploy/vast/935-twin-openclaw/ && \
    git -C /workspace/repo fetch -q --depth 1 origin '$REPO_COMMIT' && git -C /workspace/repo checkout -q --detach '$REPO_COMMIT' && \
    setsid nohup bash /workspace/repo/deploy/vast/935-twin-openclaw/onstart-cae.sh >/dev/null 2>&1 &"
  echo
  echo "Session $sess up. Deadline $(date -u -d "@$deadline" +%FT%TZ). Estimated cost $cost USD."
  echo "Follow B:    ssh -p ${b[1]} root@${b[0]} tail -f /workspace/logs/onstart-cae.log"
  echo "Dashboard:   ssh -N -L 18789:127.0.0.1:18789 -p ${b[1]} root@${b[0]}   then http://127.0.0.1:18789/"
  echo "Pull often:  $0 sync      Tear down:  $0 down"
}

cmd_sync() {
  local sd b dest stamp; sd=$(session_dir "${1:-}"); SESSION=$(basename "$sd")
  read -r -a b <<< "$(ssh_target cae "$SESSION")"; dest=$LOCAL_WORK/$SESSION; stamp=$(date -u +%Y%m%dT%H%M%SZ)
  mkdir -p "$dest"
  on_b "cd /workspace && find work logs jobs/done -type f ! -path 'work/.home/*' -print0 2>/dev/null | xargs -0 -r sha256sum" > "$dest/remote-sha256-$stamp.txt"
  for d in work logs jobs; do
    rsync -az --partial -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" --exclude '.home/' "root@${b[0]}:/workspace/$d/" "$dest/$d/" || true
  done
  # Rehash here: a file still being written on B can differ; it is listed, not hidden.
  ( cd "$dest" && sha256sum -c --quiet "remote-sha256-$stamp.txt" 2>/dev/null ) > "$dest/sync-mismatch-$stamp.txt" || true
  jq -n --arg s "$stamp" --argjson n "$(wc -l < "$dest/remote-sha256-$stamp.txt")" --argjson bad "$(grep -c FAILED "$dest/sync-mismatch-$stamp.txt" || true)" \
    '{synced: $s, files_listed: $n, mismatched: $bad}' | tee "$dest/sync-$stamp.json"
}

cmd_status() {
  local sd; sd=$(session_dir "${1:-}")
  "$VASTAI" show instances --raw | jq -r --slurpfile m "$sd/manifest.json" \
    '.[] | select(.label as $l | [$m[0].instances[]?.label] | index($l)) |
      [.id, .label, .actual_status, (.dph_total*1000|round/1000), ((.duration // 0)/3600*1000|round/1000)] | @tsv'
  echo "deadline: $(date -u -d "@$(jq -r .deadline_epoch "$sd/manifest.json")" +%FT%TZ); credit now: $(credit) USD"
}

cmd_down() {
  local s=${1:-} nosync=${2:-}; [ "$s" = --no-sync ] && { nosync=--no-sync; s=; }
  local sd; sd=$(session_dir "$s"); SESSION=$(basename "$sd")
  [ "$nosync" = --no-sync ] || cmd_sync "$SESSION" || echo "final sync failed: destroying anyway at the owner's risk" >&2
  local ids; ids=$(jq -r '.instances[]?.id' "$sd/manifest.json")
  for id in $ids; do
    # Destroy only an instance whose current label is the one this session gave it.
    local want got; want=$(jq -r --argjson i "$id" '.instances[] | select(.id == $i) | .label' "$sd/manifest.json")
    got=$("$VASTAI" show instance "$id" --raw 2>/dev/null | jq -r '.label // empty')
    if [ -z "$got" ]; then echo "instance $id already gone"; continue; fi
    [ "$got" = "$want" ] || { echo "instance $id label '$got' is not '$want': left alone" >&2; continue; }
    "$VASTAI" destroy instance "$id" -y
  done
  for _ in $(seq 1 20); do
    left=$("$VASTAI" show instances --raw | jq --argjson ids "[$(echo $ids | tr ' ' ',')]" '[.[] | select(.id as $i | $ids | index($i))] | length')
    [ "$left" = 0 ] && break; sleep 15
  done
  jq -n --arg t "$(date -u +%FT%TZ)" --argjson left "${left:-0}" --arg c "$(credit)" \
    '{torn_down: $t, instances_left: $left, credit_after_usd: $c}' | tee "$sd/teardown.json"
  [ "${left:-0}" = 0 ] || die "$left instance(s) still listed: check by hand"
}

cmd_guard() {
  local sd deadline; sd=$(session_dir "${1:-}"); deadline=$(jq -r .deadline_epoch "$sd/manifest.json")
  echo "guard: syncing every 10 min, down at $(date -u -d "@$((deadline - 600))" +%FT%TZ). It dies if this PC sleeps."
  while [ "$(now)" -lt $((deadline - 600)) ]; do cmd_sync "$(basename "$sd")" >/dev/null 2>&1 || true; sleep 600; done
  cmd_down "$(basename "$sd")"
}

case "${1:-}" in
  preflight) shift; cmd_preflight "$@";;
  offers)    shift; cmd_offers "$@";;
  up)        shift; cmd_up "$@";;
  sync)      shift; cmd_sync "$@";;
  status)    shift; cmd_status "$@";;
  down)      shift; cmd_down "$@";;
  guard)     shift; cmd_guard "$@";;
  *) sed -n '2,24p' "$0"; exit 2;;
esac
