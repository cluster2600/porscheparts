# Rebuild 2026-11-05: upstream USD BRep remains 1.0.1 on Python 3.12.
ARG PYTHON_BASE_IMAGE=python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
FROM ${PYTHON_BASE_IMAGE}
COPY containers/usd-brep.requirements.txt /tmp/requirements.txt
RUN --mount=type=bind,source=wheelhouse/usd-brep,target=/wheels,readonly pip install --no-index --find-links=/wheels --no-cache-dir --require-hashes -r /tmp/requirements.txt && pip check
COPY containers/examples/usd_brep_smoke.py /opt/usd_brep_smoke.py
WORKDIR /work
ENTRYPOINT ["python"]
CMD ["/opt/usd_brep_smoke.py", "--output", "/work/usd-brep"]
