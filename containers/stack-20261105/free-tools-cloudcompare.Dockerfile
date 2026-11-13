# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM python:3.15.2-slim-trixie@sha256:8c13a3f37a6a5b71498228e902c4b9f51c1f7900d49fabf71f9a650c6120e0d0
ARG TARGETARCH
RUN test "$TARGETARCH" = amd64
# Current stable Debian packages; exact inventory retained in the image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends cloudcompare \
    && dpkg-query -W > /opt/system-packages.txt \
    && rm -rf /var/lib/apt/lists/*
COPY benchmarks/free-tools/ft_common.py benchmarks/free-tools/ft_geometry.py benchmarks/free-tools/cloudcompare.py /opt/free-tools/
ENV HOME=/tmp QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1
WORKDIR /work
USER 1000:1000
ENTRYPOINT ["python", "/opt/free-tools/cloudcompare.py"]
