#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "vast_onstart_requires_root" >&2
    exit 77
fi

/opt/917-engine-wave-f40-vast/prepare_layout.sh

authorized_keys=/root/.ssh/authorized_keys
test -s "${authorized_keys}" || { echo "vast_authorized_keys_missing" >&2; exit 78; }
test ! -L "${authorized_keys}" || { echo "vast_authorized_keys_symlink_rejected" >&2; exit 79; }
chown root:root "${authorized_keys}"
chmod 0600 "${authorized_keys}"

report_tmp=/workspace/.image-smoke.json.tmp
report=/workspace/image-smoke.json
ready_tmp=/workspace/.READY.tmp
ready=/workspace/READY
rm -f -- "${report_tmp}" "${ready_tmp}" "${ready}"

python /opt/917-engine-wave-f40-vast/image_smoke.py \
    --expect-runtime-authorized-keys >"${report_tmp}"
python - "${report_tmp}" "${ready_tmp}" <<'PY'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if report.get("status") != "offline_transport_smoke_passed_vast_and_engine_validation_blocked":
    raise SystemExit("image smoke status rejected")
ready = {
    "schema_version": "1.0.0",
    "status": "vast_onstart_ready_for_archive_transfer_solver_not_started",
    "authorized_key_file_present": True,
    "sshd_expected_to_be_managed_by_vast_entrypoint": True,
    "f40_campaign_executed": False,
    "physical_claims_validated": False,
}
Path(sys.argv[2]).write_text(json.dumps(ready, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
mv "${report_tmp}" "${report}"
mv "${ready_tmp}" "${ready}"
chmod 0644 "${report}" "${ready}"
