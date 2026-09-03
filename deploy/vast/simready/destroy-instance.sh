#!/usr/bin/env bash
# Détruit l'instance seulement après récupération vérifiée et confirmation exacte du job.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_controller_common.sh"

INSTANCE_ID=""
EXPECTED_IMAGE=""
JOB_ID=""
CONFIRM_JOB_ID=""
CONFIRM_INSTANCE_ID=""
CONFIRM_DIGEST=""
CONFIRM_NO_RETRIEVAL=""
RETRIEVAL_REPORT=""
MAX_DPH="${MAX_ACTUAL_DPH}"
CONTROL_ROOT=""
WORKFLOW_PROFILE="legacy-f10"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --instance-id) INSTANCE_ID="$2"; shift 2 ;;
        --expected-image) EXPECTED_IMAGE="$2"; shift 2 ;;
        --job-id) JOB_ID="$2"; shift 2 ;;
        --confirm-job-id) CONFIRM_JOB_ID="$2"; shift 2 ;;
        --confirm-instance-id) CONFIRM_INSTANCE_ID="$2"; shift 2 ;;
        --confirm-digest) CONFIRM_DIGEST="$2"; shift 2 ;;
        --confirm-no-retrieval) CONFIRM_NO_RETRIEVAL="$2"; shift 2 ;;
        --retrieval-report) RETRIEVAL_REPORT="$2"; shift 2 ;;
        --max-actual-dph) MAX_DPH="$2"; shift 2 ;;
        --control-root) CONTROL_ROOT="$2"; shift 2 ;;
        --workflow-profile) WORKFLOW_PROFILE="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INSTANCE_ID}" ] && [ -n "${EXPECTED_IMAGE}" ] && [ -n "${JOB_ID}" ] \
    || controller_die "paramètres requis absents"
[ "${CONFIRM_JOB_ID}" = "${JOB_ID}" ] || controller_die "confirmation du job différente"
[ "${CONFIRM_INSTANCE_ID}" = "${INSTANCE_ID}" ] || controller_die "confirmation de l'instance différente"
[ "${CONFIRM_DIGEST}" = "${EXPECTED_IMAGE}" ] || controller_die "confirmation du digest différente"
validate_controller_id "${JOB_ID}"
validate_pinned_image "${EXPECTED_IMAGE}"
case "${WORKFLOW_PROFILE}" in
    legacy-f10) RETRIEVAL_SUMMARIZER="${SCRIPT_DIR}/_summarize_retrieval.py" ;;
    f42b-six-usd-v1)
        RETRIEVAL_SUMMARIZER="${SCRIPT_DIR}/_summarize_f42b_retrieval.py"
        PRIVATE_DESTINATION_HELPER="${SCRIPT_DIR}/_private_destination.py"
        [ -f "${PRIVATE_DESTINATION_HELPER}" ] || controller_die "helper de destination privée F42b absent"
        ;;
    *) controller_die "--workflow-profile doit être legacy-f10 ou f42b-six-usd-v1" ;;
esac
require_vast_wrapper
CONTROL_ROOT="${CONTROL_ROOT:-${REPOSITORY_ROOT}/work/vast-simready/controller/${JOB_ID}}"
mkdir -p "${CONTROL_ROOT}"
RETRIEVAL_PROOF="${CONTROL_ROOT}/retrieval-proof-for-destroy.json"
if [ -n "${RETRIEVAL_REPORT}" ]; then
python3 - "${RETRIEVAL_REPORT}" "${JOB_ID}" "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${RETRIEVAL_PROOF}" "${RETRIEVAL_SUMMARIZER}" "${WORKFLOW_PROFILE}" "${PRIVATE_DESTINATION_HELPER:-}" <<'PY'
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import tempfile

MAX_ARCHIVE_MEMBERS = 100_000
MAX_ARCHIVE_CONTENT_BYTES = 128 * 1024**3
MAX_ARCHIVE_FILE_BYTES = 64 * 1024**3
MAX_ARCHIVE_PATH_BYTES = 1024


def checked_member_path(member: tarfile.TarInfo, job_id: str) -> tuple[PurePosixPath, str]:
    raw_name = member.name
    if not isinstance(raw_name, str) or not raw_name:
        raise SystemExit("nom de membre d'archive vide ou invalide")
    if member.isdir() and raw_name.endswith("/"):
        raw_name = raw_name[:-1]
    if (
        not raw_name
        or not raw_name.isascii()
        or "\\" in raw_name
        or any(ord(character) < 32 or ord(character) == 127 for character in raw_name)
    ):
        raise SystemExit(f"nom de membre d'archive ambigu: {member.name!r}")
    raw_parts = raw_name.split("/")
    if any(part in ("", ".", "..") for part in raw_parts):
        raise SystemExit(f"nom de membre d'archive ambigu: {member.name!r}")
    path = PurePosixPath(raw_name)
    if (
        path.is_absolute()
        or path.as_posix() != raw_name
        or not path.parts
        or path.parts[0] != job_id
        or len(raw_name.encode("ascii")) > MAX_ARCHIVE_PATH_BYTES
        or any(len(part.encode("ascii")) > 255 for part in path.parts)
    ):
        raise SystemExit(f"membre d'archive interdit: {member.name!r}")
    return path, raw_name


def extract_verified_archive(archive_handle, destination: Path, job_id: str) -> Path:
    members: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
    exact_names: set[str] = set()
    collision_names: dict[str, str] = {}
    top_levels: set[str] = set()
    total_content_bytes = 0
    try:
        with tarfile.open(fileobj=archive_handle, mode="r:gz") as handle:
            for index, member in enumerate(handle):
                if index >= MAX_ARCHIVE_MEMBERS:
                    raise SystemExit(
                        f"archive trop volumineuse: plus de {MAX_ARCHIVE_MEMBERS} membres"
                    )
                path, exact_name = checked_member_path(member, job_id)
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise SystemExit(f"type de membre d'archive interdit: {member.name!r}")
                if member.size < 0 or (member.isdir() and member.size != 0):
                    raise SystemExit(f"taille de membre d'archive invalide: {member.name!r}")
                if member.isfile() and member.size > MAX_ARCHIVE_FILE_BYTES:
                    raise SystemExit(f"fichier d'archive trop volumineux: {member.name!r}")
                total_content_bytes += member.size if member.isfile() else 0
                if total_content_bytes > MAX_ARCHIVE_CONTENT_BYTES:
                    raise SystemExit(
                        "contenu décompressé de l'archive supérieur à la limite de sécurité"
                    )
                collision_name = exact_name.casefold()
                previous = collision_names.get(collision_name)
                if exact_name in exact_names or (previous is not None and previous != exact_name):
                    raise SystemExit(f"nom de membre d'archive dupliqué ou ambigu: {member.name!r}")
                exact_names.add(exact_name)
                collision_names[collision_name] = exact_name
                top_levels.add(path.parts[0])
                members.append((member, path))
            if not members:
                raise SystemExit("archive de récupération vide")
            if top_levels != {job_id}:
                raise SystemExit("l'archive ne contient pas exactement le répertoire racine du job")

            for member, path in sorted(members, key=lambda item: (len(item[1].parts), item[1].as_posix())):
                target = destination.joinpath(*path.parts)
                if member.isdir():
                    if target.exists() and not target.is_dir():
                        raise SystemExit(f"collision fichier/répertoire dans l'archive: {member.name!r}")
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    raise SystemExit(f"cible d'extraction déjà présente: {member.name!r}")
                source = handle.extractfile(member)
                if source is None:
                    raise SystemExit(f"contenu de fichier d'archive inaccessible: {member.name!r}")
                copied = 0
                with source, target.open("xb") as output:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > member.size:
                            raise SystemExit(f"taille extraite incohérente: {member.name!r}")
                        output.write(chunk)
                if copied != member.size:
                    raise SystemExit(f"taille extraite incohérente: {member.name!r}")
    except (tarfile.TarError, EOFError, OSError) as error:
        raise SystemExit(f"archive de récupération invalide: {error}") from error

    exact_root = destination / job_id
    extracted_entries = list(destination.iterdir())
    if (
        len(extracted_entries) != 1
        or extracted_entries[0] != exact_root
        or not exact_root.is_dir()
        or exact_root.is_symlink()
    ):
        raise SystemExit("réextraction sans répertoire racine unique et exact du job")
    return exact_root


report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if report.get("job_id") != sys.argv[2] or report.get("instance_id") != int(sys.argv[3]) or report.get("expected_image") != sys.argv[4]:
    raise SystemExit("rapport de récupération différent du job/instance/digest")
if report.get("workflow_profile", "legacy-f10") != sys.argv[7]:
    raise SystemExit("rapport de récupération produit pour un autre profil fermé")
if sys.argv[7] == "f42b-six-usd-v1":
    helper_path = Path(sys.argv[8]).resolve(strict=True)
    helper_spec = importlib.util.spec_from_file_location("f42b_private_destination", helper_path)
    if helper_spec is None or helper_spec.loader is None:
        raise SystemExit("helper de destination privée F42b indisponible")
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    archive_from_report = Path(str(report.get("archive_path", ""))).resolve(strict=True)
    destination = helper.prepare_destination(archive_from_report.parent, helper_path.parents[3])
    persistent_root = Path(str(report.get("extracted_root", ""))).resolve(strict=True)
    if persistent_root != destination / sys.argv[2] or persistent_root.is_symlink():
        raise SystemExit("racine extraite F42b hors de la destination privée exacte")
    policy = report.get("private_destination_policy")
    if not isinstance(policy, dict) or policy != {
        "passed": True,
        "destination_root": str(destination),
        "outside_git_worktree": True,
        "owner_uid": destination.lstat().st_uid,
        "mode": "0700",
        "symlink": False,
    }:
        raise SystemExit("frontière privée F42b absente ou incohérente")
if report.get("retrieval_attempted") is not True or report.get("artifact_archive_verified") is not True:
    raise SystemExit("archive de récupération non vérifiée")
if report.get("retrieval_complete") is not True:
    raise SystemExit(
        "récupération partielle: utiliser la confirmation NO-RETRIEVAL explicite pour le cleanup"
    )
archive = Path(report.get("archive_path", ""))
expected_archive_digest = report.get("archive_sha256")
if not isinstance(expected_archive_digest, str) or re.fullmatch(r"[0-9a-f]{64}", expected_archive_digest) is None:
    raise SystemExit("checksum attendu de l'archive récupérée invalide")
open_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
try:
    archive_descriptor = os.open(archive, open_flags)
except OSError as error:
    raise SystemExit(f"archive récupérée absente ou non sûre: {error}") from error
spec = importlib.util.spec_from_file_location("vast_retrieval", sys.argv[6])
if spec is None or spec.loader is None:
    raise SystemExit("résumeur de récupération indisponible")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with os.fdopen(archive_descriptor, "rb") as archive_handle:
    archive_stat = os.fstat(archive_handle.fileno())
    if not stat.S_ISREG(archive_stat.st_mode) or archive_stat.st_size <= 0:
        raise SystemExit("archive récupérée absente ou non régulière")
    digest = hashlib.sha256()
    for chunk in iter(lambda: archive_handle.read(1024 * 1024), b""):
        digest.update(chunk)
    verified_archive_digest = digest.hexdigest()
    if verified_archive_digest != expected_archive_digest:
        raise SystemExit("checksum de l'archive récupérée différent")
    archive_handle.seek(0)
    with tempfile.TemporaryDirectory(prefix="3dprinting993-destroy-") as temporary:
        exact_root = extract_verified_archive(archive_handle, Path(temporary), sys.argv[2])
        summary_root = exact_root
        if sys.argv[7] == "f42b-six-usd-v1":
            def tree_manifest(root: Path) -> list[tuple[str, int, str]]:
                entries = []
                for candidate in sorted(root.rglob("*")):
                    info = candidate.lstat()
                    relative = candidate.relative_to(root).as_posix()
                    if stat.S_ISLNK(info.st_mode) or not (
                        stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)
                    ):
                        raise SystemExit("type de fichier persistant F42b interdit")
                    file_digest = ""
                    if stat.S_ISREG(info.st_mode):
                        value = hashlib.sha256()
                        with candidate.open("rb") as handle:
                            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                                value.update(chunk)
                        file_digest = value.hexdigest()
                    entries.append((relative, info.st_size if stat.S_ISREG(info.st_mode) else 0, file_digest))
                return entries

            if tree_manifest(exact_root) != tree_manifest(persistent_root):
                raise SystemExit("racine F42b persistante différente de l'archive vérifiée")
            summary_root = persistent_root
        try:
            recomputed = module.summarize(
                summary_root, archive, sys.argv[2], int(sys.argv[3]), sys.argv[4]
            )
        except Exception as error:
            raise SystemExit(f"résumé de récupération impossible: {error}") from error
        if recomputed.get("archive_sha256") != verified_archive_digest:
            raise SystemExit("l'archive a changé pendant le recalcul de récupération")
if recomputed.get("retrieval_complete") is not True:
    raise SystemExit(
        "récupération recalculée partielle: utiliser la confirmation NO-RETRIEVAL explicite pour le cleanup"
    )
if recomputed.get("workflow_profile", "legacy-f10") != sys.argv[7]:
    raise SystemExit("résumé recalculé produit pour un autre profil fermé")
derived_simulation_validated = recomputed.get("simulation_validated") is True
derived_simready_validated = recomputed.get("simready_validated") is True
proof = {
    "retrieval_waived": False,
    "retrieval_report": str(Path(sys.argv[1]).resolve()),
    "artifact_archive_verified": True,
    "retrieval_complete": True,
    "workflow_profile": sys.argv[7],
    "simready_validated": bool(derived_simready_validated),
    "simulation_validated": bool(derived_simulation_validated),
}
Path(sys.argv[5]).write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
else
    EXPECTED_WAIVER="NO-RETRIEVAL:${JOB_ID}:${INSTANCE_ID}:${EXPECTED_IMAGE}"
    [ "${CONFIRM_NO_RETRIEVAL}" = "${EXPECTED_WAIVER}" ] \
        || controller_die "rapport de récupération absent; confirmation NO-RETRIEVAL exacte requise"
    python3 - "${RETRIEVAL_PROOF}" "${WORKFLOW_PROFILE}" <<'PY'
import json
from pathlib import Path
import sys
proof = {
    "retrieval_waived": True,
    "retrieval_report": None,
    "artifact_archive_verified": False,
    "retrieval_complete": False,
    "workflow_profile": sys.argv[2],
    "simready_validated": False,
    "simulation_validated": False,
    "reason": "récupération impossible ou aucun artefact distant disponible; cleanup explicitement confirmé",
}
Path(sys.argv[1]).write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
fi
GUARD_REPORT="${CONTROL_ROOT}/instance-guard-destroy.json"
python3 "${INSTANCE_GUARD}" \
    --wrapper "${OPENBAO_VASTAI_BIN}" \
    --instance-id "${INSTANCE_ID}" \
    --expected-image "${EXPECTED_IMAGE}" \
    --expected-label "${EXPECTED_LABEL}" \
    --max-actual-dph "${MAX_DPH}" \
    --skip-cost-cap \
    --skip-capability-floor \
    --allowed-status running \
    --allowed-status stopped \
    --allowed-status loading \
    --allowed-status created \
    --allowed-status exited \
    --report "${GUARD_REPORT}" >/dev/null
DESTROY_OUTPUT="${CONTROL_ROOT}/destroy-wrapper-output.json"
"${OPENBAO_VASTAI_BIN}" destroy "${INSTANCE_ID}" --confirm >"${DESTROY_OUTPUT}"
python3 - "${DESTROY_OUTPUT}" "${CONTROL_ROOT}/destroy-report.json" "${JOB_ID}" "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${RETRIEVAL_PROOF}" "${WORKFLOW_PROFILE}" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
wrapper = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if (
    wrapper.get("instance_id") != int(sys.argv[4])
    or wrapper.get("destroyed") is not True
    or wrapper.get("verified_absent") is not True
):
    raise SystemExit("le wrapper n'a pas confirmé la destruction")
retrieval = json.loads(Path(sys.argv[6]).read_text(encoding="utf-8"))
payload = {
    "schema_version": "1.0.0", "status": "passed", "passed": True,
    "job_id": sys.argv[3], "instance_id": int(sys.argv[4]), "expected_image": sys.argv[5],
    "workflow_profile": sys.argv[7],
    "retrieval_waived": retrieval["retrieval_waived"],
    "artifact_archive_verified": retrieval["artifact_archive_verified"],
    "retrieval_complete": retrieval["retrieval_complete"],
    "simready_validated": retrieval["simready_validated"],
    "simulation_validated": retrieval["simulation_validated"],
    "verified_absent": True,
    "destroyed_at": datetime.now(timezone.utc).isoformat(),
}
Path(sys.argv[2]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
printf '%s\n' "${CONTROL_ROOT}/destroy-report.json"
