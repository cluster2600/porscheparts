#!/usr/bin/env bash
# Build from a small allowlisted context; never send the source checkout.
set -euo pipefail
repo_root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
image_ref="${1:-porscheparts-warp-geometry:dev}"
context_dir="$(mktemp -d)"
trap 'rm -rf -- "${context_dir}"' EXIT
mkdir -p "${context_dir}/containers" "${context_dir}/benchmarks/warp-geometry"
for file in containers/warp-geometry.Dockerfile containers/warp-geometry.requirements.txt \
  benchmarks/warp-geometry/pilot.py benchmarks/warp-geometry/kernels.py; do
  cp "${repo_root}/${file}" "${context_dir}/${file}"
done
docker build --platform linux/amd64 \
  --file "${context_dir}/containers/warp-geometry.Dockerfile" \
  --tag "${image_ref}" "${context_dir}"
