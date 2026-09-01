"""Tests statiques et unitaires de l'image modulaire PhysicsNeMo CAE."""

from __future__ import annotations

import hashlib
import importlib.util
import json
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
LOCK = ROOT / "containers/physicsnemo-cae-cu12.lock.json"


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

    def test_lock_oci_est_immuable_public_et_borne(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        image = lock["image"]
        digest = image["digest"]
        manifest = image["manifest"]

        self.assertEqual(lock["schema_version"], "1.0.0")
        self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(
            image["immutable_reference"], f"{image['repository']}@{digest}"
        )
        self.assertEqual(image["platform"], {"os": "linux", "architecture": "amd64"})
        self.assertEqual(
            manifest["media_type"], "application/vnd.oci.image.manifest.v1+json"
        )
        self.assertGreater(manifest["layer_count"], 0)
        self.assertLess(
            manifest["largest_layer_bytes"],
            manifest["limits"]["max_layer_bytes_exclusive"],
        )
        self.assertLess(
            manifest["compressed_size_bytes"],
            manifest["limits"]["max_total_bytes_exclusive"],
        )
        self.assertTrue(manifest["limits_passed"])
        self.assertFalse(lock["recipe"]["image_revision_label_present"])
        self.assertFalse(lock["recipe"]["provenance_attestation_present"])
        self.assertFalse(lock["recipe"]["sbom_present"])

        verification = lock["verification"]
        self.assertEqual(verification["status"], "passed")
        self.assertEqual(verification["workflow"]["conclusion"], "success")
        self.assertTrue(verification["registry_manifest_digest_recomputed"])
        self.assertTrue(verification["published_digest_pulled"])
        self.assertTrue(verification["anonymous_exact_digest_access"])

    def test_lock_relit_les_hashes_des_entrees(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for source in lock["recipe"]["inputs"]:
            path = ROOT / source["path"]
            self.assertTrue(path.is_file(), source["path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                source["sha256"],
                source["path"],
            )

    def test_lock_reste_fail_closed_hors_preuve_runtime(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        smoke = lock["verification"]["offline_smoke"]
        self.assertEqual(smoke["status"], "passed")
        self.assertEqual(smoke["physicsnemo_version"], "2.2.1")
        self.assertEqual(smoke["torch_compiled_cuda"], "12.8")
        self.assertEqual(
            set(smoke["public_model_imports"]),
            {"DoMINO", "GeoTransolver", "MeshGraphNet"},
        )
        self.assertEqual(
            lock["bundled_assets"],
            {"raw_scans": False, "datasets": False, "model_weights": False},
        )
        self.assertFalse(smoke["gpu_runtime"]["checked"])

        gates = lock["release_gates"]
        self.assertTrue(gates.pop("image_build_and_public_pull"))
        self.assertTrue(gates)
        self.assertTrue(all(value is False for value in gates.values()))
        self.assertIn("ne prouve ni calcul moteur", lock["claim_scope"])


if __name__ == "__main__":
    unittest.main()
