# syntax=docker/dockerfile:1.7
# Reuse the qualified station layers; runtime corrections only.
FROM ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:540d9d4af34a73f91114f2d3dd4f4ad847eee42037c26efaf1caadb5b155e871
COPY --chmod=0644 deploy/vast/station-client/main.js deploy/vast/station-client/index.html deploy/vast/station-client/config.mjs /opt/station-client/
COPY containers/picogk-station/qwen.sh /opt/station/qwen.sh
COPY deploy/vast/station/media-relay.py /usr/local/bin/station-media-relay
RUN chmod 0755 /opt/station/qwen.sh /usr/local/bin/station-media-relay \
    && OVRTX_BIN=/opt/ovrtx-runtime/lib/python3.12/site-packages/ovrtx/bin \
    && mkdir -p "${OVRTX_BIN}/cache" "${OVRTX_BIN}/mdl/omniverse_exts" \
    && chown -R station-worker:station-worker "${OVRTX_BIN}/cache" "${OVRTX_BIN}/mdl/omniverse_exts" \
    && runuser -u station-worker -- test -w "${OVRTX_BIN}/cache" \
    && runuser -u station-worker -- test -w "${OVRTX_BIN}/mdl/omniverse_exts" \
    && /usr/bin/python3 /usr/local/bin/station-media-relay --help >/dev/null \
    && bash -n /opt/station/qwen.sh
