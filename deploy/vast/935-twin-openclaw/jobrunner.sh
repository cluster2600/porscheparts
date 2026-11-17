#!/usr/bin/env bash
# Host-side job runner on Node B: the only path from an agent to a tool image.
#
# Agents run in OpenClaw sandboxes with no network and no Docker socket. To run a tool they write
#   $JOBS/inbox/<id>.json = {"id": "<id>", "service": "cae|openfoam|cloudcompare", "argv": [...],
#                            "timeout_s": N, "agent": "<agent id>", "why": "<one line>"}
# This loop validates the file, runs `docker compose run --rm -T <service> <argv...>` (argv as an
# array, no shell), and writes $JOBS/done/<id>/{job.json,log.txt,exit.json}. It never runs a service
# outside ALLOWED, never takes a mount or a flag from the job, and runs one job at a time.
#
# Usage: jobrunner.sh JOBS_DIR COMPOSE_FILE        (systemd unit or tmux, as the operator)
set -euo pipefail
JOBS=$(realpath "$1"); COMPOSE=$(realpath "$2")
ALLOWED="cae openfoam cloudcompare"
MAX_TIMEOUT=${MAX_TIMEOUT:-21600}
mkdir -p "$JOBS/inbox" "$JOBS/running" "$JOBS/done" "$JOBS/rejected"

reject() { mkdir -p "$JOBS/rejected/$2"; mv "$1" "$JOBS/rejected/$2/job.json"; echo "{\"rejected\": \"$3\"}" > "$JOBS/rejected/$2/why.json"; echo "rejected $2: $3"; }

while true; do
  for f in "$JOBS"/inbox/*.json; do
    [ -e "$f" ] || continue
    id=$(basename "$f" .json)
    [[ "$id" =~ ^[A-Za-z0-9._-]{1,80}$ ]] || { reject "$f" "bad-id-$(date +%s)" "id must match [A-Za-z0-9._-]{1,80}"; continue; }
    if ! jq -e 'type=="object" and (.argv|type=="array") and (.argv|all(type=="string")) and (.service|type=="string")' "$f" >/dev/null 2>&1; then
      reject "$f" "$id" "not a job object with a string service and an argv array of strings"; continue
    fi
    svc=$(jq -r .service "$f")
    case " $ALLOWED " in *" $svc "*) ;; *) reject "$f" "$id" "service $svc not allowed"; continue;; esac
    t=$(jq -r '.timeout_s // 3600' "$f"); [[ "$t" =~ ^[0-9]+$ ]] && [ "$t" -le "$MAX_TIMEOUT" ] || t=$MAX_TIMEOUT
    mv "$f" "$JOBS/running/$id.json"
    out="$JOBS/done/$id"; mkdir -p "$out"; cp "$JOBS/running/$id.json" "$out/job.json"
    mapfile -d '' argv < <(jq -j '.argv[] | (. + "\u0000")' "$out/job.json")
    start=$(date -u +%FT%TZ); set +e
    timeout --kill-after=60 "$t" docker compose -f "$COMPOSE" run --rm -T "$svc" "${argv[@]}" > "$out/log.txt" 2>&1
    rc=$?; set -e
    jq -n --arg s "$start" --arg e "$(date -u +%FT%TZ)" --argjson rc "$rc" --arg svc "$svc" \
      '{service: $svc, started: $s, ended: $e, exit_code: $rc, timed_out: ($rc == 124)}' > "$out/exit.json"
    rm -f "$JOBS/running/$id.json"
    echo "job $id ($svc) exit $rc"
    # Push results home after every job (sync-hook.sh is a no-op unless a remote is configured).
    [ -x "$(dirname "$0")/sync-hook.sh" ] && "$(dirname "$0")/sync-hook.sh" || true
  done
  sleep 5
done
