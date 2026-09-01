#!/usr/bin/env python3
"""Fail closed unless the pinned PhysicsNeMo stack executes on the active GPU."""

from __future__ import annotations

import json

import physicsnemo
import torch
import torchvision


assert physicsnemo.__version__ == "2.2.0", physicsnemo.__version__
assert torch.__version__.split("+", 1)[0] == "2.10.0", torch.__version__
assert torch.version.cuda == "12.9", torch.version.cuda
assert torchvision.__version__.split("+", 1)[0] == "0.25.0", torchvision.__version__
assert torch.cuda.is_available(), "CUDA is unavailable to the PhysicsNeMo environment"
assert torch.cuda.device_count() == 1, torch.cuda.device_count()

device = torch.cuda.current_device()
properties = torch.cuda.get_device_properties(device)
tensor = torch.tensor([1.0, 2.0, 3.0], device="cuda")
tensor_result = float((tensor * tensor).sum().item())
torch.cuda.synchronize(device)
assert tensor_result == 14.0, tensor_result

print(
    json.dumps(
        {
            "schema_version": "1.0.0",
            "status": "passed",
            "claim_scope": "runtime GPU only; no engine simulation or physical validation",
            "physicsnemo_version": physicsnemo.__version__,
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "gpu_name": properties.name,
            "gpu_memory_bytes": properties.total_memory,
            "gpu_count": torch.cuda.device_count(),
            "tensor_result": tensor_result,
        },
        indent=2,
        sort_keys=True,
    )
)
