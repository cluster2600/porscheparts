#!/usr/bin/env bash
# Transfère le profil fermé F42b et exactement les six USD privés attestés par F42a.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_controller_common.sh"

# Les attestations Git doivent être indépendantes de toute redirection de dépôt
# héritée du shell appelant (GIT_DIR, GIT_WORK_TREE, GIT_CONFIG_*, etc.).
while IFS= read -r git_variable; do
    case "${git_variable}" in
        GIT_*) unset "${git_variable}" ;;
    esac
done < <(compgen -v)
unset git_variable

WORKFLOW_PROFILE="f42b-six-usd-v1"
INSTANCE_ID=""
EXPECTED_IMAGE=""
JOB_ID=""
SKILL_ROOT=""
MATERIAL_PROMPT=""
PHYSICS_PROMPT=""
F42A_OUTPUT_ROOT=""
MAX_DPH="${MAX_ACTUAL_DPH}"
MAX_RUNTIME_MINUTES=180
LOCAL_CONTROL_ROOT=""
KNOWN_HOSTS=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --instance-id) INSTANCE_ID="$2"; shift 2 ;;
        --expected-image) EXPECTED_IMAGE="$2"; shift 2 ;;
        --job-id) JOB_ID="$2"; shift 2 ;;
        --skill-root) SKILL_ROOT="$2"; shift 2 ;;
        --material-prompt) MATERIAL_PROMPT="$2"; shift 2 ;;
        --physics-prompt) PHYSICS_PROMPT="$2"; shift 2 ;;
        --f42a-output-root) F42A_OUTPUT_ROOT="$2"; shift 2 ;;
        --max-actual-dph) MAX_DPH="$2"; shift 2 ;;
        --max-runtime-minutes) MAX_RUNTIME_MINUTES="$2"; shift 2 ;;
        --control-root) LOCAL_CONTROL_ROOT="$2"; shift 2 ;;
        --known-hosts) KNOWN_HOSTS="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INSTANCE_ID}" ] && [ -n "${EXPECTED_IMAGE}" ] && [ -n "${JOB_ID}" ] \
    && [ -n "${SKILL_ROOT}" ] && [ -n "${F42A_OUTPUT_ROOT}" ] \
    || controller_die "paramètres instance/image/job/skill/f42a-output-root requis"
[ -n "${MATERIAL_PROMPT}" ] && [ -n "${PHYSICS_PROMPT}" ] \
    || controller_die "les prompts Material et Physics sont obligatoires"
validate_controller_id "${JOB_ID}"
validate_pinned_image "${EXPECTED_IMAGE}"
[[ "${MAX_RUNTIME_MINUTES}" =~ ^[1-9][0-9]*$ ]] && [ "${MAX_RUNTIME_MINUTES}" -le 360 ] \
    || controller_die "--max-runtime-minutes doit être compris entre 1 et 360"
[ -f "${SKILL_ROOT}/SKILL.md" ] || controller_die "skill NVIDIA explicite absent"
[ "$(basename "${SKILL_ROOT}")" = "omniverse-cad-to-simready" ] \
    || controller_die "répertoire skill inattendu"

validate_prompt() {
    local prompt="$1" label="$2" staged="$3"
    [ -f "${prompt}" ] || controller_die "prompt ${label} absent"
    python3 - "${prompt}" "${staged}" <<'PY'
import os
from pathlib import Path
import re
import stat
import sys

path = Path(sys.argv[1])
flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
try:
    descriptor = os.open(path, flags)
except OSError as error:
    raise SystemExit(f"prompt absent ou non sûr: {error}") from error
with os.fdopen(descriptor, "rb") as handle:
    info = os.fstat(handle.fileno())
    if not stat.S_ISREG(info.st_mode):
        raise SystemExit("prompt doit être un fichier régulier non symlink")
    data = handle.read(20_001)
if not data or len(data) > 20_000 or b"\0" in data:
    raise SystemExit("prompt vide, binaire ou trop volumineux")
text = data.decode("utf-8")
if re.search(r"(?im)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]", text):
    raise SystemExit("champ ressemblant à un secret interdit dans le prompt")
staged = Path(sys.argv[2])
with staged.open("xb") as handle:
    handle.write(data)
staged.chmod(0o600)
PY
}

TEMPORARY="$(mktemp -d)"
chmod 700 "${TEMPORARY}"
trap 'rm -r -- "${TEMPORARY}"' EXIT
STAGED_MATERIAL_PROMPT="${TEMPORARY}/material-prompt.txt"
STAGED_PHYSICS_PROMPT="${TEMPORARY}/physics-prompt.txt"
STAGED_RUNTIME_ATTESTATION="${TEMPORARY}/runtime-attestation.json"
STAGED_GHCR_WRAPPER="${TEMPORARY}/approved-openbao-ghcr"
RUNTIME_ATTESTATION_NONCE="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
validate_prompt "${MATERIAL_PROMPT}" material "${STAGED_MATERIAL_PROMPT}"
validate_prompt "${PHYSICS_PROMPT}" physics "${STAGED_PHYSICS_PROMPT}"

GIT_BIN="/usr/bin/git"
[ -x "${GIT_BIN}" ] || controller_die "binaire Git système approuvé absent"
REVISION="$("${GIT_BIN}" -C "${REPOSITORY_ROOT}" rev-parse HEAD)"
[[ "${REVISION}" =~ ^[0-9a-f]{40}$ ]] || controller_die "révision Git complète invalide"
SOURCE_FILES=(
    catalog/sources/src-fia-917-homologation-250.json
    catalog/sources/src-stuttcars-917-technical-details.json
    docs/917_GERMAN_SOURCE_AND_MEASUREMENT_MATRIX_F29.md
    deploy/openbao/openbao-vastai
    deploy/openbao/openbao-ghcr
    deploy/vast/simready/_materialize_git_snapshot.py
    twins/reference-917-engine/component-factory-f42b-gpu.json
    twins/reference-917-engine/evidence/f42a-cpu-usd/repeatability-summary.json
    twins/reference-917-engine/evidence/f42b-gpu-runtime-qualification.json
    twins/reference-917-engine/mechanical-connections-f8.json
    twins/reference-917-engine/motion-video-f7.json
    twins/reference-917-engine/remote-simready/_common.sh
    twins/reference-917-engine/remote-simready/_bundle_manifest.py
    twins/reference-917-engine/remote-simready/_report.py
    twins/reference-917-engine/remote-simready/_validate-one.sh
    twins/reference-917-engine/remote-simready/phase-readiness.sh
    twins/reference-917-engine/remote-simready/phase-preflight.sh
    twins/reference-917-engine/remote-simready/phase-conform.sh
    twins/reference-917-engine/remote-simready/phase-validate-asset.sh
    twins/reference-917-engine/remote-simready/phase-validate-geometry.sh
    twins/reference-917-engine/remote-simready/phase-validate-physics.sh
    twins/reference-917-engine/remote-simready/f42b/_contract.py
    twins/reference-917-engine/remote-simready/f42b/phase-minimum-usd.sh
    twins/reference-917-engine/remote-simready/f42b/phase-material.sh
    twins/reference-917-engine/remote-simready/f42b/phase-physics.sh
    twins/reference-917-engine/remote-simready/f42b/phase-render-preview.sh
)
SNAPSHOT_HELPER_RELATIVE="deploy/vast/simready/_materialize_git_snapshot.py"
SNAPSHOT_HELPER_SOURCE="${REPOSITORY_ROOT}/${SNAPSHOT_HELPER_RELATIVE}"
STAGED_SNAPSHOT_HELPER="${TEMPORARY}/materialize-git-snapshot.py"
STAGED_PROJECT_ROOT="${TEMPORARY}/project"

# Bootstrap minimal : l'outil de matérialisation exécuté est une copie privée
# des octets du blob Git exact, jamais un fichier relu depuis la worktree.
python3 - \
    "${REPOSITORY_ROOT}" "${REVISION}" "${SNAPSHOT_HELPER_RELATIVE}" \
    "${SNAPSHOT_HELPER_SOURCE}" "${STAGED_SNAPSHOT_HELPER}" <<'PY'
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys

root = Path(sys.argv[1]).resolve(strict=True)
revision, relative = sys.argv[2:4]
source, staged = map(Path, sys.argv[4:6])
environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
descriptor = os.open(source, flags)
with os.fdopen(descriptor, "rb") as handle:
    info = os.fstat(handle.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise SystemExit("outil snapshot Git de travail non sûr")
    data = handle.read(1_048_577)
if not data or len(data) > 1_048_576 or b"\0" in data:
    raise SystemExit("outil snapshot Git vide, binaire ou trop volumineux")
result = subprocess.run(
    ["/usr/bin/git", "--no-replace-objects", "-C", str(root), "rev-parse", f"{revision}:{relative}"],
    stdin=subprocess.DEVNULL,
    capture_output=True,
    text=True,
    check=False,
    env=environment,
)
if result.returncode != 0:
    raise SystemExit("blob Git de l'outil snapshot inaccessible")
expected_blob = result.stdout.strip()
actual_blob = hashlib.sha1(
    f"blob {len(data)}\0".encode("ascii") + data,
    usedforsecurity=False,
).hexdigest()
if expected_blob != actual_blob:
    raise SystemExit("outil snapshot Git différent du blob du commit exact")
output_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
output_descriptor = os.open(staged, output_flags, 0o700)
with os.fdopen(output_descriptor, "wb") as handle:
    handle.write(data)
    handle.flush()
    os.fchmod(handle.fileno(), 0o700)
    output_info = os.fstat(handle.fileno())
    if not stat.S_ISREG(output_info.st_mode) or stat.S_IMODE(output_info.st_mode) != 0o700:
        raise SystemExit("copie privée de l'outil snapshot invalide")
PY
PYTHONDONTWRITEBYTECODE=1 python3 "${STAGED_SNAPSHOT_HELPER}" \
    --repository "${REPOSITORY_ROOT}" --revision "${REVISION}" \
    --destination "${STAGED_PROJECT_ROOT}" \
    --manifest "${TEMPORARY}/source-allowlist.json" -- "${SOURCE_FILES[@]}" \
    || controller_die "matérialisation des blobs Git F42b refusée"

QUALIFICATION_RELATIVE="twins/reference-917-engine/evidence/f42b-gpu-runtime-qualification.json"
QUALIFICATION_EVIDENCE="${STAGED_PROJECT_ROOT}/${QUALIFICATION_RELATIVE}"
TRACKED_GHCR_WRAPPER="${STAGED_PROJECT_ROOT}/deploy/openbao/openbao-ghcr"
APPROVED_GHCR_WRAPPER="${HOME}/.local/bin/openbao-ghcr"
python3 - "${REPOSITORY_ROOT}" "${REVISION}" "${TRACKED_GHCR_WRAPPER}" "${APPROVED_GHCR_WRAPPER}" "${STAGED_GHCR_WRAPPER}" <<'PY'
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys

root = Path(sys.argv[1])
revision = sys.argv[2]
tracked, installed, staged = map(Path, sys.argv[3:])
clean_environment = {
    name: value for name, value in os.environ.items() if not name.startswith("GIT_")
}


def regular_bytes(path: Path, label: str, *, executable: bool) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise SystemExit(f"{label} inaccessible: {error}") from error
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o022
            or (executable and not info.st_mode & stat.S_IXUSR)
        ):
            raise SystemExit(f"{label} avec propriétaire, type ou mode non sûr")
        data = handle.read(1_048_577)
    if not data or len(data) > 1_048_576 or b"\0" in data:
        raise SystemExit(f"{label} vide, binaire ou trop volumineux")
    return data


tracked_data = regular_bytes(tracked, "wrapper GHCR suivi", executable=True)
installed_data = regular_bytes(installed, "wrapper GHCR approuvé", executable=True)
if tracked_data != installed_data:
    raise SystemExit("wrapper GHCR approuvé différent de la source suivie")


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(root), *arguments],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        env=clean_environment,
    )
    if result.returncode != 0:
        raise SystemExit("impossible d'attester le wrapper GHCR suivi")
    return result.stdout.strip()


relative = "deploy/openbao/openbao-ghcr"
committed_blob = git("rev-parse", f"{revision}:{relative}")
working_blob = hashlib.sha1(
    f"blob {len(tracked_data)}\0".encode("ascii") + tracked_data,
    usedforsecurity=False,
).hexdigest()
if committed_blob != working_blob:
    raise SystemExit("wrapper GHCR de travail différent du blob Git")
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
descriptor = os.open(staged, flags, 0o700)
with os.fdopen(descriptor, "wb") as handle:
    handle.write(installed_data)
    handle.flush()
    os.fchmod(handle.fileno(), 0o700)
    info = os.fstat(handle.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise SystemExit("copie privée du wrapper GHCR invalide")
PY
[ -f "${QUALIFICATION_EVIDENCE}" ] \
    || controller_die "preuve publique F42b absente"
python3 "${STAGED_GHCR_WRAPPER}" attest-simready-runtime \
    "${QUALIFICATION_EVIDENCE}" "${STAGED_RUNTIME_ATTESTATION}" \
    "${JOB_ID}" "${RUNTIME_ATTESTATION_NONCE}" \
    || controller_die "attestation runtime live OpenBao/GHCR refusée"
[ -f "${STAGED_RUNTIME_ATTESTATION}" ] \
    || controller_die "attestation runtime live non produite"

REPEATABILITY_RELATIVE="twins/reference-917-engine/evidence/f42a-cpu-usd/repeatability-summary.json"
CONTRACT_RELATIVE="twins/reference-917-engine/component-factory-f42b-gpu.json"
REPEATABILITY_SUMMARY="${STAGED_PROJECT_ROOT}/${REPEATABILITY_RELATIVE}"
F42B_CONTRACT="${STAGED_PROJECT_ROOT}/${CONTRACT_RELATIVE}"
[ -f "${REPEATABILITY_SUMMARY}" ] || controller_die "preuve de répétabilité F42a absente"
[ -f "${F42B_CONTRACT}" ] || controller_die "contrat F42b absent"
PYTHONDONTWRITEBYTECODE=1 python3 \
    "${STAGED_PROJECT_ROOT}/twins/reference-917-engine/remote-simready/f42b/_contract.py" \
    validate-contract --contract "${F42B_CONTRACT}" --require-qualified-runtime \
    --runtime-attestation "${STAGED_RUNTIME_ATTESTATION}" \
    --runtime-job-id "${JOB_ID}" --runtime-nonce "${RUNTIME_ATTESTATION_NONCE}" \
    || controller_die "contrat, preuve publique ou pin wrapper F42b non qualifié"
RUNTIME_ATTESTATION_SHA256="$(shasum -a 256 "${STAGED_RUNTIME_ATTESTATION}" | awk '{print $1}')"
mkdir -p "${TEMPORARY}/f42a-usd"

# Cette étape locale est antérieure au guard réseau. Elle refuse un contrat non
# qualifié, tout lien symbolique, tout USD supplémentaire et tout octet qui ne
# correspond pas à la preuve F42a suivie par Git.
python3 - \
    "${REPEATABILITY_SUMMARY}" \
    "${F42B_CONTRACT}" \
    "${F42A_OUTPUT_ROOT}" \
    "${EXPECTED_IMAGE}" \
    "${TEMPORARY}/f42b-input-manifest.json" \
    "${TEMPORARY}/f42a-usd" <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

summary_path, contract_path, source_root, expected_image, output_path, staged_root = (
    Path(value) if index != 3 else value
    for index, value in enumerate(sys.argv[1:])
)
families = (
    "connecting_rod",
    "crankshaft",
    "main_bearing_pair",
    "piston",
    "piston_pin",
    "piston_ring",
)
profile = "f42b-six-usd-v1"
hash_pattern = re.compile(r"[0-9a-f]{64}")


def fail(message: str) -> None:
    raise SystemExit(message)


def read_object(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"{label} illisible: {error}")
    if not isinstance(payload, dict):
        fail(f"{label} doit être un objet JSON")
    return payload


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


summary = read_object(summary_path, "preuve F42a")
repeatability = summary.get("repeatability")
if (
    summary.get("schema_version") != "1.0.0"
    or summary.get("phase") != "F42a-cpu-usd-repeatability"
    or not isinstance(summary.get("status"), str)
    or "passed_two_runs_six_canonical_USD_bitwise_identical" not in summary["status"]
    or not isinstance(repeatability, dict)
    or repeatability.get("run_count") != 2
    or repeatability.get("all_six_USD_bitwise_identical") is not True
    or repeatability.get("canonical_namespace") is not True
):
    fail("preuve F42a insuffisante pour le transfert fermé")
for claim in (
    "manufacturing_authorized",
    "performance_1600_hp_claim_authorized",
    "simulation_validated",
):
    if summary.get(claim) is not False:
        fail(f"preuve F42a avec claim interdit: {claim}")

summary_families = repeatability.get("families")
if not isinstance(summary_families, list) or [item.get("family_id") for item in summary_families if isinstance(item, dict)] != list(families):
    fail("preuve F42a sans les six familles exactes et ordonnées")
expected: dict[str, dict] = {}
for item in summary_families:
    family = item.get("family_id")
    sha256 = item.get("USD_sha256")
    size = item.get("USD_size_bytes")
    default_prim = item.get("default_prim_path")
    if (
        family not in families
        or not isinstance(sha256, str)
        or hash_pattern.fullmatch(sha256) is None
        or type(size) is not int
        or size <= 0
        or default_prim != f"/{family}"
    ):
        fail(f"métadonnées F42a invalides pour {family}")
    expected[family] = {
        "family_id": family,
        "filename": f"{family}.usd",
        "size_bytes": size,
        "sha256": sha256,
        "default_prim_path": default_prim,
    }

contract = read_object(contract_path, "contrat F42b")
runtime = contract.get("runtime")
source_usd = contract.get("source_usd")
if contract.get("schema_version") != "1.0.0" or contract.get("workflow_profile") != profile:
    fail("contrat F42b d'un autre profil")
if (
    not isinstance(source_usd, dict)
    or source_usd.get("evidence_path")
    != "twins/reference-917-engine/evidence/f42a-cpu-usd/repeatability-summary.json"
    or source_usd.get("evidence_sha256") != digest_file(summary_path)
    or source_usd.get("exact_file_count") != 6
    or source_usd.get("total_size_bytes") != 166766
    or source_usd.get("private_artifacts_committed") is not False
):
    fail("contrat F42b non lié exactement à la preuve F42a assainie")
if not isinstance(runtime, dict) or runtime.get("image_repository") != "ghcr.io/cluster2600/3dprinting993-simready-local-ai":
    fail("dépôt d'image F42b inattendu")
if runtime.get("qualification_status") != "qualified_public_linux_amd64_digest":
    fail("runtime F42b non qualifié; aucun transfert distant autorisé")
if runtime.get("qualified_image_ref") != expected_image:
    fail("digest qualifié F42b différent de --expected-image")
release_gates = contract.get("release_gates")
release_gate_keys = {
    "runtime_digest_qualified",
    "private_usd_transferred_and_hash_verified",
    "all_six_family_runs_complete",
    "simready_property_assignment_complete",
    "physical_simulation_validated",
    "fea_validated",
    "manufacturing_authorized",
    "engine_installation_authorized",
    "performance_claim_authorized",
}
if (
    not isinstance(release_gates, dict)
    or set(release_gates) != release_gate_keys
    or release_gates.get("runtime_digest_qualified") is not True
):
    fail("release gate du digest runtime F42b non fermé")
if any(
    value is not False
    for key, value in release_gates.items()
    if key != "runtime_digest_qualified"
):
    fail("seul release_gates.runtime_digest_qualified peut être vrai avant F42b")
contract_families = source_usd.get("families") if isinstance(source_usd, dict) else None
if not isinstance(contract_families, list) or [item.get("family_id") for item in contract_families if isinstance(item, dict)] != list(families):
    fail("contrat F42b sans les six familles exactes et ordonnées")
for item in contract_families:
    family = item.get("family_id")
    if family not in expected or any(item.get(key) != expected[family][key] for key in ("filename", "size_bytes", "sha256", "default_prim_path")):
        fail(f"contrat F42b différent de la preuve F42a pour {family}")

try:
    root_info = source_root.lstat()
except OSError as error:
    fail(f"racine privée F42a inaccessible: {error}")
if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
    fail("--f42a-output-root doit être un répertoire réel")
source_root = source_root.resolve(strict=True)
expected_relative = {
    Path("pipeline/01_conversion") / family / f"{family}.usd"
    for family in families
}


def scan_private_tree() -> set[Path]:
    found: set[Path] = set()

    def visit(directory: Path) -> None:
        try:
            with os.scandir(directory) as iterator:
                children = sorted(iterator, key=lambda entry: entry.name.encode("utf-8"))
        except OSError as error:
            fail(f"arbre privé F42a illisible: {error}")
        for child in children:
            child_path = Path(child.path)
            try:
                info = child_path.lstat()
            except OSError as error:
                fail(f"entrée privée F42a illisible: {error}")
            relative = child_path.relative_to(source_root)
            if stat.S_ISLNK(info.st_mode):
                fail(f"lien symbolique interdit dans l'arbre privé F42a: {relative.as_posix()}")
            if stat.S_ISDIR(info.st_mode):
                visit(child_path)
            elif stat.S_ISREG(info.st_mode):
                if child_path.suffix.lower() in {".usd", ".usda", ".usdc", ".usdz"}:
                    found.add(relative)
            else:
                fail(f"fichier spécial interdit dans l'arbre privé F42a: {relative.as_posix()}")

    visit(source_root)
    return found


found_before = scan_private_tree()
if found_before != expected_relative:
    missing = sorted(path.as_posix() for path in expected_relative - found_before)
    extras = sorted(path.as_posix() for path in found_before - expected_relative)
    fail(f"ensemble USD privé différent des six attendus; absents={missing}; extras={extras}")

staged_root = staged_root.resolve(strict=True)
assets: list[dict] = []
for family in families:
    metadata = expected[family]
    relative = Path("pipeline/01_conversion") / family / metadata["filename"]
    source = source_root / relative
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(source, flags)
    except OSError as error:
        fail(f"USD privé F42a absent ou non sûr pour {family}: {error}")
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != metadata["size_bytes"]:
            fail(f"taille/type de l'USD privé différent pour {family}")
        data = handle.read(metadata["size_bytes"] + 1)
    if len(data) != metadata["size_bytes"] or digest_bytes(data) != metadata["sha256"]:
        fail(f"hash/taille de l'USD privé différent pour {family}")
    destination = staged_root / metadata["filename"]
    with destination.open("xb") as handle:
        handle.write(data)
    destination.chmod(0o444)
    if digest_file(destination) != metadata["sha256"] or destination.stat().st_size != metadata["size_bytes"]:
        fail(f"copie temporaire incohérente pour {family}")
    assets.append(
        {
            **metadata,
            "path": f"inputs/f42a-usd/{metadata['filename']}",
        }
    )

if scan_private_tree() != found_before:
    fail("arbre privé F42a modifié pendant l'attestation")
manifest = {
    "schema_version": "1.0.0",
    "workflow_profile": profile,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "source_repeatability_summary": {
        "path": "project/twins/reference-917-engine/evidence/f42a-cpu-usd/repeatability-summary.json",
        "sha256": digest_file(summary_path),
    },
    "f42b_contract": {
        "path": "project/twins/reference-917-engine/component-factory-f42b-gpu.json",
        "sha256": digest_file(contract_path),
    },
    "asset_count": len(assets),
    "total_size_bytes": sum(item["size_bytes"] for item in assets),
    "assets": assets,
    "claims": {
        "manufacturing_authorized": False,
        "performance_1600_hp_claim_authorized": False,
        "simulation_validated": False,
        "simready_validated": False,
    },
}
output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

BUNDLE_MANIFEST_TOOL="${STAGED_PROJECT_ROOT}/twins/reference-917-engine/remote-simready/_bundle_manifest.py"
[ -f "${BUNDLE_MANIFEST_TOOL}" ] || controller_die "outil de manifeste bundle absent"
SKILL_TREE_SHA256="$(PYTHONDONTWRITEBYTECODE=1 python3 "${BUNDLE_MANIFEST_TOOL}" create-skill \
    --root "${SKILL_ROOT}" --output "${TEMPORARY}/skill-manifest.json")"
SKILL_MANIFEST_SHA256="$(shasum -a 256 "${TEMPORARY}/skill-manifest.json" | awk '{print $1}')"
INPUT_MANIFEST_SHA256="$(shasum -a 256 "${TEMPORARY}/f42b-input-manifest.json" | awk '{print $1}')"
F42B_CONTRACT_SHA256="$(shasum -a 256 "${F42B_CONTRACT}" | awk '{print $1}')"
python3 - "${STAGED_MATERIAL_PROMPT}" "${STAGED_PHYSICS_PROMPT}" "${TEMPORARY}/prompt-metadata.json" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

material, physics, output = map(Path, sys.argv[1:])
payload = {}
for name, filename, path in (
    ("material", "material-prompt.txt", material),
    ("physics", "physics-prompt.txt", physics),
):
    data = path.read_bytes()
    payload[name] = {
        "filename": filename,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

SOURCE_MANIFEST_SHA256="$(shasum -a 256 "${TEMPORARY}/source-allowlist.json" | awk '{print $1}')"
read -r BUNDLE_TOOL_SHA256 F42B_VERIFY_TOOL_SHA256 <<EOF
$(python3 - "${TEMPORARY}/source-allowlist.json" <<'PY'
import json
from pathlib import Path
import sys

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
entries = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
required = (
    "twins/reference-917-engine/remote-simready/_bundle_manifest.py",
    "twins/reference-917-engine/remote-simready/f42b/_contract.py",
)
if any(path not in entries for path in required):
    raise SystemExit("outils de vérification absents de l'allowlist F42b")
print(*(entries[path] for path in required))
PY
)
EOF

LOCAL_CONTROL_ROOT="${LOCAL_CONTROL_ROOT:-${REPOSITORY_ROOT}/work/vast-simready/controller/${JOB_ID}}"
KNOWN_HOSTS="${KNOWN_HOSTS:-${LOCAL_CONTROL_ROOT}/known_hosts}"
mkdir -p "${LOCAL_CONTROL_ROOT}"
GUARD_REPORT="${LOCAL_CONTROL_ROOT}/instance-guard.json"
guard_and_prepare_ssh "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${MAX_DPH}" "${GUARD_REPORT}" "${KNOWN_HOSTS}" running
cp "${GUARD_REPORT}" "${TEMPORARY}/instance-guard.json"

DEADLINE_EPOCH="$(( $(date +%s) + MAX_RUNTIME_MINUTES * 60 ))"
python3 - \
    "${TEMPORARY}/job-control.json" \
    "${JOB_ID}" \
    "${INSTANCE_ID}" \
    "${EXPECTED_IMAGE}" \
    "${MAX_DPH}" \
    "${MAX_RUNTIME_MINUTES}" \
    "${DEADLINE_EPOCH}" \
    "${REVISION}" \
    "${TEMPORARY}/prompt-metadata.json" \
    "${SKILL_MANIFEST_SHA256}" \
    "${SKILL_TREE_SHA256}" \
    "${SOURCE_MANIFEST_SHA256}" \
    "${INPUT_MANIFEST_SHA256}" \
    "${TEMPORARY}/f42b-input-manifest.json" \
    "${F42B_CONTRACT_SHA256}" \
    "${RUNTIME_ATTESTATION_SHA256}" \
    "${RUNTIME_ATTESTATION_NONCE}" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

input_manifest = json.loads(Path(sys.argv[14]).read_text(encoding="utf-8"))
payload = {
    "schema_version": "1.0.0",
    "workflow_profile": "f42b-six-usd-v1",
    "job_id": sys.argv[2],
    "instance_id": int(sys.argv[3]),
    "expected_image": sys.argv[4],
    "max_dph": sys.argv[5],
    "max_runtime_minutes": int(sys.argv[6]),
    "deadline_epoch": int(sys.argv[7]),
    "source_revision": sys.argv[8],
    "created_at": datetime.now(timezone.utc).isoformat(),
    "instance_guard_report": "instance-guard.json",
    "input_prompts": json.loads(Path(sys.argv[9]).read_text(encoding="utf-8")),
    "skill_manifest_report": "skill-manifest.json",
    "skill_manifest_sha256": sys.argv[10],
    "skill_tree_sha256": sys.argv[11],
    "source_allowlist_report": "source-allowlist.json",
    "source_allowlist_sha256": sys.argv[12],
    "source_transfer_attestation": "control/source-transfer-attestation.json",
    "input_assets_manifest": "control/f42b-input-manifest.json",
    "input_assets_manifest_sha256": sys.argv[13],
    "input_assets": input_manifest["assets"],
    "f42a_repeatability": input_manifest["source_repeatability_summary"],
    "f42b_contract": {
        "path": "project/twins/reference-917-engine/component-factory-f42b-gpu.json",
        "sha256": sys.argv[15],
    },
    "runtime_attestation_report": "control/runtime-attestation.json",
    "runtime_attestation_sha256": sys.argv[16],
    "runtime_attestation_nonce": sys.argv[17],
    "source_policy": (
        "private immutable snapshot materialized and transferred from exact commit blobs; six private F42a USD "
        "only by exact path, size and SHA-256; no symlink, extra USD, raw scan or secret"
    ),
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

REMOTE_PARTIAL="/workspace/jobs/${JOB_ID}.partial"
REMOTE_FINAL="/workspace/jobs/${JOB_ID}"
controller_ssh "test ! -e '${REMOTE_FINAL}' && test ! -e '${REMOTE_PARTIAL}' && mkdir -p '${REMOTE_PARTIAL}/project' '${REMOTE_PARTIAL}/vendor' '${REMOTE_PARTIAL}/control' '${REMOTE_PARTIAL}/inputs'"
(
    cd "${STAGED_PROJECT_ROOT}"
    COPYFILE_DISABLE=1 tar -cf - .
) | controller_ssh "tar --no-same-owner -xf - -C '${REMOTE_PARTIAL}/project'"
(
    cd "$(dirname "${SKILL_ROOT}")"
    COPYFILE_DISABLE=1 tar -cf - "$(basename "${SKILL_ROOT}")"
) | controller_ssh "tar --no-same-owner -xf - -C '${REMOTE_PARTIAL}/vendor'"
(
    cd "${TEMPORARY}"
    COPYFILE_DISABLE=1 tar -cf - instance-guard.json job-control.json source-allowlist.json skill-manifest.json f42b-input-manifest.json runtime-attestation.json
) | controller_ssh "tar --no-same-owner -xf - -C '${REMOTE_PARTIAL}/control'"
(
    cd "${TEMPORARY}"
    COPYFILE_DISABLE=1 tar -cf - f42a-usd
) | controller_ssh "tar --no-same-owner -xf - -C '${REMOTE_PARTIAL}/inputs'"

controller_ssh "dd of='${REMOTE_PARTIAL}/inputs/material-prompt.txt' status=none" <"${STAGED_MATERIAL_PROMPT}"
controller_ssh "dd of='${REMOTE_PARTIAL}/inputs/physics-prompt.txt' status=none" <"${STAGED_PHYSICS_PROMPT}"
controller_ssh "python3 - '${REMOTE_PARTIAL}' '${SOURCE_MANIFEST_SHA256}' '${WORKFLOW_PROFILE}'" <<'PY'
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

job_root = Path(sys.argv[1]).resolve(strict=True)
expected_manifest_sha256 = sys.argv[2]
expected_profile = sys.argv[3]
control_path = job_root / "control/job-control.json"
manifest_path = job_root / "control/source-allowlist.json"
project_root = job_root / "project"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


if digest(manifest_path) != expected_manifest_sha256:
    raise SystemExit("manifeste source distant différent")
control = json.loads(control_path.read_text(encoding="utf-8"))
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if (
    manifest.get("schema_version") != "1.0.0"
    or manifest.get("workflow_profile") != expected_profile
    or manifest.get("source_revision") != control.get("source_revision")
    or control.get("source_allowlist_sha256") != expected_manifest_sha256
):
    raise SystemExit("identité du manifeste source distant invalide")
entries = manifest.get("files")
if not isinstance(entries, list) or not entries:
    raise SystemExit("allowlist source distante vide")
expected = {}
for entry in entries:
    if not isinstance(entry, dict):
        raise SystemExit("entrée d'allowlist source invalide")
    relative = entry.get("path")
    path = Path(str(relative))
    if (
        not isinstance(relative, str)
        or path.is_absolute()
        or ".." in path.parts
        or relative in expected
        or re.fullmatch(r"[0-9a-f]{40,64}", str(entry.get("git_blob", ""))) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", ""))) is None
        or type(entry.get("size_bytes")) is not int
        or entry["size_bytes"] < 0
    ):
        raise SystemExit("entrée d'allowlist source non bornée")
    expected[relative] = entry

actual = {}


def visit(directory: Path) -> None:
    with os.scandir(directory) as iterator:
        children = sorted(iterator, key=lambda item: item.name.encode("utf-8"))
    for child in children:
        path = Path(child.path)
        info = path.lstat()
        relative = path.relative_to(project_root).as_posix()
        if stat.S_ISLNK(info.st_mode):
            raise SystemExit(f"symlink source distant interdit: {relative}")
        if stat.S_ISDIR(info.st_mode):
            visit(path)
        elif stat.S_ISREG(info.st_mode):
            actual[relative] = path
        else:
            raise SystemExit(f"fichier spécial source distant interdit: {relative}")


visit(project_root)
if set(actual) != set(expected):
    raise SystemExit("arbre source distant différent de l'allowlist fermée")
for relative, path in actual.items():
    entry = expected[relative]
    if path.stat().st_size != entry["size_bytes"] or digest(path) != entry["sha256"]:
        raise SystemExit(f"source distante différente du manifeste: {relative}")
attestation = {
    "schema_version": "1.0.0",
    "status": "passed",
    "passed": True,
    "workflow_profile": expected_profile,
    "source_revision": control["source_revision"],
    "source_allowlist_sha256": expected_manifest_sha256,
    "verified_file_count": len(actual),
    "symlink_count": 0,
    "special_file_count": 0,
    "unexpected_file_count": 0,
    "verified_at": datetime.now(timezone.utc).isoformat(),
}
(job_root / "control/source-transfer-attestation.json").write_text(
    json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY
REMOTE_BUNDLE_REL="project/twins/reference-917-engine/remote-simready/_bundle_manifest.py"
REMOTE_F42B_VERIFY_REL="project/twins/reference-917-engine/remote-simready/f42b/_contract.py"
controller_ssh "cd '${REMOTE_PARTIAL}' && test ! -L '${REMOTE_BUNDLE_REL}' && test ! -L '${REMOTE_F42B_VERIFY_REL}' && printf '%s  %s\n%s  %s\n' '${BUNDLE_TOOL_SHA256}' '${REMOTE_BUNDLE_REL}' '${F42B_VERIFY_TOOL_SHA256}' '${REMOTE_F42B_VERIFY_REL}' | sha256sum -c - >/dev/null && python3 '${REMOTE_PARTIAL}/${REMOTE_BUNDLE_REL}' verify --job-root '${REMOTE_PARTIAL}' --control '${REMOTE_PARTIAL}/control/job-control.json' >/dev/null && python3 '${REMOTE_PARTIAL}/${REMOTE_F42B_VERIFY_REL}' verify-control --contract '${REMOTE_PARTIAL}/project/twins/reference-917-engine/component-factory-f42b-gpu.json' --control '${REMOTE_PARTIAL}/control/job-control.json' >/dev/null && chmod -R go-w '${REMOTE_PARTIAL}' && mv '${REMOTE_PARTIAL}' '${REMOTE_FINAL}'"

python3 - \
    "${LOCAL_CONTROL_ROOT}/transfer-report.json" \
    "${JOB_ID}" \
    "${INSTANCE_ID}" \
    "${EXPECTED_IMAGE}" \
    "${REVISION}" \
    "${DEADLINE_EPOCH}" \
    "${SOURCE_MANIFEST_SHA256}" \
    "${TEMPORARY}/prompt-metadata.json" \
    "${SKILL_MANIFEST_SHA256}" \
    "${SKILL_TREE_SHA256}" \
    "${INPUT_MANIFEST_SHA256}" \
    "${TEMPORARY}/f42b-input-manifest.json" \
    "${F42B_CONTRACT_SHA256}" \
    "${RUNTIME_ATTESTATION_SHA256}" \
    "${RUNTIME_ATTESTATION_NONCE}" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

input_manifest = json.loads(Path(sys.argv[12]).read_text(encoding="utf-8"))
payload = {
    "schema_version": "1.0.0",
    "status": "passed",
    "passed": True,
    "workflow_profile": "f42b-six-usd-v1",
    "job_id": sys.argv[2],
    "instance_id": int(sys.argv[3]),
    "expected_image": sys.argv[4],
    "source_revision": sys.argv[5],
    "deadline_epoch": int(sys.argv[6]),
    "source_allowlist_sha256": sys.argv[7],
    "source_transfer_attestation": f"/workspace/jobs/{sys.argv[2]}/control/source-transfer-attestation.json",
    "input_prompts": json.loads(Path(sys.argv[8]).read_text(encoding="utf-8")),
    "skill_manifest_sha256": sys.argv[9],
    "skill_tree_sha256": sys.argv[10],
    "input_assets_manifest_sha256": sys.argv[11],
    "input_assets": input_manifest["assets"],
    "f42a_repeatability": input_manifest["source_repeatability_summary"],
    "f42b_contract_sha256": sys.argv[13],
    "runtime_attestation_sha256": sys.argv[14],
    "runtime_attestation_nonce": sys.argv[15],
    "remote_project_root": f"/workspace/jobs/{sys.argv[2]}/project",
    "remote_skill_root": f"/workspace/jobs/{sys.argv[2]}/vendor/omniverse-cad-to-simready",
    "remote_input_root": f"/workspace/jobs/{sys.argv[2]}/inputs/f42a-usd",
    "simulation_validated": False,
    "manufacturing_authorized": False,
    "finished_at": datetime.now(timezone.utc).isoformat(),
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
printf '%s\n' "${LOCAL_CONTROL_ROOT}/transfer-report.json"
