ARG PYTHON_BASE_IMAGE=python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
FROM ${PYTHON_BASE_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN --mount=type=bind,source=debhouse/common,target=/debs,readonly dpkg -i /debs/*.deb
COPY containers/stack-20261105/ov-libraries.requirements.txt /opt/requirements.txt
RUN --mount=type=bind,source=wheelhouse/ov,target=/wheels,readonly python -m pip install --no-index --find-links=/wheels --no-cache-dir --only-binary=:all: --require-hashes -r /opt/requirements.txt \
    && python -m pip check
COPY containers/stack-20261105/ov-smoke.py /opt/ov-smoke.py
RUN --network=none python /opt/ov-smoke.py
WORKDIR /workspace
ENTRYPOINT ["python"]
CMD ["/opt/ov-smoke.py"]
