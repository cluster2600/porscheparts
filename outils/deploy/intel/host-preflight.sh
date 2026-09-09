#!/usr/bin/env bash
set -euo pipefail

# Prévol strict et non intrusif du nœud CPU F35. Il ne découvre ni adresse,
# ni utilisateur, ni secret et ne télécharge aucune image.

fail() {
    printf 'intel-f35 preflight: %s\n' "$1" >&2
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker est absent"

docker_server_version="$(docker version --format '{{.Server.Version}}' 2>/dev/null)" \
    || fail "le moteur Docker est inaccessible"
docker_os="$(docker info --format '{{.OSType}}')"
docker_arch="$(docker info --format '{{.Architecture}}')"
docker_cpus="$(docker info --format '{{.NCPU}}')"
docker_memory_bytes="$(docker info --format '{{.MemTotal}}')"
docker_storage_driver="$(docker info --format '{{.Driver}}')"

test "${docker_os}" = "linux" \
    || fail "le moteur Docker doit exécuter des conteneurs Linux"
case "${docker_arch}" in
    amd64|x86_64) ;;
    *) fail "architecture Docker ${docker_arch}; linux/amd64 natif requis" ;;
esac
case "${docker_cpus}" in
    ''|*[!0-9]*) fail "nombre de CPU Docker illisible" ;;
esac
case "${docker_memory_bytes}" in
    ''|*[!0-9]*) fail "mémoire Docker illisible" ;;
esac

minimum_cpus=4
minimum_memory_bytes=17179869184
minimum_workspace_free_kib=41943040
test "${docker_cpus}" -ge "${minimum_cpus}" \
    || fail "au moins ${minimum_cpus} CPU Docker sont requis pour les smokes F35"
test "${docker_memory_bytes}" -ge "${minimum_memory_bytes}" \
    || fail "au moins 16 Gio de mémoire Docker sont requis pour les smokes F35"

host_os="$(uname -s)"
host_arch="$(uname -m)"
workspace_free_kib="$(df -Pk . | awk 'NR == 2 {print $4}')"
case "${workspace_free_kib}" in
    ''|*[!0-9]*) fail "espace disque du répertoire courant illisible" ;;
esac
test "${workspace_free_kib}" -ge "${minimum_workspace_free_kib}" \
    || fail "au moins 40 Gio libres sont requis dans le répertoire de travail"

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
