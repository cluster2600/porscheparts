# syntax=docker/dockerfile:1.7

FROM ghcr.io/cluster2600/3dprinting993-simready@sha256:3dc95bf1fc5f7942c86c5dba33da05b7f852aea34684c1079b24df0915324f46

ENV USD_CONVERT_CAD_ROOT=/opt/usd-convert-cad-preflight \
    PHYSICAL_AI_SIMREADY_VALIDATE_VENV=/opt/simready-validation \
    PATH=/opt/simready-validation/bin:/opt/usd-convert-cad/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COPY containers/simready-preflight/convert.py /opt/usd-convert-cad-preflight/convert.py
COPY containers/simready-preflight/validate.py /opt/usd-convert-cad-preflight/validate.py
COPY containers/simready-preflight/formats.py /opt/usd-convert-cad-preflight/src/usd_convert_cad/formats.py
COPY components/wheels/fuchs/derived/37024.013-interface-proxy.step /opt/usd-convert-cad-preflight/smoke.step
COPY containers/simready-vast-onstart.sh /usr/local/bin/simready-vast-onstart
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh
COPY containers/simready-services.sh /usr/local/bin/simready-services
COPY containers/simready-smoke.sh /usr/local/bin/simready-smoke
COPY containers/simready-nvidia-auth-check.sh /usr/local/bin/simready-nvidia-auth-check
COPY containers/simready-profile-validate.sh /usr/local/bin/simready-profile-validate

RUN chmod 0555 /opt/usd-convert-cad-preflight/convert.py /opt/usd-convert-cad-preflight/validate.py \
        /usr/local/bin/simready-vast-onstart /usr/local/bin/smoke-test.sh \
        /usr/local/bin/simready-services /usr/local/bin/simready-smoke \
        /usr/local/bin/simready-nvidia-auth-check /usr/local/bin/simready-profile-validate \
    && /opt/usd-convert-cad-preflight/validate.py \
    && /opt/usd-convert-cad-preflight/convert.py \
       /opt/usd-convert-cad-preflight/smoke.step \
       /opt/usd-convert-cad-preflight/smoke.usdc \
       --report /opt/usd-convert-cad-preflight/smoke-report.json \
       --log /opt/usd-convert-cad-preflight/smoke.log --quiet \
    && /opt/simready-validation/bin/python -c \
       "from pxr import Usd, UsdGeom, UsdPhysics; import omni.asset_validator; stage = Usd.Stage.Open('/opt/usd-convert-cad-preflight/smoke.usdc'); assert stage and Usd.GetVersion()" \
    && rm -f /opt/usd-convert-cad-preflight/smoke.step \
       /opt/usd-convert-cad-preflight/smoke.usdc \
       /opt/usd-convert-cad-preflight/smoke-report.json \
       /opt/usd-convert-cad-preflight/smoke.log

LABEL org.opencontainers.image.title="3dprinting993-simready-workflow" \
      org.opencontainers.image.description="Pinned SimReady runtime with NVIDIA CAD-to-SimReady preflight compatibility"
