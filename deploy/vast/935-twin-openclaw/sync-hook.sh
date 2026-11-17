#!/usr/bin/env bash
# Push Node B's private outputs to the owner's storage after every job and before any shutdown.
# A no-op unless /root/session/session.env sets RCLONE_REMOTE (for example "twinbackup:porscheparts-935")
# and /root/session/rclone.conf holds a credential scoped to that one bucket, write-only if the
# provider allows it. The account's own token never comes to this machine.
# The primary copy path stays `vast_deploy.sh sync` (a pull to the owner's host, rehashed there).
set -uo pipefail
[ -r /root/session/session.env ] && . /root/session/session.env
[ -n "${RCLONE_REMOTE:-}" ] || exit 0
command -v rclone >/dev/null || { apt-get -qq update && apt-get -y -qq install rclone; } >/dev/null 2>&1
dest="$RCLONE_REMOTE/${SESSION:-unknown}"
for d in work logs jobs/done; do
  [ -d "/workspace/$d" ] || continue
  timeout 900 rclone --config /root/session/rclone.conf copy --checksum --transfers 4 \
    --exclude '.home/**' "/workspace/$d" "$dest/$d" >> /workspace/logs/sync-hook.log 2>&1 \
    || echo "$(date -u +%FT%TZ) rclone copy of $d failed" >> /workspace/logs/sync-hook.log
done
# Hash list of what was pushed, kept beside it: the owner's side rehashes after download.
( cd /workspace && find work logs jobs/done -type f ! -path 'work/.home/*' -print0 2>/dev/null | xargs -0 sha256sum ) \
  > /workspace/logs/pushed-sha256.txt 2>/dev/null
timeout 300 rclone --config /root/session/rclone.conf copyto --checksum /workspace/logs/pushed-sha256.txt \
  "$dest/pushed-sha256.txt" >> /workspace/logs/sync-hook.log 2>&1 || true
