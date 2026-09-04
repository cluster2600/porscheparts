#!/usr/bin/env bash
# Supervise un futur job F46. Sans --execute, aucune API ni aucun secret n'est lu.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
CONTROLLER="${SCRIPT_DIR}/_f46_controller.py"
CONTRACT="${REPOSITORY_ROOT}/twins/reference-917-engine/f46-vast-cfd-cae-controller.json"
JOBS="${REPOSITORY_ROOT}/twins/reference-917-engine/f46-vast-job-manifest.json"
OFFERS=""
IMAGE_PROOF=""
INVENTORY_BEFORE=""
LEDGER=""
OPERATOR_DEADLINE_EPOCH=""
CONTROL_ROOT=""
EXECUTE=0
OPENBAO_VASTAI_BIN="${OPENBAO_VASTAI_BIN:-}"
OPENBAO_GHCR_BIN="${OPENBAO_GHCR_BIN:-}"
VAST_SSH_IDENTITY_FILE="${VAST_SSH_IDENTITY_FILE:-${HOME}/.ssh/id_vastai}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --offers) OFFERS="$2"; shift 2 ;;
        --image-proof) IMAGE_PROOF="$2"; shift 2 ;;
        --inventory-before) INVENTORY_BEFORE="$2"; shift 2 ;;
        --ledger) LEDGER="$2"; shift 2 ;;
        --operator-deadline-epoch) OPERATOR_DEADLINE_EPOCH="$2"; shift 2 ;;
        --control-root) CONTROL_ROOT="$2"; shift 2 ;;
        --execute) EXECUTE=1; shift ;;
        *) printf 'argument inconnu: %s\n' "$1" >&2; exit 2 ;;
    esac
done

[ -n "${OFFERS}" ] && [ -n "${IMAGE_PROOF}" ] && [ -n "${INVENTORY_BEFORE}" ] \
    && [ -n "${LEDGER}" ] && [ -n "${OPERATOR_DEADLINE_EPOCH}" ] \
    || { echo "offres, preuve image, inventaire, ledger et deadline requis" >&2; exit 2; }
[[ "${OPERATOR_DEADLINE_EPOCH}" =~ ^[1-9][0-9]*$ ]] || { echo "deadline invalide" >&2; exit 2; }
CONTROL_ROOT="${CONTROL_ROOT:-${REPOSITORY_ROOT}/work/vast-f46/controller-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "${CONTROL_ROOT}"
PLAN="${CONTROL_ROOT}/plan.json"
NOW_EPOCH="$(date +%s)"

set +e
python3 "${CONTROLLER}" \
    --contract "${CONTRACT}" --jobs "${JOBS}" --root "${REPOSITORY_ROOT}" \
    plan --offers "${OFFERS}" --image-proof "${IMAGE_PROOF}" \
    --inventory-before "${INVENTORY_BEFORE}" --ledger "${LEDGER}" \
    --now-epoch "${NOW_EPOCH}" --operator-deadline-epoch "${OPERATOR_DEADLINE_EPOCH}" \
    --output "${PLAN}"
PLAN_RC=$?
set -e
if [ "${PLAN_RC}" -ne 0 ]; then
    printf 'F46 bloqué sans dépense; voir %s\n' "${PLAN}" >&2
    exit "${PLAN_RC}"
fi
if [ "${EXECUTE}" -ne 1 ]; then
    printf 'Plan F46 recevable mais non exécuté: %s\n' "${PLAN}"
    exit 0
fi

# Le mode mutateur n'est atteint qu'après les portes du plan. Les wrappers
# approuvés sont comparés aux versions suivies sans jamais lire leurs secrets.
[ -n "${OPENBAO_VASTAI_BIN}" ] && [ -n "${OPENBAO_GHCR_BIN}" ] \
    || { echo "wrappers OpenBao explicites requis" >&2; exit 2; }
[[ "${OPENBAO_VASTAI_BIN}" = /* && "${OPENBAO_GHCR_BIN}" = /* ]] \
    || { echo "chemins absolus des wrappers requis" >&2; exit 2; }
cmp -s "${REPOSITORY_ROOT}/deploy/openbao/openbao-vastai" "${OPENBAO_VASTAI_BIN}" \
    || { echo "wrapper Vast différent de la version contrôlée" >&2; exit 1; }
cmp -s "${REPOSITORY_ROOT}/deploy/openbao/openbao-ghcr" "${OPENBAO_GHCR_BIN}" \
    || { echo "wrapper GHCR différent de la version contrôlée" >&2; exit 1; }

read -r OFFER_ID EXPECTED_IMAGE EXPECTED_GPU MAX_DPH LABEL_FAMILY REMOTE_DEADLINE_EPOCH < <(python3 - "${PLAN}" <<'PY'
import json
from pathlib import Path
import sys
p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if p.get("launch_authorized") is not True:
    raise SystemExit("plan sans autorisation de lancement")
o = p["selected_offer"]
print(
    o["id"],
    p["expected_image"],
    o["gpu"],
    p["selected_dph_total_usd"],
    p["expected_label_family"],
    p["remote_deadline_epoch"],
)
PY
)
ATTEMPT_LABEL="$(python3 - "${LABEL_FAMILY}" <<'PY'
import re
import secrets
import sys
family = sys.argv[1]
if family != "3dprinting993-f46-cfd-cae":
    raise SystemExit("famille de label F46 invalide")
label = f"{family}-{secrets.token_hex(10)}"
if re.fullmatch(r"3dprinting993-f46-cfd-cae-[0-9a-f]{20}", label) is None:
    raise SystemExit("label de tentative F46 invalide")
print(label)
PY
)"
python3 - "${PLAN}" "${ATTEMPT_LABEL}" <<'PY'
import json
import os
from pathlib import Path
import re
import sys
path = Path(sys.argv[1])
label = sys.argv[2]
if re.fullmatch(r"3dprinting993-f46-cfd-cae-[0-9a-f]{20}", label) is None:
    raise SystemExit("label de tentative F46 invalide")
plan = json.loads(path.read_text(encoding="utf-8"))
if plan.get("expected_label") is not None:
    raise SystemExit("plan F46 déjà attribué à une tentative")
plan["expected_label"] = label
temporary = path.with_name(path.name + ".partial")
temporary.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(temporary, path)
PY
JOB_ID="f46-${NOW_EPOCH}"
INSTANCE_ID=""
INSTANCE_STARTED_EPOCH="${NOW_EPOCH}"
CLEANUP_ARMED=1
LAUNCH_INVOKED=0
EXPECTED_LABEL="${ATTEMPT_LABEL}"
export OPENBAO_VASTAI_BIN VAST_SSH_IDENTITY_FILE EXPECTED_LABEL EXPECTED_GPU_NAME="${EXPECTED_GPU}"
export MIN_GPU_RAM_MB=48000 MIN_CPU_CORES=24 MIN_CPU_RAM_MB=128000 MIN_DISK_SPACE_GB=500

inventory_after() {
    local raw="${CONTROL_ROOT}/instances-after.raw.json"
    "${OPENBAO_VASTAI_BIN}" instances >"${raw}"
    python3 - "${raw}" "${CONTROL_ROOT}/inventory-after.json" "${LABEL_FAMILY}" <<'PY'
import json
from pathlib import Path
import re
import sys
items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if not isinstance(items, list):
    raise SystemExit("inventaire Vast final invalide")
if any(not isinstance(item, dict) for item in items):
    raise SystemExit("inventaire Vast final contient une entrée invalide")
family = sys.argv[3]
label_re = re.compile(rf"{re.escape(family)}-[0-9a-f]{{20}}")
filtered = [
    item
    for item in items
    if isinstance(item, dict)
    and (item.get("label") == family or label_re.fullmatch(str(item.get("label", ""))))
]
Path(sys.argv[2]).write_text(json.dumps({
    "classification": "production_wrapper_evidence",
    "pagination_complete": True,
    "label_filter": family,
    "instances": filtered,
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not filtered else 1)
PY
}

cleanup_instance_on_exit() {
    local rc=$?
    trap - EXIT INT TERM
    set +e
    if [ "${CLEANUP_ARMED}" -ne 1 ]; then
        return "${rc}"
    fi
    if [ -z "${INSTANCE_ID}" ] && [ -f "${CONTROL_ROOT}/launch.json" ]; then
        INSTANCE_ID="$(python3 - "${CONTROL_ROOT}/launch.json" <<'PY' 2>/dev/null || true
import json
from pathlib import Path
import sys
value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("instance_id")
if isinstance(value, int) and value > 0:
    print(value)
PY
)"
    fi
    if [ -z "${INSTANCE_ID}" ] && [ "${LAUNCH_INVOKED}" -eq 1 ]; then
        # Le label de tentative est persisté avant la requête payante. La
        # réconciliation ne peut donc détruire qu'une instance de cette tentative.
        for _attempt in 1 2 3 4 5; do
            "${OPENBAO_VASTAI_BIN}" reconcile-f46-attempt \
                "${ATTEMPT_LABEL}" "${EXPECTED_IMAGE}" \
                >"${CONTROL_ROOT}/reconcile-f46-${_attempt}.json" \
                2>"${CONTROL_ROOT}/reconcile-f46-${_attempt}.stderr" && break
            sleep 15
        done
    fi
    if [ -n "${INSTANCE_ID}" ]; then
        for _attempt in 1 2 3 4 5; do
            "${REPOSITORY_ROOT}/deploy/vast/simready/destroy-instance.sh" \
                --instance-id "${INSTANCE_ID}" --expected-image "${EXPECTED_IMAGE}" \
                --job-id "${JOB_ID}" --confirm-job-id "${JOB_ID}" \
                --confirm-instance-id "${INSTANCE_ID}" --confirm-digest "${EXPECTED_IMAGE}" \
                --confirm-no-retrieval "NO-RETRIEVAL:${JOB_ID}:${INSTANCE_ID}:${EXPECTED_IMAGE}" \
                --max-actual-dph "${MAX_DPH}" --control-root "${CONTROL_ROOT}" \
                --workflow-profile f46-cfd-cae-v1 && break
            sleep 15
        done
    fi
    inventory_after
    empty_rc=$?
    if [ "${empty_rc}" -eq 0 ] && [ -n "${INSTANCE_ID}" ] \
        && [ -f "${CONTROL_ROOT}/destroy-report.json" ]; then
        python3 - \
            "${LEDGER}" "${CONTROL_ROOT}/cost-current.json" \
            "${CONTROL_ROOT}/ledger-final.json" "${INSTANCE_ID}" \
            "${MAX_DPH}" "${INSTANCE_STARTED_EPOCH}" "$(date +%s)" <<'PY'
from decimal import Decimal
import json
from pathlib import Path
import sys
ledger_path, cost_path, output_path = map(Path, sys.argv[1:4])
instance_id = int(sys.argv[4])
dph = Decimal(sys.argv[5])
started = int(sys.argv[6])
finished = int(sys.argv[7])
ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
prior = Decimal(str(ledger["cumulative_spend_usd"]))
charge = dph * Decimal(max(0, finished - started)) / Decimal(3600)
if cost_path.is_file():
    cost = json.loads(cost_path.read_text(encoding="utf-8"))
    charge = max(charge, Decimal(str(cost["current_conservative_charge_usd"])))
entries = list(ledger["entries"])
entries.append({
    "charge_id": f"vast-instance-{instance_id}",
    "instance_id": instance_id,
    "provider_charge_usd": str(charge.quantize(Decimal("0.000001"))),
    "finalized": True,
    "basis": "conservative_elapsed_dph_or_provider_charge_max",
})
payload = {
    "classification": "production_wrapper_evidence",
    "entries": entries,
    "cumulative_spend_usd": str((prior + charge).quantize(Decimal("0.000001"))),
}
output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
        if [ ! -f "${CONTROL_ROOT}/jobs-state.json" ]; then
            python3 - "${PLAN}" "${CONTROL_ROOT}/jobs-state.json" <<'PY'
import json
from pathlib import Path
import sys
plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
payload = {
    "classification": "production_wrapper_evidence",
    "jobs": [{"id": identifier, "status": "cancelled"} for identifier in plan["job_ids"]],
}
Path(sys.argv[2]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
        fi
        python3 "${CONTROLLER}" \
            --contract "${CONTRACT}" --jobs "${JOBS}" --root "${REPOSITORY_ROOT}" \
            finalize --plan "${PLAN}" --jobs-state "${CONTROL_ROOT}/jobs-state.json" \
            --ledger "${CONTROL_ROOT}/ledger-final.json" \
            --destroy-report "${CONTROL_ROOT}/destroy-report.json" \
            --inventory-after "${CONTROL_ROOT}/inventory-after.json" \
            --output "${CONTROL_ROOT}/final-report.json"
        final_rc=$?
    else
        final_rc=1
    fi
    CLEANUP_ARMED=0
    if [ "${empty_rc}" -ne 0 ] || [ "${final_rc}" -ne 0 ]; then
        echo "cleanup F46, inventaire vide ou budget cumulé non prouvé" >&2
        return 1
    fi
    return "${rc}"
}
trap cleanup_instance_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

LAUNCH_INVOKED=1
"${OPENBAO_GHCR_BIN}" launch-vast-f46 \
    "${OFFER_ID}" "${EXPECTED_IMAGE}" "${REMOTE_DEADLINE_EPOCH}" \
    --attempt-label "${ATTEMPT_LABEL}" \
    | tee "${CONTROL_ROOT}/launch.json"
INSTANCE_ID="$(python3 - "${CONTROL_ROOT}/launch.json" "${PLAN}" <<'PY'
import json
import os
from pathlib import Path
import sys
launch_path, plan_path = map(Path, sys.argv[1:])
launch = json.loads(launch_path.read_text(encoding="utf-8"))
plan = json.loads(plan_path.read_text(encoding="utf-8"))
instance_id = launch.get("instance_id")
if not isinstance(instance_id, int) or instance_id <= 0:
    raise SystemExit("instance F46 absente")
if launch.get("image") != plan.get("expected_image") or launch.get("label") != plan.get("expected_label"):
    raise SystemExit("postconditions de lancement F46 différentes")
if launch.get("singleton_verified") is not True or launch.get("contract_verified") is not True:
    raise SystemExit("unicité ou contrat F46 non vérifié")
if launch.get("remote_deadline_epoch") != plan.get("remote_deadline_epoch"):
    raise SystemExit("deadline distante F46 différente")
if launch.get("remote_watchdog_armed") is not True:
    raise SystemExit("watchdog distant F46 non armé")
plan["selected_instance_id"] = instance_id
temporary = plan_path.with_name(plan_path.name + ".partial")
temporary.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(temporary, plan_path)
print(instance_id)
PY
)"

. "${REPOSITORY_ROOT}/deploy/vast/simready/_controller_common.sh"
"${REPOSITORY_ROOT}/deploy/vast/simready/check-instance.sh" \
    --instance-id "${INSTANCE_ID}" --expected-image "${EXPECTED_IMAGE}" \
    --max-actual-dph "${MAX_DPH}" --ready-timeout-seconds 1200 \
    --known-hosts "${CONTROL_ROOT}/known_hosts" \
    --report "${CONTROL_ROOT}/instance-ready.json"
guard_and_prepare_ssh \
    "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${MAX_DPH}" \
    "${CONTROL_ROOT}/instance-guard.json" "${CONTROL_ROOT}/known_hosts" \
    created loading running

# Les deux horloges consomment exactement la même valeur. Le runner de l'image
# doit interrompre chaque commande avant compute_stop_epoch; le contrôleur local
# reste responsable de la destruction de l'instance.
controller_ssh "mkdir -p '/workspace/f46/${JOB_ID}'"
controller_ssh "dd of='/workspace/f46/${JOB_ID}/plan.json' status=none" <"${PLAN}"
controller_ssh "dd of='/workspace/f46/${JOB_ID}/jobs.json' status=none" <"${JOBS}"
controller_ssh "nohup f46-run-manifest --plan '/workspace/f46/${JOB_ID}/plan.json' --manifest '/workspace/f46/${JOB_ID}/jobs.json' --output '/workspace/f46/${JOB_ID}/jobs-state.json' >'/workspace/f46/${JOB_ID}/runner.log' 2>&1 &"

INSTANCE_STARTED_EPOCH="$(date +%s)"
while :; do
    now="$(date +%s)"
    "${OPENBAO_VASTAI_BIN}" show "${INSTANCE_ID}" >"${CONTROL_ROOT}/instance-current.raw.json"
    python3 - \
        "${CONTROL_ROOT}/instance-current.raw.json" \
        "${CONTROL_ROOT}/instance-current.json" \
        "${INSTANCE_STARTED_EPOCH}" <<'PY'
import json
from pathlib import Path
import sys
source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
source["classification"] = "production_wrapper_evidence"
source["started_at_epoch"] = int(sys.argv[3])
# Le wrapper ne déclare pas aujourd'hui une charge accumulée. Zéro n'est pas
# utilisé comme estimation : le contrôleur prend le maximum avec durée*dph.
source["provider_charge_usd"] = 0
Path(sys.argv[2]).write_text(json.dumps(source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
    set +e
    python3 "${CONTROLLER}" \
        --contract "${CONTRACT}" --jobs "${JOBS}" --root "${REPOSITORY_ROOT}" \
        cost-check --plan "${PLAN}" --ledger "${LEDGER}" \
        --instance "${CONTROL_ROOT}/instance-current.json" --now-epoch "${now}" \
        --output "${CONTROL_ROOT}/cost-current.json"
    COST_RC=$?
    set -e
    if [ "${COST_RC}" -ne 0 ]; then
        controller_ssh "touch '/workspace/f46/${JOB_ID}/STOP'" || true
        break
    fi
    compute_stop="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["compute_stop_epoch"])' "${PLAN}")"
    if [ "${now}" -ge "${compute_stop}" ]; then
        controller_ssh "touch '/workspace/f46/${JOB_ID}/STOP'" || true
        break
    fi
    if controller_ssh "test -f '/workspace/f46/${JOB_ID}/jobs-state.json'"; then
        controller_ssh "dd if='/workspace/f46/${JOB_ID}/jobs-state.json' status=none" \
            >"${CONTROL_ROOT}/jobs-state.json"
        break
    fi
    sleep 60
done

# La sortie normale passe elle aussi par le trap de destruction et par la preuve
# d'inventaire vide. Aucun chemin ne désarme CLEANUP_ARMED avant ce point.
exit 0
