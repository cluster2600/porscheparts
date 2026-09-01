#!/usr/bin/env bash
# Vérifie uniquement l'image et le runtime GPU. Ne contacte aucun Content Agent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
[ "$#" -eq 0 ] || { echo "usage: $0 --project-root PATH --output-root PATH --run-id ID --control REPORT" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/readiness/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-readiness.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-readiness.log"
GPU_REPORT="${PHASE_ROOT}/gpu-runtime.json"
phase_init "readiness" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${CONTROL_REPORT}"
phase_add_output "${GPU_REPORT}"
phase_add_child_report "${GPU_REPORT}"
require_job_control
require_command timeout
require_command "${NVIDIA_SMI_BIN}"
require_executable "${CAD_PYTHON}"
# L'on-start de l'image n'écrit READY qu'après le démarrage sain des endpoints.
# Leur première inspection par le workflow reste la phase preflight suivante.
[ -f /workspace/READY ] || { phase_block "marqueur /workspace/READY absent"; exit 2; }

run_logged "${NVIDIA_SMI_BIN}" --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits

refresh_budget
timeout --foreground "${PHASE_REMAINING_SECONDS}s" "${CAD_PYTHON}" - "${GPU_REPORT}" >>"${PHASE_LOG}" 2>&1 <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import physicsnemo
import torch

report_path = Path(sys.argv[1])
version = str(physicsnemo.__version__)
cuda_available = torch.cuda.is_available()
payload = {
    "schema_version": "1.0.0",
    "status": "passed" if version == "2.2.0" and cuda_available else "failed",
    "passed": version == "2.2.0" and cuda_available,
    "classification": "runtime_gpu_ready",
    "claim_scope": "runtime uniquement; aucune simulation moteur exécutée",
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "physicsnemo_version": version,
    "torch_version": torch.__version__,
    "cuda_available": cuda_available,
    "gpu_name": None,
    "gpu_memory_bytes": None,
    "tensor_result": None,
}
if cuda_available:
    properties = torch.cuda.get_device_properties(0)
    tensor = torch.tensor([1.0, 2.0, 3.0], device="cuda")
    result = (tensor * tensor).sum().item()
    torch.cuda.synchronize()
    payload.update(
        gpu_name=properties.name,
        gpu_memory_bytes=properties.total_memory,
        tensor_result=result,
    )
report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if not payload["passed"]:
    raise SystemExit(1)
PY

require_passed_report "${GPU_REPORT}"
phase_pass "image et runtime GPU prêts; aucun Content Agent contacté et aucune simulation moteur exécutée"
