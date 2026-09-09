#!/usr/bin/env bash
set -euo pipefail

OPENBAO_GHCR_KV_PATH="github"
OPENBAO_API_PATH="secrets/data/${OPENBAO_GHCR_KV_PATH}"
POLICY_NAME="codex-3dprinting993-ghcr-read"
ROLE_NAME="3dprinting993-ghcr"
BOOTSTRAP_DIR="${HOME}/.config/openbao-ghcr-reader"
INSTALL_DIR="${HOME}/.local/bin"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

command -v bao >/dev/null 2>&1 || {
    echo "bao is not installed or not on PATH" >&2
    exit 1
}

test -f "${SCRIPT_DIR}/openbao-ghcr" || {
    echo "missing wrapper beside provisioning script" >&2
    exit 1
}

# Metadata only: neither the username nor the token is retrieved here.
if ! bao kv metadata get -mount=secrets -format=json "${OPENBAO_GHCR_KV_PATH}" >/dev/null; then
    echo "No GitHub secret metadata at secrets/${OPENBAO_GHCR_KV_PATH}" >&2
    echo "The existing GitHub token must remain at that exact path." >&2
    exit 1
fi

bao policy write "${POLICY_NAME}" - >/dev/null <<HCL
path "${OPENBAO_API_PATH}" {
  capabilities = ["read"]
}
HCL

bao write "auth/codex-deploy/role/${ROLE_NAME}" \
    token_policies="${POLICY_NAME}" \
    token_no_default_policy="true" \
    token_ttl="5m" \
    token_max_ttl="10m" \
    secret_id_ttl="0" \
    secret_id_num_uses="0" >/dev/null

install -d -m 0700 "${BOOTSTRAP_DIR}"
umask 077
bao read -field=role_id "auth/codex-deploy/role/${ROLE_NAME}/role-id" \
    > "${BOOTSTRAP_DIR}/role_id"
bao write -f -field=secret_id "auth/codex-deploy/role/${ROLE_NAME}/secret-id" \
    > "${BOOTSTRAP_DIR}/secret_id"
printf '%s\n' "${OPENBAO_API_PATH}" > "${BOOTSTRAP_DIR}/secret_path"
chmod 0600 \
    "${BOOTSTRAP_DIR}/role_id" \
    "${BOOTSTRAP_DIR}/secret_id" \
    "${BOOTSTRAP_DIR}/secret_path"

install -d -m 0755 "${INSTALL_DIR}"
install -m 0755 "${SCRIPT_DIR}/openbao-ghcr" "${INSTALL_DIR}/openbao-ghcr"

echo "OpenBao GHCR wrapper installed without exposing the package token"
echo "Next: openbao-ghcr --check"
echo "Then: openbao-ghcr --auth-check"
