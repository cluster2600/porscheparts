#!/usr/bin/env bash
# Two-node Vast.ai session for the 935 head twin: Node A serves Nemotron 3.5 Super VL with vLLM,
# Node B runs the CAE images, the job runner and OpenClaw. Run it ATTENDED, from home (outbound SSH to
# Vast's high ports is blocked from the owner's daytime network), and never across a pause.
#
#   vast_deploy.sh preflight                      account, credit, key, tools, commit on GitHub
#   vast_deploy.sh offers                         cheapest admissible offers for each role
#   vast_deploy.sh qualify OFFER_B IMAGE@sha256:D one Node B VM: pull the cae image, smoke it, bring the
#                                                 receipt home, destroy the VM (no model, no inputs)
#   vast_deploy.sh admit RECEIPT_DIR              after reading its renders: write cae-935.lock.json
#   vast_deploy.sh up OFFER_A OFFER_B INPUTS.txt  rent both, arm both dead-man switches, bring up B;
#                                                 refuses before renting unless cae-935.lock.json admits
#                                                 an image built from this Dockerfile.cae
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
#   QUAL_HOURS=1  QUAL_BUDGET_USD=1.00  QUAL_STORAGE_GB=100 (the qualify rental)
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
QUAL_HOURS=${QUAL_HOURS:-1}
QUAL_BUDGET_USD=${QUAL_BUDGET_USD:-1.00}
QUAL_STORAGE_GB=${QUAL_STORAGE_GB:-100}
LOCK=$HERE/cae-935.lock.json
SESSIONS_DIR=${SESSIONS_DIR:-$HOME/.local/state/porscheparts-vast}
LOCAL_WORK=${LOCAL_WORK:-$REPO_ROOT/work/935-cad-twin/vast-sessions}
REPO_URL=${REPO_URL:-https://github.com/cluster2600/porscheparts.git}
REPO_COMMIT=${REPO_COMMIT:-$(git -C "$REPO_ROOT" rev-parse HEAD)}
LLM_IMAGE=vllm/vllm-openai@sha256:befccf0e7e4089aa23926bb6f887a85c0d46c2a99e6de5c5ffdf5cb7957c5b34   # v0.32.0
VM_IMAGE=docker.io/vastai/kvm:ubuntu_cli_22.04-2025-11-21      # Docker 29 + NVIDIA runtime (2026-11-15 run)
LLM_QUERY=${LLM_QUERY:-"gpu_name in [H200,H200_NVL] num_gpus=1 reliability>=0.98 inet_down>=1000 disk_space>=$STORAGE_GB direct_port_count>=1 verified=true rentable=true"}
CAE_QUERY=${CAE_QUERY:-"gpu_name in [RTX_4090,RTX_3090] num_gpus=1 cpu_ram>=64 cpu_cores_effective>=16 vms_enabled=true reliability>=0.98 inet_down>=500 disk_space>=$STORAGE_GB direct_port_count>=1 verified=true rentable=true"}
QUAL_QUERY=${QUAL_QUERY:-"gpu_name in [RTX_4090,RTX_3090] num_gpus=1 vms_enabled=true reliability>=0.98 inet_down>=500 disk_space>=$QUAL_STORAGE_GB direct_port_count>=1 verified=true rentable=true"}
SSH_WAIT_TRIES=${SSH_WAIT_TRIES:-40}   # x 15 s for a new instance's sshd
SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -o ServerAliveInterval=30)

die() { echo "vast_deploy: $*" >&2; exit 1; }

# While `up` or `qualify` sets up a rental, any exit before the setup completes (an error, `die`,
# Ctrl-C) destroys the session's instances: a Node B whose bring-up never started has no deadline
# shutdown at all, and would bill until someone notices.
TEARDOWN_ON_EXIT=
teardown_on_exit() {
  local rc=$? s=$TEARDOWN_ON_EXIT
  [ -n "$s" ] || return 0
  TEARDOWN_ON_EXIT=
  echo "vast_deploy: setup of session $s stopped (exit $rc): destroying its instances" >&2
  cmd_down "$s" --no-sync || echo "vast_deploy: teardown of $s failed: check 'vastai show instances' by hand" >&2
}
trap teardown_on_exit EXIT
trap 'exit 130' INT TERM
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
digest_ref() { [[ "$1" =~ ^[a-z0-9][a-z0-9.:/_-]*@sha256:[0-9a-f]{64}$ ]]; }

# Node B runs this folder as it is at REPO_COMMIT, lock included: refuse local changes it would not see.
folder_at_commit() {
  git -C "$REPO_ROOT" diff --quiet "$REPO_COMMIT" -- "$HERE" \
    && [ -z "$(git -C "$REPO_ROOT" ls-files --others --exclude-standard -- "$HERE")" ] \
    || die "$HERE differs from commit $REPO_COMMIT: commit and push it first (Node B runs the commit)"
}

# The cae image a session may use: the one cae-935.lock.json admits, if the lock still holds. Every
# check reads files in this folder, so a failure costs nothing; it runs before any rental.
admitted_image() {
  need jq; need sha256sum
  [ -f "$LOCK" ] || die "no cae-935.lock.json: build, push, qualify and admit the cae image first (README, \"Admitting the cae image\")"
  local ref receipt want got
  ref=$(jq -r '.image.immutable_reference // empty' "$LOCK")
  digest_ref "$ref" || die "cae-935.lock.json: image.immutable_reference is not a digest reference"
  jq -e '.verification.gpu_smoke.status == "passed" and .release_gates.gpu_runtime_verified == true
         and (.verification.renders_read.by // "" | length > 0)' "$LOCK" >/dev/null \
    || die "cae-935.lock.json: no passed GPU smoke with its renders read"
  receipt=$HERE/$(jq -r '.verification.gpu_smoke.receipt' "$LOCK")
  [ -f "$receipt" ] || die "cae-935.lock.json: receipt $receipt missing"
  [ "$(sha256sum < "$receipt" | cut -d' ' -f1)" = "$(jq -r '.verification.gpu_smoke.receipt_sha256' "$LOCK")" ] \
    || die "cae-935.lock.json: receipt hash differs"
  while IFS=$'\t' read -r path want; do
    got=$(sha256sum < "$REPO_ROOT/$path" | cut -d' ' -f1)
    [ "$got" = "$want" ] || die "$path changed since the image was admitted: rebuild, qualify and admit again"
  done < <(jq -r '.recipe.inputs[] | [.path, .sha256] | @tsv' "$LOCK")
  echo "$ref"
}

cmd_preflight() {   # BUDGET_USD: the credit this rental needs
  need "$VASTAI"; need jq; need ssh; need rsync; need ssh-keygen; need sha256sum; need openssl
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
  echo "qualify (one VM, $QUAL_STORAGE_GB GB) <= $MAX_DPH_CAE USD/h:"; STORAGE_GB=$QUAL_STORAGE_GB offers "$QUAL_QUERY" "$MAX_DPH_CAE"
}

offer_dph() { "$VASTAI" search offers "id=$1" --storage "$STORAGE_GB" --raw | jq -r '.[0].dph_total // empty'; }

new_session() {  # -> prints the session id; creates its 0700 directory and marks it current
  local sess; sess=$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 4)
  mkdir -p "$SESSIONS_DIR/$sess" && chmod 700 "$SESSIONS_DIR/$sess" && echo "$sess" > "$SESSIONS_DIR/current"
  echo "$sess"
}

start_b() {  # session host port: clone the commit's deploy folder on B and start onstart-cae.sh there
  SESSION=$1 on_b "git clone -q --filter=blob:none --no-checkout '$REPO_URL' /workspace/repo && \
    git -C /workspace/repo sparse-checkout set --no-cone /deploy/vast/935-twin-openclaw/ && \
    git -C /workspace/repo fetch -q --depth 1 origin '$REPO_COMMIT' && git -C /workspace/repo checkout -q --detach '$REPO_COMMIT' && \
    setsid nohup bash /workspace/repo/deploy/vast/935-twin-openclaw/onstart-cae.sh >/dev/null 2>&1 &"
}

wait_ssh() {  # host port: until the instance's sshd answers, else die (the EXIT trap tears down)
  for _ in $(seq 1 "$SSH_WAIT_TRIES"); do ssh "${SSH_OPTS[@]}" -p "$2" "root@$1" true 2>/dev/null && return 0; sleep 15; done
  die "no SSH to $1:$2 after $((SSH_WAIT_TRIES * 15)) s"
}

wait_running() {  # id -> waits until actual_status == running (20 min max)
  for _ in $(seq 1 80); do
    [ "$("$VASTAI" show instance "$1" --raw | jq -r '.actual_status // ""')" = running ] && return 0
    sleep 15
  done
  return 1
}

cmd_up() {
  [ $# -eq 3 ] || die "usage: up OFFER_A OFFER_B INPUTS.txt"
  local offer_a=$1 offer_b=$2 inputs=$3 cae_image
  cae_image=$(admitted_image)
  folder_at_commit
  echo "cae image admitted by cae-935.lock.json: $cae_image"
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

  sess=$(new_session); sd=$SESSIONS_DIR/$sess
  deadline=$(( $(now) + HOURS * 3600 ))
  ssh-keygen -q -t ed25519 -N '' -C "tunnel-$sess" -f "$sd/tunnel_key"
  ( umask 077
    printf 'MODE=session\nSESSION=%s\nDEADLINE_EPOCH=%s\nREPO_URL=%s\nREPO_COMMIT=%s\nCAE_IMAGE=%s\nVLLM_API_KEY=%s\nOPENCLAW_GATEWAY_TOKEN=%s\nOPENCLAW_VERSION=2026.11.4\nRCLONE_REMOTE=%s\n' \
      "$sess" "$deadline" "$REPO_URL" "$REPO_COMMIT" "$cae_image" "$(openssl rand -hex 24)" "$(openssl rand -hex 24)" "${RCLONE_REMOTE:-}" > "$sd/session.env" )
  # Hashes by file name: inputs land flat in /workspace/scan, so no local path travels to the rental.
  : > "$sd/inputs.sha256"
  while read -r f; do
    [ -n "$f" ] || continue
    [ -f "$f" ] || die "input $f is not a file"
    grep -q "  $(basename "$f")\$" "$sd/inputs.sha256" && die "two inputs named $(basename "$f")"
    printf '%s  %s\n' "$(sha256sum < "$f" | cut -d' ' -f1)" "$(basename "$f")" >> "$sd/inputs.sha256"
  done < "$inputs"
  . "$sd/session.env"
  jq -n --arg s "$sess" --argjson d "$deadline" --arg c "$REPO_COMMIT" --arg cost "$cost" --arg img "$cae_image" \
    '{schema: "porscheparts-935twin-vast-session/1", kind: "session", session: $s, deadline_epoch: $d, repo_commit: $c,
      cae_image: $img, estimated_cost_usd: ($cost|tonumber), instances: {}}' > "$sd/manifest.json"

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
  TEARDOWN_ON_EXIT=$sess     # from here, a failed setup destroys what this session rented

  # Node B: a VM, because the compose services and the OpenClaw sandboxes need Docker.
  idb=$("$VASTAI" create instance "$offer_b" --image "$VM_IMAGE" --disk "$STORAGE_GB" --ssh --direct \
          --label "$lb" --raw | jq -r '.new_contract') || true
  [[ "$idb" =~ ^[0-9]+$ ]] || die "Node B creation failed: destroying Node A"
  jq --arg id "$idb" --arg l "$lb" --arg o "$offer_b" --arg p "$dph_b" '.instances.cae = {id: ($id|tonumber), label: $l, offer: $o, dph: ($p|tonumber)}' \
    "$sd/manifest.json" > "$sd/m.tmp" && mv "$sd/m.tmp" "$sd/manifest.json"
  echo "Node B: instance $idb ($lb)"

  wait_running "$ida" || die "Node A not running after 20 min"
  wait_running "$idb" || die "Node B not running after 20 min"
  local a b; read -r -a a <<< "$(ssh_target llm "$sess")"; read -r -a b <<< "$(ssh_target cae "$sess")"
  printf 'LLM_SSH_HOST=%s\nLLM_SSH_PORT=%s\n' "${a[0]}" "${a[1]}" >> "$sd/session.env"
  wait_ssh "${b[0]}" "${b[1]}"

  # Session files, then the inputs, rehashed on B before anything uses them.
  SESSION=$sess on_b "mkdir -p /root/session /workspace/scan && chmod 700 /root/session"
  rsync -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" -a "$sd/session.env" "$sd/tunnel_key" "root@${b[0]}:/root/session/"
  [ -n "${RCLONE_CONF:-}" ] && rsync -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" -a "$RCLONE_CONF" "root@${b[0]}:/root/session/rclone.conf"
  while read -r f; do
    [ -n "$f" ] && rsync -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" -a --chmod=F444 "$f" "root@${b[0]}:/workspace/scan/$(basename "$f")"
  done < "$inputs"
  SESSION=$sess on_b "cd /workspace/scan && sha256sum -c --quiet -" < "$sd/inputs.sha256" \
    || die "inputs differ after the copy"
  SESSION=$sess on_b "chmod -R a-w /workspace/scan"

  # Bring-up on B, from the commit on GitHub (the script arms B's shutdown before anything else).
  start_b "$sess"
  TEARDOWN_ON_EXIT=          # B's own deadline shutdown is armed; the session now runs until `down`
  echo
  echo "Session $sess up. Deadline $(date -u -d "@$deadline" +%FT%TZ). Estimated cost $cost USD."
  echo "Follow B:    ssh -p ${b[1]} root@${b[0]} tail -f /workspace/logs/onstart-cae.log"
  echo "Dashboard:   ssh -N -L 18789:127.0.0.1:18789 -p ${b[1]} root@${b[0]}   then http://127.0.0.1:18789/"
  echo "Pull often:  $0 sync      Tear down:  $0 down"
}

# One Node B VM, no model and no private inputs: B pulls IMAGE by digest without a registry
# credential (so the package must be public), runs smoke-cae.sh on its GPU and stops; the receipt
# comes home and the VM is destroyed. A pass is not an admission: read the renders, then `admit`.
cmd_qualify() {
  [ $# -eq 2 ] || die "usage: qualify OFFER_B IMAGE@sha256:DIGEST"
  local offer=$1 image=$2 dph cost deadline sess sd lb idb b stamp rc
  digest_ref "$image" || die "$image is not a digest reference (registry/name@sha256:<64 hex>)"
  folder_at_commit
  local STORAGE_GB=$QUAL_STORAGE_GB BUDGET_USD=$QUAL_BUDGET_USD HOURS=$QUAL_HOURS
  cmd_preflight
  dph=$(offer_dph "$offer"); [ -n "$dph" ] || die "offer no longer listed"
  cost=$(awk -v a="$dph" -v h="$HOURS" 'BEGIN { printf "%.2f", a * h }')
  awk -v a="$dph" -v m="$MAX_DPH_CAE" 'BEGIN { exit !(a <= m) }' || die "offer at $dph USD/h above $MAX_DPH_CAE"
  awk -v c="$cost" -v b="$BUDGET_USD" 'BEGIN { exit !(c <= b) }' || die "estimated $cost USD above QUAL_BUDGET_USD $BUDGET_USD"
  read -r -p "Rent one VM ($dph USD/h, at most $HOURS h, about $cost USD) to smoke-test $image? [y/N] " ok
  [ "$ok" = y ] || die "not confirmed"

  sess=$(new_session); sd=$SESSIONS_DIR/$sess
  deadline=$(( $(now) + HOURS * 3600 ))
  ( umask 077
    printf 'MODE=qualify\nSESSION=%s\nDEADLINE_EPOCH=%s\nREPO_URL=%s\nREPO_COMMIT=%s\nCAE_IMAGE=%s\nRCLONE_REMOTE=%s\n' \
      "$sess" "$deadline" "$REPO_URL" "$REPO_COMMIT" "$image" "${RCLONE_REMOTE:-}" > "$sd/session.env" )
  jq -n --arg s "$sess" --argjson d "$deadline" --arg c "$REPO_COMMIT" --arg cost "$cost" --arg img "$image" \
    '{schema: "porscheparts-935twin-vast-session/1", kind: "qualify", session: $s, deadline_epoch: $d, repo_commit: $c,
      cae_image: $img, estimated_cost_usd: ($cost|tonumber), instances: {}}' > "$sd/manifest.json"
  lb=porscheparts-935twin-qual-${sess##*-}
  idb=$("$VASTAI" create instance "$offer" --image "$VM_IMAGE" --disk "$STORAGE_GB" --ssh --direct \
          --label "$lb" --raw | jq -r '.new_contract') || true
  [[ "$idb" =~ ^[0-9]+$ ]] || die "creation returned no contract: check 'vastai show instances' by hand"
  jq --arg id "$idb" --arg l "$lb" --arg o "$offer" --arg p "$dph" '.instances.cae = {id: ($id|tonumber), label: $l, offer: $o, dph: ($p|tonumber)}' \
    "$sd/manifest.json" > "$sd/m.tmp" && mv "$sd/m.tmp" "$sd/manifest.json"
  echo "qualify VM: instance $idb ($lb)"
  TEARDOWN_ON_EXIT=$sess     # any exit before the normal teardown below destroys the VM
  wait_running "$idb" || die "VM not running after 20 min"
  read -r -a b <<< "$(ssh_target cae "$sess")"
  wait_ssh "${b[0]}" "${b[1]}"
  SESSION=$sess on_b "mkdir -p /root/session && chmod 700 /root/session"
  rsync -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" -a "$sd/session.env" "root@${b[0]}:/root/session/"
  [ -n "${RCLONE_CONF:-}" ] && rsync -e "ssh ${SSH_OPTS[*]} -p ${b[1]}" -a "$RCLONE_CONF" "root@${b[0]}:/root/session/rclone.conf"
  start_b "$sess"
  echo "qualify running; follow: ssh -p ${b[1]} root@${b[0]} tail -f /workspace/logs/onstart-cae.log"
  local done_line=""
  while [ "$(now)" -lt $((deadline - 300)) ]; do
    done_line=$(SESSION=$sess on_b "cat /workspace/work/QUALIFY_DONE 2>/dev/null" || true)
    [ -n "$done_line" ] && break
    sleep 30
  done
  TEARDOWN_ON_EXIT=
  cmd_down "$sess"     # syncs first, then destroys and checks the VM is gone
  [ -n "$done_line" ] || die "no QUALIFY_DONE before the deadline: read $LOCAL_WORK/$sess/logs/onstart-cae.log"
  read -r stamp rc <<< "$done_line"
  [ "$stamp" != none ] || die "qualify stopped before the smoke (exit $rc): read $LOCAL_WORK/$sess/logs/onstart-cae.log"
  echo "smoke exit $rc; receipt: $LOCAL_WORK/$sess/work/receipts/$stamp"
  [ "$rc" = 0 ] && echo "Read every PNG under it, then: $0 admit $LOCAL_WORK/$sess/work/receipts/$stamp"
}

# Writes cae-935.lock.json from a passed qualify receipt, after the owner has read its renders. Copies
# the receipt's small JSON files beside the lock (they contain no scan data); the PNGs stay in work/.
cmd_admit() {
  [ $# -eq 1 ] || die "usage: admit RECEIPT_DIR   (work/935-cad-twin/vast-sessions/<session>/work/receipts/smoke-cae-<stamp>)"
  need jq; need sha256sum
  local r=$1 ref stamp dest who f pngs dsha
  for f in receipt.json image.json imports.json gpu.csv smoke-exit-code; do [ -f "$r/$f" ] || die "missing $r/$f"; done
  [ "$(cat "$r/smoke-exit-code")" = 0 ] && jq -e '.passed == true' "$r/receipt.json" >/dev/null || die "the smoke did not pass"
  ref=$(jq -r '.ref' "$r/image.json")
  digest_ref "$ref" || die "image.json: $ref is not a digest reference"
  jq -e --arg ref "$ref" '.repo_digests | index($ref)' "$r/image.json" >/dev/null || die "the pulled image does not carry $ref"
  dsha=$(sha256sum < "$HERE/Dockerfile.cae" | cut -d' ' -f1)
  [ "$(jq -r '.labels["porscheparts.dockerfile_sha256"] // ""' "$r/image.json")" = "$dsha" ] \
    || die "the image was not built from this Dockerfile.cae (label porscheparts.dockerfile_sha256)"
  pngs=$(cd "$r" && find . -name '*.png' | sort)
  [ -n "$pngs" ] || die "no renders under $r"
  echo "Renders of this smoke (open each one):"; echo "$pngs" | sed "s#^\.#  $r#"
  read -r -p "Name of the person who read every picture and found it as expected (empty to stop): " who
  [ -n "$who" ] || die "not admitted"
  stamp=$(basename "$r"); dest=$HERE/receipts/$stamp; mkdir -p "$dest"
  cp "$r/receipt.json" "$r/image.json" "$r/imports.json" "$r/gpu.csv" "$dest/"
  for f in witness-cpu witness-cuda witness-cpu-mpi2; do cp "$r/$f/witness.json" "$dest/$f.json"; done
  cp "$r/demo/run-cuda/record.json" "$dest/demo-record.json"
  jq -n --arg ref "$ref" --arg dsha "$dsha" --arg receipt "receipts/$stamp/receipt.json" \
     --arg rsha "$(sha256sum < "$dest/receipt.json" | cut -d' ' -f1)" --arg who "$who" --arg on "$(date -u +%F)" \
     --arg gpu "$(tail -n +2 "$r/gpu.csv" | head -1)" --arg pngs "$pngs" --slurpfile img "$r/image.json" \
    '{schema_version: "1.0.0", artifact_kind: "oci_image_lock",
      image: {repository: ($ref | split("@")[0]), digest: ($ref | split("@")[1]), immutable_reference: $ref,
              image_id: $img[0].id, created_at: $img[0].created, cuda_arch: $img[0].labels["porscheparts.cuda_arch"]},
      recipe: {inputs: [{path: "deploy/vast/935-twin-openclaw/Dockerfile.cae", sha256: $dsha}]},
      verification: {status: "passed",
        anonymous_exact_digest_access: ($img[0].registry_credential_on_host == false),
        gpu_smoke: {status: "passed", receipt: $receipt, receipt_sha256: $rsha, gpu_name_driver_cc_memory: $gpu},
        renders_read: {by: $who, on: $on, files: ($pngs | split("\n") | map(ltrimstr("./")))}},
      release_gates: {image_build_and_public_pull: true, gpu_runtime_verified: true, head_result: false,
                      engine_simulation_validated: false, vast_long_job_allowed: false},
      claim_scope: "The software path of this image on one GPU and driver: imports, CUDA PETSc, the template witnesses on both backends, Warp, Newton, an EGL render. No head result, no speed claim, no rental authorised."}' \
    > "$LOCK"
  echo "wrote $LOCK and $dest/: review, commit and push them; \`up\` reads them from this folder."
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
  qualify)   shift; cmd_qualify "$@";;
  admit)     shift; cmd_admit "$@";;
  up)        shift; cmd_up "$@";;
  sync)      shift; cmd_sync "$@";;
  status)    shift; cmd_status "$@";;
  down)      shift; cmd_down "$@";;
  guard)     shift; cmd_guard "$@";;
  *) sed -n '2,30p' "$0"; exit 2;;
esac
