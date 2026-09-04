#!/usr/bin/env bash
set -euo pipefail

root="${1:?usage: $0 REMOTE_F36_ROOT CASE_NAME H_W_M2K}"
case_name="${2:?usage: $0 REMOTE_F36_ROOT CASE_NAME H_W_M2K}"
h_w_m2k="${3:?usage: $0 REMOTE_F36_ROOT CASE_NAME H_W_M2K}"
python_bin="${PYTHON_BIN:-/opt/venv/bin/python3}"
ccx_bin="${CCX_BIN:-ccx}"
solver="${root}/source/run_scan_conforming_thermal_f36.py"
head_stl="${root}/input/917-head-scan-conforming-4v-f36.local.stl"
flow_core="${root}/input/917-head-4v-flow-core-f36.local.stl"
case_dir="${root}/thermal/${case_name}"
driver_log="${root}/thermal/${case_name}.driver.log"

if [[ -e "${case_dir}" ]]; then
  printf 'case already exists: %s\n' "${case_dir}" >&2
  exit 64
fi

h_w_mm2k="$(${python_bin} -c 'import sys; print(f"{float(sys.argv[1]) / 1.0e6:.12g}")' "${h_w_m2k}")"
"${python_bin}" "${solver}" \
  --stl "${head_stl}" --flow-core "${flow_core}" \
  --pitch 2.5 --chamber-flux-w-mm2 0.45 \
  --external-h-w-mm2k "${h_w_mm2k}" --exhaust-h-w-mm2k 0.00005 \
  --output "${case_dir}" > "${driver_log}" 2>&1
(cd "${case_dir}" && "${ccx_bin}" -i head-f36-thermal) >> "${driver_log}" 2>&1
"${python_bin}" "${solver}" --summarize --output "${case_dir}" >> "${driver_log}" 2>&1
test -s "${case_dir}/report.json"
printf '%s\n' "${case_dir}/report.json"
