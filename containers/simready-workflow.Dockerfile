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
    && mkdir -p /opt/usd-convert-cad-preflight/smoke-a \
       /opt/usd-convert-cad-preflight/smoke-b \
    && /opt/usd-convert-cad-preflight/convert.py \
       /opt/usd-convert-cad-preflight/smoke.step \
       /opt/usd-convert-cad-preflight/smoke-a/smoke.usdc \
       --report /opt/usd-convert-cad-preflight/smoke-a/report.json \
       --log /opt/usd-convert-cad-preflight/smoke-a/conversion.log --quiet \
    && /opt/usd-convert-cad-preflight/convert.py \
       /opt/usd-convert-cad-preflight/smoke.step \
       /opt/usd-convert-cad-preflight/smoke-b/smoke.usdc \
       --report /opt/usd-convert-cad-preflight/smoke-b/report.json \
       --log /opt/usd-convert-cad-preflight/smoke-b/conversion.log --quiet \
    && /opt/simready-validation/bin/python -c \
       "from hashlib import sha256; from pathlib import Path; from pxr import Sdf, Usd, UsdGeom, UsdPhysics; import omni.asset_validator; paths = [Path('/opt/usd-convert-cad-preflight/smoke-a/smoke.usdc'), Path('/opt/usd-convert-cad-preflight/smoke-b/smoke.usdc')]; stages = [Usd.Stage.Open(str(path)) for path in paths]; assert all(stages) and Usd.GetVersion(); assert all(stage.GetDefaultPrim().GetPath() == Sdf.Path('/smoke') for stage in stages); assert all([prim.GetPath() for prim in stage.GetPseudoRoot().GetChildren()] == [Sdf.Path('/smoke')] for stage in stages); assert all(not stage.GetRootLayer().documentation for stage in stages); assert all(all(stage.GetObjectAtPath(target) for prim in stage.Traverse() for relationship in prim.GetRelationships() for target in relationship.GetTargets()) for stage in stages); assert all(all(stage.GetObjectAtPath(target) for prim in stage.Traverse() for attribute in prim.GetAttributes() for target in attribute.GetConnections()) for stage in stages); assert len({sha256(path.read_bytes()).hexdigest() for path in paths}) == 1" \
    && rm -f /opt/usd-convert-cad-preflight/smoke.step \
    && rm -rf /opt/usd-convert-cad-preflight/smoke-a \
       /opt/usd-convert-cad-preflight/smoke-b

LABEL org.opencontainers.image.title="3dprinting993-simready-workflow" \
      org.opencontainers.image.description="Pinned SimReady runtime with NVIDIA CAD-to-SimReady preflight compatibility"
