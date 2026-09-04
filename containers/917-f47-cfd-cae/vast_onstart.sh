#!/bin/sh
set -eu
test "$(id -u)" -eq 0 || { echo "vast_onstart_requires_root" >&2; exit 77; }
test "$#" -eq 2 && test "$1" = "--deadline-epoch" || { echo "deadline_argument_required" >&2; exit 2; }
case "$2" in ''|*[!0-9]*) echo "deadline_invalid" >&2; exit 2 ;; esac
deadline=$2
now=$(date +%s)
test "${deadline}" -gt "${now}" && test "${deadline}" -le $((now + 28800)) || {
    echo "deadline_outside_eight_hours" >&2
    exit 2
}
/opt/917-f47-cfd-cae/prepare_layout.sh
test ! -e /workspace/F46_STOP && test ! -L /workspace/F46_STOP || { echo "stale_stop_file" >&2; exit 78; }

marker=/run/sshd/f47-runtime-host-keys.ready
if [ ! -e "${marker}" ] && [ ! -L "${marker}" ]; then
    /usr/sbin/sshd -T >/dev/null
fi
test -f "${marker}" && test ! -L "${marker}" || { echo "host_key_marker_missing" >&2; exit 79; }
authorized=/root/.ssh/authorized_keys
test -s "${authorized}" && test ! -L "${authorized}" || { echo "authorized_keys_missing" >&2; exit 80; }
chown root:root "${authorized}"
chmod 0600 "${authorized}"

nohup /opt/917-f47-cfd-cae/watchdog.py --deadline-epoch "${deadline}" \
    >/workspace/f46-runtime/watchdog.log 2>&1 </dev/null &
watchdog_pid=$!
for attempt in 1 2 3 4 5; do
    test -s /workspace/f46-runtime/watchdog-armed.json && break
    sleep 1
done
test -s /workspace/f46-runtime/watchdog-armed.json || { kill "${watchdog_pid}"; echo "watchdog_not_armed" >&2; exit 81; }

smoke_tmp=/workspace/f46-runtime/.image-smoke.tmp
smoke=/workspace/f46-runtime/image-smoke.json
ready_tmp=/workspace/.READY.tmp
ready=/workspace/READY
rm -f -- "${smoke_tmp}" "${ready_tmp}" "${ready}"
setpriv --reuid=9147 --regid=9147 --clear-groups --no-new-privs \
    /usr/local/bin/f47-image-smoke --require-cuda >"${smoke_tmp}"
python3 - "${smoke_tmp}" "${ready_tmp}" "${deadline}" "${watchdog_pid}" <<'PY'
import json
from pathlib import Path
import sys
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if report.get("all_required_F46_runtime_smokes_passed") is not True:
    raise SystemExit("full F46 runtime smoke rejected")
if report.get("exact_ICEEngineFoam_executable_found") is not False:
    raise SystemExit("solver authority drift")
ready = {
    "schema_version": "1.0.0",
    "status": "F47_image_ready_for_digest_bound_F46_jobs_only",
    "remote_deadline_epoch": int(sys.argv[3]),
    "remote_watchdog_armed": True,
    "remote_watchdog_pid": int(sys.argv[4]),
    "solver_uid": 9147,
    "runtime_smoke_verified": True,
    "simulation_executed": False,
    "physical_validation": False,
    "manufacturing_release": False,
}
Path(sys.argv[2]).write_text(json.dumps(ready, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
mv "${smoke_tmp}" "${smoke}"
mv "${ready_tmp}" "${ready}"
chmod 0644 "${smoke}" "${ready}"
