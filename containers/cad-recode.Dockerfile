# Distinct runtimes: CAD execution never receives models, secrets or network.
FROM python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3 AS cad
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglu1-mesa libgomp1 && rm -rf /var/lib/apt/lists/*
COPY containers/cad-recode-cad.lock.txt /opt/cad-recode/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /opt/cad-recode/requirements.txt && pip check
COPY deploy/vast/cad-recode/models.lock.json /deploy/vast/cad-recode/models.lock.json
COPY scripts/cad_recode /opt/cad-recode
ENV PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
USER 65534:65534
CMD ["python", "/opt/cad-recode/pipeline.py", "--help"]

FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime@sha256:c16f4c749e2d9e96878875cdf6cc45cddda1d1a36fddd371dd6f2360f1b6e2a2 AS inference
RUN pip install --no-cache-dir transformers==4.47.1 accelerate==1.2.1 numpy==2.2.6 && pip check
COPY deploy/vast/cad-recode/models.lock.json /deploy/vast/cad-recode/models.lock.json
COPY scripts/cad_recode /opt/cad-recode
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
USER 65534:65534
ENTRYPOINT ["python", "/opt/cad-recode/infer.py"]
