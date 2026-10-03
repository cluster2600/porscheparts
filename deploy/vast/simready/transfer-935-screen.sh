#!/usr/bin/env bash
# Transfère seulement le proxy 935 versionné et le skill NVIDIA explicite.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_controller_common.sh"
INSTANCE_ID=""; EXPECTED_IMAGE=""; JOB_ID=""; SKILL_ROOT=""; CONTROL_ROOT=""; KNOWN_HOSTS=""; MAX_DPH="${MAX_ACTUAL_DPH}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --instance-id) INSTANCE_ID="$2"; shift 2;; --expected-image) EXPECTED_IMAGE="$2"; shift 2;;
    --job-id) JOB_ID="$2"; shift 2;; --skill-root) SKILL_ROOT="$2"; shift 2;;
    --control-root) CONTROL_ROOT="$2"; shift 2;; --known-hosts) KNOWN_HOSTS="$2"; shift 2;;
    --max-actual-dph) MAX_DPH="$2"; shift 2;; *) controller_die "argument inconnu: $1";;
  esac
done
[ -n "$INSTANCE_ID" ] && [ -n "$EXPECTED_IMAGE" ] && [ -n "$JOB_ID" ] && [ -n "$SKILL_ROOT" ] || controller_die "paramètres requis absents"
validate_controller_id "$JOB_ID"; validate_pinned_image "$EXPECTED_IMAGE"
[ -f "$SKILL_ROOT/SKILL.md" ] && [ "$(basename "$SKILL_ROOT")" = "omniverse-cad-to-simready" ] || controller_die "skill NVIDIA explicite absent"
PROJECT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
SCREEN="twins/935-horizontal-cooling-system-f0/vast-omniverse-screen"
INPUT_CONTRACT="twins/935-horizontal-cooling-system"
FILES=(
  "$SCREEN/README.md" "$SCREEN/materials.json" "$SCREEN/scenario.json"
  "$SCREEN/material-prompt.txt" "$SCREEN/physics-prompt.txt" "$SCREEN/source/run_campaign.py"
  "$INPUT_CONTRACT/data/input-matrix.json" "$INPUT_CONTRACT/research/coverage.json"
)
for file in "${FILES[@]}"; do
  [ -f "$PROJECT_ROOT/$file" ] || controller_die "source absente: $file"
  git -C "$PROJECT_ROOT" ls-files --error-unmatch -- "$file" >/dev/null || controller_die "source non suivie: $file"
done
git -C "$PROJECT_ROOT" diff --quiet -- "${FILES[@]}" || controller_die "sources 935 non commitées"
git -C "$PROJECT_ROOT" diff --cached --quiet -- "${FILES[@]}" || controller_die "sources 935 indexées non commitées"
CONTROL_ROOT="${CONTROL_ROOT:-$PROJECT_ROOT/work/935-vast-omniverse/controller/$JOB_ID}"
KNOWN_HOSTS="${KNOWN_HOSTS:-$CONTROL_ROOT/known_hosts}"
mkdir -p "$CONTROL_ROOT"
guard_and_prepare_ssh "$INSTANCE_ID" "$EXPECTED_IMAGE" "$MAX_DPH" "$CONTROL_ROOT/instance-guard-transfer.json" "$KNOWN_HOSTS" running
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
REVISION="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
python3 - "$PROJECT_ROOT" "$REVISION" "$TMP/source-manifest.json" "${FILES[@]}" <<'PY'
from datetime import datetime, timezone
import hashlib, json
from pathlib import Path
import subprocess, sys
root, revision, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
entries=[]
for rel in sys.argv[4:]:
    blob=subprocess.run(["git","-C",str(root),"rev-parse",f"{revision}:{rel}"],check=True,capture_output=True,text=True).stdout.strip()
    path=root/rel
    entries.append({"path":rel,"git_blob":blob,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
out.write_text(json.dumps({"schema_version":"1.0.0","source_revision":revision,"generated_at":datetime.now(timezone.utc).isoformat(),"files":entries},indent=2,sort_keys=True)+"\n")
PY
python3 - "$TMP/job-control.json" "$JOB_ID" "$INSTANCE_ID" "$EXPECTED_IMAGE" "$REVISION" <<'PY'
from datetime import datetime, timezone
import json, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({"schema_version":"1.0.0","job_id":sys.argv[2],"instance_id":int(sys.argv[3]),"expected_image":sys.argv[4],"source_revision":sys.argv[5],"scope":"935_parametric_proxy_only_no_private_scan","created_at":datetime.now(timezone.utc).isoformat()},indent=2,sort_keys=True)+"\n")
PY
PARTIAL="/workspace/jobs/${JOB_ID}.partial"; FINAL="/workspace/jobs/${JOB_ID}"
controller_ssh "test ! -e '$FINAL' && test ! -e '$PARTIAL' && mkdir -p '$PARTIAL/project' '$PARTIAL/vendor' '$PARTIAL/control'"
(cd "$PROJECT_ROOT" && COPYFILE_DISABLE=1 tar -cf - "${FILES[@]}") | controller_ssh "tar -xf - -C '$PARTIAL/project'"
(cd "$(dirname "$SKILL_ROOT")" && COPYFILE_DISABLE=1 tar -cf - "$(basename "$SKILL_ROOT")") | controller_ssh "tar -xf - -C '$PARTIAL/vendor'"
(cd "$TMP" && tar -cf - job-control.json source-manifest.json) | controller_ssh "tar -xf - -C '$PARTIAL/control'"
controller_ssh "chmod -R go-w '$PARTIAL' && mv '$PARTIAL' '$FINAL'"
python3 - "$CONTROL_ROOT/transfer-report.json" "$JOB_ID" "$INSTANCE_ID" "$EXPECTED_IMAGE" "$REVISION" "$TMP/source-manifest.json" <<'PY'
from datetime import datetime, timezone
import hashlib, json, sys
from pathlib import Path
manifest=Path(sys.argv[6])
payload={"schema_version":"1.0.0","status":"passed","passed":True,"job_id":sys.argv[2],"instance_id":int(sys.argv[3]),"expected_image":sys.argv[4],"source_revision":sys.argv[5],"source_manifest_sha256":hashlib.sha256(manifest.read_bytes()).hexdigest(),"source_policy":"tracked clean allowlist only; no raw scans; 935 matrix retains zero admitted numeric physical claims","remote_project_root":f"/workspace/jobs/{sys.argv[2]}/project","remote_skill_root":f"/workspace/jobs/{sys.argv[2]}/vendor/omniverse-cad-to-simready","finished_at":datetime.now(timezone.utc).isoformat()}
Path(sys.argv[1]).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
PY
printf '%s\n' "$CONTROL_ROOT/transfer-report.json"
