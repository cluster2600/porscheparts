# Reuse an immutable, separately maintained SALOME distribution. NETGEN is the only mesher invoked.
# Publisher: https://hub.docker.com/r/simvia/salome ; amd64 digest verified 2026-10-25.
FROM simvia/salome:9.16.0@sha256:7578fb4b5363f4667433bb3ff03efa346679281da527fd67aff537578d044561
COPY benchmarks/free-tools/ft_common.py benchmarks/free-tools/ft_geometry.py benchmarks/free-tools/salome_worker.py /opt/free-tools/
ENV HOME=/tmp PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen
WORKDIR /work
ENTRYPOINT ["salome", "shell", "--", "python3", "/opt/free-tools/salome_worker.py"]
