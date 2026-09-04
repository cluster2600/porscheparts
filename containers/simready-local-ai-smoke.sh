#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${LOCAL_VLM_PATH:-/opt/models/qwen2.5-vl-7b-instruct}"
MODEL_NAME="${LOCAL_VLM_MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"
VLLM_LIBRARY_PATH="${VLLM_LIBRARY_PATH:-/opt/local-ai/lib/python3.12/site-packages/torch/lib:/opt/local-ai/lib/python3.12/site-packages/nvidia/cu13/lib:/opt/local-ai/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:/opt/local-ai/lib/python3.12/site-packages/nvidia/cuda_nvrtc/lib}"
if [ -n "${LD_LIBRARY_PATH:-}" ]; then
    VLLM_LIBRARY_PATH="${VLLM_LIBRARY_PATH}:${LD_LIBRARY_PATH}"
fi

test -x /opt/local-ai/bin/vllm
test -f "${MODEL_PATH}/config.json"
test -f "${MODEL_PATH}/model.safetensors.index.json"
test -f "${MODEL_PATH}/LICENSE.apache-2.0"
/opt/local-ai/bin/pip check
"${PHYSICSNEMO_PYTHON:-/opt/venv/bin/python}" -m pip check
env LD_LIBRARY_PATH="${VLLM_LIBRARY_PATH}" /opt/local-ai/bin/python -c 'from importlib.metadata import version; import torch, torchaudio, torchvision, vllm; actual={"distribution":version("vllm"),"runtime":vllm.__version__,"torch":torch.__version__,"cuda":torch.version.cuda,"torchaudio":torchaudio.__version__,"torchvision":torchvision.__version__}; print(actual); assert actual["distribution"].split("+", 1)[0] == "0.26.0", actual; assert actual["runtime"].split("+", 1)[0] == "0.26.0", actual; assert actual["torch"].split("+", 1)[0] == "2.11.0", actual; assert actual["cuda"] == "12.9", actual; assert actual["torchaudio"].split("+", 1)[0] == "2.11.0", actual; assert actual["torchvision"].split("+", 1)[0] == "0.26.0", actual'
"${PHYSICSNEMO_PYTHON:-/opt/venv/bin/python}" -c 'import physicsnemo, torch, torchvision; assert physicsnemo.__version__ == "2.2.0"; assert torch.__version__.split("+", 1)[0] == "2.10.0"; assert torch.version.cuda == "12.9", torch.version.cuda; assert torchvision.__version__.split("+", 1)[0] == "0.25.0"'

if [ "${1:-}" = "--offline" ]; then
    echo "simready local AI: offline image checks passed"
    exit 0
fi

curl --fail --silent --show-error --max-time 15 \
    http://127.0.0.1:8000/v1/models \
    | jq -e --arg model "${MODEL_NAME}" '.data | any(.id == $model)' >/dev/null

curl --fail --silent --show-error --max-time 60 \
    --header 'Content-Type: application/json' \
    --data "{\"model\":\"${MODEL_NAME}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply exactly: local-ai-ok\"}],\"max_tokens\":16,\"temperature\":0}" \
    http://127.0.0.1:8000/v1/chat/completions \
    | jq -e '.choices[0].message.content | ascii_downcase | contains("local-ai-ok")' >/dev/null

curl --fail --silent --show-error --max-time 90 \
    --header 'Content-Type: application/json' \
    --data "{\"model\":\"${MODEL_NAME}\",\"messages\":[{\"role\":\"user\",\"content\":[{\"type\":\"text\",\"text\":\"Reply with the dominant colour only.\"},{\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADgAAAA4CAIAAAAn5KxJAAAASElEQVR4nO3OQQkAMBADsPo3vTm4bykEIiB5yYT+QFRUVFRUVFRUVHRAfyAqKioqKioqKio6oD8QFRUVFRUVFRUVHdAfiIrePiJyNHVX9iCVAAAAAElFTkSuQmCC\"}}]}],\"max_tokens\":16,\"temperature\":0}" \
    http://127.0.0.1:8000/v1/chat/completions \
    | jq -e '.choices[0].message.content | strings | length > 0' >/dev/null

echo "simready local AI: live endpoint checks passed"
