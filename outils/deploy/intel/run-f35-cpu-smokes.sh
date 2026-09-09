#!/usr/bin/env bash
set -euo pipefail

fail() {
    printf 'intel-f35 smokes: %s\n' "$1" >&2
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker est absent"
command -v jq >/dev/null 2>&1 || fail "jq est absent"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum est absent"

gmsh_ref="${F35_GMSH_IMAGE_REF:-}"
openfoam_ref="${F35_OPENFOAM_IMAGE_REF:-}"
cantera_ref="${F35_CANTERA_IMAGE_REF:-ghcr.io/cluster2600/3dprinting993-engine-cycle-f33@sha256:287bd6ea04ff97205cbea9f63b2cc5a7c63ff754b27a183eb482e7896d1e9251}"
output_root="${1:-work/intel-f35/cpu-smokes-$(date -u +%Y%m%dT%H%M%SZ)}"

require_digest_ref() {
    local label="$1"
    local reference="$2"
    local expected_repository="$3"
    local digest=""
    test -n "${reference}" || fail "${label} image ref est requis"
    case "${reference}" in
        "${expected_repository}"@sha256:*) digest="${reference#${expected_repository}@sha256:}" ;;
        *) fail "${label} doit utiliser le depot exact ${expected_repository}" ;;
    esac
    [[ "${digest}" =~ ^[0-9a-f]{64}$ ]] \
        || fail "${label} doit etre referencee par digest OCI"
}

inspect_local_image() {
    local label="$1"
    local reference="$2"
    local expected_user="$3"
    docker image inspect "${reference}" >/dev/null 2>&1 \
        || fail "${label} absente localement; effectuer un pull explicite du digest"
    test "$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "${reference}")" = "linux/amd64" \
        || fail "${label} n'est pas linux/amd64"
    test "$(docker image inspect --format '{{.Config.User}}' "${reference}")" = "${expected_user}" \
        || fail "${label} n'a pas l'identite runtime attendue"
    docker image inspect --format '{{json .RepoDigests}}' "${reference}" \
        | jq -e --arg reference "${reference}" \
            'type == "array" and index($reference) != null' >/dev/null \
        || fail "${label} n'est pas chargee sous le digest OCI demande"
}

require_digest_ref "Gmsh" "${gmsh_ref}" \
    "ghcr.io/cluster2600/3dprinting993-gmsh-mesh-f35"
require_digest_ref "OpenFOAM" "${openfoam_ref}" \
    "ghcr.io/cluster2600/3dprinting993-openfoam-engine-f35"
require_digest_ref "Cantera" "${cantera_ref}" \
    "ghcr.io/cluster2600/3dprinting993-engine-cycle-f33"
inspect_local_image "Gmsh" "${gmsh_ref}" "9135:9135"
inspect_local_image "OpenFOAM" "${openfoam_ref}" "9135:9135"
inspect_local_image "Cantera" "${cantera_ref}" "9133:9133"

test ! -e "${output_root}" || fail "le repertoire de sortie existe deja: ${output_root}"
mkdir -p "${output_root}"

docker run --rm --platform linux/amd64 --user 9135:9135 \
    --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
    "${gmsh_ref}" >"${output_root}/gmsh-smoke.json" 2>"${output_root}/gmsh-smoke.stderr"
test ! -s "${output_root}/gmsh-smoke.stderr"
jq -e -s '
    length == 1 and
    (.[0] |
      type == "object" and
      (keys == [
        "claim_scope",
        "engine_geometry_verified",
        "fabrication_authorized",
        "fitment_verified",
        "mesh",
        "physical_release_gates",
        "physics_simulation_verified",
        "porsche_geometry_used",
        "runtime",
        "status"
      ]) and
      .status == "passed_synthetic_occ_volume_mesh_only" and
      .claim_scope == "synthetic_occ_volume_mesh_only" and
      .porsche_geometry_used == false and
      .engine_geometry_verified == false and
      .physics_simulation_verified == false and
      .fitment_verified == false and
      .fabrication_authorized == false and
      .runtime.runtime_uid == 9135 and
      .runtime.runtime_gid == 9135 and
      .runtime.gmsh_api_version == "4.15.2" and
      .runtime.resolved_elf_dependencies == true and
      (.runtime | keys == [
        "gmsh_api_version",
        "libgmsh_sha256",
        "resolved_elf_dependencies",
        "runtime_gid",
        "runtime_uid"
      ]) and
      .mesh.gmsh_version == "4.15.2" and
      .mesh.node_count > 0 and
      .mesh.element_count_3d > 0 and
      .mesh.minimum_jacobian_positive == true and
      .mesh.minimum_det_jac_positive == true and
      .mesh.minimum_sicn_positive == true and
      .mesh.physical_groups == ["fluid_volume", "inlet", "outlet", "wall"] and
      (.mesh | keys == [
        "element_count_3d",
        "element_types_3d",
        "gmsh_version",
        "minimum_det_jac_positive",
        "minimum_jacobian_positive",
        "minimum_sicn_positive",
        "node_count",
        "physical_groups"
      ]) and
      (.physical_release_gates | type == "object" and length > 0 and all(.[]; . == false))
    )
' "${output_root}/gmsh-smoke.json" >/dev/null \
    || fail "sortie Gmsh invalide ou gate physique ouvert"

docker run --rm --platform linux/amd64 --user 9135:9135 \
    --network none --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
    --tmpfs /dev/shm:rw,noexec,nosuid,nodev,size=512m \
    --pids-limit 256 --cap-drop ALL --security-opt no-new-privileges \
    "${openfoam_ref}" >"${output_root}/openfoam-smoke.json" 2>"${output_root}/openfoam-smoke.stderr"
test ! -s "${output_root}/openfoam-smoke.stderr"
jq -e -s '
    length == 1 and
    (.[0] |
      type == "object" and
      (keys == [
        "aate_utilities",
        "engine_simulation_proved",
        "mpi_ranks",
        "openfoam_major",
        "openfoam_package_version",
        "performance_1600_hp_proved",
        "status"
      ]) and
      .status == "passed_synthetic_serial_and_mpi_solver_smoke_only" and
      .openfoam_major == 14 and
      .openfoam_package_version == "20260724" and
      .mpi_ranks == 2 and
      .aate_utilities == 4 and
      .engine_simulation_proved == false and
      .performance_1600_hp_proved == false
    )
' "${output_root}/openfoam-smoke.json" >/dev/null \
    || fail "sortie OpenFOAM invalide ou claim physique contradictoire"

docker run --rm --platform linux/amd64 --user 9133:9133 \
    --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
    "${cantera_ref}" >"${output_root}/cantera-smoke.json" 2>"${output_root}/cantera-smoke.stderr"
test ! -s "${output_root}/cantera-smoke.stderr"
jq -e -s '
    length == 1 and
    (.[0] |
      type == "object" and
      (keys == [
        "cantera",
        "dependency_audit",
        "gpu_required",
        "network_isolation_evidence",
        "non_root",
        "offline",
        "physical_release_gates",
        "platform",
        "proof_boundary",
        "python",
        "runtime_identity",
        "schema_version",
        "status",
        "synthetic_fixture"
      ]) and
      .schema_version == "1.0.0" and
      .status == "passed_synthetic_thermochemistry_fixture_only" and
      .cantera == "3.2.0" and
      .platform == "linux/amd64-cpu" and
      .gpu_required == false and
      .non_root == true and
      .offline == true and
      .network_isolation_evidence.verified == true and
      (.network_isolation_evidence | keys == [
        "external_routed_interfaces",
        "hostname_recorded",
        "socket_module_available",
        "verified"
      ]) and
      .runtime_identity.uid == 9133 and
      .runtime_identity.gid == 9133 and
      (.runtime_identity | keys == [
        "account",
        "gid",
        "home_environment",
        "passwd_home",
        "uid",
        "xdg_cache_home"
      ]) and
      (.physical_release_gates | type == "object" and
        (keys == [
          "combustion_and_knock_validated",
          "controls_and_overspeed_protection_validated",
          "cooling_system_validated",
          "held_out_physical_correlation_complete",
          "manufacturing_authorized",
          "mass_and_energy_balance_validated",
          "metal_print_authorized",
          "oil_system_validated",
          "porsche_993_packaging_validated",
          "porsche_993_vehicle_installation_authorized",
          "structural_and_fatigue_validated",
          "target_definition_complete",
          "target_power_proven",
          "test_bench_start_authorized",
          "thermodynamic_cycle_validated",
          "turbo_match_validated"
        ]) and
        all(.[]; . == false)) and
      (.proof_boundary | type == "object" and
        (keys == [
          "engine_cycle_model",
          "engine_cycle_solver_executed",
          "omniverse_executed",
          "one_dimensional_gas_dynamics",
          "physical_correlation",
          "physicsnemo_executed",
          "predicted_engine_power",
          "synthetic_fixture",
          "validated_1600_hp"
        ]) and
        .engine_cycle_model == false and
        .engine_cycle_solver_executed == false and
        .omniverse_executed == false and
        .one_dimensional_gas_dynamics == false and
        .physical_correlation == false and
        .physicsnemo_executed == false and
        .predicted_engine_power == false and
        .synthetic_fixture == true and
        .validated_1600_hp == false) and
      .synthetic_fixture.uses_engine_calibration == false and
      .synthetic_fixture.uses_engine_geometry == false and
      .synthetic_fixture.uses_porsche_data == false and
      (.synthetic_fixture | keys == [
        "equilibrium_temperature_k",
        "fixture",
        "reactor_final_temperature_k",
        "reactor_final_time_s",
        "reactor_initial_temperature_k",
        "reactor_steps",
        "uses_engine_calibration",
        "uses_engine_geometry",
        "uses_porsche_data"
      ])
    )
' "${output_root}/cantera-smoke.json" >/dev/null \
    || fail "sortie Cantera invalide ou gate physique ouvert"

printf '%s\n' \
    "GMSH=${gmsh_ref}" \
    "OPENFOAM=${openfoam_ref}" \
    "CANTERA=${cantera_ref}" \
    >"${output_root}/image-refs.txt"

(
    cd "${output_root}"
    sha256sum \
        image-refs.txt \
        gmsh-smoke.json \
        openfoam-smoke.json \
        cantera-smoke.json \
        > evidence.sha256
)

printf '{"status":"passed_three_f35_cpu_software_smokes_only","gpu_required":false,"engine_simulation_proved":false,"performance_1600_hp_proved":false,"output":"%s"}\n' \
    "${output_root}"
