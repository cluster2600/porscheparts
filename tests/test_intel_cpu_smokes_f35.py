import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/intel/run-f35-cpu-smokes.sh"


class IntelCpuSmokesF35Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_all_three_images_require_immutable_digests(self):
        self.assertIn("F35_GMSH_IMAGE_REF", self.source)
        self.assertIn("F35_OPENFOAM_IMAGE_REF", self.source)
        self.assertIn("F35_CANTERA_IMAGE_REF", self.source)
        self.assertIn("^[0-9a-f]{64}$", self.source)
        for repository in (
            "ghcr.io/cluster2600/3dprinting993-gmsh-mesh-f35",
            "ghcr.io/cluster2600/3dprinting993-openfoam-engine-f35",
            "ghcr.io/cluster2600/3dprinting993-engine-cycle-f33",
        ):
            self.assertIn(repository, self.source)
        self.assertIn("docker image inspect", self.source)
        self.assertIn("{{json .RepoDigests}}", self.source)
        self.assertNotIn("docker pull", self.source)
        self.assertNotIn(":latest", self.source)

    def test_each_smoke_is_offline_hardened_and_claim_limited(self):
        self.assertEqual(self.source.count("--network none"), 3)
        self.assertEqual(self.source.count("--read-only"), 3)
        self.assertEqual(self.source.count("--cap-drop ALL"), 3)
        self.assertEqual(self.source.count("--security-opt no-new-privileges"), 3)
        for status in (
            "passed_synthetic_occ_volume_mesh_only",
            "passed_synthetic_serial_and_mpi_solver_smoke_only",
            "passed_synthetic_thermochemistry_fixture_only",
        ):
            self.assertIn(status, self.source)
        self.assertEqual(self.source.count("jq -e -s"), 3)
        self.assertNotIn("grep -F", self.source)
        self.assertIn("all(.[]; . == false)", self.source)
        self.assertIn('"engine_simulation_proved":false', self.source)
        self.assertIn('"performance_1600_hp_proved":false', self.source)

    def test_wrapper_has_no_remote_or_secret_access(self):
        lowered = self.source.lower()
        for forbidden in (
            "openbao",
            "bao kv",
            "security find-",
            "ssh ",
            "scp ",
            "rsync ",
            "curl ",
            "wget ",
        ):
            self.assertNotIn(forbidden, lowered)

    def _fixtures(self):
        false_gmsh_gates = {
            key: False
            for key in (
                "cfd_model_validated",
                "engine_geometry_scaled_and_registered",
                "engine_interfaces_dimensionally_verified",
                "engine_mesh_quality_validated",
                "engine_start_authorized",
                "fea_model_validated",
                "fitment_verified",
                "manufacturing_authorized",
                "metal_print_authorized",
                "physical_correlation_complete",
                "target_power_proven",
            )
        }
        false_cantera_gates = {
            key: False
            for key in (
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
                "turbo_match_validated",
            )
        }
        return {
            "gmsh": {
                "claim_scope": "synthetic_occ_volume_mesh_only",
                "engine_geometry_verified": False,
                "fabrication_authorized": False,
                "fitment_verified": False,
                "mesh": {
                    "element_count_3d": 1407,
                    "element_types_3d": [4],
                    "gmsh_version": "4.15.2",
                    "minimum_det_jac_positive": True,
                    "minimum_jacobian_positive": True,
                    "minimum_sicn_positive": True,
                    "node_count": 406,
                    "physical_groups": ["fluid_volume", "inlet", "outlet", "wall"],
                },
                "physical_release_gates": false_gmsh_gates,
                "physics_simulation_verified": False,
                "porsche_geometry_used": False,
                "runtime": {
                    "gmsh_api_version": "4.15.2",
                    "libgmsh_sha256": "9" * 64,
                    "resolved_elf_dependencies": True,
                    "runtime_gid": 9135,
                    "runtime_uid": 9135,
                },
                "status": "passed_synthetic_occ_volume_mesh_only",
            },
            "openfoam": {
                "aate_utilities": 4,
                "engine_simulation_proved": False,
                "mpi_ranks": 2,
                "openfoam_major": 14,
                "openfoam_package_version": "20260724",
                "performance_1600_hp_proved": False,
                "status": "passed_synthetic_serial_and_mpi_solver_smoke_only",
            },
            "cantera": {
                "cantera": "3.2.0",
                "dependency_audit": {},
                "gpu_required": False,
                "network_isolation_evidence": {
                    "external_routed_interfaces": [],
                    "hostname_recorded": False,
                    "socket_module_available": True,
                    "verified": True,
                },
                "non_root": True,
                "offline": True,
                "physical_release_gates": false_cantera_gates,
                "platform": "linux/amd64-cpu",
                "proof_boundary": {
                    "engine_cycle_model": False,
                    "engine_cycle_solver_executed": False,
                    "omniverse_executed": False,
                    "one_dimensional_gas_dynamics": False,
                    "physical_correlation": False,
                    "physicsnemo_executed": False,
                    "predicted_engine_power": False,
                    "synthetic_fixture": True,
                    "validated_1600_hp": False,
                },
                "python": "3.12.14",
                "runtime_identity": {
                    "account": "engine-cycle",
                    "gid": 9133,
                    "home_environment": "/tmp",
                    "passwd_home": "/tmp",
                    "uid": 9133,
                    "xdg_cache_home": "/tmp/cache",
                },
                "schema_version": "1.0.0",
                "status": "passed_synthetic_thermochemistry_fixture_only",
                "synthetic_fixture": {
                    "equilibrium_temperature_k": 2200.0,
                    "fixture": "synthetic",
                    "reactor_final_temperature_k": 2800.0,
                    "reactor_final_time_s": 0.001,
                    "reactor_initial_temperature_k": 1000.0,
                    "reactor_steps": 100,
                    "uses_engine_calibration": False,
                    "uses_engine_geometry": False,
                    "uses_porsche_data": False,
                },
            },
        }

    def _run_with_fake_docker(self, fixtures):
        with tempfile.TemporaryDirectory(prefix="intel-f35-wrapper-test-") as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fixture_paths = {}
            for name, payload in fixtures.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                fixture_paths[name] = path
            docker = fake_bin / "docker"
            docker.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = image ] && [ "$2" = inspect ]; then
  if [ "$3" != --format ]; then exit 0; fi
  format="$4"
  reference="$5"
  case "$format" in
    '{{.Os}}/{{.Architecture}}') printf '%s\n' 'linux/amd64' ;;
    '{{.Config.User}}')
      case "$reference" in
        *engine-cycle-f33*) printf '%s\n' '9133:9133' ;;
        *) printf '%s\n' '9135:9135' ;;
      esac ;;
    '{{json .RepoDigests}}') printf '["%s"]\n' "$reference" ;;
    *) exit 64 ;;
  esac
elif [ "$1" = run ]; then
  reference="${!#}"
  case "$reference" in
    *gmsh-mesh-f35*) cat "$FAKE_GMSH_JSON" ;;
    *openfoam-engine-f35*) cat "$FAKE_OPENFOAM_JSON" ;;
    *engine-cycle-f33*) cat "$FAKE_CANTERA_JSON" ;;
    *) exit 65 ;;
  esac
else
  exit 66
fi
""",
                encoding="utf-8",
            )
            docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
            digest = "a" * 64
            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{fake_bin}:{environment['PATH']}",
                    "FAKE_GMSH_JSON": str(fixture_paths["gmsh"]),
                    "FAKE_OPENFOAM_JSON": str(fixture_paths["openfoam"]),
                    "FAKE_CANTERA_JSON": str(fixture_paths["cantera"]),
                    "F35_GMSH_IMAGE_REF": (
                        "ghcr.io/cluster2600/3dprinting993-gmsh-mesh-f35@sha256:" + digest
                    ),
                    "F35_OPENFOAM_IMAGE_REF": (
                        "ghcr.io/cluster2600/3dprinting993-openfoam-engine-f35@sha256:" + digest
                    ),
                    "F35_CANTERA_IMAGE_REF": (
                        "ghcr.io/cluster2600/3dprinting993-engine-cycle-f33@sha256:" + digest
                    ),
                }
            )
            return subprocess.run(
                ["bash", str(SCRIPT), str(root / "evidence")],
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_valid_exact_reports_are_accepted(self):
        result = self._run_with_fake_docker(self._fixtures())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("passed_three_f35_cpu_software_smokes_only", result.stdout)

    def test_contradictory_physical_claim_is_rejected(self):
        fixtures = self._fixtures()
        fixtures["openfoam"]["target_power_proven"] = True
        result = self._run_with_fake_docker(fixtures)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("claim physique contradictoire", result.stderr)


if __name__ == "__main__":
    unittest.main()
