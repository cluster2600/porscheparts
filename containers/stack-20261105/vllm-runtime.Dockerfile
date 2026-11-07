# Auxiliary upstream runtime; GPU model serving is a separate acceptance gate.
FROM vllm/vllm-openai:v0.33.0@sha256:d825baf9ce4b1b6bfc5ecc7b79880c7e6748c65a72d697ce3d47607aafa84c6e
COPY containers/stack-20261105/vllm-cpu-smoke.py /opt/stack/vllm-cpu-smoke.py
COPY containers/stack-20261105/vllm-dependency-check.py /opt/stack/vllm-dependency-check.py
# The unrequired experimental exporter conflicts with the retained LMCache SDK.
RUN python3 -m pip uninstall -y opentelemetry-exporter-otlp-common \
    && python3 /opt/stack/vllm-dependency-check.py \
    && python3 -m pip freeze --all > /opt/stack/runtime.freeze.txt
RUN --network=none python3 /opt/stack/vllm-cpu-smoke.py
ENTRYPOINT ["python3"]
CMD ["/opt/stack/vllm-cpu-smoke.py"]
