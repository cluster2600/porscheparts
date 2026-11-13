#!/usr/bin/env bash
# Run one fan-baseline case inside m64-engineering-worker (OpenFOAM v2312).
# Usage: ./run_case.sh <caseName>   (mounts deck root read-write)
# Provenance: container OpenFOAM v2312; see RUN_RECORD.md.
set -eu
CASE="${1:?usage: run_case.sh <caseName>}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp --entrypoint bash \
  -v "$ROOT:/work" -w "/work/$CASE" \
  m64-engineering-worker:latest \
  /work/run_case_inplace.sh "$CASE"
