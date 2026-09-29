#!/usr/bin/env bash
# Push wave-2 lane worktree branches to origin periodically so GitHub stays current
# while lane agents work. Pushes only refs that are descendants of their remote tip
# (or brand-new refs). Never force. Runs for ~4h then exits.
set -u
REPO=/home/lolman/repos/porscheparts
INTERVAL=${INTERVAL:-120}
DEADLINE=$(( $(date +%s) + ${MAX_SECONDS:-14400} ))
LOG=/tmp/push-lanes.log
: > "$LOG"
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  for wt in /home/lolman/repos/wt-*; do
    [ -d "$wt/.git" ] || [ -f "$wt/.git" ] || continue
    br=$(git -C "$wt" branch --show-current 2>/dev/null) || continue
    case "$br" in wave2/*|wave1/*) ;; *) continue ;; esac
    ahead=$(git -C "$wt" rev-list --count "origin/$br..$br" 2>/dev/null || echo "")
    if [ -z "$ahead" ]; then ahead=1; fi
    behind=$(git -C "$wt" rev-list --count "$br..origin/$br" 2>/dev/null || echo 1)
    if [ "$ahead" -gt 0 ] && [ "$behind" -eq 0 ]; then
      if git -C "$REPO" push origin "$br:$br" >>"$LOG" 2>&1; then
        echo "$(date -Is) pushed $br (+$ahead)" >>"$LOG"
      fi
    fi
  done
  # also keep the integration branch fresh when it moves locally
  mainahead=$(git -C "$REPO" rev-list --count "origin/feat/fan-cfd-deck..feat/fan-cfd-deck" 2>/dev/null || echo 0)
  if [ "$mainahead" -gt 0 ]; then
    git -C "$REPO" push origin feat/fan-cfd-deck >>"$LOG" 2>&1 && echo "$(date -Is) pushed feat/fan-cfd-deck (+$mainahead)" >>"$LOG"
  fi
  sleep "$INTERVAL"
done
echo "$(date -Is) push-lanes finished" >>"$LOG"
