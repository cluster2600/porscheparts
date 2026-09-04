# syntax=docker/dockerfile:1.7

ARG TARGETPLATFORM=linux/amd64
FROM --platform=${TARGETPLATFORM} ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:79e76882a8f493012eb4cc9ab061bce0ca2d075cd505d6e33a5200e7e1e9b126

ARG VLLM_VERSION=0.26.0
ARG VLLM_CU129_WHEEL_URL=https://github.com/vllm-project/vllm/releases/download/v0.26.0/vllm-0.26.0%2Bcu129-cp38-abi3-manylinux_2_28_x86_64.whl#sha256=6ce4ca30616f0a35810391015622b197a7b8b267ed27f8716f0789db79ff578b
ARG VLLM_TORCH_VERSION=2.11.0
ARG VLLM_TORCHVISION_VERSION=0.26.0
ARG VLLM_TORCHAUDIO_VERSION=2.11.0
ARG PHYSICSNEMO_VERSION=2.2.0
ARG TORCH_VERSION=2.10.0
ARG TORCHVISION_VERSION=0.25.0
ARG DEEPXDE_VERSION=1.15.0
ARG BUILD123D_VERSION=0.11.1
ARG CADQUERY_VERSION=2.8.0
ARG GMSH_VERSION=4.15.2
ARG MESHIO_VERSION=5.3.5
ARG PYVISTA_VERSION=0.48.4
ARG TRIMESH_VERSION=5.1.0
ARG MANIFOLD3D_VERSION=3.5.2
ARG NUMPY_VERSION=2.5.2
ARG SCIPY_VERSION=1.18.1
ARG PILLOW_VERSION=12.3.0
ARG TQDM_VERSION=4.70.0
ARG RICH_VERSION=15.0.0
ARG TYPER_VERSION=0.27.2
ARG MATPLOTLIB_VERSION=3.11.1
ARG LOCAL_VLM_REPOSITORY=Qwen/Qwen2.5-VL-7B-Instruct
ARG LOCAL_VLM_REVISION=cc594898137f460bfe9f0759e9844b3ce807cfb5
# Build-only controls: bytecode is unnecessary in immutable layers and pip's
# interactive progress/version probes add work and log traffic on CI runners.
ARG PYTHONDONTWRITEBYTECODE=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_PROGRESS_BAR=off

ENV SIMREADY_LOCAL_AI=1 \
    SIMREADY_VLM_BASE_URL=http://127.0.0.1:8000/v1 \
    LOCAL_VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct \
    LOCAL_VLM_PATH=/opt/models/qwen2.5-vl-7b-instruct \
    VLLM_LIBRARY_PATH=/opt/local-ai/lib/python3.12/site-packages/torch/lib:/opt/local-ai/lib/python3.12/site-packages/nvidia/cu13/lib:/opt/local-ai/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:/opt/local-ai/lib/python3.12/site-packages/nvidia/cuda_nvrtc/lib \
    PHYSICSNEMO_PYTHON=/opt/venv/bin/python \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_XET=1

# Keep PhysicsNeMo isolated from the independently pinned vLLM CUDA stack.
# Install the heavy runtime separately so no OCI layer combines the whole
# PhysicsNeMo environment with the embedded vision model.
RUN python3.12 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --no-compile --upgrade "pip>=26.1"

RUN /opt/venv/bin/pip install --no-cache-dir --no-compile \
       --index-url https://download.pytorch.org/whl/cu129 \
       "torch==${TORCH_VERSION}"

RUN /opt/venv/bin/pip install --no-cache-dir --no-compile \
       --index-url https://download.pytorch.org/whl/cu129 \
       "torchvision==${TORCHVISION_VERSION}"

RUN /opt/venv/bin/pip install --no-cache-dir --no-compile \
       "build123d==${BUILD123D_VERSION}" "cadquery==${CADQUERY_VERSION}" \
       "gmsh==${GMSH_VERSION}" "meshio==${MESHIO_VERSION}" \
       "pyvista==${PYVISTA_VERSION}" "trimesh==${TRIMESH_VERSION}" \
       "manifold3d==${MANIFOLD3D_VERSION}" "numpy==${NUMPY_VERSION}" \
       "scipy==${SCIPY_VERSION}" "pillow==${PILLOW_VERSION}" \
       "tqdm==${TQDM_VERSION}" "rich==${RICH_VERSION}" \
       "typer==${TYPER_VERSION}" "matplotlib==${MATPLOTLIB_VERSION}"

COPY containers/simready-physicsnemo-constraints.txt /opt/build/physicsnemo-constraints.txt

RUN /opt/venv/bin/pip install --no-cache-dir --no-compile \
       --constraint /opt/build/physicsnemo-constraints.txt \
       --extra-index-url https://download.pytorch.org/whl/cu129 \
       "nvidia-physicsnemo[sym]==${PHYSICSNEMO_VERSION}" \
       "deepxde==${DEEPXDE_VERSION}" \
    && /opt/venv/bin/pip check

# vLLM supplies the local OpenAI-compatible multimodal endpoint. Its pinned
# PyTorch stack is installed first so the full CUDA runtime and vLLM wheel do
# not end up in one registry layer larger than Vast can reliably fetch.
RUN python3.12 -m venv /opt/local-ai \
    && /opt/local-ai/bin/pip install --no-cache-dir --no-compile --upgrade "pip>=26.1"

RUN /opt/local-ai/bin/pip install --no-cache-dir --no-compile \
       --index-url https://download.pytorch.org/whl/cu129 \
       "torch==${VLLM_TORCH_VERSION}"

RUN /opt/local-ai/bin/pip install --no-cache-dir --no-compile \
       --index-url https://download.pytorch.org/whl/cu129 \
       "torchvision==${VLLM_TORCHVISION_VERSION}" \
       "torchaudio==${VLLM_TORCHAUDIO_VERSION}"

RUN /opt/local-ai/bin/pip install --no-cache-dir --no-compile \
       --extra-index-url https://download.pytorch.org/whl/cu129 \
       "${VLLM_CU129_WHEEL_URL}" \
    && /opt/local-ai/bin/pip check

# Metadata is small. Each safetensors shard is deliberately authored by its
# own ADD instruction, with an immutable revision and checksum, so Vast.ai can
# retry individual ~1-4 GB layers instead of a single 17 GB model layer.
RUN mkdir -p "${LOCAL_VLM_PATH}" \
    && HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 \
       /opt/local-ai/bin/python -c \
       "from huggingface_hub import snapshot_download; snapshot_download(repo_id='${LOCAL_VLM_REPOSITORY}', revision='${LOCAL_VLM_REVISION}', local_dir='${LOCAL_VLM_PATH}', allow_patterns=['*.json', '*.txt'], max_workers=2)" \
    && rm -rf "${LOCAL_VLM_PATH}/.cache" /root/.cache/huggingface /root/.cache/pip

ADD --link --checksum=sha256:e97b877e47fde53a6c6e77aafb36e58e91ee9d95c4a3eeac6f1b5c0e6a1c986e \
    https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/cc594898137f460bfe9f0759e9844b3ce807cfb5/model-00001-of-00005.safetensors \
    /opt/models/qwen2.5-vl-7b-instruct/model-00001-of-00005.safetensors
ADD --link --checksum=sha256:a9a300a43b4724eee2abe7c18ceb26768d0ab011eb0cad19d9bfd2476a24d024 \
    https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/cc594898137f460bfe9f0759e9844b3ce807cfb5/model-00002-of-00005.safetensors \
    /opt/models/qwen2.5-vl-7b-instruct/model-00002-of-00005.safetensors
ADD --link --checksum=sha256:111223d173e00bbee81cba1216fad28668df3476706b7fd26f4d5b50f8b3a507 \
    https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/cc594898137f460bfe9f0759e9844b3ce807cfb5/model-00003-of-00005.safetensors \
    /opt/models/qwen2.5-vl-7b-instruct/model-00003-of-00005.safetensors
ADD --link --checksum=sha256:ef47f634fa57d46ee134edcc09f34085a47da1e16c12a2abe0d67118be6d72ed \
    https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/cc594898137f460bfe9f0759e9844b3ce807cfb5/model-00004-of-00005.safetensors \
    /opt/models/qwen2.5-vl-7b-instruct/model-00004-of-00005.safetensors
ADD --link --checksum=sha256:0c859795ad3a627a9b95bcb762e059d5b768a4a36fdd4affeff269d93fdecc67 \
    https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/cc594898137f460bfe9f0759e9844b3ce807cfb5/model-00005-of-00005.safetensors \
    /opt/models/qwen2.5-vl-7b-instruct/model-00005-of-00005.safetensors

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && cp /usr/share/common-licenses/Apache-2.0 "${LOCAL_VLM_PATH}/LICENSE.apache-2.0" \
    && test -f "${LOCAL_VLM_PATH}/LICENSE.apache-2.0" \
    && test -f "${LOCAL_VLM_PATH}/model.safetensors.index.json" \
    && test "$(find "${LOCAL_VLM_PATH}" -maxdepth 1 -name 'model-*.safetensors' | wc -l)" = 5

COPY containers/simready-local-ai-supervisord.conf /etc/simready-supervisord.conf
COPY containers/simready-local-ai-smoke.sh /usr/local/bin/simready-local-ai-smoke
COPY containers/physicsnemo-gpu-smoke.py /usr/local/bin/physicsnemo-gpu-smoke
COPY containers/simready-vast-onstart.sh /usr/local/bin/simready-vast-onstart
COPY containers/simready-services.sh /usr/local/bin/simready-services
COPY containers/simready-smoke.sh /usr/local/bin/simready-smoke
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh

RUN chmod 0555 /usr/local/bin/simready-local-ai-smoke \
        /usr/local/bin/physicsnemo-gpu-smoke \
        /usr/local/bin/simready-vast-onstart \
        /usr/local/bin/simready-services /usr/local/bin/simready-smoke \
        /usr/local/bin/smoke-test.sh \
    && PYTHONDONTWRITEBYTECODE=1 /usr/local/bin/simready-local-ai-smoke --offline

EXPOSE 8000 8001 8100 8200 22

LABEL org.opencontainers.image.title="3dprinting993-simready-local-ai" \
      org.opencontainers.image.description="Offline Qwen VLM, PhysicsNeMo and NVIDIA SimReady runtime for Porsche digital-twin research" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="Apache-2.0 AND LicenseRef-NVIDIA-Omniverse"
