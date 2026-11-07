FROM node:26.13.0-bookworm-slim@sha256:bc0a2afd3b74ce12222fc8bab99271e66257f021078f5f4a5d687a77d280c1d9
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/coordinator
COPY containers/stack-20261105/openclaw/package*.json ./
RUN npm ci --omit=dev --no-audit --no-fund \
    && ln -s /opt/coordinator/node_modules/.bin/openclaw /usr/local/bin/openclaw \
    && install -d -o node -g node /state /workspace
ENV OPENCLAW_CONFIG_PATH=/etc/openclaw/cad.json OPENCLAW_STATE_DIR=/state HOME=/state
COPY deploy/vast/cad-recode/openclaw.json /etc/openclaw/cad.json
USER node
RUN --network=none openclaw --version && openclaw config validate
ENTRYPOINT ["openclaw"]
CMD ["gateway", "run"]
