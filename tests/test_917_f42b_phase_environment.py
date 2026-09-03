"""Tests de l'environnement commun des phases distantes F42b."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "twins/reference-917-engine/remote-simready/_common.sh"


class F42bPhaseEnvironmentTests(unittest.TestCase):
    def run_common(
        self,
        fragment: str,
        *,
        usd_python: str,
        environment: dict[str, str] | None = None,
        bytecode_value: str | None = "0",
    ) -> subprocess.CompletedProcess[str]:
        process_environment = {
            **os.environ,
            "PATH": "/usr/bin:/bin",
            "USD_PYTHON": usd_python,
            **(environment or {}),
        }
        if bytecode_value is None:
            process_environment.pop("PYTHONDONTWRITEBYTECODE", None)
        else:
            process_environment["PYTHONDONTWRITEBYTECODE"] = bytecode_value
        return subprocess.run(
            [
                "/bin/bash",
                "-c",
                "set -euo pipefail; "
                f". {shlex.quote(str(COMMON))}; "
                + fragment,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=process_environment,
        )

    def test_usd_python_directory_is_first_and_bytecode_is_forced_off(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            binary_directory = Path(temporary) / "usd-bin"
            binary_directory.mkdir()
            usd_python = binary_directory / "python"
            usd_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            usd_python.chmod(0o700)
            validator = binary_directory / "simready-validate"
            validator.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            validator.chmod(0o700)

            result = self.run_common(
                'printf "%s\\n%s\\n%s\\n" "${PATH%%:*}" '
                '"${PYTHONDONTWRITEBYTECODE}" "$(command -v simready-validate)"',
                usd_python=str(usd_python),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.splitlines(),
                [str(binary_directory), "1", str(validator)],
            )

    def test_prefix_is_restored_after_a_later_environment_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            binary_directory = Path(temporary) / "usd-bin"
            binary_directory.mkdir()
            usd_python = binary_directory / "python"
            usd_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            usd_python.chmod(0o700)

            result = self.run_common(
                'PATH="/late/preflight/bin:/usr/bin:/bin"; '
                'PYTHONDONTWRITEBYTECODE=0; configure_phase_environment; '
                'printf "%s\\n%s\\n" "${PATH%%:*}" "${PYTHONDONTWRITEBYTECODE}"',
                usd_python=str(usd_python),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [str(binary_directory), "1"])

    def test_relative_usd_python_is_rejected(self) -> None:
        result = self.run_common(":", usd_python="python")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("USD_PYTHON doit être absolu", result.stderr)

    def test_import_from_transferred_skill_does_not_write_pyc(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            skill = (
                Path(temporary)
                / "workspace/jobs/job/vendor/omniverse-cad-to-simready"
            )
            references = skill / "references"
            references.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            (references / "probe.py").write_text("VALUE = 42\n", encoding="utf-8")

            result = self.run_common(
                '"${USD_PYTHON}" -c '
                "'import os, sys; "
                'assert os.environ["PYTHONDONTWRITEBYTECODE"] == "1"; '
                'sys.path.insert(0, os.environ["PROBE_ROOT"]); '
                "import probe; assert probe.VALUE == 42'",
                usd_python=sys.executable,
                environment={"PROBE_ROOT": str(references)},
                bytecode_value=None,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(skill.rglob("*.pyc")), [])
            self.assertFalse((references / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
