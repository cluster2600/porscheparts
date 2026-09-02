#!/bin/sh
set -eu

SOLVER_UID=9139
SOLVER_GID=9139

if [ "$(id -u)" -ne 0 ]; then
    echo "run_job_requires_root_orchestrator" >&2
    exit 77
fi
if [ "$#" -lt 2 ]; then
    echo "usage: 917-wave-run-job JOB_ID COMMAND [ARG ...]" >&2
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
test "$(stat -c %u "${job_dir}")" = "${SOLVER_UID}" || { echo "staged_job_uid_mismatch" >&2; exit 68; }
test "$(stat -c %g "${job_dir}")" = "${SOLVER_GID}" || { echo "staged_job_gid_mismatch" >&2; exit 69; }

if [ -e "${results_dir}" ]; then
    for directory in \
        "${results_dir}" "${runtime_dir}" "${runtime_dir}/home" \
        "${runtime_dir}/cache" "${runtime_dir}/numba"; do
        test -d "${directory}" || { echo "solver_runtime_directory_missing" >&2; exit 70; }
        test ! -L "${directory}" || { echo "solver_runtime_symlink_rejected" >&2; exit 71; }
        test "$(stat -c %u "${directory}")" = "${SOLVER_UID}" || { echo "solver_runtime_uid_mismatch" >&2; exit 72; }
        test "$(stat -c %g "${directory}")" = "${SOLVER_GID}" || { echo "solver_runtime_gid_mismatch" >&2; exit 73; }
    done
else
    mkdir -p \
        "${results_dir}" "${runtime_dir}/home" \
        "${runtime_dir}/cache" "${runtime_dir}/numba"
    chmod 0750 \
        "${results_dir}" "${runtime_dir}" "${runtime_dir}/home" \
        "${runtime_dir}/cache" "${runtime_dir}/numba"
    chown -R "${SOLVER_UID}:${SOLVER_GID}" "${results_dir}"
fi

cd "${job_dir}"
exec setpriv \
    --reuid="${SOLVER_UID}" \
    --regid="${SOLVER_GID}" \
    --clear-groups \
    --inh-caps=-all \
    --ambient-caps=-all \
    --bounding-set=-all \
    --no-new-privs \
    env -i \
      HOME="${runtime_dir}/home" \
      XDG_CACHE_HOME="${runtime_dir}/cache" \
      NUMBA_CACHE_DIR="${runtime_dir}/numba" \
      NUMBA_NUM_THREADS=1 \
      OMP_NUM_THREADS=1 \
      OPENBLAS_NUM_THREADS=1 \
      MKL_NUM_THREADS=1 \
      PYTHONDONTWRITEBYTECODE=1 \
      PYTHONUNBUFFERED=1 \
      PYTHONHASHSEED=0 \
      LANG=C.UTF-8 \
      LC_ALL=C.UTF-8 \
      PATH=/usr/local/bin:/usr/bin:/bin \
      WAVE_JOB_DIR="${job_dir}" \
      WAVE_RESULTS_DIR="${results_dir}" \
      "$@"
