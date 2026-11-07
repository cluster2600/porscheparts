# syntax=docker/dockerfile:1.7
# Candidate uses Foundation 14; frozen Foundation 13 consumers require migration.
FROM porscheparts/cae-reference-f31:stack-20261105 AS reference
FROM porscheparts/openfoam-engine-f35:stack-20261105
USER root
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/venv/bin:/opt/aate/bin:/usr/local/bin:/usr/bin:/bin \
    OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libarpack2t64 libgfortran5 libgomp1 libglu1-mesa libxcursor1 libxinerama1 libxft2 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=reference /opt/venv /opt/venv
COPY --from=reference /usr/local/bin/ccx /usr/local/bin/ccx
COPY --from=reference /opt/stack/ccx-smoke.py /opt/stack/ccx-smoke.py
COPY containers/stack-20261105/gmsh-volume-smoke.py /opt/stack/gmsh-volume-smoke.py
RUN --network=none python /opt/stack/gmsh-volume-smoke.py \
    && python /opt/stack/ccx-smoke.py /tmp/ccx-smoke \
    && cat /tmp/ccx-smoke/checks.json && rm -rf /tmp/ccx-smoke \
    && openfoam-engine-f35-smoke
ENTRYPOINT ["python"]
CMD ["/opt/stack/gmsh-volume-smoke.py"]
