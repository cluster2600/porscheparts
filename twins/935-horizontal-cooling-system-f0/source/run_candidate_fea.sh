#!/usr/bin/env bash
# Linux worker: isolated serial solve; execution success is not numerical acceptance.
set -euo pipefail
test "$#" -eq 3
fea_deck=$(realpath "$1")
fea_expected_sha=$2
fea_job_dir=$(realpath -m "$3")
[[ "$fea_expected_sha" =~ ^[0-9a-f]{64}$ ]]
test "$(sha256sum "$fea_deck" | cut -d ' ' -f 1)" = "$fea_expected_sha"
test ! -e "$fea_job_dir"
fea_parent=$fea_job_dir
while [[ "$fea_parent" != / ]]; do
    if [[ -e "$fea_parent/.git" ]]; then
        [[ "$fea_job_dir" == "$fea_parent/work/"* ]]
        break
    fi
    fea_parent=$(dirname "$fea_parent")
done
mkdir -m 700 "$fea_job_dir"
cp "$fea_deck" "$fea_job_dir/rotor.inp"
cd "$fea_job_dir"
printf '%s\n' "$fea_expected_sha" > input.sha256
set +e
OMP_NUM_THREADS=1 CCX_NPROC_RESULTS=1 CCX_NPROC_STIFFNESS=1 ccx -i rotor > ccx.log 2>&1
fea_exit_status=$?
set -e
printf '%s\n' "$fea_exit_status" > ccx.exit
test "$fea_exit_status" -eq 0
grep -q 'Job finished' ccx.log
! grep -q '\*ERROR' ccx.log
test "$(sha256sum rotor.inp | cut -d ' ' -f 1)" = "$fea_expected_sha"
test "$(sha256sum "$fea_deck" | cut -d ' ' -f 1)" = "$fea_expected_sha"
