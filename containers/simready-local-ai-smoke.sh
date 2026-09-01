#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${LOCAL_VLM_PATH:-/opt/models/qwen2.5-vl-7b-instruct}"
MODEL_NAME="${LOCAL_VLM_MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"

test -x /opt/local-ai/bin/vllm
test -f "${MODEL_PATH}/config.json"
test -f "${MODEL_PATH}/model.safetensors.index.json"
test -f "${MODEL_PATH}/LICENSE.apache-2.0"
/opt/local-ai/bin/pip check
"${PHYSICSNEMO_PYTHON:-/opt/venv/bin/python}" -m pip check
/opt/local-ai/bin/python -c 'from importlib.metadata import version; import torch, torchaudio, torchvision, vllm; assert version("vllm") == "0.26.0+cu129"; assert vllm.__version__ == "0.26.0"; assert torch.__version__.split("+", 1)[0] == "2.11.0"; assert torch.version.cuda == "12.9", torch.version.cuda; assert torchaudio.__version__.split("+", 1)[0] == "2.11.0"; assert torchvision.__version__.split("+", 1)[0] == "0.26.0"'
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
