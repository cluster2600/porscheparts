#!/usr/bin/env python3
"""Vérification hors ligne de l'environnement PhysicsNeMo CAE.

Ce test prouve seulement que les versions et imports attendus sont présents.
CUDA n'est interrogé que lorsque ``--require-gpu`` (ou la variable
``PHYSICSNEMO_REQUIRE_GPU=1``) est fourni.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any


EXPECTED_PHYSICSNEMO_VERSION = "2.2.1"
EXPECTED_TORCH_VERSION = "2.10.0"
EXPECTED_TORCHVISION_VERSION = "0.25.0"
EXPECTED_TORCH_CUDA_VERSION = "12.8"


def _env_flag(name: str) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if value in {"", "0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    raise ValueError(f"{name} doit valoir 0/1, true/false, yes/no ou on/off")


def _base_version(version: str) -> str:
    return version.split("+", 1)[0]


def _require_equal(label: str, actual: str, expected: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{label}: version {actual!r}, attendu {expected!r}")


def _pip_check() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        check=False,
        capture_output=True,
        env={**os.environ, "PIP_NO_INDEX": "1"},
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise RuntimeError(f"pip check a échoué: {detail}")


def run_smoke(*, require_gpu: bool, run_pip_check: bool = True) -> dict[str, Any]:
    """Exécute le smoke test sans réseau et retourne son rapport JSON."""

    if sys.version_info < (3, 11):
        raise RuntimeError(f"Python >=3.11 requis, trouvé {sys.version.split()[0]}")

    import physicsnemo
    import torch
    import torchvision
    from physicsnemo.models.domino import DoMINO
    from physicsnemo.models.geotransolver import GeoTransolver
    from physicsnemo.models.meshgraphnet import MeshGraphNet

    _require_equal(
        "PhysicsNeMo",
        physicsnemo.__version__,
        EXPECTED_PHYSICSNEMO_VERSION,
    )
    _require_equal(
        "PyTorch",
        _base_version(torch.__version__),
        EXPECTED_TORCH_VERSION,
    )
    _require_equal(
        "torchvision",
        _base_version(torchvision.__version__),
        EXPECTED_TORCHVISION_VERSION,
    )
    _require_equal(
        "CUDA compilé dans PyTorch",
        str(torch.version.cuda),
        EXPECTED_TORCH_CUDA_VERSION,
    )

    if run_pip_check:
        _pip_check()

    gpu_runtime: dict[str, Any] = {
        "required": require_gpu,
        "checked": False,
    }
    if require_gpu:
        gpu_runtime["checked"] = True
        if not torch.cuda.is_available():
            raise RuntimeError(
                "GPU demandé mais CUDA est indisponible; vérifier le pilote NVIDIA "
                "et le lancement avec --gpus all"
            )
        gpu_count = torch.cuda.device_count()
        if gpu_count < 1:
            raise RuntimeError("GPU demandé mais aucun périphérique CUDA n'est visible")
        device = torch.cuda.current_device()
        properties = torch.cuda.get_device_properties(device)
        tensor = torch.tensor([1.0, 2.0, 3.0], device="cuda")
        tensor_result = float((tensor * tensor).sum().item())
        torch.cuda.synchronize(device)
        if tensor_result != 14.0:
            raise RuntimeError(f"calcul CUDA incorrect: {tensor_result}")
        gpu_runtime.update(
            {
                "count": gpu_count,
                "name": properties.name,
                "memory_bytes": properties.total_memory,
                "tensor_result": tensor_result,
            }
        )

    return {
        "schema_version": "1.0.0",
        "status": "passed",
        "offline_smoke": True,
        "python_version": sys.version.split()[0],
        "physicsnemo_version": physicsnemo.__version__,
        "torch_version": torch.__version__,
        "torchvision_version": torchvision.__version__,
        "torch_compiled_cuda": torch.version.cuda,
        "public_model_imports": {
            "DoMINO": f"{DoMINO.__module__}.{DoMINO.__name__}",
            "GeoTransolver": f"{GeoTransolver.__module__}.{GeoTransolver.__name__}",
            "MeshGraphNet": f"{MeshGraphNet.__module__}.{MeshGraphNet.__name__}",
        },
        "gpu_runtime": gpu_runtime,
        "bundled_assets": {
            "raw_scans": False,
            "datasets": False,
            "model_weights": False,
        },
        "claim_scope": (
            "versions, public imports and optional CUDA tensor only; no reference "
            "solver, training, engine simulation, physical correlation or "
            "manufacturing validation"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-gpu",
        action="store_true",
        default=_env_flag("PHYSICSNEMO_REQUIRE_GPU"),
        help="échoue si aucun GPU CUDA utilisable n'est visible",
    )
    parser.add_argument(
        "--skip-pip-check",
        action="store_true",
        help="saute uniquement la vérification locale des dépendances installées",
    )
    args = parser.parse_args()

    try:
        report = run_smoke(
            require_gpu=args.require_gpu,
            run_pip_check=not args.skip_pip_check,
        )
    except Exception as exc:  # rapport exploitable par le contrôleur de location
        print(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "status": "failed",
                    "error": str(exc),
                    "gpu_required": args.require_gpu,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
