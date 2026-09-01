#!/usr/bin/env bash
# Convertit un repertoire de prototypes STEP F10 avec le convertisseur NVIDIA.
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: $0 STEP_DIR USD_DIR [WORKERS]" >&2
  exit 2
fi

STEP_DIR="$1"
USD_DIR="$2"
WORKERS="${3:-4}"
test -d "${STEP_DIR}"
case "${WORKERS}" in
  ''|*[!0-9]*) echo "WORKERS doit etre un entier positif" >&2; exit 2 ;;
esac
test "${WORKERS}" -gt 0
mkdir -p "${USD_DIR}"

find "${STEP_DIR}" -type f -name '*.step' -print0 | \
  xargs -0 -r -n 1 -P "${WORKERS}" bash -c '
    set -euo pipefail
    output_dir="$1"
    step="$2"
    family="$(basename "${step}" .step)"
    usd-convert-cad -i "${step}" -o "${output_dir}/${family}.usdc" \
      --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
  ' _ "${USD_DIR}"
