#!/bin/sh
set -eu

CAD_UID=9178
CAD_GID=9178
F41_RUNTIME_IMAGE_REF='ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57'

if [ "$(id -u)" -ne 0 ]; then
    echo "run_job_requires_root_orchestrator" >&2
    exit 77
fi
if [ "$#" -lt 2 ]; then
    echo "usage: 917-cad-run-job JOB_ID COMMAND [ARG ...]" >&2
    exit 64
fi

job_id=$1
shift
case "${job_id}" in
    ""|*[!a-z0-9._-]*|.*|*..*)
        echo "invalid_job_id" >&2
        exit 65
        ;;
esac

job_dir=/workspace/jobs/${job_id}
results_dir=/workspace/results/${job_id}
runtime_dir=${results_dir}/.runtime

test -d "${job_dir}" || { echo "staged_job_missing" >&2; exit 66; }
test ! -L "${job_dir}" || { echo "staged_job_symlink_rejected" >&2; exit 67; }
test "$(stat -c %u "${job_dir}")" = "${CAD_UID}" || { echo "staged_job_uid_mismatch" >&2; exit 68; }
test "$(stat -c %g "${job_dir}")" = "${CAD_GID}" || { echo "staged_job_gid_mismatch" >&2; exit 69; }

install -d -o "${CAD_UID}" -g "${CAD_GID}" -m 0750 "${results_dir}"
install -d -o "${CAD_UID}" -g "${CAD_GID}" -m 0750 \
    "${runtime_dir}" "${runtime_dir}/home" "${runtime_dir}/cache" "${runtime_dir}/tmp"

cd "${job_dir}"
umask 027
exec setpriv \
    --reuid="${CAD_UID}" \
    --regid="${CAD_GID}" \
    --clear-groups \
    --inh-caps=-all \
    --ambient-caps=-all \
    --bounding-set=-all \
    --no-new-privs \
    env -i \
      HOME="${runtime_dir}/home" \
      XDG_CACHE_HOME="${runtime_dir}/cache" \
      TMPDIR="${runtime_dir}/tmp" \
      PYTHONDONTWRITEBYTECODE=1 \
      PYTHONUNBUFFERED=1 \
      PYTHONHASHSEED=0 \
      PYTHONNOUSERSITE=1 \
      OMP_NUM_THREADS=1 \
      OPENBLAS_NUM_THREADS=1 \
      MKL_NUM_THREADS=1 \
      SOURCE_DATE_EPOCH=0 \
      F41_RUNTIME_IMAGE_REF="${F41_RUNTIME_IMAGE_REF}" \
      TZ=UTC \
      LANG=C.UTF-8 \
      LC_ALL=C.UTF-8 \
      PATH=/usr/local/bin:/usr/bin:/bin \
      CAD_JOB_DIR="${job_dir}" \
      CAD_RESULTS_DIR="${results_dir}" \
      "$@"
