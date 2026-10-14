FROM python:3.12.13-slim-bookworm@sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONNOUSERSITE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/workspace/cache/huggingface \
    HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    MLX_CUDA_GRAPH_CACHE_SIZE=16384 \
    MLX_ENABLE_CACHE_THRASHING_CHECK=1

RUN test "${TARGETARCH}" = amd64 \
    && apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libstdc++6 openssh-server \
    && rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd /workspace

COPY containers/qwen-picogk-training-vast/requirements.txt /opt/qwen-training/requirements.txt
RUN python -m pip install --timeout 120 --no-compile -r /opt/qwen-training/requirements.txt \
    && python -m pip check \
    && python -m pip freeze --all > /opt/qwen-training/resolved-packages.txt

COPY containers/qwen-picogk-training-vast/train.py \
     containers/qwen-picogk-training-vast/base_runtime.py \
     containers/qwen-picogk-training-vast/download-model7b.py \
     containers/qwen-picogk-training-vast/base-profile-7b.json \
     containers/qwen-picogk-training-vast/image_smoke.py \
     containers/qwen-picogk-training-vast/inputs.json /opt/qwen-training/

RUN python /opt/qwen-training/image_smoke.py \
    && chmod -R a-w /opt/qwen-training
WORKDIR /workspace
ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility
LABEL org.opencontainers.image.title="Qwen PicoGK training Vast" \
      org.opencontainers.image.source="https://github.com/cluster2600/porscheparts" \
      org.opencontainers.image.description="Explicit MLX CUDA 12 QLoRA commands; no model, corpus or automatic training"
CMD ["bash"]
