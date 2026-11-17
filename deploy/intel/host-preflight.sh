#!/usr/bin/env bash
set -euo pipefail

# Strict, non-intrusive preflight of the F35 CPU node. It discovers no address,
# user or secret and downloads no image.

fail() {
    printf 'intel-f35 preflight: %s\n' "$1" >&2
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker is missing"

docker_server_version="$(docker version --format '{{.Server.Version}}' 2>/dev/null)" \
    || fail "the Docker engine is unreachable"
docker_os="$(docker info --format '{{.OSType}}')"
docker_arch="$(docker info --format '{{.Architecture}}')"
docker_cpus="$(docker info --format '{{.NCPU}}')"
docker_memory_bytes="$(docker info --format '{{.MemTotal}}')"
docker_storage_driver="$(docker info --format '{{.Driver}}')"

test "${docker_os}" = "linux" \
    || fail "the Docker engine must run Linux containers"
case "${docker_arch}" in
    amd64|x86_64) ;;
    *) fail "Docker architecture ${docker_arch}; native linux/amd64 required" ;;
esac
case "${docker_cpus}" in
    ''|*[!0-9]*) fail "Docker CPU count unreadable" ;;
esac
case "${docker_memory_bytes}" in
    ''|*[!0-9]*) fail "Docker memory unreadable" ;;
esac

minimum_cpus=4
minimum_memory_bytes=17179869184
minimum_workspace_free_kib=41943040
test "${docker_cpus}" -ge "${minimum_cpus}" \
    || fail "at least ${minimum_cpus} Docker CPUs are required for the F35 smokes"
test "${docker_memory_bytes}" -ge "${minimum_memory_bytes}" \
    || fail "at least 16 GiB of Docker memory is required for the F35 smokes"

host_os="$(uname -s)"
host_arch="$(uname -m)"
workspace_free_kib="$(df -Pk . | awk 'NR == 2 {print $4}')"
case "${workspace_free_kib}" in
    ''|*[!0-9]*) fail "disk space of the current directory unreadable" ;;
esac
test "${workspace_free_kib}" -ge "${minimum_workspace_free_kib}" \
    || fail "at least 40 GiB free is required in the working directory"

printf '{"status":"ready_for_f35_cpu_smokes","host_os":"%s","host_arch":"%s","docker_os":"%s","docker_arch":"%s","docker_server_version":"%s","docker_cpus":%s,"docker_memory_bytes":%s,"docker_storage_driver":"%s","workspace_free_kib":%s,"minimum_requirements":{"docker_cpus":%s,"docker_memory_bytes":%s,"workspace_free_kib":%s},"native_linux_amd64_required":true,"nvidia_gpu_required":false,"engine_simulation_proved":false,"performance_1600_hp_proved":false}\n' \
    "${host_os}" \
    "${host_arch}" \
    "${docker_os}" \
    "${docker_arch}" \
    "${docker_server_version}" \
    "${docker_cpus}" \
    "${docker_memory_bytes}" \
    "${docker_storage_driver}" \
    "${workspace_free_kib}" \
    "${minimum_cpus}" \
    "${minimum_memory_bytes}" \
    "${minimum_workspace_free_kib}"
