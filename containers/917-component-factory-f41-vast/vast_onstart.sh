#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "vast_onstart_requires_root" >&2
    exit 77
fi

/opt/917-component-factory-f41-vast/prepare_layout.sh

host_key_marker=/run/sshd/f41-runtime-host-keys.ready
test -f "${host_key_marker}" || { echo "vast_runtime_host_key_marker_missing" >&2; exit 83; }
test ! -L "${host_key_marker}" || { echo "vast_runtime_host_key_marker_symlink_rejected" >&2; exit 84; }
test "$(stat -c '%u:%g:%a' "${host_key_marker}")" = "0:0:600" || {
    echo "vast_runtime_host_key_marker_metadata_rejected" >&2
    exit 85
}

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

python /opt/917-component-factory-f41-vast/image_smoke.py \
    --expect-runtime-authorized-keys >"${report_tmp}"
python - "${report_tmp}" "${ready_tmp}" <<'PY'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = "offline_transport_and_cad_step_smoke_passed_vast_f41_and_manufacturing_validation_blocked"
if report.get("status") != expected:
    raise SystemExit("image smoke status rejected")
ready = {
    "schema_version": "1.0.0",
    "status": "vast_onstart_ready_for_public_archive_transfer_cad_not_started",
    "authorized_key_file_present": True,
    "runtime_host_keys_generated_before_onstart": True,
    "sshd_managed_by_vast_entrypoint": True,
    "synthetic_build123d_step_smoke_passed": True,
    "f41_component_factory_executed": False,
    "physical_claims_validated": False,
    "manufacturing_authorized": False,
}
Path(sys.argv[2]).write_text(
    json.dumps(ready, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY
mv "${report_tmp}" "${report}"
mv "${ready_tmp}" "${ready}"
chmod 0644 "${report}" "${ready}"
