# syntax=docker/dockerfile:1.7

FROM ghcr.io/cluster2600/3dprinting993-simready@sha256:0562c69276c0d3065990cb9b1b8641dcd29355d0dccb9082dcf266fa2d22e90a

ENV USD_CONVERT_CAD_ROOT=/opt/usd-convert-cad-preflight \
    PHYSICAL_AI_SIMREADY_VALIDATE_VENV=/opt/simready-validation \
    PATH=/opt/simready-validation/bin:/opt/usd-convert-cad/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COPY containers/simready-preflight/convert.py /opt/usd-convert-cad-preflight/convert.py
COPY containers/simready-preflight/validate.py /opt/usd-convert-cad-preflight/validate.py
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
    && /opt/simready-validation/bin/python -c \
       "from pxr import Usd, UsdGeom, UsdPhysics; import omni.asset_validator; assert Usd.GetVersion()"

LABEL org.opencontainers.image.title="3dprinting993-simready-workflow" \
      org.opencontainers.image.description="Pinned SimReady runtime with NVIDIA CAD-to-SimReady preflight compatibility"
