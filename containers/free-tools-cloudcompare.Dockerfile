# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM python:3.12.14-slim-trixie@sha256:44ff437bba879d4941b710a369a8f19266aea34b29002807f0c487fabc9eec9b
ARG TARGETARCH
RUN test "$TARGETARCH" = amd64
# Freeze the Debian archive as well as the application version.
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261020T000000Z trixie main' > /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends cloudcompare=2.13.2+git20240821+ds-1 \
    && dpkg-query -W > /opt/system-packages.txt \
    && rm -rf /var/lib/apt/lists/*
COPY benchmarks/free-tools/ft_common.py benchmarks/free-tools/ft_geometry.py benchmarks/free-tools/cloudcompare.py /opt/free-tools/
ENV HOME=/tmp QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1
WORKDIR /work
USER 1000:1000
ENTRYPOINT ["python", "/opt/free-tools/cloudcompare.py"]
