import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "deploy/intel/host-preflight.sh"


class IntelCpuNodeF35Tests(unittest.TestCase):
    def _write_executable(self, path: Path, source: str) -> None:
        path.write_text(source, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _run_preflight(
        self,
        docker_arch: str = "x86_64",
        docker_cpus: str = "32",
        docker_memory_bytes: str = "137438953472",
        workspace_free_kib: str = "104857600",
    ) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as temporary:
            fake_bin = Path(temporary)
            self._write_executable(
                fake_bin / "docker",
                """#!/bin/sh
case "$*" in
  "version --format {{.Server.Version}}") printf '%s\\n' '29.1.0' ;;
  "info --format {{.OSType}}") printf '%s\\n' 'linux' ;;
  "info --format {{.Architecture}}") printf '%s\\n' "${FAKE_DOCKER_ARCH}" ;;
  "info --format {{.NCPU}}") printf '%s\\n' "${FAKE_DOCKER_CPUS}" ;;
  "info --format {{.MemTotal}}") printf '%s\\n' "${FAKE_DOCKER_MEMORY_BYTES}" ;;
  "info --format {{.Driver}}") printf '%s\\n' 'overlay2' ;;
  *) exit 64 ;;
esac
""",
            )
            self._write_executable(
                fake_bin / "uname",
                """#!/bin/sh
case "$1" in
  -s) printf '%s\\n' 'Linux' ;;
  -m) printf '%s\\n' 'x86_64' ;;
  *) exit 64 ;;
esac
""",
            )
            self._write_executable(
                fake_bin / "df",
                """#!/bin/sh
printf '%s\n' 'Filesystem 1024-blocks Used Available Capacity Mounted on'
printf 'fake 209715200 1 %s 1%% /\n' "${FAKE_WORKSPACE_FREE_KIB}"
""",
            )
            environment = os.environ.copy()
            environment["FAKE_DOCKER_ARCH"] = docker_arch
            environment["FAKE_DOCKER_CPUS"] = docker_cpus
            environment["FAKE_DOCKER_MEMORY_BYTES"] = docker_memory_bytes
            environment["FAKE_WORKSPACE_FREE_KIB"] = workspace_free_kib
            environment["PATH"] = f"{fake_bin}:/usr/bin:/bin"
            return subprocess.run(
                ["bash", str(PREFLIGHT)],
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_native_linux_amd64_cpu_node_passes_without_gpu(self):
        result = self._run_preflight()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "ready_for_f35_cpu_smokes")
        self.assertEqual(report["docker_arch"], "x86_64")
        self.assertEqual(report["docker_cpus"], 32)
        self.assertEqual(report["minimum_requirements"]["docker_cpus"], 4)
        self.assertEqual(report["minimum_requirements"]["docker_memory_bytes"], 17179869184)
        self.assertEqual(report["minimum_requirements"]["workspace_free_kib"], 41943040)
        self.assertFalse(report["nvidia_gpu_required"])
        self.assertFalse(report["engine_simulation_proved"])
        self.assertFalse(report["performance_1600_hp_proved"])

    def test_non_amd64_docker_engine_fails_closed(self):
        result = self._run_preflight("aarch64")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("linux/amd64 natif requis", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_resources_below_smoke_minimum_fail_closed(self):
        cases = (
            {"docker_cpus": "3"},
            {"docker_memory_bytes": "17179869183"},
            {"workspace_free_kib": "41943039"},
        )
        for values in cases:
            with self.subTest(values=values):
                result = self._run_preflight(**values)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_script_does_not_access_credentials_or_network(self):
        source = PREFLIGHT.read_text(encoding="utf-8").lower()
        for forbidden in (
            "openbao",
            "bao kv",
            "security find-",
            "curl ",
            "wget ",
            "ssh ",
            "docker pull",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
