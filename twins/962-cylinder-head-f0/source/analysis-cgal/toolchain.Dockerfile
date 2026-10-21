# Replay recipe for the dedicated toolchain installation. The original installation
# used an owned container plus docker commit; exact package/image hashes are recorded.
FROM bionic-openfoam2406-diagnostic-build@sha256:586639782387349737869b383c9f98ec03614221255a9609009c395279835e07
USER root
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libcgal-dev=5.6-1build3
ENTRYPOINT []
