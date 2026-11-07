"""The upstream NCCL exception must not hide another dependency failure."""
import contextlib
import io
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch


CHECK = Path(__file__).resolve().parents[1] / "containers/stack-20261105/vllm-dependency-check.py"
VERSIONS = {
    "torch": "2.14.0+cu130", "nvidia-nccl-cu13": "2.31.2", "lmcache": "0.5.6",
    "opentelemetry-api": "1.40.0", "opentelemetry-exporter-otlp-proto-common": "1.40.0",
}
OVERRIDE = ('torch 2.14.0+cu130 has requirement nvidia-nccl-cu13==2.30.7; '
            'platform_system == "Linux", but you have nvidia-nccl-cu13 2.31.2.')


class DependencyCheckTests(unittest.TestCase):
    def run_check(self, versions=None, distributions=(), code=1, stdout=OVERRIDE, stderr=""):
        with patch("importlib.metadata.version", side_effect=(versions or VERSIONS).__getitem__), \
             patch("importlib.metadata.distributions", return_value=distributions), \
             patch("subprocess.run", return_value=subprocess.CompletedProcess([], code, stdout, stderr)), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            runpy.run_path(str(CHECK), run_name="__main__")
        return output.getvalue()

    def test_exact_upstream_override_is_explicit(self):
        self.assertIn('"pip_check_clean": false', self.run_check())

    def test_other_pip_results_are_rejected(self):
        for kwargs in ({"stdout": OVERRIDE + "\nunrelated mismatch"}, {"stderr": "warning"},
                       {"code": 0}, {"stdout": ""}):
            with self.subTest(kwargs=kwargs), self.assertRaises(AssertionError):
                self.run_check(**kwargs)

    def test_changed_versions_are_rejected(self):
        for name in VERSIONS:
            with self.subTest(package=name), self.assertRaises(AssertionError):
                self.run_check(versions={**VERSIONS, name: "0.0.0"})

    def test_experimental_exporter_is_rejected(self):
        distribution = SimpleNamespace(metadata={"Name": "opentelemetry-exporter-otlp-common"})
        with self.assertRaises(AssertionError):
            self.run_check(distributions=[distribution])
