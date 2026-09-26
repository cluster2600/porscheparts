FROM node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN npm install -g openclaw@2026.9.6
ENV OPENCLAW_CONFIG_PATH=/etc/openclaw/cad.json OPENCLAW_STATE_DIR=/state HOME=/state
COPY deploy/vast/cad-recode/openclaw.json /etc/openclaw/cad.json
USER node
ENTRYPOINT ["openclaw"]
CMD ["gateway", "run"]
