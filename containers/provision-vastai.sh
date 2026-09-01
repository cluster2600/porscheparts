#!/usr/bin/env bash
# Optional on-start script for a rented GPU instance.
#
# Kept out of the image on purpose: everything here is either large, fast
# moving, or specific to one job. Point the platform's PROVISIONING_SCRIPT at a
# raw URL of this file, or run it by hand after connecting.
#
# Environment switches:
#   WITH_MESHROOM=1   fetch the Meshroom/AliceVision bundle (~14 GB download)
#   WITH_MASKING=1    fetch background-removal models for turntable shots
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
WITH_MESHROOM="${WITH_MESHROOM:-0}"
WITH_MASKING="${WITH_MASKING:-0}"
MESHROOM_URL="${MESHROOM_URL:-https://zenodo.org/records/16887472/files/Meshroom-2025.1.0-Linux.tar.gz}"

mkdir -p "${WORKSPACE}"/{images,masks,sfm,dense,mesh,cad,sim,out,logs,datasets,checkpoints,cache}
echo "provision: workspace layout ready under ${WORKSPACE}"

# Make the image environment visible inside injected SSH and tmux sessions.
{
    printf 'PATH=%s\n' "${PATH}"
    [ -n "${VIRTUAL_ENV:-}" ] && printf 'VIRTUAL_ENV=%s\n' "${VIRTUAL_ENV}"
    [ -n "${FOAM_VERSION:-}" ] && printf 'FOAM_VERSION=%s\n' "${FOAM_VERSION}"
    [ -n "${DDE_BACKEND:-}" ] && printf 'DDE_BACKEND=%s\n' "${DDE_BACKEND}"
    [ -n "${XLA_PYTHON_CLIENT_PREALLOCATE:-}" ] && printf 'XLA_PYTHON_CLIENT_PREALLOCATE=%s\n' "${XLA_PYTHON_CLIENT_PREALLOCATE}"
    [ -n "${PYTORCH_CUDA_ALLOC_CONF:-}" ] && printf 'PYTORCH_CUDA_ALLOC_CONF=%s\n' "${PYTORCH_CUDA_ALLOC_CONF}"
} > /etc/environment || true

if [ "${WITH_MESHROOM}" = "1" ]; then
    # AliceVision reads and writes the same COLMAP-style inputs but ships as a
    # 14 GB bundle, so it lives on the instance disk, never in the image.
    echo "provision: downloading Meshroom bundle (large; check the disk allocation first)"
    df -h "${WORKSPACE}" | tail -1
    mkdir -p /opt/meshroom
    curl -fL --retry 3 "${MESHROOM_URL}" | tar -xz -C /opt/meshroom --strip-components=1
    ln -sf /opt/meshroom/meshroom_batch /usr/local/bin/meshroom_batch
    echo "provision: meshroom_batch available"
fi

if [ "${WITH_MASKING}" = "1" ]; then
    echo "provision: installing background-removal tooling"
    pip install --no-cache-dir rembg onnxruntime-gpu
    echo "provision: rembg available (run once to cache its model)"
fi

echo "provision: done"
