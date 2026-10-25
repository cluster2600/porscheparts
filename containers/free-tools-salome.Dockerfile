# Reuse an immutable, separately maintained SALOME distribution. NETGEN is the only mesher invoked.
# Publisher: https://hub.docker.com/r/simvia/salome ; amd64 digest verified 2026-10-25.
FROM simvia/salome:9.16.0@sha256:7578fb4b5363f4667433bb3ff03efa346679281da527fd67aff537578d044561
COPY benchmarks/free-tools/ft_common.py benchmarks/free-tools/ft_geometry.py benchmarks/free-tools/salome_worker.py /opt/free-tools/
USER root
RUN test -f /opt/SALOME-9.16.0-native-DB12-SRC/env_launch.sh
# The control runner uses the host UID, so published runtime files must be readable by it.
RUN stat -c '%a %n' /opt/SALOME-9.16.0-native-DB12-SRC/BINARIES-DB12/KERNEL/lib/python3.11/site-packages/salome/salome/__init__.py \
    && find /opt/SALOME-9.16.0-native-DB12-SRC/BINARIES-DB12 -type d ! -perm -0005 -exec chmod a+rx {} + \
    && find /opt/SALOME-9.16.0-native-DB12-SRC/BINARIES-DB12 -type f ! -perm -0004 -exec chmod a+rX {} +
RUN /bin/bash -c 'source /opt/SALOME-9.16.0-native-DB12-SRC/env_launch.sh; "$PYTHONBIN" -c "import salome; print(salome.__file__)"'
COPY --chmod=755 containers/free-tools-salome-entrypoint.sh /opt/free-tools/entrypoint.sh
USER user
ENV HOME=/tmp PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen
ENTRYPOINT ["/opt/free-tools/entrypoint.sh"]
