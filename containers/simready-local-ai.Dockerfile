# syntax=docker/dockerfile:1.7

FROM ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:86d31952f169c8daf78a474ec9d95663f4a7f211ab68f9cfad2371a67b9507bf

ARG VLLM_VERSION=0.8.5.post1
ARG PHYSICSNEMO_VERSION=2.2.0
ARG LOCAL_VLM_REPOSITORY=Qwen/Qwen2.5-VL-7B-Instruct
ARG LOCAL_VLM_REVISION=cc594898137f460bfe9f0759e9844b3ce807cfb5

ENV SIMREADY_LOCAL_AI=1 \
    SIMREADY_VLM_BASE_URL=http://127.0.0.1:8000/v1 \
    LOCAL_VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct \
    LOCAL_VLM_PATH=/opt/models/qwen2.5-vl-7b-instruct \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# vLLM supplies the local OpenAI-compatible multimodal endpoint. PhysicsNeMo
# core shares its PyTorch runtime; the larger optional solver environments stay
# in the dedicated physicsml image to avoid dependency conflicts here.
RUN python3.12 -m venv /opt/local-ai \
    && /opt/local-ai/bin/pip install --no-cache-dir --upgrade "pip>=26.1" \
    && /opt/local-ai/bin/pip install --no-cache-dir \
       "vllm==${VLLM_VERSION}" \
       "nvidia-physicsnemo==${PHYSICSNEMO_VERSION}" \
    && mkdir -p "${LOCAL_VLM_PATH}" \
    && HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 \
       /opt/local-ai/bin/python -c \
       "from huggingface_hub import snapshot_download; snapshot_download(repo_id='${LOCAL_VLM_REPOSITORY}', revision='${LOCAL_VLM_REVISION}', local_dir='${LOCAL_VLM_PATH}')" \
    && cp /usr/share/common-licenses/Apache-2.0 "${LOCAL_VLM_PATH}/LICENSE.apache-2.0" \
    && test -f "${LOCAL_VLM_PATH}/LICENSE.apache-2.0" \
    && test -f "${LOCAL_VLM_PATH}/model.safetensors.index.json" \
    && rm -rf /root/.cache/huggingface /root/.cache/pip

COPY containers/simready-local-ai-supervisord.conf /etc/simready-supervisord.conf
COPY containers/simready-local-ai-smoke.sh /usr/local/bin/simready-local-ai-smoke
COPY containers/simready-services.sh /usr/local/bin/simready-services
COPY containers/simready-smoke.sh /usr/local/bin/simready-smoke
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh

RUN chmod 0555 /usr/local/bin/simready-local-ai-smoke \
        /usr/local/bin/simready-services /usr/local/bin/simready-smoke \
        /usr/local/bin/smoke-test.sh \
    && /opt/local-ai/bin/python -c \
       "import physicsnemo, vllm; print(physicsnemo.__version__, vllm.__version__)" \
    && /usr/local/bin/simready-local-ai-smoke --offline

EXPOSE 8000 8001 8100 8200 22

LABEL org.opencontainers.image.title="3dprinting993-simready-local-ai" \
      org.opencontainers.image.description="Offline Qwen VLM, PhysicsNeMo and NVIDIA SimReady runtime for Porsche digital-twin research" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="Apache-2.0 AND LicenseRef-NVIDIA-Omniverse"
