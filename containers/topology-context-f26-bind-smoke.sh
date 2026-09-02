#!/usr/bin/env bash
set -euo pipefail

if test "$#" -ne 1; then
  printf 'usage: %s IMAGE_REFERENCE\n' "$0" >&2
  exit 64
fi

image_reference="$1"
bind_parent="${RUNNER_TEMP:-/tmp}"
bind_root="$(mktemp -d "${bind_parent%/}/topology-context-f26-bind.XXXXXXXX")"

cleanup() {
  case "${bind_root}" in
    "${bind_parent%/}"/topology-context-f26-bind.*)
      sudo rm -rf -- "${bind_root}"
      ;;
    *)
      printf 'refusing unsafe bind-smoke cleanup target\n' >&2
      ;;
  esac
}
trap cleanup EXIT

input_dir="${bind_root}/input"
output_dir="${bind_root}/output"
mkdir "${input_dir}" "${output_dir}"
sudo chown 9174:9174 "${input_dir}" "${output_dir}"
sudo chmod 0700 "${input_dir}" "${output_dir}"

docker run --rm --platform linux/amd64 --user 9174:9174 \
  --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=${input_dir},dst=/workspace/export" \
  "${image_reference}" \
  /usr/local/bin/topology-context-f26-smoke \
  --export-fixture /workspace/export \
  >"${bind_root}/fixture-export.json"

fixture_evidence="${input_dir}/synthetic-bind-fixture-f26.json"
mesh_name="$(sudo jq -er '.mesh_name' "${fixture_evidence}")"
mesh_sha256="$(sudo jq -er '.mesh_sha256' "${fixture_evidence}")"
report_name="$(sudo jq -er '.report_name' "${fixture_evidence}")"
report_sha256="$(sudo jq -er '.report_sha256' "${fixture_evidence}")"
contract_sha256="$(sudo jq -er '.contract_sha256' "${fixture_evidence}")"
mesh_before="$(sudo sha256sum "${input_dir}/${mesh_name}" | cut -d' ' -f1)"
report_before="$(sudo sha256sum "${input_dir}/${report_name}" | cut -d' ' -f1)"
test "${mesh_before}" = "${mesh_sha256}"
test "${report_before}" = "${report_sha256}"

docker run --rm --platform linux/amd64 --user 9174:9174 \
  --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=${input_dir},dst=/workspace/input,readonly" \
  --mount "type=bind,src=${output_dir},dst=/workspace/output" \
  "${image_reference}" \
  python /opt/3dprinting993/twins/reference-917-engine/source/build_topology_context_f26.py \
    --contract /opt/3dprinting993/twins/reference-917-engine/topology-context-contract-f26.json \
    --contract-sha256 "${contract_sha256}" \
    --mesh "/workspace/input/${mesh_name}" \
    --mesh-sha256 "${mesh_sha256}" \
    --f18-report "/workspace/input/${report_name}" \
    --f18-report-sha256 "${report_sha256}" \
    --expected-components 2 \
    --batch-size 1 \
    --fixture-mode \
    --output /workspace/output/topology-context-f26 \
  >"${bind_root}/generator-summary.json"

mesh_after="$(sudo sha256sum "${input_dir}/${mesh_name}" | cut -d' ' -f1)"
report_after="$(sudo sha256sum "${input_dir}/${report_name}" | cut -d' ' -f1)"
test "${mesh_after}" = "${mesh_before}"
test "${report_after}" = "${report_before}"

manifest="${output_dir}/topology-context-f26/topology-context-manifest-f26.json"
inventory="${output_dir}/topology-context-f26/topology-context-inventory-f26.csv"
sudo test -s "${manifest}"
sudo test -s "${inventory}"
sudo test "$(sudo stat -c '%u:%g' "${output_dir}/topology-context-f26")" = "9174:9174"
sudo test "$(sudo stat -c '%a' "${output_dir}/topology-context-f26")" = "700"
sudo test -z "$(sudo find "${output_dir}/topology-context-f26" -type f \! -uid 9174 -print -quit)"
sudo jq -e \
  --arg report_name "${report_name}" '
    .status == "complete_local_topology_context_pending_human_review" and
    .source_binding.f18_report_name == $report_name and
    .review_policy.component_count == 2 and
    .review_policy.confirmed_interface_count == 0 and
    .topology_policy.topological_ring_count == 2 and
    .output_bounds.publication == "private_parent_0700_owned_by_runtime_uid_exclusive_new_directory_with_manifest_linked_last" and
    all(.release_gates[]; . == false)
  ' "${manifest}" >/dev/null

output_file_count="$(sudo find "${output_dir}/topology-context-f26" -type f | wc -l | tr -d ' ')"
jq -n \
  --arg image_reference "${image_reference}" \
  --arg mesh_sha256 "${mesh_sha256}" \
  --arg report_sha256 "${report_sha256}" \
  --arg report_name "${report_name}" \
  --argjson output_file_count "${output_file_count}" '
  {
    schema_version: "1.0.0",
    status: "passed_synthetic_bind_mount_fixture_only",
    image_reference: $image_reference,
    runtime_uid_gid: "9174:9174",
    input_mount_read_only: true,
    output_mount_read_write: true,
    output_parent_mode: "0700",
    root_filesystem_read_only: true,
    network_none: true,
    capabilities_dropped: "ALL",
    no_new_privileges: true,
    input_hashes_unchanged: true,
    mesh_sha256: $mesh_sha256,
    report_name: $report_name,
    report_sha256: $report_sha256,
    output_file_count: $output_file_count,
    output_owned_by_runtime_uid: true,
    manifest_validated: true,
    canonical_scan_used: false,
    confirmed_interfaces: 0
  }'
