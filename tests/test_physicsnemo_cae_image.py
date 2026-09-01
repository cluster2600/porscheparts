"""Tests statiques et unitaires de l'image modulaire PhysicsNeMo CAE."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/physicsnemo-cae-cu12.Dockerfile"
CONSTRAINTS = ROOT / "containers/physicsnemo-cae-cu12-constraints.txt"
SMOKE = ROOT / "containers/physicsnemo-cae-cu12-smoke.py"
README = ROOT / "containers/README.physicsnemo-cae-cu12.md"
WORKFLOW = ROOT / ".github/workflows/physicsnemo-cae-image.yml"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("physicsnemo_cae_smoke", SMOKE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_modules(*, cuda_available: bool | None) -> dict[str, ModuleType]:
    physicsnemo = ModuleType("physicsnemo")
    physicsnemo.__version__ = "2.2.1"
    models = ModuleType("physicsnemo.models")
    models.__path__ = []

    modules: dict[str, ModuleType] = {
        "physicsnemo": physicsnemo,
        "physicsnemo.models": models,
    }
    for family, class_name in (
        ("domino", "DoMINO"),
        ("geotransolver", "GeoTransolver"),
        ("meshgraphnet", "MeshGraphNet"),
    ):
        family_module = ModuleType(f"physicsnemo.models.{family}")
        model_class = type(
            class_name,
            (),
            {"__module__": f"physicsnemo.models.{family}"},
        )
        setattr(family_module, class_name, model_class)
        modules[family_module.__name__] = family_module

    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            if cuda_available is None:
                raise AssertionError("CUDA ne doit pas être interrogé sans --require-gpu")
            return cuda_available

        @staticmethod
        def device_count() -> int:
            raise AssertionError("device_count ne doit pas être appelé sans GPU")

    torch = ModuleType("torch")
    torch.__version__ = "2.10.0+cu128"
    torch.version = SimpleNamespace(cuda="12.8")
    torch.cuda = FakeCuda()
    modules["torch"] = torch

    torchvision = ModuleType("torchvision")
    torchvision.__version__ = "0.25.0+cu128"
    modules["torchvision"] = torchvision
    return modules


class PhysicsNeMoCaeImageTests(unittest.TestCase):
    def test_dockerfile_est_cuda12_amd64_et_minimal(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("12.8.1-cudnn-runtime-ubuntu24.04@sha256:", dockerfile)
        self.assertIn('test "${TARGETARCH}" = "amd64"', dockerfile)
        self.assertIn("PHYSICSNEMO_VERSION=2.2.1", dockerfile)
        self.assertIn("TORCH_VERSION=2.10.0", dockerfile)
        self.assertIn("TORCHVISION_VERSION=0.25.0", dockerfile)
        self.assertIn("PHYSICSNEMO_UID=9170", dockerfile)
        self.assertIn("PHYSICSNEMO_GID=9170", dockerfile)
        self.assertIn("USER ${PHYSICSNEMO_UID}:${PHYSICSNEMO_GID}", dockerfile)
        self.assertNotIn("--gid 1000 physicsnemo", dockerfile)
        self.assertIn("ANTLR4_RUNTIME_VERSION=4.9.3", dockerfile)
        self.assertIn(
            "f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b",
            dockerfile,
        )
        self.assertIn("pip wheel --no-build-isolation --no-deps", dockerfile)
        self.assertIn("https://download.pytorch.org/whl/cu128", dockerfile)
        self.assertIn(
            '"nvidia-physicsnemo[mesh-extras]==${PHYSICSNEMO_VERSION}"',
            dockerfile,
        )
        self.assertNotIn("mesh-extras,gnns", dockerfile)
        self.assertNotIn("nvidia-physicsnemo[cu12", dockerfile)
        self.assertNotIn("cu13", dockerfile.lower())
        self.assertNotIn("nvcr.io", dockerfile.lower())
        self.assertNotIn("ngc", dockerfile.lower())

        copy_lines = [
            line.strip() for line in dockerfile.splitlines() if line.startswith("COPY ")
        ]
        self.assertEqual(
            copy_lines,
            [
                "COPY containers/physicsnemo-cae-cu12-constraints.txt /opt/build/constraints.txt",
                "COPY containers/physicsnemo-cae-cu12-smoke.py /usr/local/bin/physicsnemo-cae-smoke",
            ],
        )
        for forbidden in ("raw-scans", "COPY .", "COPY twins", "COPY work", "huggingface"):
            self.assertNotIn(forbidden, dockerfile)

    def test_versions_de_premier_niveau_sont_epinglees(self):
        constraints = CONSTRAINTS.read_text(encoding="utf-8")
        for requirement in (
            "pip==26.2.1",
            "setuptools==84.0.0",
            "wheel==0.48.0",
            "nvidia-physicsnemo==2.2.1",
            "antlr4-python3-runtime==4.9.3",
            "torch==2.10.0",
            "torchvision==0.25.0",
            "torch-geometric==2.8.0.post1",
            "torch-scatter==2.1.2+pt210cu128",
            "torch-sparse==0.6.18+pt210cu128",
            "torch-cluster==1.6.3+pt210cu128",
        ):
            self.assertIn(requirement, constraints)

    def test_smoke_sans_gpu_n_interroge_pas_cuda(self):
        smoke = _load_smoke_module()
        with patch.object(sys, "version_info", (3, 12, 0)), patch.dict(
            sys.modules, _fake_modules(cuda_available=None), clear=False
        ):
            report = smoke.run_smoke(require_gpu=False, run_pip_check=False)
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["gpu_runtime"]["required"])
        self.assertFalse(report["gpu_runtime"]["checked"])
        self.assertEqual(
            set(report["public_model_imports"]),
            {"DoMINO", "GeoTransolver", "MeshGraphNet"},
        )
        self.assertEqual(
            report["bundled_assets"],
            {"raw_scans": False, "datasets": False, "model_weights": False},
        )

    def test_smoke_gpu_echoue_si_cuda_est_absent(self):
        smoke = _load_smoke_module()
        with patch.object(sys, "version_info", (3, 12, 0)), patch.dict(
            sys.modules, _fake_modules(cuda_available=False), clear=False
        ):
            with self.assertRaisesRegex(RuntimeError, "CUDA est indisponible"):
                smoke.run_smoke(require_gpu=True, run_pip_check=False)

    def test_documentation_separe_solveur_surrogate_et_fabrication(self):
        readme = README.read_text(encoding="utf-8")
        for fragment in (
            "Frontière solveur / surrogate",
            "PhysicsNeMo n'est pas le solveur physique de référence",
            "corrélation physique",
            "ne rend pas une pièce fonctionnelle, sûre ou",
            "Apache-2.0",
            "NVIDIA CUDA Toolkit EULA",
            "aucun scan, dataset, poids de modèle",
            "digest immuable",
            "linux/amd64",
        ):
            self.assertIn(fragment, readme)

    def test_workflow_publie_et_teste_un_digest_linux_amd64(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "platforms: linux/amd64",
            "provenance: false",
            "steps.build.outputs.digest",
            "docker pull \"${pinned_ref}\"",
            "--network none",
            "--entrypoint /opt/physicsnemo/bin/python",
            "/usr/local/bin/physicsnemo-cae-smoke",
            "docker buildx imagetools inspect --raw",
            "application/vnd.oci.image.manifest.v1+json",
            "DOCKER_CONFIG=\"${anonymous_config}\"",
            "physicsnemo-cae-smoke.json",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("cache-to: type=gha,mode=max", workflow)


if __name__ == "__main__":
    unittest.main()
