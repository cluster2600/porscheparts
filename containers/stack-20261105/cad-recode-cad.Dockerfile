FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/cadquery/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv libgl1 libglu1-mesa libgomp1 libxcursor1 libxinerama1 \
    libxrandr2 libarpack2t64 libgfortran5 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=porscheparts/cadsim:stack-20261105 /opt/cadquery /opt/cadquery
COPY --from=porscheparts/cae-reference-f31:stack-20261105 /usr/local/bin/ccx /usr/local/bin/ccx
COPY containers/stack-20261105/cad-recode-cad.requirements.txt /opt/locks/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /opt/locks/requirements.txt && pip check
COPY deploy/vast/cad-recode/models.lock.json /deploy/vast/cad-recode/models.lock.json
COPY scripts/cad_recode /opt/cad-recode
COPY containers/stack-20261105/cad-recode-cad-smoke.py /opt/cad-recode/stack-smoke.py
USER 65534:65534
RUN --network=none python /opt/cad-recode/stack-smoke.py
ENTRYPOINT ["python"]
CMD ["/opt/cad-recode/stack-smoke.py"]
